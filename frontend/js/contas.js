
const API_CONTAS = "/api/contas-fixas";

// =====================================
// AUTENTICAÇÃO
// =====================================

function obterTokenContas() {
    return localStorage.getItem("access_token");
}

function encerrarSessaoContas() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("usuario");
    window.location.href = "/login";
}

function verificarAutenticacaoContas() {
    if (!obterTokenContas()) {
        window.location.href = "/login";
        return false;
    }

    return true;
}


// =====================================
// UTILITÁRIOS
// =====================================

function moedaConta(valor) {
    return Number(valor || 0).toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL"
    });
}

function dataAtualConta() {
    const hoje = new Date();

    return [
        hoje.getFullYear(),
        String(hoje.getMonth() + 1).padStart(2, "0"),
        String(hoje.getDate()).padStart(2, "0")
    ].join("-");
}

function escaparConta(valor) {
    return String(valor ?? "").replace(/[&<>"']/g, caractere => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[caractere]);
}


// =====================================
// REQUISIÇÕES COM JWT
// =====================================

async function requisicaoContas(url, opcoes = {}) {
    const token = obterTokenContas();

    if (!token) {
        throw new Error("Token não encontrado. Faça login novamente.");
    }

    const headers = new Headers(opcoes.headers || {});

    headers.set("Authorization", `Bearer ${token}`);

    if (
        opcoes.body &&
        !(opcoes.body instanceof FormData) &&
        !headers.has("Content-Type")
    ) {
        headers.set("Content-Type", "application/json");
    }

    console.log("REQUISIÇÃO CONTAS:", url);
    console.log("TOKEN ENCONTRADO:", Boolean(token));
    console.log("AUTHORIZATION ENVIADO:", headers.has("Authorization"));

    let resposta;

    try {
        resposta = await fetch(url, {
            ...opcoes,
            headers
        });
    } catch (erro) {
        console.error("Erro de conexão:", erro);
        throw new Error("Não foi possível conectar ao servidor.");
    }

    const dados = await resposta.json().catch(() => ({}));

    if (!resposta.ok) {
        console.error("Erro da API:", resposta.status, dados);

        throw new Error(
            typeof dados.detail === "string"
                ? dados.detail
                : "Não foi possível realizar a operação."
        );
    }

    return dados;
}


// =====================================
// INICIALIZAÇÃO
// =====================================

document.addEventListener("DOMContentLoaded", () => {
    if (!verificarAutenticacaoContas()) return;

    const mes = document.getElementById("mesContasFixas");
    const formulario = document.getElementById("formContaFixa");

    const hoje = new Date();

    mes.value =
        `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}`;

    document.getElementById("inicioConta").value = dataAtualConta();
    document.getElementById("categoriaConta").value = "Conta";

    mes.addEventListener("change", carregarContasFixas);
    formulario.addEventListener("submit", cadastrarContaFixa);

    carregarContasFixas();
});


// =====================================
// CARREGAR CONTAS
// =====================================

async function carregarContasFixas() {
    const mes = document.getElementById("mesContasFixas").value;
    const tabela = document.getElementById("tabelaContasFixas");

    tabela.innerHTML = `
        <tr>
            <td colspan="4" class="empty">Carregando contas...</td>
        </tr>
    `;

    try {
        const contas = await requisicaoContas(
            `${API_CONTAS}/mensais?mes=${encodeURIComponent(mes)}`
        );

        tabela.innerHTML = "";

        let pendentes = 0;
        let pagas = 0;
        let valorPendente = 0;

        if (!Array.isArray(contas) || contas.length === 0) {
            tabela.innerHTML = `
                <tr>
                    <td colspan="4" class="empty">
                        Nenhuma conta cadastrada neste mês.
                        Clique em Adicionar conta para começar.
                    </td>
                </tr>
            `;
        }

        contas.forEach(conta => {
            const estaPaga = conta.status === "paga";

            if (estaPaga) {
                pagas++;
            } else {
                pendentes++;
                valorPendente += Number(conta.valor_previsto || 0);
            }

            const tr = document.createElement("tr");

            tr.innerHTML = `
                <td class="transaction-name">
                    <strong>${escaparConta(conta.nome)}</strong>
                    <br>
                    <small>${escaparConta(conta.categoria || "Conta")}</small>

                    ${
                        conta.atrasada
                            ? '<span class="conta-atrasada">Atrasada</span>'
                            : ""
                    }
                </td>

                <td>
                    <strong>${moedaConta(conta.valor_previsto)}</strong>
                    ${
                        estaPaga
                            ? `<br><small>Pago: ${moedaConta(conta.valor_pago)}</small>`
                            : ""
                    }
                </td>

                <td>
                    <span class="conta-status ${estaPaga ? "paga" : "pendente"}">
                        ${estaPaga ? "Paga" : "Pendente"}
                    </span>
                </td>

                <td>
                    <div class="acoes-conta">
                        ${
                            estaPaga
                                ? ""
                                : `<button class="btn-primary btn-pagar"
                                    data-id="${conta.id}">
                                    Pagar
                                </button>`
                        }

                        <button class="btn-editar-conta"
                            data-id="${conta.conta_fixa_id}">
                            Editar
                        </button>

                        <button class="btn-remover-conta"
                            data-id="${conta.conta_fixa_id}"
                            data-nome="${escaparConta(conta.nome)}">
                            Remover
                        </button>
                    </div>
                </td>
            `;

            tabela.appendChild(tr);
        });

        document.getElementById("totalContasPendentes").textContent = pendentes;
        document.getElementById("totalContasPagas").textContent = pagas;

        document.getElementById("valorContasPendentes").textContent =
            moedaConta(valorPendente);

        tabela.querySelectorAll(".btn-pagar").forEach(botao => {
            botao.addEventListener("click", () => {
                const conta = contas.find(
                    item => item.id === Number(botao.dataset.id)
                );

                if (conta) {
                    pagarConta(conta);
                }
            });
        });

        tabela.querySelectorAll(".btn-editar-conta").forEach(botao => {
            botao.addEventListener("click", () => {
                editarContaNaPagina(Number(botao.dataset.id));
            });
        });

        tabela.querySelectorAll(".btn-remover-conta").forEach(botao => {
            botao.addEventListener("click", () => {
                removerConta(
                    Number(botao.dataset.id),
                    botao.dataset.nome
                );
            });
        });

    } catch (erro) {
        console.error("Erro ao carregar contas:", erro);

        tabela.innerHTML = `
            <tr>
                <td colspan="4" class="empty">
                    Erro ao carregar contas: ${escaparConta(erro.message)}
                </td>
            </tr>
        `;
    }
}


// =====================================
// CADASTRAR CONTA
// =====================================

async function cadastrarContaFixa(evento) {
    evento.preventDefault();

    const formulario = document.getElementById("formContaFixa");
    const cadastro = document.getElementById("cadastroConta");
    const mensagem = document.getElementById("mensagemConta");

    const dados = {
        nome: document.getElementById("nomeConta").value.trim(),
        categoria:
            document.getElementById("categoriaConta").value.trim() || "Conta",
        descricao:
            document.getElementById("descricaoConta").value.trim() || null,
        valor: Number(document.getElementById("valorConta").value),
        dia_vencimento: 1,
        valor_padrao: true,
        data_inicio: dataAtualConta()
    };

    try {
        await requisicaoContas(API_CONTAS, {
            method: "POST",
            body: JSON.stringify(dados)
        });

        mensagem.textContent = "Conta cadastrada com sucesso!";
        mensagem.className = "form-message success";

        formulario.reset();

        document.getElementById("categoriaConta").value = "Conta";
        document.getElementById("inicioConta").value = dataAtualConta();

        cadastro.open = false;

        await carregarContasFixas();

    } catch (erro) {
        mensagem.textContent = erro.message;
        mensagem.className = "form-message error";
    }
}


// =====================================
// EDITAR CONTA
// =====================================

async function editarContaNaPagina(id) {
    const tabela = document.getElementById("tabelaContasFixas");

    try {
        const contas = await requisicaoContas(API_CONTAS);
        const conta = contas.find(item => item.id === id);

        if (!conta) {
            alert("Conta não encontrada.");
            return;
        }

        const linha = tabela.querySelector(
            `.btn-editar-conta[data-id="${id}"]`
        )?.closest("tr");

        if (!linha) return;

        linha.innerHTML = `
            <td colspan="4">
                <div class="editor-conta">
                    <h4>Editando: ${escaparConta(conta.nome)}</h4>

                    <div class="editor-conta-grid">
                        <div>
                            <label>Nome da conta</label>
                            <input
                                type="text"
                                class="editar-nome"
                                maxlength="150"
                                value="${escaparConta(conta.nome)}"
                            >
                        </div>

                        <div>
                            <label>Categoria</label>
                            <input
                                type="text"
                                class="editar-categoria"
                                maxlength="100"
                                value="${escaparConta(conta.categoria || "Conta")}"
                            >
                        </div>

                        <div>
                            <label>Valor previsto (R$)</label>
                            <input
                                type="number"
                                class="editar-valor"
                                min="0.01"
                                step="0.01"
                                value="${(Number(conta.valor_centavos) / 100).toFixed(2)}"
                            >
                        </div>

                        <div>
                            <label>Descrição</label>
                            <input
                                type="text"
                                class="editar-descricao"
                                maxlength="300"
                                value="${escaparConta(conta.descricao || "")}"
                            >
                        </div>
                    </div>

                    <div class="acoes-editor-conta">
                        <button class="btn-primary salvar-edicao">
                            Salvar alterações
                        </button>

                        <button class="cancelar-edicao">
                            Cancelar
                        </button>
                    </div>
                </div>
            </td>
        `;

        linha.querySelector(".cancelar-edicao").addEventListener(
            "click",
            carregarContasFixas
        );

        linha.querySelector(".salvar-edicao").addEventListener(
            "click",
            async () => {
                const nome = linha.querySelector(".editar-nome").value.trim();
                const categoria =
                    linha.querySelector(".editar-categoria").value.trim() || "Conta";
                const valor = Number(
                    linha.querySelector(".editar-valor").value
                );
                const descricao =
                    linha.querySelector(".editar-descricao").value.trim();

                if (nome.length < 2) {
                    alert("Informe um nome válido.");
                    return;
                }

                if (!Number.isFinite(valor) || valor <= 0) {
                    alert("Informe um valor válido.");
                    return;
                }

                try {
                    await requisicaoContas(`${API_CONTAS}/${id}`, {
                        method: "PATCH",
                        body: JSON.stringify({
                            nome,
                            categoria,
                            descricao,
                            valor
                        })
                    });

                    alert("Conta atualizada com sucesso!");

                    await carregarContasFixas();

                } catch (erro) {
                    alert("Erro ao atualizar: " + erro.message);
                }
            }
        );

    } catch (erro) {
        alert("Erro ao abrir edição: " + erro.message);
    }
}


// =====================================
// REMOVER CONTA
// =====================================

async function removerConta(id, nome) {
    const confirmado = confirm(
        `Deseja excluir definitivamente "${nome}"?\n\n` +
        "As ocorrências mensais serão apagadas. " +
        "As despesas já registradas no histórico serão preservadas."
    );

    if (!confirmado) return;

    try {
        await requisicaoContas(`${API_CONTAS}/${id}`, {
            method: "DELETE"
        });

        alert("Conta removida com sucesso!");

        await carregarContasFixas();

    } catch (erro) {
        console.error("Erro ao remover conta:", erro);
        alert("Não foi possível remover: " + erro.message);
    }
}


// =====================================
// PAGAR CONTA
// =====================================

async function pagarConta(conta) {
    const valorPrevisto = Number(conta.valor_previsto || 0);

    const valorInformado = prompt(
        `Quanto você pagou pela conta "${conta.nome}"?\n\n` +
        `Valor previsto: ${moedaConta(valorPrevisto)}`,
        valorPrevisto.toFixed(2)
    );

    if (valorInformado === null) return;

    const valorPago = Number(valorInformado.replace(",", "."));

    if (!Number.isFinite(valorPago) || valorPago <= 0) {
        alert("Informe um valor válido.");
        return;
    }

    if (!confirm(`Confirmar pagamento de ${moedaConta(valorPago)}?`)) {
        return;
    }

    try {
        await requisicaoContas(
            `${API_CONTAS}/mensais/${conta.id}/pagar`,
            {
                method: "POST",
                body: JSON.stringify({
                    valor_pago: valorPago,
                    data_pagamento: dataAtualConta()
                })
            }
        );

        alert("Pagamento registrado com sucesso!");

        await carregarContasFixas();

        window.dispatchEvent(new CustomEvent("contaPaga"));

    } catch (erro) {
        alert("Erro ao registrar pagamento: " + erro.message);
    }
}
