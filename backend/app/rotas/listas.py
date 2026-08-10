"""
Rotas de Lista (coluna do kanban), aninhadas sob um quadro
(/quadros/{quadro_id}/listas/...).
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencias import obter_usuario_atual
from app.database import obter_sessao
from app.modelos.lista import Lista
from app.modelos.usuario import Usuario
from app.rotas.quadros import obter_quadro_do_usuario
from app.schemas.lista import ListaAtualizar, ListaCriar, ListaLeitura, ListaMover
from app.servicos.ordenacao import PosicaoInvalidaError, calcular_posicao

roteador = APIRouter(prefix="/quadros/{quadro_id}/listas", tags=["listas"])


def obter_lista_do_usuario(sessao: Session, quadro_id: int, lista_id: int, usuario: Usuario) -> Lista:
    """Mesma lógica de fronteira de `obter_quadro_do_usuario`, um nível
    abaixo: a lista só é alcançável se o quadro que a contém pertencer ao
    usuário logado. Chamar `obter_quadro_do_usuario` primeiro garante isso
    e devolve 404 cedo se o próprio quadro já não for do usuário -- a
    consulta da lista abaixo só roda depois dessa garantia."""
    obter_quadro_do_usuario(sessao, quadro_id, usuario)
    lista = sessao.scalar(select(Lista).where(Lista.id == lista_id, Lista.quadro_id == quadro_id))
    if lista is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lista não encontrada.")
    return lista


def _obter_posicao_da_ultima_lista(sessao: Session, quadro_id: int) -> Decimal | None:
    """A posição da última lista visível do quadro (não arquivada), ou
    None se o quadro não tem nenhuma lista ainda. Usada só para decidir
    onde anexar uma lista recém-criada (Etapa 3: uma lista nova sempre vai
    para o final) -- a conta em si é feita por `calcular_posicao`, não
    aqui."""
    return sessao.scalar(
        select(Lista.posicao)
        .where(Lista.quadro_id == quadro_id, Lista.arquivado.is_(False))
        .order_by(Lista.posicao.desc(), Lista.id.desc())
        .limit(1)
    )


@roteador.post("", response_model=ListaLeitura, status_code=status.HTTP_201_CREATED)
def criar_lista(
    quadro_id: int,
    dados: ListaCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    """Uma lista nova sempre entra no final do quadro (Etapa 3: sem campo
    `posicao` no schema -- ver o comentário em ListaCriar). A posição é
    calculada como "depois da última lista, sem nada depois dela",
    exatamente o caso de borda "soltar no fim" da Etapa 3.7."""
    obter_quadro_do_usuario(sessao, quadro_id, usuario_atual)
    posicao_da_ultima = _obter_posicao_da_ultima_lista(sessao, quadro_id)
    lista = Lista(
        quadro_id=quadro_id,
        nome=dados.nome,
        posicao=calcular_posicao(anterior=posicao_da_ultima, posterior=None),
    )
    sessao.add(lista)
    sessao.commit()
    sessao.refresh(lista)
    return lista


@roteador.get("", response_model=list[ListaLeitura])
def listar_listas(
    quadro_id: int,
    incluir_arquivadas: bool = False,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    obter_quadro_do_usuario(sessao, quadro_id, usuario_atual)
    # Desempate por `id` (Etapa 3.8): sem ele, duas listas com a mesma
    # posição (possível quando duas inserções concorrentes calculam o
    # mesmo ponto médio) poderiam aparecer em ordens diferentes em
    # consultas diferentes.
    consulta = (
        select(Lista)
        .where(Lista.quadro_id == quadro_id)
        .order_by(Lista.posicao, Lista.id)
    )
    if not incluir_arquivadas:
        # Etapa 2.8: "arquivar uma lista arquiva seus cartões" -- e, por
        # simetria, uma lista arquivada não deve reaparecer na visão normal
        # do quadro, mesmo que ainda exista no banco.
        consulta = consulta.where(Lista.arquivado.is_(False))
    return list(sessao.scalars(consulta))


@roteador.patch("/{lista_id}", response_model=ListaLeitura)
def atualizar_lista(
    quadro_id: int,
    lista_id: int,
    dados: ListaAtualizar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    """Cobre a edição de conteúdo: renomear (`nome`). Note que, embora
    `ListaAtualizar` também aceite `arquivado`, arquivar uma lista por este
    PATCH genérico NÃO arquiva os cartões dela em cascata -- isso é feito
    pela rota dedicada `arquivar_lista_e_cartoes` abaixo, que implementa o
    comportamento completo da Etapa 2.7. Reordenar as colunas também não é
    um campo aqui -- é a rota dedicada `mover_lista` (Etapa 3), logo
    abaixo. Um PATCH que só muda um campo faria a metade do trabalho em
    ambos os casos, então a interface deve preferir as rotas dedicadas.
    """
    lista = obter_lista_do_usuario(sessao, quadro_id, lista_id, usuario_atual)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(lista, campo, valor)
    sessao.commit()
    sessao.refresh(lista)
    return lista


@roteador.post("/{lista_id}/mover", response_model=ListaLeitura)
def mover_lista(
    quadro_id: int,
    lista_id: int,
    dados: ListaMover,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    """Reordena as colunas do quadro (Etapa 2.2: "listas também precisam
    de ordem"). O cliente manda só os vizinhos onde a lista foi solta
    (ver o comentário em ListaMover, app/schemas/lista.py) -- esta rota
    busca a posição de cada um e delega a conta para
    `calcular_posicao` (Etapa 3.6). Só a lista movida é escrita; os
    vizinhos nunca são tocados (Etapa 3.9: "mover altera apenas aquele
    registro")."""
    lista = obter_lista_do_usuario(sessao, quadro_id, lista_id, usuario_atual)

    posicao_anterior = None
    if dados.lista_anterior_id is not None:
        posicao_anterior = obter_lista_do_usuario(
            sessao, quadro_id, dados.lista_anterior_id, usuario_atual
        ).posicao

    posicao_posterior = None
    if dados.lista_posterior_id is not None:
        posicao_posterior = obter_lista_do_usuario(
            sessao, quadro_id, dados.lista_posterior_id, usuario_atual
        ).posicao

    try:
        lista.posicao = calcular_posicao(anterior=posicao_anterior, posterior=posicao_posterior)
    except PosicaoInvalidaError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro

    sessao.commit()
    sessao.refresh(lista)
    return lista


@roteador.post("/{lista_id}/arquivar", response_model=ListaLeitura)
def arquivar_lista_e_cartoes(
    quadro_id: int,
    lista_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    """Implementa a Etapa 2.7 ao pé da letra: "arquivar a lista arquiva os
    cartões dentro dela". É uma rota própria (POST .../arquivar), e não um
    PATCH genérico, justamente porque tem um efeito colateral em cascata
    que precisa ficar explícito para quem lê a lista de endpoints da API.
    """
    lista = obter_lista_do_usuario(sessao, quadro_id, lista_id, usuario_atual)
    lista.arquivado = True
    for cartao in lista.cartoes:
        cartao.arquivado = True
    sessao.commit()
    sessao.refresh(lista)
    return lista
