const API_URL = "/api";

let cartoes = [];
let cartaoEditandoId = null;

// =====================================
// AUTENTICAÇÃO
// =====================================

function obterTokenCartoes() {
    return localStorage.getItem("access_token");
}

function encerrarSessaoCartoes() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("usuario");
    window.location.href = "/login";
}

function verificarAutenticacaoCartoes() {
    if (!obterTokenCartoes()) {
        window.location.href = "/login";
        return false;
    }

    return true;
}

// =====================================
// UTILITÁRIOS
// =====================================

const dinheiro = valor =>
    (Number(valor || 0) / 100).toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL"
    });

function mensagem(elemento, texto, erro = false) {
    if (!elemento) return;

    elemento.textContent = texto;
    elemento.style.color = erro ? "#dc2626" : "#16a34a";
}

// =====================================
// REQUISIÇÕES COM JWT
// =====================================

async function requisicao(url, opcoes = {}) {
    const token = obterTokenCartoes();

    if (!token) {
        encerrarSessaoCartoes();
        throw new Error("Sessão expirada. Faça login novamente.");
    }

    const headers = {
        ...opcoes.headers,
        Authorization: `Bearer ${token}`
    };

    if (opcoes.body && !(opcoes.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }

    const resposta = await fetch(`${API_URL}${url}`, {
        ...opcoes,
        headers
    });

    if (resposta.status === 401) {
        encerrarSessaoCartoes();
        throw new Error("Sessão expirada. Faça login novamente.");
    }

    const dados = await resposta.json().catch(() => ({}));

    if (!resposta.ok) {
        throw new Error(
            typeof dados.detail === "string"
                ? dados.detail
                : "Não foi possível realizar a operação."
        );
    }

    return dados;
}

// =====================================
// FORMULÁRIO DE CADASTRO E EDIÇÃO
// =====================================

function inicializarCadastroCartao() {
    const btnMostrar = document.getElementById("btnMostrarCadastro");
    const btnCancelar = document.getElementById("btnCancelarCadastro");
    const formulario = document.getElementById("formCartao");

    btnMostrar.addEventListener("click", () => {
        cancelarEdicaoCartao();

        document.getElementById("formularioCartao").hidden = false;

        document.getElementById("nomeCartao").focus();
    });

    btnCancelar.addEventListener("click", () => {
        cancelarEdicaoCartao();
    });

    formulario.addEventListener("submit", async event => {
        event.preventDefault();

        const msg = document.getElementById("mensagemCartao");

        const dados = {
            nome: document.getElementById("nomeCartao").value.trim(),
            banco: document.getElementById("bancoCartao").value.trim() || null,
            limite: Number(document.getElementById("limiteCartao").value),
            dia_fechamento: Number(
                document.getElementById("fechamentoCartao").value
            ),
            dia_vencimento: Number(
                document.getElementById("vencimentoCartao").value
            )
        };

        if (!dados.nome || dados.nome.length < 2) {
            mensagem(msg, "Informe um nome válido para o cartão.", true);
            return;
        }

        if (!Number.isFinite(dados.limite) || dados.limite <= 0) {
            mensagem(msg, "Informe um limite válido.", true);
            return;
        }

        if (
            dados.dia_fechamento < 1 ||
            dados.dia_fechamento > 31 ||
            dados.dia_vencimento < 1 ||
            dados.dia_vencimento > 31
        ) {
            mensagem(
                msg,
                "Informe dias válidos de fechamento e vencimento.",
                true
            );
            return;
        }

        try {
            if (cartaoEditandoId !== null) {
                await requisicao(`/cartoes/${cartaoEditandoId}`, {
                    method: "PUT",
                    body: JSON.stringify(dados)
                });

                mensagem(msg, "Cartão atualizado com sucesso!");
            } else {
                await requisicao("/cartoes", {
                    method: "POST",
                    body: JSON.stringify(dados)
                });

                mensagem(msg, "Cartão cadastrado com sucesso!");
            }

            formulario.reset();

            document.getElementById("fechamentoCartao").value = 9;
            document.getElementById("vencimentoCartao").value = 16;

            cartaoEditandoId = null;

            document.getElementById("formularioCartao").hidden = true;

            await carregarCartoes();

        } catch (erro) {
            mensagem(msg, erro.message, true);
            console.error("Erro ao salvar cartão:", erro);
        }
    });
}

// =====================================
// CANCELAR EDIÇÃO
// =====================================

function cancelarEdicaoCartao() {
    cartaoEditandoId = null;

    const formulario = document.getElementById("formCartao");

    formulario.reset();

    document.getElementById("fechamentoCartao").value = 9;
    document.getElementById("vencimentoCartao").value = 16;

    document.getElementById("formularioCartao").hidden = true;

    const titulo = document.querySelector(
        "#formularioCartao .panel-header h3"
    );

    if (titulo) {
        titulo.textContent = "Novo cartão";
    }

    const botaoSalvar = formulario.querySelector(
        'button[type="submit"]'
    );

    if (botaoSalvar) {
        botaoSalvar.textContent = "Salvar cartão";
    }

    mensagem(document.getElementById("mensagemCartao"), "");
}

// =====================================
// EDITAR CARTÃO
// =====================================

function editarCartao(id) {
    const cartao = cartoes.find(item => item.id === id);

    if (!cartao) {
        alert("Cartão não encontrado.");
        return;
    }

    cartaoEditandoId = cartao.id;

    document.getElementById("nomeCartao").value = cartao.nome || "";
    document.getElementById("bancoCartao").value = cartao.banco || "";

    document.getElementById("limiteCartao").value = (
        Number(cartao.limite_centavos || 0) / 100
    ).toFixed(2);

    document.getElementById("fechamentoCartao").value =
        cartao.dia_fechamento;

    document.getElementById("vencimentoCartao").value =
        cartao.dia_vencimento;

    const titulo = document.querySelector(
        "#formularioCartao .panel-header h3"
    );

    if (titulo) {
        titulo.textContent = "Editar cartão";
    }

    const botaoSalvar = document.querySelector(
        '#formCartao button[type="submit"]'
    );

    if (botaoSalvar) {
        botaoSalvar.textContent = "Salvar alterações";
    }

    mensagem(document.getElementById("mensagemCartao"), "");

    document.getElementById("formularioCartao").hidden = false;

    document.getElementById("formularioCartao").scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

// =====================================
// EXCLUIR CARTÃO
// =====================================

async function excluirCartao(id) {
    const cartao = cartoes.find(item => item.id === id);

    if (!cartao) {
        alert("Cartão não encontrado.");
        return;
    }

    const confirmar = confirm(
        `Deseja realmente excluir o cartão "${cartao.nome}"?`
    );

    if (!confirmar) return;

    try {
        await requisicao(`/cartoes/${id}`, {
            method: "DELETE"
        });

        alert("Cartão excluído com sucesso!");

        if (cartaoEditandoId === id) {
            cancelarEdicaoCartao();
        }

        await carregarCartoes();

        const select = document.getElementById("filtroCartaoFatura");

        if (select.value === String(id)) {
            document.getElementById("listaFaturas").innerHTML =
                "<p>Selecione um cartão para visualizar as compras.</p>";
        }

    } catch (erro) {
        alert(erro.message);
        console.error("Erro ao excluir cartão:", erro);
    }
}

// =====================================
// LISTAR CARTÕES
// =====================================

async function carregarCartoes() {
    const lista = document.getElementById("listaCartoes");
    const selectFatura = document.getElementById("filtroCartaoFatura");

    try {
        const cartaoSelecionado = selectFatura.value;

        cartoes = await requisicao("/cartoes");

        lista.innerHTML = "";

        selectFatura.innerHTML =
            '<option value="">Selecione um cartão</option>';

        if (!Array.isArray(cartoes) || cartoes.length === 0) {
            lista.innerHTML = "<p>Nenhum cartão cadastrado.</p>";

            document.getElementById("listaFaturas").innerHTML =
                "<p>Cadastre um cartão para começar.</p>";

            return;
        }

        cartoes.forEach(cartao => {
            const card = document.createElement("div");
            card.className = "card";

            const titulo = document.createElement("h3");
            titulo.textContent = cartao.nome;

            const banco = document.createElement("p");
            banco.textContent = cartao.banco || "Cartão de crédito";

            const limite = document.createElement("p");
            limite.textContent =
                `Limite: ${dinheiro(cartao.limite_centavos)}`;

            const utilizado = document.createElement("p");
            utilizado.textContent =
                `Utilizado: ${dinheiro(cartao.utilizado_centavos)}`;

            const restante = document.createElement("h2");
            restante.textContent =
                `Disponível: ${dinheiro(cartao.disponivel_centavos)}`;

            const datas = document.createElement("p");
            datas.textContent =
                `Fecha dia ${cartao.dia_fechamento} · Vence dia ${cartao.dia_vencimento}`;

            const acoes = document.createElement("div");
            acoes.className = "form-actions";

            const btnEditar = document.createElement("button");
            btnEditar.type = "button";
            btnEditar.className = "btn-secondary";
            btnEditar.textContent = "Editar";

            btnEditar.addEventListener("click", () => {
                editarCartao(cartao.id);
            });

            const btnExcluir = document.createElement("button");
            btnExcluir.type = "button";
            btnExcluir.className = "btn-secondary";
            btnExcluir.textContent = "Excluir";

            btnExcluir.addEventListener("click", () => {
                excluirCartao(cartao.id);
            });

            acoes.append(btnEditar, btnExcluir);

            card.append(
                titulo,
                banco,
                limite,
                utilizado,
                restante,
                datas,
                acoes
            );

            lista.appendChild(card);

            const opcaoFatura = document.createElement("option");
            opcaoFatura.value = cartao.id;
            opcaoFatura.textContent = cartao.nome;

            selectFatura.appendChild(opcaoFatura);
        });

        if (
            cartaoSelecionado &&
            cartoes.some(c => String(c.id) === cartaoSelecionado)
        ) {
            selectFatura.value = cartaoSelecionado;
        }

    } catch (erro) {
        lista.textContent = erro.message;
        console.error("Erro ao carregar cartões:", erro);
    }
}

// =====================================
// FILTRO DE FATURAS
// =====================================

function inicializarFiltroFaturas() {
    const select = document.getElementById("filtroCartaoFatura");

    select.addEventListener("change", event => {
        if (event.target.value) {
            carregarFaturas(event.target.value);
        } else {
            document.getElementById("listaFaturas").innerHTML =
                "<p>Selecione um cartão para visualizar as compras.</p>";
        }
    });
}

// =====================================
// LISTAR COMPRAS E VALORES
// =====================================

async function carregarFaturas(cartaoId) {
    const lista = document.getElementById("listaFaturas");

    lista.innerHTML = "<p>Carregando faturas...</p>";

    try {
        const faturas = await requisicao(
            `/cartoes/${cartaoId}/faturas`
        );

        lista.innerHTML = "";

        if (!Array.isArray(faturas) || faturas.length === 0) {
            lista.innerHTML = "<p>Nenhuma compra encontrada.</p>";
            return;
        }

        const compras = new Map();

        faturas.forEach(fatura => {
            (fatura.compras || []).forEach(compra => {
                const descricao = compra.descricao || "Compra";

                const resultado = descricao.match(/\s\((\d+)\/(\d+)\)$/);

                const nome = resultado
                    ? descricao.replace(/\s\(\d+\/\d+\)$/, "")
                    : descricao;

                const quantidade = resultado
                    ? Number(resultado[2])
                    : 1;

                const valorParcela = Number(compra.valor_centavos || 0);

                if (!compras.has(nome)) {
                    compras.set(nome, {
                        quantidade,
                        total: 0,
                        valorParcela
                    });
                }

                const item = compras.get(nome);

                item.total += valorParcela;
                item.quantidade = Math.max(item.quantidade, quantidade);
            });
        });

        if (compras.size === 0) {
            lista.innerHTML = "<p>Nenhuma compra encontrada.</p>";
            return;
        }

        compras.forEach((compra, nome) => {
            const linha = document.createElement("div");
            linha.className = "card";
            linha.style.marginBottom = "14px";

            const descricao = document.createElement("h3");
            descricao.textContent = nome;

            const parcelas = document.createElement("p");
            parcelas.textContent = compra.quantidade > 1
                ? `${compra.quantidade} vezes`
                : "À vista";

            const valorParcela = document.createElement("p");
            valorParcela.textContent =
                `Valor da parcela: ${dinheiro(compra.valorParcela)}`;

            const total = document.createElement("p");
            total.textContent =
                `Valor total: ${dinheiro(compra.total)}`;

            linha.append(
                descricao,
                parcelas,
                valorParcela,
                total
            );

            lista.appendChild(linha);
        });

    } catch (erro) {
        lista.textContent = erro.message;
        console.error("Erro ao carregar compras:", erro);
    }
}

// =====================================
// INICIALIZAÇÃO
// =====================================

document.addEventListener("DOMContentLoaded", async () => {
    if (!verificarAutenticacaoCartoes()) return;

    inicializarCadastroCartao();
    inicializarFiltroFaturas();

    await carregarCartoes();
}); 