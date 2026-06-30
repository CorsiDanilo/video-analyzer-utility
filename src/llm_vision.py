import os
import time
import base64
import logging
import json
import requests
from PIL import Image
import io
from google import genai
from google.genai import types

from .config import (
    GEMINI_API_KEY,
    OLLAMA_ENDPOINT,
    LMSTUDIO_ENDPOINT,
    _,
)

def _is_model_loaded_ollama(model_name: str) -> bool:
    try:
        url = OLLAMA_ENDPOINT.rstrip("/") + "/api/ps"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            loaded = [m.get("name", "") for m in data.get("models", [])]
            return any(model_name in name for name in loaded)
    except Exception:
        pass
    return False

def _is_model_loaded_lmstudio(model_name: str) -> bool:
    try:
        url = LMSTUDIO_ENDPOINT.rstrip("/") + "/v1/models"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            ids = [m.get("id", "") for m in data.get("data", [])]
            return any(model_name in mid for mid in ids)
    except Exception:
        pass
    return False

def _trigger_lmstudio_load(model_name: str) -> None:
    try:
        url = LMSTUDIO_ENDPOINT.rstrip("/") + "/api/v1/models/load"
        payload = {"model": model_name}
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            logging.info(f"Triggered load for model {model_name} on LM Studio (/api/v1/models/load)")
            return
    except Exception:
        pass
    try:
        url = LMSTUDIO_ENDPOINT.rstrip("/") + "/v1/models/load"
        payload = {"model": model_name}
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            logging.info(f"Triggered load for model {model_name} on LM Studio (/v1/models/load)")
            return
    except Exception:
        pass

def _image_to_base64(img_path: str) -> str:
    """Convert an image file to a base64-encoded PNG string."""
    try:
        with Image.open(img_path) as img:
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        logging.error(f"Error encoding image {img_path}: {e}")
        return ""

def _get_video_prompt(language: str = "Italiano") -> str:
    if language.lower() == "italiano":
        return (
            "Questi sono frame sequenziali estratti da un video, o il video stesso. "
            "Guarda/analizza il contenuto visivo dall'inizio alla fine e fornisci una "
            "descrizione dettagliata e unificata di ciò che accade in italiano. Non menzionare che "
            "questi sono frame, descrivi semplicemente gli eventi del video in modo naturale."
        )
    else:
        return (
            "These are sequential frames from a video, or the video itself. "
            "Watch/analyze the visual content from start to finish and provide a "
            "detailed and unified description of what happens in english. Do not mention that "
            "these are frames, just describe the events in the video naturally."
        )

def _get_video_system_instruction(language: str = "Italiano") -> str:
    if language.lower() == "italiano":
        return (
            "IMPORTANTE: Restituisci DIRETTAMENTE il testo trascritto o la descrizione "
            "senza alcuna introduzione, spiegazione, prefazione, chiusura o commento aggiuntivo. "
            "Non includere frasi del tipo 'Ecco il testo...', 'Di seguito l'estrazione...', 'Ecco la descrizione...' o simili. "
            "Inizia a rispondere direttamente con il contenuto richiesto."
        )
    else:
        return (
            "IMPORTANT: Return the transcribed text or description DIRECTLY "
            "without any introduction, explanation, preface, closing, or additional comment. "
            "Do not include sentences like 'Here is the text...', 'Below is the extraction...', 'Here is the description...' or similar. "
            "Start responding directly with the requested content."
        )

def analyze_video_gemini(video_path: str, model_name: str, response_language: str = "Italiano") -> str:
    """Upload video to Gemini via File API and analyze it."""
    if not GEMINI_API_KEY:
        return "[Error: GEMINI_API_KEY not configured in .env or config/gemini.yaml]"
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        logging.info(f"Uploading {video_path} to Gemini...")
        video_file = client.files.upload(file=video_path)
        
        logging.info(f"Waiting for Gemini to process {video_file.name}...")
        # Polling for processing to complete
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = client.files.get(name=video_file.name)
            
        if video_file.state.name == "FAILED":
            return "[Error: Gemini failed to process the video file.]"
            
        logging.info(f"Video ready. Sending generation request to {model_name}...")
        prompt = _get_video_prompt(response_language)
        system_instruction = _get_video_system_instruction(response_language)
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruction
        )
        
        response = client.models.generate_content(
            model=model_name,
            contents=[video_file, prompt],
            config=config
        )
        
        # Cleanup file from Gemini servers
        try:
            client.files.delete(name=video_file.name)
        except Exception as e:
            logging.warning(f"Failed to delete file from Gemini: {e}")
            
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini API Error: {e}", exc_info=True)
        return f"[Gemini API Error: {str(e)}]"

def analyze_frames_ollama(frame_paths: list[str], model_name: str, response_language: str = "Italiano") -> str:
    """Send all frames to Ollama in a single request."""
    try:
        prompt = _get_video_prompt(response_language)
        system_instruction = _get_video_system_instruction(response_language)
        images_b64 = []
        for path in frame_paths:
            b64 = _image_to_base64(path)
            if b64:
                images_b64.append(b64)
                
        if not images_b64:
            return "[Error: No valid frames found to analyze.]"
            
        url = OLLAMA_ENDPOINT.rstrip("/") + "/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "system": system_instruction,
            "images": images_b64,
        }
        
        logging.info(f"Sending {len(images_b64)} frames to Ollama ({model_name})...")
        resp = requests.post(url, json=payload, timeout=300) # Give it 5 mins for multiple frames
        resp.raise_for_status()

        accumulated = ""
        for line in resp.text.strip().split("\n"):
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and "response" in obj:
                    accumulated += obj["response"]
            except Exception:
                continue
        return accumulated.strip() if accumulated else "[No response from Ollama]"
    except Exception as e:
        logging.error(f"Ollama Vision API Error ({OLLAMA_ENDPOINT}): {e}", exc_info=True)
        return f"[Ollama Vision Error ({OLLAMA_ENDPOINT}): {str(e)}]"

def analyze_frames_lmstudio(frame_paths: list[str], model_name: str, response_language: str = "Italiano") -> str:
    """Send all frames to LM Studio in a single request."""
    try:
        prompt = _get_video_prompt(response_language)
        system_instruction = _get_video_system_instruction(response_language)
        
        content_array = [{"type": "text", "text": prompt}]
        for path in frame_paths:
            b64 = _image_to_base64(path)
            if b64:
                content_array.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"}
                })
                
        if len(content_array) == 1:
            return "[Error: No valid frames found to analyze.]"
            
        url = LMSTUDIO_ENDPOINT.rstrip("/") + "/v1/chat/completions"
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": system_instruction,
                },
                {
                    "role": "user",
                    "content": content_array
                }
            ],
        }
        
        logging.info(f"Sending {len(frame_paths)} frames to LM Studio ({model_name})...")
        resp = requests.post(url, json=payload, timeout=300)
        resp.raise_for_status()
        
        data = resp.json()
        choices = data.get("choices", [])
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message", {})
            return message.get("content", "").strip()
        return "[No response from LM Studio]"
    except Exception as e:
        logging.error(f"LM Studio Vision API Error ({LMSTUDIO_ENDPOINT}): {e}", exc_info=True)
        return f"[LM Studio Vision Error ({LMSTUDIO_ENDPOINT}): {str(e)}]"

def list_ollama_models() -> list[str]:
    """Fetch the list of available models from Ollama."""
    try:
        url = OLLAMA_ENDPOINT.rstrip("/") + "/api/tags"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("models", [])
            return [m["name"] for m in models]
    except Exception as e:
        logging.error(f"Error fetching Ollama models: {e}")
    return []

def list_lmstudio_models() -> list[str]:
    """Fetch the list of available models from LM Studio."""
    try:
        url = LMSTUDIO_ENDPOINT.rstrip("/") + "/v1/models"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("data", [])
            return [m["id"] for m in models]
    except Exception as e:
        logging.error(f"Error fetching LM Studio models: {e}")
    return []

def get_sorted_gemini_models(api_key: str) -> list[str]:
    """
    Recupera tutti i modelli Gemini e Gemma disponibili tramite API
    e li ordina posizionando il più recente all'inizio.
    """
    if not api_key:
        return []
        
    try:
        import re
        client = genai.Client(api_key=api_key)
        retrieved_models = []
        
        # 1. Recupera i modelli dall'API
        for model in client.models.list():
            name_lower = model.name.lower()
            # Includi solo modelli generativi per testo/visione che siano Gemini o Gemma
            if model.supported_actions and "generateContent" in model.supported_actions:
                if "gemini" in name_lower or "gemma" in name_lower:
                    # Escludi esplicitamente modelli di embeddings, audio, image, tts, video, tool, robotics, computer
                    exclude_keywords = ["embed", "audio", "image", "tts", "video", "tool", "robotics", "computer"]
                    if any(kw in name_lower for kw in exclude_keywords):
                        continue
                    clean_name = model.name.replace("models/", "")
                    retrieved_models.append(clean_name)
                    
        if not retrieved_models:
            return []

        # 2. Algoritmo di ordinamento semantico (Latest-First)
        def get_sort_key(name):
            name_lower = name.lower()
            
            # Priorità per i modelli 'latest' (0 = prima, 1 = dopo)
            is_latest = 0 if "latest" in name_lower else 1
            
            # Priorità del brand (Gemini prima di Gemma)
            brand_priority = 1 if "gemini" in name_lower else 2
            
            # Estrazione della versione numerica principale
            version = 1.0
            brand_match = re.search(r'(?:gemini|gemma)-?(\d+(?:\.\d+)?)', name_lower)
            if brand_match:
                val_str = brand_match.group(1)
                match_str = brand_match.group(0)
                idx = name_lower.find(match_str) + len(match_str)
                if idx < len(name_lower) and name_lower[idx] == 'b':
                    version = 1.0
                else:
                    version = float(val_str)
                    
            # Priorità del tipo di modello (preferiamo 'flash' per il default, poi 'pro', poi altri)
            flavor_priority = 3
            if "flash" in name_lower:
                flavor_priority = 1
            elif "pro" in name_lower:
                flavor_priority = 2
                
            # Restituiamo una tupla per ordinare:
            # - is_latest (latest in cima)
            # - version decrescente (-version)
            # - brand_priority crescente (Gemini prima di Gemma)
            # - flavor_priority crescente (Flash prima di Pro)
            # - nome alfabetico decrescente per tie-break
            return (is_latest, -version, brand_priority, flavor_priority, name_lower)

        return sorted(retrieved_models, key=get_sort_key)
        
    except Exception as e:
        logging.error(f"Impossibile connettersi a Gemini API o recuperare i modelli: {e}")
        return []

SYSTEM_PROMPT = (
    "Rispondi in modo chiaro e utile basandoti sulla descrizione del video fornita. \n"
    "NON iniziare la risposta indicando che si tratta di una descrizione. \n"
    "Limitati solo a rispondere alla richiesta dell'utente."
)

SYSTEM_PROMPT_EN = (
    "Respond clearly and helpfully based on the provided video description. \n"
    "DO NOT start your response by stating that it is a description. \n"
    "Limit yourself to answering only the user's request."
)

SYSTEM_PROMPT_FIX_TEXT = (
    "Sei un assistente specializzato nella correzione e formattazione del testo. "
    "Usa TUTTI i token a tua disposizione per massimizzare l'output e restituire il testo nella sua completezza. "
    "Correggi tutti gli errori di battitura, grammatica, punteggiatura e formattazione. "
    "NON omettere, tagliare o riassumere nessuna parte del testo originale: ogni parola deve essere presente nell'output. "
    "Restituisci esclusivamente il testo corretto, senza commenti, prefazioni o spiegazioni."
)

SYSTEM_PROMPT_FIX_TEXT_EN = (
    "You are a specialist assistant for text correction and formatting. "
    "Use ALL available tokens to maximize your output and return the text in its entirety. "
    "Correct all typos, grammar, punctuation, and formatting errors. "
    "Do NOT omit, truncate, or summarize any part of the original text: every word must be present in the output. "
    "Return exclusively the corrected text, with no comments, preambles, or explanations."
)

def query_ollama(user_input, transcription, ollama_model, fix_text=False, response_language="Italiano"):
    """Stream a response from a local Ollama server."""
    try:
        yield _("llm_checking_model")
        
        ready = False
        elapsed = 0
        while elapsed < 60:
            if _is_model_loaded_ollama(ollama_model):
                ready = True
                break
            yield _("llm_model_loading").format(elapsed=elapsed)
            import time
            time.sleep(2)
            elapsed += 2
            
        if not ready:
            yield _("llm_model_sending")
        else:
            yield _("llm_model_ready")

        is_english = str(response_language).strip().lower() == "english"
        if fix_text:
            sys_prompt = SYSTEM_PROMPT_FIX_TEXT_EN if is_english else SYSTEM_PROMPT_FIX_TEXT
        else:
            sys_prompt = SYSTEM_PROMPT_EN if is_english else SYSTEM_PROMPT

        if is_english:
            prompt = (
                f"# Description\n{transcription}\n\n"
                f"User prompt: \n{user_input}"
            )
        else:
            prompt = (
                f"# Descrizione\n{transcription}\n\n"
                f"User prompt: \n{user_input}"
            )
        url = OLLAMA_ENDPOINT.rstrip("/") + "/api/generate"
        payload = {
            "model": ollama_model,
            "prompt": prompt,
            "system": sys_prompt,
        }
        resp = requests.post(url, json=payload, timeout=120, stream=True)
        resp.raise_for_status()
        accumulated = ""
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                accumulated += line
                yield accumulated
                continue
            chunk = ""
            if isinstance(obj, dict):
                if 'response' in obj:
                    chunk = obj['response']
                elif 'text' in obj:
                    chunk = obj['text']
                elif 'output' in obj:
                    chunk = obj['output']
                elif 'results' in obj and isinstance(obj['results'], list):
                    for r in obj['results']:
                        if isinstance(r, dict) and 'text' in r:
                            chunk += r['text']
            if chunk:
                accumulated += chunk
                yield accumulated
    except Exception as e:
        logging.error(f"Error querying Ollama at {OLLAMA_ENDPOINT}: {e}")
        yield f"Error querying Ollama: {e}"

def query_lmstudio(user_input, transcription, lmstudio_model, fix_text=False, response_language="Italiano"):
    """Stream a response from a local LM Studio server."""
    try:
        if not lmstudio_model:
            yield "Error querying LM Studio: no model selected."
            return

        yield _("llm_checking_model")
        
        _trigger_lmstudio_load(lmstudio_model)
        
        ready = False
        elapsed = 0
        while elapsed < 60:
            if _is_model_loaded_lmstudio(lmstudio_model):
                ready = True
                break
            yield _("llm_model_loading").format(elapsed=elapsed)
            import time
            time.sleep(2)
            elapsed += 2
            
        if not ready:
            yield _("llm_model_timeout_lmstudio")
            return

        yield _("llm_model_ready")

        is_english = str(response_language).strip().lower() == "english"
        if fix_text:
            sys_prompt = SYSTEM_PROMPT_FIX_TEXT_EN if is_english else SYSTEM_PROMPT_FIX_TEXT
        else:
            sys_prompt = SYSTEM_PROMPT_EN if is_english else SYSTEM_PROMPT

        if is_english:
            user_content = (
                f"# Description\n{transcription}\n\n"
                f"User prompt: \n{user_input}"
            )
        else:
            user_content = (
                f"# Descrizione\n{transcription}\n\n"
                f"User prompt: \n{user_input}"
            )

        url = LMSTUDIO_ENDPOINT.rstrip("/") + "/v1/chat/completions"
        payload = {
            "model": lmstudio_model,
            "messages": [
                {
                    "role": "system",
                    "content": sys_prompt,
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
            "temperature": 0.2,
            "stream": True,
        }
        resp = requests.post(
            url,
            json=payload,
            timeout=(5, 120),
            stream=True,
        )
        resp.raise_for_status()
        accumulated = ""
        for line in resp.iter_lines(decode_unicode=True):
            if not line or line.strip() == "data: [DONE]":
                continue
            if line.startswith("data: "):
                line = line[6:]
            try:
                obj = json.loads(line)
                choices = obj.get("choices", []) if isinstance(obj, dict) else []
                if choices and isinstance(choices[0], dict):
                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "") if isinstance(delta, dict) else ""
                    if content:
                        accumulated += content
                        yield accumulated
            except Exception:
                continue
    except Exception as e:
        logging.error(f"Error querying LM Studio at {LMSTUDIO_ENDPOINT}: {e}")
        yield f"Error querying LM Studio: {e}"

def query_gemini(user_input, transcription, gemini_model, provider="Google", ollama_model=None, lmstudio_model=None, fix_text=False, response_language="Italiano"):
    """Dispatch query to the selected provider and stream the response.

    response_language: "Italiano" (default) or "English" — controls the
    language the LLM is instructed to reply in.
    """
    try:
        if provider and str(provider).lower().startswith('olla'):
            model_name = ollama_model or (gemini_model if gemini_model else 'llama2')
            yield from query_ollama(user_input, transcription, model_name, fix_text=fix_text, response_language=response_language)
            return

        if provider and str(provider).lower().startswith('lm'):
            model_name = lmstudio_model or (gemini_model if gemini_model else "local-model")
            yield from query_lmstudio(user_input, transcription, model_name, fix_text=fix_text, response_language=response_language)
            return

        # Use Gemini
        if not GEMINI_API_KEY:
            yield "Error: Gemini API key not found."
            return

        yield _("llm_waiting_gemini")

        client = genai.Client(api_key=GEMINI_API_KEY)

        is_english = str(response_language).strip().lower() == "english"
        if fix_text:
            sys_prompt = SYSTEM_PROMPT_FIX_TEXT_EN if is_english else SYSTEM_PROMPT_FIX_TEXT
        else:
            sys_prompt = SYSTEM_PROMPT_EN if is_english else SYSTEM_PROMPT

        if is_english:
            user_prompt = f"# Description\n{transcription}\n\nUser prompt: \n{user_input}"
        else:
            user_prompt = f"# Descrizione\n{transcription}\n\nUser prompt: \n{user_input}"

        config = types.GenerateContentConfig(
            system_instruction=sys_prompt
        )

        accumulated = ""
        for chunk in client.models.generate_content_stream(
            model=gemini_model,
            contents=[user_prompt],
            config=config,
        ):
            if chunk.text:
                accumulated += chunk.text
                yield accumulated
    except Exception as e:
        logging.error(f"Error querying AI provider: {e}")
        yield f"Error querying AI provider: {e}"
