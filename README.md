
# 💰 Sistema Financeiro

Sistema de controle financeiro pessoal desenvolvido para organizar receitas, despesas, contas fixas e cartões de crédito. Possui autenticação de usuários e armazenamento de dados individualizado.

## 🚀 Funcionalidades

### 👤 Usuários e autenticação
- Cadastro de usuários.
- Login com e-mail e senha.
- Autenticação utilizando JWT.
- Senhas armazenadas com hash.
- Dados separados por usuário.

### 💸 Transações
- Cadastro de receitas e despesas.
- Edição e exclusão de movimentações.
- Filtro por tipo e mês.
- Organização por categorias.

### 📅 Contas fixas
- Cadastro de contas recorrentes.
- Organização das contas por usuário.
- Controle das contas mensais.

### 💳 Cartões de crédito
- Cadastro e gerenciamento de cartões.
- Controle de limite.
- Registro de compras parceladas.
- Geração e organização de faturas.
- Controle de vencimentos e pagamentos.

### 📊 Dashboard
- Visualização de receitas e despesas.
- Consulta de saldo.
- Despesas agrupadas por categoria.
- Movimentações recentes.
- Filtro por mês.

### 📁 Planilhas
- Exportação de movimentações para Excel.
- Importação de planilhas no formato `.xlsx`.
- Validação dos dados importados.

## 🛠️ Tecnologias utilizadas

### Backend
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL
- SQLite para desenvolvimento local
- PyJWT
- Argon2
- OpenPyXL

### Frontend
- HTML5
- CSS3
- JavaScript

### Hospedagem
- Render
- PostgreSQL

## 📂 Estrutura do projeto

```text
finanças/
│
├── backend/
│   ├── routers/
│   │   ├── autenticacao.py
│   │   ├── transacoes.py
│   │   ├── contas_fixas.py
│   │   └── cartoes.py
│   │
│   ├── auth.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── css/
│   │   └── style.css
│   │
│   ├── js/
│   │   ├── app.js
│   │   ├── auth.js
│   │   ├── sidebar.js
│   │   ├── contas.js
│   │   └── cartoes.js
│   │
│   ├── index.html
│   ├── login.html
│   ├── cadastro.html
│   ├── contas-fixas.html
│   └── cartoes.html
│
└── README.md
```

## ⚙️ Instalação e execução local

### 1. Clonar o repositório

```bash
git clone https://github.com/CarlosELS-s/sistema-financeiro.git
```

### 2. Entrar na pasta do backend

```bash
cd sistema-financeiro/backend
```

### 3. Criar ambiente virtual

```bash
python -m venv venv
```

### 4. Ativar o ambiente virtual

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 5. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 6. Configurar as variáveis de ambiente

Crie um arquivo `.env` dentro da pasta `backend`:

```env
DATABASE_URL=sqlite:///./financeiro.db
SECRET_KEY=coloque_uma_chave_secreta_aqui
```

> Nunca publique o arquivo `.env` no GitHub. Utilize uma chave secreta forte e mantenha suas credenciais protegidas.

### 7. Iniciar o servidor

```bash
python -m uvicorn main:app --reload
```

O sistema ficará disponível em:

```text
http://127.0.0.1:8000
```

## 📖 Documentação da API

Com o servidor iniciado, acesse:

```text
http://127.0.0.1:8000/docs
```

A documentação interativa é disponibilizada pelo Swagger UI do FastAPI.

## ☁️ Deploy no Render

O projeto pode ser hospedado no Render utilizando um Web Service e um banco PostgreSQL.

### Configuração do Web Service

**Root Directory:**

```text
backend
```

**Build Command:**

```bash
pip install -r requirements.txt
```

**Start Command:**

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Variáveis de ambiente

Configure no painel do Render:

| Variável | Descrição |
|---|---|
| `DATABASE_URL` | URL interna do PostgreSQL |
| `SECRET_KEY` | Chave secreta para autenticação JWT |

O banco PostgreSQL é utilizado para armazenar os dados de forma persistente.

## 🔐 Segurança

- Autenticação baseada em JWT.
- Senhas protegidas com hash Argon2.
- Separação dos registros por usuário.
- Configurações sensíveis armazenadas em variáveis de ambiente.
- Validação dos dados recebidos pela API.

## 👨‍💻 Autor

Desenvolvido como projeto de estudo e aplicação prática de desenvolvimento web com Python, FastAPI, SQLAlchemy e JavaScript.

---

**Sistema Financeiro — Organização e controle das suas finanças em um só lugar.**
