# TensorFlow MoE 路由模型（ATC 友好版）

本工具实现了一个轻量 MoE 路由网络：
- 多个接口一致的 expert 基础模型；
- 一个 router 网络预测每个 expert 的概率；
- 通过 `tf.cond` 自动在 **1 个 expert** 和 **2 个 expert 融合**之间切换；
- 导出 frozen `.pb`，用于 Ascend CANN `atc` 编译为 `.om`。

## 目录
- `build_moe_pb.py`：构图并导出 pb
- `atc_compile_example.sh`：ATC 编译示例

## 1) 导出 PB

```bash
python tools/moe_export/build_moe_pb.py \
  --output_pb artifacts/moe_router.pb \
  --input_dim 32 \
  --hidden_dim 64 \
  --num_classes 8 \
  --num_experts 3 \
  --confidence_threshold 0.75
```

输出节点：
- `output_probs`：最终分类概率
- `selected_expert_count_output`：本次路由选择了 1 还是 2 个 expert
- `top1_id` / `top2_id` / `top1_prob` / `router_probs`：调试和可观测信息

## 2) 使用 ATC 编译为 OM

```bash
bash tools/moe_export/atc_compile_example.sh artifacts/moe_router.pb Ascend310P3
```

## ATC 兼容性优化点

1. **固定输入 shape**：采用 `input_features:1,32`，避免动态 batch 在 ATC 上带来的不确定性。
2. **图静态化**：使用 `convert_variables_to_constants` 将变量冻结为常量。
3. **仅使用基础算子**：MatMul/Add/Relu/Softmax/TopKV2/Gather/ReduceSum/`tf.cond`，减少不支持算子风险。
4. **避免控制流嵌套复杂度**：仅一层 `tf.cond` 用于 1~2 expert 路由。
5. **单输入单图部署**：router + experts 在同一图中，避免多模型串并联编排开销。

## 常见问题

- **ATC 报动态 shape 错误**：确认 `--input_shape` 与 pb 中 placeholder 名字、维度一致。
- **ATC 报不支持算子**：优先升级 CANN；或将脚本中相关算子替换为更基础实现。
- **推理性能不达标**：降低 `num_experts`/`hidden_dim`，或提高 `confidence_threshold` 让更多样本走单 expert。
