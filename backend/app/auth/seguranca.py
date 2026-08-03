"""
As duas peças criptográficas do "login simples" da Etapa 1.4: transformar
senha em hash, e assinar/verificar o cookie que identifica uma sessão
logada.

Por que não JWT, OAuth, ou uma tabela de sessões no banco?
A Etapa 1.4 pede login "simples — identifica o usuário e suas assinaturas
de push". Não há, nas Etapas 1 e 2, nenhuma exigência de múltiplos
dispositivos com controle individual, de expiração revogável por sessão,
nem de terceiros se autenticando via este backend. Um cookie assinado
resolve exatamente o problema que existe hoje: saber quem está fazendo a
requisição, sem poder ser forjado sem a chave secreta do servidor. Se um
requisito real pedir mais que isso no futuro, é uma decisão nova — não
uma complexidade a antecipar agora.
"""

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import configuracoes

# bcrypt é o algoritmo de hash de senha: deliberadamente lento (ao
# contrário de md5/sha256), o que é uma propriedade desejada aqui — torna
# um ataque de força bruta contra senhas vazadas caro, mesmo que o hash em
# si vaze. Usamos a biblioteca `bcrypt` diretamente, e não o `passlib`
# (comum em tutoriais mais antigos): o passlib está sem manutenção ativa e
# quebra com versões recentes do próprio bcrypt, o que é exatamente o tipo
# de dependência frágil que este projeto não precisa carregar.

# O serializer assina (e, com `max_age`, expira) um valor usando a chave
# secreta da aplicação. "sessao-kanban" é um "salt" de propósito: garante
# que um token assinado para outra finalidade dentro do mesmo app (se um
# dia existir) não possa ser reaproveitado aqui por engano.
_serializador_sessao = URLSafeTimedSerializer(
    configuracoes.chave_secreta, salt="sessao-kanban"
)

NOME_COOKIE_SESSAO = "sessao"


def criar_hash_senha(senha: str) -> str:
    """Transforma a senha em texto puro (vinda do cadastro) no valor que
    de fato é gravado em `Usuario.senha_hash`.

    bcrypt trabalha com bytes, não com str, e embute o próprio "salt"
    aleatório dentro do hash gerado (gensalt()) -- por isso não precisamos
    guardar um salt separado em nenhuma coluna: ele já vem dentro do
    valor devolvido aqui."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Confere se a senha digitada no login corresponde ao hash salvo.
    Nunca comparamos senha com senha, nem descriptografamos o hash — bcrypt
    é uma via de mão única por desenho; `checkpw` recalcula o hash da
    senha recebida usando o salt embutido em `senha_hash` e compara os
    dois resultados."""
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))


def criar_token_sessao(usuario_id: int) -> str:
    """Gera o valor que vai dentro do cookie de sessão: o id do usuário,
    assinado. Assinado (não criptografado) é suficiente aqui porque o id do
    usuário não é um segredo — o que importa é que o cliente não consiga
    *forjar* um token para outro id sem conhecer a chave secreta."""
    return _serializador_sessao.dumps(usuario_id)


def ler_usuario_id_do_token(token: str) -> int | None:
    """Verifica a assinatura e a validade (não expirado) do token do
    cookie, e devolve o id do usuário nele contido. Devolve None para
    qualquer token ausente, adulterado ou expirado — o chamador (ver
    app/auth/dependencias.py) trata None como "não autenticado", sem
    precisar saber qual dos três motivos causou a falha."""
    try:
        return _serializador_sessao.loads(
            token, max_age=configuracoes.duracao_sessao_segundos
        )
    except (BadSignature, SignatureExpired):
        return None
