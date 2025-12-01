import requests
import json
import sys
import os
import subprocess
import shutil
import argparse
from distutils.version import LooseVersion  # type: ignore
import time

# --- 1. CONFIGURATION (Taken from original main.py) ---
# File and directory paths are in EXPANDED form for easy use.
UNEXPANDED_CONFIG_PATH = "%appdata%/Godot/app_userdata/Gamesa/config_updater.json"
GAME_DIR_PATH = "%appdata%/Godot/app_userdata/Gamesa/game_files"
GAME_EXE_NAME = "gamesa.exe"
RAR_EXE_PATH = "bin/Rar.exe" 
# ZDE JE NASTAVENO JMENO SOUBORU, KTERÝ SE STAHUJE Z GITHUB RELEASE
DOWNLOADED_RAR_NAME = "latest_win.rar" 

# EXPANDED PATHS (for Windows AppData structure)
LOCAL_SETTINGS_PATH = os.path.expandvars(UNEXPANDED_CONFIG_PATH).replace('\\', '/')
EXPANDED_GAME_DIR = os.path.expandvars(GAME_DIR_PATH).replace('\\', '/')
EXPANDED_GAME_EXE_PATH = os.path.join(EXPANDED_GAME_DIR, GAME_EXE_NAME)

# NOVÁ CESTA KE STAŽENÉMU RAR SOUBORU
# Bude v %appdata%/Godot/app_userdata/Gamesa/game_files/latest_win.rar
DOWNLOADED_RAR_PATH = os.path.join(EXPANDED_GAME_DIR, DOWNLOADED_RAR_NAME)


GITHUB_API_URL = "https://api.github.com/repos/mimrpim/Gamesa/releases/latest"
VERSION_KEY = "version"
DEFAULT_VERSION = "0.0.0"
GITHUB_HEADERS = {'Accept': 'application/vnd.github.com'} 


# --- 2. KONZOLOVÉ FUNKCE ---

def cprint(message, level="INFO"):
    """Enhanced console output with timestamp and color coding."""
    timestamp = time.strftime("[%H:%M:%S]")
    color_code = {
        "INFO": "\033[94m", 	# Blue
        "SUCCESS": "\033[92m", # Green
        "ERROR": "\033[91m", 	# Red
        "WARN": "\033[93m" 	# Yellow
    }.get(level, "\033[0m")
    
    # \033[0m resets the color
    print(f"{timestamp} {color_code}[{level}]\033[0m {message}")

# --- 3. HELPER FUNCTIONS ---

def _load_local_config():
    """Loads the local game version from config."""
    config_data = {}
    version = DEFAULT_VERSION
    try:
        with open(LOCAL_SETTINGS_PATH, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        version = config_data.get(VERSION_KEY, DEFAULT_VERSION)
    except (FileNotFoundError, json.JSONDecodeError):
        # Returns default version and empty data if file doesn't exist or is corrupted
        pass 
    return version, config_data

def _save_local_config(version, config_data):
    """Saves the local version to config."""
    config_data[VERSION_KEY] = version
    config_dir = os.path.dirname(LOCAL_SETTINGS_PATH)
    try:
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)
        with open(LOCAL_SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        return True
    except IOError as e:
        cprint(f"Error writing config: {e}", "ERROR")
        return False

def _get_remote_data():
    """Fetches data about the latest version from GitHub API."""
    cprint(f"Checking for updates at: {GITHUB_API_URL}", "INFO")
    try:
        response = requests.get(GITHUB_API_URL, headers=GITHUB_HEADERS, timeout=10)
        response.raise_for_status() 
        remote_data = response.json()
        
        assets = remote_data.get('assets', [])
        download_url = None
        for asset in assets:
            # Assumes the downloadable file is named as specified in DOWNLOADED_RAR_NAME
            if asset.get('name') == DOWNLOADED_RAR_NAME:
                # Důležité: GitHub API pro assets vrací speciální 'browser_download_url',
                # ale pro 'application/octet-stream' je často potřeba použít přímou API URL.
                # Zde používáme asset.get('url') a v download_file nastavujeme header
                # 'Accept': 'application/octet-stream'.
                download_url = asset.get('url') 
                break
        
        if not download_url:
            cprint(f"Error: Asset '{DOWNLOADED_RAR_NAME}' not found on GitHub. Cannot update.", "ERROR")
            return None, None, None

        # tag_name is typically the version string (e.g., v1.2.3)
        remote_version = remote_data.get('tag_name', DEFAULT_VERSION)
        return remote_version, download_url, remote_data.get('body', "Changelog není k dispozici.")
        
    except requests.exceptions.RequestException as e:
        cprint(f"Error connecting to GitHub API (no internet?): {e}", "ERROR")
        return None, None, None

def download_file(url, save_path):
    """Downloads a file from GitHub."""
    # Use 'application/octet-stream' for downloading asset from GitHub
    headers = {'Accept': 'application/octet-stream'}
    cprint(f"Downloading file from URL: {url} to {save_path}", "INFO")
    try:
        req = requests.get(url, headers=headers, stream=True) 
        req.raise_for_status() 

        # Ensure the destination directory exists before writing the file
        os.makedirs(os.path.dirname(save_path), exist_ok=True) 

        with open(save_path, 'wb') as file:
            # Iterate through 8KB chunks for large files
            for chunk in req.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
        return True
        
    except requests.exceptions.RequestException as e:
        cprint(f"Error downloading file: {e}", "ERROR")
        return False

def run_installation(remote_version, download_url):
    """Performs download and extraction of files."""
    cprint("--- START INSTALLATION / UPDATE ---", "INFO")
    
    # 1. Download
    # Používá plnou cestu, která je nastavena na začátku souboru (DOWNLOADED_RAR_PATH)
    if not download_file(download_url, DOWNLOADED_RAR_PATH):
        cprint("Installation failed at download step.", "ERROR")
        return False
        
    # 2. Extraction
    cprint(f"Extracting file '{DOWNLOADED_RAR_PATH}' to directory: {EXPANDED_GAME_DIR}", "INFO")
    try:
        # Původní kód pro smazání celé složky EXPANDED_GAME_DIR byl odebrán.
        # Nyní se extrakcí pouze přepíší existující soubory.
        
        # Vytvoření adresáře pro extrakci (což je i adresář pro stažení)
        os.makedirs(EXPANDED_GAME_DIR, exist_ok=True)
        
        if not os.path.exists(RAR_EXE_PATH):
            cprint(f"Error: Rar.exe not found at path: {RAR_EXE_PATH}. CANNOT EXTRACT.", "ERROR")
            cprint("Installation failed - Rar.exe missing.", "ERROR")
            return False

        # Run Rar.exe for extraction (x: extract, -y: assume yes/overwrite)
        rar_command = [RAR_EXE_PATH, 'x', '-y', DOWNLOADED_RAR_PATH, EXPANDED_GAME_DIR]
        # Capture Rar.exe output to avoid console issues
        result = subprocess.run(rar_command, capture_output=True, text=True, check=False) 
        
        if result.returncode != 0 and "All OK" not in result.stdout:
            cprint(f"Error during extraction (Rar.exe Code: {result.returncode}).", "ERROR")
            cprint(f"ERROR: {result.stderr.strip()}", "ERROR")
            return False
        else:
            cprint("Extraction completed. Rar.exe output (if any):", "INFO")
            print(result.stdout.strip()) 
        
        # 3. Delete downloaded RAR file
        if os.path.exists(DOWNLOADED_RAR_PATH):
            cprint(f"Deleting downloaded file: {DOWNLOADED_RAR_PATH}", "INFO")
            os.remove(DOWNLOADED_RAR_PATH)
            
    except Exception as e:
        cprint(f"Unexpected error during extraction: {e}", "ERROR")
        return False

    # 4. Version save
    cprint(f"Updating local version to {remote_version}", "INFO")
    _, config_data = _load_local_config()
    if not _save_local_config(remote_version, config_data):
           cprint("Version update in config failed.", "ERROR")
           return False

    cprint("UPDATE COMPLETED SUCCESSFULLY!", "SUCCESS")
    return True

def run_game():
    """Runs the game and waits for it to complete."""
    cprint(f"Running game: {EXPANDED_GAME_EXE_PATH}", "INFO")
    
    if not os.path.exists(EXPANDED_GAME_EXE_PATH):
        cprint(f"Error: Game executable not found: {EXPANDED_GAME_EXE_PATH}", "ERROR")
        return False

    try:
        # Run game with output redirected to current console
        cprint("---------------------------------------", "INFO")
        cprint("--- START GAME OUTPUT (Godot Console) ---", "INFO")
        cprint("---------------------------------------", "INFO")
        
        # Runs the game and lets it run. Output will be in current console.
        process = subprocess.Popen([EXPANDED_GAME_EXE_PATH], 
                                   cwd=EXPANDED_GAME_DIR, 
                                   stdout=sys.stdout, 
                                   stderr=sys.stderr 
                                  )
        
        process.wait() # Wait until game finishes
        
        cprint("---------------------------------------", "INFO")
        cprint("--- END GAME OUTPUT ---", "INFO")
        cprint("---------------------------------------", "INFO")
        cprint(f"Game ended with code: {process.returncode}", "SUCCESS" if process.returncode == 0 else "WARN")
        return True
        
    except Exception as e:
        cprint(f"Unexpected error while running game: {e}", "ERROR")
        return False

# --- 4. MAIN LOGIC ---

def main():
    parser = argparse.ArgumentParser(
        description="Gamesa Console Launcher and Updater. By default checks for updates and runs the game."
    )
    
    # Define arguments
    
    parser.add_argument(
        '--update_only',
        action='store_true',
        help='Only checks for updates and performs update/installation. Does NOT run the game.'
    )
    parser.add_argument(
        '--no_launch',
        action='store_true',
        help='Prevents the game from launching after checking/performing updates.'
    )
    
    # Nový argument pro explicitní spuštění hry (přepíše výchozí chování)
    parser.add_argument(
        '--launch',
        action='store_true',
        help='Forces the game to launch after update checks/installation (overrides default/update_only).'
    )
    
    args = parser.parse_args()

    # --- NEW DEFAULT BEHAVIOR IMPLEMENTATION ---
    # Původní chování pro spuštění bez argumentů bylo nastaveno na --forceupdate a --update_only.
    # Nyní bude nastaveno na standardní kontrolu aktualizace a --update_only (tj. nespustí hru)
    if len(sys.argv) == 1:
        cprint("No arguments provided. Defaulting to: Check Update and Exit.", "INFO")
        args.update_only = True
        # Ensure launch flags are off for the default case
        args.launch = False
        args.no_launch = True
    # -------------------------------------------


    # Stanovení, zda se má hra spustit.
    # Spustí se POUZE, pokud je explicitně zadáno --launch,
    # NEBO pokud není zadáno --update_only a --no_launch.
    should_launch = args.launch or (not args.update_only and not args.no_launch)


    # --- Step 1: Get versions and data ---
    local_version, _ = _load_local_config()
    remote_version, download_url, changelog = _get_remote_data()
    
    cprint("-" * 50, "INFO")
    
    # Check if we could get data from GitHub
    if remote_version is None or download_url is None:
        cprint("Cannot get remote version information (API/Network Error).", "ERROR")
        
        if should_launch and os.path.exists(EXPANDED_GAME_EXE_PATH):
            cprint("Continuing with only launching local game (if it exists).", "WARN")
            cprint("Running local game...", "INFO")
            run_game()
            sys.exit(0)
        else:
            cprint("Game not launched (Update failed or local exe doesn't exist / Launch suppressed).", "INFO")
            sys.exit(1) # Exit with error code because update failed

    # --- Step 2: Version comparison ---
    
    try:
        # LooseVersion comparison is safer for schemes like v0.9.1
        needs_update = LooseVersion(local_version) < LooseVersion(remote_version)
    except Exception:
        # Fallback if version string format is weird
        needs_update = local_version != remote_version
        
    cprint(f"Local version: {local_version} | Latest version: {remote_version}", "INFO")
    
    # Is the game installed?
    is_installed = os.path.exists(EXPANDED_GAME_EXE_PATH)
    
    # Do we need to perform installation/update?
    # should_install se nyní spouští, pokud je potřeba_update NEBO není_instalováno.
    should_install = needs_update or not is_installed

    if should_install:
        if not is_installed:
            cprint("Game is not installed. Installation required.", "WARN")
        else:
            cprint("New version found! Update is required.", "WARN")

        # Optional changelog print
        cprint("\n--- CHANGELOG ---", "INFO")
        print(changelog)
        cprint("-----------------", "INFO")
        
    elif not should_install:
        cprint("Game is up-to-date, no update needed.", "SUCCESS")


    # --- Step 3: Process Arguments and Actions ---
    
    installation_success = True

    if should_install:
        cprint("Running installation/update.", "INFO")
        installation_success = run_installation(remote_version, download_url)

    # Handling update failure
    if should_install and not installation_success:
        cprint("Update failed. Launch skipped.", "ERROR")
        sys.exit(1) 

    # Launching logic
    if should_launch:
        # If we reach here, update was either successful, not needed, or forced, and launch is permitted.
        cprint("Launching game.", "INFO")
        run_game()
    else:
        # If should_launch is False (due to default mode, --update_only, or --no_launch)
        cprint("Launch skipped (Update/Install finished, or already up-to-date).", "SUCCESS")
        
    cprint("Script finished running.", "INFO")
    sys.exit(0)


if __name__ == "__main__":
    # Setup for color support in console on Windows 10/11
    if sys.platform == "win32":
        try:
            # Enable ANSI escape sequences
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7) 
        except Exception:
            pass
            
    try:
        # Quick dependency check
        import requests 
        # distutils.version.LooseVersion is imported correctly at the top
    except ImportError as e:
        print(f"ERROR: Missing dependency: {e}. Please install it, e.g., 'pip install requests'")
        sys.exit(1)
        
    # Spuštění hlavní funkce
    main()