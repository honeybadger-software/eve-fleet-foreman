@echo off
title EVE Fleet Foreman
cd /d "C:\PythonProjects\eve_foreman"
echo ============================================
echo   EVE Fleet Foreman  -  starting up...
echo   A browser tab will open at:
echo   http://localhost:8088
echo ============================================
echo.
python app.py
echo.
echo (Foreman stopped. Close this window or press a key.)
pause
