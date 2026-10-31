const API_URL = "/api";

const categorias = {
    receita: [
        "Salário",
        "Freelance",
        "Investimentos",
        "Vendas",
        "Presente",
        "Outros"
    ],

    despesa: [
        "Alimentação",
        "Moradia",
        "Transporte",
        "Saúde",
        "Educação",
        "Lazer",
        "Compras",
        "Contas",
        "Assinaturas",
        "Outros"
    ]
};

const coresGrafico = [
    "#22c55e",
    "#3b82f6",
    "#f59e0b",
    "#a855f7",
    "#ef4444",
    "#06b6d4",
    "#ec4899",
    "#84cc16",
    "#f97316",
    "#64748b"
];

const formatarMoeda = (valor) => {
    return Number(valor || 0).toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL"
    });
};

const formatarData = (data) => {
    const [ano, mes, dia] = data.split("-");

    return `${dia}/${mes}/${ano}`;
};

const escaparHTML = (valor) => {
    return String(valor).replace(/[&<>"']/g, caractere => {
        const mapa = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        };

        return mapa[caractere];
    });
};

async function requisicao(url, opcoes = {}) {
    const resposta = await fetch(url, {
        ...opcoes,
        headers: {
            "Content-Type": "application/json",
            ...opcoes.headers
        }
    });

    const dados = await resposta.json().catch(() => ({}));

    if (!resposta.ok) {
        throw new Error(
            dados.detail || "Não foi possível realizar a operação."
        );
    }

    return dados;
}


// ======================================
// INICIALIZAÇÃO
// ======================================

document.addEventListener("DOMContentLoaded", () => {

    const agora = new Date();

    const mesAtual =
        `${agora.getFullYear()}-${String(agora.getMonth() + 1).padStart(2, "0")}`;

    document.getElementById("mesFiltro").value = mesAtual;

    document.getElementById("data").value =
        `${agora.getFullYear()}-${String(agora.getMonth() + 1).padStart(2, "0")}-${String(agora.getDate()).padStart(2, "0")}`;

    atualizarCategorias();

    carregarDashboard();
    carregarTransacoes();

    document.getElementById("mesFiltro").addEventListener(
        "change",
        atualizarTela
    );

    document.getElementById("filtroTipo").addEventListener(
        "change",
        carregarTransacoes
    );

    document.getElementById("tipo").addEventListener(
        "change",
        atualizarCategorias
    );

    document.getElementById("formTransacao").addEventListener(
        "submit",
        salvarTransacao
    );

});


// ======================================
// ATUALIZAR TELA
// ======================================

function atualizarTela() {
    carregarDashboard();
    carregarTransacoes();
}


// ======================================
// CATEGORIAS
// ======================================

function atualizarCategorias() {

    const tipo = document.getElementById("tipo").value;

    const select = document.getElementById("categoria");

    select.innerHTML = "";

    categorias[tipo].forEach(categoria => {

        const option = document.createElement("option");

        option.value = categoria;
        option.textContent = categoria;

        select.appendChild(option);

    });

}


// ======================================
// DASHBOARD
// ======================================

async function carregarDashboard() {

    const mes = document.getElementById("mesFiltro").value;

    try {

        const dados = await requisicao(
            `${API_URL}/dashboard?mes=${encodeURIComponent(mes)}`
        );

        document.getElementById("saldoTotal").textContent =
            formatarMoeda(dados.saldo_total);

        document.getElementById("receitasMes").textContent =
            formatarMoeda(dados.receitas_mes);

        document.getElementById("despesasMes").textContent =
            formatarMoeda(dados.despesas_mes);

        document.getElementById("saldoMes").textContent =
            formatarMoeda(dados.saldo_mes);

        document.getElementById("saldoMes").className =
            dados.saldo_mes >= 0 ? "green-text" : "red-text";

        atualizarGraficoComparacao(
            dados.receitas_mes,
            dados.despesas_mes
        );

        atualizarGraficoCategorias(
            dados.despesas_categoria
        );

    } catch (erro) {

        console.error("Erro ao carregar dashboard:", erro);

        mostrarMensagem(
            "Não foi possível carregar o dashboard.",
            "error"
        );

    }

}


// ======================================
// GRÁFICO RECEITAS X DESPESAS
// ======================================

function atualizarGraficoComparacao(receitas, despesas) {

    const maior = Math.max(receitas, despesas, 1);

    const porcentagemReceitas = (receitas / maior) * 100;
    const porcentagemDespesas = (despesas / maior) * 100;

    document.getElementById("barraReceitas").style.width =
        `${porcentagemReceitas}%`;

    document.getElementById("barraDespesas").style.width =
        `${porcentagemDespesas}%`;

    document.getElementById("graficoReceitasValor").textContent =
        formatarMoeda(receitas);

    document.getElementById("graficoDespesasValor").textContent =
        formatarMoeda(despesas);

}


// ======================================
// GRÁFICO DE CATEGORIAS
// ======================================

function atualizarGraficoCategorias(dados) {

    const grafico = document.getElementById("graficoCategorias");

    const legenda = document.getElementById("legendaCategorias");

    const total = dados.reduce(
        (soma, item) => soma + Number(item.valor),
        0
    );

    document.getElementById("totalCategorias").textContent =
        formatarMoeda(total);

    legenda.innerHTML = "";

    if (total <= 0) {

        grafico.style.background =
            "conic-gradient(#263247 0deg 360deg)";

        legenda.innerHTML =
            '<span class="legend-item">Nenhuma despesa registrada</span>';

        return;
    }

    let anguloAtual = 0;

    const partes = [];

    dados.forEach((item, indice) => {

        const porcentagem = (item.valor / total) * 100;

        const angulo = (porcentagem / 100) * 360;

        const cor = coresGrafico[indice % coresGrafico.length];

        partes.push(
            `${cor} ${anguloAtual}deg ${anguloAtual + angulo}deg`
        );

        anguloAtual += angulo;

        const elemento = document.createElement("div");

        elemento.className = "legend-item";

        elemento.innerHTML = `
            <span
                class="legend-color"
                style="background:${cor}"
            ></span>

            <span>${escaparHTML(item.categoria)}</span>

            <strong>${porcentagem.toFixed(1)}%</strong>
        `;

        legenda.appendChild(elemento);

    });

    grafico.style.background =
        `conic-gradient(${partes.join(", ")})`;

}


// ======================================
// LISTAR TRANSAÇÕES
// ======================================

async function carregarTransacoes() {

    const mes = document.getElementById("mesFiltro").value;

    const tipo = document.getElementById("filtroTipo").value;

    const tabela = document.getElementById("tabelaTransacoes");

    tabela.innerHTML = `
        <tr>
            <td colspan="6" class="empty">
                Carregando...
            </td>
        </tr>
    `;

    try {

        const parametros = new URLSearchParams();

        if (mes) parametros.append("mes", mes);

        if (tipo) parametros.append("tipo", tipo);

        const transacoes = await requisicao(
            `${API_URL}/transacoes?${parametros.toString()}`
        );

        tabela.innerHTML = "";

        if (transacoes.length === 0) {

            tabela.innerHTML = `
                <tr>
                    <td colspan="6" class="empty">
                        Nenhuma movimentação encontrada.
                    </td>
                </tr>
            `;

            return;
        }

        transacoes.forEach(transacao => {

            const tr = document.createElement("tr");

            const receita = transacao.tipo === "receita";

            const tipoTexto = receita ? "Receita" : "Despesa";

            const sinal = receita ? "+" : "-";

            tr.innerHTML = `

                <td class="transaction-name">
                    ${escaparHTML(transacao.descricao)}
                </td>

                <td class="transaction-category">
                    ${escaparHTML(transacao.categoria)}
                </td>

                <td class="transaction-date">
                    ${formatarData(transacao.data)}
                </td>

                <td>
                    <span class="type-badge type-${transacao.tipo}">
                        ${tipoTexto}
                    </span>
                </td>

                <td class="value-${transacao.tipo}">
                    ${sinal} ${formatarMoeda(transacao.valor)}
                </td>

                <td>
                    <button
                        class="delete-btn"
                        title="Excluir movimentação"
                        aria-label="Excluir movimentação"
                        data-id="${transacao.id}"
                    >
                        ✕
                    </button>
                </td>

            `;

            tr.querySelector(".delete-btn").addEventListener(
                "click",
                () => excluirTransacao(transacao.id)
            );

            tabela.appendChild(tr);

        });

    } catch (erro) {

        console.error("Erro ao listar transações:", erro);

        tabela.innerHTML = `
            <tr>
                <td colspan="6" class="empty">
                    Erro ao carregar movimentações.
                </td>
            </tr>
        `;

    }

}


// ======================================
// CADASTRAR TRANSAÇÃO
// ======================================

async function salvarTransacao(evento) {

    evento.preventDefault();

    const botao = document.getElementById("btnSalvar");

    const mensagem = document.getElementById("mensagemFormulario");

    const dados = {

        descricao: document.getElementById("descricao").value.trim(),

        tipo: document.getElementById("tipo").value,

        categoria: document.getElementById("categoria").value,

        valor: Number(document.getElementById("valor").value),

        data: document.getElementById("data").value

    };

    if (
        !dados.descricao ||
        !dados.categoria ||
        !dados.data ||
        !Number.isFinite(dados.valor) ||
        dados.valor <= 0
    ) {

        mensagem.textContent = "Preencha todos os campos corretamente.";

        mensagem.className = "form-message error";

        return;
    }

    botao.disabled = true;
    botao.textContent = "Salvando...";

    try {

        await requisicao(`${API_URL}/transacoes`, {

            method: "POST",

            body: JSON.stringify(dados)

        });

        mensagem.textContent =
            "Movimentação cadastrada com sucesso!";

        mensagem.className = "form-message success";

        document.getElementById("formTransacao").reset();

        atualizarCategorias();

        const agora = new Date();

        document.getElementById("data").value =
            `${agora.getFullYear()}-${String(agora.getMonth() + 1).padStart(2, "0")}-${String(agora.getDate()).padStart(2, "0")}`;

        atualizarTela();

    } catch (erro) {

        mensagem.textContent = erro.message;

        mensagem.className = "form-message error";

    } finally {

        botao.disabled = false;

        botao.textContent = "Salvar movimentação";

    }

}


// ======================================
// EXCLUIR TRANSAÇÃO
// ======================================

async function excluirTransacao(id) {

    const confirmar = confirm(
        "Tem certeza que deseja excluir esta movimentação?"
    );

    if (!confirmar) return;

    try {

        await requisicao(`${API_URL}/transacoes/${id}`, {

            method: "DELETE"

        });

        atualizarTela();

    } catch (erro) {

        alert(erro.message);

    }

}


// ======================================
// NAVEGAÇÃO
// ======================================

function irParaFormulario() {

    document.getElementById("nova-transacao").scrollIntoView({
        behavior: "smooth"
    });

    document.getElementById("descricao").focus();

}


// ======================================
// MENSAGENS
// ======================================

function mostrarMensagem(texto, tipo) {

    const mensagem = document.getElementById("mensagemFormulario");

    mensagem.textContent = texto;

    mensagem.className = `form-message ${tipo}`;

}