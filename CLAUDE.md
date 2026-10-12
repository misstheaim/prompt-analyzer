# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Prompt Analyzer is a small Windows Tkinter app for personal use. It lists the user's Claude Code sessions in two tabs, **All sessions** and **Favorites**. It takes the user's own prompts from the selected sessions and runs a headless `claude -p` session with the `/prompt-review` skill. That session's stdout is saved as a Markdown report.

Python 3.12+ (developed on 3.14 / Tk 9.0). The only runtime dependency is `sv-ttk` (dark theme), listed in `requirements.txt`.

## Commands

- Install dependencies: `python -m pip install -r requirements.txt`.
- Run (dev): `run.bat`, or `python app.py`.
- Build the distributable exe: `build.bat`. It needs `pyinstaller` as well and produces `dist\PromptAnalyzer.exe` with `skill\SKILL.md` and sv-ttk's theme files bundled (`--collect-data sv_ttk`).
- Quick parser check: `python -c "import sessions; [print(s) for s in sessions.list_sessions(r'%USERPROFILE%\.claude\projects')]"`

There is no test suite.

## Architecture

- `sessions.py` parses Claude Code transcripts at `<sessions_dir>\<project-slug>\<session-id>.jsonl`, one JSON record per line.
  - **A user prompt** is a record with `type:"user"`, no `isMeta`, no `isSidechain`, and no `tool_result` blocks, whose text does not start with a harness wrapper tag (`WRAPPER_PREFIXES`).
  - **The title** is the last `ai-title` record. The fallback is the `last-prompt` record, then the first prompt.
  - Only top-level `*/*.jsonl` files are read, so subagent transcripts in nested folders are skipped.
  - "Expires in" = `cleanupPeriodDays` minus the transcript file's age since last modification. Claude Code deletes transcripts based on that mtime. `cleanupPeriodDays` is read from `settings.json` in the parent of the sessions folder (normally `~\.claude`), with a default of 30.
- `analyzer.py` sends `/prompt-review\n\n<prompts as markdown>` on stdin to `claude -p --no-session-persistence --disallowedTools …`.
  - `--no-session-persistence` keeps analysis runs out of the session list.
  - Text after the slash command becomes `$ARGUMENTS` in the skill.
- `config.py` stores settings in `%APPDATA%\PromptAnalyzer\config.json`: the sessions folder, the reports base, the claude path, favorites, and whether the user has been asked about the skill. Defaults come from env vars so the app works on other machines.
  - Validation requires every configured path to already exist.
  - The `reports` subfolder under the reports base (default: the user's Documents known folder, resolved via `SHGetKnownFolderPath` so OneDrive redirection is respected) is the only folder the app creates.
- `skill_installer.py` copies the bundled `skill\SKILL.md` to `~\.claude\skills\prompt-review\SKILL.md`, but only after asking on first run or when the user clicks Install in Settings.
  - When running as a frozen exe, the bundled file is read from `sys._MEIPASS`.
- `skill\SKILL.md` is the review rubric and report format. It intentionally has **no `description`** and sets `disable-model-invocation: true`, so it adds nothing to context in the user's normal sessions. Keep it that way.
- `cleanup.py` backs the "Delete all app data" button. It removes the skill folder and `%APPDATA%\PromptAnalyzer`. It must **never delete reports** (a user requirement), and it never touches Claude Code's own settings or sessions.
- `reports.py` and `reports_tab.py` implement the Reports tab. It lists **all** `*.md` files in `<reports_base>\reports`, not just `*_prompt-review.md`, so renamed reports still appear.
  - The date comes from the `YYYY-MM-DD_HHMMSS` file-name prefix, falling back to the file's modification time.
  - The score is parsed from `**Overall score: N/10**` in the first 4 KB.
  - Deleting a report there is an explicit user action that always asks for confirmation. This is allowed; only the "Delete all app data" cleanup must never touch reports.
- `md_preview.py` renders Markdown into a `tk.Text` using tags. It deliberately supports only what `skill/SKILL.md` reports use: headings, bold/italic/code/links, lists, `>` quotes at line start, fenced code and `---`. If the report format in the skill changes, check that the renderer still covers it.
- `ui_common.py` holds the shared theme colors and window helpers (`apply_theme`, `enable_dpi_awareness`, `scaled`, `center`, `dark_title_bar`). Use them for any new window.
- `app.py` is the main window. Its tabs, in order, are All sessions, Favorites, Reports (`REPORTS_TAB`) and Settings (`SETTINGS_TAB`). The session button bar is hidden on the Reports and Settings tabs, and the status bar is shared by all tabs.
  - `SettingsForm` holds the path fields, the skill status and validation. It is shared by the first-run `SettingsDialog` and the Settings tab. The window is about 30% of the screen.
  - The first run shows the settings dialog, then the skill-install prompt.
  - Analysis runs on a worker thread, and its result comes back through a `queue` polled with `root.after`.
  - Theme: `apply_theme` (in `ui_common.py`) calls `sv_ttk.set_theme("dark")` and then explicitly runs sv-ttk's Tcl `configure_colors`. sv-ttk normally runs that from a `<<ThemeChanged>>` binding, which Tk 9 doesn't deliver; without it, frame backgrounds stay light. Colors are tuned for dark: `MUTED_FG` and `ERROR_FG`. Primary buttons use `Accent.TButton`.
  - The process is DPI-aware (`SetProcessDpiAwareness`), so pixel sizes are physical. Wrap fixed sizes in `scaled()`. Title bars are made dark with `DwmSetWindowAttribute` (`dark_title_bar`).
