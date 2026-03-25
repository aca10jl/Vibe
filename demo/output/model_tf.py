"""
PyTorch UNet Model for Semantic Segmentation

A standard UNet architecture with:
    - Encoder: 4 down-sampling blocks (Conv → BN → ReLU → MaxPool)
    - Bottleneck: Double convolution block
    - Decoder: 4 up-sampling blocks (ConvTranspose → Concat → Conv → BN → ReLU)
    - Output: 1x1 Conv for class prediction
"""

import tensorflow as tf


def _pt_padding_to_tf(padding, ndim=4, channels_first=False):
    """Convert PyTorch flat padding to TensorFlow nested padding at runtime.

    PyTorch padding is a flat tuple: (left, right, top, bottom[, front, back])
    from innermost dim to outermost dim.
    TF padding is nested: [[before_0, after_0], [before_1, after_1], ...]
    for each dimension (NHWC or NCHW).
    """
    import tensorflow as tf
    if isinstance(padding, (int, float)):
        padding = (int(padding), int(padding))
    padding = list(padding)
    n_pad_dims = len(padding) // 2
    # Build pairs: [(left, right), (top, bottom), ...]
    pairs = [[padding[2 * i], padding[2 * i + 1]] for i in range(n_pad_dims)]
    # Reverse order: PyTorch pads from innermost to outermost
    pairs = pairs[::-1]
    # Build full padding for each dim (ndim dimensions)
    full = [[0, 0] for _ in range(ndim)]
    if channels_first:
        # NCHW: spatial dims are [2, 3, ...] from the end
        for i, pair in enumerate(pairs):
            dim_idx = ndim - 1 - i  # innermost spatial dim first
            full[dim_idx] = pair
    else:
        # NHWC: spatial dims are [1, 2, ...] (skip batch), channel is last
        for i, pair in enumerate(pairs):
            dim_idx = ndim - 2 - i  # skip last (channel) dim
            full[dim_idx] = pair
    return tf.constant(full, dtype=tf.int32)


# NOTE: This model uses data_format='channels_first' (NCHW),
# matching the original PyTorch dimension ordering.
# Input tensors should be in NCHW format (batch, channels, height, width).


class DoubleConv(tf.keras.Model):
    """Double convolution block: (Conv2d → BN → ReLU) × 2"""

    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv1 = tf.keras.layers.Conv2D(out_channels, kernel_size=3, padding='same', use_bias=False, data_format='channels_first')
        self.bn1 = tf.keras.layers.BatchNormalization(axis=1)
        self.conv2 = tf.keras.layers.Conv2D(out_channels, kernel_size=3, padding='same', use_bias=False, data_format='channels_first')
        self.bn2 = tf.keras.layers.BatchNormalization(axis=1)

    def call(self, x, training=False):
        x = tf.nn.relu(self.bn1(self.conv1(x)))
        x = tf.nn.relu(self.bn2(self.conv2(x)))
        return x


class Down(tf.keras.Model):
    """Downscaling block: MaxPool → DoubleConv"""

    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.pool = tf.keras.layers.MaxPool2D(pool_size=2, data_format='channels_first')
        self.conv = DoubleConv(in_channels, out_channels)

    def call(self, x, training=False):
        x = self.pool(x)
        x = self.conv(x)
        return x


class Up(tf.keras.Model):
    """Upscaling block: ConvTranspose2d → Concat → DoubleConv"""

    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.up = tf.keras.layers.Conv2DTranspose(in_channels // 2, kernel_size=2, strides=2, data_format='channels_first')
        self.conv = DoubleConv(in_channels, out_channels)

    def call(self, x1, x2, training=False):
        x1 = self.up(x1)

        # Pad x1 to match x2 spatial dimensions if needed
        diff_y = x2.shape[2] - x1.shape[2]
        diff_x = x2.shape[3] - x1.shape[3]
        x1 = tf.pad(x1, _pt_padding_to_tf((diff_x // 2, diff_x - diff_x // 2,
                         diff_y // 2, diff_y - diff_y // 2), len(x1.shape), channels_first=True))

        x = tf.concat([x2, x1], axis=1)
        x = self.conv(x)
        return x


class UNet(tf.keras.Model):
    """UNet for semantic segmentation.

    Args:
        in_channels: Number of input channels (e.g. 3 for RGB).
        num_classes: Number of output segmentation classes.
        base_features: Number of features in the first encoder layer.
    """

    def __init__(self, in_channels=3, num_classes=2, base_features=32):
        super().__init__()

        # Encoder
        self.inc = DoubleConv(in_channels, base_features)
        self.down1 = Down(base_features, base_features * 2)
        self.down2 = Down(base_features * 2, base_features * 4)
        self.down3 = Down(base_features * 4, base_features * 8)
        self.down4 = Down(base_features * 8, base_features * 16)

        # Decoder
        self.up1 = Up(base_features * 16, base_features * 8)
        self.up2 = Up(base_features * 8, base_features * 4)
        self.up3 = Up(base_features * 4, base_features * 2)
        self.up4 = Up(base_features * 2, base_features)

        # Output
        self.outc = tf.keras.layers.Conv2D(num_classes, kernel_size=1, data_format='channels_first')

    def call(self, x, training=False):
        # Encoder path
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)

        # Decoder path
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)

        # Output
        x = self.outc(x)
        return x


if __name__ == "__main__":
    model = UNet(in_channels=3, num_classes=2, base_features=32)
    x = tf.random.normal(1, 3, 256, 256)
    y = model(x)
    print(f"Input shape:  {x.shape}")
    print(f"Output shape: {y.shape}")
    print(f"Parameters:   {sum(tf.size(p) for p in model.trainable_variables):,}")
