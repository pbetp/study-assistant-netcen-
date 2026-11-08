@echo off
rem Shortcuts:
rem   .\ask udp                  one search
rem   .\ask                      keep asking; the model loads once, then every search is instant
rem Runs the slide finder with the project's own .venv, from the project folder.
cd /d "%~dp0"
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
".venv\Scripts\python.exe" -m app.cli find %*
