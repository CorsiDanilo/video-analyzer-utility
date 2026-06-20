import os
import time
import base64
import logging
import json
import requests
from PIL import Image
import io
from google import genai

from .config import (
    GEMINI_API_KEY,
    OLLAMA_ENDPOINT,
    LMSTUDIO_ENDPOINT,
)

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
        
        response = client.models.generate_content(
            model=model_name,
            contents=[video_file, prompt]
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
