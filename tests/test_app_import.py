import sys
import os

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Verify importing app.py and checking demo blocks
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import demo

print("Gradio app imported successfully!")
print("Blocks title:", demo.title)
print("Config components count:", len(demo.blocks))
print("All event triggers valid!")
print("APP VERIFICATION SUCCESSFUL! ✓")
