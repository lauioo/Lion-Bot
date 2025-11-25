import json
import os

# Ensures the data folder exists
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# ------------------------------------------------------------
# Safe JSON Loader
# ------------------------------------------------------------
def load_json(path: str):
    """
    Safely loads a JSON file.
    If it does not exist or fails, returns an empty dict instead of crashing.
    """
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


# ------------------------------------------------------------
# Safe JSON Saver
# ------------------------------------------------------------
def save_json(path: str, data: dict):
    """
    Safely writes a dictionary to a JSON file.
    Creates the folder if necessary.
    """

    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
