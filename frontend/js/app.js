
const API_URL = "/api";

// ======================================
// MODO VISITANTE
// ======================================

function ehVisitante() {
    try {
        const usuario = JSON.parse(
            localStorage.getItem("usuario") || "{}"
        );

        return usuario.visitante === true;
    } catch {
        return false;
    }
}

const MODO_VISITANTE = ehVisitante();
let cartoesDisponiveisOrcamento = [];
let orcamentoEmEdicao = false;

// ======================================
// CATEGORIAS
// ======================================

const categorias = {
    receita: [
        "Salário", "Freelance", "Investimentos",
        "Vendas", "Presente", "Outros"
    ],
    despesa: [
        "Alimentação", "Moradia", "Transporte", "Saúde",
        "Educação", "Lazer", "Compras", "Contas",
        "Assinaturas", "Parcelados", "Outros"
    ]
};

const coresGrafico = [
    "#22c55e", "#3b82f6", "#f59e0b", "#a855f7",
    "#ef4444", "#06b6d4", "#ec4899", "#84cc16",
    "#f97316", "#64748b"
];

// ======================================
// FORMATAÇÃO
// ======================================

const formatarMoeda = valor => {
    const numero = Number(valor || 0);
    const negativo = numero < 0;

    const formatado = Math.abs(numero).toLocaleString("pt-BR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });

    return `${negativo ? "-" : ""}R$ ${formatado}`;
};

const formatarData = data => {
    if (!data) return "-";
    const [ano, mes, dia] = data.split("-");
    return `${dia}/${mes}/${ano}`;
};

const escaparHTML = valor => {
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

// ======================================
// AUTENTICAÇÃO E REQUISIÇÕES
// ======================================

function obterToken() {
    return localStorage.getItem("access_token");
}

function limparSessao() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("usuario");
}

function redirecionarLogin() {
    limparSessao();

    if (window.location.pathname !== "/login") {
        window.location.href = "/login";
    }
}

async function requisicao(url, opcoes = {}) {
    const token = obterToken();

    if (!token) {
        redirecionarLogin();
        throw new Error("Faça login para continuar.");
    }

    const headers = { ...opcoes.headers };

    if (
        opcoes.body &&
        !(opcoes.body instanceof FormData) &&
        !headers["Content-Type"]
    ) {
        headers["Content-Type"] = "application/json";
    }

    headers["Authorization"] = `Bearer ${token}`;

    const resposta = await fetch(url, {
        ...opcoes,
        headers
    });

    if (resposta.status === 401) {
        redirecionarLogin();
        throw new Error("Sua sessão expirou. Faça login novamente.");
    }

    const texto = await resposta.text();
    let dados = {};

    try {
        dados = texto ? JSON.parse(texto) : {};
    } catch {
        dados = {};
    }

    if (!resposta.ok) {
        console.error("Erro da API:", {
            url,
            status: resposta.status,
            resposta: texto
        });

        throw new Error(
            dados.detail ||
            dados.mensagem ||
            dados.message ||
            `Erro ${resposta.status}: ${texto || "Não foi possível realizar a operação."}`
        );
    }

    return dados;
}

// ======================================
// INICIALIZAÇÃO
// ======================================

document.addEventListener("DOMContentLoaded", () => {
    if (!obterToken()) {
        redirecionarLogin();
        return;
    }

    if (MODO_VISITANTE) {
        const aviso = document.createElement("div");

        aviso.id = "avisoVisitante";
        aviso.innerHTML = `
            <strong>👁 Modo visitante — demonstração</strong>
            <span>Você está visualizando dados fictícios. As alterações estão desativadas.</span>
        `;

        aviso.style.cssText = `
            background: #1e3a5f;
            color: #dbeafe;
            border: 1px solid #3b82f6;
            padding: 14px 18px;
            border-radius: 10px;
            margin: 15px 0 20px;
            display: flex;
            flex-direction: column;
            gap: 5px;
        `;

        document.querySelector("main")?.prepend(aviso);

        bloquearEdicaoVisitante();
    }

    const usuarioSalvo = localStorage.getItem("usuario");

    if (usuarioSalvo) {
        try {
            const usuario = JSON.parse(usuarioSalvo);
            const nomeElemento = document.querySelector(".user-card strong");
            const avatarElemento = document.querySelector(".user-avatar");

            if (nomeElemento && usuario.nome) {
                nomeElemento.textContent = usuario.nome;
            }

            if (avatarElemento && usuario.nome) {
                avatarElemento.textContent =
                    usuario.nome.charAt(0).toUpperCase();
            }
        } catch (erro) {
            console.error("Erro ao carregar usuário:", erro);
        }
    }

    const agora = new Date();

    const mesAtual =
        `${agora.getFullYear()}-${String(agora.getMonth() + 1).padStart(2, "0")}`;

    const mesFiltro = document.getElementById("mesFiltro");
    const campoData = document.getElementById("data");

    if (mesFiltro) mesFiltro.value = mesAtual;

    if (campoData) {
        campoData.value =
            `${agora.getFullYear()}-${String(agora.getMonth() + 1).padStart(2, "0")}-${String(agora.getDate()).padStart(2, "0")}`;
    }

    atualizarCategorias();
    configurarPagamento();

    carregarDashboard();
    carregarTransacoes();
    carregarCartoes();

    carregarCategoriasOrcamento();
    prepararSelecaoCartoesOrcamento();
    carregarCartoesOrcamento();
    carregarOrcamentos();

    configurarOrcamentosRecolhiveis();

    mesFiltro?.addEventListener("change", atualizarTela);

    ["filtroTipo", "filtroCategoria", "filtroOrigem"].forEach(id => {
        document.getElementById(id)?.addEventListener(
            "change",
            carregarTransacoes
        );
    });

    document.getElementById("tipo")?.addEventListener("change", () => {
        atualizarCategorias();
        atualizarCamposPagamento();
    });

    // Apenas um evento para salvar orçamento.
    document.getElementById("formOrcamento")?.addEventListener(
        "submit",
        salvarOrcamento
    );

    document.getElementById("formaPagamento")?.addEventListener(
        "change",
        atualizarCamposPagamento
    );

    document.getElementById("formTransacao")?.addEventListener("reset", () => {
        setTimeout(() => {
            atualizarCategorias();
            configurarPagamento();
        }, 0);
    });

    document.getElementById("formOrcamento")?.addEventListener("reset", () => {
        setTimeout(() => {
            orcamentoEmEdicao = false;

            const categoria = document.getElementById("orcamentoCategoria");
            const botao = document.getElementById("btnSalvarOrcamento");
            const mensagem = document.getElementById("mensagemOrcamento");

            if (categoria) categoria.disabled = false;
            if (botao) botao.textContent = "Salvar orçamento";
            if (mensagem) mensagem.textContent = "";

            carregarCategoriasOrcamento();
            renderizarCartoesOrcamento();
            atualizarVisibilidadeCartoesOrcamento();
        }, 0);
    });

    document.getElementById("orcamentoCategoria")?.addEventListener(
        "change",
        atualizarVisibilidadeCartoesOrcamento
    );

    document.getElementById("arquivoExcel")?.addEventListener(
        "change",
        importarExcel
    );
});

// ======================================
// ORÇAMENTOS RECOLHÍVEIS
// ======================================

function configurarOrcamentosRecolhiveis() {
    const botao = document.getElementById("btnExpandirOrcamentos");
    const conteudo = document.getElementById("conteudoOrcamentos");
    const texto = document.getElementById("textoExpandirOrcamentos");
    const icone = document.getElementById("iconeExpandirOrcamentos");

    if (!botao || !conteudo) return;

    conteudo.hidden = true;
    botao.setAttribute("aria-expanded", "false");

    if (texto) texto.textContent = "Expandir";
    if (icone) icone.textContent = "⌄";

    botao.addEventListener("click", () => {
        const expandido = botao.getAttribute("aria-expanded") === "true";
        const novoEstado = !expandido;

        conteudo.hidden = !novoEstado;
        botao.setAttribute("aria-expanded", String(novoEstado));

        if (texto) texto.textContent = novoEstado ? "Recolher" : "Expandir";
        if (icone) icone.textContent = novoEstado ? "⌃" : "⌄";
    });
}

// ======================================
// PAGAMENTO E CARTÕES
// ======================================

function configurarPagamento() {
    const forma = document.getElementById("formaPagamento");

    if (forma) forma.value = "pix";

    atualizarCamposPagamento();
}

function atualizarCamposPagamento() {
    const tipoElemento = document.getElementById("tipo");
    const formaElemento = document.getElementById("formaPagamento");

    const grupoForma = document.getElementById("grupoFormaPagamento");
    const grupoCartao = document.getElementById("grupoCartao");
    const grupoParcelas = document.getElementById("grupoParcelas");

    const cartaoElemento = document.getElementById("cartaoSelecionado");
    const parcelasElemento = document.getElementById("quantidadeParcelas");

    if (!tipoElemento) return;

    const ehDespesa = tipoElemento.value === "despesa";
    const ehCredito = ehDespesa && formaElemento?.value === "credito";

    if (grupoForma) grupoForma.hidden = !ehDespesa;
    if (grupoCartao) grupoCartao.hidden = !ehCredito;
    if (grupoParcelas) grupoParcelas.hidden = !ehCredito;

    if (!ehCredito) {
        if (cartaoElemento) cartaoElemento.value = "";
        if (parcelasElemento) parcelasElemento.value = "1";
    }
}

async function carregarCartoes() {
    const select = document.getElementById("cartaoSelecionado");

    if (!select) return;

    try {
        const cartoes = await requisicao(`${API_URL}/cartoes`);

        select.innerHTML = `<option value="">Selecione um cartão</option>`;

        cartoes.forEach(cartao => {
            const option = document.createElement("option");

            option.value = cartao.id;
            option.textContent =
                `${cartao.nome} - Disponível: ${formatarMoeda(cartao.disponivel_centavos / 100)}`;

            select.appendChild(option);
        });

        if (!cartoes.length) {
            select.innerHTML = `<option value="">Nenhum cartão cadastrado</option>`;
        }
    } catch (erro) {
        console.error("Erro ao carregar cartões:", erro);
        select.innerHTML = `<option value="">Erro ao carregar cartões</option>`;
    }
}

// ======================================
// ATUALIZAR TELA
// ======================================

function atualizarTela() {
    carregarDashboard();
    carregarTransacoes();
    carregarOrcamentos();
}

// ======================================
// CATEGORIAS
// ======================================

function atualizarCategorias() {
    const tipoElemento = document.getElementById("tipo");
    const select = document.getElementById("categoria");

    if (!tipoElemento || !select) return;

    select.innerHTML = "";

    (categorias[tipoElemento.value] || categorias.despesa).forEach(categoria => {
        const option = document.createElement("option");

        option.value = categoria;
        option.textContent = categoria;

        select.appendChild(option);
    });
}

// ======================================
// CONTAS FIXAS
// ======================================

async function carregarContasFixasDoMes(mes) {
    if (!mes) return [];

    try {
        const contas = await requisicao(
            `${API_URL}/contas-fixas/mensais?mes=${encodeURIComponent(mes)}`
        );

        const [anoSelecionado, mesSelecionado] = mes.split("-").map(Number);

        return contas
            .filter(conta =>
                Number(conta.ano) === anoSelecionado &&
                Number(conta.mes) === mesSelecionado &&
                conta.status === "pendente"
            )
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
    const campoMes = document.getElementById("mesFiltro");

    if (!campoMes) return;

    const mes = campoMes.value;

    try {
        const [dados, contasPendentes] = await Promise.all([
            requisicao(`${API_URL}/dashboard?mes=${encodeURIComponent(mes)}`),
            carregarContasFixasDoMes(mes)
        ]);

        const totalContasPendentes = contasPendentes.reduce(
            (soma, conta) => soma + conta.valor,
            0
        );

        const despesasComPrevisao =
            Number(dados.despesas_mes || 0) + totalContasPendentes;

        const saldoComPrevisao =
            Number(dados.saldo_mes || 0) - totalContasPendentes;

        const saldoTotalElemento = document.getElementById("saldoTotal");
        const saldoTotal = Number(dados.saldo_total || 0);

        if (saldoTotalElemento) {
            saldoTotalElemento.textContent = formatarMoeda(saldoTotal);
            saldoTotalElemento.style.whiteSpace = "nowrap";
            saldoTotalElemento.classList.toggle("red-text", saldoTotal < 0);
            saldoTotalElemento.classList.toggle("green-text", saldoTotal >= 0);
        }

        const saldoMesElemento = document.getElementById("saldoMes");

        if (saldoMesElemento) {
            saldoMesElemento.textContent = formatarMoeda(saldoComPrevisao);
            saldoMesElemento.style.whiteSpace = "nowrap";
            saldoMesElemento.classList.toggle("red-text", saldoComPrevisao < 0);
            saldoMesElemento.classList.toggle("green-text", saldoComPrevisao >= 0);
        }

        document.getElementById("receitasMes").textContent =
            formatarMoeda(dados.receitas_mes);

        document.getElementById("despesasMes").textContent =
            formatarMoeda(despesasComPrevisao);

        atualizarGraficoComparacao(
            Number(dados.receitas_mes || 0),
            despesasComPrevisao
        );

        const categoriasAgrupadas = new Map();

        (dados.despesas_categoria || []).forEach(item => {
            const categoria = item.categoria || "Outros";

            categoriasAgrupadas.set(
                categoria,
                (categoriasAgrupadas.get(categoria) || 0) + Number(item.valor || 0)
            );
        });

        contasPendentes.forEach(conta => {
            const categoria = conta.categoria || "Contas";

            categoriasAgrupadas.set(
                categoria,
                (categoriasAgrupadas.get(categoria) || 0) + conta.valor
            );
        });

        atualizarGraficoCategorias(
            Array.from(categoriasAgrupadas, ([categoria, valor]) => ({
                categoria,
                valor
            }))
        );
    } catch (erro) {
        console.error("Erro ao carregar dashboard:", erro);
        mostrarMensagem("Não foi possível carregar o dashboard.", "error");
    }
}

// ======================================
// GRÁFICOS
// ======================================

function atualizarGraficoComparacao(receitas, despesas) {
    const barraReceitas = document.getElementById("barraReceitas");
    const barraDespesas = document.getElementById("barraDespesas");

    if (!barraReceitas || !barraDespesas) return;

    const maior = Math.max(receitas, despesas, 1);

    barraReceitas.style.width = `${(receitas / maior) * 100}%`;
    barraDespesas.style.width = `${(despesas / maior) * 100}%`;

    document.getElementById("graficoReceitasValor").textContent =
        formatarMoeda(receitas);

    document.getElementById("graficoDespesasValor").textContent =
        formatarMoeda(despesas);
}

function atualizarGraficoCategorias(dados) {
    const grafico = document.getElementById("graficoCategorias");
    const legenda = document.getElementById("legendaCategorias");

    if (!grafico || !legenda) return;

    const total = dados.reduce(
        (soma, item) => soma + Number(item.valor),
        0
    );

    document.getElementById("totalCategorias").textContent =
        formatarMoeda(total);

    legenda.innerHTML = "";

    if (total <= 0) {
        grafico.style.background = "conic-gradient(#263247 0deg 360deg)";
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

        partes.push(`${cor} ${anguloAtual}deg ${anguloAtual + angulo}deg`);
        anguloAtual += angulo;

        const elemento = document.createElement("div");
        elemento.className = "legend-item";

        elemento.innerHTML = `
            <span class="legend-color" style="background:${cor}"></span>
            <span>${escaparHTML(item.categoria)}</span>
            <strong>${porcentagem.toFixed(1)}%</strong>
        `;

        legenda.appendChild(elemento);
    });

    grafico.style.background = `conic-gradient(${partes.join(", ")})`;
}

// ======================================
// MOVIMENTAÇÕES
// ======================================

async function carregarTransacoes() {
    const mes = document.getElementById("mesFiltro")?.value;
    const tipo = document.getElementById("filtroTipo")?.value || "";
    const categoria = document.getElementById("filtroCategoria")?.value || "";
    const origem = document.getElementById("filtroOrigem")?.value || "";
    const tabela = document.getElementById("tabelaTransacoes");

    if (!tabela) return;

    tabela.innerHTML =
        `<tr><td colspan="6" class="empty">Carregando...</td></tr>`;

    try {
        const parametros = new URLSearchParams();

        if (mes) parametros.append("mes", mes);

        const [transacoes, contasPendentes] = await Promise.all([
            requisicao(`${API_URL}/movimentos?${parametros.toString()}`),
            carregarContasFixasDoMes(mes)
        ]);

        let movimentacoes = [
            ...transacoes.map(item => ({ ...item, prevista: false })),
            ...contasPendentes
        ];

        movimentacoes = movimentacoes.map(item => ({
            ...item,
            origem: item.prevista
                ? "conta-fixa"
                : item.origem === "cartao"
                    ? "cartao"
                    : "transacao"
        }));

        const selectCategoria = document.getElementById("filtroCategoria");

        if (selectCategoria) {
            const categoriasDisponiveis = [
                ...new Set(movimentacoes.map(item => item.categoria || "Outros"))
            ].sort((a, b) => a.localeCompare(b, "pt-BR"));

            selectCategoria.innerHTML = `
                <option value="">Todas as categorias</option>
                ${categoriasDisponiveis.map(nome => `
                    <option value="${escaparHTML(nome)}">${escaparHTML(nome)}</option>
                `).join("")}
            `;

            if (categoriasDisponiveis.includes(categoria)) {
                selectCategoria.value = categoria;
            }
        }

        if (tipo) {
            movimentacoes = movimentacoes.filter(item => item.tipo === tipo);
        }

        if (categoria) {
            movimentacoes = movimentacoes.filter(
                item => (item.categoria || "Outros") === categoria
            );
        }

        if (origem) {
            movimentacoes = movimentacoes.filter(
                item => item.origem === origem
            );
        }

        movimentacoes.sort((a, b) =>
            (b.data || "").localeCompare(a.data || "")
        );

        tabela.innerHTML = "";

        if (!movimentacoes.length) {
            tabela.innerHTML = `
                <tr><td colspan="6" class="empty">
                    Nenhuma movimentação encontrada com esses filtros.
                </td></tr>
            `;
            return;
        }

        movimentacoes.forEach(transacao => {
            const tr = document.createElement("tr");
            const receita = transacao.tipo === "receita";
            const tipoTexto = receita ? "Receita" : "Despesa";
            const sinal = receita ? "+" : "-";
            const ehPrevista = transacao.prevista === true;
            const ehParcelaCartao = transacao.origem === "cartao";

            const descricaoExibida =
                ehParcelaCartao && transacao.cartao_nome
                    ? `${transacao.descricao} (${transacao.cartao_nome})`
                    : transacao.descricao;

            let identificacao = "";

            if (ehPrevista) {
                identificacao =
                    `<span class="movement-tag tag-prevista">Prevista</span>`;
            } else if (ehParcelaCartao) {
                identificacao =
                    `<span class="movement-tag tag-cartao">Parcela do cartão</span>`;
            }

            let acao = "";

            if (ehPrevista) {
                acao = '<span style="color:#94a3b8;">Conta fixa</span>';
            } else if (ehParcelaCartao) {
                acao = '<span style="color:#94a3b8;">Fatura do cartão</span>';
            } else {
                acao = `
                    <button class="delete-btn" title="Excluir movimentação"
                        aria-label="Excluir movimentação"
                        data-id="${transacao.id}">✕</button>
                `;
            }

            tr.innerHTML = `
                <td class="transaction-name">
                    <div class="transaction-identificacao">
                        <span class="transaction-description">${escaparHTML(descricaoExibida)}</span>
                        ${identificacao}
                    </div>
                </td>
                <td class="transaction-category">${escaparHTML(transacao.categoria || "Outros")}</td>
                <td class="transaction-date">${formatarData(transacao.data)}</td>
                <td><span class="type-badge type-${transacao.tipo}">
                    ${ehPrevista ? "Despesa prevista" : tipoTexto}
                </span></td>
                <td class="value-${transacao.tipo} valor-movimento">
                    ${sinal}&nbsp;${formatarMoeda(transacao.valor)}
                </td>
                <td>${acao}</td>
            `;

            if (!ehPrevista && !ehParcelaCartao) {
                tr.querySelector(".delete-btn")?.addEventListener(
                    "click",
                    () => excluirTransacao(transacao.id)
                );
            }

            tabela.appendChild(tr);
        });
    } catch (erro) {
        console.error("Erro ao listar movimentações:", erro);

        tabela.innerHTML = `
            <tr><td colspan="6" class="empty">
                Erro ao carregar movimentações.
            </td></tr>
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
    const tipo = document.getElementById("tipo").value;

    const formaPagamento =
        document.getElementById("formaPagamento")?.value || "pix";

    const valor = Number(document.getElementById("valor").value);

    const dados = {
        descricao: document.getElementById("descricao").value.trim(),
        tipo,
        categoria: document.getElementById("categoria").value,
        valor,
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

    if (tipo === "despesa") {
        dados.forma_pagamento = formaPagamento;

        if (formaPagamento === "credito") {
            const cartaoId =
                document.getElementById("cartaoSelecionado")?.value;

            const parcelas = Number(
                document.getElementById("quantidadeParcelas")?.value
            );

            if (!cartaoId) {
                mensagem.textContent = "Selecione um cartão de crédito.";
                mensagem.className = "form-message error";
                return;
            }

            if (!Number.isInteger(parcelas) || parcelas < 1 || parcelas > 60) {
                mensagem.textContent =
                    "Informe uma quantidade de parcelas entre 1 e 60.";
                mensagem.className = "form-message error";
                return;
            }

            dados.cartao_id = Number(cartaoId);
            dados.parcelas = parcelas;
        }
    }

    botao.disabled = true;
    botao.textContent = "Salvando...";

    try {
        const resposta = await requisicao(`${API_URL}/transacoes`, {
            method: "POST",
            body: JSON.stringify(dados)
        });

        mensagem.textContent =
            resposta.mensagem ||
            resposta.message ||
            "Movimentação cadastrada com sucesso!";

        mensagem.className = "form-message success";

        document.getElementById("formTransacao").reset();
        atualizarCategorias();
        configurarPagamento();

        const agora = new Date();

        document.getElementById("data").value =
            `${agora.getFullYear()}-${String(agora.getMonth() + 1).padStart(2, "0")}-${String(agora.getDate()).padStart(2, "0")}`;

        await carregarCartoes();
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
    if (!confirm("Tem certeza que deseja excluir esta movimentação?")) {
        return;
    }

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
// NAVEGAÇÃO E MENSAGENS
// ======================================

function irParaFormulario() {
    document.getElementById("nova-transacao").scrollIntoView({
        behavior: "smooth"
    });

    document.getElementById("descricao").focus();
}

function mostrarMensagem(texto, tipo) {
    const mensagem = document.getElementById("mensagemFormulario");

    if (!mensagem) return;

    mensagem.textContent = texto;
    mensagem.className = `form-message ${tipo}`;
}

// ======================================
// EXPORTAR EXCEL
// ======================================

async function exportarExcel() {
    try {
        const token = obterToken();

        if (!token) {
            redirecionarLogin();
            return;
        }

        const mes = document.getElementById("mesFiltro")?.value;

        if (!mes) {
            alert("Selecione um mês antes de exportar.");
            return;
        }

        const resposta = await fetch(
            `${API_URL}/planilhas/exportar?mes=${encodeURIComponent(mes)}`,
            {
                headers: {
                    Authorization: `Bearer ${token}`
                }
            }
        );

        if (resposta.status === 401) {
            redirecionarLogin();
            return;
        }

        if (!resposta.ok) {
            const dados = await resposta.json().catch(() => ({}));
            throw new Error(dados.detail || "Erro ao exportar planilha.");
        }

        const blob = await resposta.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download = `movimentacoes_${mes}.xlsx`;

        document.body.appendChild(link);
        link.click();
        link.remove();

        URL.revokeObjectURL(url);
    } catch (erro) {
        alert(erro.message);
        console.error("Erro ao exportar Excel:", erro);
    }
}

// ======================================
// IMPORTAR EXCEL
// ======================================

async function importarExcel(evento) {
    const arquivo = evento.target.files[0];

    if (!arquivo) return;

    if (!arquivo.name.toLowerCase().endsWith(".xlsx")) {
        alert("Selecione um arquivo Excel .xlsx.");
        evento.target.value = "";
        return;
    }

    if (!confirm(
        "Deseja importar as movimentações desta planilha? " +
        "As novas movimentações serão adicionadas às existentes."
    )) {
        evento.target.value = "";
        return;
    }

    const token = obterToken();

    if (!token) {
        redirecionarLogin();
        evento.target.value = "";
        return;
    }

    const formulario = new FormData();
    formulario.append("arquivo", arquivo);

    try {
        const resposta = await fetch(`${API_URL}/planilhas/importar`, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${token}`
            },
            body: formulario
        });

        if (resposta.status === 401) {
            redirecionarLogin();
            return;
        }

        const dados = await resposta.json().catch(() => ({}));

        if (!resposta.ok) {
            throw new Error(dados.detail || "Erro ao importar planilha.");
        }

        alert(
            `${dados.importadas ?? dados.importados ?? 0} movimentações importadas com sucesso!`
        );

        atualizarTela();
    } catch (erro) {
        alert(erro.message);
    } finally {
        evento.target.value = "";
    }
}

// ======================================
// SAIR DA CONTA
// ======================================

function sairDaConta() {
    if (!confirm("Deseja realmente sair da sua conta?")) return;

    limparSessao();
    window.location.replace("/login");
}

// ======================================
// ORÇAMENTOS
// ======================================

function carregarCategoriasOrcamento() {
    const select = document.getElementById("orcamentoCategoria");

    if (!select) return;

    const categoriaAtual = select.value;

    select.innerHTML = `
        <option value="">Selecione uma categoria</option>
        ${categorias.despesa.map(categoria => `
            <option value="${escaparHTML(categoria)}">
                ${escaparHTML(categoria)}
            </option>
        `).join("")}
    `;

    if (categorias.despesa.includes(categoriaAtual)) {
        select.value = categoriaAtual;
    }
}

// ======================================
// SELEÇÃO DE CARTÕES NO ORÇAMENTO
// ======================================

function prepararSelecaoCartoesOrcamento() {
    const categoria = document.getElementById("orcamentoCategoria");

    if (!categoria || document.getElementById("grupoCartoesOrcamento")) {
        return;
    }

    const grupo = document.createElement("div");

    grupo.id = "grupoCartoesOrcamento";
    grupo.style.display = "none";
    grupo.style.marginTop = "12px";

    grupo.innerHTML = `
        <label style="display:block; margin-bottom:8px;">
            Cartões considerados
        </label>
        <div style="position:relative;">
            <button type="button" id="btnCartoesOrcamento"
                class="campo-cartoes" aria-expanded="false"
                style="width:100%;min-height:46px;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;background:#151f30;color:#fff;border:1px solid #334155;border-radius:8px;cursor:pointer;text-align:left;">
                <span id="textoCartoesOrcamento">Todos os cartões</span>
                <span id="iconeCartoesOrcamento">⌄</span>
            </button>
            <div id="listaCartoesOrcamento" hidden
                style="position:absolute;z-index:1000;top:calc(100% + 6px);left:0;width:100%;max-height:240px;overflow-y:auto;padding:5px;background:#151f30;border:1px solid #334155;border-radius:8px;box-shadow:0 12px 30px rgba(0,0,0,.35);">
            </div>
        </div>
    `;

    categoria.insertAdjacentElement("afterend", grupo);

    const botao = document.getElementById("btnCartoesOrcamento");
    const lista = document.getElementById("listaCartoesOrcamento");

    botao.addEventListener("click", () => {
        lista.hidden = !lista.hidden;

        botao.setAttribute("aria-expanded", String(!lista.hidden));

        document.getElementById("iconeCartoesOrcamento").textContent =
            lista.hidden ? "⌄" : "⌃";
    });

    document.addEventListener("click", evento => {
        if (!grupo.contains(evento.target)) {
            lista.hidden = true;
            botao.setAttribute("aria-expanded", "false");

            document.getElementById("iconeCartoesOrcamento").textContent = "⌄";
        }
    });

    categoria.addEventListener(
        "change",
        atualizarVisibilidadeCartoesOrcamento
    );
}

async function carregarCartoesOrcamento() {
    const lista = document.getElementById("listaCartoesOrcamento");

    if (!lista) return;

    try {
        const resposta = await requisicao(`${API_URL}/cartoes`);

        cartoesDisponiveisOrcamento = Array.isArray(resposta)
            ? resposta
            : (resposta.cartoes || []);

        renderizarCartoesOrcamento();
    } catch (erro) {
        console.error("Erro ao carregar cartões para orçamento:", erro);
        lista.innerHTML = "<small>Não foi possível carregar os cartões.</small>";
    }
}

function renderizarCartoesOrcamento(idsSelecionados = null) {
    const lista = document.getElementById("listaCartoesOrcamento");

    if (!lista) return;

    if (!cartoesDisponiveisOrcamento.length) {
        lista.innerHTML = "<small>Nenhum cartão cadastrado.</small>";
        atualizarTextoCartoesOrcamento();
        return;
    }

    const todos = idsSelecionados === null;
    const ids = new Set((idsSelecionados || []).map(Number));

    lista.innerHTML = `
        <label class="opcao-cartao-orcamento opcao-todos-cartoes">
            <span>Todos os cartões</span>
            <input type="checkbox" id="orcamentoTodosCartoes"
                ${todos ? "checked" : ""}>
        </label>
        <div class="divisor-cartoes-orcamento"></div>
        ${cartoesDisponiveisOrcamento.map(cartao => `
            <label class="opcao-cartao-orcamento">
                <span>${escaparHTML(cartao.nome)}</span>
                <input type="checkbox" class="orcamento-cartao-checkbox"
                    value="${Number(cartao.id)}"
                    ${todos || ids.has(Number(cartao.id)) ? "checked" : ""}
                    ${todos ? "disabled" : ""}>
            </label>
        `).join("")}
    `;

    document.getElementById("orcamentoTodosCartoes").addEventListener(
        "change",
        evento => {
            renderizarCartoesOrcamento(
                evento.target.checked ? null : []
            );
        }
    );

    lista.querySelectorAll(".orcamento-cartao-checkbox").forEach(input => {
        input.addEventListener("change", () => {
            const marcados = [
                ...lista.querySelectorAll(
                    ".orcamento-cartao-checkbox:checked"
                )
            ].map(item => Number(item.value));

            renderizarCartoesOrcamento(marcados);
        });
    });

    atualizarTextoCartoesOrcamento();
}

function atualizarTextoCartoesOrcamento() {
    const texto = document.getElementById("textoCartoesOrcamento");

    if (!texto) return;

    const selecionados = [
        ...document.querySelectorAll(
            "#listaCartoesOrcamento .orcamento-cartao-checkbox:checked"
        )
    ];

    if (
        cartoesDisponiveisOrcamento.length === 0 ||
        selecionados.length === cartoesDisponiveisOrcamento.length
    ) {
        texto.textContent = "Todos os cartões";
        return;
    }

    if (!selecionados.length) {
        texto.textContent = "Selecione os cartões";
        return;
    }

    if (selecionados.length === 1) {
        const id = Number(selecionados[0].value);

        const cartao = cartoesDisponiveisOrcamento.find(
            item => Number(item.id) === id
        );

        texto.textContent = cartao?.nome || "1 cartão selecionado";
        return;
    }

    texto.textContent = `${selecionados.length} cartões selecionados`;
}

function obterCartoesSelecionadosOrcamento() {
    const todos = document.getElementById("orcamentoTodosCartoes");

    if (!todos || todos.checked) return null;

    return [
        ...document.querySelectorAll(
            "#listaCartoesOrcamento .orcamento-cartao-checkbox:checked"
        )
    ].map(input => Number(input.value));
}

function atualizarVisibilidadeCartoesOrcamento() {
    const grupo = document.getElementById("grupoCartoesOrcamento");
    const categoria = document.getElementById("orcamentoCategoria");

    if (!grupo || !categoria) return;

    grupo.style.display =
        categoria.value === "Parcelados" ? "block" : "none";
}

// ======================================
// LISTAR ORÇAMENTOS
// ======================================

async function carregarOrcamentos() {
    const lista = document.getElementById("listaOrcamentos");
    const campoMes = document.getElementById("mesFiltro");

    if (!lista || !campoMes?.value) return;

    lista.innerHTML =
        '<p class="empty">Carregando orçamentos...</p>';

    try {
        const mes = campoMes.value;

        const dados = await requisicao(
            `${API_URL}/orcamentos?mes=${encodeURIComponent(mes)}`
        );

        const orcamentos = dados.orcamentos || [];
        const contador = document.getElementById("totalOrcamentos");

        if (contador) {
            contador.textContent =
                `${orcamentos.length} ${orcamentos.length === 1 ? "categoria" : "categorias"}`;
        }

        if (!orcamentos.length) {
            lista.innerHTML = `
                <p class="empty">Nenhum orçamento cadastrado para este mês.</p>
            `;
            return;
        }

        lista.innerHTML = "";

        orcamentos.forEach(orcamento => {
            const percentual = Math.max(
                0,
                Number(orcamento.percentual || 0)
            );

            const percentualVisual = Math.min(percentual, 100);
            const ultrapassou = Boolean(orcamento.ultrapassou);
            const restante = Number(orcamento.restante || 0);
            const fixado = Boolean(orcamento.fixado);

            const card = document.createElement("div");
            card.className = "orcamento-card";

            card.innerHTML = `
                <div class="orcamento-topo">
                    <div>
                        <strong>${escaparHTML(orcamento.categoria)}</strong>

                        <span class="orcamento-status ${ultrapassou ? "ultrapassou" : "dentro-limite"}">
                            ${ultrapassou ? "Limite ultrapassado" : "Dentro do limite"}
                        </span>

                        ${fixado ? `
                            <span class="orcamento-status dentro-limite">
                                📌 Fixo mensal
                            </span>
                        ` : ""}
                    </div>

                    ${!MODO_VISITANTE ? `
                        <div class="orcamento-acoes">
                            <button type="button"
                                class="btn-fixar-orcamento"
                                title="${fixado ? "Desafixar orçamento" : "Fixar orçamento"}">
                                ${fixado ? "📌 Desafixar" : "📌 Fixar"}
                            </button>

                            <button type="button"
                                class="btn-editar-orcamento"
                                title="Editar orçamento">
                                Editar
                            </button>

                            <button type="button"
                                class="btn-excluir-orcamento"
                                title="Excluir orçamento">
                                ✕
                            </button>
                        </div>
                    ` : ""}
                </div>

                <div class="orcamento-valores">
                    <div>
                        <span>Gasto</span>
                        <strong>${formatarMoeda(orcamento.gasto)}</strong>
                    </div>

                    <div>
                        <span>Limite</span>
                        <strong>${formatarMoeda(orcamento.limite)}</strong>
                    </div>

                    <div>
                        <span>${ultrapassou ? "Excedido" : "Restante"}</span>
                        <strong class="${ultrapassou ? "red-text" : "green-text"}">
                            ${formatarMoeda(Math.abs(restante))}
                        </strong>
                    </div>
                </div>

                <div class="orcamento-barra">
                    <div class="orcamento-progresso ${ultrapassou ? "barra-estourada" : ""}"
                        style="width:${percentualVisual}%"></div>
                </div>

                <div class="orcamento-rodape">
                    <span>${percentual.toFixed(1)}% utilizado</span>
                </div>
            `;

            if (!MODO_VISITANTE) {
                card.querySelector(".btn-fixar-orcamento")?.addEventListener(
                    "click",
                    () => alternarOrcamentoFixo(orcamento.id)
                );

                card.querySelector(".btn-editar-orcamento")?.addEventListener(
                    "click",
                    () => editarOrcamento(orcamento)
                );

                card.querySelector(".btn-excluir-orcamento")?.addEventListener(
                    "click",
                    () => excluirOrcamento(orcamento.id)
                );
            }

            lista.appendChild(card);
        });
    } catch (erro) {
        console.error("Erro ao carregar orçamentos:", erro);

        lista.innerHTML = `
            <p class="empty">Não foi possível carregar os orçamentos.</p>
        `;
    }
}

// ======================================
// SALVAR ORÇAMENTO
// ======================================

async function salvarOrcamento(evento) {
    evento.preventDefault();

    if (MODO_VISITANTE) return;

    const formulario = document.getElementById("formOrcamento");
    const categoria = document.getElementById("orcamentoCategoria");
    const valor = document.getElementById("orcamentoValor");
    const mesFiltro = document.getElementById("mesFiltro");
    const botao = document.getElementById("btnSalvarOrcamento");
    const mensagem = document.getElementById("mensagemOrcamento");

    if (!categoria || !valor || !mesFiltro || !botao || !mensagem) {
        console.error("Elementos do formulário de orçamento não encontrados.");
        return;
    }

    const [ano, mes] = mesFiltro.value.split("-").map(Number);
    const valorLimite = Number(valor.value);

    if (
        !categoria.value ||
        !ano ||
        !mes ||
        !Number.isFinite(valorLimite) ||
        valorLimite <= 0
    ) {
        mensagem.textContent = "Preencha os campos corretamente.";
        mensagem.className = "form-message error";
        return;
    }

    const dados = {
        categoria: categoria.value,
        ano,
        mes,
        valor_limite: valorLimite,
        cartoes_ids: categoria.value === "Parcelados"
            ? obterCartoesSelecionadosOrcamento()
            : null
    };

    botao.disabled = true;
    botao.textContent = "Salvando...";

    try {
        const resposta = await requisicao(`${API_URL}/orcamentos`, {
            method: "POST",
            body: JSON.stringify(dados)
        });

        mensagem.textContent =
            resposta.mensagem || "Orçamento salvo com sucesso!";

        mensagem.className = "form-message success";

        formulario.reset();
        orcamentoEmEdicao = false;

        categoria.disabled = false;
        botao.textContent = "Salvar orçamento";

        carregarCategoriasOrcamento();
        renderizarCartoesOrcamento();
        atualizarVisibilidadeCartoesOrcamento();

        await carregarOrcamentos();

    } catch (erro) {
        mensagem.textContent = erro.message;
        mensagem.className = "form-message error";
    } finally {
        botao.disabled = false;
        botao.textContent = orcamentoEmEdicao
            ? "Atualizar orçamento"
            : "Salvar orçamento";
    }
}

// ======================================
// EDITAR ORÇAMENTO
// ======================================

function editarOrcamento(orcamento) {
    if (MODO_VISITANTE) return;

    const categoria = document.getElementById("orcamentoCategoria");
    const valor = document.getElementById("orcamentoValor");
    const botao = document.getElementById("btnSalvarOrcamento");
    const mensagem = document.getElementById("mensagemOrcamento");
    const conteudo = document.getElementById("conteudoOrcamentos");

    if (!categoria || !valor || !botao) return;

    orcamentoEmEdicao = true;

    categoria.value = orcamento.categoria;
    categoria.disabled = true;

    valor.value = Number(orcamento.limite).toFixed(2);

    botao.textContent = "Atualizar orçamento";

    if (mensagem) {
        mensagem.textContent =
            "Edite o limite e clique em Atualizar orçamento.";
        mensagem.className = "form-message";
    }

    if (conteudo) {
        conteudo.hidden = false;
    }

    atualizarVisibilidadeCartoesOrcamento();

    if (orcamento.categoria === "Parcelados") {
        renderizarCartoesOrcamento(orcamento.cartoes_ids);
    }

    document.getElementById("formOrcamento")?.scrollIntoView({
        behavior: "smooth",
        block: "center"
    });

    valor.focus();
}

// ======================================
// EXCLUIR ORÇAMENTO
// ======================================

async function excluirOrcamento(id) {
    if (MODO_VISITANTE) return;

    if (!confirm("Deseja realmente excluir este orçamento?")) {
        return;
    }

    try {
        const resposta = await requisicao(
            `${API_URL}/orcamentos/${id}`,
            {
                method: "DELETE"
            }
        );

        alert(resposta.mensagem || "Orçamento excluído com sucesso!");

        await carregarOrcamentos();
    } catch (erro) {
        alert(erro.message);
        console.error("Erro ao excluir orçamento:", erro);
    }
}

// ======================================
// FIXAR / DESAFIXAR ORÇAMENTO
// ======================================

async function alternarOrcamentoFixo(id) {
    if (MODO_VISITANTE) return;

    try {
        const resposta = await requisicao(
            `${API_URL}/orcamentos/${id}/fixar`,
            {
                method: "POST"
            }
        );

        alert(resposta.mensagem || "Orçamento atualizado!");

        await carregarOrcamentos();
    } catch (erro) {
        alert(erro.message);
        console.error("Erro ao alterar orçamento fixo:", erro);
    }
}

// ======================================
// BLOQUEAR EDIÇÃO DO VISITANTE
// ======================================

function bloquearEdicaoVisitante() {
    if (!MODO_VISITANTE) return;

    document.getElementById("formTransacao")?.setAttribute("hidden", "");
    document.getElementById("formOrcamento")?.setAttribute("hidden", "");

    [
        "arquivoExcel",
        "btnExportar",
        "btnImportar"
    ].forEach(id => {
        const elemento = document.getElementById(id);

        if (elemento) {
            elemento.hidden = true;
        }

        document.querySelectorAll(`label[for="${id}"]`).forEach(label => {
            label.hidden = true;
        });
    });

    [
        "btnSalvar",
        "btnSalvarOrcamento"
    ].forEach(id => {
        const elemento = document.getElementById(id);

        if (elemento) {
            elemento.hidden = true;
        }
    });
}
