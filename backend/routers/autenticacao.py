
import os
import secrets
import smtplib

from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario
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
# CONFIGURAÇÕES
# =====================================

INTERVALO_SOLICITACAO = 60
MAX_SOLICITACOES = 5
JANELA_SOLICITACOES = 60
VALIDADE_CODIGO = 10
MAX_TENTATIVAS_CODIGO = 5


# =====================================
# SCHEMAS
# =====================================

class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class VerificarCodigoRequest(BaseModel):
    email: EmailStr
    codigo: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^[0-9]{6}$"
    )


class RedefinirSenhaRequest(BaseModel):
    email: EmailStr
    codigo: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^[0-9]{6}$"
    )
    nova_senha: str = Field(
        min_length=8,
        max_length=128
    )


# =====================================
# FUNÇÕES AUXILIARES
# =====================================

def obter_data_utc():
    return datetime.now(timezone.utc)


def normalizar_data(data):
    if data and data.tzinfo is None:
        return data.replace(tzinfo=timezone.utc)

    return data


def enviar_codigo_email(destinatario: str, codigo: str):
    remetente = os.getenv("EMAIL_REMETENTE")
    senha_app = os.getenv("EMAIL_SENHA_APP")

    if not remetente or not senha_app:
        raise HTTPException(
            status_code=500,
            detail="Configuração de email não encontrada."
        )

    mensagem = EmailMessage()
    mensagem["Subject"] = "Recuperação de senha"
    mensagem["From"] = remetente
    mensagem["To"] = destinatario

    mensagem.set_content(
        f"Seu código de recuperação é: {codigo}\n"
        "Ele é válido por 10 minutos."
    )

    try:
        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465,
            timeout=30
        ) as smtp:

            smtp.login(remetente, senha_app)
            smtp.send_message(mensagem)

    except Exception as erro:
        print(
            f"[EMAIL] Erro: {type(erro).__name__}: {erro}"
        )

        raise HTTPException(
            status_code=500,
            detail="Não foi possível enviar o email."
        )


def validar_codigo(
    usuario: Usuario,
    codigo: str,
    db: Session
):
    agora = obter_data_utc()

    if not usuario.codigo_recuperacao_hash:
        raise HTTPException(
            status_code=400,
            detail="Solicite um novo código."
        )

    expira = normalizar_data(
        usuario.codigo_recuperacao_expira
    )

    if not expira or agora > expira:
        raise HTTPException(
            status_code=400,
            detail="Código expirado. Solicite outro."
        )

    if usuario.codigo_recuperacao_tentativas >= MAX_TENTATIVAS_CODIGO:
        raise HTTPException(
            status_code=429,
            detail="Limite de tentativas atingido. Solicite outro código."
        )

    if not verificar_senha(
        codigo,
        usuario.codigo_recuperacao_hash
    ):
        usuario.codigo_recuperacao_tentativas += 1
        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Código incorreto."
        )


def buscar_usuario_por_email(
    email: str,
    db: Session
):
    return db.query(Usuario).filter(
        Usuario.email == email,
        Usuario.ativo == True
    ).first()


# =====================================
# CADASTRO
# =====================================

@router.post(
    "/cadastro",
    response_model=__import__("schemas").UsuarioResponse,
    status_code=status.HTTP_201_CREATED
)
def cadastrar_usuario(
    dados: __import__("schemas").UsuarioCreate,
    db: Session = Depends(get_db)
):
    email = dados.email.strip().lower()

    existente = buscar_usuario_por_email(
        email,
        db
    )

    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este email já está cadastrado."
        )

    # Verifica também emails cadastrados em contas inativas.
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
    response_model=__import__("schemas").TokenResponse
)
def login(
    dados: __import__("schemas").UsuarioLogin,
    db: Session = Depends(get_db)
):
    email = dados.email.strip().lower()

    usuario = buscar_usuario_por_email(
        email,
        db
    )

    if (
        not usuario
        or not verificar_senha(
            dados.senha,
            usuario.senha_hash
        )
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


# =====================================
# SOLICITAR RECUPERAÇÃO
# =====================================

@router.post("/recuperar-senha")
def recuperar_senha(
    dados: RecuperarSenhaRequest,
    db: Session = Depends(get_db)
):
    email = str(dados.email).strip().lower()

    resposta = {
        "mensagem": (
            "Se o email estiver cadastrado, "
            "você receberá um código."
        )
    }

    usuario = db.query(Usuario).filter(
        Usuario.email == email,
        Usuario.ativo == True
    ).with_for_update().first()

    # Não revela se o email está cadastrado.
    if not usuario:
        return resposta

    agora = obter_data_utc()

    ultima_solicitacao = normalizar_data(
        usuario.codigo_recuperacao_solicitado_em
    )

    solicitacoes = (
        usuario.codigo_recuperacao_solicitacoes or 0
    )

    # Reinicia o contador após uma hora sem solicitações.
    if (
        ultima_solicitacao
        and agora - ultima_solicitacao >= timedelta(
            minutes=JANELA_SOLICITACOES
        )
    ):
        solicitacoes = 0

    # Intervalo mínimo de 60 segundos.
    if ultima_solicitacao and agora - ultima_solicitacao < timedelta(
        seconds=INTERVALO_SOLICITACAO
    ):
        restante = INTERVALO_SOLICITACAO - int(
            (agora - ultima_solicitacao).total_seconds()
        )

        raise HTTPException(
            status_code=429,
            detail=(
                f"Aguarde {max(restante, 1)} segundos "
                "antes de solicitar outro código."
            )
        )

    # Máximo de cinco solicitações.
    if solicitacoes >= MAX_SOLICITACOES:
        raise HTTPException(
            status_code=429,
            detail=(
                "Você atingiu o limite de 5 solicitações. "
                "Tente novamente após uma hora."
            )
        )

    codigo = f"{secrets.randbelow(1000000):06d}"

    usuario.codigo_recuperacao_hash = gerar_hash_senha(
        codigo
    )

    usuario.codigo_recuperacao_expira = (
        agora + timedelta(minutes=VALIDADE_CODIGO)
    )

    usuario.codigo_recuperacao_tentativas = 0

    usuario.codigo_recuperacao_solicitado_em = agora
    usuario.codigo_recuperacao_solicitacoes = solicitacoes + 1

    # Salva antes do envio para registrar a solicitação
    # mesmo se o serviço de email apresentar falha.
    db.commit()

    try:
        enviar_codigo_email(email, codigo)

    except Exception:
        # Invalida o código caso o envio não tenha funcionado.
        usuario = db.query(Usuario).filter(
            Usuario.id == usuario.id
        ).first()

        if usuario:
            usuario.codigo_recuperacao_hash = None
            usuario.codigo_recuperacao_expira = None
            db.commit()

        raise

    print("[RECUPERACAO] Código enviado.")

    return resposta


# =====================================
# VERIFICAR CÓDIGO
# =====================================

@router.post("/verificar-codigo")
def verificar_codigo(
    dados: VerificarCodigoRequest,
    db: Session = Depends(get_db)
):
    email = str(dados.email).strip().lower()

    usuario = buscar_usuario_por_email(
        email,
        db
    )

    if not usuario:
        raise HTTPException(
            status_code=400,
            detail="Código inválido ou expirado."
        )

    validar_codigo(
        usuario,
        dados.codigo,
        db
    )

    return {
        "mensagem": "Código verificado com sucesso."
    }


# =====================================
# REDEFINIR SENHA
# =====================================

@router.post("/redefinir-senha")
def redefinir_senha(
    dados: RedefinirSenhaRequest,
    db: Session = Depends(get_db)
):
    email = str(dados.email).strip().lower()

    usuario = buscar_usuario_por_email(
        email,
        db
    )

    if not usuario:
        raise HTTPException(
            status_code=400,
            detail="Código inválido ou expirado."
        )

    validar_codigo(
        usuario,
        dados.codigo,
        db
    )

    usuario.senha_hash = gerar_hash_senha(
        dados.nova_senha
    )

    # Invalida o código depois de utilizado.
    usuario.codigo_recuperacao_hash = None
    usuario.codigo_recuperacao_expira = None
    usuario.codigo_recuperacao_tentativas = 0

    db.commit()

    return {
        "mensagem": "Senha redefinida com sucesso!"
    }
