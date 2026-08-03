"""
Dependência do FastAPI que identifica o usuário logado a partir do cookie
de sessão, e que toda rota "protegida" declara como parâmetro.

É esta dependência que torna a fronteira "um usuário não alcança quadro de
outro" (Etapa 2.8) possível de aplicar: toda rota de quadro/lista/cartão
recebe o `Usuario` autenticado e filtra as consultas por ele, em vez de
confiar em qualquer id que o cliente possa mandar no corpo da requisição.
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.seguranca import NOME_COOKIE_SESSAO, ler_usuario_id_do_token
from app.database import obter_sessao
from app.modelos.usuario import Usuario


def obter_usuario_atual(
    requisicao: Request, sessao: Session = Depends(obter_sessao)
) -> Usuario:
    """Lê o cookie de sessão da requisição, valida o token, e carrega o
    usuário correspondente do banco.

    Lança 401 (não autenticado) em qualquer um destes casos, sem distinguir
    entre eles na resposta: cookie ausente, token inválido/expirado, ou
    usuário que não existe mais no banco (por exemplo, uma conta apagada
    enquanto a sessão antiga ainda estava com um cookie válido). Misturar
    esses casos numa única mensagem genérica é intencional — não é
    informação que o cliente precise distinguir, e detalhar demais só
    ajudaria alguém tentando adivinhar contas válidas.
    """
    token = requisicao.cookies.get(NOME_COOKIE_SESSAO)
    usuario_id = ler_usuario_id_do_token(token) if token else None

    erro_nao_autenticado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado.",
    )

    if usuario_id is None:
        raise erro_nao_autenticado

    usuario = sessao.get(Usuario, usuario_id)
    if usuario is None:
        raise erro_nao_autenticado

    return usuario
