import os
import smtplib
from dotenv import load_dotenv

load_dotenv()

email = os.getenv("EMAIL_REMETENTE")
senha = os.getenv("EMAIL_SENHA_APP")

print("Email configurado:", bool(email))
print("Senha configurada:", bool(senha))
print("Tamanho da senha:", len(senha or ""))

try:
    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        timeout=30
    ) as smtp:

        smtp.ehlo()
        print("Conexão SSL: OK")

        resposta = smtp.login(email, senha)

        print("Autenticação:", resposta)

except Exception as erro:
    print("Tipo do erro:", type(erro).__name__)
    print("Mensagem:", erro)