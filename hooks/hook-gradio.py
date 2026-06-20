module_collection_mode = {
    # Skip *.pyi file generation when the app is packaged with PyInstaller.
    # We must collect `gradio` package as source .py files.
    'gradio': 'py',  
}
