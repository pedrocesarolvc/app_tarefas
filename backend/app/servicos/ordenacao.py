"""
Ordenação por indexação fracionária (Etapa 3 da documentação).

Este é o ÚNICO lugar do sistema que sabe calcular uma posição. Nenhuma
rota, nenhum schema, decide isso sozinho -- todos só chamam
`calcular_posicao(anterior, posterior)` e recebem de volta "a posição
entre A e B". É essa fronteira estreita que torna a estratégia de
ordenação trocável (Etapa 3.6): se um dia o LexoRank substituir o NUMERIC,
a mudança acontece neste arquivo, e em nenhum outro -- nenhuma rota
precisaria mudar uma linha.

Por que a posição é um Decimal, e não um float:
Inteiros consecutivos (1, 2, 3...) obrigam a renumerar N registros a cada
movimento (Etapa 3.2). Soltar essa restrição e aceitar qualquer número
racional entre dois vizinhos resolve isso com um único UPDATE (Etapa
3.3) -- mas float64 tem só 52 bits de mantissa, e um ponto médio calculado
repetidas vezes no mesmo lugar (por exemplo, a usuária arrastando cartões
sempre para o topo) colapsa depois de ~52 divisões: dois números
diferentes viram o mesmo float, e a ordem entre os dois passa a ser
indefinida (Etapa 3.4). `Decimal` (mapeado para NUMERIC no PostgreSQL, sem
limite de precisão) elimina essa armadilha por construção: dividir um
intervalo ao meio nunca "estoura" -- só acrescenta mais um dígito decimal
(Etapa 3.6).
"""

from decimal import Decimal, localcontext

# O módulo `decimal` do Python, por padrão, arredonda resultados de conta
# em 28 dígitos SIGNIFICATIVOS (`decimal.getcontext().prec`) -- diferente
# do NUMERIC do PostgreSQL, que é de fato ilimitado. Como cada bisseção
# consecutiva no mesmo ponto (Etapa 3.4) acrescenta aproximadamente um
# dígito decimal de precisão ao resultado, os 28 dígitos padrão dariam
# margem para só ~25 inserções nesta função antes de a própria conta em
# Python arredondar e reintroduzir o colapso que o NUMERIC deveria ter
# eliminado -- ironicamente, o mesmo bug da Etapa 3.4, um nível abaixo.
# Por isso o cálculo do ponto médio roda dentro de um `localcontext` com
# precisão bem mais folgada: alto o suficiente para milhares de arrastes
# consecutivos no mesmo ponto, e local (não `decimal.getcontext().prec =
# ...` global) para não alterar a precisão decimal do resto do processo
# por um efeito colateral escondido neste módulo.
_DIGITOS_DE_PRECISAO = 200

# Posição do primeiro item de uma lista vazia (Etapa 3.7). O valor em si
# é arbitrário -- o que importa é deixar espaço confortável dos dois lados
# para as primeiras inserções no topo e no fim.
POSICAO_INICIAL = Decimal(1000)

# Quanto somar (inserir no fim) ou subtrair (inserir no topo) da posição
# do único vizinho existente, quando não há vizinho do outro lado (Etapa
# 3.7). É um valor FIXO, não um valor dividido pela metade: se cada
# inserção no topo dividisse a posição do vizinho por dois rumo a zero, os
# valores encolheriam indefinidamente e reencontrariam o mesmo problema de
# precisão da Etapa 3.4 -- só que perto do zero, em vez de perto de um
# vizinho fixo. Somar/subtrair um intervalo fixo mantém os valores numa
# faixa saudável indefinidamente.
INTERVALO_PADRAO = Decimal(1000)


class PosicaoInvalidaError(ValueError):
    """Levantada quando `anterior` e `posterior` não estão na ordem que
    seus nomes prometem (anterior deveria vir estritamente antes de
    posterior). Isso só pode acontecer se quem chamou passou os vizinhos
    errados -- por exemplo, ids que vieram de uma versão desatualizada da
    lista no cliente -- então é tratado como erro do chamador, não
    silenciado."""


def calcular_posicao(anterior: Decimal | None, posterior: Decimal | None) -> Decimal:
    """Calcula a posição de um item a ser inserido entre `anterior` e
    `posterior` -- os dois já como a posição (não o item inteiro), e
    ambos opcionais para cobrir os três casos de borda da Etapa 3.7:

    - `anterior=None, posterior=None`: lista vazia -- primeira posição.
    - `anterior=None, posterior=X`   : inserção no topo (nada antes).
    - `anterior=X, posterior=None`   : inserção no fim (nada depois).
    - `anterior=X, posterior=Y`      : inserção entre dois itens -- o
      ponto médio (Etapa 3.3), que é o caso comum de arrastar-e-soltar.
    """
    if anterior is not None and posterior is not None and anterior >= posterior:
        raise PosicaoInvalidaError(
            f"anterior ({anterior}) precisa ser estritamente menor que posterior ({posterior})."
        )

    if anterior is None and posterior is None:
        return POSICAO_INICIAL
    if anterior is None:
        assert posterior is not None  # só para o verificador de tipos
        return posterior - INTERVALO_PADRAO
    if posterior is None:
        return anterior + INTERVALO_PADRAO

    with localcontext() as contexto:
        contexto.prec = _DIGITOS_DE_PRECISAO
        return (anterior + posterior) / 2
