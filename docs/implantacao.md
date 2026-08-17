# Implantação — Vercel (frontend) + Hostinger (backend)

Guia para publicar este app de verdade, saindo de "roda na minha máquina" para duas máquinas de produção: o **frontend** (React, estático) na Vercel, e o **backend** (API + worker + Postgres) num servidor da Hostinger.

A arquitetura de produção fica em dois domínios separados, ex.:

- `https://kanban.seudominio.com` (ou `algumacoisa.vercel.app`) — o frontend, servido pela Vercel.
- `https://api.seudominio.com` — a API + WebSocket, rodando na Hostinger.

Isso é exatamente o cenário que a Etapa 7.5 (CORS) e as variáveis `COOKIE_ENTRE_SITES`/`VITE_API_URL` já foram desenhadas para suportar (ver `app/config.py` e `frontend/src/api/cliente.ts`) — nenhuma das duas pontas precisa de código novo, só de configuração.

Por que dois provedores, e não um só? Porque encaixam no que cada um faz melhor: a Vercel é feita para servir um build estático com CDN e HTTPS automático em segundos; a Hostinger é onde você já tem servidor e domínio, e este backend precisa de processos de longa duração (a API, o worker, o Postgres) que uma hospedagem de estático não roda.

## 0. Antes de começar: qual plano você tem na Hostinger?

O backend deste app **precisa** rodar Docker (ou, no mínimo, processos Python de longa duração + PostgreSQL) — algo só possível numa **VPS** (servidor virtual com acesso root via SSH). Hospedagem **compartilhada** (o plano de e-mail/site institucional mais comum e barato da Hostinger, com cPanel/hPanel de "site") normalmente não permite instalar Docker nem rodar um processo em segundo plano como o worker.

Como descobrir qual você tem, no [hPanel](https://hpanel.hostinger.com):

- Se existe um item de menu **"VPS"** na barra lateral, com um servidor listado (IP, sistema operacional, botão de "Acessar via SSH" ou "Console") → você tem uma **VPS**. Siga a seção 3 abaixo.
- Se o que existe é **"Hospedagem"**/"Websites" com gerenciador de arquivos, "Bancos de dados MySQL" e sem nenhuma opção de SSH com acesso root → você tem **hospedagem compartilhada**. Veja a seção 5 ("Alternativa sem VPS") antes de continuar — o caminho é diferente.

Na dúvida, o teste definitivo: tente abrir um terminal SSH com as credenciais da Hostinger (`ssh usuario@seu-ip`) e rodar `docker --version`. Numa VPS isso funciona (ou funciona depois de instalar o Docker, seção 3.2); numa hospedagem compartilhada, o acesso SSH costuma nem existir, ou existir só dentro de uma jail sem permissão de instalar nada.

## 1. Publicar o frontend na Vercel

O frontend (`frontend/`) é um build estático (Vite) — a Vercel reconhece o projeto automaticamente.

### 1.1. Importar o projeto

1. Em [vercel.com](https://vercel.com), **Add New → Project**, e importe o repositório GitHub `app_tarefas` (o mesmo já publicado — ver README).
2. Em **"Root Directory"**, aponte para `frontend` (não a raiz do repositório — é aí que fica o `package.json` do frontend).
3. A Vercel detecta "Vite" automaticamente e preenche:
   - Build Command: `npm run build`
   - Output Directory: `dist`
   Se ela não detectar sozinha, preencha esses dois campos manualmente.

### 1.2. Configurar `VITE_API_URL`

Antes (ou depois) do primeiro deploy, em **Project Settings → Environment Variables**, adicione:

```
VITE_API_URL=https://api.seudominio.com
```

para o ambiente **Production** (e também **Preview**, se quiser que branches/PRs apontem para a mesma API — ou deixe Preview sem essa variável se preferir que previews continuem sem backend configurado). Esse é exatamente o `VITE_API_URL` que `frontend/src/api/cliente.ts` e `frontend/src/api/tempoReal.ts` já leem (ver `frontend/.env.example`) — sem ela, o build usaria o proxy `/api`/`/ws` do Vite, que só existe em `npm run dev` e não faz sentido num build estático publicado.

Você ainda não tem `https://api.seudominio.com` no ar neste ponto (isso é a seção 3) — tudo bem, configure o valor mesmo assim; a Vercel só usa a variável no *build*, então um redeploy (Deployments → ⋯ → Redeploy) depois que o backend estiver de pé é o suficiente para "ligar" a integração, sem precisar reimportar o projeto.

### 1.3. Deploy

Clique em **Deploy**. Em poucos minutos a Vercel devolve uma URL (`algumacoisa.vercel.app`, ou o seu domínio próprio se você configurar um em **Project Settings → Domains**). Guarde essa URL — o backend (seção 3.4) precisa saber exatamente qual é, para liberar CORS.

Neste ponto o frontend carrega, mas login e tudo o mais ainda falha (a API não existe ainda). Isso é esperado — siga para a seção 3.

## 2. DNS: apontar o subdomínio da API para a Hostinger

Você já tem um domínio apontando para a Hostinger. Falta um registro para o subdomínio da API — no painel de DNS da Hostinger (hPanel → Domínios → [seu domínio] → DNS/Nameservers):

```
Tipo   Nome   Aponta para           TTL
A      api    <IP público da VPS>   automático (ou 3600)
```

Depois de criar, a propagação costuma levar de alguns minutos a algumas horas; confirme com `nslookup api.seudominio.com` (ou `ping`) antes de seguir para o Certbot/Caddy na seção 3.3 — pedir um certificado HTTPS para um domínio que ainda não resolve para o IP certo falha.

## 3. Publicar o backend na VPS da Hostinger

### 3.1. Acessar a VPS

```bash
ssh root@<IP público da VPS>
```

(A Hostinger mostra o IP e as credenciais iniciais no hPanel, em VPS → seu servidor → Visão geral. Se for a primeira vez, ela geralmente força a troca de senha no primeiro acesso.)

### 3.2. Instalar Docker

Se `docker --version` ainda não funciona:

```bash
curl -fsSL https://get.docker.com | sh
```

(Script oficial da Docker Inc., cobre Ubuntu/Debian, que é a imagem mais comum nas VPS da Hostinger. Confirme a distribuição com `cat /etc/os-release` se tiver dúvida.) O plugin `docker compose` (sem hífen) já vem junto desse script nas versões atuais do Docker — confirme com `docker compose version`.

### 3.3. Instalar o Caddy (proxy reverso + HTTPS automático)

A API precisa responder em `https://api.seudominio.com`, não em `http://IP:8000` — e o Web Push (Etapa 7.3) exige HTTPS de verdade, não autoassinado. [Caddy](https://caddyserver.com) foi escolhido aqui (em vez de nginx + Certbot manual) porque emite e renova o certificado Let's Encrypt sozinho, com uma configuração de poucas linhas — para um servidor só, é a opção com menos partes móveis para manter:

```bash
sudo apt update
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

Configure o site em `/etc/caddy/Caddyfile` (substitua o conteúdo pelo abaixo):

```
api.seudominio.com {
    reverse_proxy localhost:8000
}
```

É só isso — o `reverse_proxy` do Caddy já repassa o upgrade de conexão do WebSocket (`GET /ws/quadros/{id}`) automaticamente, sem configuração extra, e o certificado HTTPS é emitido e renovado sozinho na primeira requisição. Aplique com:

```bash
sudo systemctl reload caddy
```

### 3.4. Clonar o repositório e configurar o `.env`

```bash
git clone https://github.com/<seu-usuario>/app_tarefas.git
cd app_tarefas
cp backend/.env.example backend/.env
```

Edite `backend/.env` (`nano backend/.env`) e ajuste, no mínimo:

```
CHAVE_SECRETA=<gere com: python3 -c "import secrets; print(secrets.token_hex(32))">
CHAVE_INTERNA=<gere outra, do mesmo jeito -- diferente da CHAVE_SECRETA>
VAPID_PUBLIC_KEY=<gerada com o comando `vapid`, ver comentário no próprio .env.example>
VAPID_PRIVATE_KEY=<idem>
ORIGENS_PERMITIDAS_CORS=https://algumacoisa.vercel.app
COOKIE_ENTRE_SITES=true
```

Alguns pontos que não são óbvios:

- `DATABASE_URL` **não precisa mudar** — o valor do `.env.example` já aponta para `banco:5432`, o nome do serviço Postgres dentro da rede do `docker-compose.yml` (não é `localhost`; ver o comentário nesse arquivo).
- `ORIGENS_PERMITIDAS_CORS` é a URL da Vercel da seção 1.3, **exatamente como o navegador a vê** (com `https://`, sem barra no final). Se você tiver mais de uma (ex.: domínio próprio + o `.vercel.app` de fallback), separe por vírgula: `https://kanban.seudominio.com,https://algumacoisa.vercel.app`.
- `COOKIE_ENTRE_SITES=true` só faz sentido a partir do momento em que `api.seudominio.com` já está atrás do HTTPS do Caddy (seção 3.3) — é o que permite `SameSite=None; Secure` no cookie de sessão (ver `app/rotas/auth.py`); sem HTTPS, o navegador simplesmente recusaria esse cookie, e o login pareceria não funcionar.
- As chaves VAPID: gere com o par de comandos do próprio comentário em `backend/.env.example` (`vapid --gen` e depois `vapid --applicationServerKey`) — pode gerar localmente na sua máquina (dentro do `venv` do backend) e só colar os valores aqui; não precisam ser geradas na VPS.

### 3.5. Restringir as portas publicadas (segurança)

O `docker-compose.yml` de desenvolvimento publica a API (`8000`) e o Postgres (`5432`) em todas as interfaces de rede — correto numa máquina local, errado numa VPS com IP público (exporia o banco de dados direto para a internet, sem passar pelo Caddy). Use o override já preparado para isso, [`docker-compose.prod.yml`](../docker-compose.prod.yml), que restringe as duas portas a `127.0.0.1` (só o próprio servidor alcança; o Caddy, rodando fora do Docker nessa mesma máquina, continua alcançando a API por `localhost:8000` normalmente).

> Regra de firewall (`ufw`) sozinha **não basta** aqui: o Docker manipula o `iptables` diretamente e, em muitas configurações padrão, ignora as regras do `ufw` para as portas que ele mesmo publica. Restringir a publicação da porta em si (o que o override faz) é o jeito confiável de garantir isso — configure o `ufw` (`ufw allow 22,80,443/tcp`, `ufw enable`) como uma segunda camada, não como a única.

### 3.6. Subir os serviços e aplicar as migrações

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec api alembic revision --autogenerate -m "schema inicial"
docker compose exec api alembic upgrade head
```

(A mesma dança de duas etapas do Alembic descrita no README para rodar local — só muda o `-f` extra apontando para o override de produção.)

Confira que subiu:

```bash
curl https://api.seudominio.com/saude
```

### 3.7. Religar a Vercel

Volte à seção 1.2: se ainda não redeployou o frontend depois de configurar `VITE_API_URL`, faça isso agora (Deployments → ⋯ → Redeploy) — é nesse redeploy que o build passa a apontar de fato para `https://api.seudominio.com`.

Abra a URL da Vercel, crie uma conta pela tela de login e confirme que o quadro carrega, cartões arrastam e o WebSocket conecta (ícone/console sem erro de `wss://`). Se o login "não pegar" (a resposta de `/auth/login` vem 200, mas a chamada seguinte diz não autenticada), revise `COOKIE_ENTRE_SITES=true` no `.env` do backend e reinicie o serviço `api` (`docker compose restart api`) — é o sintoma exato descrito no comentário desse campo em `app/config.py`.

### 3.8. Atualizando depois do primeiro deploy

Para publicar mudanças de código futuras no backend:

```bash
cd app_tarefas
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec api alembic upgrade head
```

A Vercel já faz isso sozinha para o frontend: todo push na branch conectada (`master`, por padrão) dispara um novo deploy automaticamente.

## 4. Checklist final

- [ ] `https://api.seudominio.com/saude` responde `200`.
- [ ] `https://algumacoisa.vercel.app` (ou seu domínio) abre a tela de login.
- [ ] Criar conta + criar quadro + criar lista + criar cartão funcionam de ponta a ponta.
- [ ] Arrastar um cartão persiste (recarregar a página mantém a nova posição).
- [ ] Abrir o mesmo quadro em duas abas: mover um cartão numa aba atualiza a outra em tempo real (confirma o WebSocket `wss://api.seudominio.com/ws/quadros/...`).
- [ ] Definir um prazo próximo com aviso prévio curto e aceitar a permissão de notificação do navegador: o push chega (confirma HTTPS + VAPID + worker rodando).

## 5. Alternativa sem VPS (hospedagem compartilhada da Hostinger)

Se a seção 0 concluiu que você só tem hospedagem compartilhada: ela não roda Docker nem um processo Python de longa duração (o worker precisa ficar acordado, consultando o banco a cada minuto — não é algo que um PHP/CGI tradicional sob Apache suporta), então **este backend não roda diretamente nela**. Duas saídas realistas, sem precisar contratar/trocar de VPS:

1. **Hospede o backend em outro provedor com camada gratuita** (Railway, Render ou Fly.io são os mais diretos para "Dockerfile + Postgres gerenciado") e deixe a Hostinger só como está hoje, sem envolvimento no backend. O frontend na Vercel aponta `VITE_API_URL` para esse provedor, exatamente como apontaria para a Hostinger — nada na seção 1 muda.
2. **Faça upgrade para o plano VPS da Hostinger** (eles costumam oferecer migração dentro do próprio hPanel) e siga a seção 3 normalmente.

Não há uma forma segura de rodar o Postgres + worker "encaixados" na hospedagem compartilhada — evite a tentação de trocar o worker por um cron job do cPanel chamando um script PHP: o resto da arquitetura (SQLAlchemy, o processo Python do worker, o Postgres) não tem equivalente ali, e replicar só a notificação sem o resto do backend não entrega o app.
