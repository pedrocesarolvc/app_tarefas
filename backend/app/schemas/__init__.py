"""Reexporta os schemas para facilitar o import nas rotas (ex.:
`from app.schemas import CartaoLeitura` em vez de
`from app.schemas.cartao import CartaoLeitura`)."""

from app.schemas.cartao import CartaoAtualizar, CartaoCriar, CartaoLeitura, CartaoMover
from app.schemas.lista import ListaAtualizar, ListaCriar, ListaLeitura, ListaMover
from app.schemas.quadro import QuadroAtualizar, QuadroCriar, QuadroLeitura
from app.schemas.usuario import UsuarioCriar, UsuarioLeitura, UsuarioLogin

__all__ = [
    "UsuarioCriar",
    "UsuarioLogin",
    "UsuarioLeitura",
    "QuadroCriar",
    "QuadroAtualizar",
    "QuadroLeitura",
    "ListaCriar",
    "ListaAtualizar",
    "ListaMover",
    "ListaLeitura",
    "CartaoCriar",
    "CartaoAtualizar",
    "CartaoMover",
    "CartaoLeitura",
]
