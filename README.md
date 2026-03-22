# PyTorch to TensorFlow Converter

一个强大的 PyTorch → TensorFlow 模型转换工具，专为昇腾（Ascend）平台部署设计。

## 核心功能

| 功能 | 说明 |
|------|------|
| **模型代码转换** | 将 PyTorch `nn.Module` 模型文件自动转换为 TensorFlow/Keras `tf.keras.Model` |
| **权重转换** | 将 `.pth` 权重文件转换为 TensorFlow 兼容格式（含形状转置、命名映射） |
| **精度校验** | 对比 PyTorch 与 TensorFlow 模型的输出一致性（余弦相似度、绝对/相对误差） |
| **PB 模型导出** | 导出 SavedModel / Frozen Graph (.pb)，兼容昇腾 ATC 工具链 |
| **channels_first 模式** | 支持保持 NCHW 格式（`--channels-first`），全链路兼容 |

## 安装

```bash
pip install -e ".[full]"
```

或分别安装：

```bash
pip install -e ".[pytorch]"    # 仅 PyTorch 依赖
pip install -e ".[tensorflow]" # 仅 TensorFlow 依赖
```

## 快速使用

### 1. 转换模型代码

```bash
# 默认 NHWC 格式 (TensorFlow 标准)
python -m pytorch2tensorflow convert-model model.py -o model_tf.py

# 保持 NCHW 格式 (匹配 PyTorch)
python -m pytorch2tensorflow convert-model model.py -o model_tf.py --channels-first
```

```python
from pytorch2tensorflow import ModelConverter

# NHWC 模式 (默认)
converter = ModelConverter()
converter.convert_file("model.py", "model_tf.py")

# NCHW 模式
converter = ModelConverter(channels_first=True)
converter.convert_file("model.py", "model_tf.py")
```

### 2. 转换权重

```bash
# 转为 numpy（无需 TF 模型）
python -m pytorch2tensorflow convert-weights ckpt.pth --numpy-only -o weights/

# 直接加载到 TF 模型
python -m pytorch2tensorflow convert-weights ckpt.pth \
    --tf-model model_tf.py --input-shape 3,224,224 -o weights/
```

```python
from pytorch2tensorflow import WeightConverter

converter = WeightConverter()
stats = converter.convert("ckpt.pth", tf_model, output_path="weights/")
print(f"成功转换: {stats['assigned']}/{stats['total_pytorch_weights']}")
```

### 3. 精度校验

```bash
python -m pytorch2tensorflow validate \
    --pt-model model.py --tf-model model_tf.py \
    --pt-weights ckpt.pth \
    --input-shape 3,224,224

# channels_first 模式校验
python -m pytorch2tensorflow validate \
    --pt-model model.py --tf-model model_tf.py \
    --pt-weights ckpt.pth \
    --input-shape 3,224,224 --channels-first
```

```python
from pytorch2tensorflow import AccuracyValidator

validator = AccuracyValidator(atol=1e-4, cosine_threshold=0.999)
result = validator.validate(
    pt_model, tf_model,
    input_shapes=[(3, 224, 224)],
    nchw_to_nhwc=True,   # channels_first 模式设为 False
)
print(result)
# Validation PASSED
#   Max Absolute Diff : 1.23e-04
#   Cosine Similarity : 0.999998
```

### 4. 导出 PB 模型（昇腾部署）

```bash
python -m pytorch2tensorflow export \
    --tf-model model_tf.py --tf-weights weights/ \
    --input-shape 3,224,224 -o export/ \
    --soc-version Ascend910B4

# channels_first 模式导出
python -m pytorch2tensorflow export \
    --tf-model model_tf.py --tf-weights weights/ \
    --input-shape 3,224,224 -o export/ \
    --soc-version Ascend910B4 --channels-first
```

```python
from pytorch2tensorflow import PBExporter

# NHWC 模式 (默认)
exporter = PBExporter()

# NCHW 模式
exporter = PBExporter(channels_first=True)

results = exporter.export_and_verify(
    tf_model,
    output_dir="export/",
    input_shapes=[(3, 224, 224)],
    soc_version="Ascend910B4",
)
# 自动生成 ATC 转换命令
print(results["atc_command"])
```

### 5. 一键完整流水线

```bash
python -m pytorch2tensorflow auto \
    --pt-model model.py --pt-weights ckpt.pth \
    --input-shape 3,224,224 -o output/ \
    --soc-version Ascend910B4

# 保持 NCHW 格式
python -m pytorch2tensorflow auto \
    --pt-model model.py --pt-weights ckpt.pth \
    --input-shape 3,224,224 -o output/ \
    --soc-version Ascend910B4 --channels-first
```

### 6. Demo 演示

```bash
# 运行 UNet 完整转换 Demo（代码转换 + 权重 + 校验 + PB 导出）
python demo/run_conversion.py

# channels_first 模式
python demo/run_conversion.py --channels-first
```

## 支持的层与操作

### 卷积层
`Conv1d` `Conv2d` `Conv3d` `ConvTranspose2d` `DepthwiseConv2D`

### 归一化层
`BatchNorm1d/2d/3d` `LayerNorm` `GroupNorm` `InstanceNorm`

### 池化层
`MaxPool2d` `AvgPool2d` `AdaptiveAvgPool2d` `GlobalAveragePooling`

### 激活函数
`ReLU` `LeakyReLU` `GELU` `SiLU/Swish` `Sigmoid` `Tanh` `Softmax` `Mish` `Hardswish`

### 线性与嵌入
`Linear/Dense` `Embedding`

### RNN
`LSTM` `GRU` `SimpleRNN`

### 张量操作
`view/reshape` `permute/transpose` `cat/concat` `split/chunk` `squeeze/unsqueeze` `flatten` `repeat/tile` `expand/broadcast_to`

### 函数操作
`F.interpolate` `F.pad` `F.softmax` `F.relu` `F.conv2d` `torch.matmul` `torch.einsum`

## 权重转换规则

| PyTorch 格式 | TensorFlow 格式 | 转置规则 |
|-------------|-----------------|---------|
| Conv2d `[O,I,H,W]` | Conv2D `[H,W,I,O]` | `(2,3,1,0)` |
| Conv1d `[O,I,L]` | Conv1D `[L,I,O]` | `(2,1,0)` |
| Linear `[O,I]` | Dense `[I,O]` | `(1,0)` |
| ConvTranspose2d `[I,O,H,W]` | Conv2DTranspose `[H,W,O,I]` | `(2,3,1,0)` |
| BatchNorm `running_mean` | BatchNorm `moving_mean` | - |
| BatchNorm `running_var` | BatchNorm `moving_variance` | - |

## channels_first 模式

默认情况下，转换器将 PyTorch 的 NCHW 格式转为 TensorFlow 标准的 NHWC 格式。使用 `--channels-first` 可保持 NCHW 格式：

| 特性 | NHWC (默认) | NCHW (--channels-first) |
|------|-------------|------------------------|
| 数据格式 | `(N, H, W, C)` | `(N, C, H, W)` |
| TF 层参数 | 默认 | 自动添加 `data_format='channels_first'` |
| BatchNorm axis | `-1` (默认) | `1` (通道维) |
| concat axis | `-1` | `1` |
| flatten 转换 | `transpose + reshape` | 直接 `reshape` |
| PB 导出格式 | NHWC | NCHW |
| ATC input_format | `NHWC` | `NCHW` |

## PB 模型导出

导出器支持：

- **SavedModel** 格式导出（含多输入子模块兼容，如 UNet 的 `Up(x1, x2)`）
- **Frozen Graph (.pb)** 导出（昇腾 ATC 工具首选格式）
- **多输出模型**支持（如 MultiHeadNet 的 tuple 输出）
- **昇腾兼容性检查**（自动扫描算子是否在 Ascend 支持列表中）
- **ATC 命令自动生成**（含正确的 input_shape 和 input_format）
- **Conv1d/Conv2d/Conv3d** 输入形状自动转换

## 昇腾平台部署流程

```
PyTorch Model (.py + .pth)
    │
    ▼ pytorch2tensorflow (支持 --channels-first)
TensorFlow Model (.py + weights)
    │
    ▼ PBExporter
Frozen Graph (.pb)
    │
    ▼ ATC Tool (自动生成命令)
OM Model (.om)
    │
    ▼
Ascend 910B4/310P 部署
```

## 项目结构

```
pytorch2tensorflow/
├── __init__.py          # 包入口
├── __main__.py          # python -m 入口
├── layer_mapping.py     # PyTorch → TF 层/操作映射表
├── converter.py         # 模型代码转换器
├── weight_converter.py  # 权重转换器
├── validator.py         # 精度校验器
├── exporter.py          # PB 导出器（昇腾兼容）
├── cli.py               # 命令行接口
├── auto_convert.py      # 一键转换流水线
└── examples/
    ├── run_conversion.py         # 完整流水线 Demo
    ├── example_resnet_block.py   # ResNet 转换示例
    ├── demo_multi_models.py      # 多模型快速转换 Demo
    ├── unet_model.py             # UNet PyTorch 模型定义
    ├── validate_models.py        # 7 种架构端到端验证 (含 PB 导出)
    └── verify_unet_conversion.py # UNet 完整流水线验证

demo/
├── run_conversion.py             # 一键转换脚本 (支持 --channels-first)
├── pytorch_model/
│   ├── model.py                  # PyTorch UNet 模型
│   ├── generate_weights.py       # 权重生成脚本
│   └── unet_weights.pth          # PyTorch 权重
└── output/                       # 转换输出
    ├── model_tf.py               # TF 模型代码
    ├── weights.weights.h5        # TF 权重
    ├── frozen_model.pb           # 冻结图
    └── saved_model/              # SavedModel 格式

tests/
└── test_ops.py           # 45 项算子级测试 (含 PB 导出验证)
```

## 已验证模型架构

转换器已通过以下 7 种架构的端到端验证（代码转换 + 权重迁移 + 精度校验 + PB 导出），NHWC 和 NCHW 双模式全部通过：

| 模型 | 类型 | 关键特性 |
|------|------|----------|
| **UNet** | 语义分割 | Skip connections, `torch.cat`, `ConvTranspose2d` |
| **SimpleResNet** | 图像分类 | 残差连接 (`+=`), `AdaptiveAvgPool2d`, `flatten` |
| **LeNet** | 经典 CNN | `MaxPool2d`, 多层 `Linear` |
| **MiniVGG** | VGG 风格 | 循环内构建 `Sequential`, `BatchNorm2d` + `ReLU` |
| **MultiHeadNet** | 多任务 | 双输出头 (分类 + 回归), `tuple` 输出 |
| **BottleneckNet** | ResNet-50 风格 | 1×1 → 3×3 → 1×1 瓶颈块, 下采样旁路 |
| **EncoderDecoder** | 编解码器 | 编码-解码结构, skip connection, `ConvTranspose2d` |

运行验证：

```bash
# NHWC 模式 (7 模型)
python -m pytorch2tensorflow.examples.validate_models

# NHWC + NCHW 双模式 (14 模型)
python -m pytorch2tensorflow.examples.validate_models --channels-first

# 算子级测试 (45 项, 含 PB 导出)
python -m tests.test_ops
```

## 默认参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--soc-version` | `Ascend910B4` | 目标昇腾 SoC 型号 |
| `--atol` | `1e-4` | 绝对误差容忍度 |
| `--rtol` | `1e-3` | 相对误差容忍度 |
| `--cosine-threshold` | `0.999` | 最低余弦相似度 |
| `--batch-size` | `1` | 导出批量大小 |

## 注意事项

- 模型代码转换基于正则表达式匹配，对于高度动态的控制流可能需要手动调整
- 默认将数据格式从 NCHW（PyTorch）转换为 NHWC（TensorFlow），可用 `--channels-first` 保持 NCHW
- 权重转换自动处理形状转置（卷积核、全连接层等）
- 导出 PB 模型前建议先运行精度校验
- 生成的 ATC 命令需要在安装了昇腾 CANN 工具包的环境中执行
- 多输入子模块（如 UNet 的 `Up(x1, x2)`）的 SavedModel 导出已做特殊处理
