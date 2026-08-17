import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// Ponto de entrada padrão de um app React com Vite: encontra a <div
// id="raiz"> declarada em index.html e monta o componente <App> dentro
// dela. React.StrictMode não muda nada em produção -- em desenvolvimento,
// ajuda a pegar cedo efeitos colaterais escritos de forma não segura para
// re-renderizações repetidas (algo que vai importar bastante mais adiante,
// quando o estado do quadro passar a ser atualizado em tempo real, na
// Etapa 6).
ReactDOM.createRoot(document.getElementById("raiz")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Registra o service worker (Etapa 5.7/7.3) -- fora do React de propósito,
// não é estado de tela, é infraestrutura do navegador que só precisa
// acontecer uma vez. `"serviceWorker" in navigator` protege navegadores
// antigos que não suportam a API (o app funciona normalmente sem push
// neles, só não recebe notificação com a aba fechada).
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch((erro) => {
      console.error("Não foi possível registrar o service worker:", erro);
    });
  });
}
