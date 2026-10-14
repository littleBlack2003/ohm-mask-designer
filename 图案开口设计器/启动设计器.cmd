@echo off
python -X utf8 -B "%~dp0launch.py"
if errorlevel 1 pause
