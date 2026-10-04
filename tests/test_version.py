from pathlib import Path
import tomllib

import dreadnought


def test_runtime_version_matches_package_metadata() -> None:
    project = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert dreadnought.__version__ == project["version"]
