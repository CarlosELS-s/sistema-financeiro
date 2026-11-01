
import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario


SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "Configure a variável de ambiente SECRET_KEY antes de iniciar a API."
    )

ALGORITHM = "HS256"
TEMPO_TOKEN_HORAS = 12

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)


def gerar_hash_senha(senha: str) -> str:
    return password_hash.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return password_hash.verify(senha, senha_hash)


def criar_token(usuario_id: int) -> str:
    agora = datetime.now(timezone.utc)

    payload = {
        "sub": str(usuario_id),
        "iat": agora,
        "exp": agora + timedelta(hours=TEMPO_TOKEN_HORAS)
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def get_usuario_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Usuario:

    erro = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão inválida ou expirada. Faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        usuario_id = payload.get("sub")

        if usuario_id is None:
            raise erro

        usuario_id = int(usuario_id)

    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise erro

    usuario = db.query(Usuario).filter(
        Usuario.id == usuario_id,
        Usuario.ativo == True
    ).first()

    if not usuario:
        raise erro

    return usuario
