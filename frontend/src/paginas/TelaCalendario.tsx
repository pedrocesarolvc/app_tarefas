import { useEffect, useState } from "react";
import { calendario } from "../api/cliente";
import type { Cartao } from "../api/tipos";
import "../estilos/calendario.css";

const DIAS_PADRAO_A_FRENTE = 30;

function formatarCabecalhoDoDia(data: Date): string {
  return data.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" });
}

function formatarHora(iso: string): string {
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function chaveDoDia(iso: string): string {
  return iso.slice(0, 10); // "AAAA-MM-DD" -- suficiente para agrupar, sem precisar de fuso na chave
}

/**
 * O calendário (Etapa 4.5 / 7.4): a mesma "lente" descrita na
 * documentação -- os cartões do quadro, olhados por data em vez de por
 * lista, atravessando todos os quadros do usuário (não só o que está
 * aberto agora). Uma lista por dia (agenda), não uma grade de mês: para
 * o volume de cartões de uma usuária só, uma grade mensal seria mais
 * estrutura visual do que dado para mostrar -- a lista já responde "o
 * que eu tenho essa semana" sem exigir rolar por semanas vazias.
 *
 * O cuidado da Etapa 4.6 é o que mais importa aqui: quando não houver
 * nenhum cartão com prazo no período, a tela precisa dizer isso
 * explicitamente -- "nenhum cartão com data neste período" -- em vez de
 * mostrar uma lista em branco que parece quebrada. A maioria dos cartões
 * não tem prazo (Etapa 1.4/4.6); um calendário vazio é o estado normal,
 * não um bug.
 */
export default function TelaCalendario() {
  const [cartoes, setCartoes] = useState<Cartao[] | null>(null);
  const [erro, setErro] = useState(false);

  useEffect(() => {
    const de = new Date();
    de.setHours(0, 0, 0, 0);
    const ate = new Date(de);
    ate.setDate(ate.getDate() + DIAS_PADRAO_A_FRENTE);

    calendario
      .listar(de.toISOString(), ate.toISOString())
      .then(setCartoes)
      .catch(() => setErro(true));
  }, []);

  if (erro) {
    return <div className="pagina-calendario__estado">Não foi possível carregar o calendário.</div>;
  }

  if (cartoes === null) {
    return <div className="pagina-calendario__estado">Carregando...</div>;
  }

  if (cartoes.length === 0) {
    return (
      <div className="pagina-calendario__estado">
        Nenhum cartão com data nos próximos {DIAS_PADRAO_A_FRENTE} dias.
      </div>
    );
  }

  const grupos = new Map<string, Cartao[]>();
  for (const cartao of cartoes) {
    if (!cartao.prazo) continue;
    const chave = chaveDoDia(cartao.prazo);
    if (!grupos.has(chave)) grupos.set(chave, []);
    grupos.get(chave)!.push(cartao);
  }

  const diasEmOrdem = [...grupos.keys()].sort();

  return (
    <div className="pagina-calendario">
      {diasEmOrdem.map((chave) => (
        <section key={chave} className="pagina-calendario__dia">
          <h2 className="pagina-calendario__cabecalho-dia">
            {formatarCabecalhoDoDia(new Date(`${chave}T00:00:00`))}
          </h2>
          <ul className="pagina-calendario__lista">
            {grupos.get(chave)!.map((cartao) => (
              <li key={cartao.id} className="pagina-calendario__item">
                <span className="pagina-calendario__hora">{formatarHora(cartao.prazo!)}</span>
                <span className="pagina-calendario__titulo">{cartao.titulo}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
