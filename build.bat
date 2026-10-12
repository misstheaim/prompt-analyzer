@echo off
rem Builds dist\PromptAnalyzer.exe. Requires: python -m pip install -r requirements.txt pyinstaller
cd /d "%~dp0"
python -m PyInstaller --noconfirm --onefile --windowed --name PromptAnalyzer ^
  --add-data "skill\SKILL.md;skill" --collect-data sv_ttk app.py
