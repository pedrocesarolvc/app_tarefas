"""
Schemas Pydantic do Usuario.

Um "schema" aqui não é o mesmo que "modelo" (app/modelos/usuario.py): o
modelo descreve a tabela do banco; o schema descreve o formato JSON que
entra e sai pela API. Eles parecem iguais para Usuario, mas nunca são a
mesma classe — o modelo tem `senha_hash`, e nenhum schema de leitura pode
ter esse campo, ou a API vazaria o hash da senha de volta pro cliente.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UsuarioCriar(BaseModel):
    """O que a rota de cadastro recebe: e-mail e senha em texto puro.
    A senha em texto puro só existe neste schema, de passagem — ela é
    transformada em hash (app/auth/seguranca.py) antes de qualquer
    gravação no banco, e nunca é logada nem devolvida."""

    email: EmailStr
    senha: str


class UsuarioLogin(BaseModel):
    """O que a rota de login recebe. Mesmo formato de UsuarioCriar, mas é
    um schema separado de propósito: cadastro e login são operações
    diferentes, e mantê-los distintos evita que um campo futuro adicionado
    só para um dos dois (por exemplo, confirmação de senha no cadastro)
    vaze para o outro sem querer."""

    email: EmailStr
    senha: str


class UsuarioLeitura(BaseModel):
    """O que a API devolve sobre um usuário. Note a ausência de
    `senha_hash` — é a fronteira que impede o hash de vazar."""

    id: int
    email: EmailStr
    criado_em: datetime

    # from_attributes=True permite construir este schema diretamente a
    # partir de um objeto Usuario do SQLAlchemy (lendo `.id`, `.email`,
    # `.criado_em` como atributos), em vez de exigir um dicionário.
    model_config = ConfigDict(from_attributes=True)
