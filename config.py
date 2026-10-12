"""Persistent app settings stored in %APPDATA%\\PromptAnalyzer\\config.json."""
import json
import os
import shutil
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("APPDATA", Path.home())) / "PromptAnalyzer" / "config.json"
REPORTS_SUBDIR = "reports"

PATH_FIELDS = ("sessions_dir", "reports_base", "claude_path")


def _documents_dir() -> Path:
    """The user's Documents folder, following redirection (e.g. to OneDrive)."""
    if os.name == "nt":
        import ctypes
        # FOLDERID_Documents {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
        guid = (ctypes.c_byte * 16)(*bytes.fromhex("d09ad3fd8f23af46adb46c85480369c7"))
        buf = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(guid, 0, None, ctypes.byref(buf)) == 0:
            path = buf.value
            ctypes.windll.ole32.CoTaskMemFree(buf)
            return Path(path)
    return Path.home() / "Documents"


def defaults() -> dict:
    return {
        "sessions_dir": str(Path.home() / ".claude" / "projects"),
        "reports_base": str(_documents_dir()),
        "claude_path": shutil.which("claude") or "",
        "favorites": [],
        "skill_prompt_answered": False,
    }


def exists() -> bool:
    return CONFIG_PATH.is_file()


def load() -> dict:
    cfg = defaults()
    if CONFIG_PATH.is_file():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
    return cfg


def save(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def validate(values: dict) -> dict[str, str]:
    """Return {field: error message} for every invalid path field."""
    errors = {}
    if not Path(values.get("sessions_dir", "")).is_dir():
        errors["sessions_dir"] = "Folder does not exist."
    if not Path(values.get("reports_base", "")).is_dir():
        errors["reports_base"] = "Folder does not exist (only the 'reports' subfolder is created automatically)."
    claude = values.get("claude_path", "")
    if not claude or not Path(claude).is_file():
        errors["claude_path"] = "claude.exe not found. Is Claude Code installed?"
    return errors


def reports_dir(cfg: dict) -> Path:
    return Path(cfg["reports_base"]) / REPORTS_SUBDIR


def ensure_reports_dir(cfg: dict) -> Path:
    path = reports_dir(cfg)
    path.mkdir(exist_ok=True)
    return path
