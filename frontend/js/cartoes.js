
const API_URL = "/api";

let cartoes = [];

const dinheiro = valor =>
    (valor / 100).toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL"
    });

const dataBR = data => {
    if (!data) return "-";

    const [ano, mes, dia] = data.split("-");
    return `${dia}/${mes}/${ano}`;
};

function mensagem(elemento, texto, erro = false) {
    elemento.textContent = texto;
    elemento.style.color = erro ? "#dc2626" : "#16a34a";
}

async function requisicao(url, opcoes = {}) {
    const resposta = await fetch(`${API_URL}${url}`, {
        ...opcoes,
        headers: {
            "Content-Type": "application/json",
            ...(opcoes.headers || {})
        }
    });

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
// CADASTRO DE CARTÃO
// =====================================

document.getElementById("btnMostrarCadastro").addEventListener("click", () => {
    document.getElementById("formularioCartao").hidden = false;
});

document.getElementById("btnCancelarCadastro").addEventListener("click", () => {
    document.getElementById("formularioCartao").hidden = true;
});

document.getElementById("formCartao").addEventListener("submit", async event => {
    event.preventDefault();

    const msg = document.getElementById("mensagemCartao");

    const dados = {
        nome: document.getElementById("nomeCartao").value.trim(),
        banco: document.getElementById("bancoCartao").value.trim() || null,
        limite: Number(document.getElementById("limiteCartao").value),
        dia_fechamento: Number(document.getElementById("fechamentoCartao").value),
        dia_vencimento: Number(document.getElementById("vencimentoCartao").value)
    };

    try {
        await requisicao("/cartoes", {
            method: "POST",
            body: JSON.stringify(dados)
        });

        event.target.reset();
        document.getElementById("fechamentoCartao").value = 9;
        document.getElementById("vencimentoCartao").value = 16;
        document.getElementById("formularioCartao").hidden = true;

        mensagem(msg, "Cartão cadastrado com sucesso!");

        await carregarCartoes();

    } catch (erro) {
        mensagem(msg, erro.message, true);
    }
});


// =====================================
// LISTAR CARTÕES
// =====================================

async function carregarCartoes() {
    try {
        cartoes = await requisicao("/cartoes");

        const lista = document.getElementById("listaCartoes");
        const selectCompra = document.getElementById("cartaoCompra");
        const selectFatura = document.getElementById("filtroCartaoFatura");

        lista.innerHTML = "";
        selectCompra.innerHTML = '<option value="">Selecione um cartão</option>';
        selectFatura.innerHTML = '<option value="">Selecione um cartão</option>';

        if (!cartoes.length) {
            lista.innerHTML = "<p>Nenhum cartão cadastrado.</p>";
            document.getElementById("listaFaturas").innerHTML =
                "<p>Cadastre um cartão para começar.</p>";
            return;
        }

        cartoes.forEach(cartao => {
            const disponivel = cartao.disponivel_centavos;

            const card = document.createElement("div");
            card.className = "card";

            const titulo = document.createElement("h3");
            titulo.textContent = cartao.nome;

            const banco = document.createElement("p");
            banco.textContent = cartao.banco || "Cartão de crédito";

            const limite = document.createElement("p");
            limite.textContent = `Limite: ${dinheiro(cartao.limite_centavos)}`;

            const utilizado = document.createElement("p");
            utilizado.textContent = `Utilizado: ${dinheiro(cartao.utilizado_centavos)}`;

            const restante = document.createElement("h2");
            restante.textContent = `Disponível: ${dinheiro(disponivel)}`;

            const datas = document.createElement("p");
            datas.textContent =
                `Fecha dia ${cartao.dia_fechamento} · Vence dia ${cartao.dia_vencimento}`;

            card.append(titulo, banco, limite, utilizado, restante, datas);
            lista.appendChild(card);

            const opcaoCompra = document.createElement("option");
            opcaoCompra.value = cartao.id;
            opcaoCompra.textContent = cartao.nome;
            selectCompra.appendChild(opcaoCompra);

            const opcaoFatura = document.createElement("option");
            opcaoFatura.value = cartao.id;
            opcaoFatura.textContent = cartao.nome;
            selectFatura.appendChild(opcaoFatura);
        });

    } catch (erro) {
        document.getElementById("listaCartoes").textContent = erro.message;
    }
}


// =====================================
// REGISTRAR COMPRA
// =====================================

document.getElementById("formCompra").addEventListener("submit", async event => {
    event.preventDefault();

    const msg = document.getElementById("mensagemCompra");

    const cartaoId = document.getElementById("cartaoCompra").value;

    if (!cartaoId) {
        mensagem(msg, "Selecione um cartão.", true);
        return;
    }

    const dados = {
        descricao: document.getElementById("descricaoCompra").value.trim(),
        categoria: document.getElementById("categoriaCompra").value.trim(),
        valor: Number(document.getElementById("valorCompra").value),
        data: document.getElementById("dataCompra").value
    };

    try {
        await requisicao(`/cartoes/${cartaoId}/compras`, {
            method: "POST",
            body: JSON.stringify(dados)
        });

        event.target.reset();

        mensagem(msg, "Compra registrada com sucesso!");

        await carregarCartoes();
        await carregarFaturas(cartaoId);

    } catch (erro) {
        mensagem(msg, erro.message, true);
    }
});


// =====================================
// LISTAR FATURAS
// =====================================

document.getElementById("filtroCartaoFatura").addEventListener("change", event => {
    if (event.target.value) {
        carregarFaturas(event.target.value);
    } else {
        document.getElementById("listaFaturas").innerHTML =
            "<p>Selecione um cartão para visualizar as faturas.</p>";
    }
});

async function carregarFaturas(cartaoId) {
    const lista = document.getElementById("listaFaturas");

    try {
        const faturas = await requisicao(`/cartoes/${cartaoId}/faturas`);

        lista.innerHTML = "";

        if (!faturas.length) {
            lista.innerHTML = "<p>Esse cartão ainda não possui faturas.</p>";
            return;
        }

        faturas.forEach(fatura => {
            const bloco = document.createElement("div");
            bloco.className = "panel";
            bloco.style.marginBottom = "16px";

            const titulo = document.createElement("h3");
            titulo.textContent =
                `Fatura ${String(fatura.mes).padStart(2, "0")}/${fatura.ano}`;

            const total = document.createElement("h2");
            total.textContent = dinheiro(fatura.total_centavos);

            const vencimento = document.createElement("p");
            vencimento.textContent = `Vencimento: ${dataBR(fatura.vencimento)}`;

            const status = document.createElement("p");
            status.textContent = `Situação: ${fatura.status}`;

            bloco.append(titulo, total, vencimento, status);

            const comprasTitulo = document.createElement("h4");
            comprasTitulo.textContent = "Compras";
            bloco.appendChild(comprasTitulo);

            if (!fatura.compras.length) {
                const vazio = document.createElement("p");
                vazio.textContent = "Nenhuma compra nesta fatura.";
                bloco.appendChild(vazio);
            }

            fatura.compras.forEach(compra => {
                const linha = document.createElement("p");
                linha.textContent =
                    `${dataBR(compra.data)} — ${compra.descricao} — ${dinheiro(compra.valor_centavos)}`;

                bloco.appendChild(linha);
            });

            if (fatura.status !== "paga" && fatura.total_centavos > 0) {
                const botao = document.createElement("button");
                botao.className = "btn-primary";
                botao.textContent = "Pagar fatura inteira";

                botao.addEventListener("click", () => pagarFatura(fatura));

                bloco.appendChild(botao);
            } else if (fatura.status === "paga") {
                const pago = document.createElement("p");
                pago.textContent = "Fatura paga integralmente.";
                bloco.appendChild(pago);
            }

            lista.appendChild(bloco);
        });

    } catch (erro) {
        lista.textContent = erro.message;
    }
}


// =====================================
// PAGAR FATURA INTEIRA
// =====================================

async function pagarFatura(fatura) {
    const confirmado = confirm(
        `Deseja pagar a fatura inteira de ${dinheiro(fatura.total_centavos)}?`
    );

    if (!confirmado) return;

    try {
        const hoje = new Date();
        const dataPagamento =
            `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}-${String(hoje.getDate()).padStart(2, "0")}`;

        await requisicao(`/cartoes/faturas/${fatura.id}/pagar`, {
            method: "POST",
            body: JSON.stringify({
                data_pagamento: dataPagamento
            })
        });

        alert("Fatura paga integralmente!");

        await carregarCartoes();
        await carregarFaturas(fatura.cartao_id);

    } catch (erro) {
        alert(erro.message);
    }
}


// =====================================
// INICIALIZAÇÃO
// =====================================

document.addEventListener("DOMContentLoaded", async () => {
    const hoje = new Date();

    const dataCompra = document.getElementById("dataCompra");

    dataCompra.value =
        `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}-${String(hoje.getDate()).padStart(2, "0")}`;

    await carregarCartoes();
});
