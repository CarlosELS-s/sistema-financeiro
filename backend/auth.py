
import os
from dataclasses import dataclass
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


@dataclass
class ContextoVisitante:
    tipo: str = "visitante"


def gerar_hash_senha(senha: str) -> str:
    return password_hash.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return password_hash.verify(senha, senha_hash)


def criar_token(usuario_id: int) -> str:
    agora = datetime.now(timezone.utc)

    payload = {
        "sub": str(usuario_id),
        "tipo": "usuario",
        "iat": agora,
        "exp": agora + timedelta(hours=TEMPO_TOKEN_HORAS)
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def criar_token_visitante() -> str:
    agora = datetime.now(timezone.utc)

    payload = {
        "sub": "visitante",
        "tipo": "visitante",
        "iat": agora,
        "exp": agora + timedelta(hours=TEMPO_TOKEN_HORAS)
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def get_contexto_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
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

        tipo = payload.get("tipo")
        usuario_id = payload.get("sub")

        if tipo == "visitante" and usuario_id == "visitante":
            return ContextoVisitante()

        if tipo != "usuario" or usuario_id is None:
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


def get_usuario_atual(
    contexto=Depends(get_contexto_atual)
) -> Usuario:
    if isinstance(contexto, ContextoVisitante):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="O modo visitante é somente para visualização."
        )

    return contexto
