@echo off
rem Avvia tk-listino dalla pennetta (nessuna installazione). I listini stanno nella cartella "Listini".
rem Aggiornamento interrotto (pennetta tolta, PC spento): se "app" manca si rimette a posto la versione rimasta
rem (prima quella di prima, "app.vecchia", poi quella nuova se e' completa). Niente blocchi tra parentesi:
rem una cartella con le parentesi nel nome li romperebbe.
set "TKD=%~dp0"
if exist "%TKD%app\run.py" goto avvia
if not exist "%TKD%app.vecchia\python\pythonw.exe" goto nuova
if not exist "%TKD%app.vecchia\run.py" goto nuova
if exist "%TKD%app" rmdir /s /q "%TKD%app"
move "%TKD%app.vecchia" "%TKD%app" >nul
goto avvia
:nuova
if not exist "%TKD%app.nuova\python\pythonw.exe" goto avvia
if not exist "%TKD%app.nuova\run.py" goto avvia
if exist "%TKD%app" rmdir /s /q "%TKD%app"
move "%TKD%app.nuova" "%TKD%app" >nul
:avvia
start "" "%TKD%app\python\pythonw.exe" "%TKD%app\run.py" %*
