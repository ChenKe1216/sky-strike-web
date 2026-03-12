$env:PYTHONUTF8 = '1'
& "$PSScriptRoot/.venv/Scripts/python.exe" -m pygbag --build "$PSScriptRoot/main.py"