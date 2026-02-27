# PyTorch MoE 门控路由示例（业务场景版）

该示例用于“多个接口一致、能力相近模型”的自动路由：

- `top_k=1`：路由到 **1 个最适合专家**（硬路由）
- `top_k=2`：路由到 **2 个专家并加权融合**（软路由）

## 模型设计

### 1) 基础专家模型（接口统一）

输入输出接口统一为 `Tensor[B, input_dim] -> Tensor[B, output_dim]`：

- `MLPExpert`：轻量全连接模型，适合规则性场景
- `ResidualExpert`：带残差，适合中复杂场景
- `DeepExpert`：更深非线性结构，适合复杂场景

### 2) MoE 门控路由

`MoERouter` 由 `gate + experts` 组成：

1. gate 输出每个专家的概率 `gate_probs`
2. 取 top-k 专家（k=1 或 2）
3. 仅对 top-k 权重做归一化
4. 按路由结果仅执行被选中的 1~2 个专家（稀疏推理）
5. 按权重融合专家输出，得到最终预测

同时输出：

- `prediction`：融合后的预测
- `selected_experts`：每条样本选中的专家索引
- `expert_weights`：top-k 归一化权重
- `gate_probs`：全量门控概率（便于监控与可解释性）

### 3) 训练增强（可选）

提供 `load_balance_loss`（负载均衡损失）示例，防止路由流量长期偏向单个专家。

> 与“所有 expert 全量推理再挑选”不同，本实现采用稀疏分发：每个样本只会触发 top-k 对应专家计算。

## ONNX 导出

可导出为 ONNX（含动态 batch）：

- `artifacts/moe_router_top1.onnx`
- `artifacts/moe_router_top2.onnx`

导出输出节点：

- `prediction`
- `selected_experts`
- `expert_weights`
- `gate_probs`

## 运行

```bash
python moe_routing_onnx.py
```

## 业务接入建议

- 输入特征应包含场景信息：任务类型、用户分层、时段、端侧约束（延迟/成本）等。
- 可以采用两阶段训练：先冻结专家只训练 gate，再做联合微调。
- 线上建议监控：
  - 各专家路由占比
  - 各专家下游指标（准确率、点击率、转化、时延）
  - 负载均衡损失走势（是否出现路由塌缩）
