import os
import subprocess

subprocess.Popen(["py", "launcher_cli.exe", "--forceupdate", "--update_only"])
os.startfile("icon_taskbar.py")
