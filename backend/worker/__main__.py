"""
Ponto de entrada do processo do worker (Etapa 5.2).

Roda com `python -m worker`, a partir de `backend/` — nunca é importado
pela API; é um processo próprio, com o serviço `worker` dedicado no
docker-compose.yml, que sobe e cai independente do serviço `api`. É
exatamente essa independência que resolve os três problemas da Etapa 5.2
(reiniciar a API não mata o worker, duas instâncias da API não duplicam
notificação, e envio pesado não disputa CPU com as requisições).

"Acorda, consulta, envia, dorme" (Etapa 5.3) — um laço deliberadamente
simples. A resposta de produção seria uma fila com agendador (ARQ, Celery
beat); trocar depois é um upgrade natural, mas exigiria Redis/broker agora
sem ensinar nada a mais sobre o problema em si.
"""

import time
from datetime import datetime, timezone

from app.database import SessionLocal
from worker.agendador import INTERVALO_PADRAO_SEGUNDOS, executar_ciclo


def rodar_para_sempre() -> None:
    print(f"worker: iniciado, verificando a cada {INTERVALO_PADRAO_SEGUNDOS}s", flush=True)
    while True:
        sessao = SessionLocal()
        try:
            quantidade = executar_ciclo(sessao)
            if quantidade:
                agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
                print(f"worker: {quantidade} cartão(ões) notificado(s) às {agora}", flush=True)
        finally:
            sessao.close()
        time.sleep(INTERVALO_PADRAO_SEGUNDOS)


if __name__ == "__main__":
    rodar_para_sempre()
