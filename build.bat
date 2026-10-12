@echo off
rem Builds dist\PromptAnalyzer.exe. Requires: python -m pip install -r requirements.txt pyinstaller
cd /d "%~dp0"
python -m PyInstaller --noconfirm --onefile --windowed --name PromptAnalyzer ^
  --icon assets\icon.ico ^
  --add-data "skill\SKILL.md;skill" --add-data "assets\icon.ico;assets" ^
  --collect-data sv_ttk app.py
