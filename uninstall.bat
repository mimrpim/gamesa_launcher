::[Bat To Exe Converter]
::
::fBE1pAF6MU+EWHreyHcjLQlHcAmLMXmqOpEZ++Pv4Pq7tE8Oa/Y6a5vnzLadbuIS/iU=
::YAwzoRdxOk+EWAjk
::fBw5plQjdCyDJGyX8VAjFBZdQRaSAE+1EbsQ5+n//NaSrEQTR/Y+dIOV07eBQA==
::YAwzuBVtJxjWCl3EqQJgSA==
::ZR4luwNxJguZRRnk
::Yhs/ulQjdF+5
::cxAkpRVqdFKZSTk=
::cBs/ulQjdF+5
::ZR41oxFsdFKZSDk=
::eBoioBt6dFKZSDk=
::cRo6pxp7LAbNWATEpCI=
::egkzugNsPRvcWATEpCI=
::dAsiuh18IRvcCxnZtBJQ
::cRYluBh/LU+EWAnk
::YxY4rhs+aU+JeA==
::cxY6rQJ7JhzQF1fEqQJQ
::ZQ05rAF9IBncCkqN+0xwdVs0
::ZQ05rAF9IAHYFVzEqQJQ
::eg0/rx1wNQPfEVWB+kM9LVsJDGQ=
::fBEirQZwNQPfEVWB+kM9LVsJDGQ=
::cRolqwZ3JBvQF1fEqQJQ
::dhA7uBVwLU+EWDk=
::YQ03rBFzNR3SWATElA==
::dhAmsQZ3MwfNWATElA==
::ZQ0/vhVqMQ3MEVWAtB9wSA==
::Zg8zqx1/OA3MEVWAtB9wSA==
::dhA7pRFwIByZRRnk
::YB416Ek+ZW8=
::
::
::978f952a14a936cc963da21a135fa983
@echo off
title uninstaller
call vbs.bat
if %errorlevel% == 2 (
rmdir /S /Q "%appdata%\Godot\app_userdata\Gamesa"
)
if %errorlevel% == 1 (
exit /b 1
)
del /f /q "C:\Users\%username%\Desktop\Gamesa Launcher.lnk"
rmdir /q /s "C:\Users\%username%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Gamesa\Launcher"
for %%I in ("%cd%") do set "currentdir=%%~nxI"
cd ..
echo %currentdir%
pause
start cmd /C rmdir /s /q "%currentdir%"
exit