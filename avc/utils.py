from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


def pretty_print(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def find_project_root(marker_files=("pyproject.toml", ".git")) -> Path:
    path = Path.cwd()
    for parent in [path] + list(path.parents):
        if any((parent / marker).exists() for marker in marker_files):
            return parent
    raise FileNotFoundError("Project root not found")
