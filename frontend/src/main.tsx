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
