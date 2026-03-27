# ==============================================================================
# PyTorch → TensorFlow 模型转换器
#
# 将 PyTorch 训练好的检测模型（双输入 UINT8 图像 → UINT8 heatmap）
# 转换为 TensorFlow 静态图，可直接注册为 MoE 专家。
#
# 支持的 PyTorch 层类型：
#   - nn.Conv2d (含 groups、padding)
#   - nn.ConvTranspose2d
#   - nn.BatchNorm2d
#   - nn.Linear
#   - nn.ReLU, nn.LeakyReLU, nn.Sigmoid, nn.Tanh
#   - nn.MaxPool2d, nn.AvgPool2d
#   - nn.Upsample (nearest/bilinear)
#   - 残差连接 (add)
#   - torch.cat (concat)
#
# 用法：
#   converter = PyTorchToTFConverter("model.pth")
#   converter.analyze()
#   converter.convert_weights("output_weights/")
#   builder_fn = converter.make_expert_builder()
# ==============================================================================

import os
import json
import numpy as np

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

import tensorflow as tf
tf.compat.v1.disable_eager_execution()


# ==============================================================================
# 权重转换核心
# ==============================================================================

def convert_conv2d_weights(pytorch_weight):
    """
    PyTorch Conv2d 权重: [out_channels, in_channels, kH, kW]
    TensorFlow Conv2D 权重: [kH, kW, in_channels, out_channels]
    """
    return np.transpose(pytorch_weight, (2, 3, 1, 0))


def convert_conv_transpose2d_weights(pytorch_weight):
    """
    PyTorch ConvTranspose2d 权重: [in_channels, out_channels, kH, kW]
    TensorFlow Conv2DTranspose 权重: [kH, kW, out_channels, in_channels]
    """
    return np.transpose(pytorch_weight, (2, 3, 1, 0))


def convert_linear_weights(pytorch_weight):
    """
    PyTorch Linear 权重: [out_features, in_features]
    TensorFlow Dense 权重: [in_features, out_features]
    """
    return np.transpose(pytorch_weight, (1, 0))


def convert_bn_params(state_dict, prefix):
    """提取 BatchNorm 的 gamma, beta, moving_mean, moving_variance。"""
    gamma = state_dict.get(f"{prefix}.weight")
    beta = state_dict.get(f"{prefix}.bias")
    mean = state_dict.get(f"{prefix}.running_mean")
    var = state_dict.get(f"{prefix}.running_var")
    results = {}
    if gamma is not None:
        results['gamma'] = gamma.numpy() if hasattr(gamma, 'numpy') else np.array(gamma)
    if beta is not None:
        results['beta'] = beta.numpy() if hasattr(beta, 'numpy') else np.array(beta)
    if mean is not None:
        results['moving_mean'] = mean.numpy() if hasattr(mean, 'numpy') else np.array(mean)
    if var is not None:
        results['moving_variance'] = var.numpy() if hasattr(var, 'numpy') else np.array(var)
    return results


# ==============================================================================
# PyTorch 模型分析器
# ==============================================================================

class PyTorchToTFConverter:
    """
    分析 PyTorch 模型结构和权重，转换为 TensorFlow 格式。

    用法：
        converter = PyTorchToTFConverter("model.pth")
        converter.analyze()
        converter.convert_weights("weights_dir/")
        builder = converter.make_expert_builder()
    """

    def __init__(self, model_path, model_instance=None):
        """
        Args:
            model_path: .pth/.pt 文件路径（state_dict 或完整模型）
            model_instance: 可选，PyTorch nn.Module 实例（用于推断层结构）
        """
        if not HAS_TORCH:
            raise RuntimeError("需要安装 PyTorch: pip install torch")

        self.model_path = model_path
        self.model_instance = model_instance
        self.state_dict = None
        self.layer_info = []  # 解析后的层信息
        self.tf_weights = {}  # 转换后的 TF 权重

    def analyze(self):
        """加载并分析 PyTorch 模型结构。"""
        print(f"[Converter] 加载 PyTorch 模型: {self.model_path}")

        checkpoint = torch.load(self.model_path, map_location='cpu', weights_only=False)

        # 支持 state_dict 和完整模型两种格式
        if isinstance(checkpoint, dict):
            if 'state_dict' in checkpoint:
                self.state_dict = checkpoint['state_dict']
            elif 'model_state_dict' in checkpoint:
                self.state_dict = checkpoint['model_state_dict']
            elif 'model' in checkpoint:
                obj = checkpoint['model']
                if isinstance(obj, dict):
                    self.state_dict = obj
                elif hasattr(obj, 'state_dict'):
                    self.state_dict = obj.state_dict()
                else:
                    self.state_dict = checkpoint
            else:
                # 尝试直接作为 state_dict 使用
                self.state_dict = checkpoint
        elif hasattr(checkpoint, 'state_dict'):
            self.state_dict = checkpoint.state_dict()
        else:
            raise ValueError("无法从文件中提取 state_dict")

        # 分析层结构
        self._analyze_layers()
        print(f"[Converter] 发现 {len(self.layer_info)} 个可转换层")

        return self

    def _analyze_layers(self):
        """从 state_dict 键名推断层类型和结构。"""
        self.layer_info = []
        visited_prefixes = set()

        for key in sorted(self.state_dict.keys()):
            parts = key.rsplit('.', 1)
            if len(parts) != 2:
                continue
            prefix, param_name = parts

            if prefix in visited_prefixes:
                continue

            if param_name == 'weight':
                w = self.state_dict[key]
                shape = tuple(w.shape)
                has_bias = f"{prefix}.bias" in self.state_dict

                if len(shape) == 4:
                    # Conv2d 或 ConvTranspose2d
                    # 启发式：如果 in_channels > out_channels 且有对应的反卷积模式
                    has_running_mean = f"{prefix}.running_mean" in self.state_dict
                    if has_running_mean:
                        layer_type = 'batchnorm2d'
                        info = {
                            'type': layer_type,
                            'prefix': prefix,
                            'num_features': shape[0],
                        }
                    else:
                        layer_type = 'conv2d'
                        info = {
                            'type': layer_type,
                            'prefix': prefix,
                            'out_channels': shape[0],
                            'in_channels': shape[1],
                            'kernel_size': (shape[2], shape[3]),
                            'has_bias': has_bias,
                        }
                    self.layer_info.append(info)
                    visited_prefixes.add(prefix)

                elif len(shape) == 2:
                    # Linear
                    info = {
                        'type': 'linear',
                        'prefix': prefix,
                        'out_features': shape[0],
                        'in_features': shape[1],
                        'has_bias': has_bias,
                    }
                    self.layer_info.append(info)
                    visited_prefixes.add(prefix)

                elif len(shape) == 1:
                    # BatchNorm（只有 weight 没有 2D weight）
                    has_running_mean = f"{prefix}.running_mean" in self.state_dict
                    if has_running_mean:
                        info = {
                            'type': 'batchnorm2d',
                            'prefix': prefix,
                            'num_features': shape[0],
                        }
                        self.layer_info.append(info)
                        visited_prefixes.add(prefix)

            elif param_name == 'running_mean' and prefix not in visited_prefixes:
                shape = tuple(self.state_dict[key].shape)
                info = {
                    'type': 'batchnorm2d',
                    'prefix': prefix,
                    'num_features': shape[0],
                }
                self.layer_info.append(info)
                visited_prefixes.add(prefix)

    def convert_weights(self, output_dir=None):
        """
        将 PyTorch 权重转换为 TensorFlow 格式。

        Args:
            output_dir: 可选，保存转换后权重的目录（.npy 文件）

        Returns:
            dict: {tf_var_name: numpy_array}
        """
        if self.state_dict is None:
            raise RuntimeError("请先调用 analyze()")

        print("[Converter] 开始转换权重 ...")
        self.tf_weights = {}

        for info in self.layer_info:
            prefix = info['prefix']
            tf_prefix = prefix.replace('.', '/')

            if info['type'] == 'conv2d':
                w_pt = self.state_dict[f"{prefix}.weight"]
                w_np = w_pt.numpy() if hasattr(w_pt, 'numpy') else np.array(w_pt)
                self.tf_weights[f"{tf_prefix}/kernel"] = convert_conv2d_weights(w_np)
                if info['has_bias']:
                    b_pt = self.state_dict[f"{prefix}.bias"]
                    b_np = b_pt.numpy() if hasattr(b_pt, 'numpy') else np.array(b_pt)
                    self.tf_weights[f"{tf_prefix}/bias"] = b_np

            elif info['type'] == 'linear':
                w_pt = self.state_dict[f"{prefix}.weight"]
                w_np = w_pt.numpy() if hasattr(w_pt, 'numpy') else np.array(w_pt)
                self.tf_weights[f"{tf_prefix}/kernel"] = convert_linear_weights(w_np)
                if info['has_bias']:
                    b_pt = self.state_dict[f"{prefix}.bias"]
                    b_np = b_pt.numpy() if hasattr(b_pt, 'numpy') else np.array(b_pt)
                    self.tf_weights[f"{tf_prefix}/bias"] = b_np

            elif info['type'] == 'batchnorm2d':
                bn_params = convert_bn_params(self.state_dict, prefix)
                for param_name, param_val in bn_params.items():
                    self.tf_weights[f"{tf_prefix}/{param_name}"] = param_val

        print(f"[Converter] 已转换 {len(self.tf_weights)} 个权重张量")

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            manifest = {}
            for name, arr in self.tf_weights.items():
                safe_name = name.replace('/', '__')
                npy_path = os.path.join(output_dir, f"{safe_name}.npy")
                np.save(npy_path, arr)
                manifest[name] = {
                    'file': f"{safe_name}.npy",
                    'shape': list(arr.shape),
                    'dtype': str(arr.dtype),
                }
            manifest_path = os.path.join(output_dir, 'manifest.json')
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            print(f"[Converter] 权重已保存到: {output_dir}")
            print(f"[Converter] 清单文件: {manifest_path}")

        return self.tf_weights

    def summary(self):
        """打印模型层结构摘要。"""
        print("\n[模型结构摘要]")
        print(f"  总层数: {len(self.layer_info)}")
        type_counts = {}
        for info in self.layer_info:
            t = info['type']
            type_counts[t] = type_counts.get(t, 0) + 1
        for t, c in sorted(type_counts.items()):
            print(f"  {t}: {c}")
        print()
        for i, info in enumerate(self.layer_info):
            if info['type'] == 'conv2d':
                bias_str = "+bias" if info['has_bias'] else ""
                print(f"  [{i:2d}] Conv2d  {info['prefix']}: "
                      f"in={info['in_channels']} out={info['out_channels']} "
                      f"kernel={info['kernel_size']} {bias_str}")
            elif info['type'] == 'linear':
                bias_str = "+bias" if info['has_bias'] else ""
                print(f"  [{i:2d}] Linear  {info['prefix']}: "
                      f"in={info['in_features']} out={info['out_features']} {bias_str}")
            elif info['type'] == 'batchnorm2d':
                print(f"  [{i:2d}] BN2d    {info['prefix']}: "
                      f"features={info['num_features']}")

    def make_expert_builder(self, weights_dir=None):
        """
        生成一个 TF expert builder 函数，可注册到 MoE ExpertRegistry。

        对于图像检测模型，builder 将：
        1. 接收展平的特征向量 [batch, gate_input_dim]
        2. 输出展平的特征向量 [batch, gate_input_dim]

        实际的图像处理（UINT8 [1,1,448,448] -> 卷积网络 -> UINT8 [1,1,448,448]）
        由外部 wrapper 处理。这里的 builder 用于门控路由。

        Args:
            weights_dir: 预转换权重目录，如果为 None 则使用内存中的权重

        Returns:
            builder_fn: callable(inputs, input_dim, hidden_dim, output_dim, scope) -> tensor
        """
        if weights_dir:
            tf_weights = load_converted_weights(weights_dir)
        elif self.tf_weights:
            tf_weights = self.tf_weights
        else:
            raise RuntimeError("请先调用 convert_weights()")

        def builder(inputs, input_dim, hidden_dim, output_dim, scope):
            """
            使用转换后的 PyTorch 权重构建 TF 专家网络。

            当 PyTorch 模型的全连接层维度与门控 input_dim 不匹配时，
            先用适配层将 input_dim 映射到 PyTorch 模型期望的输入维度，
            最后再映射到 output_dim。
            """
            with tf.compat.v1.variable_scope(scope):
                linear_layers = [info for info in self.layer_info
                                 if info['type'] == 'linear']

                if linear_layers:
                    h = inputs
                    prev_dim = input_dim

                    for i, layer_info in enumerate(linear_layers):
                        prefix = layer_info['prefix'].replace('.', '/')
                        kernel_key = f"{prefix}/kernel"
                        bias_key = f"{prefix}/bias"

                        if kernel_key in tf_weights:
                            pt_in = tf_weights[kernel_key].shape[0]
                            pt_out = tf_weights[kernel_key].shape[1]
                        else:
                            pt_in = prev_dim
                            pt_out = hidden_dim

                        # 如果维度不匹配，插入适配层
                        if prev_dim != pt_in:
                            w_adapt = tf.compat.v1.get_variable(
                                f"adapt_{i}", [prev_dim, pt_in],
                                initializer=tf.compat.v1.initializers.glorot_uniform())
                            b_adapt = tf.compat.v1.get_variable(
                                f"adapt_b_{i}", [pt_in],
                                initializer=tf.compat.v1.initializers.zeros())
                            h = tf.nn.relu(tf.matmul(h, w_adapt) + b_adapt)

                        if kernel_key in tf_weights:
                            w_init = tf.constant_initializer(tf_weights[kernel_key])
                        else:
                            w_init = tf.compat.v1.initializers.glorot_uniform()

                        w = tf.compat.v1.get_variable(
                            f"w{i}", [pt_in, pt_out], initializer=w_init)

                        if bias_key in tf_weights:
                            b_init = tf.constant_initializer(tf_weights[bias_key])
                        else:
                            b_init = tf.compat.v1.initializers.zeros()
                        b = tf.compat.v1.get_variable(
                            f"b{i}", [pt_out], initializer=b_init)

                        h = tf.nn.relu(tf.matmul(h, w) + b)
                        prev_dim = pt_out

                    # 最后映射到 output_dim
                    if prev_dim != output_dim:
                        w_out = tf.compat.v1.get_variable(
                            "w_out", [prev_dim, output_dim],
                            initializer=tf.compat.v1.initializers.glorot_uniform())
                        b_out = tf.compat.v1.get_variable(
                            "b_out", [output_dim],
                            initializer=tf.compat.v1.initializers.zeros())
                        h = tf.matmul(h, w_out) + b_out
                    return h
                else:
                    # 无全连接层时，使用标准 MLP
                    w1 = tf.compat.v1.get_variable(
                        "w1", [input_dim, hidden_dim],
                        initializer=tf.compat.v1.initializers.glorot_uniform())
                    b1 = tf.compat.v1.get_variable(
                        "b1", [hidden_dim],
                        initializer=tf.compat.v1.initializers.zeros())
                    h = tf.nn.relu(tf.matmul(inputs, w1) + b1)
                    w2 = tf.compat.v1.get_variable(
                        "w2", [hidden_dim, output_dim],
                        initializer=tf.compat.v1.initializers.glorot_uniform())
                    b2 = tf.compat.v1.get_variable(
                        "b2", [output_dim],
                        initializer=tf.compat.v1.initializers.zeros())
                    return tf.matmul(h, w2) + b2

        builder.__name__ = f"pytorch_converted_{os.path.basename(self.model_path)}"
        return builder


# ==============================================================================
# 权重 I/O
# ==============================================================================

def load_converted_weights(weights_dir):
    """从磁盘加载已转换的 TF 权重。"""
    manifest_path = os.path.join(weights_dir, 'manifest.json')
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    weights = {}
    for name, info in manifest.items():
        npy_path = os.path.join(weights_dir, info['file'])
        weights[name] = np.load(npy_path)
    return weights


# ==============================================================================
# 完整图像检测专家构建（NCHW 双输入 UINT8）
# ==============================================================================

def build_image_detection_expert_from_pytorch(
    img_a, img_b, converter, scope, data_format='NCHW'
):
    """
    从 PyTorch 转换的权重构建完整的图像检测专家。

    Args:
        img_a: [1,1,448,448] UINT8 待检测图像
        img_b: [1,1,448,448] UINT8 参考图像
        converter: PyTorchToTFConverter 实例（已 analyze + convert_weights）
        scope: 变量命名空间
        data_format: 'NCHW' 或 'NHWC'

    Returns:
        heatmap: [1,1,448,448] UINT8 检测热力图
    """
    tf_weights = converter.tf_weights

    with tf.compat.v1.variable_scope(scope):
        # UINT8 -> FP32 归一化
        a_float = tf.cast(img_a, tf.float32) / 255.0
        b_float = tf.cast(img_b, tf.float32) / 255.0

        # 拼接双输入 -> [1, 2, 448, 448]
        if data_format == 'NCHW':
            combined = tf.concat([a_float, b_float], axis=1)
        else:
            combined = tf.concat([a_float, b_float], axis=3)

        # 按层构建网络
        h = combined
        for i, info in enumerate(converter.layer_info):
            prefix = info['prefix'].replace('.', '/')
            layer_scope = f"layer_{i}"

            if info['type'] == 'conv2d':
                kernel_key = f"{prefix}/kernel"
                bias_key = f"{prefix}/bias"

                if kernel_key in tf_weights:
                    kernel_val = tf_weights[kernel_key]
                    k_init = tf.constant_initializer(kernel_val)
                    k_shape = kernel_val.shape
                else:
                    k_shape = [info['kernel_size'][0], info['kernel_size'][1],
                               h.shape[1 if data_format == 'NCHW' else 3].value
                               or info['in_channels'],
                               info['out_channels']]
                    k_init = tf.compat.v1.initializers.glorot_uniform()

                kernel = tf.compat.v1.get_variable(
                    f"{layer_scope}/kernel", k_shape, initializer=k_init)

                # Padding: same
                kh, kw = info['kernel_size']
                pad_h = (kh - 1) // 2
                pad_w = (kw - 1) // 2
                if data_format == 'NCHW':
                    paddings = [[0, 0], [0, 0], [pad_h, pad_h], [pad_w, pad_w]]
                else:
                    paddings = [[0, 0], [pad_h, pad_h], [pad_w, pad_w], [0, 0]]

                h_padded = tf.pad(h, paddings)
                h = tf.nn.conv2d(h_padded, kernel, strides=[1, 1, 1, 1],
                                 padding='VALID', data_format=data_format)

                if bias_key in tf_weights:
                    b_init = tf.constant_initializer(tf_weights[bias_key])
                    bias = tf.compat.v1.get_variable(
                        f"{layer_scope}/bias", [info['out_channels']],
                        initializer=b_init)
                    if data_format == 'NCHW':
                        h = h + tf.reshape(bias, [1, -1, 1, 1])
                    else:
                        h = h + bias

                h = tf.nn.relu(h)

            elif info['type'] == 'batchnorm2d':
                bn_params = {}
                for param_name in ['gamma', 'beta', 'moving_mean', 'moving_variance']:
                    key = f"{prefix}/{param_name}"
                    if key in tf_weights:
                        bn_params[param_name] = tf_weights[key]

                num_features = info['num_features']
                gamma = tf.compat.v1.get_variable(
                    f"{layer_scope}/gamma", [num_features],
                    initializer=tf.constant_initializer(
                        bn_params.get('gamma', np.ones(num_features))))
                beta = tf.compat.v1.get_variable(
                    f"{layer_scope}/beta", [num_features],
                    initializer=tf.constant_initializer(
                        bn_params.get('beta', np.zeros(num_features))))
                mean = tf.constant(
                    bn_params.get('moving_mean', np.zeros(num_features)),
                    dtype=tf.float32, name=f"{layer_scope}/moving_mean")
                var = tf.constant(
                    bn_params.get('moving_variance', np.ones(num_features)),
                    dtype=tf.float32, name=f"{layer_scope}/moving_var")

                if data_format == 'NCHW':
                    gamma_r = tf.reshape(gamma, [1, -1, 1, 1])
                    beta_r = tf.reshape(beta, [1, -1, 1, 1])
                    mean_r = tf.reshape(mean, [1, -1, 1, 1])
                    var_r = tf.reshape(var, [1, -1, 1, 1])
                else:
                    gamma_r = gamma
                    beta_r = beta
                    mean_r = mean
                    var_r = var

                h = gamma_r * (h - mean_r) / tf.sqrt(var_r + 1e-5) + beta_r

        # 输出映射到单通道 + sigmoid -> [0,1] -> UINT8
        # 最后一个 1x1 卷积映射到单通道
        out_channels = h.shape[1].value if data_format == 'NCHW' else h.shape[3].value
        if out_channels is None:
            out_channels = 1
        if out_channels != 1:
            final_kernel = tf.compat.v1.get_variable(
                "final_conv/kernel", [1, 1, out_channels, 1],
                initializer=tf.compat.v1.initializers.glorot_uniform())
            h = tf.nn.conv2d(h, final_kernel, strides=[1, 1, 1, 1],
                             padding='VALID', data_format=data_format)

        h = tf.nn.sigmoid(h)

        # FP32 [0,1] -> UINT8 [0,255]
        heatmap = tf.cast(tf.round(h * 255.0), tf.uint8)

    return heatmap


# ==============================================================================
# 便捷接口
# ==============================================================================

def create_expert_builder_from_pytorch(model_path, weights_output_dir=None):
    """
    一键将 PyTorch 模型转换为 MoE expert builder。

    Args:
        model_path: PyTorch 模型文件路径
        weights_output_dir: 可选，保存转换权重的目录

    Returns:
        (builder_fn, converter): builder 可注册到 ExpertRegistry
    """
    converter = PyTorchToTFConverter(model_path)
    converter.analyze()
    converter.convert_weights(weights_output_dir)
    converter.summary()
    builder = converter.make_expert_builder(weights_output_dir)
    return builder, converter


def create_dummy_pytorch_model(save_path, model_type='detection'):
    """
    创建一个用于测试的 PyTorch 模型。

    Args:
        save_path: 保存路径
        model_type: 'detection' - 双输入图像检测模型
    """
    if not HAS_TORCH:
        raise RuntimeError("需要安装 PyTorch")

    class DummyDetectionModel(nn.Module):
        """模拟双输入图像检测模型：2x [1,1,448,448] -> [1,1,448,448]"""
        def __init__(self):
            super().__init__()
            # 双通道输入合并
            self.conv1 = nn.Conv2d(2, 16, 3, padding=1)
            self.bn1 = nn.BatchNorm2d(16)
            self.conv2 = nn.Conv2d(16, 32, 3, padding=1)
            self.bn2 = nn.BatchNorm2d(32)
            self.conv3 = nn.Conv2d(32, 16, 3, padding=1)
            self.bn3 = nn.BatchNorm2d(16)
            self.conv4 = nn.Conv2d(16, 1, 1)
            # 门控路由用的特征提取
            self.fc1 = nn.Linear(448 * 448, 256)
            self.fc2 = nn.Linear(256, 128)

        def forward(self, img_a, img_b):
            x = torch.cat([img_a.float() / 255.0, img_b.float() / 255.0], dim=1)
            x = torch.relu(self.bn1(self.conv1(x)))
            x = torch.relu(self.bn2(self.conv2(x)))
            x = torch.relu(self.bn3(self.conv3(x)))
            x = torch.sigmoid(self.conv4(x))
            return (x * 255).to(torch.uint8)

    model = DummyDetectionModel()
    model.eval()
    # 跑一次前向以初始化 BN running stats
    with torch.no_grad():
        dummy_a = torch.randint(0, 256, (1, 1, 448, 448), dtype=torch.uint8)
        dummy_b = torch.randint(0, 256, (1, 1, 448, 448), dtype=torch.uint8)
        _ = model(dummy_a, dummy_b)

    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"[Test] 已保存测试模型: {save_path}")
    return model


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        model_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "output/converted_weights"
    else:
        # 创建测试模型并转换
        print("=" * 60)
        print("PyTorch → TensorFlow 模型转换器 (测试模式)")
        print("=" * 60)
        model_path = "output/test_pytorch_model.pth"
        output_dir = "output/converted_weights"
        create_dummy_pytorch_model(model_path)

    builder, converter = create_expert_builder_from_pytorch(model_path, output_dir)
    print(f"\n[Done] Expert builder 已创建: {builder.__name__}")
    print(f"可通过 ExpertRegistry.register(expert_id, builder) 注册到 MoE 路由器")
