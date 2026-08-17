"""
Ponto de entrada da API: cria a aplicação FastAPI e registra as rotas.

Este arquivo é deliberadamente curto -- ele só monta peças que já existem
em outros módulos (app/rotas/*). Toda regra de negócio mora nas rotas, nos
modelos e nos schemas; aqui é só "encanamento" de inicialização.
"""

from fastapi import FastAPI

from app.rotas import assinaturas_push, auth, calendario, cartoes, listas, quadros, realtime

app = FastAPI(
    title="Kanban com tempo",
    description=(
        "API do app de tarefas em kanban com uma dimensão a mais: tempo. "
        "Etapas 1 a 6 da documentação (docs/documentacao.md): estrutura "
        "de quadro/lista/cartão, ordenação fracionária, a dimensão tempo "
        "(prazo, aviso prévio, calendário), o worker de notificação via "
        "Web Push, e o canal em tempo real (WebSocket por quadro, "
        "last-write-wins). A parte de cliente da Etapa 6 -- atualização "
        "otimista, supressão de eco, reconexão -- ainda não existe: não "
        "há board de kanban construído no frontend para aplicá-la."
    ),
    version="0.1.0",
)

# Cada roteador já define seu próprio prefixo (ex.: "/quadros",
# "/quadros/{quadro_id}/listas") lá no próprio arquivo -- aqui só
# conectamos os sete ao app principal. A ordem de inclusão não importa
# para o funcionamento, mas segue a mesma ordem hierárquica do domínio
# (Etapa 2.2), com calendário, assinaturas e tempo real por último por
# serem lentes/infraestrutura sobre os cartões, não níveis novos da
# hierarquia.
app.include_router(auth.roteador)
app.include_router(quadros.roteador)
app.include_router(listas.roteador)
app.include_router(cartoes.roteador)
app.include_router(calendario.roteador)
app.include_router(assinaturas_push.roteador)
app.include_router(realtime.roteador)


@app.get("/saude", tags=["infraestrutura"])
def saude():
    """Endpoint trivial de "estou de pé", usado por health checks (Docker,
    e futuramente um orquestrador em produção) -- não representa nenhuma
    regra de negócio do domínio."""
    return {"status": "ok"}
