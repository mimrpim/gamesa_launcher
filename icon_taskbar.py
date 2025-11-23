import pystray
from PIL import Image, ImageDraw
import sys
import os

# Vytvoření jednoduchého obrázku pro ikonu (čtverec s tečkou)
# Nyní s podporou průhlednosti
def create_image(width, height, color1, color2):
    # Změna režimu na 'RGBA' pro podporu průhlednosti
    # Třetí hodnota v color1 tuple bude alfa kanál (0 = plně průhledné)
    image = Image.new('RGBA', (width, height), (*color1, 0)) # Rozbalíme RGB a přidáme 0 pro alfa
    dc = ImageDraw.Draw(image)
    # Pro elipsu použijeme plnou neprůhlednost (255)
    dc.ellipse((width / 4, height / 4, width * 3 / 4, height * 3 / 4), fill=(*color2, 255))
    return image

def on_quit(icon, item):
    os.system("taskkill /im launcher.exe")
    icon.stop()

def default_function(icon, item):
    print("Byla kliknuta výchozí akce")
    os.startfile("launcher.exe")

# Vytvoření ikony
# Použijte vlastní cestu k .ico nebo .png souboru, nebo použijte create_image
icon_image = Image.open("icon.ico")

# Volání create_image s RGB hodnotami pro barvy
# 'black' je (0, 0, 0), 'pink' je (255, 192, 203)
# Funkce si sama přidá alfa kanál
#icon_image = create_image(64, 64, (0, 0, 0), (255, 192, 203)) # Předáváme RGB tuplu

icon = pystray.Icon(name="Gamesa Launcher Icon",icon=icon_image,title="Gamesa Launcher",menu=pystray.Menu(
    pystray.MenuItem(text="",action=default_function,default=True),
    pystray.MenuItem(text="Quit", action=on_quit)
))

# Spuštění ikony v pozadí
print("Aplikace v pozadí...")
icon.run()

