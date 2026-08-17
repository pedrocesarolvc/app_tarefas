import { useState } from "react";

export interface Aviso {
  id: string;
  titulo: string;
  mensagem: string;
}

/**
 * A "lista de avisos" da Etapa 7.4: a notificação in-app chegando pelo
 * canal em tempo real (Etapa 6), sem precisar do Web Push nem do app
 * fechado. Um sino no cabeçalho com contagem, que abre um painel com o
 * histórico da sessão -- não é persistido (recarregar a página limpa a
 * lista; os avisos que já chegaram por push continuam na central de
 * notificações do sistema operacional, essa parte não depende do app).
 */
export default function PainelDeAvisos({ avisos }: { avisos: Aviso[] }) {
  const [aberto, setAberto] = useState(false);

  return (
    <div className="painel-avisos">
      <button
        type="button"
        className="botao-fantasma botao-sino"
        onClick={() => setAberto((valor) => !valor)}
        aria-label="Avisos"
      >
        🔔
        {avisos.length > 0 && <span className="painel-avisos__contagem">{avisos.length}</span>}
      </button>

      {aberto && (
        <div className="painel-avisos__lista">
          {avisos.length === 0 ? (
            <p className="painel-avisos__vazio">Nenhum aviso ainda.</p>
          ) : (
            avisos.map((aviso) => (
              <div key={aviso.id} className="painel-avisos__item">
                <strong>{aviso.titulo}</strong>
                <span>{aviso.mensagem}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
