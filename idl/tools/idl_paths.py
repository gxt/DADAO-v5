"""IDL 工具的仓库路径真源（`idl/tools/*.py` 同深度：`tools → idl → 仓库根`）。"""
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
IDL = TOOLS.parent
REPO = IDL.parent
DATA = IDL / "data"
DOCS = IDL / "docs"
