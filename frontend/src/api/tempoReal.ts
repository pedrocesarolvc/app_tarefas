import { useEffect, useRef, useState } from "react";

/** O formato exato que app/realtime/eventos.py monta no backend --
 * mantido em espelho, como tipos.ts faz com os schemas Pydantic. */
export interface EventoTempoReal {
  tipo: string;
  dados: Record<string, unknown>;
  origem: string | null;
}

// Etapa 6.8: "a reconexão automática precisa de espera crescente entre
// tentativas — senão um servidor caído recebe uma enxurrada de clientes
// tentando mil vezes por segundo". Dobra a cada tentativa, começando em
// 1s, sem passar de 30s.
const ATRASO_INICIAL_MS = 1000;
const ATRASO_MAXIMO_MS = 30_000;

/**
 * Conecta ao canal em tempo real de um quadro (Etapa 6.4: `GET
 * /ws/quadros/{id}`) e devolve o id de conexão que o servidor atribui ao
 * conectar -- é esse id que precisa viajar no cabeçalho
 * `X-Origem-Conexao` de toda escrita HTTP (ver api/cliente.ts), para que
 * o evento que ela mesma gerou volte com `origem` igual a este id e
 * possa ser reconhecido como eco (Etapa 6.7), em vez de aplicado de novo.
 *
 * Reconecta sozinho com espera crescente ao cair (Etapa 6.8), e chama
 * `aoReconectar` sempre que uma reconexão (não a primeira conexão) tiver
 * sucesso -- a política do v1 para "o que fazer com o que mudou enquanto
 * eu estava fora do ar" é simples de propósito: recarregar o quadro
 * inteiro, em vez de reconciliar evento por evento (a documentação já
 * descarta o versionamento por ser complexidade desproporcional a "um
 * quadro tem alguns KB").
 */
export function useCanalDoQuadro(
  quadroId: number | null,
  aoReceberEvento: (evento: EventoTempoReal) => void,
  aoReconectar: () => void
): string | null {
  const [idConexao, setIdConexao] = useState<string | null>(null);

  // Refs para os callbacks: guardam sempre a versão mais recente sem
  // forçar o efeito abaixo a fechar e reabrir a conexão toda vez que o
  // componente pai re-renderiza (o que aconteceria se `aoReceberEvento`/
  // `aoReconectar` estivessem nas dependências do efeito, já que são
  // funções novas a cada render).
  const aoReceberEventoRef = useRef(aoReceberEvento);
  const aoReconectarRef = useRef(aoReconectar);
  aoReceberEventoRef.current = aoReceberEvento;
  aoReconectarRef.current = aoReconectar;

  useEffect(() => {
    if (quadroId === null) return;

    let socket: WebSocket | null = null;
    let idDoTimeout: ReturnType<typeof setTimeout> | null = null;
    let tentativas = 0;
    let desmontado = false;

    function conectar() {
      const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(`${protocolo}//${window.location.host}/ws/quadros/${quadroId}`);

      socket.onopen = () => {
        if (tentativas > 0) aoReconectarRef.current();
        tentativas = 0;
      };

      socket.onmessage = (mensagem) => {
        const dados = JSON.parse(mensagem.data);
        if (dados.tipo === "conectado") {
          setIdConexao(dados.id_conexao);
          return;
        }
        aoReceberEventoRef.current(dados as EventoTempoReal);
      };

      socket.onclose = () => {
        if (desmontado) return;
        setIdConexao(null);
        const atraso = Math.min(ATRASO_INICIAL_MS * 2 ** tentativas, ATRASO_MAXIMO_MS);
        tentativas += 1;
        idDoTimeout = setTimeout(conectar, atraso);
      };
    }

    conectar();

    return () => {
      desmontado = true;
      if (idDoTimeout) clearTimeout(idDoTimeout);
      socket?.close();
      setIdConexao(null);
    };
  }, [quadroId]);

  return idConexao;
}
