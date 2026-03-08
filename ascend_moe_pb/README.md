# Ascend-Friendly Split MoE PB Export

这个工程不是把门控和所有专家硬塞进一个会动态分支的 `pb`，而是采用更适合 Ascend `atc` 的拆分方案：

1. `router.pb` 只负责根据输入特征输出 `top1/top2` 专家编号、权重和选中数量。
2. `expert_*.pb` 各自负责同接口推理。
3. 部署时先执行 `router.om`，再只调度 1~2 个 `expert_*.om`。

这样做有两个直接收益：

1. 避免单图内部 `tf.cond` / `switch_case` / 动态子图带来的 `atc` 编译失败风险。
2. 真正做到只让被选中的 1~2 个专家参与推理，而不是把所有专家都算完再做加权。

## 文件说明

- `export_split_moe_pb.py`
  - 使用 `tensorflow.compat.v1` 静态图导出冻结 `pb`
  - 导出 `router.pb`、`experts/expert_0.pb`... 和 `manifest.json`
- `inspect_pb.py`
  - 打印 `pb` 中的算子统计，方便快速检查是否出现了不想要的复杂控制流算子
- `requirements.txt`
  - 本地导出环境依赖

## 设计要点

为了提升 `atc` 通过率，导出的图只使用了较基础的算子组合：

- `Placeholder`
- `MatMul`
- `BiasAdd`
- `Relu`
- `Softmax`
- `ArgMax`
- `OneHot`
- `ReduceSum`
- `Mul`
- `Add` / `Sub`
- `GreaterEqual`
- `Cast`
- `Maximum`
- `Pack`
- `Identity`

路由图里没有使用 `tf.cond`、`tf.case`、`tf.while_loop` 之类的动态图控制流。

## 导出

```powershell
python .\export_split_moe_pb.py `
  --output-dir .\exports `
  --num-experts 4 `
  --feature-dim 64 `
  --output-dim 16 `
  --router-hidden-dim 32 `
  --expert-hidden-dim 64 `
  --second-expert-threshold 0.22
```

导出后目录示例：

```text
exports/
  router.pb
  manifest.json
  experts/
    expert_0.pb
    expert_1.pb
    expert_2.pb
    expert_3.pb
```

## 张量命名

### router.pb

- 输入
  - `input_features:0`
- 输出
  - `route_prob:0`
  - `selected_expert_ids:0`
  - `selected_expert_weights:0`
  - `selected_expert_count:0`
  - `selected_expert_mask:0`

其中：

- `selected_expert_ids:0` 形状是 `[batch, 2]`
- `selected_expert_weights:0` 形状是 `[batch, 2]`
- `selected_expert_count:0` 取值为 `1` 或 `2`
- 如果只选中 1 个专家，那么第二列 `id` 会回填为 `top1`，第二列 `weight` 为 `0`

### expert_x.pb

- 输入
  - `input_features:0`
- 输出
  - `expert_output:0`

## Ascend ATC 编译示例

以下示例以 batch=1、feature_dim=64 为例，请按你的实际模型维度修改：

```powershell
atc --model=.\exports\router.pb `
    --framework=3 `
    --output=.\om\router `
    --soc_version=Ascend310P3 `
    --input_shape="input_features:1,64"
```

```powershell
atc --model=.\exports\experts\expert_0.pb `
    --framework=3 `
    --output=.\om\expert_0 `
    --soc_version=Ascend310P3 `
    --input_shape="input_features:1,64"
```

对其他 `expert_1.pb`、`expert_2.pb` 等重复执行即可。

## 运行时调度逻辑

推荐的推理流程：

1. 输入特征先进入 `router.om`
2. 读取 `selected_expert_ids`、`selected_expert_weights`、`selected_expert_count`
3. 只调用前 `1~2` 个被选中的 `expert_x.om`
4. 在宿主侧做输出加权融合

融合公式：

```text
final_output = weight_0 * expert_output_0 + weight_1 * expert_output_1
```

如果 `selected_expert_count == 1`，第二项权重就是 `0`。

## 为什么不建议导出单个大一统 PB

如果把门控和全部专家放进一个冻结图里，通常会落入两类问题：

1. 为了“只执行部分专家”而引入控制流算子，`atc` 更容易失败。
2. 如果不用控制流，而是所有专家都参与计算再做 mask/加权，就失去了你最关心的算力节省目标。

所以对 Ascend 离线部署，更稳妥且更符合需求的方案就是这里的拆分式导出。
