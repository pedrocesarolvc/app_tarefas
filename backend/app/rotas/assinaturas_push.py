"""
Rotas de AssinaturaPush (Etapa 5.6): o backend guardando o "endereço" de
Web Push de cada navegador da usuária, e servindo a chave pública VAPID
que o navegador precisa para gerar esse endereço em primeiro lugar.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencias import obter_usuario_atual
from app.config import configuracoes
from app.database import obter_sessao
from app.modelos.assinatura_push import AssinaturaPush
from app.modelos.usuario import Usuario
from app.schemas.assinatura_push import AssinaturaPushCriar, AssinaturaPushLeitura

roteador = APIRouter(prefix="/assinaturas-push", tags=["notificações push"])


@roteador.get("/chave-publica")
def obter_chave_publica():
    """A chave pública VAPID (Etapa 5.5) que o frontend passa para
    `PushManager.subscribe()` ao criar uma assinatura no navegador. Não
    exige login: a chave pública não é secreta -- é, por definição, a
    metade que pode circular; só a privada (nunca exposta por aqui)
    precisa de sigilo."""
    return {"chave_publica": configuracoes.vapid_public_key}


@roteador.post("", response_model=AssinaturaPushLeitura, status_code=status.HTTP_201_CREATED)
def criar_assinatura(
    dados: AssinaturaPushCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    """Registra a assinatura de Web Push do navegador atual.

    Se o `endpoint` já existir no banco, a linha é REATRIBUÍDA ao usuário
    atual em vez de duplicada ou rejeitada pela restrição de unicidade
    (Etapa 5.6: a assinatura pertence a um navegador, não a uma pessoa).
    Isso cobre o caso real de duas contas usando o mesmo navegador: se a
    usuária B loga num Chrome onde a usuária A já tinha assinado push
    antes sem cancelar, o próprio navegador devolve a MESMA assinatura já
    existente -- e faz sentido que ela passe a notificar quem está logado
    agora, não quem assinou primeiro.
    """
    assinatura = sessao.scalar(select(AssinaturaPush).where(AssinaturaPush.endpoint == dados.endpoint))
    if assinatura is None:
        assinatura = AssinaturaPush(usuario_id=usuario_atual.id, **dados.model_dump())
        sessao.add(assinatura)
    else:
        assinatura.usuario_id = usuario_atual.id
        assinatura.chave_p256dh = dados.chave_p256dh
        assinatura.chave_auth = dados.chave_auth
    sessao.commit()
    sessao.refresh(assinatura)
    return assinatura


@roteador.get("", response_model=list[AssinaturaPushLeitura])
def listar_assinaturas(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    return list(
        sessao.scalars(select(AssinaturaPush).where(AssinaturaPush.usuario_id == usuario_atual.id))
    )


@roteador.delete("/{assinatura_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_assinatura(
    assinatura_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    """Cancelar push manualmente (ex.: a usuária desativou nas
    configurações do app). A mesma fronteira de posse do resto da API:
    404, não 403, se a assinatura não for do usuário atual (ver o
    comentário em obter_quadro_do_usuario, app/rotas/quadros.py)."""
    assinatura = sessao.scalar(
        select(AssinaturaPush).where(
            AssinaturaPush.id == assinatura_id, AssinaturaPush.usuario_id == usuario_atual.id
        )
    )
    if assinatura is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assinatura não encontrada.")
    sessao.delete(assinatura)
    sessao.commit()
