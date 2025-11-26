import requests
import json
import sys
import os
import subprocess
import shutil
import argparse
from distutils.version import LooseVersion  # type: ignore
import time

# --- 1. KONFIGURACE (Převzato z původního main.py) ---
# Cesty k souborům a adresářům jsou v EXPANDOVANÉ podobě pro snadné použití.
UNEXPANDED_CONFIG_PATH = "%appdata%/Godot/app_userdata/Gamesa/config_updater.json"
GAME_DIR_PATH = "%appdata%/Godot/app_userdata/Gamesa/game_files"
GAME_EXE_NAME = "gamesa.exe"
RAR_EXE_PATH = "bin/Rar.exe" 
DOWNLOADED_RAR_NAME = "latest_win.rar"
GITHUB_API_URL = "https://api.github.com/repos/mimrpim/Gamesa/releases/latest"
VERSION_KEY = "version"
DEFAULT_VERSION = "0.0.0"
GITHUB_HEADERS = {'Accept': 'application/vnd.github.com'} 

# EXPANDOVANÉ CESTY
LOCAL_SETTINGS_PATH = os.path.expandvars(UNEXPANDED_CONFIG_PATH).replace('\\', '/')
EXPANDED_GAME_DIR = os.path.expandvars(GAME_DIR_PATH).replace('\\', '/')
EXPANDED_GAME_EXE_PATH = os.path.join(EXPANDED_GAME_DIR, GAME_EXE_NAME)

# --- 2. KONZOLOVÉ FUNKCE ---

def cprint(message, level="INFO"):
    """Vylepšený konzolový výpis s časovou značkou a barevným kódem."""
    timestamp = time.strftime("[%H:%M:%S]")
    color_code = {
        "INFO": "\033[94m",    # Modrá
        "SUCCESS": "\033[92m", # Zelená
        "ERROR": "\033[91m",   # Červená
        "WARN": "\033[93m"     # Žlutá
    }.get(level, "\033[0m")
    
    # \033[0m resetuje barvu
    print(f"{timestamp} {color_code}[{level}]\033[0m {message}")

# --- 3. HELPER FUNKCE (Převzato/upraveno z main.py) ---

def _load_local_config():
    """Načte lokální verzi hry z configu."""
    config_data = {}
    version = DEFAULT_VERSION
    try:
        with open(LOCAL_SETTINGS_PATH, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        version = config_data.get(VERSION_KEY, DEFAULT_VERSION)
    except (FileNotFoundError, json.JSONDecodeError):
        # Vrací defaultní verzi a prázdná data, pokud soubor neexistuje nebo je poškozený
        pass 
    return version, config_data

def _save_local_config(version, config_data):
    """Uloží lokální verzi do configu."""
    config_data[VERSION_KEY] = version
    config_dir = os.path.dirname(LOCAL_SETTINGS_PATH)
    try:
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)
        with open(LOCAL_SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        return True
    except IOError as e:
        cprint(f"Chyba při zápisu configu: {e}", "ERROR")
        return False

def _get_remote_data():
    """Získá data o poslední verzi z GitHub API."""
    cprint(f"Kontrola aktualizací na: {GITHUB_API_URL}", "INFO")
    try:
        response = requests.get(GITHUB_API_URL, headers=GITHUB_HEADERS, timeout=10)
        response.raise_for_status() 
        remote_data = response.json()
        
        assets = remote_data.get('assets', [])
        download_url = None
        for asset in assets:
            if asset.get('name') == DOWNLOADED_RAR_NAME:
                download_url = asset.get('url') 
                break
        
        if not download_url:
            cprint(f"Chyba: Asset '{DOWNLOADED_RAR_NAME}' nebyl na GitHubu nalezen. Nelze aktualizovat.", "ERROR")
            return None, None, None

        remote_version = remote_data.get('tag_name', DEFAULT_VERSION)
        return remote_version, download_url, remote_data.get('body', "Changelog není k dispozici.")
        
    except requests.exceptions.RequestException as e:
        cprint(f"Chyba při připojování k GitHub API (bez internetu?): {e}", "ERROR")
        return None, None, None

def download_file(url, save_path):
    """Stáhne soubor z GitHubu."""
    # Používáme 'application/octet-stream' pro stažení assetu z GitHubu
    headers = {'Accept': 'application/octet-stream'}
    cprint(f"Stahování souboru z URL: {url}", "INFO")
    try:
        req = requests.get(url, headers=headers, stream=True) 
        req.raise_for_status() 

        with open(save_path, 'wb') as file:
            # Iterace přes chunk velikosti 8KB pro velké soubory
            for chunk in req.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
        return True
        
    except requests.exceptions.RequestException as e:
        cprint(f"Chyba při stahování souboru: {e}", "ERROR")
        return False

def run_installation(remote_version, download_url):
    """Provede stažení a extrakci souborů."""
    cprint("--- START INSTALACE / UPDATE ---", "INFO")
    
    # 1. Stažení
    if not download_file(download_url, DOWNLOADED_RAR_NAME):
        cprint("Instalace selhala v kroku stahování.", "ERROR")
        return False
        
    # 2. Extrakce
    cprint(f"Extrakce souboru '{DOWNLOADED_RAR_NAME}' do adresáře: {EXPANDED_GAME_DIR}", "INFO")
    try:
        # Bezpečné smazání starého adresáře
        if os.path.exists(EXPANDED_GAME_DIR):
            cprint(f"Mazání starého adresáře: {EXPANDED_GAME_DIR}", "WARN")
            shutil.rmtree(EXPANDED_GAME_DIR, ignore_errors=True)
        os.makedirs(EXPANDED_GAME_DIR, exist_ok=True)
        
        if not os.path.exists(RAR_EXE_PATH):
            cprint(f"Chyba: Rar.exe nebyl nalezen na cestě: {RAR_EXE_PATH}. NELZE EXTRAHOVAT.", "ERROR")
            cprint("Instalace selhala - chybí Rar.exe.", "ERROR")
            return False

        # Spuštění Rar.exe pro extrakci
        rar_command = [RAR_EXE_PATH, 'x', '-y', DOWNLOADED_RAR_NAME, EXPANDED_GAME_DIR]
        # Potřebujeme zachytit výstup Rar.exe, aby nedošlo k problémům s konzolí
        result = subprocess.run(rar_command, capture_output=True, text=True, check=False) 
        
        if result.returncode != 0 and "All OK" not in result.stdout:
            cprint(f"Chyba při extrakci (Rar.exe Code: {result.returncode}).", "ERROR")
            cprint(f"ERROR: {result.stderr.strip()}", "ERROR")
            return False
        else:
            cprint("Extrakce dokončena. Výstup Rar.exe (pokud je):", "INFO")
            # Tiskne jen ty nejdůležitější řádky (typicky se zde zobrazí "All OK")
            print(result.stdout.strip()) 
        
        # Smazání staženého RAR souboru
        if os.path.exists(DOWNLOADED_RAR_NAME):
            os.remove(DOWNLOADED_RAR_NAME)
            
    except Exception as e:
        cprint(f"Neočekávaná chyba při extrakci: {e}", "ERROR")
        return False

    # 3. Uložení verze
    cprint(f"Aktualizace lokální verze na {remote_version}", "INFO")
    _, config_data = _load_local_config()
    if not _save_local_config(remote_version, config_data):
         cprint("Aktualizace verze v configu selhala.", "ERROR")
         return False

    cprint("UPDATE DOKONČEN ÚSPĚŠNĚ!", "SUCCESS")
    return True

def run_game():
    """Spustí hru a čeká na její dokončení."""
    cprint(f"Spouštění hry: {EXPANDED_GAME_EXE_PATH}", "INFO")
    
    if not os.path.exists(EXPANDED_GAME_EXE_PATH):
        cprint(f"Chyba: Spustitelný soubor hry nebyl nalezen: {EXPANDED_GAME_EXE_PATH}", "ERROR")
        return False

    try:
        # Spuštění hry s přesměrováním výstupu do aktuální konzole
        cprint("---------------------------------------", "INFO")
        cprint("--- START VÝSTUPU HRY (Godot Console) ---", "INFO")
        cprint("---------------------------------------", "INFO")
        
        # Spustí hru a nechá ji bežet. Výstup bude v aktuální konzoli.
        process = subprocess.Popen([EXPANDED_GAME_EXE_PATH], 
                                   cwd=EXPANDED_GAME_DIR, 
                                   stdout=sys.stdout, 
                                   stderr=sys.stderr  
                                  )
        
        process.wait() # Čekání, dokud hra neskončí
        
        cprint("---------------------------------------", "INFO")
        cprint("--- KONEC VÝSTUPU HRY ---", "INFO")
        cprint("---------------------------------------", "INFO")
        cprint(f"Hra ukončena s kódem: {process.returncode}", "SUCCESS" if process.returncode == 0 else "WARN")
        return True
        
    except Exception as e:
        cprint(f"Neočekávaná chyba při spouštění hry: {e}", "ERROR")
        return False

# --- 4. HLAVNÍ LOGIKA ---

def main():
    parser = argparse.ArgumentParser(
        description="Gamesa Console Launcher a Updater. Defaultně kontroluje update a spouští hru."
    )
    
    # Definice argumentů
    parser.add_argument(
        '--forceupdate',
        action='store_true',
        help='Vynutí aktualizaci (stažení a instalaci), i když se zdá být aktuální. Poté spustí hru.'
    )
    parser.add_argument(
        '--update_only',
        action='store_true',
        help='Pouze zkontroluje aktualizace a provede update/instalaci. Hru NESPÚŠTÍ.'
    )
    
    args = parser.parse_args()

    # --- Krok 1: Získání verzí a dat ---
    local_version, _ = _load_local_config()
    remote_version, download_url, changelog = _get_remote_data()
    
    cprint("-" * 50, "INFO")
    
    # Kontrola, zda se podařilo získat data z GitHubu
    if remote_version is None or download_url is None:
        cprint("Nelze získat informace o vzdálené verzi (Chyba API/sítě).", "ERROR")
        cprint("Pokračuji pouze se spuštěním lokální hry (pokud existuje).", "WARN")
        
        if not args.update_only and os.path.exists(EXPANDED_GAME_EXE_PATH):
            cprint("Spouštím lokální hru...", "INFO")
            run_game()
        else:
            cprint("Hra nespouštěna (Update je požadován nebo lokální exe neexistuje).", "INFO")
        
        sys.exit(1) # Konec s chybovým kódem, protože update selhal

    # --- Krok 2: Porovnání verzí ---
    
    try:
        # Porovnání LooseVersion je bezpečnější pro schémata jako v0.9.1
        needs_update = LooseVersion(local_version) < LooseVersion(remote_version)
    except Exception:
        needs_update = local_version != remote_version
        
    cprint(f"Lokální verze: {local_version} | Nejnovější verze: {remote_version}", "INFO")
    
    # Je hra nainstalovaná?
    is_installed = os.path.exists(EXPANDED_GAME_EXE_PATH)
    
    # Musíme provést instalaci/update?
    should_install = needs_update or args.forceupdate or not is_installed

    if should_install:
        if args.forceupdate:
            cprint("VYNUCENÝ UPDATE požadován (--forceupdate).", "WARN")
        elif not is_installed:
            cprint("Hra není nainstalována. Nutná instalace.", "WARN")
        else:
            cprint("Nalezena nová verze! Je nutný update.", "WARN")

        # Volitelný tisk Changelogu
        cprint("\n--- CHANGELOG ---", "INFO")
        print(changelog)
        cprint("-----------------", "INFO")
        
    elif not should_install:
        cprint("Hra je aktuální, update není nutný.", "SUCCESS")


    # --- Krok 3: Zpracování Argumentů a Akce ---

    # 1. Režim --update_only (Pouze kontrola a instalace/update)
    if args.update_only:
        cprint("\nRežim: POUZE UPDATE (--update_only)", "INFO")
        if should_install:
            if run_installation(remote_version, download_url):
                cprint("Update/Instalace dokončena. Hra NENÍ spuštěna.", "SUCCESS")
                sys.exit(0)
            else:
                cprint("Update/Instalace selhala.", "ERROR")
                sys.exit(1)
        else:
            cprint("Update není nutný. Hra NENÍ spuštěna.", "SUCCESS")
            sys.exit(0)

    # 2. Režim --forceupdate A Defaultní režim (Vždy spustit hru)
    cprint("\nRežim: Update A SPUŠTĚNÍ", "INFO")
    
    if should_install:
        cprint("Spouštím instalaci/update před spuštěním hry.", "INFO")
        if not run_installation(remote_version, download_url):
            cprint("Update selhal. Pokouším se spustit starou verzi, pokud existuje.", "ERROR")
            # Pokud update selhal, pokusíme se spustit starou verzi
            if os.path.exists(EXPANDED_GAME_EXE_PATH):
                cprint("Spouštím starou verzi...", "WARN")
                run_game()
            else:
                cprint("Spuštění přeskočeno - hra není nainstalována.", "ERROR")
                sys.exit(1) # Konec s chybou
        else:
            # Update proběhl, spouštíme novou verzi
            run_game()
    else:
        # Update není nutný, spouštíme hru
        run_game()
        
    cprint("Skript dokončil běh.", "INFO")
    sys.exit(0)


if __name__ == "__main__":
    # Nastavení pro podporu barev v konzoli na Windows 10/11
    if sys.platform == "win32":
        try:
            # Povolení ANSI escape sekvencí
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7) 
        except Exception:
            pass
            
    try:
        # Rychlá kontrola závislostí
        import requests 
        from distutils.version import LooseVersion # pyright: ignore
    except ImportError as e:
        print(f"Chybí požadovaný balíček: {e.name}. Nainstalujte jej pomocí 'pip install requests setuptools'.")
        sys.exit(1)
        
    # Spuštění hlavní funkce
    main()