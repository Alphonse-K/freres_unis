# import os
# import uuid
# from fastapi import UploadFile

# UPLOAD_ROOT = 'uploads'

# def save_image(file: UploadFile, folder: str):
#     os.makedirs(f"{UPLOAD_ROOT}/{folder}", exist_ok=True)
#     ext = file.filename.split(".")[-1]
#     filename = f"{uuid.uuid4()}.{ext}"
#     path = f"{UPLOAD_ROOT}/{folder}/{filename}"
#     with open(path, "wb") as f:
#         f.write(file.file.read())
#     return path

from pathlib import Path
import uuid
import shutil
from fastapi import UploadFile

UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "uploads"

def save_image(file: UploadFile, folder: str):
    folder = folder.strip().replace("..", "")
    
    folder_path = UPLOAD_ROOT / folder
    folder_path.mkdir(parents=True, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4()}.{ext}"

    file_path = folder_path / filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return f"/uploads/{folder}/{filename}"