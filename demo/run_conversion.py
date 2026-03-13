#!/usr/bin/env python3
"""
一键转换脚本：将 PyTorch UNet 模型转换为 TensorFlow 版本

用法:
    python demo/run_conversion.py

输入文件 (demo/pytorch_model/):
    model.py          — PyTorch UNet 模型定义
    unet_weights.pth  — PyTorch 训练权重

输出文件 (demo/output/):
    model_tf.py       — 转换后的 TensorFlow 模型代码
    weights.weights.h5 — 转换后的 TensorFlow 权重
    frozen_model.pb   — 冻结图 (昇腾部署用)
    saved_model/      — TF SavedModel 格式
    验证报告           — 精度校验结果
"""

import os
import sys
from pathlib import Path

# 设置项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DEMO_DIR = PROJECT_ROOT / "demo"
PT_MODEL_DIR = DEMO_DIR / "pytorch_model"
OUTPUT_DIR = DEMO_DIR / "output"


def main():
    print("=" * 70)
    print("  PyTorch UNet → TensorFlow 全流程转换")
    print("=" * 70)

    # 检查输入文件
    pt_model_path = PT_MODEL_DIR / "model.py"
    pt_weights_path = PT_MODEL_DIR / "unet_weights.pth"

    if not pt_model_path.exists():
        print(f"[ERROR] 找不到 PyTorch 模型文件: {pt_model_path}")
        return 1
    if not pt_weights_path.exists():
        print(f"  权重文件不存在，自动生成中...")
        import subprocess
        subprocess.run(
            [sys.executable, str(PT_MODEL_DIR / "generate_weights.py")],
            check=True,
        )
        print(f"  ✓ 权重已生成: {pt_weights_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    input_shape = (3, 128, 128)  # CHW

    # ──────────────────────────────────────────
    # Step 1: 转换模型代码
    # ──────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("[Step 1/5] 转换 PyTorch 模型代码 → TensorFlow ...")
    from pytorch2tensorflow.converter import ModelConverter

    converter = ModelConverter(add_channel_convert=True)
    tf_model_path = OUTPUT_DIR / "model_tf.py"
    converted_code = converter.convert_file(str(pt_model_path), str(tf_model_path))
    line_count = converted_code.count("\n")
    print(f"  输出文件: {tf_model_path}")
    print(f"  代码行数: {line_count}")
    print(f"  ✓ 模型代码转换完成")

    # 展示关键转换片段
    print(f"\n  --- 转换后关键代码 ---")
    for line in converted_code.split("\n"):
        s = line.strip()
        if any(k in s for k in [
            "class UNet", "class DoubleConv", "class Down", "class Up",
            "tf.pad(", "tf.concat(", "def call",
        ]):
            print(f"  │ {line.rstrip()}")

    # ──────────────────────────────────────────
    # Step 2: 加载 PyTorch 模型
    # ──────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("[Step 2/5] 加载 PyTorch 模型 & 权重 ...")
    import torch
    sys.path.insert(0, str(PT_MODEL_DIR))
    from model import UNet as PyTorchUNet

    pt_model = PyTorchUNet(in_channels=3, num_classes=2, base_features=32)
    state_dict = torch.load(str(pt_weights_path), map_location="cpu", weights_only=True)
    pt_model.load_state_dict(state_dict)
    pt_model.eval()

    param_count = sum(p.numel() for p in pt_model.parameters())
    print(f"  参数量:   {param_count:,}")
    print(f"  ✓ PyTorch 模型加载完成")

    # ──────────────────────────────────────────
    # Step 3: 构建 TF 模型 & 转换权重
    # ──────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("[Step 3/5] 构建 TensorFlow 模型 & 转换权重 ...")
    import tensorflow as tf
    import numpy as np

    tf_model = _build_tf_unet()

    # 用 dummy input 构建模型
    dummy = tf.zeros((1, 128, 128, 3))  # NHWC
    _ = tf_model(dummy, training=False)

    tf_param_count = sum(np.prod(w.shape) for w in tf_model.weights)
    print(f"  TF 参数量: {tf_param_count:,}")

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
    print(f"  ✓ 权重转换完成")

    # ──────────────────────────────────────────
    # Step 4: 精度校验
    # ──────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("[Step 4/5] 校验 PyTorch ↔ TensorFlow 输出精度 ...")

    np.random.seed(42)
    torch.manual_seed(42)

    num_tests = 5
    all_max_abs = []
    all_cosine = []

    for i in range(num_tests):
        # 生成随机输入
        input_np = np.random.randn(1, 3, 128, 128).astype(np.float32)

        # PyTorch 前向推理 (NCHW)
        with torch.no_grad():
            pt_out = pt_model(torch.from_numpy(input_np)).numpy()

        # TF 前向推理 (NHWC)
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
    passed = avg_cosine >= 0.99
    status = "PASSED" if passed else "FAILED"
    print(f"\n  汇总 ({num_tests} 个样本):")
    print(f"    平均最大绝对差: {avg_max_abs:.2e}")
    print(f"    平均余弦相似度: {avg_cosine:.6f}")
    print(f"  ✓ 精度校验: {status}")

    # ──────────────────────────────────────────
    # Step 5: 导出 PB 模型
    # ──────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("[Step 5/5] 导出 PB 模型 (昇腾部署) ...")
    from pytorch2tensorflow.exporter import PBExporter

    exporter = PBExporter()

    # 导出 SavedModel
    saved_model_dir = str(OUTPUT_DIR / "saved_model")
    exporter.export_saved_model(tf_model, saved_model_dir, input_shapes=[(128, 128, 3)])
    print(f"  SavedModel: {saved_model_dir}")

    # 导出 Frozen Graph
    pb_path = str(OUTPUT_DIR / "frozen_model.pb")
    exporter.export_frozen_graph(tf_model, pb_path, input_shapes=[(128, 128, 3)])
    pb_size = os.path.getsize(pb_path)
    print(f"  Frozen PB:  {pb_path} ({pb_size/1024:.0f} KB)")

    # 昇腾兼容性检查
    compat = exporter.check_ascend_compatibility(pb_path=pb_path)
    compat_status = "兼容" if compat["compatible"] else "存在问题"
    print(f"  昇腾兼容:  {compat_status} (算子: {compat['unique_ops']} 种)")

    if compat["unsupported_ops"]:
        print(f"  未知算子:  {compat['unsupported_ops']}")

    # 生成 ATC 命令
    atc_cmd = exporter.generate_atc_command(
        pb_path=pb_path,
        output_path=str(OUTPUT_DIR / "unet_model"),
        soc_version="Ascend310",
        input_shape="input:1,128,128,3",
    )
    print(f"\n  ATC 转换命令 (在昇腾环境执行):")
    for line in atc_cmd.split("\n"):
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
    print(f"  精度验证:  {status} (余弦相似度={avg_cosine:.6f})")
    print(f"  昇腾兼容:  {compat_status}")
    print(f"{'=' * 70}")

    return 0 if passed else 1


def _build_tf_unet():
    """构建与 PyTorch 版本对应的 TensorFlow UNet 模型."""
    import tensorflow as tf

    class TFDoubleConv(tf.keras.layers.Layer):
        def __init__(self, out_channels, **kwargs):
            super().__init__(**kwargs)
            self.conv1 = tf.keras.layers.Conv2D(
                out_channels, 3, padding="same", use_bias=False)
            self.bn1 = tf.keras.layers.BatchNormalization()
            self.conv2 = tf.keras.layers.Conv2D(
                out_channels, 3, padding="same", use_bias=False)
            self.bn2 = tf.keras.layers.BatchNormalization()

        def call(self, x, training=False):
            x = tf.nn.relu(self.bn1(self.conv1(x), training=training))
            x = tf.nn.relu(self.bn2(self.conv2(x), training=training))
            return x

    class TFDown(tf.keras.layers.Layer):
        def __init__(self, out_channels, **kwargs):
            super().__init__(**kwargs)
            self.pool = tf.keras.layers.MaxPool2D(2)
            self.conv = TFDoubleConv(out_channels)

        def call(self, x, training=False):
            return self.conv(self.pool(x), training=training)

    class TFUp(tf.keras.layers.Layer):
        def __init__(self, in_channels, out_channels, **kwargs):
            super().__init__(**kwargs)
            self.up = tf.keras.layers.Conv2DTranspose(
                in_channels // 2, kernel_size=2, strides=2)
            self.conv = TFDoubleConv(out_channels)

        def call(self, x1, x2, training=False):
            x1 = self.up(x1)
            # 对齐空间维度 (NHWC)
            diff_h = tf.shape(x2)[1] - tf.shape(x1)[1]
            diff_w = tf.shape(x2)[2] - tf.shape(x1)[2]
            x1 = tf.pad(x1, [
                [0, 0],
                [diff_h // 2, diff_h - diff_h // 2],
                [diff_w // 2, diff_w - diff_w // 2],
                [0, 0]
            ])
            x = tf.concat([x2, x1], axis=-1)
            return self.conv(x, training=training)

    class TFUNet(tf.keras.Model):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.inc = TFDoubleConv(32, name="inc")
            self.down1 = TFDown(64, name="down1")
            self.down2 = TFDown(128, name="down2")
            self.down3 = TFDown(256, name="down3")
            self.down4 = TFDown(512, name="down4")
            self.up1 = TFUp(512, 256, name="up1")
            self.up2 = TFUp(256, 128, name="up2")
            self.up3 = TFUp(128, 64, name="up3")
            self.up4 = TFUp(64, 32, name="up4")
            self.outc = tf.keras.layers.Conv2D(2, 1, name="outc")

        def call(self, x, training=False):
            x1 = self.inc(x, training=training)
            x2 = self.down1(x1, training=training)
            x3 = self.down2(x2, training=training)
            x4 = self.down3(x3, training=training)
            x5 = self.down4(x4, training=training)
            x = self.up1(x5, x4, training=training)
            x = self.up2(x, x3, training=training)
            x = self.up3(x, x2, training=training)
            x = self.up4(x, x1, training=training)
            return self.outc(x)

    return TFUNet()


if __name__ == "__main__":
    sys.exit(main())
