"""
Reúne os cinco modelos num só lugar de import.

Isso tem um motivo técnico, não é só conveniência: o SQLAlchemy precisa que
toda classe mapeada tenha sido importada (e portanto registrada em
`Base.metadata`) antes de coisas como `Base.metadata.create_all(...)` ou o
`env.py` do Alembic funcionarem corretamente. Sem este arquivo, seria fácil
esquecer de importar um modelo novo em algum lugar e ele simplesmente não
apareceria nas migrações nem nas tabelas criadas.

Basta importar `app.modelos` (este pacote) em vez de cada arquivo
individual para garantir que os cinco modelos estão registrados.
"""

from app.modelos.assinatura_push import AssinaturaPush
from app.modelos.cartao import Cartao
from app.modelos.lista import Lista
from app.modelos.quadro import Quadro
from app.modelos.usuario import Usuario

__all__ = ["Usuario", "Quadro", "Lista", "Cartao", "AssinaturaPush"]
