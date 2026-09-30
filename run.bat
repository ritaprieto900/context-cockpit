@echo off
chcp 65001 >nul
title Context Cockpit

echo ========================================================
echo        Starting Context Cockpit (Multi-Agent)
echo ========================================================

REM Run using uv
uv run python -m context_cockpit.cli %*

pause
