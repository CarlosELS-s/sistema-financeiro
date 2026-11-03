
const API_URL = "/api";

// ======================================
// CATEGORIAS
// ======================================

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

// ======================================
// FORMATAÇÃO
// ======================================

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

    const headers = {
        ...opcoes.headers
    };

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

    const dados = await resposta.json().catch(() => ({}));

    if (!resposta.ok) {
        throw new Error(
            dados.detail ||
            dados.mensagem ||
            "Não foi possível realizar a operação."
        );
    }

    return dados;
}

// ======================================
// INICIALIZAÇÃO
// ======================================

document.addEventListener("DOMContentLoaded", () => {

    const token = obterToken();

    if (!token) {
        redirecionarLogin();
        return;
    }

    const usuarioSalvo = localStorage.getItem("usuario");

    if (usuarioSalvo) {
        try {
            const usuario = JSON.parse(usuarioSalvo);

            const nomeElemento = document.querySelector(
                ".user-card strong"
            );

            const avatarElemento = document.querySelector(
                ".user-avatar"
            );

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

    if (mesFiltro) {
        mesFiltro.value = mesAtual;
    }

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
    carregarOrcamentos();

    configurarOrcamentosRecolhiveis();

    mesFiltro?.addEventListener("change", atualizarTela);

    ["filtroTipo", "filtroCategoria", "filtroOrigem"].forEach(id => {
        document.getElementById(id)?.addEventListener(
            "change",
            carregarTransacoes
        );
    });

    document.getElementById("tipo")?.addEventListener(
        "change",
        () => {
            atualizarCategorias();
            atualizarCamposPagamento();
        }
    );

    document.getElementById("formTransacao")?.addEventListener(
        "submit",
        salvarTransacao
    );

    document.getElementById("formOrcamento")?.addEventListener(
        "submit",
        salvarOrcamento
    );

    document.getElementById("arquivoExcel")?.addEventListener(
        "change",
        importarExcel
    );

    document.getElementById("formaPagamento")?.addEventListener(
        "change",
        atualizarCamposPagamento
    );

    document.getElementById("formTransacao")?.addEventListener(
        "reset",
        () => {
            setTimeout(() => {
                atualizarCategorias();
                configurarPagamento();
            }, 0);
        }
    );

    document.getElementById("formOrcamento")?.addEventListener(
        "reset",
        () => {
            setTimeout(() => {
                carregarCategoriasOrcamento();

                const mensagem = document.getElementById("mensagemOrcamento");

                if (mensagem) {
                    mensagem.textContent = "";
                }
            }, 0);
        }
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

    // Começa sempre recolhido.
    conteudo.hidden = true;

    botao.setAttribute("aria-expanded", "false");

    if (texto) {
        texto.textContent = "Expandir";
    }

    if (icone) {
        icone.textContent = "⌄";
    }

    botao.addEventListener("click", () => {
        const expandido =
            botao.getAttribute("aria-expanded") === "true";

        const novoEstado = !expandido;

        conteudo.hidden = !novoEstado;

        botao.setAttribute(
            "aria-expanded",
            String(novoEstado)
        );

        if (texto) {
            texto.textContent = novoEstado ? "Recolher" : "Expandir";
        }

        if (icone) {
            icone.textContent = novoEstado ? "⌃" : "⌄";
        }
    });
}

// ======================================
// PAGAMENTO E CARTÕES
// ======================================

function configurarPagamento() {
    const forma = document.getElementById("formaPagamento");

    if (forma) {
        forma.value = "pix";
    }

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

    const tipo = tipoElemento.value;
    const forma = formaElemento?.value || "pix";

    const ehDespesa = tipo === "despesa";
    const ehCredito = ehDespesa && forma === "credito";

    if (grupoForma) {
        grupoForma.hidden = !ehDespesa;
    }

    if (grupoCartao) {
        grupoCartao.hidden = !ehCredito;
    }

    if (grupoParcelas) {
        grupoParcelas.hidden = !ehCredito;
    }

    if (!ehCredito) {
        if (cartaoElemento) {
            cartaoElemento.value = "";
        }

        if (parcelasElemento) {
            parcelasElemento.value = "1";
        }
    }
}

async function carregarCartoes() {
    const select = document.getElementById("cartaoSelecionado");

    if (!select) return;

    try {
        const cartoes = await requisicao(`${API_URL}/cartoes`);

        select.innerHTML = `
            <option value="">Selecione um cartão</option>
        `;

        cartoes.forEach(cartao => {
            const option = document.createElement("option");

            option.value = cartao.id;

            option.textContent =
                `${cartao.nome} - Disponível: ${formatarMoeda(cartao.disponivel_centavos / 100)}`;

            select.appendChild(option);
        });

        if (cartoes.length === 0) {
            select.innerHTML = `
                <option value="">Nenhum cartão cadastrado</option>
            `;
        }

    } catch (erro) {
        console.error("Erro ao carregar cartões:", erro);

        select.innerHTML = `
            <option value="">Erro ao carregar cartões</option>
        `;
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

    const tipo = tipoElemento.value;

    select.innerHTML = "";

    (categorias[tipo] || categorias.despesa).forEach(categoria => {
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
    const campoMes = document.getElementById("mesFiltro");

    if (!campoMes) return;

    const mes = campoMes.value;

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

        const despesasComPrevisao =
            Number(dados.despesas_mes || 0) + totalContasPendentes;

        const saldoComPrevisao =
            Number(dados.saldo_mes || 0) - totalContasPendentes;

        const saldoTotalElemento =
            document.getElementById("saldoTotal");

        const saldoTotal = Number(dados.saldo_total || 0);

        if (saldoTotalElemento) {
            saldoTotalElemento.textContent =
                formatarMoeda(saldoTotal);

            saldoTotalElemento.classList.toggle(
                "red-text",
                saldoTotal < 0
            );

            saldoTotalElemento.classList.toggle(
                "green-text",
                saldoTotal >= 0
            );
        }

        const saldoMesElemento =
            document.getElementById("saldoMes");

        if (saldoMesElemento) {
            saldoMesElemento.textContent =
                formatarMoeda(saldoComPrevisao);

            saldoMesElemento.classList.toggle(
                "red-text",
                saldoComPrevisao < 0
            );

            saldoMesElemento.classList.toggle(
                "green-text",
                saldoComPrevisao >= 0
            );
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
    const barraReceitas = document.getElementById("barraReceitas");
    const barraDespesas = document.getElementById("barraDespesas");

    if (!barraReceitas || !barraDespesas) return;

    const maior = Math.max(receitas, despesas, 1);

    const porcentagemReceitas = (receitas / maior) * 100;
    const porcentagemDespesas = (despesas / maior) * 100;

    barraReceitas.style.width = `${porcentagemReceitas}%`;
    barraDespesas.style.width = `${porcentagemDespesas}%`;

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

    if (!grafico || !legenda) return;

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
// LISTAR E FILTRAR MOVIMENTAÇÕES
// ======================================

async function carregarTransacoes() {
    const mes = document.getElementById("mesFiltro")?.value;
    const tipo = document.getElementById("filtroTipo")?.value || "";
    const categoria = document.getElementById("filtroCategoria")?.value || "";
    const origem = document.getElementById("filtroOrigem")?.value || "";

    const tabela = document.getElementById("tabelaTransacoes");

    if (!tabela) return;

    tabela.innerHTML = `
        <tr>
            <td colspan="6" class="empty">Carregando...</td>
        </tr>
    `;

    try {
        const parametros = new URLSearchParams();

        if (mes) {
            parametros.append("mes", mes);
        }

        const [transacoes, contasPendentes] = await Promise.all([
            requisicao(
                `${API_URL}/movimentos?${parametros.toString()}`
            ),
            carregarContasFixasDoMes(mes)
        ]);

        let movimentacoes = [
            ...transacoes.map(transacao => ({
                ...transacao,
                prevista: false
            })),
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

        const selectCategoria =
            document.getElementById("filtroCategoria");

        if (selectCategoria) {
            const categoriaAtual = categoria;

            const categoriasDisponiveis = [
                ...new Set(
                    movimentacoes.map(item =>
                        item.categoria || "Outros"
                    )
                )
            ].sort((a, b) => a.localeCompare(b, "pt-BR"));

            selectCategoria.innerHTML = `
                <option value="">Todas as categorias</option>
                ${categoriasDisponiveis.map(nome => `
                    <option value="${escaparHTML(nome)}">
                        ${escaparHTML(nome)}
                    </option>
                `).join("")}
            `;

            if (categoriasDisponiveis.includes(categoriaAtual)) {
                selectCategoria.value = categoriaAtual;
            }
        }

        if (tipo) {
            movimentacoes = movimentacoes.filter(
                item => item.tipo === tipo
            );
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

        movimentacoes.sort((a, b) => {
            return (b.data || "").localeCompare(a.data || "");
        });

        tabela.innerHTML = "";

        if (movimentacoes.length === 0) {
            tabela.innerHTML = `
                <tr>
                    <td colspan="6" class="empty">
                        Nenhuma movimentação encontrada com esses filtros.
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
            const ehParcelaCartao = transacao.origem === "cartao";

            let identificacao = "";

            if (ehPrevista) {
                identificacao = `
                    <span class="movement-tag tag-prevista">
                        Prevista
                    </span>
                `;
            } else if (ehParcelaCartao) {
                identificacao = `
                    <span class="movement-tag tag-cartao">
                        Parcela do cartão
                    </span>
                `;
            }

            let acao = "";

            if (ehPrevista) {
                acao = '<span style="color:#94a3b8;">Conta fixa</span>';
            } else if (ehParcelaCartao) {
                acao = '<span style="color:#94a3b8;">Fatura do cartão</span>';
            } else {
                acao = `
                    <button
                        class="delete-btn"
                        title="Excluir movimentação"
                        aria-label="Excluir movimentação"
                        data-id="${transacao.id}"
                    >
                        ✕
                    </button>
                `;
            }

            tr.innerHTML = `
                <td class="transaction-name">
                    ${escaparHTML(transacao.descricao)}
                    ${identificacao}
                </td>

                <td class="transaction-category">
                    ${escaparHTML(transacao.categoria || "Outros")}
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

            if (
                !Number.isInteger(parcelas) ||
                parcelas < 1 ||
                parcelas > 60
            ) {
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

    if (!mensagem) return;

    mensagem.textContent = texto;
    mensagem.className = `form-message ${tipo}`;
}

// ======================================
// EXPORTAR PLANILHA EXCEL
// ======================================

async function exportarExcel() {
    try {
        const token = obterToken();

        if (!token) {
            redirecionarLogin();
            return;
        }

        const campoMes = document.getElementById("mesFiltro");
        const mes = campoMes?.value;

        if (!mes) {
            alert("Selecione um mês antes de exportar.");
            return;
        }

        const resposta = await fetch(
            `${API_URL}/planilhas/exportar?mes=${encodeURIComponent(mes)}`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        if (resposta.status === 401) {
            redirecionarLogin();
            return;
        }

        if (!resposta.ok) {
            const dados = await resposta.json().catch(() => ({}));

            throw new Error(
                dados.detail || "Erro ao exportar planilha."
            );
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

    const token = obterToken();

    if (!token) {
        redirecionarLogin();
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
                headers: {
                    "Authorization": `Bearer ${token}`
                },
                body: formulario
            }
        );

        if (resposta.status === 401) {
            redirecionarLogin();
            return;
        }

        const dados = await resposta.json().catch(() => ({}));

        if (!resposta.ok) {
            throw new Error(
                dados.detail || "Erro ao importar planilha."
            );
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
    const confirmar = confirm(
        "Deseja realmente sair da sua conta?"
    );

    if (!confirmar) return;

    limparSessao();

    window.location.replace("/login");
}

// ======================================
// ORÇAMENTOS MENSAIS POR CATEGORIA
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

async function carregarOrcamentos() {
    const lista = document.getElementById("listaOrcamentos");
    const campoMes = document.getElementById("mesFiltro");

    if (!lista || !campoMes?.value) return;

    lista.innerHTML = '<p class="empty">Carregando orçamentos...</p>';

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

        if (orcamentos.length === 0) {
            lista.innerHTML = `
                <p class="empty">
                    Nenhum orçamento cadastrado para este mês.
                </p>
            `;
            return;
        }

        lista.innerHTML = "";

        orcamentos.forEach(orcamento => {
            const percentual = Math.max(
                0,
                Number(orcamento.percentual || 0)
            );

            const ultrapassou = Boolean(orcamento.ultrapassou);
            const percentualVisual = Math.min(percentual, 100);
            const restante = Number(orcamento.restante || 0);

            const card = document.createElement("div");

            card.className = "orcamento-card";

            card.innerHTML = `
                <div class="orcamento-topo">
                    <div>
                        <strong>${escaparHTML(orcamento.categoria)}</strong>

                        <span class="orcamento-status ${ultrapassou ? "ultrapassou" : "dentro-limite"}">
                            ${ultrapassou ? "Limite ultrapassado" : "Dentro do limite"}
                        </span>
                    </div>

                    <div class="orcamento-acoes">
                        <button
                            type="button"
                            class="btn-editar-orcamento"
                            title="Editar orçamento"
                        >
                            Editar
                        </button>

                        <button
                            type="button"
                            class="btn-excluir-orcamento"
                            title="Excluir orçamento"
                        >
                            ✕
                        </button>
                    </div>
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
                    <div
                        class="orcamento-progresso ${ultrapassou ? "barra-estourada" : ""}"
                        style="width: ${percentualVisual}%"
                    ></div>
                </div>

                <div class="orcamento-rodape">
                    <span>${percentual.toFixed(1)}% utilizado</span>
                </div>
            `;

            card.querySelector(".btn-editar-orcamento").addEventListener(
                "click",
                () => editarOrcamento(orcamento)
            );

            card.querySelector(".btn-excluir-orcamento").addEventListener(
                "click",
                () => excluirOrcamento(orcamento.id)
            );

            lista.appendChild(card);
        });

    } catch (erro) {
        console.error("Erro ao carregar orçamentos:", erro);

        lista.innerHTML = `
            <p class="empty">
                Não foi possível carregar os orçamentos.
            </p>
        `;
    }
}

async function salvarOrcamento(evento) {
    evento.preventDefault();

    const botao = document.getElementById("btnSalvarOrcamento");
    const mensagem = document.getElementById("mensagemOrcamento");

    const categoria = document.getElementById("orcamentoCategoria").value;
    const valor = Number(document.getElementById("orcamentoValor").value);
    const mes = document.getElementById("mesFiltro").value;

    if (!categoria || !mes || !Number.isFinite(valor) || valor <= 0) {
        mensagem.textContent = "Preencha a categoria e um limite válido.";
        mensagem.className = "form-message error";
        return;
    }

    const [ano, numeroMes] = mes.split("-").map(Number);

    botao.disabled = true;
    botao.textContent = "Salvando...";

    try {
        await requisicao(`${API_URL}/orcamentos`, {
            method: "POST",
            body: JSON.stringify({
                categoria,
                ano,
                mes: numeroMes,
                valor_limite: valor
            })
        });

        mensagem.textContent = "Orçamento salvo com sucesso!";
        mensagem.className = "form-message success";

        document.getElementById("formOrcamento").reset();

        await carregarOrcamentos();

    } catch (erro) {
        mensagem.textContent = erro.message;
        mensagem.className = "form-message error";

    } finally {
        botao.disabled = false;
        botao.textContent = "Salvar orçamento";
    }
}

function editarOrcamento(orcamento) {
    const select = document.getElementById("orcamentoCategoria");
    const valor = document.getElementById("orcamentoValor");

    select.value = orcamento.categoria;
    valor.value = Number(orcamento.limite).toFixed(2);

    const conteudo = document.getElementById("conteudoOrcamentos");
    const botao = document.getElementById("btnExpandirOrcamentos");

    if (conteudo?.hidden) {
        botao?.click();
    }

    document.getElementById("orcamentos").scrollIntoView({
        behavior: "smooth"
    });

    valor.focus();

    const mensagem = document.getElementById("mensagemOrcamento");

    mensagem.textContent =
        "Altere o limite e clique em Salvar orçamento.";

    mensagem.className = "form-message";
}

async function excluirOrcamento(id) {
    const confirmar = confirm(
        "Deseja realmente excluir este orçamento?"
    );

    if (!confirmar) return;

    try {
        await requisicao(`${API_URL}/orcamentos/${id}`, {
            method: "DELETE"
        });

        await carregarOrcamentos();

    } catch (erro) {
        alert(erro.message);
    }
}
