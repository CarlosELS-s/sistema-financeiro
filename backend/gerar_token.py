from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]

flow = InstalledAppFlow.from_client_secrets_file(
    "credentials.json",
    SCOPES
)

credenciais = flow.run_local_server(
    host="localhost",
    port=0,
    access_type="offline",
    prompt="consent",
    open_browser=True
)

print("\nAutorização concluída!")

if credenciais.refresh_token:
    print("Refresh Token gerado com sucesso!")
    print(credenciais.refresh_token)
else:
    print("Não foi possível gerar o Refresh Token.")