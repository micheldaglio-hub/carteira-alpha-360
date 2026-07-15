from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rate_limit import auth_rate_limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.services.audit import write_audit_event
from app.services.rbac import ensure_default_user_role, list_user_role_names


router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _enforce_auth_rate_limit(request: Request, action: str, email: str, *, limit: int, window_seconds: int) -> None:
    normalized_email = email.strip().lower()
    ip = _client_ip(request)
    keys = [f"auth:{action}:ip:{ip}", f"auth:{action}:email:{normalized_email}"]
    if not all(auth_rate_limiter.allow(key, limit=limit, window_seconds=window_seconds) for key in keys):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas em pouco tempo. Aguarde alguns minutos e tente novamente.",
        )


def public_user(user: User, db: Session | None = None) -> dict:
    roles = list_user_role_names(db, user_id=user.id) if db is not None else []
    return {"id": user.id, "email": user.email, "fullName": user.full_name, "roles": roles}


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    _enforce_auth_rate_limit(request, "register", payload.email, limit=6, window_seconds=600)
    existing = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja cadastrado.")
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    ensure_default_user_role(db, user_id=user.id, commit=False)
    db.commit()
    db.refresh(user)
    write_audit_event(
        db,
        event_type="user_registered",
        category="auth",
        action="register",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        message="Usuario cadastrado com sucesso.",
    )
    return {"access_token": create_access_token(user.id), "token_type": "bearer", "user": public_user(user, db)}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    _enforce_auth_rate_limit(request, "login", payload.email, limit=8, window_seconds=300)
    user = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        write_audit_event(
            db,
            event_type="login_failed",
            category="auth",
            action="login",
            actor_type="anonymous",
            severity="warning",
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
            message="Tentativa de login invalida.",
            metadata={"email": payload.email.lower()},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha invalidos.")
    write_audit_event(
        db,
        event_type="login_success",
        category="auth",
        action="login",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        message="Login realizado com sucesso.",
    )
    ensure_default_user_role(db, user_id=user.id, commit=True)
    return {"access_token": create_access_token(user.id), "token_type": "bearer", "user": public_user(user, db)}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_default_user_role(db, user_id=user.id, commit=True)
    return public_user(user, db)
