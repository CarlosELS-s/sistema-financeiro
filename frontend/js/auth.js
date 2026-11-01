
const API_URL = "/api";

// =====================================
// SESSÃO
// =====================================

function salvarSessao(dados) {
    localStorage.setItem("access_token", dados.access_token);
    localStorage.setItem("usuario", JSON.stringify(dados.usuario));
}

function encerrarSessao() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("usuario");
    window.location.href = "/login";
}

// =====================================
// LOGIN
// =====================================

document.getElementById("formLogin")?.addEventListener(
    "submit",
    async (evento) => {
        evento.preventDefault();

        const botao = document.getElementById("btnLogin");
        const mensagem = document.getElementById("mensagemLogin");

        const dados = {
            email: document.getElementById("email").value.trim(),
            senha: document.getElementById("senha").value
        };

        botao.disabled = true;
        botao.textContent = "Entrando...";
        mensagem.textContent = "";

        try {
            const resposta = await fetch(`${API_URL}/auth/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(dados)
            });

            const resultado = await resposta.json().catch(() => ({}));

            if (!resposta.ok) {
                throw new Error(
                    resultado.detail || "E-mail ou senha incorretos."
                );
            }

            salvarSessao(resultado);

            window.location.href = "/dashboard";

        } catch (erro) {
            mensagem.textContent = erro.message;
            mensagem.className = "form-message error";

        } finally {
            botao.disabled = false;
            botao.textContent = "Entrar";
        }
    }
);

// =====================================
// CADASTRO
// =====================================

document.getElementById("formCadastro")?.addEventListener(
    "submit",
    async (evento) => {
        evento.preventDefault();

        const botao = document.getElementById("btnCadastro");
        const mensagem = document.getElementById("mensagemCadastro");

        const dados = {
            nome: document.getElementById("nome").value.trim(),
            email: document.getElementById("email").value.trim(),
            senha: document.getElementById("senha").value
        };

        if (dados.nome.length < 2) {
            mensagem.textContent = "Informe um nome válido.";
            mensagem.className = "form-message error";
            return;
        }

        if (dados.senha.length < 8) {
            mensagem.textContent =
                "A senha deve possuir pelo menos 8 caracteres.";
            mensagem.className = "form-message error";
            return;
        }

        botao.disabled = true;
        botao.textContent = "Criando conta...";
        mensagem.textContent = "";

        try {
            const resposta = await fetch(`${API_URL}/auth/cadastro`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(dados)
            });

            const resultado = await resposta.json().catch(() => ({}));

            if (!resposta.ok) {
                throw new Error(
                    resultado.detail || "Não foi possível criar sua conta."
                );
            }

            mensagem.textContent =
                "Conta criada com sucesso! Redirecionando para o login...";
            mensagem.className = "form-message success";

            document.getElementById("formCadastro").reset();

            setTimeout(() => {
                window.location.href = "/login";
            }, 1200);

        } catch (erro) {
            mensagem.textContent = erro.message;
            mensagem.className = "form-message error";

        } finally {
            botao.disabled = false;
            botao.textContent = "Criar conta";
        }
    }
);
