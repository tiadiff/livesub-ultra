@echo off
echo [INFO] Installazione PyInstaller...
.\venv\Scripts\pip.exe install pyinstaller

echo [INFO] Creazione dell'eseguibile LiveSub Ultra...
echo [ATTENZIONE] Questa operazione puo richiedere diversi minuti e molta RAM.
.\venv\Scripts\pyinstaller --noconsole --onefile --name "LiveSubUltra" --collect-all nvidia main.py

echo.
echo [OK] Operazione completata! Troverai 'LiveSubUltra.exe' nella cartella 'dist'.
pause
