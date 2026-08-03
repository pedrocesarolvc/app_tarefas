import { useEffect, useState } from "react";

/**
 * Este componente NÃO é a interface do kanban -- é só uma página de
 * espera que prova que o encanamento (Vite servindo React, e o proxy até
 * o backend FastAPI, ver vite.config.ts) funciona de ponta a ponta.
 *
 * O desenho de verdade da tela (quadro, lista, cartão, arrastar,
 * calendário) fica para quando a documentação chegar nas etapas que
 * decidem isso -- por ora, desenhar essa interface seria inventar decisão
 * de produto que ainda não foi tomada nem validada com a usuária real do
 * projeto (ver Etapa 1.1 da documentação).
 */
export default function App() {
  // Três estados possíveis da checagem: ainda checando, backend
  // respondeu, ou backend não respondeu (por exemplo, se ele não estiver
  // rodando localmente).
  const [statusBackend, setStatusBackend] = useState<"verificando" | "no-ar" | "inacessivel">(
    "verificando"
  );

  useEffect(() => {
    // "/api" é reescrito para o backend pelo proxy do Vite (ver
    // vite.config.ts) -- o código do navegador nunca precisa saber a URL
    // real do backend.
    fetch("/api/saude")
      .then((resposta) => (resposta.ok ? setStatusBackend("no-ar") : setStatusBackend("inacessivel")))
      .catch(() => setStatusBackend("inacessivel"));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem", maxWidth: "40rem" }}>
      <h1>Kanban com tempo</h1>
      <p>
        Estrutura inicial do projeto (Etapas 1 e 2 da documentação: domínio e modelo
        kanban). A interface de verdade -- quadro, listas, cartões, calendário -- ainda
        não foi desenhada.
      </p>
      <p>
        Backend:{" "}
        {statusBackend === "verificando" && "verificando…"}
        {statusBackend === "no-ar" && "no ar ✓"}
        {statusBackend === "inacessivel" && "inacessível (rode a API em backend/, veja o README)"}
      </p>
    </main>
  );
}
