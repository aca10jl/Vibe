# 业界方案对比与技术路线分析

## 业界现有方案

### 1. ONNX 中间表示路线（主流）

**路线**：PyTorch → ONNX → TensorFlow（通过 onnx-tf）

这是目前最常见的方案，但存在公认的局限：
- 转换后模型**只能用于推理**，参数被 bake 进图中，无法继续训练
- NCHW→NHWC 转换会插入**大量冗余 Transpose** 算子，推理变慢
- **不支持动态控制流**（`if/else`、`while` 循环等），ONNX 规范本身缺乏对 Switch/Merge 等控制流算子的完整支持，因此所有以 ONNX 作为中间层的技术路线都无法实现 `while`、`if` 等关键特性
- onnx-tf 项目维护不活跃，很多 op 不支持
- 输出是计算图，**不是可读的源代码**

### 2. Nobuco（图追踪路线）

**路线**：运行时 trace PyTorch 图 → 逐节点映射为 Keras 等价节点

比 ONNX 更直接，但：
- 只支持 **Keras 2**，不兼容最新的 Keras 3
- 遇到不支持的 op 需要用户**手写 node converter**
- 基于 tracing，对动态图（条件分支、变长输入）天然不友好
- 社区反馈调试困难
- 输出也是**计算图**，不是人类可读的模型代码

### 3. Microsoft MMdnn（中间表示路线）

**路线**：PyTorch → MMdnn IR → TensorFlow

微软的通用框架转换工具，支持 7+ 框架互转。但：
- **事实上已停止维护**（最后一次发版 2020 年，323 个 issue 无人回复）
- 最后支持的是 PyTorch 1.5.1（现在已经到 2.x）
- 依赖已过时的 Python 3.6

### 4. Google AI Edge Torch（2024）

Google 官方出品，但**目标是 TFLite**（移动端），不是完整的 TensorFlow。不适用于昇腾等服务器端部署场景。

### 5. 权重迁移方案（如 nn-transfer）

只搬运权重，需要用户**手动用 Keras 重写整个模型架构**。本质上不是转换器，是个辅助工具。

---

## 技术路线对比

| 维度 | ONNX 路线 | Nobuco | 本项目 |
|------|----------|--------|--------|
| **输出物** | 计算图 (protobuf) | 计算图 (Keras graph) | **可读的 .py 源代码** |
| **可维护性** | 不可编辑 | 不可编辑 | 可以直接修改、调试 |
| **可训练性** | 仅推理 | 仅推理 | **可继续训练** |
| **控制流** | 不支持 while/if | 不支持动态分支 | **支持 Switch 任务流 (while/if)** |
| **权重转换** | 内嵌在图中 | 自动 | **独立文件 (.h5)** |
| **部署产物** | 需额外转换 | 需额外转换 | **直出 PB + ATC 命令** |
| **昇腾适配** | 无 | 无 | **内置兼容性检查** |
| **技术路线** | IR 中间表示 | 运行时 tracing | **源码级正则转换** |

---

## 本项目的技术路线选择

### 为什么选择源码级转换

业界方案普遍在"图"层面工作——把模型当作计算图来转换。本项目选择在"代码"层面工作——把模型当作源代码来转换。

这条路线的**优势**：

1. **输出可读可改**：转换结果是标准的 Python 代码，开发者可以直接阅读、修改、调试，不需要反序列化工具
2. **可继续训练**：生成的 TF 模型是完整的 `tf.keras.Model` 子类，权重独立存储为 `.h5` 文件，可以在 TF 侧继续 fine-tune
3. **支持控制流**：因为输出是源代码而非静态图，Python 原生的 `if/else`、`while` 等控制流自然保留，导出 PB 时通过 `tf.function` trace 生成 TF 原生的 Switch/Merge 控制流算子，这是 ONNX 路线做不到的
4. **端到端昇腾部署**：直出 Frozen Graph (.pb)，内置算子兼容性检查，自动生成 ATC 转换命令

这条路线的**代价**：

1. 正则引擎的脆弱性——嵌套括号、子串冲突、跨类上下文污染等问题
2. 需要为每种层类型编写独立的参数映射规则
3. 对高度动态的代码模式（运行时生成的层、metaclass 等）支持有限

### 关于控制流支持的技术分析

ONNX 规范在设计上将模型表示为静态数据流图，缺乏对动态控制流的完整支持。虽然 ONNX 定义了 `If` 和 `Loop` 算子，但实际的 PyTorch → ONNX 导出器（`torch.onnx.export`）对这些算子的支持非常有限，许多包含条件分支和循环的模型无法成功导出。

本项目的源码级转换路线天然避开了这个限制：
- PyTorch 源码中的 `if/else` 在转换后仍然是 Python 的 `if/else`
- `for/while` 循环同样原样保留
- 当通过 `tf.function` trace 导出 PB 时，TensorFlow 自身的 AutoGraph 机制会将这些 Python 控制流编译为 TF 原生的 Switch/Merge/LoopCond 等算子
- 这些 TF 原生控制流算子在昇腾 ATC 工具链中有完整的支持

---

## 已验证的精度结果

| 模型架构 | 余弦相似度 | 状态 |
|---------|----------|------|
| UNet (语义分割) | 1.000000 | PASSED |
| SimpleResNet (轻量版, 3 层) | 0.999552 | PASSED |
| SimpleResNet (标准版, 含 MaxPool) | 0.998725 | PASSED |
| LeNet (经典 CNN) | > 0.999 | PASSED |
| MiniVGG (VGG 风格) | > 0.999 | PASSED |
| MultiHeadNet (多任务双输出) | > 0.999 | PASSED |
| BottleneckNet (ResNet-50 风格) | > 0.999 | PASSED |
| EncoderDecoder (编解码器) | > 0.999 | PASSED |

所有模型在 NHWC 和 NCHW 双模式下均通过精度校验和 PB 导出验证。

---

## 参考资料

- [ONNX - Open Neural Network Exchange](https://onnx.ai/)
- [onnx-tf - ONNX to TensorFlow](https://github.com/onnx/onnx-tensorflow)
- [Nobuco - PyTorch to Keras conversion](https://github.com/AlexanderLutsenko/nobuco)
- [Microsoft MMdnn](https://github.com/microsoft/MMdnn)
- [AI Edge Torch](https://ai.google.dev/edge/litert/models/convert_pytorch)
- [On the Challenge of Converting TF Models to PyTorch](https://towardsdatascience.com/on-the-challenge-of-converting-tensorflow-models-to-pytorch/)
- [deep-learning-model-convertor collection](https://github.com/ysh329/deep-learning-model-convertor)
