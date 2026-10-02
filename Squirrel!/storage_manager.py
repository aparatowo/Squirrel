# storage_manager.py - Generic file manager with full logging
import os
from charmap import ascii_name

_ILLEGAL = '\\/:*?"<>|'          # characters a FAT file name cannot hold


def file_stem(title):
    """The file name (without extension) for a title: ASCII, lower case, '_' for spaces and illegal characters.

    Polish letters become plain ones (ż -> z), so two titles may share a stem: callers that must not
    overwrite an existing item ask unique_title() first.  The real title stays in the file's first line.
    """
    name = ascii_name(title).strip().lower().replace(" ", "_")
    name = "".join("_" if (c in _ILLEGAL or ord(c) < 32) else c for c in name)
    return name or "untitled"

class StorageManager:
    def __init__(self, base_dir="/flash/apps/Squirrel"):
        self.base_dir = base_dir
        print(f"[STORAGE INIT] Initializing StorageManager at: {self.base_dir}")
        self._ensure_dir(self.base_dir)

    def _ensure_dir(self, path):
        """Helper method to ensure target directory exists."""
        try:
            os.stat(path)
            print(f"[STORAGE FS] Directory exists: {path}")
        except OSError:
            try:
                print(f"[STORAGE FS] Creating missing directory: {path}")
                os.mkdir(path)
            except Exception as e:
                print(f"[STORAGE ERROR] Failed to create directory {path}: {e}")

    def list_items(self, collection_name, extension=".txt", default_content=None):
        """Returns a formatted item list. Empty folder returns a clean empty state, not an error."""
        target_dir = f"{self.base_dir}/{collection_name.lower()}"
        print(f"[STORAGE READ] Reading collection '{collection_name}' from {target_dir}")
        self._ensure_dir(target_dir)

        items = []

        try:
            files = sorted([f for f in os.listdir(target_dir) if f.endswith(extension)])
            print(f"[STORAGE FS] Found {len(files)} files ({extension}) in {target_dir}")
            
            if not files and default_content:
                print(f"[STORAGE FS] Collection {collection_name} is empty. Creating default sample file...")
                self.save_item(collection_name, "sample", default_content, extension)
                files = sorted([f for f in os.listdir(target_dir) if f.endswith(extension)])

            for idx, filename in enumerate(files, 1):
                stem = filename[:-len(extension)]
                clean_name = stem.replace("_", " ")
                if clean_name:
                    clean_name = clean_name[0].upper() + clean_name[1:]
                if extension == ".txt":
                    real = self._real_title(f"{target_dir}/{filename}", stem)
                    if real:
                        clean_name = real                    # the title as typed, with its Polish letters
                items.append(f"{idx}. {clean_name}")

        except Exception as e:
            print(f"[STORAGE ERROR] Exception while listing {collection_name}: {e}")

        print(f"[STORAGE RESULT] Returned {len(items)} items for menu {collection_name}")
        return items

    def count_items(self, collection_name, extension=".txt"):
        """Returns the number of files in a collection. Used for prev/next navigation."""
        target_dir = f"{self.base_dir}/{collection_name.lower()}"
        try:
            return len([f for f in os.listdir(target_dir) if f.endswith(extension)])
        except Exception:
            return 0

    def _get_filepath_by_index(self, collection_name, index, extension=".txt"):
        """Maps menu list index to physical filepath."""
        target_dir = f"{self.base_dir}/{collection_name.lower()}"
        try:
            files = sorted([f for f in os.listdir(target_dir) if f.endswith(extension)])
            if 0 <= index < len(files):
                filepath = f"{target_dir}/{files[index]}"
                print(f"[STORAGE MAP] Index {index} -> Filepath: {filepath}")
                return filepath
            else:
                print(f"[STORAGE WARN] Index {index} out of bounds (Available files: {len(files)})")
        except Exception as e:
            print(f"[STORAGE ERROR] Error mapping filepath for {collection_name}: {e}")
        return None

    def read_item(self, collection_name, index, extension=".txt"):
        """Reads content from the specified file."""
        print(f"[STORAGE ACTION] Reading content for {collection_name}, file index: {index}")
        filepath = self._get_filepath_by_index(collection_name, index, extension)
        if not filepath:
            return None
        try:
            with open(filepath, "r") as f:
                content = f.read()
                print(f"[STORAGE SUCCESS] Read {len(content)} bytes from {filepath}")
                return content
        except Exception as e:
            print(f"[STORAGE ERROR] Failed reading file {filepath}: {e}")
            return None

    def stems(self, collection_name, extension=".txt"):
        """File names without the extension, in the order list_items() shows them (sorted)."""
        target_dir = f"{self.base_dir}/{collection_name.lower()}"
        try:
            return [f[:-len(extension)] for f in sorted(os.listdir(target_dir)) if f.endswith(extension)]
        except OSError:
            return []

    def _real_title(self, path, stem):
        """The first line of a text file, if it is what the file name was made from (else None).

        File names are plain ASCII, so "Zażółć" is stored as zazolc.txt; the list shows the first line instead.
        """
        try:
            with open(path, "r") as f:
                first = f.readline().strip()
        except Exception:
            return None
        if not first:
            return None
        full = file_stem(first)
        base = stem
        head, sep, tail = stem.rpartition("_")           # "buy_milk_2" -> "buy_milk" (a number added for uniqueness)
        if sep and tail.isdigit():
            base = head
        if full.startswith(stem) or full.startswith(base):
            return first
        return None

    def unique_title(self, collection_name, title, max_len=30, extension=".txt"):
        """`title`, or `title 2`, `title 3` ... - the first one whose file does not exist yet.

        save_item overwrites a file of the same name, so anything that must not replace an
        existing item (a mind dump, say) asks here first.
        """
        target_dir = f"{self.base_dir}/{collection_name.lower()}"
        base = title.strip()[:max_len]
        candidate, n = base, 2
        while self._exists(f"{target_dir}/{file_stem(candidate)}{extension}"):
            suffix = " %d" % n
            candidate = base[:max_len - len(suffix)] + suffix
            n += 1
        return candidate

    @staticmethod
    def _exists(path):
        try:
            os.stat(path)
            return True
        except OSError:
            return False

    def save_item(self, collection_name, title, content, extension=".txt"):
        """Creates or updates a file on storage."""
        target_dir = f"{self.base_dir}/{collection_name.lower()}"
        self._ensure_dir(target_dir)
        
        filepath = f"{target_dir}/{file_stem(title)}{extension}"
        print(f"[STORAGE ACTION] Saving file: {filepath}")
        try:
            with open(filepath, "w") as f:
                f.write(content)
            print(f"[STORAGE SUCCESS] Saved file {filepath}")
            return True
        except Exception as e:
            print(f"[STORAGE ERROR] Failed saving file {filepath}: {e}")
            return False

    def update_item(self, collection_name, old_index, new_title, content, extension=".txt"):
        """Edit an existing file: save under new title, delete old file if title changed.

        If the title is unchanged the old file is simply overwritten in place.
        Returns True on success, False on any error.
        """
        old_filepath = self._get_filepath_by_index(collection_name, old_index, extension)
        target_dir = f"{self.base_dir}/{collection_name.lower()}"
        new_filepath = f"{target_dir}/{file_stem(new_title)}{extension}"
        if new_filepath != old_filepath and self._exists(new_filepath):
            # renaming onto another item's name must not overwrite that item
            new_title = self.unique_title(collection_name, new_title, max(len(new_title), 8), extension)
            new_filepath = f"{target_dir}/{file_stem(new_title)}{extension}"

        print(f"[STORAGE ACTION] Updating: {old_filepath} -> {new_filepath}")

        # Write new content first — if this fails, the old file is untouched
        try:
            with open(new_filepath, "w") as f:
                f.write(content)
            print(f"[STORAGE SUCCESS] Written new file: {new_filepath}")
        except Exception as e:
            print(f"[STORAGE ERROR] Failed writing {new_filepath}: {e}")
            return False

        # Remove old file only when the title (filename) actually changed
        if old_filepath and old_filepath != new_filepath:
            try:
                os.remove(old_filepath)
                print(f"[STORAGE SUCCESS] Removed old file: {old_filepath}")
            except Exception as e:
                print(f"[STORAGE WARN] Could not remove old file {old_filepath}: {e}")
                # Non-fatal — new file was already saved successfully

        return True

    def delete_path(self, filepath):
        """Delete one file by absolute path.  Refuses anything outside base_dir."""
        print(f"[STORAGE ACTION] Delete request for path: {filepath}")
        if (not filepath or not filepath.startswith(self.base_dir + "/")
                or ".." in filepath.split("/")):
            print(f"[STORAGE WARN] Refusing to delete outside {self.base_dir}: {filepath}")
            return False
        try:
            os.remove(filepath)
            print(f"[STORAGE SUCCESS] Deleted file: {filepath}")
            return True
        except Exception as e:
            print(f"[STORAGE ERROR] Failed deleting file {filepath}: {e}")
            return False

    def delete_item(self, collection_name, index, extension=".txt"):
        """Deletes a file from storage."""
        print(f"[STORAGE ACTION] Delete request for {collection_name}, index: {index}")
        filepath = self._get_filepath_by_index(collection_name, index, extension)
        if filepath:
            try:
                os.remove(filepath)
                print(f"[STORAGE SUCCESS] Deleted file: {filepath}")
                return True
            except Exception as e:
                print(f"[STORAGE ERROR] Failed deleting file {filepath}: {e}")
        return False