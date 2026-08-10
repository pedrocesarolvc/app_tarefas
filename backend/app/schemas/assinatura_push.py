"""
Schemas Pydantic da AssinaturaPush (Etapa 5.6).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AssinaturaPushCriar(BaseModel):
    """O que o frontend manda depois que o navegador gera uma assinatura
    de Web Push (Etapa 5.5, passo 3) — `usuario_id` não aparece aqui pelo
    mesmo motivo de sempre: vem do usuário autenticado, nunca do corpo da
    requisição."""

    endpoint: str = Field(min_length=1)
    chave_p256dh: str = Field(min_length=1)
    chave_auth: str = Field(min_length=1)


class AssinaturaPushLeitura(BaseModel):
    id: int
    endpoint: str
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
