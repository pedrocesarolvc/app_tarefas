"""
Rotas do canal em tempo real (Etapa 6): a conexão WebSocket que os
clientes abrem por quadro, e o endpoint interno que só o worker chama.

A escrita continua sendo HTTP normal (Etapa 6.4) -- nada aqui recebe
comandos do cliente para mudar o quadro. As únicas duas coisas que
acontecem por aqui são: entrar numa sala e ficar recebendo eventos, e (do
lado do worker) publicar um evento nela.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencias import obter_usuario_da_conexao
from app.config import configuracoes
from app.database import obter_sessao
from app.realtime.gerenciador import gerenciador_de_salas
from app.rotas.quadros import obter_quadro_do_usuario

roteador = APIRouter(tags=["tempo real"])

# Códigos de fechamento de WebSocket "de aplicação" (a faixa 4000-4999 é
# reservada pelo protocolo para uso privado) -- o equivalente, aqui, aos
# 401/404 que o resto da API usa em HTTP.
_FECHAR_NAO_AUTENTICADO = 4401
_FECHAR_QUADRO_NAO_ENCONTRADO = 4404


@roteador.websocket("/ws/quadros/{quadro_id}")
async def canal_do_quadro(
    websocket: WebSocket, quadro_id: int, sessao: Session = Depends(obter_sessao)
):
    """Um cliente conectado aqui entra na sala do quadro (Etapa 6.5) e
    recebe, em tempo real, todo evento que as rotas de lista/cartão
    transmitirem para esse `quadro_id` -- ver app/rotas/cartoes.py e
    listas.py.

    A mesma fronteira de posse do resto da API (Etapa 2.8) vale aqui:
    conectar exige estar logado E o quadro pertencer a quem está logado.
    Como um WebSocket não tem "resposta HTTP de erro" no sentido usual, a
    recusa é fechar a conexão com um código de aplicação, em vez de
    levantar `HTTPException` (que só faz sentido antes do handshake ser
    aceito).
    """
    usuario = await obter_usuario_da_conexao(websocket, sessao)
    if usuario is None:
        await websocket.close(code=_FECHAR_NAO_AUTENTICADO)
        return

    try:
        obter_quadro_do_usuario(sessao, quadro_id, usuario)
    except HTTPException:
        await websocket.close(code=_FECHAR_QUADRO_NAO_ENCONTRADO)
        return

    id_conexao = await gerenciador_de_salas.conectar(quadro_id, websocket)
    try:
        # O primeiro (e único) evento que o SERVIDOR inicia, não uma
        # resposta a uma escrita: dá ao cliente o próprio id de conexão,
        # que ele deve mandar de volta como cabeçalho `X-Origem-Conexao`
        # em toda escrita HTTP -- é o que permite reconhecer e ignorar o
        # próprio eco (Etapa 6.7).
        await websocket.send_json({"tipo": "conectado", "id_conexao": id_conexao})

        # O v1 não processa nenhuma mensagem vinda do cliente (Etapa 6.4:
        # "a escrita continua sendo HTTP") -- este laço só existe para
        # detectar a desconexão via `WebSocketDisconnect`.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        gerenciador_de_salas.desconectar(quadro_id, id_conexao)


class EventoInternoEntrada(BaseModel):
    """O que o worker manda ao publicar um evento (Etapa 5.8/6.5) --
    `evento` já vem pronto no formato de `construir_evento`
    (app/realtime/eventos.py); esta rota só repassa para a sala certa."""

    quadro_id: int
    evento: dict


@roteador.post(
    "/interno/eventos-tempo-real",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
def publicar_evento_interno(
    dados: EventoInternoEntrada,
    x_chave_interna: str = Header(alias="X-Chave-Interna"),
):
    """A ponte entre o worker (um processo à parte, Etapa 5.2) e as salas
    em memória deste processo (Etapa 6.5) -- ver o comentário em
    `configuracoes.chave_interna`, app/config.py, sobre por que essa ponte
    precisa existir e por que é HTTP (não Redis) no v1.

    `include_in_schema=False`: não é uma rota pensada para o frontend
    chamar -- não aparece no Swagger (/docs) para não confundir quem está
    integrando o cliente com uma rota que não é dele.
    """
    if x_chave_interna != configuracoes.chave_interna:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chave interna inválida.")
    gerenciador_de_salas.transmitir_sync(dados.quadro_id, dados.evento)
