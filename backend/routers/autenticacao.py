from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario
from schemas import (
    UsuarioCreate,
    UsuarioLogin,
    UsuarioResponse,
    TokenResponse
)

from auth import (
    gerar_hash_senha,
    verificar_senha,
    criar_token
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Autenticação"]
)


# =====================================
# CADASTRO
# =====================================

@router.post(
    "/cadastro",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED
)
def cadastrar_usuario(
    dados: UsuarioCreate,
    db: Session = Depends(get_db)
):
    email = dados.email.strip().lower()

    existente = db.query(Usuario).filter(
        Usuario.email == email
    ).first()

    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este email já está cadastrado."
        )

    usuario = Usuario(
        nome=dados.nome.strip(),
        email=email,
        senha_hash=gerar_hash_senha(dados.senha),
        ativo=True
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return usuario


# =====================================
# LOGIN
# =====================================

@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    dados: UsuarioLogin,
    db: Session = Depends(get_db)
):
    email = dados.email.strip().lower()

    usuario = db.query(Usuario).filter(
        Usuario.email == email
    ).first()

    if (
        not usuario
        or not verificar_senha(
            dados.senha,
            usuario.senha_hash
        )
        or not usuario.ativo
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = criar_token(usuario.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": usuario
    }