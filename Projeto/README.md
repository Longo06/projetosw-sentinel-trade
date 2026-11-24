# SentinelTrade

Plataforma **simulada** de negociação de ativos financeiros (ações, ETFs e FIIs) da corretora fictícia Orion Capital. Projeto acadêmico (N1/N2) de especificação, modelagem e implementação de um sistema de trade de alta criticidade.

> **Aviso:** não há bolsa real, dinheiro real nem dados pessoais reais. Todos os ativos, contas e cotações são simulados. O sistema não conecta a nenhuma bolsa, não movimenta dinheiro real e não deve ser usado para negociação financeira.

## Sumário

1. [Visão do projeto](#visão-do-projeto)
2. [Integrantes](#integrantes)
3. [Tecnologias e arquitetura](#tecnologias-e-arquitetura)
4. [Estrutura do repositório](#estrutura-do-repositório)
5. [Documentação](#documentação)
6. [Instalação e execução](#instalação-e-execução)
7. [Contas fictícias para demonstração](#contas-fictícias-para-demonstração)
8. [Fluxo de autenticação](#fluxo-de-autenticação)
9. [Principais endpoints](#principais-endpoints)
10. [Regras implementadas](#regras-implementadas)
11. [Testes](#testes)
12. [Segurança e boas práticas](#segurança-e-boas-práticas)
13. [Limitações conhecidas e passos externos](#limitações-conhecidas-e-passos-externos)
14. [Status](#status)

## Visão do projeto

O SentinelTrade permite que investidores autorizados:

- autentiquem-se com senha e MFA por e-mail;
- consultem cotações e sua carteira (posições e saldo);
- enviem ordens de compra e venda, confirmadas por PIN transacional;
- cancelem ordens e acompanhem seu ciclo de vida (criada, validada, enviada, parcialmente executada, executada, rejeitada, cancelada);
- recebam notificações e consultem o histórico de operações.

Administradores gerenciam investidores, ativos e limites de risco; auditores consultam registros de auditoria imutáveis.

Por ser um sistema crítico, o projeto prioriza **segurança, consistência de dados, resiliência (timeout, retentativa, idempotência, fila, indisponibilidade segura), auditabilidade e rastreabilidade**.

## Integrantes

| Nome | RA |
|---|---|
| Gustavo Francisco Toito | 10438660 |
| Guilherme Longo | 10736785 |
| Leonardo Assis | 10742770 |

## Tecnologias e arquitetura

| Componente | Tecnologia |
|---|---|
| Linguagem / framework | Python 3.11+ · FastAPI (API REST e documentação OpenAPI) |
| Banco de dados | SQLAlchemy 2 + SQLite por padrão (PostgreSQL configurável via `DATABASE_URL`) |
| Fila de mensagens | Não implementada: notificações são gravadas no banco e exibidas no console (ver [limitações](#limitações-conhecidas-e-passos-externos)) |
| Serviço de cotações (externo) | Adaptador simulado (`SimulatedQuoteProvider`) |
| Corretora / sandbox (externo) | Adaptador simulado (`SimulatedBroker`) |
| Serviço de e-mail (externo) | Simulado: o código MFA é devolvido na resposta apenas em desenvolvimento |
| Testes | pytest + `TestClient` do FastAPI (httpx) |
| Modelagem UML | Draw.io (fontes editáveis em `docs/uml/`) |

Módulos do pacote `sentineltrade/`:

- `domain.py`: enums, estados da ordem, transições permitidas e janela de negociação.
- `models.py`: persistência relacional.
- `services.py`: regras de negócio e casos de uso.
- `integrations.py`: abstrações e integrações simuladas.
- `security.py`: hash de credenciais e token assinado.
- `schemas.py`: validação dos dados de entrada.
- `api.py`: interface HTTP, validação e autorização.
- `config.py` e `db.py`: configuração (variáveis de ambiente) e conexão com o banco.

## Estrutura do repositório

```text
Projeto/
├── main.py                  # inicialização da API
├── seed.py                  # dados fictícios de demonstração
├── requirements.txt
├── .env.example             # nomes das variáveis de ambiente (sem segredos reais)
├── sentineltrade/           # código-fonte da aplicação
├── tests/                   # testes automatizados
└── docs/                    # requisitos, diagramas e notas de implementação
```

## Documentação

Toda a documentação fica na pasta [`docs/`](docs/):

| Documento | Conteúdo |
|---|---|
| [requisitos_sentineltrade.md](docs/requisitos_sentineltrade.md) | Visão, atores, requisitos funcionais e não funcionais, regras de negócio, restrições técnicas, critérios de aceitação, casos de uso, pensamento sistêmico e matriz de rastreabilidade |
| [IMPLEMENTACAO_PYTHON.md](docs/IMPLEMENTACAO_PYTHON.md) | Mapeamento entre requisitos e endpoints, decisões e limites da versão |
| Diagrama de casos de uso (imagem N1) | [Visualizar diagrama](docs/diagrama_casos_de_uso.png) |
| Diagramas UML editáveis | [Fontes Draw.io e instruções](docs/uml/README.md) |
| [ARQUIVOS_IMPLEMENTACAO.md](ARQUIVOS_IMPLEMENTACAO.md) | Lista dos arquivos da implementação |

## Instalação e execução

Clone o repositório e entre na pasta do projeto:

```bash
git clone <url-do-repositorio>
cd <pasta-do-repositorio>/Projeto
```

### Windows / PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python seed.py
python main.py
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed.py
python main.py
```

A API estará em `http://127.0.0.1:8000`. Documentação interativa: `http://127.0.0.1:8000/docs`.

Edite o `.env` com os valores locais (**nunca versione o `.env`**). Variáveis lidas pela aplicação:

| Variável | Descrição |
|---|---|
| `APP_ENV` | `development` (padrão) exibe o código MFA em `debug_code`. Qualquer outro valor o omite e exige `SECRET_KEY` forte. |
| `DATABASE_URL` | URL do banco (SQLite por padrão; exemplo PostgreSQL em `.env.example`). |
| `SECRET_KEY` | Chave de assinatura dos tokens. Fora de `development`, a aplicação **não inicia** com a chave de exemplo ou com menos de 32 caracteres. |

> No Windows, o pacote `tzdata` (incluído em `requirements.txt`) é necessário para o fuso `America/Sao_Paulo`.

## Contas fictícias para demonstração

Criadas por `python seed.py` (que só executa com `APP_ENV=development`):

| Perfil | E-mail | Senha | PIN |
|---|---|---|---|
| Administrador | admin@sentineltrade.local | Admin123! | 1234 |
| Investidor | investidor@sentineltrade.local | Invest123! | 1234 |
| Auditor | auditor@sentineltrade.local | Audit123! | 1234 |
| Analista de Risco | risco@sentineltrade.local | Risk123! | 1234 |

O investidor demo começa com saldo de R$ 100.000,00 e sem posições; para vender, compre antes e simule a execução com `broker-update` (como administrador).

O código MFA aparece no campo `debug_code` somente quando `APP_ENV=development`. Em produção esse campo é omitido; o envio real por e-mail ainda precisa ser conectado.

## Fluxo de autenticação

1. `POST /api/auth/login` com `email` e `password`.
2. Copie `challenge_id` e `debug_code` (apenas desenvolvimento).
3. `POST /api/auth/verify-mfa` com `challenge_id` e `code`.
4. Use `access_token` no cabeçalho `Authorization: Bearer <token>`.

## Principais endpoints

| Método | Endpoint | Acesso |
|---|---|---|
| GET | `/health` | Público |
| POST | `/api/investors` | Público (cadastro de investidor) |
| GET | `/api/investors/me` | Autenticado |
| PATCH | `/api/investors/{id}` | Administrador |
| POST | `/api/auth/login` | Público |
| POST | `/api/auth/verify-mfa` | Público |
| GET | `/api/portfolio` | Autenticado (carteira do próprio usuário) |
| GET | `/api/assets` | Autenticado |
| POST/PATCH | `/api/assets` e `/api/assets/{id}` | Administrador |
| POST | `/api/orders` | Autenticado (exige PIN e `idempotency_key`) |
| GET | `/api/orders` | Ordens do próprio usuário |
| GET | `/api/orders/{id}` | Dono da ordem; Administrador, Auditor e Analista de Risco também podem consultar |
| POST | `/api/orders/{id}/cancel` | Dono da ordem |
| POST | `/api/orders/{id}/broker-update` | Administrador / Analista de Risco (simula o retorno da corretora) |
| GET | `/api/history` | Histórico de ordens do próprio usuário |
| GET | `/api/notifications` | Notificações do próprio usuário |
| GET | `/api/audit` | Administrador / Auditor |
| PATCH | `/api/admin/investors/{id}/risk-limits` | Administrador |

As listagens (`orders`, `history`, `notifications`, `audit`) aceitam `limit` (1–500, padrão 100) e, em `orders` e `history`, também `offset`.

## Regras implementadas

- Hash PBKDF2-HMAC-SHA256 com salt para senha e PIN.
- MFA de seis dígitos, validade de cinco minutos e até três tentativas; um novo login invalida desafios anteriores.
- Bloqueio de 15 minutos após três falhas consecutivas de senha, PIN ou MFA; conta bloqueada não autentica nem opera.
- Estados de ordem com transições explicitamente permitidas, incluindo execuções parciais sucessivas.
- Retornos da corretora validados: `FILLED` exige a quantidade total, `PARTIALLY_FILLED` exige quantidade parcial, `REJECTED` não pode ter execução; mensagens repetidas são idempotentes.
- Idempotência por investidor + chave única.
- Saldo reservado para compra e posição reservada para venda; no cancelamento de ordem parcialmente executada, só o saldo não executado é liberado.
- Limites por ordem e exposição diária configuráveis por investidor (a exposição nunca pode ser menor que o limite por ordem).
- Janela de negociação: dias úteis, 10:00–17:55, America/Sao_Paulo (feriados não são considerados).
- Cotação com validade máxima de dez segundos. O provedor simulado carimba a cotação no instante da consulta; para simular cotação defasada use `SimulatedQuoteProvider(fresh=False)`.
- Auditoria append-only pela aplicação e eventos de transição.
- Autorização por perfil e isolamento de ordens/carteira por investidor (ordem de outro investidor responde 404).
- Valores monetários normalizados para centavos.

## Testes

```bash
pytest -q
```

Os testes usam um SQLite temporário (nunca o banco local) e cobrem hash de credenciais, token assinado, máquina de estados, janela de negociação, autenticação/MFA/bloqueio, envio e cancelamento de ordens, execuções parciais, idempotência, limites de risco e autorização na API.

## Segurança e boas práticas

- **Nunca** versionar senhas, tokens, chaves de API ou dados sensíveis. Use variáveis de ambiente; o arquivo `.env.example` traz apenas os nomes das variáveis, sem valores reais.
- O `.env` e demais arquivos sensíveis constam no `.gitignore`.
- Mensagens de commit descritivas e coerentes com a evolução do projeto.
- Não insira dados pessoais ou financeiros reais; o banco e os dados são fictícios.

## Limitações conhecidas e passos externos

1. **E-mail real:** MFA é simulado; implementar SMTP/provedor e retirar `debug_code` antes de publicar.
2. **Corretora sandbox:** o adaptador `SimulatedBroker` apenas aceita/cancela localmente. Conectar sandbox real exige credenciais e documentação do provedor.
3. **Cotações externas:** `SimulatedQuoteProvider` usa os preços persistidos. Integrar API externa exige endpoint, chave e termos do provedor.
4. **Fila assíncrona:** notificações são registradas no banco e exibidas no console. Para produção, integrar Celery/RQ + Redis/RabbitMQ.
5. **Retentativas e timeouts:** `max_retries`, `quote_timeout_seconds` e `broker_timeout_seconds` existem em `config.py`, mas só serão aplicados quando houver integrações reais.
6. **TLS e implantação:** executar atrás de proxy HTTPS com certificados válidos; configurar PostgreSQL, backups, monitoramento e gestão de segredos.
7. **Segurança de produção:** trocar o token didático por OAuth2/JWT com rotação/expiração e refresh, rate limiting, política de senha, proteção CSRF conforme cliente, e revisar o modelo de bloqueio.
8. **Concorrência financeira:** habilitar transações/locks adequados no PostgreSQL e testes concorrentes antes de qualquer uso além da simulação acadêmica. O SQLite grava valores monetários como ponto flutuante; use PostgreSQL (`NUMERIC`) para precisão exata.
9. **Custos e feriados:** corretagem/taxas (RN-03) e calendário de feriados (RN-06) não são modelados.

## Status

Fase atual: **especificação, modelagem e implementação acadêmica simulada** — requisitos, casos de uso, fontes editáveis dos diagramas UML e API em Python com testes automatizados. Integrações externas reais continuam fora do escopo (ver limitações).
