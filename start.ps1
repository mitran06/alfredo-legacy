# AI Personal Secretary Launcher
# This script sets up the Python path and launches the application

$env:PYTHONPATH = $PSScriptRoot
& "$PSScriptRoot\venv\Scripts\python.exe" "$PSScriptRoot\src\main.py" $args
