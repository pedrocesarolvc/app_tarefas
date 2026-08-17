"""
Rotas de autenticação: cadastro, login, logout e "quem sou eu".
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencias import obter_usuario_atual
from app.auth.seguranca import (
    NOME_COOKIE_SESSAO,
    criar_hash_senha,
    criar_token_sessao,
    verificar_senha,
)
from app.config import configuracoes
from app.database import obter_sessao
from app.modelos.usuario import Usuario
from app.schemas.usuario import UsuarioCriar, UsuarioLeitura, UsuarioLogin

roteador = APIRouter(prefix="/auth", tags=["autenticação"])


@roteador.post("/registrar", response_model=UsuarioLeitura, status_code=status.HTTP_201_CREATED)
def registrar(dados: UsuarioCriar, sessao: Session = Depends(obter_sessao)):
    usuario = Usuario(email=dados.email, senha_hash=criar_hash_senha(dados.senha))
    sessao.add(usuario)
    try:
        # O commit é quem de fato aciona a restrição UNIQUE do banco sobre
        # `email` (app/modelos/usuario.py). Deixamos o banco ser a fonte
        # da verdade sobre unicidade, em vez de só checar antes com um
        # SELECT -- um SELECT-depois-INSERT tem uma janela de corrida onde
        # dois cadastros simultâneos com o mesmo e-mail passariam os dois.
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado.")
    sessao.refresh(usuario)
    return usuario


@roteador.post("/login", response_model=UsuarioLeitura)
def login(dados: UsuarioLogin, resposta: Response, sessao: Session = Depends(obter_sessao)):
    usuario = sessao.scalar(select(Usuario).where(Usuario.email == dados.email))

    # Mesma mensagem de erro para "e-mail não existe" e "senha errada" --
    # diferenciar daria a um atacante uma forma de descobrir quais e-mails
    # estão cadastrados, só tentando logins.
    erro_credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos."
    )
    if usuario is None or not verificar_senha(dados.senha, usuario.senha_hash):
        raise erro_credenciais_invalidas

    token = criar_token_sessao(usuario.id)
    resposta.set_cookie(
        key=NOME_COOKIE_SESSAO,
        value=token,
        max_age=configuracoes.duracao_sessao_segundos,
        # httponly: JavaScript no navegador não consegue ler este cookie,
        # o que reduz o estrago de um eventual XSS (o script malicioso não
        # rouba a sessão só por rodar na página).
        httponly=True,
        # samesite="lax" (padrão) mitiga CSRF e é suficiente quando
        # frontend e API são a mesma origem (dev). Com
        # `cookie_entre_sites=True` (implantação com domínios separados,
        # ver app/config.py), vira "none" -- e "none" exige `secure=True`,
        # senão o navegador recusa o cookie inteiro.
        samesite="none" if configuracoes.cookie_entre_sites else "lax",
        secure=configuracoes.cookie_entre_sites,
    )
    return usuario


@roteador.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(resposta: Response):
    resposta.delete_cookie(NOME_COOKIE_SESSAO)


@roteador.get("/eu", response_model=UsuarioLeitura)
def eu(usuario_atual: Usuario = Depends(obter_usuario_atual)):
    """Devolve o usuário logado. Existe principalmente para o frontend
    perguntar "eu já estou logada?" ao carregar o app, sem precisar tentar
    uma operação de verdade só para descobrir."""
    return usuario_atual
