import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import data  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def dataset():
    if not data.MANIFEST.exists():
        data.make_dataset()
    return data.MANIFEST


@pytest.fixture(scope="session")
def baseline_config():
    return yaml.safe_load((ROOT / "configs" / "algo" / "baseline.yaml").read_text())


@pytest.fixture(scope="session")
def tuner_cfg():
    return yaml.safe_load((ROOT / "configs" / "tuner.yaml").read_text())
