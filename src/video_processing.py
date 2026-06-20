import os
import subprocess
import logging
import shutil
import glob

def get_video_duration(video_path: str) -> float:
    """Retrieve video duration using ffprobe."""
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    try:
        import sys
        kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True, "check": True}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(command, **kwargs)
        return float(result.stdout.strip())
    except Exception as e:
        logging.error(f"Error getting video duration: {e}")
        return 0.0

def extract_frames(video_path: str, interval: int = 5, max_frames: int = 20) -> list[str]:
    """
    Extract frames from a video using ffmpeg.
    interval: extract 1 frame every 'interval' seconds.
    max_frames: stop extracting after this many frames.
    
    Returns a list of file paths to the extracted images.
    """
    temp_dir = os.path.abspath("temp_frames")
    
    # Clean up existing temp dir if present
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    
    output_pattern = os.path.join(temp_dir, "frame_%04d.jpg")
    
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", video_path,
        "-vf", f"fps=1/{interval}",
        "-vframes", str(max_frames),
        "-q:v", "2",  # high quality JPEG
        output_pattern
    ]
    
    try:
        import sys
        kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True, "check": True}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            
        logging.info(f"Running ffmpeg to extract frames: {' '.join(command)}")
        subprocess.run(command, **kwargs)
        
        # Get list of extracted frames sorted alphabetically
        frames = sorted(glob.glob(os.path.join(temp_dir, "*.jpg")))
        logging.info(f"Extracted {len(frames)} frames to {temp_dir}.")
        return frames
    except FileNotFoundError:
        logging.error("ffmpeg is not installed or not available on PATH.")
        raise RuntimeError("ffmpeg not found on the system. Please install ffmpeg to use local vision models.")
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        logging.error(f"ffmpeg extraction failed: {stderr}")
        raise RuntimeError(f"Error extracting frames: {stderr}")

def cleanup_frames():
    """Remove the temporary frames directory."""
    temp_dir = os.path.abspath("temp_frames")
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            logging.info(f"Cleaned up {temp_dir}")
        except Exception as e:
            logging.error(f"Failed to clean up temp frames: {e}")
