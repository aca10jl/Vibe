# MoE 门控路由模型 —— 基于 tf.cond 的稀疏条件执行

基于 TensorFlow 静态图实现的 Mixture-of-Experts 路由模型，使用 `tf.cond` 实现真正的条件分支执行，仅激活 1~2 个被选中的专家，显著降低推理计算开销。导出 frozen pb 格式，可通过 Ascend CANN ATC 工具编译为 om 离线模型。

## 架构设计

```
输入 [1, 128]
    │
    ▼
┌──────────────────┐
│  门控网络 (Gate)  │  MLP: 128 → 64 → 4 (softmax)
└──────┬───────────┘
       │ 路由概率 [1, 4]
       ▼
┌──────────────────┐
│  Top-K 选择      │  置信度 ≥ 0.7 → Top-1; 否则 → Top-2
└──────┬───────────┘
       │
       ▼
┌──────────────────────────────────────────────────┐
│  tf.cond 条件执行                                │
│                                                  │
│  专家0 (MLP)        ──── Switch ──── 选中? → 计算 │
│  专家1 (残差MLP)    ──── Switch ──── 选中? → 计算 │
│  专家2 (双隐层MLP)  ──── Switch ──── 选中? → 计算 │
│  专家3 (宽浅MLP)    ──── Switch ──── 选中? → 计算 │
│                          未选中 → 零张量 (跳过)    │
└──────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────┐
│  加权融合输出      │  output [1, 64]
└──────────────────┘
```

### 核心特性

- **真正的稀疏执行**：通过 `tf.cond` 生成 `Switch/Merge` 控制流节点，运行时仅执行被选中专家的计算分支
- **动态 Top-1/Top-2 路由**：门控置信度高时只用 1 个专家，不确定时融合 2 个专家
- **ATC 全兼容**：仅使用 ATC 支持的 21 种算子（含 Switch/Merge 控制流）
- **训练/推理分离**：训练时所有专家参与（保证梯度传播），推理图使用 `tf.cond` 跳过未选中专家

## 文件结构

```
moe_routing/
├── config.py          # 模型/训练/导出配置
├── model.py           # MoE 模型定义（含 tf.cond 条件执行）
├── train_export.py    # 训练 + 冻结 pb 导出
├── verify_pb.py       # pb 模型验证 + ATC 兼容性检查
├── requirements.txt   # 依赖
└── output/
    └── moe_routing_model.pb  # 导出的 frozen pb
```

## 使用方法

```bash
# 安装依赖
pip install -r requirements.txt

# 训练并导出 pb
python train_export.py

# 验证 pb 模型
python verify_pb.py
```

## ATC 编译

```bash
atc \
  --model=output/moe_routing_model.pb \
  --framework=3 \
  --output=output/moe_routing_model \
  --input_shape="input_tensor:1,128" \
  --input_format=ND \
  --output_type=FP32 \
  --out_nodes="moe/output;moe/routing_indices;moe/routing_weights" \
  --log=info \
  --soc_version=Ascend310
```

## 模型参数

| 参数 | 值 |
|------|-----|
| 输入维度 | 128 |
| 输出维度 | 64 |
| 专家数量 | 4 |
| Top-K | 2 (动态 1~2) |
| 置信度阈值 | 0.7 |
| 门控隐层 | 64 |
| 专家隐层 | 256 |
| 推理 batch | 1 |
