#!/usr/bin/env python3
"""
生成 PyTorch UNet 模型权重

用法:
    python demo/pytorch_model/generate_weights.py

输出:
    demo/pytorch_model/unet_weights.pth
"""

import sys
from pathlib import Path

import torch

# 导入模型
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))
from model import UNet

# 固定随机种子，保证权重可复现
torch.manual_seed(42)

model = UNet(in_channels=3, num_classes=2, base_features=32)
model.eval()

# 保存权重
output_path = script_dir / "unet_weights.pth"
torch.save(model.state_dict(), str(output_path))

# 验证
param_count = sum(p.numel() for p in model.parameters())
x = torch.randn(1, 3, 128, 128)
with torch.no_grad():
    y = model(x)

print(f"模型参数量: {param_count:,}")
print(f"输入形状:   {tuple(x.shape)} (NCHW)")
print(f"输出形状:   {tuple(y.shape)} (NCHW)")
print(f"权重文件:   {output_path} ({output_path.stat().st_size / 1024:.0f} KB)")
