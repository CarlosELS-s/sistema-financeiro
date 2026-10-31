
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
    if (!data) return "-";

    const [ano, mes, dia] = data.split("-");

    return `${dia}/${mes}/${ano}`;
};

const escaparHTML = (valor) => {
    return String(valor ?? "").replace(/[&<>"']/g, caractere => {
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

    document.getElementById("arquivoExcel").addEventListener(
        "change",
        importarExcel
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
// BUSCAR CONTAS FIXAS DO MÊS
// ======================================

async function carregarContasFixasDoMes(mes) {

    if (!mes) return [];

    try {

        const contas = await requisicao(
            `${API_URL}/contas-fixas/mensais?mes=${encodeURIComponent(mes)}`
        );

        const [anoSelecionado, mesSelecionado] = mes.split("-").map(Number);

        return contas
            .filter(conta => {

                const pertenceAoMes =
                    Number(conta.ano) === anoSelecionado &&
                    Number(conta.mes) === mesSelecionado;

                // Somente pendentes entram como previsão.
                // As pagas já aparecem em /transacoes.
                return pertenceAoMes && conta.status === "pendente";

            })
            .map(conta => ({

                id: `conta-fixa-${conta.id}`,

                descricao: conta.nome,

                categoria: conta.categoria || "Contas",

                data: conta.vencimento,

                tipo: "despesa",

                valor: Number(conta.valor_previsto || 0),

                prevista: true,

                contaMensalId: conta.id

            }));

    } catch (erro) {

        console.error("Erro ao carregar contas fixas:", erro);

        return [];

    }

}


// ======================================
// DASHBOARD
// ======================================

async function carregarDashboard() {

    const mes = document.getElementById("mesFiltro").value;

    try {

        const [dados, contasPendentes] = await Promise.all([

            requisicao(
                `${API_URL}/dashboard?mes=${encodeURIComponent(mes)}`
            ),

            carregarContasFixasDoMes(mes)

        ]);

        const totalContasPendentes = contasPendentes.reduce(
            (soma, conta) => soma + conta.valor,
            0
        );

        // As despesas pagas já estão no dashboard.
        // Somamos apenas as contas que ainda estão pendentes.
        const despesasComPrevisao =
            Number(dados.despesas_mes || 0) + totalContasPendentes;

        const saldoComPrevisao =
            Number(dados.saldo_mes || 0) - totalContasPendentes;


        document.getElementById("saldoTotal").textContent =
            formatarMoeda(dados.saldo_total);

        document.getElementById("receitasMes").textContent =
            formatarMoeda(dados.receitas_mes);

        document.getElementById("despesasMes").textContent =
            formatarMoeda(despesasComPrevisao);

        document.getElementById("saldoMes").textContent =
            formatarMoeda(saldoComPrevisao);

        document.getElementById("saldoMes").className =
            saldoComPrevisao >= 0 ? "green-text" : "red-text";


        atualizarGraficoComparacao(
            dados.receitas_mes,
            despesasComPrevisao
        );


        // Agrupa as despesas registradas e as contas pendentes
        // para mostrar tudo no gráfico de categorias.
        const categoriasAgrupadas = new Map();

        (dados.despesas_categoria || []).forEach(item => {

            const categoria = item.categoria || "Outros";

            categoriasAgrupadas.set(
                categoria,
                (categoriasAgrupadas.get(categoria) || 0) +
                Number(item.valor || 0)
            );

        });

        contasPendentes.forEach(conta => {

            const categoria = conta.categoria || "Contas";

            categoriasAgrupadas.set(
                categoria,
                (categoriasAgrupadas.get(categoria) || 0) +
                conta.valor
            );

        });

        const despesasPorCategoria = Array.from(
            categoriasAgrupadas,
            ([categoria, valor]) => ({
                categoria,
                valor
            })
        );

        atualizarGraficoCategorias(despesasPorCategoria);

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
// LISTAR TRANSAÇÕES E CONTAS FIXAS
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

        const [transacoes, contasPendentes] = await Promise.all([

            requisicao(
                `${API_URL}/transacoes?${parametros.toString()}`
            ),

            carregarContasFixasDoMes(mes)

        ]);


        // Junta as movimentações reais com as contas pendentes.
        // Pagamentos não são adicionados novamente, pois já estão
        // registrados como transações no banco.
        let movimentacoes = [
            ...transacoes.map(transacao => ({
                ...transacao,
                prevista: false
            })),

            ...contasPendentes
        ];


        if (tipo) {
            movimentacoes = movimentacoes.filter(
                item => item.tipo === tipo
            );
        }


        // Ordena pela data, da mais recente para a mais antiga.
        movimentacoes.sort((a, b) => {

            const dataA = a.data || "";
            const dataB = b.data || "";

            return dataB.localeCompare(dataA);

        });


        tabela.innerHTML = "";

        if (movimentacoes.length === 0) {

            tabela.innerHTML = `
                <tr>
                    <td colspan="6" class="empty">
                        Nenhuma movimentação encontrada.
                    </td>
                </tr>
            `;

            return;
        }


        movimentacoes.forEach(transacao => {

            const tr = document.createElement("tr");

            const receita = transacao.tipo === "receita";

            const tipoTexto = receita ? "Receita" : "Despesa";

            const sinal = receita ? "+" : "-";

            const ehPrevista = transacao.prevista === true;


            tr.innerHTML = `

                <td class="transaction-name">
                    ${escaparHTML(transacao.descricao)}

                    ${ehPrevista ? `
                        <span style="
                            display:inline-block;
                            margin-left:6px;
                            padding:3px 7px;
                            border-radius:5px;
                            font-size:10px;
                            background:#78350f;
                            color:#fcd34d;
                        ">
                            Prevista
                        </span>
                    ` : ""}
                </td>

                <td class="transaction-category">
                    ${escaparHTML(transacao.categoria)}
                </td>

                <td class="transaction-date">
                    ${formatarData(transacao.data)}
                </td>

                <td>
                    <span class="type-badge type-${transacao.tipo}">
                        ${ehPrevista ? "Despesa prevista" : tipoTexto}
                    </span>
                </td>

                <td class="value-${transacao.tipo}">
                    ${sinal} ${formatarMoeda(transacao.valor)}
                </td>

                <td>
                    ${
                        ehPrevista
                            ? '<span style="color:#94a3b8;">Conta fixa</span>'
                            : `
                                <button
                                    class="delete-btn"
                                    title="Excluir movimentação"
                                    aria-label="Excluir movimentação"
                                    data-id="${transacao.id}"
                                >
                                    ✕
                                </button>
                            `
                    }
                </td>

            `;


            if (!ehPrevista) {

                tr.querySelector(".delete-btn").addEventListener(
                    "click",
                    () => excluirTransacao(transacao.id)
                );

            }

            tabela.appendChild(tr);

        });

    } catch (erro) {

        console.error("Erro ao listar movimentações:", erro);

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


// ======================================
// EXPORTAR PLANILHA EXCEL
// ======================================

async function exportarExcel() {

    try {

        const resposta = await fetch(
            `${API_URL}/planilhas/exportar`
        );

        if (!resposta.ok) {
            throw new Error("Erro ao exportar planilha.");
        }

        const blob = await resposta.blob();

        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");

        link.href = url;

        link.download = "movimentacoes_financeiras.xlsx";

        document.body.appendChild(link);

        link.click();

        link.remove();

        URL.revokeObjectURL(url);

    } catch (erro) {

        alert(erro.message);

    }

}


// ======================================
// IMPORTAR PLANILHA EXCEL
// ======================================

async function importarExcel(evento) {

    const arquivo = evento.target.files[0];

    if (!arquivo) return;

    if (!arquivo.name.toLowerCase().endsWith(".xlsx")) {
        alert("Selecione um arquivo Excel .xlsx.");
        evento.target.value = "";
        return;
    }

    const confirmar = confirm(
        "Deseja importar as movimentações desta planilha? " +
        "As novas movimentações serão adicionadas às existentes."
    );

    if (!confirmar) {
        evento.target.value = "";
        return;
    }

    const formulario = new FormData();

    formulario.append("arquivo", arquivo);

    try {

        const resposta = await fetch(
            `${API_URL}/planilhas/importar`,
            {
                method: "POST",
                body: formulario
            }
        );

        const dados = await resposta.json();

        if (!resposta.ok) {
            throw new Error(
                dados.detail || "Erro ao importar planilha."
            );
        }

        alert(
            `${dados.importadas} movimentações importadas com sucesso!`
        );

        atualizarTela();

    } catch (erro) {

        alert(erro.message);

    } finally {

        evento.target.value = "";

    }

}
