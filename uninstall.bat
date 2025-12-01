::[Bat To Exe Converter]
::
::YAwzoRdxOk+EWAjk
::fBw5plQjdCyDJGyX8VAjFBZdQRaSAE+1EbsQ5+n//NaSrEQTR/Y+dIOV07eBQA==
::YAwzuBVtJxjWCl3EqQJgSA==
::ZR4luwNxJguZRRnk
::Yhs/ulQjdF+5
::cxAkpRVqdFKZSDk=
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
::Zh4grVQjdCyDJGyX8VAjFBZdQRaSAE+/Fb4I5/jH2uSOrF4JVe4zNorD39Q=
::YB416Ek+ZW8=
::
::
::978f952a14a936cc963da21a135fa983
@echo off
del /f /q "C:\Users\%username%\Desktop\Gamesa Launcher.lnk"
del /q /s "%appdata%\Microsoft\Windows\Start Menu\Programs\Startup\icon_taskbar_gamesa_launcher.lnk"
rmdir /q /s "%appdata%\Microsoft\Windows\Start Menu\Programs\Gamesa\"
rmdir /S /Q "%appdata%\Godot\app_userdata\Gamesa"
for %%I in ("%cd%") do set "currentdir=%%~nxI"
cd ..
cmd /C rmdir /s /q "%currentdir%\"
exit /b 0