#!/usr/bin/env python3
"""
一键转换脚本：将 PyTorch 模型转换为 TensorFlow 版本并导出 PB 模型

用法:
    # 默认 demo 模型
    python demo/run_conversion.py
    python demo/run_conversion.py --channels-first

    # 自定义模型文件
    python demo/run_conversion.py --pt-model path/to/model.py --model-class UNet
    python demo/run_conversion.py --pt-model path/to/model.py --pt-weights path/to/weights.pth

    # 自定义参数
    python demo/run_conversion.py --model-args "in_channels=1, out_channels=2"
    python demo/run_conversion.py --input-shapes "3,128,128"              # 单输入
    python demo/run_conversion.py --input-shapes "1,224,224 1,224,224"    # 多输入

输出文件 (<output-dir>/):
    model_tf.py        — 转换后的 TensorFlow 模型代码
    weights.weights.h5 — 转换后的 TensorFlow 权重
    frozen_model.pb    — 冻结图 (昇腾部署用)
    saved_model/       — TF SavedModel 格式
"""

import argparse
import ast
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np

# 设置项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DEMO_DIR = PROJECT_ROOT / "demo"
DEFAULT_PT_MODEL = DEMO_DIR / "pytorch_model" / "model.py"
DEFAULT_OUTPUT_DIR = DEMO_DIR / "output"


# ──────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────

def _detect_entry_class(source: str, base_keyword: str = "Module") -> str | None:
    """从源文件 AST 中检测入口模型类 (最后一个含 base_keyword 基类的 class)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    entry = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_str = ast.dump(base) if isinstance(base, ast.Attribute) else getattr(base, "id", "")
                if base_keyword in base_str:
                    entry = node.name
    return entry


def _detect_forward_args(source: str, class_name: str) -> list[str]:
    """检测指定 class 的 forward/call 方法参数列表 (不含 self/training)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in ("forward", "call"):
                    return [
                        a.arg for a in item.args.args
                        if a.arg not in ("self", "training")
                    ]
    return []


def _load_class_from_file(file_path: Path, class_name: str, module_name: str = "dynamic_model"):
    """从 Python 文件动态加载指定 class."""
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cls = getattr(mod, class_name, None)
    if cls is None:
        available = [n for n in dir(mod) if not n.startswith("_")]
        raise ValueError(
            f"类 '{class_name}' 在 {file_path} 中未找到。"
            f"可用名称: {available}"
        )
    return mod, cls


def _parse_input_shapes(raw: str) -> list[tuple[int, ...]]:
    """解析 --input-shapes 字符串为 list[tuple].

    格式: "C,H,W" (单输入) 或 "C1,H1,W1 C2,H2,W2" (多输入, 空格分隔)
    """
    shapes = []
    for part in raw.strip().split():
        dims = tuple(int(d) for d in part.split(","))
        shapes.append(dims)
    return shapes


def _build_dummy_inputs(input_shapes, batch_size):
    """根据 input_shapes 构建 numpy dummy 输入列表 (NCHW 格式)."""
    inputs = []
    for shape in input_shapes:
        if len(shape) == 3:
            c, h, w = shape
            inputs.append(np.random.randn(batch_size, c, h, w).astype(np.float32))
        else:
            inputs.append(np.random.randn(batch_size, *shape).astype(np.float32))
    return inputs


def _nchw_to_nhwc(arr):
    """将 4D NCHW 数组转为 NHWC."""
    if arr.ndim == 4:
        return np.transpose(arr, (0, 2, 3, 1))
    return arr


def _nhwc_to_nchw(arr):
    """将 4D NHWC 数组转为 NCHW."""
    if arr.ndim == 4:
        return np.transpose(arr, (0, 3, 1, 2))
    return arr


def _to_numpy(tensor):
    """将 PyTorch/TF tensor 或 tuple/list 转为 numpy, 多输出时取第一个."""
    if isinstance(tensor, (tuple, list)):
        tensor = tensor[0]
    if hasattr(tensor, "numpy"):
        return tensor.numpy()
    return np.asarray(tensor)


def main():
    parser = argparse.ArgumentParser(description="PyTorch Model → TensorFlow 全流程转换")
    parser.add_argument(
        "--pt-model", default=None,
        help="PyTorch 模型文件路径 (默认: demo/pytorch_model/model.py)",
    )
    parser.add_argument(
        "--channels-first", action="store_true",
        help="保持 NCHW 数据格式 (匹配 PyTorch), TF 层使用 data_format='channels_first'",
    )
    parser.add_argument(
        "--pt-weights", default=None,
        help="PyTorch 权重文件路径 (默认: 与模型同目录, 不存在则自动初始化)",
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="输出目录 (默认: demo/output/)",
    )
    parser.add_argument(
        "--soc-version", default="Ascend910B4",
        help="目标昇腾 SoC 型号 (默认: Ascend910B4)",
    )
    parser.add_argument(
        "--model-class", default=None,
        help="入口模型类名 (如 UNet)。未指定时自动检测源文件中最后一个 nn.Module 子类",
    )
    parser.add_argument(
        "--model-args", default=None,
        help=(
            "模型构造参数 (Python kwargs 格式)。"
            "示例: 'in_channels=3, num_classes=2, base_features=32'。"
            "未指定时尝试使用模型默认参数"
        ),
    )
    parser.add_argument(
        "--input-shapes", default=None,
        help=(
            "模型输入形状 (CHW 格式, 不含 batch)。"
            "单输入: '3,128,128'  多输入: '3,128,128 1,128,128' (空格分隔)。"
            "未指定时根据 forward 签名参数数量自动推断"
        ),
    )
    parser.add_argument(
        "--cosine-threshold", type=float, default=0.99,
        help="精度校验的最低余弦相似度阈值 (默认: 0.99)",
    )
    args = parser.parse_args()

    channels_first = args.channels_first
    mode_label = "NCHW (channels_first)" if channels_first else "NHWC (channels_last)"

    # ──────────────────────────────────────────
    # 解析模型路径
    # ──────────────────────────────────────────
    pt_model_path = Path(args.pt_model) if args.pt_model else DEFAULT_PT_MODEL
    if not pt_model_path.exists():
        print(f"[ERROR] 找不到 PyTorch 模型文件: {pt_model_path}")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR

    # ──────────────────────────────────────────
    # 解析模型构造参数
    # ──────────────────────────────────────────
    model_kwargs = {}
    if args.model_args:
        for item in args.model_args.split(","):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                model_kwargs[k.strip()] = ast.literal_eval(v.strip())

    # ──────────────────────────────────────────
    # 检测入口模型类
    # ──────────────────────────────────────────
    pt_source = pt_model_path.read_text(encoding="utf-8")

    if args.model_class:
        entry_class = args.model_class
        print(f"  入口模型类: {entry_class} (用户指定)")
    else:
        entry_class = _detect_entry_class(pt_source, "Module")
        if entry_class is None:
            print("[ERROR] 未能自动检测到 nn.Module 子类，请通过 --model-class 指定")
            return 1
        print(f"  入口模型类: {entry_class} (自动检测)")

    # ──────────────────────────────────────────
    # 解析输入形状
    # ──────────────────────────────────────────
    if args.input_shapes:
        input_shapes = _parse_input_shapes(args.input_shapes)
    else:
        # 根据 forward 签名推断输入数量，每个输入默认使用第一个参数的形状
        forward_args = _detect_forward_args(pt_source, entry_class)
        num_inputs = max(len(forward_args), 1)
        in_channels = model_kwargs.get("in_channels", 3)
        default_shape = (in_channels, 128, 128)
        input_shapes = [default_shape] * num_inputs

    batch_size = 1
    num_tests = 5
    random_seed = 42
    cosine_threshold = args.cosine_threshold

    print("=" * 70)
    print("  PyTorch Model → TensorFlow 全流程转换")
    print(f"  模型文件: {pt_model_path}")
    print(f"  数据格式: {mode_label}")
    if model_kwargs:
        print(f"  模型参数: {', '.join(f'{k}={v}' for k, v in model_kwargs.items())}")
    if len(input_shapes) == 1:
        print(f"  输入形状: {input_shapes[0]} (CHW)")
    else:
        for idx, s in enumerate(input_shapes):
            print(f"  输入 {idx}: {s} (CHW)")
    print(f"  余弦阈值: {cosine_threshold}")
    print("=" * 70)

    # ──────────────────────────────────────────
    # 权重文件检查 & 自动初始化
    # ──────────────────────────────────────────
    if args.pt_weights:
        pt_weights_path = Path(args.pt_weights)
    else:
        # 默认: 与模型文件同目录下的 <model_stem>_weights.pth
        pt_weights_path = pt_model_path.parent / f"{pt_model_path.stem}_weights.pth"

    if not pt_weights_path.exists():
        print(f"  权重文件不存在，初始化模型参数并保存...")
        import torch
        sys.path.insert(0, str(pt_model_path.parent))
        _, ModelCls = _load_class_from_file(pt_model_path, entry_class, "pt_init_model")
        torch.manual_seed(random_seed)
        _init_model = ModelCls(**model_kwargs)
        _init_model.eval()
        pt_weights_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(_init_model.state_dict(), str(pt_weights_path))
        _param_count = sum(p.numel() for p in _init_model.parameters())
        print(f"  参数量: {_param_count:,}")
        print(f"  权重已初始化并保存: {pt_weights_path}")
        del _init_model

    output_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────
    # Step 1: 转换模型代码
    # ──────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("[Step 1/5] 转换 PyTorch 模型代码 → TensorFlow ...")
    from pytorch2tensorflow.converter import ModelConverter

    converter = ModelConverter(channels_first=channels_first)
    tf_model_path = output_dir / "model_tf.py"
    converted_code = converter.convert_file(str(pt_model_path), str(tf_model_path))
    line_count = converted_code.count("\n")
    print(f"  输出文件: {tf_model_path}")
    print(f"  代码行数: {line_count}")
    print(f"  数据格式: {mode_label}")
    print(f"  转换完成")

    # 展示关键转换片段
    print(f"\n  --- 转换后关键代码 ---")
    for line in converted_code.split("\n"):
        s = line.strip()
        if any(k in s for k in [
            "class ", "def call", "tf.pad(", "tf.concat(",
            "data_format", "BilinearUpsample2D",
        ]):
            print(f"  | {line.rstrip()}")

    # ──────────────────────────────────────────
    # Step 2: 加载 PyTorch 模型
    # ──────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("[Step 2/5] 加载 PyTorch 模型 & 权重 ...")
    import torch

    sys.path.insert(0, str(pt_model_path.parent))
    _, PyTorchModelCls = _load_class_from_file(pt_model_path, entry_class, "pt_model")

    pt_model = PyTorchModelCls(**model_kwargs)
    state_dict = torch.load(str(pt_weights_path), map_location="cpu", weights_only=True)
    pt_model.load_state_dict(state_dict)
    pt_model.eval()

    param_count = sum(p.numel() for p in pt_model.parameters())
    print(f"  参数量:   {param_count:,}")
    print(f"  PyTorch 模型加载完成")

    # ──────────────────────────────────────────
    # Step 3: 构建 TF 模型 & 转换权重
    # ──────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("[Step 3/5] 构建 TensorFlow 模型 & 转换权重 ...")
    import tensorflow as tf

    # 加载转换后的 TF 模型
    tf_mod, tf_cls = _load_class_from_file(tf_model_path, entry_class, "tf_model")
    if not (isinstance(tf_cls, type) and issubclass(tf_cls, tf.keras.Model)):
        # 如果指定类名在 TF 侧不是 keras Model，回退自动检测
        tf_cls = None
        tree = ast.parse(converted_code)
        tf_cls_names = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
        for cname in reversed(tf_cls_names):
            obj = getattr(tf_mod, cname, None)
            if obj and isinstance(obj, type) and issubclass(obj, tf.keras.Model):
                tf_cls = obj
                break
        if tf_cls is None:
            print("[ERROR] 未在转换后代码中找到 tf.keras.Model 子类")
            return 1

    tf_model = tf_cls(**model_kwargs)

    # 构建模型 (多输入兼容)
    dummy_inputs_tf = []
    for shape in input_shapes:
        if len(shape) == 3:
            c, h, w = shape
            if channels_first:
                dummy_inputs_tf.append(tf.zeros((batch_size, c, h, w)))
            else:
                dummy_inputs_tf.append(tf.zeros((batch_size, h, w, c)))
        else:
            dummy_inputs_tf.append(tf.zeros((batch_size, *shape)))

    if len(dummy_inputs_tf) == 1:
        tf_model(dummy_inputs_tf[0], training=False)
    else:
        tf_model(*dummy_inputs_tf, training=False)

    tf_param_count = sum(int(np.prod(v.shape)) for v in tf_model.weights)
    print(f"  TF 参数量: {tf_param_count:,}")

    # 权重转换
    from pytorch2tensorflow.weight_converter import WeightConverter
    weight_converter = WeightConverter(strict=False)

    tf_weights_path = str(output_dir / "weights.weights.h5")
    stats = weight_converter.convert(
        str(pt_weights_path), tf_model,
        output_path=tf_weights_path,
    )
    # 权重映射报告
    total_mappable = stats.get("total_mappable", stats["total_pytorch_weights"])
    match_method = stats.get("match_method", "name")
    method_label_w = "名称匹配" if match_method == "name" else "结构匹配"
    print(f"  映射策略: {method_label_w}")
    if match_method == "structural":
        name_hits = stats.get("name_based_matches", 0)
        print(f"    名称匹配命中 {name_hits}/{total_mappable}, 不足 50%，自动切换到结构匹配")
        print(f"    结构匹配按层顺序逐一对齐权重角色 (conv_kernel, bn_gamma …)")
    print(f"  映射结果: {stats['assigned']}/{total_mappable} 成功"
          f"  (跳过 {stats['skipped']}, 错误 {stats['errors']})")
    if stats["errors"] > 0:
        print(f"  [!] 映射错误详情:")
        for err in stats.get("error_details", []):
            print(f"      - {err}")
    skipped_entries = [e for e in stats.get("conversion_log", []) if e["action"] == "skip"]
    if skipped_entries:
        print(f"  跳过的权重 ({len(skipped_entries)} 个):")
        for entry in skipped_entries[:5]:
            reason = entry.get("reason", "")
            print(f"    - {entry['pytorch_name']}: {reason}")
        if len(skipped_entries) > 5:
            print(f"    ... 其余 {len(skipped_entries) - 5} 个已省略")
        print(f"  说明: 跳过的权重通常为 num_batches_tracked 等 TF 不需要的统计量，不影响推理精度")
    print(f"  权重文件: {tf_weights_path}")
    print(f"  权重转换完成")

    # ──────────────────────────────────────────
    # Step 4: 精度校验
    # ──────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("[Step 4/5] 校验 PyTorch <-> TensorFlow 输出精度 ...")

    np.random.seed(random_seed)
    torch.manual_seed(random_seed)
    all_max_abs = []
    all_cosine = []

    for i in range(num_tests):
        # 生成随机输入 (NCHW)
        inputs_nchw = _build_dummy_inputs(input_shapes, batch_size)

        # PyTorch 前向推理 (NCHW)
        with torch.no_grad():
            pt_tensors = [torch.from_numpy(x) for x in inputs_nchw]
            if len(pt_tensors) == 1:
                pt_out = _to_numpy(pt_model(pt_tensors[0]))
            else:
                pt_out = _to_numpy(pt_model(*pt_tensors))

        # TF 前向推理
        if channels_first:
            tf_inputs = [tf.constant(x) for x in inputs_nchw]
        else:
            tf_inputs = [tf.constant(_nchw_to_nhwc(x)) for x in inputs_nchw]

        if len(tf_inputs) == 1:
            tf_out = _to_numpy(tf_model(tf_inputs[0], training=False))
        else:
            tf_out = _to_numpy(tf_model(*tf_inputs, training=False))

        tf_out_nchw = tf_out if channels_first else _nhwc_to_nchw(tf_out)

        # 计算指标
        abs_diff = np.abs(pt_out - tf_out_nchw)
        max_abs = float(np.max(abs_diff))

        pt_flat = pt_out.flatten()
        tf_flat = tf_out_nchw.flatten()
        cos_sim = float(np.dot(pt_flat, tf_flat) / (
            np.linalg.norm(pt_flat) * np.linalg.norm(tf_flat) + 1e-10
        ))

        all_max_abs.append(max_abs)
        all_cosine.append(cos_sim)
        print(f"  样本 {i+1}: 最大绝对差={max_abs:.2e}, 余弦相似度={cos_sim:.6f}")

    avg_cosine = np.mean(all_cosine)
    avg_max_abs = np.mean(all_max_abs)
    passed = avg_cosine >= cosine_threshold
    status = "PASSED" if passed else "FAILED"
    print(f"\n  汇总 ({num_tests} 个样本):")
    print(f"    平均最大绝对差: {avg_max_abs:.2e}")
    print(f"    平均余弦相似度: {avg_cosine:.6f}")
    print(f"  精度校验: {status}")

    # ──────────────────────────────────────────
    # Step 5: 导出 PB 模型
    # ──────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("[Step 5/5] 导出 PB 模型 (昇腾部署) ...")
    from pytorch2tensorflow.exporter import PBExporter

    exporter = PBExporter(channels_first=channels_first)

    export_results = exporter.export_and_verify(
        tf_model,
        str(output_dir),
        input_shapes,
        soc_version=args.soc_version,
        batch_size=batch_size,
    )

    pb_path = export_results["frozen_graph_path"]
    pb_size = os.path.getsize(pb_path)
    print(f"  SavedModel: {export_results['saved_model_dir']}")
    print(f"  Frozen PB:  {pb_path} ({pb_size/1024:.0f} KB)")

    compat = export_results["ascend_compatibility"]
    compat_status = "兼容" if compat["compatible"] else "存在问题"
    print(f"  昇腾兼容:  {compat_status} (算子: {compat['unique_ops']} 种)")

    if compat["unsupported_ops"]:
        print(f"  未知算子:  {compat['unsupported_ops']}")

    print(f"\n  ATC 转换命令 (在昇腾环境执行):")
    for line in export_results["atc_command"].split("\n"):
        print(f"    {line}")

    # ──────────────────────────────────────────
    # 输出汇总
    # ──────────────────────────────────────────
    rel_output = output_dir.relative_to(PROJECT_ROOT) if output_dir.is_relative_to(PROJECT_ROOT) else output_dir
    print(f"\n{'=' * 70}")
    print("  转换完成! 输出文件汇总:")
    print(f"{'=' * 70}")
    print(f"  {rel_output}/")
    print(f"  ├── model_tf.py          TensorFlow 模型代码")
    print(f"  ├── weights.weights.h5   TensorFlow 权重")
    print(f"  ├── frozen_model.pb      冻结图 (PB 格式)")
    print(f"  └── saved_model/         SavedModel 格式")
    print(f"")
    print(f"  数据格式:  {mode_label}")
    print(f"  精度验证:  {status} (余弦相似度={avg_cosine:.6f})")
    print(f"  昇腾兼容:  {compat_status}")
    print(f"{'=' * 70}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
