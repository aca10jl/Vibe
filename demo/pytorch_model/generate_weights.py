#!/usr/bin/env python3
"""
生成 PyTorch UNet 模型权重

用法:
    python demo/pytorch_model/generate_weights.py
    python demo/pytorch_model/generate_weights.py --out weights.pth

输出:
    demo/pytorch_model/unet_weights.pth (默认)
"""

import argparse
import sys
from pathlib import Path

import torch

# ──────────────────────────────────────────
# 核心参数 (与 run_conversion.py 保持一致)
# ──────────────────────────────────────────
IN_CHANNELS = 3           # 输入通道数
NUM_CLASSES = 2           # 输出类别数
BASE_FEATURES = 32        # 基础特征图通道数
INPUT_SHAPE = (IN_CHANNELS, 128, 128)  # CHW 格式
RANDOM_SEED = 42          # 随机种子 (可复现)

# 导入模型
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))
from model import UNet


def main():
    parser = argparse.ArgumentParser(description="生成 PyTorch UNet 模型权重")
    parser.add_argument(
        "--out", default=str(script_dir / "unet_weights.pth"),
        help="输出权重文件路径 (默认: demo/pytorch_model/unet_weights.pth)",
    )
    args = parser.parse_args()
    output_path = Path(args.out)

    # 固定随机种子，保证权重可复现
    torch.manual_seed(RANDOM_SEED)

    model = UNet(in_channels=IN_CHANNELS, num_classes=NUM_CLASSES, base_features=BASE_FEATURES)
    model.eval()

    # 保存权重
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), str(output_path))

    # 验证
    param_count = sum(p.numel() for p in model.parameters())
    c, h, w = INPUT_SHAPE
    x = torch.randn(1, c, h, w)
    with torch.no_grad():
        y = model(x)

    print(f"模型参数量: {param_count:,}")
    print(f"输入形状:   {tuple(x.shape)} (NCHW)")
    print(f"输出形状:   {tuple(y.shape)} (NCHW)")
    print(f"权重文件:   {output_path} ({output_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
