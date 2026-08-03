"""
Ponto de entrada da API: cria a aplicação FastAPI e registra as rotas.

Este arquivo é deliberadamente curto -- ele só monta peças que já existem
em outros módulos (app/rotas/*). Toda regra de negócio mora nas rotas, nos
modelos e nos schemas; aqui é só "encanamento" de inicialização.
"""

from fastapi import FastAPI

from app.rotas import auth, cartoes, listas, quadros

app = FastAPI(
    title="Kanban com tempo",
    description=(
        "API do app de tarefas em kanban com uma dimensão a mais: tempo. "
        "Etapas 1 e 2 da documentação (docs/documentacao.md): estrutura "
        "de quadro/lista/cartão. Os campos de prazo já existem no modelo, "
        "mas a lógica de calendário e notificação (Etapas 4 e 5) ainda não."
    ),
    version="0.1.0",
)

# Cada roteador já define seu próprio prefixo (ex.: "/quadros",
# "/quadros/{quadro_id}/listas") lá no próprio arquivo -- aqui só
# conectamos os quatro ao app principal. A ordem de inclusão não importa
# para o funcionamento, mas segue a mesma ordem hierárquica do domínio
# (Etapa 2.2): usuário/autenticação, depois quadro, lista, cartão.
app.include_router(auth.roteador)
app.include_router(quadros.roteador)
app.include_router(listas.roteador)
app.include_router(cartoes.roteador)


@app.get("/saude", tags=["infraestrutura"])
def saude():
    """Endpoint trivial de "estou de pé", usado por health checks (Docker,
    e futuramente um orquestrador em produção) -- não representa nenhuma
    regra de negócio do domínio."""
    return {"status": "ok"}
