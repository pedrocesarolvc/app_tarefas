"""
Salas de WebSocket por quadro (Etapa 6.5) — "quem recebe o quê".

O servidor mantém, em memória, quais conexões estão olhando qual quadro.
Quando um cartão ou lista de um quadro muda, o evento vai só para quem
está conectado àquele quadro — nenhum outro cliente recebe.

A limitação honesta, direto da documentação (Etapa 6.5): este dicionário
vive na memória de UM processo. Com dois processos de API, um não
enxergaria as conexões do outro, e eventos se perderiam — a solução de
produção seria Redis pub/sub entre eles. Para um app de uma usuária, um
processo basta, e é por isso que o worker (que É um segundo processo,
Etapa 5.2) precisa de uma ponte HTTP para chegar até aqui — ver
app/rotas/realtime.py e o comentário lá sobre o endpoint interno.
"""

from uuid import uuid4

import anyio
from fastapi import WebSocket


class GerenciadorDeSalas:
    """Uma sala por `quadro_id`; cada sala é um dicionário de
    `id_conexao -> WebSocket`. `id_conexao` (não o objeto WebSocket em si)
    é o que o cliente recebe de volta ao conectar (ver a rota WebSocket) e
    é a peça que permite a supressão de eco da Etapa 6.7: o cliente manda
    esse id de volta nas escritas HTTP, e o evento transmitido carrega
    esse mesmo id em `origem` — o cliente que originou a mudança consegue
    reconhecer e ignorar o próprio eco.
    """

    def __init__(self) -> None:
        self._salas: dict[int, dict[str, WebSocket]] = {}

    async def conectar(self, quadro_id: int, websocket: WebSocket) -> str:
        """Aceita a conexão e a registra na sala do quadro. Devolve o id
        de conexão gerado -- quem chama (a rota WebSocket) é responsável
        por mandar esse id de volta ao cliente."""
        await websocket.accept()
        id_conexao = uuid4().hex
        self._salas.setdefault(quadro_id, {})[id_conexao] = websocket
        return id_conexao

    def desconectar(self, quadro_id: int, id_conexao: str) -> None:
        """Remove a conexão da sala. Se a sala ficar vazia, o próprio
        dicionário da sala é removido -- sem isso, salas de quadros que
        ninguém mais olha ficariam ocupando memória para sempre (Etapa
        6.10: "desconectar remove a conexão da sala, sem vazamento de
        memória")."""
        sala = self._salas.get(quadro_id)
        if sala is None:
            return
        sala.pop(id_conexao, None)
        if not sala:
            del self._salas[quadro_id]

    def quantidade_de_conexoes(self, quadro_id: int) -> int:
        """Usado pelos testes para provar que desconectar não vaza
        memória -- não tem uso em produção."""
        return len(self._salas.get(quadro_id, {}))

    async def transmitir(self, quadro_id: int, evento: dict) -> None:
        """Envia `evento` para todas as conexões da sala do quadro. Uma
        conexão que falhar ao receber (já morta, mas ainda não chegou a
        vez de o próprio loop dela detectar a desconexão) é ignorada
        aqui -- ela se limpa sozinha quando `receive_text()` levantar
        `WebSocketDisconnect` na rota (ver app/rotas/realtime.py)."""
        sala = self._salas.get(quadro_id, {})
        for websocket in list(sala.values()):
            try:
                await websocket.send_json(evento)
            except Exception:
                pass

    def transmitir_sync(self, quadro_id: int, evento: dict) -> None:
        """A porta de entrada para código SÍNCRONO (as rotas HTTP deste
        projeto são `def`, não `async def` -- ver app/rotas/cartoes.py e
        listas.py). FastAPI roda rotas síncronas numa thread própria (via
        `anyio.to_thread`); `anyio.from_thread.run` é o jeito correto de,
        a partir dessa thread, voltar ao loop de eventos principal e
        `await`ar `transmitir` -- só funciona porque a rota que chama isto
        já está rodando dentro de uma thread gerenciada pelo anyio (é
        assim que o próprio FastAPI a colocou lá)."""
        anyio.from_thread.run(self.transmitir, quadro_id, evento)

    def zerar(self) -> None:
        """Limpa todas as salas. Não é usado em produção -- existe só
        para os testes começarem cada caso com o gerenciador vazio (ver
        tests/conftest.py), já que esta é uma instância única e
        compartilhada durante toda a vida do processo."""
        self._salas.clear()


# Instância única do processo (Etapa 6.5: as salas vivem na memória de UM
# processo). Importada por app/rotas/realtime.py (para conectar/
# desconectar/expor o endpoint interno) e por app/rotas/cartoes.py e
# listas.py (para transmitir depois de cada escrita).
gerenciador_de_salas = GerenciadorDeSalas()
