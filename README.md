# 🎥 Video Analyzer Utility

## 📝 Description
This project is a multi-engine video analysis utility designed to describe, analyze, and extract insights from video files. It can analyze videos directly using Google's cloud-based Gemini models (via File API upload) or run entirely offline by extracting video frames (using `ffmpeg`/`ffprobe`) and processing them through local vision models (Ollama or LM Studio). It features a modern Gradio web interface, multi-language UI support (Italian/English), and an AI Assistant to interact with, summarize, or extract actionable tasks from the video descriptions.

## ✨ Features
- 🎥 **Video Analysis**: Support for MP4, MOV, MKV, and AVI files.
- ⚙️ **Dual Processing Modes**:
  - **Gemini (Cloud)**: Uploads videos natively to Gemini using the Google GenAI File API for native video understanding.
  - **Local Vision (Ollama / LM Studio)**: Offline processing by extracting frames using `ffmpeg` with custom intervals and frame limits.
- 💡 **Companion Files**: Automatically saves a `.txt` companion file (ending in `_description.txt`) next to each processed video file in its source directory.
- 🤖 **AI Assistant**: Post-process the generated video description to summarize, extract key action items (to-do list), or correct text errors using Gemini, Ollama, or LM Studio.
- 🌍 **Localization**: Fully localized user interface supporting both **English** and **Italiano** (auto-detected or configured in settings).
- 🖥️ **Modern Web UI**: A clean, responsive Gradio dashboard with integrated system file-browsing.
- 📋 **One-Click Copy**: Built-in buttons to copy the video description or AI assistant responses directly to your clipboard.

## 📋 Requirements
- 🐍 [Python 3.10+](https://apps.microsoft.com/detail/9ncvdn91xzqp)
- 🎬 **FFmpeg & FFprobe** (Required on PATH for local frame extraction engines)
- 🖼️ **Gradio** and other python libraries listed in `requirements.txt`.

### (Optional) AI Providers
This app can analyze the videos or interact with descriptions using one of these AI backends:

- **Google Gemini (Cloud)**
  - Create a `.env` file in the root directory and add your API key:
    ```env
    GEMINI_API_KEY=your_gemini_api_key_here
    ```
  - The UI will automatically detect the key, retrieve available models (latest first), and enable Gemini vision/chat models.

- **Ollama (Local)**
  - Install [Ollama](https://ollama.com/) and make sure the service is running.
  - Pull a multimodal/vision model for video frame processing (e.g., `llava:latest` or `qwen:vl`):
    ```bash
    ollama pull llava:latest
    ```
  - Select **Ollama** in the UI and choose your loaded model from the dropdown.

- **LM Studio (Local)**
  - Launch LM Studio and start the Local Server (defaults to `http://localhost:1234`).
  - Load your desired model.
  - In the UI, choose **LM Studio**, click **Refresh Models**, and select your model.

## 📦 Installation

### Step 1: Clone the repository
```bash
git clone https://github.com/CorsiDanilo/video-analyzer-utility.git
cd video-analyzer-utility
```

### Step 2: Set up a virtual environment
```bash
python -m venv .venv
# On Windows (PowerShell/CMD)
.venv\Scripts\activate
# On Linux/macOS
source .venv/bin/activate
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Install FFmpeg (Required for Local Vision Engines)
- 🖥️ **Windows**:
  - Download FFmpeg binaries (e.g. from gyan.dev or BtbN).
  - Add the `bin` folder containing `ffmpeg.exe` and `ffprobe.exe` to your system's **PATH** environment variable.
- 🍎 **macOS**:
  ```bash
  brew install ffmpeg
  ```
- 🐧 **Linux**:
  ```bash
  sudo apt update
  sudo apt install ffmpeg
  ```

## 🚀 Usage

1. Start the application:
   ```bash
   python main.py
   ```
2. Open your web browser and navigate to the address shown in the terminal (usually `http://127.0.0.1:7860`).
3. Select your video files using the **Browse Video Files / Sfoglia File Video** button or paste their absolute paths (one per line).
4. Click **Analyze Video / Analizza Video** to run the video analysis.

💡 **REMEMBER**: In addition to displaying the description in the UI, a companion file named `<video_name>_description.txt` is automatically created in the exact same folder as the original video file.

## 🎛️ Interface Guide
- **Percorso File Video / Video File Path(s)**: The text area containing the list of video file paths to process.
- **Sfoglia File Video / Browse Video Files**: Open a native system dialog to select multiple video files.
- **Provider AI**: Choose between **Google** (cloud-based Gemini API), **Ollama** (local offline vision models), and **LM Studio** (local API compatible models).
- **Frame Extraction Settings**: Adjust the interval (how many seconds between each frame extraction) and the maximum frame limit when using local vision engines.
- **Analizza Video / Analyze Video**: Start the analysis.
- **Copia Risultato / Copia Risposta**: Fast clipboard copy with success notifications.
- **Salva con nome... / Save As...**: Manually save the aggregated descriptions.
- **Assistente AI**: Use presets ("Summary / Riassunto", "To-Do List / Cose da fare", "Fix Text / Correggi Testo") or write custom questions to query the AI provider about the generated video descriptions.

## 📦 Standalone Desktop App (Windows)
You can package the application into a native standalone Windows desktop application (which runs in a webview with a system tray icon) using PyInstaller:

1. Double-click or execute the `installer.bat` batch script:
   ```bash
   installer.bat
   ```
2. The compilation process will run in your terminal. Once completed, you will find the standalone distribution folder in `dist/VideoAnalyzer/`.
3. Run `VideoAnalyzer.exe` inside that folder. The app will open in a native desktop window and place a **Video Analyzer Utility** icon in your system tray, from which you can show/hide or close the app.

## 📄 License
This project is licensed under the MIT License.

## 🙏 Acknowledgments
- [Gradio](https://www.gradio.app/) for the user interface.
- [Google GenAI SDK](https://github.com/google/generative-ai-python) for Gemini model access.
- [FFmpeg](https://ffmpeg.org/) for the frame extraction system.
- [PyWebView](https://pywebview.flowrl.com/) and [PyStray](https://github.com/moses-palmer/pystray) for the standalone desktop wrapper.
