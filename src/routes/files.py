# src/routes/files.py - FIXED VERSION
from fastapi import APIRouter, HTTPException, Depends, Path as FastAPIPath
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Literal
import os
from pathlib import Path as PathLib  # Rename pathlib Path to avoid conflict
from src.core.permissions import Permissions
from src.core.auth_dependencies import require_permission

from src.core.database import get_db
from src.models.clients import Client, ClientApproval

router = APIRouter(prefix="/files", tags=["files"])

# Type definitions for documentation
AllowedDocType = Literal["face", "badge", "id-recto", "id-verso", "magnetic-card"]

@router.get(
    "/clients/{client_id}/documents",
    summary="Get all document URLs for a client",
    description="""
    Get URLs for all available documents for a specific client.
    
    Returns direct static URLs that can be used in:
    - `<iframe>` tags to display PDFs
    - `<a>` tags for downloads
    - `<img>` tags for images
    
    Also returns API endpoints for each document type.
    """,
    response_description="Dictionary of all available documents with URLs"
)
async def get_client_documents(
    client_id: int = FastAPIPath(..., description="Client ID", examples=2),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.READ_CLIENT))
):
    """
    Get ALL document URLs for a client.
    Returns URLs that frontend can use directly.
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    approval = db.query(ClientApproval).filter(
        ClientApproval.client_id == client_id
    ).first()
    
    if not approval:
        return {
            "client_id": client_id,
            "client_name": f"{client.first_name} {client.last_name}",
            "has_documents": False,
            "documents": {}
        }
    
    # Document type definitions
    doc_types = [
        ("face", "face_photo", "Face Photo"),
        ("badge", "badge_photo", "Badge Photo"),
        ("id-recto", "id_photo_recto", "ID Card Front"),
        ("id-verso", "id_photo_verso", "ID Card Back"),
        ("magnetic-card", "magnetic_card_photo", "Magnetic Card")
    ]
    
    # BASE_URL = "http://localhost:8000"  # In production, use your domain
    BASE_URL = "http://78.47.72.137:8030"  # In production, use your domain

    documents = {}
    
    for url_key, db_field, description in doc_types:
        file_path = getattr(approval, db_field, None)
        if file_path:
            # Create clean URL
            if file_path.startswith("uploads/"):
                clean_path = file_path
            else:
                clean_path = f"uploads/{file_path}"
            
            filename = PathLib(file_path).name
            
            documents[url_key] = {
                "url": f"{BASE_URL}/{clean_path}",
                "filename": filename,
                "api_endpoint": f"/api/v1/files/clients/{client_id}/document/{url_key}",
                "description": description,
                "type": url_key
            }
    
    return {
        "client_id": client_id,
        "client_name": f"{client.first_name} {client.last_name}",
        "has_documents": len(documents) > 0,
        "documents": documents
    }

@router.get(
    "/clients/{client_id}/document/{doc_type}",
    summary="Get information about a specific client document",
    description="""
    Get information about a specific document for a client.
    Returns JSON with the file URL and metadata (same as the individual items in /documents endpoint).
    
    **Available document types:**
    - `face` - Client's face photo
    - `badge` - Client's badge photo  
    - `id-recto` - ID card front side (recto)
    - `id-verso` - ID card back side (verso)
    - `magnetic-card` - Magnetic card photo
    """,
    responses={
        200: {
            "description": "Document information",
            "content": {
                "application/json": {
                    "example": {
                        "url": "http://localhost:8000/uploads/face_photo.jpg",
                        "filename": "face_photo.jpg",
                        "api_endpoint": "/api/v1/files/clients/2/document/face",
                        "description": "Face Photo",
                        "type": "face"
                    }
                }
            }
        },
        400: {"description": "Invalid document type"},
        404: {"description": "Client or document not found"}
    }
)
async def get_client_document(
    client_id: int = FastAPIPath(..., description="Client ID", examples=2),
    doc_type: AllowedDocType = FastAPIPath(
        ...,
        description="Document type. Options: face, badge, id-recto, id-verso, magnetic-card",
        examples="face"
    ),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission(Permissions.READ_CLIENT))
):
    """
    Get information about a specific client document.
    Returns metadata including the file URL.
    """
    # Map to database field
    doc_map = {
        "face": "face_photo",
        "badge": "badge_photo", 
        "id-recto": "id_photo_recto",
        "id-verso": "id_photo_verso",
        "magnetic-card": "magnetic_card_photo"
    }
    
    # Document descriptions
    doc_descriptions = {
        "face": "Face Photo",
        "badge": "Badge Photo",
        "id-recto": "ID Card Front",
        "id-verso": "ID Card Back",
        "magnetic-card": "Magnetic Card"
    }
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    approval = db.query(ClientApproval).filter(
        ClientApproval.client_id == client_id
    ).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="No approval record found")
    
    file_path = getattr(approval, doc_map[doc_type], None)
    
    if not file_path:
        raise HTTPException(
            status_code=404, 
            detail=f"{doc_type.replace('-', ' ').title()} not found"
        )
    
    # Clean the path
    if file_path.startswith("uploads/"):
        clean_path = file_path
    else:
        clean_path = f"uploads/{file_path}"
    
    BASE_URL = "http://78.47.72.137:8030"  # Change to your actual domain

    
    return {
        "url": f"{BASE_URL}/{clean_path}",
        "filename": os.path.basename(file_path),
        "api_endpoint": f"/api/v1/files/clients/{client_id}/document/{doc_type}",
        "description": doc_descriptions.get(doc_type, doc_type),
        "type": doc_type
    }

@router.get(
    "/health",
    summary="Check file service health",
    description="Simple health check endpoint for the file service",
    response_description="Service status"
)
async def health_check(current_user = Depends(require_permission(Permissions.READ_CLIENT))):
    return {"status": "ok", "service": "file-service"}