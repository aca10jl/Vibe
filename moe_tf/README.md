# TensorFlow MoE 路由模型（导出 PB / 面向 Ascend ATC）

该示例实现了一个轻量级 MoE 路由结构：
- 多个结构相同的专家模型（experts）。
- 一个门控网络（gate）自动决定使用 **1 个或 2 个专家**。
- 支持 `route_override` 强制 top-1/top-2（调试与业务策略回退时有用）。
- 导出为 frozen `.pb`，可用 ATC 编译为 `.om`。

## 1. 环境

建议 Python 3.8+，TensorFlow 2.x（使用 `tf.compat.v1` 图模式）。

```bash
pip install -r requirements.txt
```

## 2. 导出 PB

```bash
python3 moe_tf/export_moe_pb.py --output_pb build/moe_router_frozen.pb
```

导出后关键输入输出：
- 输入
  - `input_features:0`，形状 `[batch, input_dim]`
  - `route_override:0`，标量 int（0=自动，1=强制top1，2=强制top2）
- 输出
  - `model_output:0`，融合后的推理结果
  - `expert_weights:0`，每个专家的最终权重
  - `top_indices:0`，门控选中的 top-2 专家索引
  - `top_values:0`，top-2 原始概率
  - `chosen_topk:0`，每个样本最终选择 1 或 2
  - `gate_probs:0`，完整门控概率分布

## 3. ATC 编译示例

```bash
atc \
  --framework=3 \
  --model=build/moe_router_frozen.pb \
  --input_shape="input_features:1,16" \
  --output="build/moe_router" \
  --soc_version=Ascend310
```

如果需要固定 batch，例如 8：

```bash
--input_shape="input_features:8,16"
```

## 4. 常见 PB/ATC 问题与规避

1. **变量未冻结导致 ATC 报错**  
   本项目使用 `convert_variables_to_constants` 固化变量，导出单一 frozen graph。

2. **输出节点名写错**  
   只使用显式 `tf.identity(name=...)` 暴露稳定节点名，避免 scope 变化带来的名称漂移。

3. **路由逻辑动态控制流过重**  
   使用张量化 `top_k + one_hot + mask` 实现，不依赖 Python 循环分支，图更稳定。

4. **全部模型都参与计算导致开销大**  
   只对 top-1/top-2 分配非零权重，未选中专家权重为 0，达到“按场景选择最合适模型”的效果。

5. **业务需要兜底策略**  
   `route_override` 可在服务端强制 top-1 或 top-2，便于灰度或异常回退。
