# src/utils/file_upload.py
import os
import uuid
from fastapi import UploadFile

UPLOAD_ROOT = "uploads"

def save_image(file: UploadFile, folder: str) -> str:
    os.makedirs(f"{UPLOAD_ROOT}/{folder}", exist_ok=True)

    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    path = f"{UPLOAD_ROOT}/{folder}/{filename}"

    with open(path, "wb") as f:
        f.write(file.file.read())

    return f"/uploads/{folder}/{filename}"
