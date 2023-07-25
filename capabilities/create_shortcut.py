import os
import winshell
from win32com.client import Dispatch

# Source file path
src = 'P:\\Scripts\\ahk\\Keyboard_bindings.ahk'

# Path to AutoHotkey executable
ahk_exe = 'C:\\Program Files\\AutoHotkey\\AutoHotkey.exe'

# Destination path
startup_folder = os.path.join(os.environ['APPDATA'], 'Microsoft\\Windows\\Start Menu\\Programs\\Startup')

# Create a shortcut
shell = Dispatch('WScript.Shell')
shortcut = shell.CreateShortCut(os.path.join(startup_folder, 'Keyboard_bindings.lnk'))

# If the source file is an AutoHotkey script, set the target path to the AutoHotkey executable
if src.endswith('.ahk'):
    shortcut.Targetpath = ahk_exe
    shortcut.Arguments = '"' + src + '"'
else:
    shortcut.Targetpath = src

shortcut.WorkingDirectory = os.path.dirname(src)
shortcut.save()
