#!/usr/bin/env python3
"""
一键转换脚本：将 PyTorch 模型转换为 TensorFlow 版本并导出 PB 模型

用法:
    python demo/run_conversion.py
    python demo/run_conversion.py --channels-first   # 保持 NCHW 格式

输入文件 (demo/pytorch_model/):
    model.py          — PyTorch 模型定义
    unet_weights.pth  — PyTorch 训练权重

输出文件 (demo/output/):
    model_tf.py        — 转换后的 TensorFlow 模型代码
    weights.weights.h5 — 转换后的 TensorFlow 权重
    frozen_model.pb    — 冻结图 (昇腾部署用)
    saved_model/       — TF SavedModel 格式
    验证报告            — 精度校验结果
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
PT_MODEL_DIR = DEMO_DIR / "pytorch_model"
OUTPUT_DIR = DEMO_DIR / "output"


def main():
    parser = argparse.ArgumentParser(description="PyTorch Model → TensorFlow 全流程转换")
    parser.add_argument(
        "--channels-first", action="store_true",
        help="保持 NCHW 数据格式 (匹配 PyTorch), TF 层使用 data_format='channels_first'",
    )
    parser.add_argument(
        "--pt-weights", default=None,
        help="PyTorch 权重文件路径 (默认: demo/pytorch_model/unet_weights.pth, 不存在则自动初始化)",
    )
    parser.add_argument(
        "--soc-version", default="Ascend910B4",
        help="目标昇腾 SoC 型号 (默认: Ascend910B4)",
    )
    args = parser.parse_args()

    channels_first = args.channels_first
    mode_label = "NCHW (channels_first)" if channels_first else "NHWC (channels_last)"

    # ──────────────────────────────────────────
    # 核心参数 (模型构造 / 数据维度 / 验证配置)
    # ──────────────────────────────────────────
    in_channels = 3           # 输入通道数
    num_classes = 2           # 输出类别数
    base_features = 32        # 基础特征图通道数
    input_shape = (in_channels, 128, 128)  # CHW 格式
    batch_size = 1            # 推理批次大小
    num_tests = 5             # 精度校验样本数
    random_seed = 42          # 随机种子 (可复现)
    cosine_threshold = 0.99   # 余弦相似度通过阈值

    print("=" * 70)
    print("  PyTorch Model → TensorFlow 全流程转换")
    print(f"  数据格式: {mode_label}")
    print(f"  模型参数: in_channels={in_channels}, num_classes={num_classes}, base_features={base_features}")
    print(f"  输入形状: {input_shape} (CHW)")
    print("=" * 70)

    # 检查输入文件
    pt_model_path = PT_MODEL_DIR / "model.py"
    pt_weights_path = Path(args.pt_weights) if args.pt_weights else PT_MODEL_DIR / "unet_weights.pth"

    if not pt_model_path.exists():
        print(f"[ERROR] 找不到 PyTorch 模型文件: {pt_model_path}")
        return 1
    if not pt_weights_path.exists():
        print(f"  权重文件不存在，初始化模型参数并保存...")
        import torch
        sys.path.insert(0, str(PT_MODEL_DIR))
        from model import UNet as Model
        torch.manual_seed(random_seed)
        _init_model = Model(in_channels=in_channels, num_classes=num_classes, base_features=base_features)
        _init_model.eval()
        pt_weights_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(_init_model.state_dict(), str(pt_weights_path))
        _param_count = sum(p.numel() for p in _init_model.parameters())
        print(f"  参数量: {_param_count:,}")
        print(f"  权重已初始化并保存: {pt_weights_path}")
        del _init_model

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────
    # Step 1: 转换模型代码
    # ──────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("[Step 1/5] 转换 PyTorch 模型代码 → TensorFlow ...")
    from pytorch2tensorflow.converter import ModelConverter

    converter = ModelConverter(channels_first=channels_first)
    tf_model_path = OUTPUT_DIR / "model_tf.py"
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
            "class UNet", "class DoubleConv", "class Down", "class Up",
            "tf.pad(", "tf.concat(", "def call", "data_format",
        ]):
            print(f"  | {line.rstrip()}")

    # ──────────────────────────────────────────
    # Step 2: 加载 PyTorch 模型
    # ──────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("[Step 2/5] 加载 PyTorch 模型 & 权重 ...")
    import torch

    sys.path.insert(0, str(PT_MODEL_DIR))
    from model import UNet as PyTorchModel

    pt_model = PyTorchModel(in_channels=in_channels, num_classes=num_classes, base_features=base_features)
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

    # 使用自动转换的代码加载 TF 模型
    spec = importlib.util.spec_from_file_location("tf_model", str(tf_model_path))
    tf_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tf_mod)

    # 找到主模型类 (最后一个 tf.keras.Model 子类)
    tree = ast.parse(converted_code)
    tf_cls_names = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    tf_cls = None
    for cname in reversed(tf_cls_names):
        obj = getattr(tf_mod, cname, None)
        if obj and isinstance(obj, type) and issubclass(obj, tf.keras.Model):
            tf_cls = obj
            break

    tf_model = tf_cls(in_channels=in_channels, num_classes=num_classes, base_features=base_features)

    # 构建模型
    c, h, w = input_shape
    if channels_first:
        dummy = tf.zeros((batch_size, c, h, w))   # NCHW
    else:
        dummy = tf.zeros((batch_size, h, w, c))   # NHWC
    tf_model(dummy, training=False)

    tf_param_count = sum(np.prod(v.shape) for v in tf_model.weights)
    print(f"  TF 参数量: {int(tf_param_count):,}")

    # 权重转换
    from pytorch2tensorflow.weight_converter import WeightConverter
    weight_converter = WeightConverter(strict=False)

    tf_weights_path = str(OUTPUT_DIR / "weights.weights.h5")
    stats = weight_converter.convert(
        str(pt_weights_path), tf_model,
        output_path=tf_weights_path,
    )
    print(f"  权重映射: {stats['assigned']}/{stats['total_pytorch_weights']} 成功")
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
        input_np = np.random.randn(batch_size, c, h, w).astype(np.float32)

        # PyTorch 前向推理 (NCHW)
        with torch.no_grad():
            pt_out = pt_model(torch.from_numpy(input_np)).numpy()

        # TF 前向推理
        if channels_first:
            tf_out = tf_model(tf.constant(input_np), training=False).numpy()
            tf_out_nchw = tf_out
        else:
            input_nhwc = np.transpose(input_np, (0, 2, 3, 1))
            tf_out = tf_model(tf.constant(input_nhwc), training=False).numpy()
            tf_out_nchw = np.transpose(tf_out, (0, 3, 1, 2))

        # 计算指标
        abs_diff = np.abs(pt_out - tf_out_nchw)
        max_abs = float(np.max(abs_diff))
        mean_abs = float(np.mean(abs_diff))

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
        str(OUTPUT_DIR),
        [input_shape],
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
    print(f"\n{'=' * 70}")
    print("  转换完成! 输出文件汇总:")
    print(f"{'=' * 70}")
    print(f"  demo/output/")
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
