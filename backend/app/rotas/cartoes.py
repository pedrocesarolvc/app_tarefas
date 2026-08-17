"""
Rotas de Cartao (a tarefa), aninhadas sob uma lista
(/quadros/{quadro_id}/listas/{lista_id}/cartoes/...).
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencias import obter_usuario_atual
from app.database import obter_sessao
from app.modelos.cartao import Cartao
from app.modelos.usuario import Usuario
from app.realtime.eventos import construir_evento
from app.realtime.gerenciador import gerenciador_de_salas
from app.rotas.listas import obter_lista_do_usuario
from app.schemas.cartao import CartaoAtualizar, CartaoCriar, CartaoLeitura, CartaoMover
from app.servicos.ordenacao import PosicaoInvalidaError, calcular_posicao
from app.servicos.prazos import aplicar_edicao_de_cartao, calcular_notificar_em

# Parâmetro de rota compartilhado pelas quatro escritas abaixo: o id de
# conexão do cliente que originou a mudança (Etapa 6.7), ausente para
# quem escreve sem WebSocket nenhum (ex.: um teste, ou um cliente sem
# tempo real). Ver o comentário em construir_evento, app/realtime/eventos.py.
_ORIGEM_CONEXAO = Header(default=None, alias="X-Origem-Conexao")


def _transmitir(quadro_id: int, tipo: str, cartao: Cartao, origem: str | None) -> None:
    """Publica o evento na sala do quadro depois de uma escrita bem-
    sucedida (Etapa 6.5). Fica isolado aqui, e não repetido em cada rota,
    pelo mesmo motivo de app/servicos/ordenacao.py e prazos.py: um só
    lugar decide como o evento de cartão é montado."""
    gerenciador_de_salas.transmitir_sync(
        quadro_id,
        construir_evento(
            tipo, CartaoLeitura.model_validate(cartao).model_dump(mode="json"), origem
        ),
    )

roteador = APIRouter(prefix="/quadros/{quadro_id}/listas/{lista_id}/cartoes", tags=["cartões"])


def obter_cartao_do_usuario(
    sessao: Session, quadro_id: int, lista_id: int, cartao_id: int, usuario: Usuario
) -> Cartao:
    """Fecha a cadeia de fronteira de posse: cartão pertence a lista,
    lista pertence a quadro, quadro pertence a usuário. Cada elo é
    validado por quem vem antes -- `obter_lista_do_usuario` já garante
    quadro e lista; aqui só falta amarrar o cartão."""
    obter_lista_do_usuario(sessao, quadro_id, lista_id, usuario)
    cartao = sessao.scalar(select(Cartao).where(Cartao.id == cartao_id, Cartao.lista_id == lista_id))
    if cartao is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cartão não encontrado.")
    return cartao


def _obter_posicao_do_ultimo_cartao(sessao: Session, lista_id: int) -> Decimal | None:
    """A posição do último cartão visível da lista (não arquivado), ou
    None se a lista ainda não tem nenhum cartão. Só decide onde anexar um
    cartão recém-criado (Etapa 3: um cartão novo sempre vai para o final
    da lista) -- o cálculo em si é `calcular_posicao`."""
    return sessao.scalar(
        select(Cartao.posicao)
        .where(Cartao.lista_id == lista_id, Cartao.arquivado.is_(False))
        .order_by(Cartao.posicao.desc(), Cartao.id.desc())
        .limit(1)
    )


@roteador.post("", response_model=CartaoLeitura, status_code=status.HTTP_201_CREATED)
def criar_cartao(
    quadro_id: int,
    lista_id: int,
    dados: CartaoCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
    origem_conexao: str | None = _ORIGEM_CONEXAO,
):
    """Um cartão novo sempre entra no final da lista (Etapa 3: sem campo
    `posicao` no schema -- ver o comentário em CartaoCriar). Mesmo caso de
    borda "soltar no fim" da Etapa 3.7 usado em `criar_lista`
    (app/rotas/listas.py).

    `notificar_em` já nasce calculado (Etapa 4.3) -- mesmo numa criação,
    não só numa edição -- para que um cartão criado com prazo e aviso
    prévio já esteja pronto para o worker (Etapa 5) sem precisar de um
    segundo PATCH."""
    obter_lista_do_usuario(sessao, quadro_id, lista_id, usuario_atual)
    posicao_do_ultimo = _obter_posicao_do_ultimo_cartao(sessao, lista_id)
    cartao = Cartao(
        lista_id=lista_id,
        posicao=calcular_posicao(anterior=posicao_do_ultimo, posterior=None),
        notificar_em=calcular_notificar_em(dados.prazo, dados.aviso_previo),
        **dados.model_dump(),
    )
    sessao.add(cartao)
    sessao.commit()
    sessao.refresh(cartao)
    _transmitir(quadro_id, "cartao_criado", cartao, origem_conexao)
    return cartao


@roteador.get("", response_model=list[CartaoLeitura])
def listar_cartoes(
    quadro_id: int,
    lista_id: int,
    incluir_arquivados: bool = False,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    obter_lista_do_usuario(sessao, quadro_id, lista_id, usuario_atual)
    # Desempate por `id` (Etapa 3.8) -- ver o comentário equivalente em
    # listar_listas, app/rotas/listas.py.
    consulta = (
        select(Cartao)
        .where(Cartao.lista_id == lista_id)
        .order_by(Cartao.posicao, Cartao.id)
    )
    if not incluir_arquivados:
        # Etapa 2.8: "arquivar um cartão o remove das consultas normais,
        # mas ele continua no banco" -- o filtro é o que faz a primeira
        # metade dessa frase acontecer; o segundo `select` sem este WHERE
        # (via incluir_arquivados=True) é o que prova a segunda metade.
        consulta = consulta.where(Cartao.arquivado.is_(False))
    return list(sessao.scalars(consulta))


@roteador.patch("/{cartao_id}", response_model=CartaoLeitura)
def atualizar_cartao(
    quadro_id: int,
    lista_id: int,
    cartao_id: int,
    dados: CartaoAtualizar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
    origem_conexao: str | None = _ORIGEM_CONEXAO,
):
    """Edita conteúdo (título, descrição, prazo, aviso prévio). Não move o
    cartão de lista -- essa é a rota `mover_cartao` abaixo, de propósito
    separada (ver o comentário em CartaoAtualizar, app/schemas/cartao.py).

    A aplicação dos campos passa por `aplicar_edicao_de_cartao` (Etapa
    4.3), não por um `setattr` direto: é ela quem garante que mudar
    `prazo` ou `aviso_previo` recalcula `notificar_em` e reseta
    `notificado` -- a regra cujo esquecimento é o bug silencioso descrito
    em app/servicos/prazos.py."""
    cartao = obter_cartao_do_usuario(sessao, quadro_id, lista_id, cartao_id, usuario_atual)
    aplicar_edicao_de_cartao(cartao, dados.model_dump(exclude_unset=True))
    sessao.commit()
    sessao.refresh(cartao)
    _transmitir(quadro_id, "cartao_atualizado", cartao, origem_conexao)
    return cartao


@roteador.post("/{cartao_id}/mover", response_model=CartaoLeitura)
def mover_cartao(
    quadro_id: int,
    lista_id: int,
    cartao_id: int,
    dados: CartaoMover,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
    origem_conexao: str | None = _ORIGEM_CONEXAO,
):
    """A operação central do kanban (Etapa 2.3): mover um cartão é mudar
    `lista_id` -- nada mais. Não há validação de "transição permitida"
    porque, por desenho, todas são permitidas (Etapa 2.4: "não existem
    transições inválidas").

    A posição no destino vem de vizinhos, não de um número calculado pelo
    cliente (Etapa 3.3/3.6): `cartao_anterior_id` e `cartao_posterior_id`
    (ver CartaoMover, app/schemas/cartao.py) são buscados DENTRO da lista
    de destino -- `obter_cartao_do_usuario` com `dados.lista_id` garante
    isso e, de quebra, garante que a lista de destino é do mesmo usuário e
    do mesmo quadro (mover entre quadros diferentes não está no escopo,
    ver o comentário abaixo).

    Só o cartão movido é escrito; os vizinhos nunca são tocados (Etapa
    3.9: "mover altera apenas aquele registro").
    """
    cartao = obter_cartao_do_usuario(sessao, quadro_id, lista_id, cartao_id, usuario_atual)

    # `obter_lista_do_usuario` sob o mesmo `quadro_id` da URL: um cartão só
    # pode ser movido para outra lista do MESMO quadro. Mover entre
    # quadros diferentes não é uma operação descrita na documentação
    # (Etapa 2), então não é uma decisão deste código tomar sozinho.
    obter_lista_do_usuario(sessao, quadro_id, dados.lista_id, usuario_atual)

    posicao_anterior = None
    if dados.cartao_anterior_id is not None:
        posicao_anterior = obter_cartao_do_usuario(
            sessao, quadro_id, dados.lista_id, dados.cartao_anterior_id, usuario_atual
        ).posicao

    posicao_posterior = None
    if dados.cartao_posterior_id is not None:
        posicao_posterior = obter_cartao_do_usuario(
            sessao, quadro_id, dados.lista_id, dados.cartao_posterior_id, usuario_atual
        ).posicao

    try:
        nova_posicao = calcular_posicao(anterior=posicao_anterior, posterior=posicao_posterior)
    except PosicaoInvalidaError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro

    cartao.lista_id = dados.lista_id
    cartao.posicao = nova_posicao
    sessao.commit()
    sessao.refresh(cartao)
    _transmitir(quadro_id, "cartao_movido", cartao, origem_conexao)
    return cartao


@roteador.post("/{cartao_id}/arquivar", response_model=CartaoLeitura)
def arquivar_cartao(
    quadro_id: int,
    lista_id: int,
    cartao_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
    origem_conexao: str | None = _ORIGEM_CONEXAO,
):
    """"Excluir" um cartão, na Etapa 2.7, é isto: marcar `arquivado=True`,
    nunca um DELETE de verdade. O registro continua no banco, só some das
    consultas normais (ver `listar_cartoes` acima)."""
    cartao = obter_cartao_do_usuario(sessao, quadro_id, lista_id, cartao_id, usuario_atual)
    cartao.arquivado = True
    sessao.commit()
    sessao.refresh(cartao)
    _transmitir(quadro_id, "cartao_arquivado", cartao, origem_conexao)
    return cartao
