# Prompt Analyzer

A small Windows desktop app that reviews the prompts you write to [Claude Code](https://claude.ai/code) and tells you how to write better ones.

It reads your saved Claude Code sessions, takes only the messages **you** typed, and sends them to a headless Claude Code run with a built-in review skill. The result is a Markdown report with scores, strengths and weaknesses, recurring habits, and before/after rewrites of your real prompts.

## Features

- **Session browser.** All your Claude Code sessions are listed by title, project, last activity, and how many days remain before Claude Code deletes them. Sessions with 7 days or fewer left are shown in red.
- **Favorites tab.** Double-click the ★ column, or use **☆ Toggle favorite**, to keep important sessions in a separate tab.
- **One-click analysis.** Select one or more sessions and click **Analyze**. Claude Code runs in the background with no console window and closes when it's done. The new report appears in the **Reports** tab; nothing opens automatically.
- **Report contents:**
  1. Summary and overall score (1–10)
  2. Per-session review, with a rating for each prompt
  3. Recurring patterns: good habits and habits to change
  4. Suggestions, with before/after rewrites (only if there are issues)
- **Reports tab.** Lists every report with date, name, overall score and size.
  - Sort by clicking a column header, and type in the filter box to narrow the list.
  - **Preview** (or double-click / Enter) shows the report as formatted Markdown in its own dark window. You can open several previews side by side. The preview window has **Copy** and **Open externally** buttons.
  - **Open** uses your default `.md` app, and **Show in folder** opens Explorer with the file selected.
  - **Rename…** (F2) and **Delete…** (Del, always asks first) manage the files. Right-click a report for the same actions.
- **Settings tab.** Change the sessions folder, the reports location and the path to `claude.exe`. Every path is checked before saving. **Restore defaults** refills the form with the original values.
- **Clean removal.** **Delete all app data…** removes the skill and the app's settings after you confirm. Your reports are always kept.

## Requirements

- Windows 10/11
- [Claude Code](https://claude.ai/code) installed and logged in (`claude` command available)
- To run from source: Python 3.12+ with tkinter, plus `python -m pip install -r requirements.txt`, which installs the [sv-ttk](https://github.com/rdbende/Sun-Valley-ttk-theme) dark theme.

## Getting started

Run from source:

```bat
run.bat
```

Or build a standalone executable (needs `python -m pip install -r requirements.txt pyinstaller`):

```bat
build.bat
```

This produces `dist\PromptAnalyzer.exe`, which runs without Python installed.

### First start

1. A settings window shows the default locations. Change them if needed, then click **OK**.

   | Setting | Default |
   |---|---|
   | Claude sessions folder | `%USERPROFILE%\.claude\projects` |
   | Reports location | your Documents folder, e.g. `C:\Users\<you>\Documents` (a `reports` subfolder is created automatically) |
   | claude.exe | found on `PATH` |

2. The app asks for permission to install the **prompt-review** skill into `%USERPROFILE%\.claude\skills\prompt-review\`. The skill has no description, so it adds nothing to Claude's context in your normal sessions. It only runs when the app calls `/prompt-review`. If you decline, Analyze stays disabled until you install the skill from the Settings tab.

## Where things are stored

| What | Location | Removed by "Delete all app data" |
|---|---|---|
| Review skill | `%USERPROFILE%\.claude\skills\prompt-review\` | Yes |
| App settings and favorites | `%APPDATA%\PromptAnalyzer\config.json` | Yes |
| Reports | `<reports location>\reports\*_prompt-review.md` | **No, always kept** |

## How session expiry works

By default, Claude Code deletes session transcripts 30 days after their last activity. You can change this with `cleanupPeriodDays` in `%USERPROFILE%\.claude\settings.json`, for example `"cleanupPeriodDays": 90`. The **Expires in** column reads that value. Analysis runs use `--no-session-persistence`, so they never add sessions of their own.

## Project structure

| File | Purpose |
|---|---|
| `app.py` | Main window: session tabs, Settings tab, first-run setup, analysis thread |
| `reports_tab.py` | Reports tab: list, sort, filter, preview, open, rename, delete |
| `reports.py` | Report file logic: listing, score parsing, name validation, rename and delete |
| `md_preview.py` | Preview window with a small Markdown renderer (Tk text tags, no extra dependencies) |
| `ui_common.py` | Theme colors and window helpers (dark theme, DPI scaling, dark title bar) |
| `sessions.py` | Finds session transcripts, extracts user prompts, computes days left |
| `analyzer.py` | Builds the review input and runs `claude -p /prompt-review` |
| `config.py` | Settings defaults, load/save, path validation |
| `skill_installer.py` | Installs the bundled skill |
| `skill/SKILL.md` | The review rubric and report format |
| `cleanup.py` | "Delete all app data" (never touches reports) |
| `run.bat` / `build.bat` | Run from source / build the exe |
| `assets/icon.ico`, `assets/icon.png` | App icon, used for the windows, the taskbar and the exe |
| `tools/make_icon.py` | Regenerates the icon (dev-only; needs `pip install pillow`) |
