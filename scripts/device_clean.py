# MicroPython cleanup script to run on the Pico W via: mpremote run scripts/device_clean.py
# Keeps only runtime files:
# - main.py, boot.py, *.json at root
# - lib/**/*.py under lib/
# Removes other files and empty directories.

import os

ROOT_KEEP_FILES = {"main.py", "boot.py"}


def is_dir(path: str) -> bool:
    try:
        os.listdir(path)
        return True
    except OSError:
        return False


def listdir(path: str):
    if path:
        return os.listdir(path)
    return os.listdir()


def join(path: str, name: str) -> str:
    return (path + "/" + name) if path else name


def should_keep_file(path: str, name: str, in_lib: bool) -> bool:
    if in_lib:
        return name.endswith(".py")
    # root
    if name in ROOT_KEEP_FILES:
        return True
    if name.endswith(".json"):
        return True
    return False


def clean(path: str, in_lib: bool = False) -> None:
    for name in listdir(path):
        p = join(path, name)
        if is_dir(p):
            next_in_lib = in_lib or p == "lib" or p.startswith("lib/")
            clean(p, next_in_lib)
            # Try to remove directory if empty
            try:
                os.rmdir(p)
            except OSError:
                pass
        else:
            if not should_keep_file(path, name, in_lib):
                try:
                    os.remove(p)
                except OSError:
                    pass


# Run cleanup from root
clean("")
print("CLEAN_DONE")
