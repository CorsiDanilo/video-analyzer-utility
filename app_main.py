import sys
import os
import warnings
import threading
import multiprocessing
import pystray
import webview
from PIL import Image

# Ignore deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Ensure freeze support is initialized early
if __name__ == "__main__":
    multiprocessing.freeze_support()

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.ui import create_ui, custom_css
from src.config import get_translation as _

def on_show(icon, item):
    if webview.windows:
        window = webview.windows[0]
        window.show()
        window.restore()

def on_quit(icon, item):
    icon.stop()
    if webview.windows:
        webview.windows[0].destroy()
    sys.exit(0)

def setup_tray():
    if hasattr(sys, '_MEIPASS'):
        icon_path = os.path.join(sys._MEIPASS, 'logo.ico')
    else:
        icon_path = 'logo.ico'
        
    try:
        image = Image.open(icon_path)
    except FileNotFoundError:
        image = Image.new('RGB', (64, 64), color='white')
        
    menu = pystray.Menu(
        pystray.MenuItem(_('tray_show_hide'), on_show),
        pystray.MenuItem(_('tray_exit'), on_quit)
    )
    
    icon = pystray.Icon("VideoAnalyzerApp", image, "Video Analyzer Utility", menu)
    icon.run()

if __name__ == "__main__":
    print("Starting Standalone Video Analyzer Utility...")
    app = create_ui()
    
    app.launch(
        server_name="127.0.0.1",
        inbrowser=False,
        css=custom_css,
        prevent_thread_lock=True
    )
    
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()
    
    title = _('title') if _('title') != 'title' else "Video Analyzer Utility"
    title = title.replace("#", "").strip()
    webview.create_window(title, app.local_url)
    webview.start()
