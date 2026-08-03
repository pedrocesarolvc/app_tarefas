"""
Rotas de Cartao (a tarefa), aninhadas sob uma lista
(/quadros/{quadro_id}/listas/{lista_id}/cartoes/...).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencias import obter_usuario_atual
from app.database import obter_sessao
from app.modelos.cartao import Cartao
from app.modelos.usuario import Usuario
from app.rotas.listas import obter_lista_do_usuario
from app.schemas.cartao import CartaoAtualizar, CartaoCriar, CartaoLeitura, CartaoMover

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


@roteador.post("", response_model=CartaoLeitura, status_code=status.HTTP_201_CREATED)
def criar_cartao(
    quadro_id: int,
    lista_id: int,
    dados: CartaoCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    obter_lista_do_usuario(sessao, quadro_id, lista_id, usuario_atual)
    cartao = Cartao(lista_id=lista_id, **dados.model_dump())
    sessao.add(cartao)
    sessao.commit()
    sessao.refresh(cartao)
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
    consulta = select(Cartao).where(Cartao.lista_id == lista_id).order_by(Cartao.posicao)
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
):
    """Edita conteúdo (título, descrição, prazo, aviso prévio). Não move o
    cartão de lista -- essa é a rota `mover_cartao` abaixo, de propósito
    separada (ver o comentário em CartaoAtualizar, app/schemas/cartao.py)."""
    cartao = obter_cartao_do_usuario(sessao, quadro_id, lista_id, cartao_id, usuario_atual)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(cartao, campo, valor)
    sessao.commit()
    sessao.refresh(cartao)
    return cartao


@roteador.post("/{cartao_id}/mover", response_model=CartaoLeitura)
def mover_cartao(
    quadro_id: int,
    lista_id: int,
    cartao_id: int,
    dados: CartaoMover,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    """A operação central do kanban (Etapa 2.3): mover um cartão é mudar
    `lista_id` -- nada mais. Não há validação de "transição permitida"
    porque, por desenho, todas são permitidas (Etapa 2.4: "não existem
    transições inválidas").

    `dados.lista_id` é validado com `obter_lista_do_usuario` sob o mesmo
    `quadro_id` da URL -- ou seja, um cartão só pode ser movido para outra
    lista do MESMO quadro. Mover entre quadros diferentes não é uma
    operação descrita na documentação (Etapa 2), então não é uma decisão
    deste código tomar sozinho; fica de fora até existir uma razão
    concreta para o contrário.
    """
    cartao = obter_cartao_do_usuario(sessao, quadro_id, lista_id, cartao_id, usuario_atual)
    obter_lista_do_usuario(sessao, quadro_id, dados.lista_id, usuario_atual)
    cartao.lista_id = dados.lista_id
    cartao.posicao = dados.nova_posicao
    sessao.commit()
    sessao.refresh(cartao)
    return cartao


@roteador.post("/{cartao_id}/arquivar", response_model=CartaoLeitura)
def arquivar_cartao(
    quadro_id: int,
    lista_id: int,
    cartao_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    """"Excluir" um cartão, na Etapa 2.7, é isto: marcar `arquivado=True`,
    nunca um DELETE de verdade. O registro continua no banco, só some das
    consultas normais (ver `listar_cartoes` acima)."""
    cartao = obter_cartao_do_usuario(sessao, quadro_id, lista_id, cartao_id, usuario_atual)
    cartao.arquivado = True
    sessao.commit()
    sessao.refresh(cartao)
    return cartao
