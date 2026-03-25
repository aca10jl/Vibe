# PyTorch → TensorFlow 转换器：工程难点与挑战总结

经过 **42 次迭代提交**（其中 8 次专项 bugfix），5335 行核心代码，这个项目暴露了若干深层工程挑战。

---

## 一、两套框架的语义鸿沟

这是整个项目最本质的难点——PyTorch 和 TensorFlow 表面 API 相似，但在底层语义上存在大量不对称。

### 1. 数据格式对立：NCHW vs NHWC

PyTorch 全局使用 `NCHW`，TensorFlow 默认 `NHWC`。这不只是改个 transpose 的问题，它像涟漪一样扩散到所有角落：
- `concat` 的 `dim=1` → `axis=-1`
- `BatchNorm` 的 axis 从 `1` 变为 `-1`
- `tf.pad` 的 padding 维度顺序完全不同
- `torch.flatten(x, 1)` 在 NHWC 下需要先 transpose 再 reshape
- PB 导出的 `input_format` 和 ATC 命令也要跟着变

为此额外支持了 `--channels-first` 模式，保持 NCHW 不转，但这又引入了一整套 `data_format='channels_first'` 的注入逻辑，需要对 Conv/BN/Pool/Upsample 全部处理。

### 2. padding 语义不一致（最顽固的 bug 来源）

PyTorch `padding=1` 是精确的对称整数填充；TensorFlow `padding='same'` 是自动计算的，且在 `stride > 1` 时采用**非对称填充**，与 PyTorch 结果不同。

这导致了一整套显式 padding 注入机制：
- 检测 `stride > 1 + padding > 0` 的 Conv/Pool 层
- 在 `__init__` 中改为 `padding='valid'`
- 在 `call()` 中注入 `tf.pad(x, ...)` 调用

而这个注入机制本身又引发了**跨类污染**问题：当 `BasicBlock.conv1` 和 `SimpleResNet.conv1` 同名时，SimpleResNet 的 padding 被错误注入到 BasicBlock。解决方案是引入 class-aware scoping。

### 3. 参数命名体系完全不同

| PyTorch | TensorFlow | 备注 |
|---------|-----------|------|
| `kernel_size` | `kernel_size`(Conv) / `pool_size`(Pool) | Pool 层不一样 |
| `stride` | `strides` | 复数 |
| `bias` | `use_bias` | |
| `padding=1` | `padding='same'` | 语义转换 |
| `dilation` | `dilation_rate` | |
| `in_channels` | 无（自动推断） | 需要 drop |

每种层类型都有自己的参数映射规则，不能统一处理。

---

## 二、基于正则的代码转换 vs AST

项目选择了**正则表达式**而非 AST 重写作为核心技术路线。这是一个务实但充满陷阱的决策。

**优点**：保持原始代码格式、注释、缩进，输出可读性好。

**代价**：

- **括号匹配**：无法用简单正则处理嵌套括号。项目多处实现了手动的 paren-depth tracking：
  ```python
  depth = 1
  while i < len(source) and depth > 0:
      if source[i] == "(": depth += 1
      elif source[i] == ")": depth -= 1
  ```
  `converter.py` 中这种模式出现了至少 **10 处**。

- **子串冲突**：`torch.log` vs `torch.log_softmax`，`F.relu` vs `F.relu6`，`x.mean` vs `x.mean_value`。必须按长度降序排序替换，否则长函数名被短匹配截断。

- **上下文缺失**：正则无法知道一段代码属于哪个 class、哪个 method。跨类 padding 注入的 bug 就是典型。最终不得不在正则的基础上叠加了 class boundary detection。

---

## 三、权重转换的"结构匹配"难题

PyTorch 和 TensorFlow 的权重命名体系完全不同：

```
PyTorch: down1.conv.conv1.weight       → shape [64, 32, 3, 3]
TF:      down/double_conv/conv2d/kernel → shape [3, 3, 32, 64]
```

**名称匹配**在 demo UNet 等标准模型上完全失败（命中率 0/100），因为两边的命名结构差距太大。

解决方案是**结构匹配**：
1. 对 PyTorch 和 TF 的权重按层遍历顺序排列
2. 对每个权重分配角色标签（`conv_kernel`, `bn_gamma`, `bn_beta`, `bn_moving_mean`, ...）
3. 按角色序列逐一对齐

挑战在于：
- PyTorch 有 `num_batches_tracked` 等 TF 没有的字段，需要跳过
- 卷积核需要转置 `[O,I,H,W]` → `[H,W,I,O]`
- ConvTranspose 的转置规则又不一样 `[I,O,H,W]` → `[H,W,O,I]`
- Linear/Dense 需要 `[O,I]` → `[I,O]`

---

## 四、动态 vs 静态的冲突

PyTorch 天然支持动态计算图，很多操作用 Python 变量控制：

```python
# padding 是变量，不是常量
diff_y = x2.shape[2] - x1.shape[2]
x1 = F.pad(x1, [diff_x // 2, diff_x - diff_x // 2, ...])
```

这类代码不能静态替换为固定的 `tf.pad` 常量。解决方案是生成一个**运行时辅助函数** `_pt_padding_to_tf()`，在 TF 执行时动态计算 padding 布局。类似地 `torch.flatten(x, start_dim)` 中 `start_dim` 也可能是变量，需要运行时处理。

---

## 五、PB 导出与昇腾兼容

从 Keras Model 到 Frozen Graph (.pb) 的路径本身就有挑战：

- **多输入子模块**：UNet 的 `Up(x1, x2)` 接收两个输入，`tf.function` 的 trace 需要特殊处理，不能直接用 `model(input)` 方式 trace
- **算子白名单**：昇腾 ATC 工具只支持特定 TF 算子集，需要扫描 frozen graph 中的每个 op 并校验兼容性
- **input_shape / input_format**：PB 的输入签名需要精确匹配 NHWC/NCHW 格式和具体 shape

---

## 六、测试与验证的组合爆炸

每个修复都可能破坏其他模型。验证矩阵是：

```
7 种模型架构 x 2 种数据格式 (NHWC/NCHW) x 4 个阶段 (代码/权重/精度/PB)
= 56 个端到端检查点
+ 45 项算子级单元测试
```

越到后期，每次修改的回归风险越高。比如修复 `MaxPool2d` 参数转换时，必须确保不影响已经工作的 `MaxPool2d(2)` (简单形式) 和 `AdaptiveMaxPool2d` (完全不同的转换逻辑)。

---

## 总结

| 难度维度 | 核心挑战 | 解决方式 |
|---------|---------|---------|
| 框架语义差异 | NCHW/NHWC, padding, 参数命名 | 分层转换 + channels_first 双模式 |
| 代码转换引擎 | 嵌套括号、上下文感知、子串冲突 | 手动括号深度追踪 + 类边界检测 |
| 权重对齐 | 命名不匹配、形状转置规则多样 | 结构匹配 + 角色标签对齐 |
| 动态计算 | 变量 padding/shape 无法静态替换 | 运行时辅助函数注入 |
| 部署链路 | 多输入 trace、算子兼容性 | 分支 trace + 算子白名单扫描 |
| 质量保证 | 修复 A 破坏 B 的回归风险 | 7 模型 x 2 格式 + 45 算子测试 |

这个项目的本质困难在于：**它不是在做翻译，而是在弥合两套有着不同设计哲学的深度学习框架之间的语义裂缝**——每一层看似简单的 API 映射背后，都隐藏着数据格式、数值行为、参数约定的微妙差异。
