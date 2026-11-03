
# 💰 Sistema Financeiro

Sistema de controle financeiro pessoal desenvolvido para facilitar a organização e o acompanhamento das finanças.

A aplicação permite gerenciar receitas, despesas, contas fixas, cartões de crédito e orçamentos mensais, além de acompanhar os resultados por meio de um dashboard.

🌐 **Acesse o sistema:**  
https://sistema-financeiro-tj76.onrender.com/

---

## 🚀 Funcionalidades

### 👤 Usuários e autenticação
- Cadastro de usuários.
- Login com e-mail e senha.
- Autenticação utilizando JWT.
- Senhas armazenadas com hash.
- Dados individualizados por usuário.

### 💸 Transações
- Cadastro de receitas e despesas.
- Edição e exclusão de movimentações.
- Filtro por tipo e mês.
- Organização por categorias.
- Histórico de movimentações.

### 📅 Contas fixas
- Cadastro de contas recorrentes.
- Organização das contas por usuário.
- Controle das contas mensais.
- Acompanhamento dos compromissos financeiros.

### 💳 Cartões de crédito
- Cadastro e gerenciamento de cartões.
- Controle de limite disponível.
- Registro de compras parceladas.
- Organização das parcelas por fatura.
- Controle de vencimentos.
- Registro de pagamentos de faturas.

### 🎯 Orçamentos mensais
- Criação de limites de gastos por categoria.
- Definição de orçamento para cada mês.
- Acompanhamento dos valores já gastos.
- Visualização do saldo restante.
- Indicador de percentual utilizado.
- Aviso quando o limite é ultrapassado.
- Edição e exclusão de orçamentos.

### 📊 Dashboard
- Visualização de receitas e despesas.
- Consulta de saldo mensal e total.
- Despesas agrupadas por categoria.
- Movimentações recentes.
- Filtro por mês.
- Acompanhamento dos resultados financeiros.

### 📁 Importação e exportação de planilhas
- Exportação de movimentações para Excel.
- Importação de planilhas no formato `.xlsx`.
- Validação dos dados importados.

---

## 🛠️ Tecnologias utilizadas

### Backend
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL
- SQLite para desenvolvimento local
- Alembic
- PyJWT
- Argon2
- OpenPyXL

### Frontend
- HTML5
- CSS3
- JavaScript

### Banco de dados e hospedagem
- PostgreSQL
- Supabase
- Render

---

## 📂 Estrutura do projeto

```text
sistema-financeiro/
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
│   ├── requirements.txt
│   └── alembic/
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
