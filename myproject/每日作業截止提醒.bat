@echo off
chcp 65001 >nul
cd /d "%~dp0"
C:\Python312\python.exe manage.py send_assignment_deadline_reminders --hours 24 >> "%~dp0assignment_reminders.log" 2>&1
