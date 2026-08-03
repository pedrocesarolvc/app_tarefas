"""
Rotas de Lista (coluna do kanban), aninhadas sob um quadro
(/quadros/{quadro_id}/listas/...).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencias import obter_usuario_atual
from app.database import obter_sessao
from app.modelos.lista import Lista
from app.modelos.usuario import Usuario
from app.rotas.quadros import obter_quadro_do_usuario
from app.schemas.lista import ListaAtualizar, ListaCriar, ListaLeitura

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


@roteador.post("", response_model=ListaLeitura, status_code=status.HTTP_201_CREATED)
def criar_lista(
    quadro_id: int,
    dados: ListaCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    obter_quadro_do_usuario(sessao, quadro_id, usuario_atual)
    lista = Lista(quadro_id=quadro_id, nome=dados.nome, posicao=dados.posicao)
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
    consulta = select(Lista).where(Lista.quadro_id == quadro_id).order_by(Lista.posicao)
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
    """Cobre renomear e reordenar (posicao). Note que, embora
    `ListaAtualizar` também aceite `arquivado`, arquivar uma lista por este
    PATCH genérico NÃO arquiva os cartões dela em cascata -- isso é feito
    pela rota dedicada `arquivar_lista_e_cartoes` abaixo, que implementa o
    comportamento completo da Etapa 2.7. Um PATCH que só muda o campo
    faria a metade do trabalho, então a interface deve preferir sempre a
    rota dedicada para arquivar uma lista.
    """
    lista = obter_lista_do_usuario(sessao, quadro_id, lista_id, usuario_atual)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(lista, campo, valor)
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
