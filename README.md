# PyTorch to TensorFlow Converter

一个强大的 PyTorch → TensorFlow 模型转换工具，专为昇腾（Ascend）平台部署设计。

## 核心功能

| 功能 | 说明 |
|------|------|
| **模型代码转换** | 将 PyTorch `nn.Module` 模型文件自动转换为 TensorFlow/Keras `tf.keras.Model` |
| **权重转换** | 将 `.pth` 权重文件转换为 TensorFlow 兼容格式（含形状转置、命名映射） |
| **精度校验** | 对比 PyTorch 与 TensorFlow 模型的输出一致性（余弦相似度、绝对/相对误差） |
| **PB 模型导出** | 导出 SavedModel / Frozen Graph (.pb)，兼容昇腾 ATC 工具链 |

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
python -m pytorch2tensorflow convert-model model.py -o model_tf.py
```

```python
from pytorch2tensorflow import ModelConverter

converter = ModelConverter()
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
```

```python
from pytorch2tensorflow import AccuracyValidator

validator = AccuracyValidator(atol=1e-5, cosine_threshold=0.9999)
result = validator.validate(pt_model, tf_model, input_shapes=[(3, 224, 224)])
print(result)
# Validation PASSED
#   Max Absolute Diff : 1.23e-06
#   Cosine Similarity : 0.999998
```

### 4. 导出 PB 模型（昇腾部署）

```bash
python -m pytorch2tensorflow export \
    --tf-model model_tf.py --tf-weights weights/ \
    --input-shape 3,224,224 -o export/ \
    --soc-version Ascend310
```

```python
from pytorch2tensorflow import PBExporter

exporter = PBExporter()
results = exporter.export_and_verify(
    tf_model,
    output_dir="export/",
    input_shapes=[(3, 224, 224)],
    soc_version="Ascend310",
)
# 自动生成 ATC 转换命令
print(results["atc_command"])
```

### 5. 一键完整流水线

```bash
python -m pytorch2tensorflow full \
    --pt-model model.py --pt-weights ckpt.pth \
    --input-shape 3,224,224 -o output/ \
    --soc-version Ascend310
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

## 昇腾平台部署流程

```
PyTorch Model (.py + .pth)
    │
    ▼ pytorch2tensorflow
TensorFlow Model (.py + weights)
    │
    ▼ PBExporter
Frozen Graph (.pb)
    │
    ▼ ATC Tool (自动生成命令)
OM Model (.om)
    │
    ▼
Ascend 310/910 部署
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
└── examples/
    ├── run_conversion.py         # 完整流水线 Demo（转换+权重+校验+导出）
    ├── example_resnet_block.py   # ResNet 转换示例
    ├── demo_multi_models.py      # 多模型快速转换 Demo
    ├── unet_model.py             # UNet PyTorch 模型定义
    ├── validate_models.py        # 7 种架构端到端精度验证
    └── verify_unet_conversion.py # UNet 完整流水线验证
```

## 已验证模型架构

转换器已通过以下 7 种架构的端到端验证（代码转换 + 模型构建 + 输出形状对比）：

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
python -m pytorch2tensorflow.examples.validate_models
```

## 注意事项

- 模型代码转换基于正则表达式匹配，对于高度动态的控制流可能需要手动调整
- 数据格式从 NCHW（PyTorch 默认）转换为 NHWC（TensorFlow 默认）
- 权重转换自动处理形状转置（卷积核、全连接层等）
- 导出 PB 模型前建议先运行精度校验
- 生成的 ATC 命令需要在安装了昇腾 CANN 工具包的环境中执行
