
import os
import secrets
import smtplib
import base64

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

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
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")

    if not all([
        remetente,
        client_id,
        client_secret,
        refresh_token
    ]):
        raise HTTPException(
            status_code=500,
            detail="Configuração da API do Gmail incompleta."
        )

    mensagem = EmailMessage()
    mensagem["Subject"] = "Recuperação de senha | Financeiro"
    mensagem["From"] = remetente
    mensagem["To"] = destinatario

    mensagem.set_content(
        f"""
Olá!

Recebemos uma solicitação para recuperar sua senha.

Seu código de verificação é: {codigo}

Esse código é válido por 10 minutos.

Se você não solicitou essa alteração, ignore este email.

Equipe Financeiro
        """
    )

    mensagem.add_alternative(
        f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Recuperação de senha</title>
        </head>

        <body style="
            margin: 0;
            padding: 35px 15px;
            background-color: #09090b;
            font-family: Arial, Helvetica, sans-serif;
            color: #ffffff;
        ">
            <div style="
                max-width: 480px;
                margin: 0 auto;
                background-color: #18181b;
                border: 1px solid #27272a;
                border-radius: 16px;
                overflow: hidden;
            ">
                <div style="
                    padding: 28px 25px;
                    text-align: center;
                    border-bottom: 1px solid #27272a;
                ">
                    <div style="
                        display: inline-block;
                        background-color: #14532d;
                        color: #4ade80;
                        padding: 10px 16px;
                        border-radius: 10px;
                        font-size: 15px;
                        font-weight: bold;
                        letter-spacing: 1px;
                    ">
                        FINANCEIRO
                    </div>
                </div>

                <div style="padding: 32px 28px;">
                    <h1 style="
                        margin: 0 0 15px;
                        font-size: 23px;
                        color: #ffffff;
                        text-align: center;
                    ">
                        Recuperação de senha
                    </h1>

                    <p style="
                        color: #a1a1aa;
                        font-size: 15px;
                        line-height: 1.7;
                        text-align: center;
                    ">
                        Recebemos uma solicitação para redefinir
                        a senha da sua conta.
                    </p>

                    <p style="
                        color: #d4d4d8;
                        font-size: 14px;
                        text-align: center;
                        margin-top: 28px;
                    ">
                        Utilize o código abaixo:
                    </p>

                    <div style="
                        margin: 20px 0;
                        padding: 22px 10px;
                        background-color: #09090b;
                        border: 1px solid #166534;
                        border-radius: 12px;
                        text-align: center;
                    ">
                        <span style="
                            color: #4ade80;
                            font-size: 34px;
                            font-weight: bold;
                            letter-spacing: 10px;
                        ">
                            {codigo}
                        </span>
                    </div>

                    <p style="
                        color: #a1a1aa;
                        font-size: 13px;
                        text-align: center;
                        line-height: 1.6;
                    ">
                        Este código é válido por
                        <strong style="color: #ffffff;">
                            10 minutos
                        </strong>.
                    </p>

                    <div style="
                        margin-top: 28px;
                        padding: 15px;
                        background-color: #27272a;
                        border-radius: 10px;
                    ">
                        <p style="
                            margin: 0;
                            color: #a1a1aa;
                            font-size: 12px;
                            line-height: 1.6;
                            text-align: center;
                        ">
                            Se você não solicitou a recuperação
                            da senha, ignore este email.
                            Sua conta continuará protegida.
                        </p>
                    </div>
                </div>

                <div style="
                    padding: 20px;
                    border-top: 1px solid #27272a;
                    text-align: center;
                ">
                    <p style="
                        margin: 0;
                        color: #71717a;
                        font-size: 12px;
                    ">
                        © Financeiro — Sistema de controle financeiro
                    </p>
                </div>
            </div>
        </body>
        </html>
        """,
        subtype="html"
    )

    try:
        credenciais = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=[
                "https://www.googleapis.com/auth/gmail.send"
            ]
        )

        servico = build(
            "gmail",
            "v1",
            credentials=credenciais,
            cache_discovery=False
        )

        mensagem_codificada = base64.urlsafe_b64encode(
            mensagem.as_bytes()
        ).decode("utf-8")

        resultado = servico.users().messages().send(
            userId="me",
            body={
                "raw": mensagem_codificada
            }
        ).execute()

        print(
            f"[EMAIL] Enviado pela API do Gmail. ID: {resultado.get('id')}"
        )

    except Exception as erro:
        print(
            f"[EMAIL] Erro na API: {type(erro).__name__}: {erro}"
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
