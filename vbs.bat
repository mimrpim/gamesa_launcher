::[Bat To Exe Converter]
::
::YAwzoRdxOk+EWAnk
::fBw5plQjdG8=
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
::YB416Ek+ZW8=
::
::
::978f952a14a936cc963da21a135fa983
@echo off
:: Vytvoříme unikátní název souboru s cestou do dočasné složky Windows, což nevyžaduje oprávnění správce
set "tempVBS=%TEMP%\tempDialog_%RANDOM%.vbs"

:: Vytvoření VBScript souboru
echo WScript.Quit MsgBox("Chceš pokračovat?", 36, "Potvrzení volby") > "%tempVBS%"
:: 36 = ikonka otazníku (32) + Ano/Ne tlačítka (4)

:: Spuštění VBScriptu a zachycení návratové hodnoty (ExitCode)
cscript //nologo "%tempVBS%"
set "VBS_RESULT=%ERRORLEVEL%"

:: Smazání dočasného VBScript souboru
del "%tempVBS%"

:: Podmínky pro nastavení finálního ErrorLevelu
:: VBScript vrací: 6 pro Ano, 7 pro Ne

if "%VBS_RESULT%"=="6" (
    :: Uživatel zvolil "Ano" -> ErrorLevel 2
    set errorlevel = 2
)

if "%VBS_RESULT%"=="7" (
    :: Uživatel zvolil "Ne" -> ErrorLevel 3
    set errorlevel = 3
) else (
set errorlevel = 1
)
pause