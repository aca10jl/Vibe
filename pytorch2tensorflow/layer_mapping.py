"""
Layer and operation mapping from PyTorch to TensorFlow/Keras.

Provides comprehensive mapping tables for:
- nn.Module layers → tf.keras.layers
- Activation functions
- Pooling operations
- Normalization layers
- PyTorch functional ops → TensorFlow equivalents
- Weight name and shape transformations
"""

# ─────────────────────────────────────────────
# PyTorch nn.Module → tf.keras.layers mapping
# ─────────────────────────────────────────────

LAYER_MAP = {
    # Convolution layers
    "nn.Conv1d": "tf.keras.layers.Conv1D",
    "nn.Conv2d": "tf.keras.layers.Conv2D",
    "nn.Conv3d": "tf.keras.layers.Conv3D",
    "nn.ConvTranspose1d": "tf.keras.layers.Conv1DTranspose",
    "nn.ConvTranspose2d": "tf.keras.layers.Conv2DTranspose",
    "nn.ConvTranspose3d": "tf.keras.layers.Conv3DTranspose",
    # Depthwise / Separable
    "nn.Conv2d_depthwise": "tf.keras.layers.DepthwiseConv2D",
    # Linear
    "nn.Linear": "tf.keras.layers.Dense",
    # Pooling
    "nn.MaxPool1d": "tf.keras.layers.MaxPool1D",
    "nn.MaxPool2d": "tf.keras.layers.MaxPool2D",
    "nn.MaxPool3d": "tf.keras.layers.MaxPool3D",
    "nn.AvgPool1d": "tf.keras.layers.AveragePooling1D",
    "nn.AvgPool2d": "tf.keras.layers.AveragePooling2D",
    "nn.AvgPool3d": "tf.keras.layers.AveragePooling3D",
    "nn.AdaptiveAvgPool1d": "tf.keras.layers.GlobalAveragePooling1D",
    "nn.AdaptiveAvgPool2d": "tf.keras.layers.GlobalAveragePooling2D",
    "nn.AdaptiveAvgPool3d": "tf.keras.layers.GlobalAveragePooling3D",
    "nn.AdaptiveMaxPool1d": "tf.keras.layers.GlobalMaxPool1D",
    "nn.AdaptiveMaxPool2d": "tf.keras.layers.GlobalMaxPool2D",
    # Normalization
    "nn.BatchNorm1d": "tf.keras.layers.BatchNormalization",
    "nn.BatchNorm2d": "tf.keras.layers.BatchNormalization",
    "nn.BatchNorm3d": "tf.keras.layers.BatchNormalization",
    "nn.InstanceNorm1d": "tfa.layers.InstanceNormalization",
    "nn.InstanceNorm2d": "tfa.layers.InstanceNormalization",
    "nn.InstanceNorm3d": "tfa.layers.InstanceNormalization",
    "nn.GroupNorm": "tf.keras.layers.GroupNormalization",
    "nn.LayerNorm": "tf.keras.layers.LayerNormalization",
    # Dropout
    "nn.Dropout": "tf.keras.layers.Dropout",
    "nn.Dropout2d": "tf.keras.layers.SpatialDropout2D",
    "nn.Dropout3d": "tf.keras.layers.SpatialDropout3D",
    # Activation layers
    "nn.ReLU": "tf.keras.layers.ReLU",
    "nn.LeakyReLU": "tf.keras.layers.LeakyReLU",
    "nn.PReLU": "tf.keras.layers.PReLU",
    "nn.ELU": "tf.keras.layers.ELU",
    "nn.GELU": "tf.keras.layers.Activation('gelu')",
    "nn.Sigmoid": "tf.keras.layers.Activation('sigmoid')",
    "nn.Tanh": "tf.keras.layers.Activation('tanh')",
    "nn.Softmax": "tf.keras.layers.Softmax",
    "nn.Mish": "tf.keras.layers.Activation('mish')",
    "nn.SiLU": "tf.keras.layers.Activation('swish')",
    "nn.Hardswish": "tf.keras.layers.Activation('hard_swish')",
    "nn.Hardsigmoid": "tf.keras.layers.Activation('hard_sigmoid')",
    # Reshape / Utility
    "nn.Flatten": "tf.keras.layers.Flatten",
    "nn.Unflatten": "tf.keras.layers.Reshape",
    "nn.Identity": "tf.keras.layers.Activation('linear')",
    # Padding
    "nn.ZeroPad2d": "tf.keras.layers.ZeroPadding2D",
    "nn.ConstantPad2d": "tf.keras.layers.ZeroPadding2D",
    "nn.ReflectionPad2d": "ReflectionPadding2D",  # custom layer
    # Embedding
    "nn.Embedding": "tf.keras.layers.Embedding",
    # RNN
    "nn.LSTM": "tf.keras.layers.LSTM",
    "nn.GRU": "tf.keras.layers.GRU",
    "nn.RNN": "tf.keras.layers.SimpleRNN",
    # Upsampling
    "nn.Upsample": "tf.keras.layers.UpSampling2D",
    "nn.UpsamplingBilinear2d": "tf.keras.layers.UpSampling2D",
    "nn.UpsamplingNearest2d": "tf.keras.layers.UpSampling2D",
    "nn.PixelShuffle": "PixelShuffle",  # custom implementation
}

# ─────────────────────────────────────────────
# Activation function mapping (F.xxx / torch.xxx)
# ─────────────────────────────────────────────

ACTIVATION_MAP = {
    "F.relu": "tf.nn.relu",
    "torch.relu": "tf.nn.relu",
    "F.relu6": "tf.nn.relu6",
    "F.leaky_relu": "tf.nn.leaky_relu",
    "F.elu": "tf.nn.elu",
    "F.gelu": "tf.nn.gelu",
    "F.selu": "tf.nn.selu",
    "F.sigmoid": "tf.math.sigmoid",
    "torch.sigmoid": "tf.math.sigmoid",
    "F.tanh": "tf.math.tanh",
    "torch.tanh": "tf.math.tanh",
    "F.softmax": "tf.nn.softmax",
    "F.log_softmax": "tf.nn.log_softmax",
    "F.softplus": "tf.math.softplus",
    "F.silu": "tf.nn.silu",
    "F.mish": "tf.keras.activations.mish",
    "F.hardswish": "tf.keras.activations.hard_swish",
    "F.hardsigmoid": "tf.keras.activations.hard_sigmoid",
    "F.dropout": "tf.nn.dropout",
    "F.dropout2d": "tf.nn.dropout",
    "F.dropout3d": "tf.nn.dropout",
}

# ─────────────────────────────────────────────
# Functional operation mapping
# ─────────────────────────────────────────────

FUNCTIONAL_MAP = {
    # Interpolation / Resize
    "F.interpolate": "tf.image.resize",
    "F.upsample": "tf.image.resize",
    "F.upsample_nearest": "tf.image.resize",
    "F.upsample_bilinear": "tf.image.resize",
    # Padding
    "F.pad": "tf.pad",
    # Pooling
    "F.avg_pool2d": "tf.nn.avg_pool2d",
    "F.max_pool2d": "tf.nn.max_pool2d",
    "F.adaptive_avg_pool2d": "tf.reduce_mean",  # with reshape
    # Normalization
    "F.batch_norm": "tf.nn.batch_normalization",
    "F.layer_norm": "tf.keras.layers.LayerNormalization",
    "F.group_norm": "tf.keras.layers.GroupNormalization",
    "F.instance_norm": "tfa.layers.InstanceNormalization",
    # Dropout (functional)
    "F.dropout": "tf.nn.dropout",
    "F.dropout2d": "tf.nn.dropout",
    "F.dropout3d": "tf.nn.dropout",
    # Convolution
    "F.conv1d": "tf.nn.conv1d",
    "F.conv2d": "tf.nn.conv2d",
    "F.conv3d": "tf.nn.conv3d",
    "F.conv_transpose2d": "tf.nn.conv2d_transpose",
    # Linear algebra
    "torch.matmul": "tf.matmul",
    "torch.bmm": "tf.matmul",
    "torch.mm": "tf.matmul",
    "torch.einsum": "tf.einsum",
    # Tensor operations
    "torch.cat": "tf.concat",
    "torch.stack": "tf.stack",
    "torch.split": "tf.split",
    "torch.chunk": "tf.split",
    "torch.squeeze": "tf.squeeze",
    "torch.unsqueeze": "tf.expand_dims",
    "torch.flatten": "tf.reshape",
    "torch.reshape": "tf.reshape",
    "torch.permute": "tf.transpose",
    "torch.transpose": "tf.transpose",
    "torch.contiguous": "",  # no-op in TF
    # Math operations
    "torch.abs": "tf.abs",
    "torch.clamp": "tf.clip_by_value",
    "torch.clip": "tf.clip_by_value",
    "torch.exp": "tf.exp",
    "torch.log": "tf.math.log",
    "torch.sqrt": "tf.math.sqrt",
    "torch.pow": "tf.pow",
    "torch.mean": "tf.reduce_mean",
    "torch.sum": "tf.reduce_sum",
    "torch.max": "tf.reduce_max",
    "torch.min": "tf.reduce_min",
    "torch.argmax": "tf.argmax",
    "torch.argmin": "tf.argmin",
    "torch.where": "tf.where",
    "torch.zeros": "tf.zeros",
    "torch.ones": "tf.ones",
    "torch.zeros_like": "tf.zeros_like",
    "torch.ones_like": "tf.ones_like",
    "torch.arange": "tf.range",
    "torch.linspace": "tf.linspace",
    "torch.tensor": "tf.constant",
    "torch.norm": "tf.norm",
    # Comparison
    "torch.eq": "tf.equal",
    "torch.ne": "tf.not_equal",
    "torch.gt": "tf.greater",
    "torch.lt": "tf.less",
    "torch.ge": "tf.greater_equal",
    "torch.le": "tf.less_equal",
}

# ─────────────────────────────────────────────
# Tensor method mapping (.xxx())
# ─────────────────────────────────────────────

TENSOR_METHOD_MAP = {
    ".view(": "tf.reshape(",
    ".reshape(": "tf.reshape(",
    ".permute(": "tf.transpose(",
    ".transpose(": "tf.transpose(",
    ".contiguous()": "",  # no-op in TF
    ".unsqueeze(": "tf.expand_dims(",
    ".squeeze(": "tf.squeeze(",
    ".flatten(": "tf.reshape(",
    ".mean(": "tf.reduce_mean(",
    ".sum(": "tf.reduce_sum(",
    ".max(": "tf.reduce_max(",
    ".min(": "tf.reduce_min(",
    ".clamp(": "tf.clip_by_value(",
    ".clip(": "tf.clip_by_value(",
    ".abs()": "tf.abs(",
    ".exp()": "tf.exp(",
    ".log()": "tf.math.log(",
    ".sqrt()": "tf.math.sqrt(",
    ".pow(": "tf.pow(",
    ".float()": "tf.cast(, tf.float32)",
    ".long()": "tf.cast(, tf.int64)",
    ".int()": "tf.cast(, tf.int32)",
    ".half()": "tf.cast(, tf.float16)",
    ".to(": "",  # device ops not needed in TF
    ".cuda()": "",
    ".cpu()": "",
    ".detach()": "tf.stop_gradient(",
    ".item()": ".numpy()",
    ".size(": "tf.shape(",
    ".shape": ".shape",
    ".dim()": "len(.shape)",
    ".repeat(": "tf.tile(",
    ".expand(": "tf.broadcast_to(",
    ".chunk(": "tf.split(",
    ".split(": "tf.split(",
    ".type_as(": "tf.cast(",
    ".masked_fill(": "tf.where(",
    ".fill_(": "tf.fill(",
    ".zero_()": "tf.zeros_like(",
    ".clone()": "tf.identity(",
    ".numpy()": ".numpy()",
}

# ─────────────────────────────────────────────
# Conv parameter mapping
# ─────────────────────────────────────────────

CONV_PARAM_MAP = {
    "in_channels": "filters",  # handled specially: TF uses filters=out_channels
    "out_channels": "filters",
    "kernel_size": "kernel_size",
    "stride": "strides",
    "padding": "padding",
    "dilation": "dilation_rate",
    "groups": "groups",
    "bias": "use_bias",
}

# ─────────────────────────────────────────────
# Weight name transformation rules
# ─────────────────────────────────────────────

WEIGHT_NAME_MAP = {
    "weight": "kernel",
    "bias": "bias",
    "running_mean": "moving_mean",
    "running_var": "moving_variance",
    "num_batches_tracked": None,  # not used in TF
}

# ─────────────────────────────────────────────
# Weight shape transpose rules
# Describes which weight types need transposing and how
# ─────────────────────────────────────────────

WEIGHT_TRANSPOSE_RULES = {
    # Conv2d: PyTorch [out_ch, in_ch, H, W] → TF [H, W, in_ch, out_ch]
    "conv2d": (2, 3, 1, 0),
    # Conv1d: PyTorch [out_ch, in_ch, L] → TF [L, in_ch, out_ch]
    "conv1d": (2, 1, 0),
    # Conv3d: PyTorch [out_ch, in_ch, D, H, W] → TF [D, H, W, in_ch, out_ch]
    "conv3d": (2, 3, 4, 1, 0),
    # ConvTranspose2d: PyTorch [in_ch, out_ch, H, W] → TF [H, W, out_ch, in_ch]
    "conv_transpose2d": (2, 3, 1, 0),
    # Linear: PyTorch [out, in] → TF [in, out]
    "linear": (1, 0),
    # DepthwiseConv2d: PyTorch [ch, 1, H, W] → TF [H, W, ch, 1]
    "depthwise_conv2d": (2, 3, 0, 1),
}

# ─────────────────────────────────────────────
# Padding mode mapping
# ─────────────────────────────────────────────

PADDING_MAP = {
    "zeros": "CONSTANT",
    "constant": "CONSTANT",
    "reflect": "REFLECT",
    "replicate": "SYMMETRIC",
    "circular": "SYMMETRIC",  # approximate
}

# ─────────────────────────────────────────────
# Interpolation mode mapping
# ─────────────────────────────────────────────

INTERPOLATION_MAP = {
    "nearest": "nearest",
    "bilinear": "bilinear",
    "bicubic": "bicubic",
    "trilinear": "bilinear",  # approximate
    "area": "area",
}

# ─────────────────────────────────────────────
# Import replacement mapping
# ─────────────────────────────────────────────

IMPORT_MAP = {
    "import torch": "import tensorflow as tf",
    "import torch.nn as nn": "import tensorflow as tf",
    "import torch.nn.functional as F": "import tensorflow as tf",
    "from torch import nn": "import tensorflow as tf",
    "from torch import Tensor": "import tensorflow as tf",
    "import torchvision": "# torchvision not needed in TF",
    "from torchvision import models": "# torchvision models not needed in TF",
    "from torchvision import transforms": "# Use tf.image for transforms",
}
