import os
import sys
import platform
import subprocess

def build():
    system = platform.system()
    print(f"Building Project Titan for {system}...")
    
    # Determine separator for --add-data
    sep = ";" if system == "Windows" else ":"
    
    # Asset Path: assets/ -> assets/
    assets_arg = f"assets{sep}assets"
    
    # PyInstaller Command
    cmd = [
        "pyinstaller",
        "--name", "TitanConfig",
        "--add-data", assets_arg,
        "--hidden-import", "scapy.layers.all",
        "--noconsole",
        "--onefile",
        "src/main.py"
    ]
    
    print("Executing:", " ".join(cmd))
    
    try:
        subprocess.check_call(cmd)
        print("Build Complete! Check dist/ folder.")
    except subprocess.CalledProcessError as e:
        print(f"Build Failed: {e}")
    except FileNotFoundError:
        print("Error: 'pyinstaller' not found. Install it with: pip install pyinstaller")

if __name__ == "__main__":
    build()
