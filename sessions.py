"""Discover Claude Code session transcripts and extract the user's own prompts."""
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Harness-injected user records (slash-command echoes, local command output)
# start with one of these tags; they are not prompts the user typed.
WRAPPER_PREFIXES = (
    "<local-command-caveat>",
    "<local-command-stdout>",
    "<local-command-stderr>",
    "<command-name>",
    "<command-message>",
    "<system-reminder>",
)


@dataclass
class Prompt:
    timestamp: str
    text: str


@dataclass
class Session:
    id: str
    path: Path
    title: str
    project: str
    last_timestamp: str
    prompt_count: int
    modified: float  # transcript mtime; Claude Code's cleanup is based on it

    def days_left(self, retention_days: int) -> int:
        age = (datetime.now().timestamp() - self.modified) / 86400
        return max(0, int(retention_days - age))

    @property
    def date_display(self) -> str:
        try:
            dt = datetime.fromisoformat(self.last_timestamp.replace("Z", "+00:00"))
            return dt.astimezone().strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return self.last_timestamp


def _iter_records(path: Path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _prompt_text(record: dict) -> str | None:
    """Return the typed prompt text of a user record, or None if it isn't one."""
    if record.get("type") != "user" or record.get("isMeta") or record.get("isSidechain"):
        return None
    content = (record.get("message") or {}).get("content")
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        content = "\n".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    if not isinstance(content, str):
        return None
    text = content.strip()
    if not text or text.startswith(WRAPPER_PREFIXES):
        return None
    return text


def extract_prompts(path: Path) -> list[Prompt]:
    return [
        Prompt(r.get("timestamp", ""), text)
        for r in _iter_records(path)
        if (text := _prompt_text(r)) is not None
    ]


def _load_session(path: Path) -> Session | None:
    title = last_prompt = project = last_ts = ""
    prompts: list[str] = []
    for r in _iter_records(path):
        rtype = r.get("type")
        if rtype == "ai-title" and r.get("aiTitle"):
            title = r["aiTitle"]
        elif rtype == "last-prompt" and r.get("lastPrompt"):
            last_prompt = r["lastPrompt"]
        if r.get("cwd"):
            project = r["cwd"]
        if r.get("timestamp"):
            last_ts = r["timestamp"]
        if (text := _prompt_text(r)) is not None:
            prompts.append(text)
    if not prompts:
        return None
    if not title:
        title = (last_prompt or prompts[0]).replace("\n", " ")[:60]
    return Session(
        id=path.stem,
        path=path,
        title=title,
        project=Path(project).name if project else path.parent.name,
        last_timestamp=last_ts,
        prompt_count=len(prompts),
        modified=path.stat().st_mtime,
    )


DEFAULT_RETENTION_DAYS = 30


def retention_days(claude_dir: Path) -> int:
    """Claude Code's `cleanupPeriodDays` from <claude_dir>/settings.json (default 30)."""
    try:
        settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
        days = int(settings.get("cleanupPeriodDays", DEFAULT_RETENTION_DAYS))
        return days if days > 0 else DEFAULT_RETENTION_DAYS
    except (OSError, ValueError, TypeError):
        return DEFAULT_RETENTION_DAYS


def list_sessions(sessions_dir: str) -> list[Session]:
    """All sessions with at least one prompt, newest first.

    Only top-level <project>/<session>.jsonl files are read, so subagent
    transcripts stored in nested folders are skipped.
    """
    sessions = []
    for path in Path(sessions_dir).glob("*/*.jsonl"):
        try:
            s = _load_session(path)
        except OSError:
            continue
        if s:
            sessions.append(s)
    sessions.sort(key=lambda s: s.last_timestamp, reverse=True)
    return sessions
