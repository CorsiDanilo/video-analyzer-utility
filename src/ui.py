import os
import signal
import datetime
import logging
import gradio as gr

from .video_processing import extract_frames, cleanup_frames
from .llm_vision import (
    analyze_video_gemini,
    analyze_frames_ollama,
    analyze_frames_lmstudio,
    list_ollama_models,
    list_lmstudio_models
)
from .config import (
    get_gemini_api_key,
    setup_logging,
    _,
    GEMINI_VISION_MODELS
)

def browse_local_files():
    """Open a native file dialog to select one or more files."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected_paths = filedialog.askopenfilenames(
            title=_("dialog_select_title"),
            filetypes=[
                (_("dialog_filter_video"), "*.mp4 *.mov *.mkv *.avi"),
                (_("dialog_filter_all"), "*.*"),
            ],
            parent=root,
        )
        root.destroy()
        if selected_paths:
            return "\n".join(selected_paths)
        return gr.update()
    except Exception as e:
        logging.error(f"Error selecting files: {e}")
        gr.Error(_("dialog_err_select").format(str(e)))
        return gr.update()

def save_extracted_text(extracted_text, file_paths_text=""):
    """Open a native Save As dialog to save the extracted text."""
    if not extracted_text or not extracted_text.strip():
        gr.Warning(_("proc_no_files"))
        return
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        if file_paths_text and file_paths_text.strip():
            first_file = file_paths_text.strip().split("\n")[0].strip()
            import os
            video_name = os.path.splitext(os.path.basename(first_file))[0]
            initialfile = f"{video_name}_description.txt"
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            initialfile = f"video_analysis_{timestamp}.txt"

        target_path = filedialog.asksaveasfilename(
            title=_("dialog_save_title"),
            initialfile=initialfile,
            defaultextension=".txt",
            filetypes=[
                ("Text Files", "*.txt"),
                ("Markdown Files", "*.md"),
                (_("dialog_filter_all"), "*.*"),
            ],
            parent=root,
        )
        root.destroy()

        if target_path:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(extracted_text)
            gr.Info(_("dialog_info_saved").format(target_path))
        else:
            gr.Info(_("dialog_info_cancelled"))
    except Exception as e:
        logging.error(f"Error saving file: {e}")
        gr.Error(_("dialog_err_save").format(str(e)))

def notify_copy():
    gr.Info(_("copy_success"))

def process_video(file_paths_text, provider, response_language, gemini_model, ollama_model, lmstudio_model, frame_interval, max_frames):
    """Process video files based on provider."""
    if not file_paths_text or not file_paths_text.strip():
        yield _("proc_no_files"), gr.update(visible=False)
        return

    raw_paths = [p.strip() for p in file_paths_text.strip().split("\n") if p.strip()]
    combined_text = ""

    for file_path in raw_paths:
        if not os.path.isfile(file_path):
            logging.error(f"File not found: {file_path}")
            combined_text += _("proc_file_not_found").format(file_path)
            yield combined_text.strip(), gr.update(visible=False)
            continue

        filename = os.path.basename(file_path)
        combined_text += _("proc_analyzing").format(filename)
        yield combined_text.strip(), gr.update(visible=False)

        try:
            if provider == "Gemini":
                combined_text += _("uploading_to_gemini") + "\n"
                yield combined_text.strip(), gr.update(visible=False)
                
                result = analyze_video_gemini(file_path, gemini_model, response_language)
                combined_text += f"\n\n{result}\n\n---\n\n"
            else:
                # Ollama or LM Studio -> need to extract frames
                combined_text += _("frame_extraction_info").format(frame_interval, max_frames) + "\n"
                yield combined_text.strip(), gr.update(visible=False)
                
                frames = extract_frames(file_path, interval=int(frame_interval), max_frames=int(max_frames))
                if not frames:
                    combined_text += _("proc_error").format("No frames extracted.") + "\n\n---\n\n"
                    continue
                    
                model_name = ollama_model if provider == "Ollama" else lmstudio_model
                combined_text += _("frame_extraction_done").format(len(frames), provider) + "\n"
                yield combined_text.strip(), gr.update(visible=False)
                
                if provider == "Ollama":
                    result = analyze_frames_ollama(frames, model_name, response_language)
                else:
                    result = analyze_frames_lmstudio(frames, model_name, response_language)
                    
                combined_text += f"\n\n{result}\n\n---\n\n"
                cleanup_frames()

            # Save individual description text file
            if result and not any(result.startswith(prefix) for prefix in ["[Error", "[No response", "[Gemini API Error", "[Ollama Vision Error", "[LM Studio Vision Error"]):
                try:
                    from pathlib import Path
                    video_path_obj = Path(file_path)
                    video_name = video_path_obj.stem
                    out_file = video_path_obj.with_name(f"{video_name}_description.txt")
                    with open(out_file, "w", encoding="utf-8") as f:
                        f.write(result.strip())
                    logging.info(f"Auto-saved individual analysis to {out_file}")
                except Exception as e:
                    logging.error(f"Error auto-saving individual analysis for {file_path}: {e}", exc_info=True)

        except Exception as e:
            logging.error(f"Error processing {file_path}: {e}", exc_info=True)
            combined_text += _("proc_error").format(str(e)) + "\n\n---\n\n"

        yield combined_text.strip(), gr.update(visible=False)

    yield combined_text.strip(), gr.update(visible=True)


def reset_fields():
    return (
        "",                          
        _("output_placeholder"),     
        gr.update(visible=False),    
    )

def quit_app():
    try:
        logging.info(_("quitting"))
        os.kill(os.getpid(), signal.SIGINT)
    except Exception as e:
        logging.error(f"Error quitting application: {e}")
        raise

custom_css = """
.scrollable-markdown {
    max-height: 400px !important;
    overflow-y: auto !important;
}
.scrollable-markdown * {
    overflow: visible !important;
    max-height: none !important;
}
* {
    user-select: text !important;
    -webkit-user-select: text !important;
    -ms-user-select: text !important;
    -moz-user-select: text !important;
}
"""

def create_ui():
    setup_logging()
    has_gemini = get_gemini_api_key() is not None

    with gr.Blocks(title="Video Analyzer Utility") as demo:
        title_markdown = gr.Markdown(_("title"))

        with gr.Row():
            file_path_input = gr.Textbox(
                label=_("file_path_label"),
                placeholder=_("file_path_placeholder"),
                lines=3,
            )
        browse_button = gr.Button(_("browse_btn"), variant="secondary")

        config_accordion = gr.Accordion(label=_("config_accordion"), open=True)
        with config_accordion:
            response_language = gr.Radio(
                choices=["Italiano", "English"],
                value="Italiano",
                label=_("response_language_label"),
            )
            provider_radio = gr.Radio(
                choices=["Gemini", "Ollama", "LM Studio"],
                value="Gemini" if has_gemini else "Ollama",
                label=_("provider_label"),
            )

            gemini_model = gr.Radio(
                choices=GEMINI_VISION_MODELS,
                value=GEMINI_VISION_MODELS[0],
                label=_("gemini_model_label"),
                visible=has_gemini,
            )

            try:
                _ollama_init = list_ollama_models() if not has_gemini else []
            except Exception:
                _ollama_init = []
            _ollama_val = _ollama_init[0] if _ollama_init else ""

            ollama_model = gr.Dropdown(
                choices=_ollama_init,
                value=_ollama_val,
                allow_custom_value=True,
                label=_("ollama_model_label"),
                visible=not has_gemini,
            )

            lmstudio_model = gr.Dropdown(
                choices=[],
                value="",
                allow_custom_value=True,
                label=_("lmstudio_model_label"),
                visible=False,
            )

            refresh_btn = gr.Button(_("refresh_btn"), size="sm")

            with gr.Group(visible=not has_gemini) as extraction_group:
                gr.Markdown("**Frame Extraction Settings** (For local models)")
                with gr.Row():
                    frame_interval = gr.Number(value=5, label=_("frame_interval_label"), precision=0, minimum=1)
                    max_frames = gr.Number(value=20, label=_("max_frames_label"), precision=0, minimum=1, maximum=100)

        process_btn = gr.Button(_("process_btn"), variant="primary")

        output_accordion = gr.Accordion(_("output_accordion"), open=True)
        with output_accordion:
            copy_text_button = gr.Button(_("copy_btn"), variant="secondary", size="sm")
            output_text = gr.Markdown(
                _("output_placeholder"),
                container=True,
                line_breaks=True,
                elem_classes="scrollable-markdown",
            )
        save_button = gr.Button(_("save_btn"), variant="primary", visible=False)

        with gr.Row():
            reset_button = gr.Button(_("reset_btn"), variant="secondary")
            quit_button = gr.Button(_("quit_btn"), variant="stop")

        # EVENT HANDLERS
        browse_button.click(fn=browse_local_files, inputs=[], outputs=[file_path_input])

        def _provider_change(p):
            no_models = _("no_models_found")
            is_gemini = str(p).lower().startswith("g")
            
            if is_gemini:
                return (
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False) # extraction group hidden
                )
            
            if str(p).lower().startswith("olla"):
                models = list_ollama_models() or [no_models]
                val = models[0] if models and models[0] != no_models else ""
                return (
                    gr.update(visible=False),
                    gr.update(visible=True, choices=models, value=val),
                    gr.update(visible=False),
                    gr.update(visible=True)
                )
                
            lm_models = list_lmstudio_models() or [no_models]
            lm_val = lm_models[0] if lm_models and lm_models[0] != no_models else ""
            return (
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True, choices=lm_models, value=lm_val),
                gr.update(visible=True)
            )

        provider_radio.change(
            fn=_provider_change,
            inputs=[provider_radio],
            outputs=[gemini_model, ollama_model, lmstudio_model, extraction_group],
        )

        def _refresh_models(provider):
            no_models = _("no_models_found")
            if str(provider).lower().startswith("olla"):
                models = list_ollama_models() or [no_models]
                val = models[0] if models and models[0] != no_models else ""
                return gr.update(choices=models, value=val)
            if str(provider).lower().startswith("lm"):
                models = list_lmstudio_models() or [no_models]
                val = models[0] if models and models[0] != no_models else ""
                return gr.update(choices=models, value=val)
            return gr.update()

        refresh_btn.click(
            fn=_refresh_models,
            inputs=[provider_radio],
            outputs=[ollama_model], 
        )

        process_btn.click(
            fn=process_video,
            inputs=[
                file_path_input,
                provider_radio,
                response_language,
                gemini_model,
                ollama_model,
                lmstudio_model,
                frame_interval,
                max_frames
            ],
            outputs=[output_text, save_button],
        )

        save_button.click(fn=save_extracted_text, inputs=[output_text, file_path_input], outputs=[])

        js_copy_text = "(text) => { navigator.clipboard.writeText(text); }"
        copy_text_button.click(
            fn=notify_copy, inputs=[], outputs=[]
        ).then(fn=None, inputs=[output_text], js=js_copy_text)

        reset_button.click(
            fn=reset_fields,
            inputs=[],
            outputs=[file_path_input, output_text, save_button],
        )

        quit_button.click(fn=quit_app, inputs=[], outputs=[])

    return demo
