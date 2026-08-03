"""
Rotas de Quadro (board): criar, listar os quadros do usuário logado, obter
um quadro, renomear e apagar.

Toda rota aqui recebe `usuario_atual` via `Depends(obter_usuario_atual)` e
filtra as consultas por ele. É assim, e não confiando em nenhum id vindo
do cliente, que a Etapa 2.8 ("um usuário não alcança quadro de outro") é
garantida em código.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencias import obter_usuario_atual
from app.database import obter_sessao
from app.modelos.quadro import Quadro
from app.modelos.usuario import Usuario
from app.schemas.quadro import QuadroAtualizar, QuadroCriar, QuadroLeitura

roteador = APIRouter(prefix="/quadros", tags=["quadros"])


def obter_quadro_do_usuario(sessao: Session, quadro_id: int, usuario: Usuario) -> Quadro:
    """Busca um quadro garantindo que ele pertence ao usuário logado.
    Usada por esta rota e também pelas rotas de lista e cartão (ver
    app/rotas/listas.py e app/rotas/cartoes.py), que precisam validar a
    posse do quadro antes de mexer em qualquer coisa dentro dele.

    Devolve 404 (não 403) quando o quadro existe mas é de outro usuário --
    de propósito: 403 já confirmaria "esse quadro existe, você só não pode
    vê-lo", o que vaza informação. 404 trata "não existe" e "não é seu" da
    mesma forma, sem diferença observável de fora.
    """
    quadro = sessao.scalar(
        select(Quadro).where(Quadro.id == quadro_id, Quadro.usuario_id == usuario.id)
    )
    if quadro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quadro não encontrado.")
    return quadro


@roteador.post("", response_model=QuadroLeitura, status_code=status.HTTP_201_CREATED)
def criar_quadro(
    dados: QuadroCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    quadro = Quadro(nome=dados.nome, usuario_id=usuario_atual.id)
    sessao.add(quadro)
    sessao.commit()
    sessao.refresh(quadro)
    return quadro


@roteador.get("", response_model=list[QuadroLeitura])
def listar_quadros(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    return list(sessao.scalars(select(Quadro).where(Quadro.usuario_id == usuario_atual.id)))


@roteador.get("/{quadro_id}", response_model=QuadroLeitura)
def obter_quadro(
    quadro_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    return obter_quadro_do_usuario(sessao, quadro_id, usuario_atual)


@roteador.patch("/{quadro_id}", response_model=QuadroLeitura)
def atualizar_quadro(
    quadro_id: int,
    dados: QuadroAtualizar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    quadro = obter_quadro_do_usuario(sessao, quadro_id, usuario_atual)
    # exclude_unset=True: só os campos que o cliente de fato mandou no
    # corpo do PATCH viram atualização. Um campo omitido não deve
    # sobrescrever o valor atual com None.
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(quadro, campo, valor)
    sessao.commit()
    sessao.refresh(quadro)
    return quadro


@roteador.delete("/{quadro_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_quadro(
    quadro_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    """Apaga o quadro de verdade (o cascade do modelo leva junto listas e
    cartões) -- diferente de lista e cartão, que só arquivam (Etapa 2.7).
    Apagar o quadro inteiro é uma ação rara e deliberada ("não quero mais
    organizar nada sobre isso"), não o "excluir" do dia a dia que precisa
    ser perdoável. Por isso, aqui a exclusão real é aceitável.
    """
    quadro = obter_quadro_do_usuario(sessao, quadro_id, usuario_atual)
    sessao.delete(quadro)
    sessao.commit()
