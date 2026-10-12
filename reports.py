"""List and manage generated reports (*.md) in the reports folder."""
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Name produced by analyzer.run_analysis: YYYY-MM-DD_HHMMSS_prompt-review.md
DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})(\d{2})?")
SCORE = re.compile(r"\*\*Overall score:\s*(\d+(?:\.\d+)?)\s*/\s*10")
INVALID_NAME_CHARS = set('<>:"/\\|?*')


@dataclass
class Report:
    path: Path
    created: datetime
    size: int
    score: float | None

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def date_display(self) -> str:
        return self.created.strftime("%Y-%m-%d %H:%M")

    @property
    def size_display(self) -> str:
        return f"{self.size / 1024:.1f} KB" if self.size >= 1024 else f"{self.size} B"

    @property
    def score_display(self) -> str:
        if self.score is None:
            return "—"
        return f"{self.score:g}/10"


def _created(path: Path) -> datetime:
    """Date from the file name if it has our prefix (survives renames that keep it), else mtime."""
    if m := DATE_PREFIX.match(path.name):
        try:
            return datetime.strptime(
                f"{m[1]} {m[2]}{m[3]}{m[4] or '00'}", "%Y-%m-%d %H%M%S")
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime)


def _score(path: Path) -> float | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            head = f.read(4096)  # the summary is at the top of the report
    except OSError:
        return None
    m = SCORE.search(head)
    return float(m[1]) if m else None


def list_reports(reports_dir: Path) -> list[Report]:
    """All .md files in the reports folder, newest first. Renamed reports are included too."""
    if not reports_dir.is_dir():
        return []
    reports = []
    for p in reports_dir.glob("*.md"):
        try:
            reports.append(Report(p, _created(p), p.stat().st_size, _score(p)))
        except OSError:
            continue
    reports.sort(key=lambda r: r.created, reverse=True)
    return reports


def validate_name(new_name: str, current: Path) -> str | None:
    """Return an error message for a proposed report name (without .md), or None if OK."""
    name = new_name.strip()
    if not name:
        return "Name cannot be empty."
    if any(c in INVALID_NAME_CHARS for c in name):
        return 'Name cannot contain any of: < > : " / \\ | ? *'
    if name.endswith((".", " ")):
        return "Name cannot end with a dot or a space."
    target = current.with_name(name + ".md")
    if target.exists() and target.resolve() != current.resolve():
        return "A report with this name already exists."
    return None


def rename_report(path: Path, new_name: str) -> Path:
    target = path.with_name(new_name.strip() + ".md")
    path.rename(target)
    return target


def delete_reports(paths: list[Path]) -> list[str]:
    """Delete the given report files (explicit user action only). Returns errors."""
    errors = []
    for p in paths:
        try:
            p.unlink()
        except OSError as e:
            errors.append(f"{p.name}: {e}")
    return errors
