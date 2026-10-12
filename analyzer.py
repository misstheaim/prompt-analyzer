"""Run a headless Claude Code session that reviews the selected sessions' prompts."""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import config
from sessions import Session, extract_prompts
from skill_installer import SKILL_NAME

MAX_PROMPT_CHARS = 6000
TIMEOUT_SECONDS = 15 * 60

# The review only needs to read the prompts it is given; block anything that
# could change files or reach out. -p mode can't ask for permission anyway.
DISALLOWED_TOOLS = [
    "Bash", "PowerShell", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch", "Agent",
]


class AnalysisError(Exception):
    pass


def build_input(sessions: list[Session]) -> str:
    parts = []
    for s in sessions:
        parts.append(f"## Session: {s.title} ({s.project}, {s.date_display})\n")
        for i, p in enumerate(extract_prompts(s.path), 1):
            text = p.text
            if len(text) > MAX_PROMPT_CHARS:
                text = text[:MAX_PROMPT_CHARS] + "\n[…truncated]"
            parts.append(f"### Prompt {i}\n{text}\n")
    return "\n".join(parts)


def run_analysis(sessions: list[Session], cfg: dict) -> Path:
    """Run the review and return the path of the saved report."""
    stdin = f"/{SKILL_NAME}\n\n{build_input(sessions)}"
    cmd = [
        cfg["claude_path"], "-p",
        "--no-session-persistence",
        "--output-format", "text",
        "--disallowedTools", *DISALLOWED_TOOLS,
    ]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        result = subprocess.run(
            cmd,
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            creationflags=flags,
        )
    except subprocess.TimeoutExpired:
        raise AnalysisError(f"Claude did not finish within {TIMEOUT_SECONDS // 60} minutes.")
    except OSError as e:
        raise AnalysisError(f"Could not start Claude Code: {e}")

    report = result.stdout.strip()
    if result.returncode != 0 or not report:
        detail = result.stderr.strip() or report or "no output"
        raise AnalysisError(f"Claude exited with code {result.returncode}:\n{detail}")

    out_dir = config.ensure_reports_dir(cfg)
    out_path = out_dir / f"{datetime.now():%Y-%m-%d_%H%M%S}_prompt-review.md"
    out_path.write_text(report + "\n", encoding="utf-8")
    return out_path
