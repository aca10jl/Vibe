from setuptools import setup, find_packages

setup(
    name="pytorch2tensorflow",
    version="1.0.0",
    description="PyTorch to TensorFlow model converter for Huawei Ascend deployment",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.21.0",
    ],
    extras_require={
        "pytorch": ["torch>=1.9.0"],
        "tensorflow": ["tensorflow>=2.10.0"],
        "full": [
            "torch>=1.9.0",
            "tensorflow>=2.10.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pytorch2tensorflow=pytorch2tensorflow.cli:main",
        ],
    },
)
