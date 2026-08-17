import { useEffect, useState } from "react";
import { auth } from "./api/cliente";
import type { Usuario } from "./api/tipos";
import QuadroKanban from "./paginas/QuadroKanban";
import TelaLogin from "./paginas/TelaLogin";

/**
 * O quadro kanban de verdade (Etapas 2, 3 e 4: listas, cartões,
 * arrastar-e-soltar, prazo). Este componente só decide UMA coisa: existe
 * uma sessão válida (cookie de login, Etapa 1.4) ou não -- e mostra a
 * tela de login ou o quadro de acordo.
 *
 * O que ainda não existe aqui, de propósito: o cliente WebSocket da
 * Etapa 6 (sincronização entre abas/dispositivos, supressão de eco,
 * reconexão) e o service worker que recebe push da Etapa 5 -- ver
 * docs/documentacao.md, seção 6.13, sobre o que da Etapa 6 ainda é só
 * backend.
 */
export default function App() {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [verificandoSessao, setVerificandoSessao] = useState(true);

  useEffect(() => {
    auth
      .eu()
      .then(setUsuario)
      .catch(() => setUsuario(null))
      .finally(() => setVerificandoSessao(false));
  }, []);

  if (verificandoSessao) return null;

  if (!usuario) {
    return <TelaLogin aoEntrar={setUsuario} />;
  }

  return <QuadroKanban onSair={() => setUsuario(null)} />;
}
