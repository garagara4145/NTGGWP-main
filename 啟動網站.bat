@echo off
chcp 65001 >nul
echo ============================================
echo   GGWP 開發伺服器啟動中...
echo   啟動後請在瀏覽器打開
echo   要停止伺服器,回到這個視窗按 Ctrl+C
echo ============================================
cd /d "%~dp0myproject"
python manage.py runserver
pause
