"""Remove everything Prompt Analyzer has written to the system, except reports."""
import shutil
from pathlib import Path

import config
from skill_installer import TARGET as SKILL_TARGET


def app_data_dirs() -> list[Path]:
    """Folders delete_app_data removes. Reports are user output and are always kept."""
    return [SKILL_TARGET.parent, config.CONFIG_PATH.parent]


def delete_app_data() -> list[str]:
    """Delete the skill folder and app config. Returns a list of errors (empty on success)."""
    errors = []
    for d in app_data_dirs():
        try:
            if d.exists():
                shutil.rmtree(d)
        except OSError as e:
            errors.append(f"{d}: {e}")
    return errors
