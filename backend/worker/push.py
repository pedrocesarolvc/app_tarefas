"""
Envio de notificação via Web Push (Etapa 5.5).

Só este módulo conhece `pywebpush`, VAPID e o formato de uma assinatura —
o laço do worker (agendador.py) chama `enviar_notificacao` sem saber nada
disso. É essa fronteira estreita que a Etapa 5.10 pede: "isolar a função
de envio atrás de uma interface e substituí-la por um dublê nos testes —
você testa a lógica, não a rede".

O que este arquivo NÃO faz: decidir o que acontece depois de um envio
falhar ou de uma assinatura expirar. Isso é regra de negócio (Etapa 5.4),
e mora em agendador.py — aqui só existe "tentei enviar, e isto é o que
aconteceu".
"""

import json

from pywebpush import WebPushException, webpush

from app.config import configuracoes
from app.modelos.assinatura_push import AssinaturaPush


class AssinaturaExpiradaError(Exception):
    """O serviço de push respondeu 404 ou 410: essa assinatura não existe
    mais do lado do navegador (Etapa 5.6, "assinaturas morrem" — a
    usuária limpou os dados do navegador, desinstalou, ou o navegador
    renovou a assinatura sozinho). Quem chama `enviar_notificacao` deve
    apagar a assinatura do banco ao receber este erro, e nunca tentar
    reenviar para ela — diferente de qualquer outra falha, que é
    considerada temporária (Etapa 5.9)."""


def enviar_notificacao(assinatura: AssinaturaPush, titulo: str, corpo: str, url_destino: str) -> None:
    """Envia UMA notificação para UMA assinatura (Etapa 5.5: "você
    entrega a mensagem ao carteiro do Google, e ele leva").

    `url_destino` viaja dentro do payload e é o que permite ao service
    worker (Etapa 5.7, frontend/src/sw.ts) abrir o app já no quadro certo
    ao clicar na notificação, em vez de sempre cair na tela inicial —
    "é um detalhe pequeno e é o que faz a notificação parecer útil em vez
    de decorativa".

    Não devolve nada em caso de sucesso. Levanta `AssinaturaExpiradaError`
    se a assinatura expirou; deixa propagar qualquer outra exceção (rede
    fora do ar, timeout, serviço de push com erro 5xx) como falha
    temporária — o chamador é quem decide, por cartão e por assinatura, o
    que fazer com cada tipo de erro."""
    try:
        webpush(
            subscription_info={
                "endpoint": assinatura.endpoint,
                "keys": {
                    "p256dh": assinatura.chave_p256dh,
                    "auth": assinatura.chave_auth,
                },
            },
            data=json.dumps({"titulo": titulo, "corpo": corpo, "url": url_destino}),
            vapid_private_key=configuracoes.vapid_private_key,
            vapid_claims={"sub": configuracoes.vapid_subject},
        )
    except WebPushException as erro:
        resposta = erro.response
        if resposta is not None and resposta.status_code in (404, 410):
            raise AssinaturaExpiradaError(
                f"assinatura {assinatura.id} respondeu {resposta.status_code}"
            ) from erro
        raise
