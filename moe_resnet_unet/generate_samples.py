# ==============================================================================
# 生成验证用样本图像
#
# 为每个路由类别生成 2 张样本图像及对应掩码，保存为 PNG 和 npy 格式。
#   - class0_skip:    低噪声空白图像（路由到跳过）
#   - class1_simple:  单个简单形状（路由到轻量 UNet）
#   - class2_complex: 多个叠加形状+噪声（路由到重量 UNet）
# ==============================================================================

import os
import numpy as np

from config import MODEL_CONFIG
from train_export import generate_synthetic_batch


def save_as_png(array_chw, path):
    """
    将 [C, H, W] float32 数组保存为 PNG 图像。

    使用纯 numpy 生成 BMP 格式（无第三方依赖），
    若 Pillow 可用则使用 PIL 保存 PNG。
    """
    # [C, H, W] -> [H, W, C]
    img = np.transpose(array_chw, (1, 2, 0))
    img = np.clip(img * 255, 0, 255).astype(np.uint8)

    # 单通道 -> 灰度
    if img.shape[2] == 1:
        img = img[:, :, 0]

    try:
        from PIL import Image
        if img.ndim == 2:
            pil_img = Image.fromarray(img, mode='L')
        else:
            pil_img = Image.fromarray(img, mode='RGB')
        pil_img.save(path)
    except ImportError:
        # 无 Pillow 时保存为 npy（已在外部保存，此处跳过）
        print(f"  [注意] Pillow 未安装，跳过 PNG: {path}")


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "sample_data")
    os.makedirs(output_dir, exist_ok=True)

    num_per_class = 2
    total = num_per_class * MODEL_CONFIG['num_classes']

    # 固定随机种子保证可复现
    np.random.seed(42)

    # 生成足够多的样本，按类别分拣
    class_samples = {0: [], 1: [], 2: []}
    max_attempts = 50
    attempt = 0
    while any(len(v) < num_per_class for v in class_samples.values()):
        attempt += 1
        if attempt > max_attempts:
            break
        images, masks, labels = generate_synthetic_batch(
            total, MODEL_CONFIG)
        for i in range(total):
            cls = int(labels[i])
            if len(class_samples[cls]) < num_per_class:
                class_samples[cls].append((images[i], masks[i]))

    # 类别名称映射
    class_names = {0: "class0_skip", 1: "class1_simple", 2: "class2_complex"}

    print(f"保存验证样本到 {output_dir}/")
    for cls, name_prefix in class_names.items():
        samples = class_samples[cls]
        for idx, (img, mask) in enumerate(samples):
            # 保存 PNG
            img_path = os.path.join(output_dir, f"{name_prefix}_{idx}.png")
            mask_path = os.path.join(output_dir, f"{name_prefix}_mask_{idx}.png")
            save_as_png(img, img_path)
            save_as_png(mask, mask_path)

            # 保存 npy（精确数值，可用于推理验证）
            npy_img_path = os.path.join(output_dir, f"{name_prefix}_{idx}.npy")
            npy_mask_path = os.path.join(output_dir, f"{name_prefix}_mask_{idx}.npy")
            np.save(npy_img_path, img)
            np.save(npy_mask_path, mask)

            print(f"  {name_prefix}_{idx}: img={img.shape} mask={mask.shape}")

    print(f"\n完成! 共生成 {sum(len(v) for v in class_samples.values())} 组样本。")


if __name__ == "__main__":
    main()
