"""
A ponte HTTP entre o worker e o canal em tempo real da API (Etapa 5.8 e
6.5): "o worker da Etapa 5 também emite nesse canal -- é assim que o
aviso in-app chega sem recarregar".

Por que HTTP, e não o dicionário de salas direto: as salas de WebSocket
vivem na memória do processo da API (Etapa 6.5); o worker é, por desenho,
um processo à parte (Etapa 5.2) -- os dois nunca compartilham memória.
Publicar via HTTP para a própria API é a ponte mais simples entre eles
sem introduzir Redis (que a Etapa 5.2 já descartou para o v1 por adicionar
infraestrutura sem ensinar o conceito). Ver `configuracoes.chave_interna`
(app/config.py) sobre a autenticação simples dessa chamada.
"""

import httpx

from app.config import configuracoes
from app.realtime.eventos import construir_evento


def publicar_evento_de_notificacao(quadro_id: int, dados_cartao: dict) -> None:
    """Avisa a sala do quadro que um cartão acabou de ser notificado.

    Deliberadamente "best-effort": se a API estiver fora do ar, com a
    chave interna divergente, ou qualquer outro erro de rede, a exceção é
    engolida em silêncio, e o worker segue para o próximo cartão. A
    notificação de verdade (Web Push, Etapa 5) já foi entregue por outro
    caminho antes desta função ser chamada -- o aviso in-app é um bônus,
    e travar o worker (ou pior, deixar de marcar `notificado` por causa
    disso) para garantir esse bônus inverteria a prioridade."""
    evento = construir_evento("cartao_notificado", dados_cartao, origem=None)
    try:
        httpx.post(
            f"{configuracoes.url_api_interna}/interno/eventos-tempo-real",
            json={"quadro_id": quadro_id, "evento": evento},
            headers={"X-Chave-Interna": configuracoes.chave_interna},
            timeout=5.0,
        )
    except Exception:
        pass
