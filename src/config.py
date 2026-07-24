import os
import logging
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project Paths
BASE_DIR = Path(__file__).resolve().parent.parent

def load_default_config():
    """Load configuration from settings/default.yaml."""
    try:
        with open("settings/default.yaml", "r", encoding="utf-8") as ymlfile:
            return yaml.safe_load(ymlfile) or {}
    except Exception as e:
        logging.error(f"Error loading default config: {e}")
        return {}

def get_gemini_api_key():
    """Retrieve the Gemini API key without logging or exposing the secret."""
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        return env_key
    try:
        with open("secrets/gemini.yaml", "r", encoding="utf-8") as ymlfile:
            gemini = yaml.safe_load(ymlfile)
        if isinstance(gemini, dict):
            key = gemini.get("gemini_api_key")
            if key:
                return key
    except Exception:
        return None
    return None

def get_ollama_endpoint():
    config = load_default_config()
    if "ollama_endpoint" in config:
        return config["ollama_endpoint"]
    env_val = os.environ.get("OLLAMA_ENDPOINT")
    if env_val:
        return env_val
    return "http://127.0.0.1:11434"

def get_lmstudio_endpoint():
    config = load_default_config()
    if "lmstudio_endpoint" in config:
        return config["lmstudio_endpoint"]
    env_val = os.environ.get("LMSTUDIO_ENDPOINT")
    if env_val:
        return env_val
    return "http://127.0.0.1:1234"

def get_lmstudio_timeout():
    config = load_default_config()
    if "lmstudio_timeout" in config:
        try:
            return int(config["lmstudio_timeout"])
        except (ValueError, TypeError):
            pass
    env_val = os.environ.get("LMSTUDIO_TIMEOUT") or os.environ.get("LMSTUDIO_READ_TIMEOUT")
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            pass
    return 300

def get_ollama_timeout():
    config = load_default_config()
    if "ollama_timeout" in config:
        try:
            return int(config["ollama_timeout"])
        except (ValueError, TypeError):
            pass
    env_val = os.environ.get("OLLAMA_TIMEOUT") or os.environ.get("OLLAMA_READ_TIMEOUT")
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            pass
    return 300

# API Keys, Endpoints and Timeouts
GEMINI_API_KEY = get_gemini_api_key()
OLLAMA_ENDPOINT = get_ollama_endpoint()
LMSTUDIO_ENDPOINT = get_lmstudio_endpoint()
LMSTUDIO_TIMEOUT = get_lmstudio_timeout()
OLLAMA_TIMEOUT = get_ollama_timeout()

# Default models
DEFAULT_OLLAMA_MODEL = "llava:latest"
DEFAULT_LMSTUDIO_MODEL = "local-model"

# Localization Translators
_locales = None
_current_language = None

def get_ui_language():
    """Return configured UI language ('english' or 'italian')."""
    try:
        config = load_default_config()
        return config.get("ui_language", "english").strip().lower()
    except Exception:
        return "english"

def get_translation(key):
    """Retrieve a translated string based on ui_language."""
    global _locales, _current_language
    
    if _locales is None:
        try:
            with open("settings/locales.yaml", "r", encoding="utf-8") as f:
                _locales = yaml.safe_load(f) or {}
        except Exception as e:
            logging.error(f"Error loading locales: {e}")
            _locales = {}
            
    if _current_language is None:
        _current_language = get_ui_language()
            
    lang_dict = _locales.get(_current_language, {})
    if key in lang_dict:
        return lang_dict[key]
        
    english_dict = _locales.get("english", {})
    if key in english_dict:
        return english_dict[key]
        
    return key

# Alias get_translation as _
_ = get_translation

def setup_logging(log_file="video_analyzer.log"):
    """Configure logging: remove previous log file and set up handlers."""
    try:
        if os.path.exists(log_file):
            os.remove(log_file)
    except PermissionError:
        pass  # File locked by a previous process on Windows — skip removal
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )
