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

/** Mesmo raciocínio de `URL_BASE_DA_API` em api/cliente.ts: sem
 * `VITE_API_URL` (desenvolvimento), conecta na própria origem da página,
 * que o proxy `/ws` do Vite encaminha para o backend local (ver
 * vite.config.ts). Com `VITE_API_URL` definida (produção, API numa
 * origem separada -- ver docs/implantacao.md), conecta direto nela,
 * trocando o protocolo HTTP pelo WebSocket equivalente (http→ws,
 * https→wss). */
function montarUrlDoCanal(quadroId: number): string {
  const urlDaApi = import.meta.env.VITE_API_URL;
  if (urlDaApi) {
    const url = new URL(urlDaApi);
    const protocolo = url.protocol === "https:" ? "wss:" : "ws:";
    return `${protocolo}//${url.host}/ws/quadros/${quadroId}`;
  }
  const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocolo}//${window.location.host}/ws/quadros/${quadroId}`;
}

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
    // TypeScript não propaga o `=== null` acima para dentro de `conectar`
    // (uma closure não tem como o compilador garantir que `quadroId`, um
    // parâmetro capturado, não mudou até lá) -- uma const local resolve.
    const idDoQuadro = quadroId;

    let socket: WebSocket | null = null;
    let idDoTimeout: ReturnType<typeof setTimeout> | null = null;
    let tentativas = 0;
    let desmontado = false;

    function conectar() {
      socket = new WebSocket(montarUrlDoCanal(idDoQuadro));

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
