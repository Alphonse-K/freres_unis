from pathlib import Path
import uuid
import shutil
from fastapi import UploadFile

UPLOAD_ROOT = Path("/app/uploads")

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