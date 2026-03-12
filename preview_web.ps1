$env:PYTHONUTF8 = '1'
Write-Host "启动本地预览服务器: http://localhost:8000"
& "$PSScriptRoot/.venv/Scripts/python.exe" -m http.server 8000 --directory "$PSScriptRoot/build/web"
