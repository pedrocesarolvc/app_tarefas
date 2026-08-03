# Imagem enxuta com só o Python necessário para rodar a API -- não usamos
# a imagem "full" porque não compilamos nada além do psycopg2 (que já vem
# pré-compilado na variante -binary do requirements.txt).
FROM python:3.12-slim

WORKDIR /app

# Copia só o requirements.txt primeiro, e instala antes de copiar o resto
# do código. Isso é uma otimização de cache de camadas do Docker: o
# código da aplicação muda a cada commit, mas as dependências mudam raro
# -- separar os dois passos evita reinstalar tudo a cada rebuild só
# porque uma linha de app/main.py mudou.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# --host 0.0.0.0 é obrigatório dentro do container: o padrão do uvicorn
# (127.0.0.1) só aceitaria conexões de dentro do próprio container, e o
# docker-compose não conseguiria alcançar a API de fora dele.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
