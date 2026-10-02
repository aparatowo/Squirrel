# note_editor.py - Standard Note entry handler
from appconfig import cfg

class NoteEditor:
    def __init__(self, storage_manager):
        self.storage = storage_manager

    def validate_title(self, title):
        """Ensures title is provided and valid."""
        cleaned_title = title.strip()
        if not cleaned_title:
            print("[NOTE ERROR] Title cannot be empty!")
            return None
        
        if len(cleaned_title) > cfg.get("NOTE_TITLE_MAX_LEN"):
            cleaned_title = cleaned_title[:cfg.get("NOTE_TITLE_MAX_LEN")].rstrip()
            
        return cleaned_title

    def create_note(self, title, body_content=""):
        """Creates a note only if a valid title is provided."""
        valid_title = self.validate_title(title)
        if not valid_title:
            print("[NOTE ABORT] Cannot proceed to body editor without a valid title.")
            return False

        if len(body_content) > cfg.get("NOTE_BODY_MAX_CHARS"):
            print(f"[NOTE WARN] Body exceeds {cfg.get("NOTE_BODY_MAX_CHARS")} chars. Truncating...")
            body_content = body_content[:cfg.get("NOTE_BODY_MAX_CHARS")]

        print(f"[NOTE ACTION] Creating note: '{valid_title}'")
        success = self.storage.save_item("notes", valid_title, body_content)
        
        if success:
            print(f"[NOTE SUCCESS] Note '{valid_title}' saved successfully.")
        else:
            print(f"[NOTE ERROR] Failed to save note '{valid_title}'.")
        return success