import os
import subprocess
import sys

# Simple script to compile Qt resources for the plugin

plugin_dir = os.path.dirname(os.path.abspath(__file__))
qrc_file = os.path.join(plugin_dir, 'resources.qrc')
py_file = os.path.join(plugin_dir, 'resources.py')

# List of possible commands for pyrcc in different environments
pyrcc_cmds = ['pyrcc6', 'pyrcc5', 'pyqt6-resource']

for cmd in pyrcc_cmds:
    try:
        print(f"Trying to compile with '{cmd}'...")
        subprocess.check_call([cmd, '-o', py_file, qrc_file])
        print(f"Successfully compiled {qrc_file} to {py_file} using {cmd}")
        sys.exit(0) # Success
    except FileNotFoundError:
        print(f"'{cmd}' not found. Trying next...")
        continue
    except subprocess.CalledProcessError as e:
        print(f"Error compiling resources with {cmd}: {e}")
        sys.exit(1)

print("Error: Could not find a valid pyrcc executable (tried pyrcc6, pyqt6-resource).")
print("Please ensure you are in a QGIS environment with pyqt6-tools installed.")
sys.exit(1)

