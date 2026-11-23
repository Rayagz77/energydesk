"""Schemas Pydantic : validation des entrees et forme des reponses de l'API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import Role, TicketCategory, TicketPriority, TicketStatus

EQUIPMENT_ID_PATTERN = r"^CPT-FICTIF-\d{6}$"


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Utilisateurs et authentification ----------
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Le nom doit contenir au moins 2 caracteres.")
        return value


class UserBrief(ORMModel):
    id: uuid.UUID
    full_name: str
    role: Role


class UserOut(ORMModel):
    id: uuid.UUID
    email: str  # deja valide a l'inscription ; les comptes agents peuvent utiliser un domaine interne
    full_name: str
    role: Role
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - type de jeton OAuth2, pas un secret
    expires_in: int


# ---------- Tickets ----------
class TicketCreate(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    description: str = Field(min_length=1, max_length=5000)
    category: TicketCategory
    equipment_id: str = Field(pattern=EQUIPMENT_ID_PATTERN, examples=["CPT-FICTIF-000123"])
    priority: TicketPriority = TicketPriority.MOYENNE


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketAssign(BaseModel):
    agent_id: uuid.UUID


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class CommentOut(ORMModel):
    id: uuid.UUID
    author: UserBrief
    content: str
    created_at: datetime


class AttachmentOut(ORMModel):
    id: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_by: UserBrief
    created_at: datetime


class TicketOut(ORMModel):
    id: uuid.UUID
    title: str
    description: str
    category: TicketCategory
    equipment_id: str
    priority: TicketPriority
    status: TicketStatus
    created_by: UserBrief
    assigned_to: UserBrief | None
    notified_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TicketDetail(TicketOut):
    comments: list[CommentOut]
    attachments: list[AttachmentOut]


class TicketPage(BaseModel):
    items: list[TicketOut]
    total: int
    limit: int
    offset: int


class Stats(BaseModel):
    """Tableau de bord metier. 'ouverts' = statut Nouveau. 'critiques' = priorite Critique non fermes."""

    ouverts: int
    en_cours: int
    resolus: int
    fermes: int
    critiques: int
    total: int
