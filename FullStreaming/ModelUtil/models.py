from ModelUtil.layers import *
from tensorflow.keras import layers, Model

# from data import HR_SIZE

GEN_FILTERS = 64
DISC_FILTERS = 64


def Generator():
    lr_image = layers.Input(shape=(None, None, 3))

    spatial_feats = layers.Lambda(lambda x: x / 255.0)(lr_image)
    spatial_feats = Conv2DBlock(
        filters=GEN_FILTERS, kernel_size=3, strides=1, padding="same", batchnorm=False
    )(spatial_feats)
    spatial_feats = Conv2DBlock(
        filters=GEN_FILTERS, kernel_size=1, strides=1, padding="valid", batchnorm=False
    )(spatial_feats)

    rrdb1 = RRDBlock(GEN_FILTERS)(spatial_feats)
    rrdb2 = RRDBlock(GEN_FILTERS)(rrdb1)
    rrdb3 = RRDBlock(GEN_FILTERS)(rrdb2)
    rrdb4 = RRDBlock(GEN_FILTERS)(rrdb3)

    upsample1 = PixelShuffleUpSampling(GEN_FILTERS * 4, 2)(rrdb4)
    upsample2 = PixelShuffleUpSampling(GEN_FILTERS * 4, 2)(upsample1)

    x = Conv2DBlock(filters=GEN_FILTERS, batchnorm=False)(upsample2)
    x = Conv2DBlock(filters=3, kernel_size=3, activate=False, batchnorm=False)(x)
    x = layers.Activation("tanh")(x)

    sr_image = layers.Lambda(lambda x: (x + 1) * 127.5)(x)

    return Model(inputs=lr_image, outputs=sr_image, name="Generator")
