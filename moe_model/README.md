# MoE 路由模型 — TensorFlow Frozen PB → Ascend ATC om

基于 **Mixture of Experts（MoE）** 门控路由机制，根据输入特征自动选择
1~2 个最合适的专家模型参与推理，最终导出 **frozen .pb** 文件并通过
Ascend CANN **ATC** 工具编译成 **om** 离线模型，在昇腾计算平台部署。

---

## 架构设计

```
输入 [B, D]
    │
    ├──► 门控网络（轻量 MLP + Softmax）──► routing_probs [B, N_experts]
    │                                          │
    │                                    Top-K 选择（K=1 or 2）
    │                                          │
    │                              sparse_weights [B, N_experts]
    │                              （仅 Top-K 位置非零）
    │
    ├──► Expert 0（MLP v0）──► out_0 [B, D_out]
    ├──► Expert 1（MLP v1，残差）──► out_1 [B, D_out]
    ├──► Expert 2（MLP v2，双隐层）──► out_2 [B, D_out]
    └──► Expert 3（MLP v3，宽浅）──► out_3 [B, D_out]
              │
         Stack → [N_experts, B, D_out]
              │
         稀疏加权求和（只有 Top-K 专家有非零权重）
              │
         输出 [B, D_out]
```

### 为什么使用静态稀疏路由

| 方案 | 优点 | 缺点 |
|------|------|------|
| 动态控制流（`tf.cond`）| 仅计算选中专家 | ATC 不支持动态分支 |
| **静态稀疏掩码（本方案）** | ATC 完全兼容，算子均为标准 TF op | 所有专家参与前向，用权重为 0 抑制未选专家 |

> 静态图中 Top-K 外的专家权重强制为 0，其输出不影响最终结果，
> 等效实现"只选 K 个专家"的稀疏路由语义，且对 ATC/om 完全兼容。

---

## 文件说明

| 文件 | 用途 |
|------|------|
| `config.py` | 模型超参数、训练参数、输出节点名 |
| `model.py` | MoE 静态图定义（门控网络 + 4 种专家 + 路由组合） |
| `train_export.py` | 训练（含负载均衡损失）+ 冻结图导出 |
| `verify_pb.py` | 加载 pb 验证推理正确性，输出 ATC 命令参考 |
| `output/moe_model.pb` | 导出的 frozen pb 文件 |

---

## 快速开始

### 1. 安装依赖

```bash
pip install tensorflow>=2.10.0,<2.16.0 numpy
```

### 2. 训练并导出 pb

```bash
cd moe_model
python train_export.py
# 输出：output/moe_model.pb
```

### 3. 验证 pb 模型

```bash
python verify_pb.py
```

### 4. ATC 编译为 om（在昇腾环境执行）

```bash
atc \
  --model=output/moe_model.pb \
  --framework=3 \
  --output=output/moe_model \
  --input_shape="input_tensor:1,128" \
  --input_format=ND \
  --output_type=FP32 \
  --out_nodes="moe/output;moe/routing_indices;moe/routing_weights" \
  --log=info \
  --soc_version=Ascend310
```

> 根据实际硬件将 `Ascend310` 替换为 `Ascend910`、`Ascend310B` 等。

---

## 关键配置说明（config.py）

```python
MODEL_CONFIG = {
    'input_dim':        128,   # 输入特征维度（与业务模型对齐）
    'output_dim':       64,    # 输出维度（所有专家接口统一）
    'num_experts':      4,     # 专家数量
    'top_k':            2,     # 每次激活的专家数（1 或 2）
    'gate_hidden_dim':  64,    # 门控网络隐层（轻量）
    'expert_hidden_dim':256,   # 专家网络隐层
    'infer_batch_size': 1,     # ATC 编译固定 batch_size
}
```

---

## 冻结图节点信息

| 节点名 | shape | 说明 |
|--------|-------|------|
| `input_tensor` | `[B, 128]` float32 | ATC `--input_shape` 指定 |
| `moe/output` | `[B, 64]` float32 | 加权融合输出 |
| `moe/routing_indices` | `[B, top_k]` int32 | 选中专家索引 |
| `moe/routing_weights` | `[B, top_k]` float32 | 选中专家归一化权重 |

---

## 图中使用的算子类型（均为 ATC 支持算子）

`AddV2` · `Const` · `ExpandDims` · `Identity` · `MatMul` · `Maximum`
· `Mul` · `OneHot` · `Pack` · `Placeholder` · `RealDiv` · `Relu`
· `Softmax` · `Sum` · `TopKV2` · `Transpose` · `Unpack`

---

## 替换为真实专家模型

`model.py` 中的 `_build_expert_v*` 函数为演示用 MLP，可替换为任何
满足以下条件的 TF1 静态图实现：

- **输入**：`[batch, input_dim]` float32
- **输出**：`[batch, output_dim]` float32
- **无动态控制流**（无 `tf.cond`、`tf.while_loop`）
- **无 Python 级动态 shape 操作**
