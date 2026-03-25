"""
PyTorch to TensorFlow Converter
================================

A comprehensive tool for converting PyTorch CV models to TensorFlow,
including model architecture conversion, weight migration, accuracy
validation, and PB model export for Huawei Ascend (昇腾) deployment.

Main components:
    - ModelConverter: Convert PyTorch model .py files to TensorFlow/Keras
    - WeightConverter: Convert .pth weights to TensorFlow-compatible format
    - AccuracyValidator: Validate output consistency between frameworks
    - PBExporter: Export TF models to PB format for Ascend platform
"""

__version__ = "1.0.0"

from pytorch2tensorflow.layer_mapping import LAYER_MAP, ACTIVATION_MAP
from pytorch2tensorflow.converter import ModelConverter
from pytorch2tensorflow.weight_converter import WeightConverter
from pytorch2tensorflow.validator import AccuracyValidator
from pytorch2tensorflow.exporter import PBExporter
from pytorch2tensorflow.auto_convert import auto_convert

__all__ = [
    "ModelConverter",
    "WeightConverter",
    "AccuracyValidator",
    "PBExporter",
    "auto_convert",
    "LAYER_MAP",
    "ACTIVATION_MAP",
]
