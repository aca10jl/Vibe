# MoE 门控路由模型 V2

基于 TensorFlow 静态图实现的 Mixture-of-Experts 路由模型。使用 `tf.cond` 实现真正的条件分支执行（Switch/Merge），仅激活 1~2 个被选中的专家。支持从 PyTorch 转换专家模型并注册到路由器。

## 架构设计

```
输入特征 [1, 128]
    │
    ▼
┌──────────────────┐
│  门控网络 (Gate)  │  MLP: 128 → 64 → N (softmax)
└──────┬───────────┘
       │ 路由概率 [1, N]
       ▼
┌──────────────────┐
│  Top-K 选择      │  top_k=1: 始终单专家
│                  │  top_k=2: 置信度 ≥ 0.7 → 单专家，否则双专家
└──────┬───────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  tf.cond 条件执行 (Switch/Merge)        │
│                                         │
│  专家0 (自定义/默认) ── 选中? → 计算    │
│  专家1 (自定义/默认) ── 选中? → 计算    │
│  专家N ...            ── 未选中 → 跳过  │
└─────────────────────────────────────────┘
       │
       ▼
  加权融合输出 [1, 128]
```

## 核心特性

- **Top-K=1 和 Top-K=2 完整支持**
- **用户可注册自定义专家**（从 PyTorch 转换或自定义 builder）
- **PyTorch → TensorFlow 权重转换**（支持 Conv2d/BN/Linear 等层）
- **图像检测模型适配**（双输入 UINT8 [1,1,448,448] → UINT8 heatmap）
- **ATC 全兼容**（Switch/Merge 控制流 + 标准算子）

## 文件结构

```
moe_routing/
├── config.py            # 配置（门控维度、专家数、top_k 等）
├── model.py             # MoE 模型 + ExpertRegistry
├── train_export.py      # 训练 + frozen pb 导出
├── verify_pb.py         # pb 验证 + ATC 兼容性检查
├── pytorch_to_tf.py     # PyTorch → TF 转换器
├── requirements.txt
└── output/
    └── moe_routing_model.pb
```

## 快速使用

### 1. 使用默认专家

```bash
python train_export.py     # 训练 + 导出 pb
python verify_pb.py        # 验证 pb
```

### 2. 注册 PyTorch 转换的自定义专家

```python
from model import ExpertRegistry, set_registry
from pytorch_to_tf import create_expert_builder_from_pytorch
from train_export import train, export_inference_pb
from config import MODEL_CONFIG, TRAIN_CONFIG, OUTPUT_CONFIG

# 转换 PyTorch 模型
builder, converter = create_expert_builder_from_pytorch(
    "my_detection_model.pth",
    "output/converted_weights"
)

# 注册到路由器
registry = ExpertRegistry(MODEL_CONFIG['num_experts'])
registry.register(0, builder)  # 专家 0 使用自定义模型
# 专家 1~3 使用默认 MLP
set_registry(registry)

# 训练 + 导出
trained = train(MODEL_CONFIG, TRAIN_CONFIG, registry)
export_inference_pb(trained, MODEL_CONFIG, OUTPUT_CONFIG, registry)
```

### 3. 切换 Top-K 模式

```python
# config.py 中修改
MODEL_CONFIG['top_k'] = 1   # 始终只用 1 个专家
MODEL_CONFIG['top_k'] = 2   # 最多用 2 个专家（默认）
```

## PyTorch 模型要求

支持的模型输入输出规格：
- **输入**: 2 个 NCHW [1,1,448,448] UINT8 图像（待检测图 + 参考图）
- **输出**: 1 个 NCHW [1,1,448,448] UINT8 热力图

支持的层类型：
- `nn.Conv2d`, `nn.ConvTranspose2d`
- `nn.BatchNorm2d`
- `nn.Linear`
- `nn.ReLU`, `nn.Sigmoid`, `nn.Tanh`

## ATC 编译

```bash
atc \
  --model=output/moe_routing_model.pb \
  --framework=3 \
  --output=output/moe_routing_model \
  --input_shape="input_features:1,128" \
  --input_format=ND \
  --output_type=FP32 \
  --out_nodes="moe/output;moe/routing_indices;moe/routing_weights" \
  --log=info \
  --soc_version=Ascend310
```
