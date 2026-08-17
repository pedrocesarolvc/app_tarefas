"""
O formato dos eventos transmitidos pelo canal em tempo real (Etapa 6.5).

Um só lugar decide esse formato, pelo mesmo motivo de app/servicos/
ordenacao.py e prazos.py: cada rota que escreve (app/rotas/cartoes.py,
listas.py) só chama `construir_evento`, sem reinventar o formato cada vez.
"""

from typing import Any


def construir_evento(tipo: str, dados: dict[str, Any], origem: str | None) -> dict[str, Any]:
    """Monta o payload transmitido pela sala do quadro.

    `tipo` identifica o que aconteceu (ex.: "cartao_movido",
    "lista_arquivada") -- o cliente usa isso para decidir como atualizar a
    tela, sem precisar adivinhar a partir do formato de `dados`.

    `origem` é o id de conexão de quem originou a mudança (Etapa 6.7: a
    defesa contra eco). `None` quando a mudança não veio de nenhuma
    conexão WebSocket conhecida -- por exemplo, o worker (Etapa 5)
    notificando um cartão não tem um `id_conexao` de cliente nenhum
    associado.
    """
    return {"tipo": tipo, "dados": dados, "origem": origem}
