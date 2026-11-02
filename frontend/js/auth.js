
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


// =====================================
// RECUPERAÇÃO DE SENHA
// =====================================

let emailRecuperacao = "";
let codigoRecuperacao = "";


// =====================================
// ETAPA 1: SOLICITAR CÓDIGO
// =====================================

document.getElementById("formRecuperar")?.addEventListener(
    "submit",
    async (evento) => {
        evento.preventDefault();

        const botao = document.getElementById("btnEnviarCodigo");
        const mensagem = document.getElementById("mensagemRecuperacao");

        emailRecuperacao = document
            .getElementById("emailRecuperacao")
            .value.trim();

        botao.disabled = true;
        botao.textContent = "Enviando...";
        mensagem.textContent = "";

        try {
            const resposta = await fetch(
                `${API_URL}/auth/recuperar-senha`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        email: emailRecuperacao
                    })
                }
            );

            const resultado = await resposta.json().catch(() => ({}));

            if (!resposta.ok) {
                throw new Error(
                    resultado.detail || "Não foi possível solicitar o código."
                );
            }

            document.getElementById("etapaEmail").hidden = true;
            document.getElementById("etapaCodigo").hidden = false;

        } catch (erro) {
            mensagem.textContent = erro.message;
            mensagem.className = "form-message error";

        } finally {
            botao.disabled = false;
            botao.textContent = "Enviar código";
        }
    }
);


// =====================================
// ETAPA 2: VERIFICAR CÓDIGO
// =====================================

document.getElementById("formCodigo")?.addEventListener(
    "submit",
    async (evento) => {
        evento.preventDefault();

        const botao = document.getElementById("btnVerificarCodigo");
        const mensagem = document.getElementById("mensagemCodigo");

        codigoRecuperacao = document
            .getElementById("codigoRecuperacao")
            .value.trim();

        if (!/^[0-9]{6}$/.test(codigoRecuperacao)) {
            mensagem.textContent =
                "Digite um código válido de 6 dígitos.";

            mensagem.className = "form-message error";
            return;
        }

        botao.disabled = true;
        botao.textContent = "Verificando...";
        mensagem.textContent = "";

        try {
            const resposta = await fetch(
                `${API_URL}/auth/verificar-codigo`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        email: emailRecuperacao,
                        codigo: codigoRecuperacao
                    })
                }
            );

            const resultado = await resposta.json().catch(() => ({}));

            if (!resposta.ok) {
                throw new Error(
                    resultado.detail || "Código inválido."
                );
            }

            document.getElementById("etapaCodigo").hidden = true;
            document.getElementById("etapaNovaSenha").hidden = false;

        } catch (erro) {
            mensagem.textContent = erro.message;
            mensagem.className = "form-message error";

        } finally {
            botao.disabled = false;
            botao.textContent = "Verificar código";
        }
    }
);


// =====================================
// ETAPA 3: REDEFINIR SENHA
// =====================================

document.getElementById("formNovaSenha")?.addEventListener(
    "submit",
    async (evento) => {
        evento.preventDefault();

        const botao = document.getElementById("btnRedefinirSenha");
        const mensagem = document.getElementById("mensagemNovaSenha");

        const novaSenha = document.getElementById("novaSenha").value;

        const confirmarSenha = document
            .getElementById("confirmarSenha")
            .value;

        if (novaSenha.length < 8) {
            mensagem.textContent =
                "A senha precisa ter pelo menos 8 caracteres.";

            mensagem.className = "form-message error";
            return;
        }

        if (novaSenha !== confirmarSenha) {
            mensagem.textContent = "As senhas não coincidem.";
            mensagem.className = "form-message error";
            return;
        }

        botao.disabled = true;
        botao.textContent = "Salvando...";
        mensagem.textContent = "";

        try {
            const resposta = await fetch(
                `${API_URL}/auth/redefinir-senha`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        email: emailRecuperacao,
                        codigo: codigoRecuperacao,
                        nova_senha: novaSenha
                    })
                }
            );

            const resultado = await resposta.json().catch(() => ({}));

            if (!resposta.ok) {
                throw new Error(
                    resultado.detail || "Não foi possível redefinir a senha."
                );
            }

            mensagem.textContent =
                "Senha alterada com sucesso! Voltando ao login...";

            mensagem.className = "form-message success";

            document.getElementById("formNovaSenha").reset();

            setTimeout(() => {
                window.location.href = "/login";
            }, 1800);

        } catch (erro) {
            mensagem.textContent = erro.message;
            mensagem.className = "form-message error";

        } finally {
            botao.disabled = false;
            botao.textContent = "Redefinir senha";
        }
    }
);
