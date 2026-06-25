import sys
import os
import warnings

# Ignore deprecation warnings from packages
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Add src to path so modules can be imported without 'src.' prefix if needed.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.ui import create_ui, custom_css

if __name__ == "__main__":
    print("Starting Video Analyzer Utility...")
    app = create_ui()
    app.launch(server_name="127.0.0.1", inbrowser=True, css=custom_css)
