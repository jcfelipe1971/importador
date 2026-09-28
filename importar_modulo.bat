@echo off
rem Importa un módulo de Merge (Delphi 6) en Merge13 (Delphi 13).
rem Uso:  importar_modulo.bat UFMFamilias
rem Requisitos: Python 3.10+  y  pip install firebird-driver
rem Ajustar las rutas a vuestro equipo:
set MERGE=C:\Delfos\Proyectos\Merge
set PROYECTO=%~dp0Merge13
set MAXFACTU=C:\Delfos\Proyectos\maxfactu
set BD=localhost:C:\Datos\ARMTEX-DEMO.FDB
set FBCLIENT=C:\Program Files\Firebird\Firebird_5_0\fbclient.dll

python "%~dp0importador\merge2m13.py" --merge %MERGE% --proyecto "%PROYECTO%" --maxfactu %MAXFACTU% --modulo %1 --bd %BD% --fbclient "%FBCLIENT%" --sin-teechart
if errorlevel 1 goto fin
cd /d "%PROYECTO%"
call compila.bat
:fin
