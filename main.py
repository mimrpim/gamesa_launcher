import requests
import json
import sys
import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from distutils.version import LooseVersion  # type: ignore
import time
import markdown
from html.parser import HTMLParser

# --- 1. KONFIGURACE ---
UNEXPANDED_CONFIG_PATH = "%appdata%/Godot/app_userdata/Gamesa/config_updater.json"
GAME_DIR_PATH = "%appdata%/Godot/app_userdata/Gamesa/game_files"
UNEXPANDED_LOGS_DIR = "%appdata%/Godot/app_userdata/Gamesa/logs" 
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
EXPANDED_LOGS_DIR = os.path.expandvars(UNEXPANDED_LOGS_DIR).replace('\\', '/')

# --- 2. MINECRAFT DARK TÉMA BARVY ---
BG_DARK = "#202020"       # Tmavé pozadí (černá/tmavě šedá)
BG_LIGHTER = "#363636"    # Lehce světlejší pozadí pro rámečky
TEXT_COLOR = "#FFFFFF"    # Bílý text
BUTTON_BG = "#444444"     # Šedé tlačítko
BUTTON_ACTIVE = "#666666" # Aktivní (hover) tlačítko
BUTTON_FG = "#FFFFFF"     # Bílý text na tlačítku
LOG_BG = "#000000"        # Opravdu černé pozadí pro log
LOG_FG = "#00FF00"        # Zelený text pro konzolový dojem

class MarkdownToTkinter(HTMLParser):
    """Pomocná třída pro parsování HTML (vygenerovaného z Markdownu) a aplikování Tkinter tagů."""
    def __init__(self, text_widget, title_text):
        super().__init__()
        self.text_widget = text_widget
        self.title_text = title_text
        self.in_list = False
        self.list_count = 1
        self.last_tag = 'p' 
        self.list_indent = 0

    def handle_starttag(self, tag, attrs):
        self.text_widget.mark_set('tag_start', tk.END)
        self.last_tag = tag

        if tag == 'h1' or tag == 'h2':
            self.text_widget.insert(tk.END, '\n\n')
            self.text_widget.mark_set('tag_start', tk.END) 
        elif tag == 'p':
            self.text_widget.insert(tk.END, '\n') 
        elif tag == 'ul' or tag == 'ol':
            self.in_list = True
            self.list_count = 1
            self.list_indent += 1
            self.text_widget.insert(tk.END, '\n')
        elif tag == 'li':
            # Vložení odrážky/čísla s odsazením
            indent = '  ' * (self.list_indent - 1)
            if self.in_list and self.last_tag == 'ul':
                self.text_widget.insert(tk.END, f"{indent}• ", 'list_tag')
            elif self.in_list and self.last_tag == 'ol':
                self.text_widget.insert(tk.END, f"{indent}{self.list_count}. ", 'list_tag')
                self.list_count += 1
            
    def handle_endtag(self, tag):
        if tag == 'h1':
            self.text_widget.tag_add('h1_tag', 'tag_start', tk.END)
            self.text_widget.insert(tk.END, '\n', 'default')
        elif tag == 'h2':
            self.text_widget.tag_add('h2_tag', 'tag_start', tk.END)
            self.text_widget.insert(tk.END, '\n', 'default')
        elif tag == 'strong' or tag == 'b':
            self.text_widget.tag_add('bold_tag', 'tag_start', tk.END)
        elif tag == 'p':
            self.text_widget.insert(tk.END, '\n', 'default')
        elif tag == 'ul' or tag == 'ol':
            self.in_list = False
            self.list_indent -= 1
            self.text_widget.insert(tk.END, '\n', 'default')
        elif tag == 'li':
            self.text_widget.insert(tk.END, '\n', 'default')

    def handle_data(self, data):
        self.text_widget.insert(tk.END, data, 'default')

    def render_markdown(self, markdown_text):
        """Převádí a vkládá Markdown do Tkinter widgetu."""
        html = markdown.markdown(markdown_text)
        self.feed(html)
        self.text_widget.see(tk.END)


class GameLauncher(tk.Tk):
    """Hlavní třída aplikace s grafickým rozhraním v Dark Mode."""
    def __init__(self):
        super().__init__()
        self.title("Gamesa Aktualizace & Launcher (mimrpim)")
        
        # Pevné rozměry okna
        self.window_width = 854
        self.window_height = 480
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        center_x = int(screen_width/2 - self.window_width/2)
        center_y = int(screen_height/2 - self.window_height/2)
        self.geometry(f"{self.window_width}x{self.window_height}+{center_x}+{center_y}")
        
        # Zakázání změny velikosti a fullscreenu (okno je FIXED)
        self.resizable(False, False) 
        self.config(bg=BG_DARK)
        
        # Stavy
        self.local_version = DEFAULT_VERSION
        self.remote_version = None
        self.download_url = None
        self.remote_changelog = "Probíhá kontrola aktualizací..."
        self.is_installed = os.path.exists(EXPANDED_GAME_EXE_PATH)
        self.is_up_to_date = False
        self.is_busy = False 
        self.log_mode = 'changelog' 
        
        self.create_widgets()
        
        # První volání pro kontrolu aktualizací
        self.after(100, self.check_update_async) 

    def create_widgets(self):
        # --- STYLOVÁNÍ ---
        self.style = ttk.Style()
        self.style.theme_use('clam') 
        self.style.configure('TFrame', background=BG_DARK)
        
        # Nastavení stylu pro Tlačítka
        self.style.configure('TButton', 
                             font=('Inter', 10, 'bold'), 
                             padding=[10, 5],            
                             background=BUTTON_BG,
                             foreground=BUTTON_FG,
                             bordercolor=BG_LIGHTER,
                             borderwidth=2,
                             focuscolor=BG_DARK
                            )
        self.style.map('TButton',
                       background=[('active', BUTTON_ACTIVE)],
                       foreground=[('active', BUTTON_FG)],
                       relief=[('pressed', 'sunken'), ('!active', 'raised')],
                       bordercolor=[('active', TEXT_COLOR)]
                       )
                       
        # Nastavení stylu pro Popisky
        self.style.configure('TLabel', 
                             font=('Inter', 10), 
                             background=BG_DARK,
                             foreground=TEXT_COLOR
                            )
                            
        # Nastavení stylu pro Checkbox
        self.style.configure('TCheckbutton', 
                             font=('Inter', 10), 
                             background=BG_DARK,
                             foreground=TEXT_COLOR,
                             selectcolor=BG_DARK, 
                            )
        
        # FIX: Nastavení chování pozadí Checkboxu při HOVER
        self.style.map('TCheckbutton',
                       background=[
                           ('active', BG_LIGHTER), 
                           ('!active', BG_DARK)   
                       ],
                       foreground=[
                           ('active', TEXT_COLOR), 
                           ('!active', TEXT_COLOR)
                       ] 
                       )
        
        # STYL PRO PŘEPÍNÁNÍ LOGŮ
        self.style.configure('LogSwitcher.TButton', 
                             font=('Inter', 10, 'bold'), 
                             padding=[10, 5],            
                             background=BG_LIGHTER,
                             foreground=TEXT_COLOR,
                             bordercolor=BG_DARK,
                             borderwidth=1
                            )
        self.style.map('LogSwitcher.TButton',
                       background=[('active', BUTTON_ACTIVE)],
                       foreground=[('active', TEXT_COLOR)]
                       )
        
        title_font = ("Inter", 16, "bold")
        
        # --- Rozložení - Hlavní grid ---
        # 0: Log Switcher Frame
        # 1: Title Label
        # 2: Log Selector Frame (Novinka)
        # 3: Output Text Area (Flexibilní)
        # 4: Controls Frame
        self.grid_rowconfigure(3, weight=1) # Row 3 (Output Text) je flexibilní
        self.grid_rowconfigure(4, weight=0) # Row 4 (Controls) je pevný
        self.grid_columnconfigure(0, weight=1) 

        # ------------------- Row 0: Tlačítka pro přepínání logů -------------------
        log_switcher_frame = ttk.Frame(self, padding="20 5 20 0")
        log_switcher_frame.grid(row=0, column=0, sticky="new")
        log_switcher_frame.grid_columnconfigure(0, weight=1) 
        log_switcher_frame.grid_columnconfigure(1, weight=1) 

        self.changelog_button = ttk.Button(log_switcher_frame, text="Changelog", 
                                           command=lambda: self.switch_log_mode('changelog'), 
                                           style='LogSwitcher.TButton')
        self.changelog_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        self.gamelog_button = ttk.Button(log_switcher_frame, text="Herní Logy", 
                                         command=lambda: self.switch_log_mode('gamelog'), 
                                         style='LogSwitcher.TButton')
        self.gamelog_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        # ------------------- Row 1: Nadpis (Changelog / Log) -------------------
        self.output_title_label = ttk.Label(self, text="Změny (Changelog)", font=title_font, style='TLabel')
        self.output_title_label.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="w")
        
        # ------------------- Row 2: Selektor Logů (Nový řádek - Combobox) -------------------
        self.log_selector_frame = ttk.Frame(self, padding="20 0 20 5", style='TFrame')
        self.log_selector_frame.grid(row=2, column=0, sticky="ew") # Umístění
        self.log_selector_frame.grid_columnconfigure(1, weight=1) # Combobox je flexibilní

        log_select_label = ttk.Label(self.log_selector_frame, text="Vybraný soubor logu:", style='TLabel')
        log_select_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        self.log_combobox = ttk.Combobox(self.log_selector_frame, state='readonly', font=('Consolas', 9))
        self.log_combobox.grid(row=0, column=1, sticky="ew")
        # Bindujeme event, který se spustí při výběru položky v Comboboxu
        self.log_combobox.bind("<<ComboboxSelected>>", self._load_selected_log)

        # Na začátku skryjeme frame selektoru logů
        self.log_selector_frame.grid_remove()

        # ------------------- Row 3: Textová plocha -------------------
        self.output_text = scrolledtext.ScrolledText(self, wrap=tk.WORD, state=tk.DISABLED, 
                                                     height=10, font=("Consolas", 9), 
                                                     bg=LOG_BG, fg=LOG_FG, insertbackground=LOG_FG) 
        self.output_text.grid(row=3, column=0, padx=20, pady=(5, 5), sticky="nsew")

        
        # DEFINICE TAGŮ PRO MARKDOWN/LOG
        self.output_text.tag_configure("title", foreground=TEXT_COLOR, font=title_font)
        self.output_text.tag_configure("default", font=("Consolas", 9), foreground=LOG_FG) 
        self.output_text.tag_configure("bold_tag", font=("Consolas", 9, 'bold'), foreground=TEXT_COLOR)
        self.output_text.tag_configure("h1_tag", font=("Consolas", 12, 'bold'), foreground="#FFC000") 
        self.output_text.tag_configure("h2_tag", font=("Consolas", 10, 'bold'), foreground="#00FF00") 
        self.output_text.tag_configure("list_tag", foreground="#FF4444") 

        # PRVNÍ ZPRÁVY - Inicializace zobrazení
        self.switch_log_mode('changelog') 
        
        # ------------------- Row 4: Spodní sekce (Ovládání) -------------------
        controls_frame = ttk.Frame(self, padding="10 10 10 10")
        controls_frame.grid(row=4, column=0, sticky="ew")
        controls_frame.config(style='TFrame') 
        
        controls_frame.grid_columnconfigure(0, weight=0) 
        controls_frame.grid_columnconfigure(1, weight=0) 
        controls_frame.grid_columnconfigure(2, weight=1) 

        # --- Levý Blok (Force Install, Verze) - V C0 ---
        left_controls_group_frame = ttk.Frame(controls_frame, style='TFrame')
        left_controls_group_frame.grid(row=0, column=0, sticky="w", padx=(5, 10)) 
        
        self.force_install_var = tk.BooleanVar()
        self.force_install_check = ttk.Checkbutton(
            left_controls_group_frame, 
            text="Vynutit přeinstalaci", 
            variable=self.force_install_var, 
            command=self.update_button_state,
            style='TCheckbutton' 
        ) 
        self.force_install_check.grid(row=0, column=0, pady=5, sticky="w")
        
        self.version_label = ttk.Label(left_controls_group_frame, 
                                        text=f"Lokální: {self.local_version}", 
                                        style='TLabel')
        self.version_label.grid(row=1, column=0, sticky="w", pady=(0, 5))
        
        # --- Centrální Tlačítko (Install / Play) ---
        self.main_button = ttk.Button(controls_frame, text="Kontrola...", 
                                      command=self.on_main_button_click, 
                                      state=tk.DISABLED,
                                      style='TButton')
                                      
        self.main_button.place(relx=0.5, rely=0.5, anchor='center')

    def _get_available_log_files(self):
        """Vrátí seřazený seznam (nejnovější nahoře) jmen log souborů s plnou cestou."""
        if not os.path.exists(EXPANDED_LOGS_DIR):
            return []
        
        # Sestavení seznamu (cesta, čas modifikace) pro všechny .log soubory
        log_files_with_time = []
        for filename in os.listdir(EXPANDED_LOGS_DIR):
            full_path = os.path.join(EXPANDED_LOGS_DIR, filename)
            # Kontrola, zda je soubor a zda má příponu .log
            if os.path.isfile(full_path) and filename.endswith('.log'):
                log_files_with_time.append((full_path, os.path.getmtime(full_path)))
                
        # Seřazení podle času modifikace (nejnovější nejdříve)
        log_files_with_time.sort(key=lambda item: item[1], reverse=True)
        
        # Vrácení pouze seznamu jmen souborů (basename)
        return [os.path.basename(path) for path, _ in log_files_with_time]

    def highlight_active_button(self):
        """Zvýrazní aktivní tlačítko pro přepínání logů."""
        
        # Styl pro aktivní tlačítko
        active_style = 'ActiveLogSwitcher.TButton'
        self.style.configure(active_style, 
                             background="#007ACC",  # Modrá pro aktivní tlačítko
                             foreground=TEXT_COLOR,
                             bordercolor="#007ACC",
                             font=('Inter', 10, 'bold')
                            )
        
        # Resetování stylů
        self.changelog_button.config(style='LogSwitcher.TButton')
        self.gamelog_button.config(style='LogSwitcher.TButton')

        if self.log_mode == 'changelog':
            self.changelog_button.config(style=active_style)
        elif self.log_mode == 'gamelog':
            self.gamelog_button.config(style=active_style)

    def _load_selected_log(self, event=None, file_name=None):
        """Načte a zobrazí obsah vybraného log souboru."""
        
        if file_name is None:
            # Získáme jméno souboru z Comboboxu (pokud je voláno z Comboboxu)
            file_name = self.log_combobox.get()
            
        if not file_name or file_name == "Žádné logy nenalezeny":
            self.log_message("Žádné logy k zobrazení.", is_changelog=False, append=False)
            return
            
        full_path = os.path.join(EXPANDED_LOGS_DIR, file_name)
        
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        
        self.output_text.insert(tk.END, f"Načítám log: {file_name}\n", "title")
        self.output_text.insert(tk.END, "=" * 30 + "\n\n", 'default')
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.output_text.insert(tk.END, content, 'default')
        except Exception as e:
            self.output_text.insert(tk.END, f"❌ CHYBA ČTENÍ LOGU: {e}\n", 'default')
            
        self.output_text.config(state=tk.DISABLED)
        self.output_text.see(tk.END)


    def switch_log_mode(self, mode):
        """Přepne zobrazení logů mezi changelogem a herními logy/instalacemi."""
        if self.is_busy:
            self.log_message("\nProbíhá operace, nelze přepínat zobrazení.", is_changelog=False, append=True)
            return

        self.log_mode = mode
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)

        if mode == 'changelog':
            self.log_selector_frame.grid_remove() # Skrytí selektoru logů
            self.output_title_label.config(text="Změny (Changelog)")
            # Zobrazení aktuálního stavu changelogu
            self.log_message(self.remote_changelog, is_changelog=True, append=False) 
            # Přidání info o verzi, pokud už je známé
            if self.remote_version:
                 self.log_message(f"\n--- Launcher info ---\nLokální verze: {self.local_version}, Nejnovější: {self.remote_version}", is_changelog=False, append=True)
            
        elif mode == 'gamelog':
            self.log_selector_frame.grid() # Zobrazení selektoru logů
            self.output_title_label.config(text="Herní Logy (Přepínatelné)")
            
            log_files = self._get_available_log_files()
            self.log_combobox['values'] = log_files
            
            if log_files:
                # Nastavíme jako výchozí nejnovější log (první v seznamu)
                latest_file_name = log_files[0]
                self.log_combobox.set(latest_file_name)
                # Načteme a zobrazíme tento log
                self._load_selected_log(file_name=latest_file_name) 
            else:
                self.log_combobox.set("Žádné logy nenalezeny")
                self.log_message("V adresáři logů nejsou žádné soubory logů.", is_changelog=False, append=False)
                
        self.highlight_active_button()


    def log_message(self, message, is_changelog=False, append=True):
        """Vypíše zprávu do logovacího okna. Podporuje Markdown pro changelog."""
        self.output_text.config(state=tk.NORMAL)
        
        if not append:
            self.output_text.delete(1.0, tk.END)
            
        if is_changelog:
            parser = MarkdownToTkinter(self.output_text, self.output_title_label.cget('text'))
            parser.render_markdown(message)
            
        else:
            if not append and self.log_mode != 'gamelog': 
                self.output_text.insert(tk.END, f"{self.output_title_label.cget('text')}\n", "title")
                self.output_text.insert(tk.END, "="*len(self.output_title_label.cget('text')) + "\n", 'default')
            
            self.output_text.insert(tk.END, message + "\n", 'default')
            
        self.output_text.config(state=tk.DISABLED)
        self.output_text.see(tk.END) 
        
    def update_button_state(self):
        """Nastaví text a stav hlavního tlačítka na základě stavu aplikace."""
        self.is_installed = os.path.exists(EXPANDED_GAME_EXE_PATH)
        self.version_label.config(text=f"Lokální: {self.local_version} | Nejnovější: {self.remote_version if self.remote_version else 'N/A'}")
        
        if self.is_busy:
            self.main_button.config(text="Probíhá operace...", state=tk.DISABLED)
            return

        is_force = self.force_install_var.get()
        
        if not self.is_installed:
            self.main_button.config(text="INSTALOVAT HRU", state=tk.NORMAL)
        elif not self.is_up_to_date or is_force:
            self.main_button.config(text=f"AKTUALIZOVAT na {self.remote_version}", state=tk.NORMAL)
        else:
            self.main_button.config(text="HRÁT HRU", state=tk.NORMAL)

    # --- KONTROLA AKTUALIZACÍ ---
    
    def check_update_async(self):
        self.is_busy = True
        self.update_button_state()
        threading.Thread(target=self._check_update_logic, daemon=True).start()

    def _check_update_logic(self):
        self.local_version, _ = self._load_local_config()
        remote_data = self._get_remote_data()
        
        if remote_data is None:
            self.remote_version = "CHYBA"
        else:
            self.remote_version = remote_data.get('tag_name', DEFAULT_VERSION)
            self.remote_changelog = remote_data.get('body', "Changelog nebyl poskytnut.")
            
            try:
                self.is_up_to_date = LooseVersion(self.local_version) >= LooseVersion(self.remote_version)
            except Exception:
                self.is_up_to_date = self.local_version == self.remote_version

            self.after(0, self._finalize_update_check)
            
    def _finalize_update_check(self):
        self.is_busy = False
        
        # Kontrola aktualizace se provádí pouze pro changelog mód, ne pro gamelog
        if self.log_mode == 'changelog':
            self.output_title_label.config(text="Změny (Changelog)")
            self.log_message(self.remote_changelog, is_changelog=True, append=False) 
            
            if self.is_installed:
                if self.is_up_to_date:
                    self.log_message(f"\n--- Launcher info ---\nHra je aktuální ({self.local_version}).", is_changelog=False, append=True)
                else:
                    self.log_message(f"\n--- Launcher info ---\nNalezena nová verze: {self.remote_version}. Doporučujeme aktualizovat.", is_changelog=False, append=True)
            else:
                self.log_message(f"\n--- Launcher info ---\nHra není nainstalovaná. Nejnovější verze: {self.remote_version}. Je nutné ji nainstalovat.", is_changelog=False, append=True)
        
        self.update_button_state()

        
    # --- POMOCNÉ FUNKCE PRO FILE/API ---

    def _load_local_config(self):
        config_data = {}
        version = DEFAULT_VERSION
        try:
            with open(LOCAL_SETTINGS_PATH, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            version = config_data.get(VERSION_KEY, DEFAULT_VERSION)
        except FileNotFoundError:
            self._create_config_dir()
            self._save_local_config(DEFAULT_VERSION, config_data)
        except json.JSONDecodeError:
            pass
        return version, config_data

    def _save_local_config(self, version, config_data):
        config_data[VERSION_KEY] = version
        try:
            with open(LOCAL_SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
        except IOError as e:
            self.log_message(f"CHYBA ZÁPISU: Nepodařilo se zapsat novou verzi: {e}", is_changelog=False, append=True)
            messagebox.showerror("Chyba", "Chyba zápisu do configu.")
            
    def _create_config_dir(self):
        config_dir = os.path.dirname(LOCAL_SETTINGS_PATH)
        try:
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
        except OSError as e:
            self.log_message(f"CHYBA: Nepodařilo se vytvořit adresář: {config_dir}. {e}", is_changelog=False, append=True)
            messagebox.showerror("Chyba", "Nelze vytvořit adresář pro config.")

    def _get_remote_data(self):
        try:
            response = requests.get(GITHUB_API_URL, headers=GITHUB_HEADERS, timeout=10)
            response.raise_for_status() 
            remote_data = response.json()
            
            assets = remote_data.get('assets', [])
            download_url = None
            for asset in assets:
                if asset.get('name') == DOWNLOADED_RAR_NAME:
                    # Všimněte si, že pro stahování assetů je potřeba speciální URL/hlavička, kterou GitHub vrací.
                    # Použijeme stávající asset URL, ale hlavičku s octet-stream musíme přidat v download_file.
                    download_url = asset.get('url') 
                    break
            
            if not download_url:
                self.log_message(f"❌ CHYBA: Na GitHubu nebyl nalezen asset s názvem '{DOWNLOADED_RAR_NAME}'.", is_changelog=False, append=True)
                return None

            self.download_url = download_url
            return remote_data
            
        except requests.exceptions.RequestException as e:
            self.log_message(f"Chyba připojení k GitHub API: {e}", is_changelog=False, append=True)
            return None

    # --- KLIKACÍ AKCE ---

    def on_main_button_click(self):
        if self.is_busy:
            return

        is_force = self.force_install_var.get()
        needs_install = not self.is_installed or not self.is_up_to_date or is_force

        if needs_install:
            self.log_mode = 'gamelog' # Přepnutí na log mód
            self.log_selector_frame.grid_remove() # Skryjeme selektor, který není potřeba pro živý log instalace
            self.highlight_active_button()
            self.output_title_label.config(text="Instalační Log")
            self.log_message("--- START INSTALACE / AKTUALIZACE ---", is_changelog=False, append=False)
            self.is_busy = True
            self.update_button_state()
            threading.Thread(target=self._run_installation, daemon=True).start()
        elif self.is_installed:
            self.log_mode = 'gamelog' # Přepnutí na log mód
            self.log_selector_frame.grid_remove() # Skryjeme selektor
            self.highlight_active_button()
            self.output_title_label.config(text="Výstup Hry")
            self.log_message("--- SPUŠTĚNÍ HRY A ČEKÁNÍ NA VÝSTUP ---", is_changelog=False, append=False)
            self.is_busy = True 
            self.update_button_state()
            threading.Thread(target=self._run_game_and_capture_output, daemon=True).start()

    def _run_installation(self):
        download_success = False
        
        self.log_message(f"1/3 Stahování souboru '{DOWNLOADED_RAR_NAME}' z GitHubu...", is_changelog=False, append=True)
        # Používáme speciální hlavičku pro stahování assetů
        headers = {'Accept': 'application/octet-stream'} 
        download_success = download_file(self.download_url, DOWNLOADED_RAR_NAME, headers) 
        
        if download_success:
            self.log_message(f"2/3 Extrakce pomocí '{RAR_EXE_PATH}' do cílového adresáře...", is_changelog=False, append=True)
            try:
                if os.path.exists(EXPANDED_GAME_DIR):
                    import shutil
                    self.log_message(f"Mažu starý adresář: {EXPANDED_GAME_DIR}", is_changelog=False, append=True)
                    shutil.rmtree(EXPANDED_GAME_DIR, ignore_errors=True)
                os.makedirs(EXPANDED_GAME_DIR, exist_ok=True)
                
                rar_command = [RAR_EXE_PATH, 'x', '-y', DOWNLOADED_RAR_NAME, EXPANDED_GAME_DIR]
                result = subprocess.run(rar_command, capture_output=True, text=True, check=False) 
                
                if result.returncode != 0 and "All OK" not in result.stdout:
                    self.log_message(f"❌ CHYBA EXTRACTU: Rar.exe selhalo. Kód: {result.returncode}. CHYBA: {result.stderr.strip()}", is_changelog=False, append=True)
                    download_success = False
                else:
                    self.log_message(result.stdout.strip() if result.stdout else "Rar.exe spuštěno (Bez viditelného výstupu).", is_changelog=False, append=True)
                    self.log_message("Extrakce hotova.", is_changelog=False, append=True)
                
                if os.path.exists(DOWNLOADED_RAR_NAME):
                    os.remove(DOWNLOADED_RAR_NAME)
                
            except FileNotFoundError:
                self.log_message(f"❌ CHYBA: Soubor RAR.EXE nebyl nalezen na cestě: {RAR_EXE_PATH}. NELZE EXTRAHOVAT!", is_changelog=False, append=True)
                download_success = False
            except Exception as e:
                self.log_message(f"❌ NEOČEKÁVANÁ CHYBA PŘI MANIPULACI SE SOUBORY: {e}", is_changelog=False, append=True)
                download_success = False

        if download_success:
            self.log_message(f"3/3 Aktualizace lokální verze na {self.remote_version}...", is_changelog=False, append=True)
            _, config_data = self._load_local_config()
            self._save_local_config(self.remote_version, config_data) 
            
            self.local_version = self.remote_version
            self.is_installed = True
            self.is_up_to_date = True
            self.log_message("✅ AKTUALIZACE DOKONČENA USPEŠNĚ!", is_changelog=False, append=True)
        else:
            self.log_message("❌ Instalace / Aktualizace selhala.", is_changelog=False, append=True)
            
        self.after(0, self._finalize_installation)

    def _finalize_installation(self):
        self.is_busy = False
        self.force_install_var.set(False) 
        self.update_button_state()
        # Vracíme se na changelog
        self.switch_log_mode('changelog') 
        
    def _run_game_and_capture_output(self):
        self.log_message(f"Spouštím hru {GAME_EXE_NAME}...", is_changelog=False, append=True)
        self.log_message("POZOR: Launcher je zablokován, dokud se hra neukončí.", is_changelog=False, append=True)
        self.log_message("-" * 30, is_changelog=False, append=True)
        
        try:
            # Spuštění hry s přesměrováním výstupu (Godot Console Output)
            process = subprocess.Popen([EXPANDED_GAME_EXE_PATH], 
                                       cwd=EXPANDED_GAME_DIR, 
                                       stdout=subprocess.PIPE, 
                                       stderr=subprocess.STDOUT, 
                                       universal_newlines=True 
                                      )
            
            # Asynchronní čtení výstupu a zobrazení v GUI
            for line in process.stdout:
                self.after(0, lambda msg=line.strip(): self.log_message(msg, is_changelog=False, append=True))
            
            process.wait() # Čekání na ukončení hry
            
            self.log_message("-" * 30, is_changelog=False, append=True)
            self.log_message(f"Hra skončila s kódem: {process.returncode}", is_changelog=False, append=True)
            
        except FileNotFoundError:
            self.log_message(f"❌ CHYBA: Spustitelný soubor nenalezen na cestě: {EXPANDED_GAME_EXE_PATH}", is_changelog=False, append=True)
            messagebox.showerror("Chyba spuštění", "Spustitelný soubor hry nebyl nalezen.")
        except Exception as e:
            self.log_message(f"❌ NEOČEKÁVANÁ CHYBA PŘI SPUŠTĚNÍ HRY: {e}", is_changelog=False, append=True)

        self.after(0, self._finalize_game_run)

    def _finalize_game_run(self):
        self.is_busy = False
        self.update_button_state()
        # Vracíme se na changelog
        self.switch_log_mode('changelog') 

# --- Funkce pro stažení ---
def download_file(url, save_path, headers):
    """Stáhne soubor z API endpointu s požadovanými hlavičkami (např. application/octet-stream)."""
    try:
        req = requests.get(url, headers=headers, stream=True) 
        req.raise_for_status() 

        with open(save_path, 'wb') as file:
            for chunk in req.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Chyba stahování: {e}") 
        return False

# --- Spuštění Aplikace ---
if __name__ == "__main__":
    try:
        # Kontrola závislostí
        import requests
        from distutils.version import LooseVersion # type: ignore
        import markdown 
    except ImportError as e:
        print(f"Chybí požadovaný balíček: {e.name}. Nainstalujte jej pomocí 'pip install {e.name}'.")
        sys.exit(1)
    os.startfile("icon_taskbar.exe")
    app = GameLauncher()
    app.mainloop()