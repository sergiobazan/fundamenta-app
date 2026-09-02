from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from PIL import Image, UnidentifiedImageError
from psycopg.errors import UniqueViolation
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.config import get_settings, get_upload_dir
from app.db import connection_scope

router = APIRouter(prefix="/auth", tags=["auth"])
password_hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
bearer_dependency = Depends(bearer)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 20_000_000


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("El nombre es demasiado corto")
        return cleaned


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    bio: str = Field(default="", max_length=280)

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("El nombre es demasiado corto")
        return cleaned


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def serialize_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "bio": user["bio"],
        "avatar_url": (
            f"/uploads/avatars/{user['avatar_filename']}"
            if user.get("avatar_filename")
            else None
        ),
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }


def create_session(cursor, user_id: int) -> tuple[str, datetime]:
    settings = get_settings()
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(days=settings.session_ttl_days)
    cursor.execute(
        """
        INSERT INTO auth_sessions (user_id, token_hash, expires_at)
        VALUES (%s, %s, %s)
        """,
        (user_id, hash_session_token(token), expires_at),
    )
    return token, expires_at


def current_user(
    credentials: HTTPAuthorizationCredentials | None = bearer_dependency,
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT u.*
            FROM auth_sessions s
            JOIN app_users u ON u.id = s.user_id
            WHERE s.token_hash = %s
              AND s.revoked_at IS NULL
              AND s.expires_at > NOW()
            """,
            (hash_session_token(credentials.credentials),),
        )
        user = cursor.fetchone()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida")
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> dict:
    email = normalize_email(str(payload.email))
    try:
        with connection_scope() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO app_users (email, password_hash, full_name)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (email, password_hasher.hash(payload.password), payload.full_name),
            )
            user = cursor.fetchone()
            token, expires_at = create_session(cursor, user["id"])
    except UniqueViolation as error:
        raise HTTPException(status_code=409, detail="Ese correo ya está registrado") from error
    return {"user": serialize_user(user), "session_token": token, "expires_at": expires_at}


@router.post("/login")
def login(payload: LoginRequest) -> dict:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM app_users WHERE email = %s",
            (normalize_email(str(payload.email)),),
        )
        user = cursor.fetchone()
        if user is None or not password_hasher.verify(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
        token, expires_at = create_session(cursor, user["id"])
    return {"user": serialize_user(user), "session_token": token, "expires_at": expires_at}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    credentials: HTTPAuthorizationCredentials | None = bearer_dependency,
) -> None:
    if credentials is None:
        return
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE auth_sessions SET revoked_at = NOW()
            WHERE token_hash = %s AND revoked_at IS NULL
            """,
            (hash_session_token(credentials.credentials),),
        )


current_user_dependency = Depends(current_user)


@router.get("/me")
def me(user: dict = current_user_dependency) -> dict:
    return {"user": serialize_user(user)}


@router.patch("/profile")
def update_profile(payload: ProfileUpdateRequest, user: dict = current_user_dependency) -> dict:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE app_users
            SET full_name = %s, bio = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (payload.full_name, payload.bio.strip(), user["id"]),
        )
        updated_user = cursor.fetchone()
    return {"user": serialize_user(updated_user)}


@router.post("/profile/avatar")
def upload_avatar(
    avatar: UploadFile,
    user: dict = current_user_dependency,
) -> dict:
    if avatar.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Usa una imagen JPG, PNG o WebP")

    raw = avatar.file.read(MAX_AVATAR_BYTES + 1)
    if len(raw) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=413, detail="La imagen no puede superar 2 MB")

    try:
        source = Image.open(BytesIO(raw))
        source.verify()
        source = Image.open(BytesIO(raw))
        source.thumbnail((1024, 1024))
        if source.mode not in ("RGB", "RGBA"):
            source = source.convert("RGBA" if "transparency" in source.info else "RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise HTTPException(status_code=422, detail="El archivo no es una imagen válida") from error

    upload_dir = get_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"user-{user['id']}.webp"
    source.save(upload_dir / filename, format="WEBP", quality=88, method=6)

    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE app_users
            SET avatar_filename = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (filename, user["id"]),
        )
        updated_user = cursor.fetchone()
    return {"user": serialize_user(updated_user)}
