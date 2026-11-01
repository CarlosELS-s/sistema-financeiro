document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("access_token");

    // Se não estiver logado, volta para o login.
    if (!token) {
        window.location.replace("/login");
        return;
    }

    // Recupera os dados do usuário.
    let usuario = {};

    try {
        usuario = JSON.parse(localStorage.getItem("usuario")) || {};
    } catch {
        usuario = {};
    }

    const nome = usuario.nome || "Meu usuário";
    const inicial = nome.charAt(0).toUpperCase();

    // Atualiza o nome em todos os menus.
    document.querySelectorAll(".user-card strong").forEach(elemento => {
        elemento.textContent = nome;
    });

    // Atualiza o avatar.
    document.querySelectorAll(".user-avatar").forEach(elemento => {
        elemento.textContent = inicial;
    });

    // Configura o botão de sair.
    const botaoSair = document.querySelector("#btnSair");

    if (botaoSair) {
        botaoSair.addEventListener("click", () => {
            const confirmar = confirm("Deseja realmente sair da sua conta?");

            if (!confirmar) return;

            localStorage.removeItem("access_token");
            localStorage.removeItem("usuario");

            window.location.replace("/login");
        });
    }
});