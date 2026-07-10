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
    list_lmstudio_models,
    get_sorted_gemini_models,
    query_gemini,
    _is_model_loaded_ollama,
    _is_model_loaded_lmstudio,
    _trigger_lmstudio_load
)
from .config import (
    get_gemini_api_key,
    setup_logging,
    _
)

def browse_local_files(existing_paths=""):
    """Open a native file dialog to select files."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        files = filedialog.askopenfilenames(
            title=_("dialog_select_title"),
            filetypes=[
                (_("dialog_filter_video"), "*.mp4 *.mov *.mkv *.avi"),
                (_("dialog_filter_all"), "*.*"),
            ],
            parent=root,
        )
        root.destroy()

        if files:
            new_paths = "\n".join(list(files))
            existing = existing_paths.strip() if existing_paths else ""
            if existing:
                return f"{existing}\n{new_paths}"
            return new_paths
        return gr.update()
    except Exception as e:
        logging.error(f"Error selecting files: {e}")
        gr.Error(_("dialog_err_select").format(str(e)))
        return gr.update()

def browse_local_folders(existing_paths=""):
    """Open a native folder dialog and recursively get all files inside."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        import os

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        folder = filedialog.askdirectory(
            title=_("dialog_select_type_title"),
            parent=root,
        )
        root.destroy()

        if folder:
            SUPPORTED_EXTS = {".mp4", ".mov", ".mkv", ".avi"}
            expanded_paths = []
            for root_dir, dirs, files in os.walk(folder):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_EXTS:
                        expanded_paths.append(os.path.join(root_dir, f))
            
            if expanded_paths:
                new_paths = "\n".join(expanded_paths)
                existing = existing_paths.strip() if existing_paths else ""
                if existing:
                    return f"{existing}\n{new_paths}"
                return new_paths
        return gr.update()
    except Exception as e:
        logging.error(f"Error selecting folders: {e}")
        gr.Error(_("dialog_err_select").format(str(e)))
        return gr.update()

def save_extracted_text(extracted_text, file_paths_text="", output_format=".txt"):
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
            initialfile = f"{video_name}_description{output_format}"
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            initialfile = f"video_analysis_{timestamp}{output_format}"

        target_path = filedialog.asksaveasfilename(
            title=_("dialog_save_title"),
            initialfile=initialfile,
            defaultextension=output_format,
            filetypes=[
                (_("dialog_filter_md") if output_format == ".md" else "Text Files", f"*{output_format}"),
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

def preset_query_summary():
    return _("preset_summary_val")

def preset_query_todo():
    return _("preset_todo_val")

def preset_query_fix():
    return _("preset_fix_val")


def process_video(file_paths_text, provider, response_language, gemini_model, ollama_model, lmstudio_model, frame_interval, max_frames, output_format=".txt"):
    """Process video files based on provider."""
    if not file_paths_text or not file_paths_text.strip():
        yield _("proc_no_files"), gr.update(visible=False), gr.update(visible=False), gr.update()
        return

    raw_paths = [p.strip() for p in file_paths_text.strip().split("\n") if p.strip()]
    
    SUPPORTED_EXTS = {".mp4", ".mov", ".mkv", ".avi"}
    expanded_paths = []
    for p in raw_paths:
        if os.path.isdir(p):
            for root_dir, dirs, files in os.walk(p):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_EXTS:
                        expanded_paths.append(os.path.join(root_dir, f))
        else:
            expanded_paths.append(p)

    file_paths_text_new = "\n".join(expanded_paths)

    if not expanded_paths:
        yield _("proc_no_files"), gr.update(visible=False), gr.update(visible=False), file_paths_text
        return

    session_text = ""
    total_files = len(expanded_paths)

    for index, file_path in enumerate(expanded_paths, 1):
        filename = os.path.basename(file_path)
        header = f"### File {index}/{total_files}: {filename}\n\n"

        yield session_text + header + _("proc_processing"), gr.update(visible=False), gr.update(visible=False), file_paths_text_new

        try:
            if not os.path.isfile(file_path):
                logging.error(f"File not found: {file_path}")
                result = _("proc_file_not_found").format(file_path)
                yield session_text + header + result, gr.update(visible=False), gr.update(visible=False), file_paths_text_new
                session_text += header + result + "\n\n---\n\n"
                continue

            if provider == "Google":
                msg = _("uploading_to_gemini")
                yield session_text + header + msg, gr.update(visible=False), gr.update(visible=False), file_paths_text_new
                
                result = analyze_video_gemini(file_path, gemini_model, response_language, output_format)
            else:
                # Ollama or LM Studio -> need to extract frames
                if max_frames and int(max_frames) > 0:
                    msg = _("frame_extraction_info").format(frame_interval, max_frames)
                else:
                    msg = _("frame_extraction_info_no_limit").format(frame_interval)
                yield session_text + header + msg, gr.update(visible=False), gr.update(visible=False), file_paths_text_new
                
                frames = extract_frames(file_path, interval=int(frame_interval), max_frames=int(max_frames or 0))
                if not frames:
                    result = _("proc_error").format("No frames extracted.")
                else:
                    msg = _("frame_extraction_done").format(len(frames), provider)
                    yield session_text + header + msg, gr.update(visible=False), gr.update(visible=False), file_paths_text_new
                    
                    model_name = ollama_model if provider == "Ollama" else lmstudio_model
                    
                    yield session_text + header + _("llm_checking_model"), gr.update(visible=False), gr.update(visible=False), file_paths_text_new
                    if provider == "LM Studio":
                        _trigger_lmstudio_load(model_name)
                    ready = False
                    elapsed = 0
                    while elapsed < 60:
                        if provider == "Ollama" and _is_model_loaded_ollama(model_name):
                            ready = True
                            break
                        if provider == "LM Studio" and _is_model_loaded_lmstudio(model_name):
                            ready = True
                            break
                        yield session_text + header + _("llm_model_loading").format(elapsed=elapsed), gr.update(visible=False), gr.update(visible=False), file_paths_text_new
                        import time
                        time.sleep(2)
                        elapsed += 2
                    
                    if not ready:
                        if provider == "Ollama":
                            yield session_text + header + _("llm_model_sending"), gr.update(visible=False), gr.update(visible=False), file_paths_text_new
                        else:
                            result = _("llm_model_timeout_lmstudio")
                            yield session_text + header + result, gr.update(visible=False), gr.update(visible=False), file_paths_text_new
                            session_text += header + result + "\n\n---\n\n"
                            cleanup_frames()
                            continue
                    else:
                        yield session_text + header + _("llm_model_ready"), gr.update(visible=False), gr.update(visible=False), file_paths_text_new

                    yield session_text + header + _("video_analysis_in_progress"), gr.update(visible=False), gr.update(visible=False), file_paths_text_new

                    if provider == "Ollama":
                        result = analyze_frames_ollama(frames, model_name, response_language, output_format)
                    else:
                        result = analyze_frames_lmstudio(frames, model_name, response_language, output_format)
                    cleanup_frames()

            # Save individual description text file
            if result and not any(result.startswith(prefix) for prefix in ["[Error", "[No response", "[Gemini API Error", "[Ollama Vision Error", "[LM Studio Vision Error"]):
                try:
                    from pathlib import Path
                    video_path_obj = Path(file_path)
                    video_name = video_path_obj.stem
                    out_file = video_path_obj.with_name(f"{video_name}_description{output_format}")
                    with open(out_file, "w", encoding="utf-8") as f:
                        f.write(result.strip())
                    logging.info(f"Auto-saved individual analysis to {out_file}")
                except Exception as e:
                    logging.error(f"Error auto-saving individual analysis for {file_path}: {e}", exc_info=True)

        except Exception as e:
            logging.error(f"Error processing {file_path}: {e}", exc_info=True)
            result = _("proc_error").format(str(e))

        yield session_text + header + result, gr.update(visible=False), gr.update(visible=False), file_paths_text_new
        session_text += header + result + "\n\n---\n\n"

    session_text = session_text.strip()
    if session_text.endswith("---"):
        session_text = session_text[:-3].strip()

    yield session_text, gr.update(visible=True), gr.update(visible=True), file_paths_text_new



def reset_fields():
    return (
        "",                          
        _("output_placeholder"),     
        gr.update(visible=False),    
        "",                          # user_query
        _("response_placeholder"),   # ai_response
        gr.update(visible=False),    # submit_query_button
        ".txt",                      # output_format
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
    
    gemini_api_key = get_gemini_api_key()
    gemini_models = get_sorted_gemini_models(gemini_api_key)
    has_gemini = len(gemini_models) > 0

    with gr.Blocks(title="Video Analyzer Utility") as demo:
        title_markdown = gr.Markdown(_("title"))

        with gr.Row():
            file_path_input = gr.Textbox(
                label=_("file_path_label"),
                placeholder=_("file_path_placeholder"),
                lines=3,
            )
        with gr.Row():
            browse_files_btn = gr.Button(_("dialog_btn_files"), variant="secondary")
            browse_folders_btn = gr.Button(_("dialog_btn_folder"), variant="secondary")

        config_accordion = gr.Accordion(label=_("config_accordion"), open=True)
        with config_accordion:
            response_language = gr.Radio(
                choices=["Italiano", "English"],
                value="Italiano",
                label=_("response_language_label"),
            )
            
            output_format = gr.Radio(
                choices=[".txt", ".md"],
                value=".txt",
                label=_("output_format_label"),
            )
            
            provider_choices = ["Google", "Ollama", "LM Studio"] if has_gemini else ["Ollama", "LM Studio"]
            provider_radio = gr.Radio(
                choices=provider_choices,
                value="Google" if has_gemini else "Ollama",
                label=_("provider_label"),
            )

            google_brand_radio = gr.Radio(
                choices=["Gemini", "Gemma"],
                value="Gemini",
                label=_("model_family_label"),
                visible=has_gemini,
            )


            initial_filtered_models = [m for m in gemini_models if "gemini" in m.lower()]
            if not initial_filtered_models and gemini_models:
                initial_filtered_models = [m for m in gemini_models if "gemma" in m.lower()]

            default_val = None
            for m in initial_filtered_models:
                if "gemini-flash-latest" in m.lower():
                    default_val = m
                    break
            if not default_val and initial_filtered_models:
                default_val = initial_filtered_models[0]

            gemini_model = gr.Dropdown(
                choices=initial_filtered_models,
                value=default_val,
                allow_custom_value=True,
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
                    frame_interval = gr.Number(value=2, label=_("frame_interval_label"), precision=0, minimum=1)
                    max_frames = gr.Number(value=0, label=_("max_frames_label"), precision=0, minimum=0)

        with gr.Row():
            process_btn = gr.Button(_("process_btn"), variant="primary")
            stop_process_btn = gr.Button(_("stop_btn"), variant="stop", visible=False)

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

        # ── AI Assistant section ──────────────────────────────────
        assistant_accordion = gr.Accordion(_("assistant_accordion"), open=True)
        with assistant_accordion:
            # Provider Radio — Google only if API key and models are available
            assist_provider_choices = ["Google", "Ollama", "LM Studio"] if has_gemini else ["Ollama", "LM Studio"]
            assist_provider = gr.Radio(
                choices=assist_provider_choices,
                value="Google" if has_gemini else "Ollama",
                label=_("assist_provider_label"),
            )

            assist_google_brand_radio = gr.Radio(
                choices=["Gemini", "Gemma"],
                value="Gemini",
                label=_("model_family_label"),
                visible=has_gemini,
            )

            initial_filtered_models = [m for m in gemini_models if "gemini" in m.lower()]
            if not initial_filtered_models and gemini_models:
                initial_filtered_models = [m for m in gemini_models if "gemma" in m.lower()]

            default_val = None
            for m in initial_filtered_models:
                if "gemini-flash-latest" in m.lower():
                    default_val = m
                    break
            if not default_val and initial_filtered_models:
                default_val = initial_filtered_models[0]

            assist_gemini_model = gr.Dropdown(
                choices=initial_filtered_models,
                value=default_val,
                allow_custom_value=True,
                label=_("gemini_model_label"),
                visible=has_gemini,
            )

            try:
                _ollama_init = list_ollama_models() if not has_gemini else []
            except Exception:
                _ollama_init = []
            _ollama_val = _ollama_init[0] if _ollama_init else ""

            assist_ollama_model = gr.Dropdown(
                choices=_ollama_init,
                value=_ollama_val,
                allow_custom_value=True,
                label=_("ollama_model_label"),
                visible=not has_gemini,
            )

            assist_lmstudio_model = gr.Dropdown(
                choices=[],
                value="",
                allow_custom_value=True,
                label=_("lmstudio_model_label"),
                visible=False,
            )

            # Response language selector for AI assistant
            assist_response_language = gr.Radio(
                choices=["Italiano", "English"],
                value="Italiano",
                label=_("response_language_label"),
            )

            with gr.Row():
                preset_summary_button = gr.Button(_("preset_summary"), variant="secondary")
                preset_todo_button = gr.Button(_("preset_todo"), variant="secondary")
                preset_fix_button = gr.Button(_("preset_fix"), variant="secondary")

            fix_text_mode = gr.State(False)
            user_query = gr.Textbox(label=_("enter_query_label"))
            with gr.Row():
                submit_query_button = gr.Button(_("submit_query_btn"), variant="primary", visible=False)
                stop_query_btn = gr.Button(_("stop_btn"), variant="stop", visible=False)

        with gr.Accordion(_("ai_response_accordion")):
            copy_response_button = gr.Button(_("copy_response"), variant="secondary", size="sm")
            ai_response = gr.Markdown(_("response_placeholder"), container=True, line_breaks=True, elem_classes="scrollable-markdown")

        with gr.Row():
            reset_button = gr.Button(_("reset_btn"), variant="secondary")
            quit_button = gr.Button(_("quit_btn"), variant="stop")


        # EVENT HANDLERS
        browse_files_btn.click(fn=browse_local_files, inputs=[file_path_input], outputs=[file_path_input])
        browse_folders_btn.click(fn=browse_local_folders, inputs=[file_path_input], outputs=[file_path_input])

        def _provider_change(p):
            no_models = _("no_models_found")
            is_google = str(p).lower().startswith("g")
            
            if is_google:
                return (
                    gr.update(visible=True),
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
                gr.update(visible=False),
                gr.update(visible=True, choices=lm_models, value=lm_val),
                gr.update(visible=True)
            )

        provider_radio.change(
            fn=_provider_change,
            inputs=[provider_radio],
            outputs=[google_brand_radio, gemini_model, ollama_model, lmstudio_model, extraction_group],
        )

        def _update_google_models(brand):
            filtered = [m for m in gemini_models if brand.lower() in m.lower()]
            val = None
            if brand.lower() == "gemini":
                for m in filtered:
                    if "gemini-flash-latest" in m.lower():
                        val = m
                        break
            if not val and filtered:
                val = filtered[0]
            return gr.update(choices=filtered, value=val)

        google_brand_radio.change(
            fn=_update_google_models,
            inputs=[google_brand_radio],
            outputs=[gemini_model],
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

        proc_start = process_btn.click(
            fn=lambda: (gr.update(visible=False), gr.update(visible=True)),
            inputs=[],
            outputs=[process_btn, stop_process_btn]
        )
        proc_event = proc_start.then(
            fn=process_video,
            inputs=[
                file_path_input,
                provider_radio,
                response_language,
                gemini_model,
                ollama_model,
                lmstudio_model,
                frame_interval,
                max_frames,
                output_format,
            ],
            outputs=[output_text, save_button, submit_query_button, file_path_input],
        )
        proc_event.then(
            fn=lambda: (gr.update(visible=True), gr.update(visible=False)),
            inputs=[],
            outputs=[process_btn, stop_process_btn]
        )
        stop_process_btn.click(
            fn=lambda: (gr.update(visible=True), gr.update(visible=False)),
            inputs=[],
            outputs=[process_btn, stop_process_btn],
            cancels=[proc_event]
        )

        save_button.click(fn=save_extracted_text, inputs=[output_text, file_path_input, output_format], outputs=[])

        js_copy_text = "(text) => { navigator.clipboard.writeText(text); }"
        copy_text_button.click(
            fn=notify_copy, inputs=[], outputs=[]
        ).then(fn=None, inputs=[output_text], js=js_copy_text)

        # Assistant provider change
        def _assist_provider_change(p):
            no_models = _("no_models_found")
            if str(p).lower().startswith("g"):
                return (
                    gr.update(visible=True),
                    gr.update(visible=True),
                    gr.update(visible=False, choices=[], value=""),
                    gr.update(visible=False, choices=[], value=""),
                )
            if str(p).lower().startswith("olla"):
                models = list_ollama_models() or [no_models]
                val = models[0] if models and models[0] != no_models else ""
                return (
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=True, choices=models, value=val),
                    gr.update(visible=False, choices=[], value=""),
                )
            lm_models = list_lmstudio_models() or [no_models]
            lm_val = lm_models[0] if lm_models and lm_models[0] != no_models else ""
            return (
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False, choices=[], value=""),
                gr.update(visible=True, choices=lm_models, value=lm_val),
            )

        assist_provider.change(
            fn=_assist_provider_change,
            inputs=[assist_provider],
            outputs=[assist_google_brand_radio, assist_gemini_model, assist_ollama_model, assist_lmstudio_model],
        )

        def _update_assist_google_models(brand):
            filtered = [m for m in gemini_models if brand.lower() in m.lower()]
            val = None
            if brand.lower() == "gemini":
                for m in filtered:
                    if "gemini-flash-latest" in m.lower():
                        val = m
                        break
            if not val and filtered:
                val = filtered[0]
            return gr.update(choices=filtered, value=val)

        assist_google_brand_radio.change(
            fn=_update_assist_google_models,
            inputs=[assist_google_brand_radio],
            outputs=[assist_gemini_model],
        )

        # Preset query buttons
        preset_summary_button.click(fn=preset_query_summary, inputs=[], outputs=[user_query]).then(
            fn=lambda: False, inputs=[], outputs=[fix_text_mode]
        )
        preset_todo_button.click(fn=preset_query_todo, inputs=[], outputs=[user_query]).then(
            fn=lambda: False, inputs=[], outputs=[fix_text_mode]
        )
        preset_fix_button.click(fn=preset_query_fix, inputs=[], outputs=[user_query]).then(
            fn=lambda: True, inputs=[], outputs=[fix_text_mode]
        )

        # Submit query to AI (streaming)
        query_start = submit_query_button.click(
            fn=lambda: (gr.update(visible=False), gr.update(visible=True)),
            inputs=[],
            outputs=[submit_query_button, stop_query_btn]
        )
        query_event = query_start.then(
            fn=query_gemini,
            inputs=[
                user_query,
                output_text,
                assist_gemini_model,
                assist_provider,
                assist_ollama_model,
                assist_lmstudio_model,
                fix_text_mode,
                assist_response_language,
            ],
            outputs=[ai_response],
            stream_every=0.05,
        )
        query_event.then(
            fn=lambda: (gr.update(visible=True), gr.update(visible=False)),
            inputs=[],
            outputs=[submit_query_button, stop_query_btn]
        )
        stop_query_btn.click(
            fn=lambda: (gr.update(visible=True), gr.update(visible=False)),
            inputs=[],
            outputs=[submit_query_button, stop_query_btn],
            cancels=[query_event]
        )

        copy_response_button.click(
            fn=notify_copy, inputs=[], outputs=[]
        ).then(fn=None, inputs=[ai_response], js=js_copy_text)

        reset_button.click(
            fn=reset_fields,
            inputs=[],
            outputs=[
                file_path_input,
                output_text,
                save_button,
                user_query,
                ai_response,
                submit_query_button,
                output_format,
            ],
        ).then(fn=lambda: False, inputs=[], outputs=[fix_text_mode])

        quit_button.click(fn=quit_app, inputs=[], outputs=[])

    return demo
