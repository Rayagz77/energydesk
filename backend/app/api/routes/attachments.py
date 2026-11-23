"""Pieces jointes : controle de taille et de type, stockage objet, telechargement controle."""

import hashlib
import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_ticket, get_current_user
from app.core.config import get_settings
from app.core.logging import security_logger
from app.db.session import get_db
from app.models import Attachment, Role, Ticket, User
from app.schemas import AttachmentOut
from app.services.files import ALLOWED_TYPES, detect_content_type, sanitize_filename
from app.services.storage import Storage, get_storage

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pieces jointes"])


@router.post(
    "/tickets/{ticket_id}/attachments",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_attachment(
    request: Request,
    file: UploadFile = File(...),
    ticket: Ticket = Depends(get_accessible_ticket),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> Attachment:
    max_bytes = get_settings().max_upload_bytes
    # On lit au plus max+1 octets : suffisant pour savoir si la limite est depassee.
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        security_logger.warning(
            "fichier refuse : trop volumineux",
            extra={"event": "upload_rejected", "reason": "too_large", "user_id": str(user.id)},
        )
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Fichier trop volumineux (maximum {get_settings().max_upload_mb} Mo).",
        )
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Fichier vide.")

    content_type = detect_content_type(data)
    if content_type not in ALLOWED_TYPES:
        security_logger.warning(
            "fichier refuse : type non autorise",
            extra={
                "event": "upload_rejected",
                "reason": "type",
                "declared_type": file.content_type,
                "user_id": str(user.id),
            },
        )
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Type de fichier non autorise. Formats acceptes : PDF, PNG, JPEG.",
        )

    attachment_id = uuid.uuid4()
    # La cle ne contient jamais le nom d'origine (pas d'injection de chemin possible).
    object_key = f"tickets/{ticket.id}/{attachment_id}"
    storage.put_object(object_key, data, content_type)

    attachment = Attachment(
        id=attachment_id,
        ticket_id=ticket.id,
        uploaded_by_id=user.id,
        original_filename=sanitize_filename(file.filename),
        object_key=object_key,
        content_type=content_type,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    logger.info(
        "piece jointe ajoutee",
        extra={
            "event": "attachment_uploaded",
            "ticket_id": str(ticket.id),
            "attachment_id": str(attachment.id),
            "size_bytes": attachment.size_bytes,
        },
    )
    return attachment


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> StreamingResponse:
    attachment = db.get(Attachment, attachment_id)
    allowed = attachment is not None and (
        user.role == Role.AGENT or attachment.ticket.created_by_id == user.id
    )
    if not allowed:
        security_logger.warning(
            "telechargement refuse",
            extra={
                "event": "access_denied",
                "user_id": str(user.id),
                "attachment_id": str(attachment_id),
            },
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Piece jointe introuvable.")
    return StreamingResponse(
        storage.iter_object(attachment.object_key),
        media_type=attachment.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{attachment.original_filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )
