"""Install the bundled prompt-review skill into the user's ~/.claude/skills."""
import shutil
import sys
from pathlib import Path

SKILL_NAME = "prompt-review"
TARGET = Path.home() / ".claude" / "skills" / SKILL_NAME / "SKILL.md"


def _bundled_skill() -> Path:
    # PyInstaller unpacks --add-data files under sys._MEIPASS.
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "skill" / "SKILL.md"


def skill_installed() -> bool:
    return TARGET.is_file()


def install_skill() -> Path:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_bundled_skill(), TARGET)
    return TARGET
