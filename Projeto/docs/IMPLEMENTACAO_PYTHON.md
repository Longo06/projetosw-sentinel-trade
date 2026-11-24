# Implementação Python — SentinelTrade

## Mapeamento dos requisitos

| Requisito / regra | Implementação |
|---|---|
| RF-01 | `POST /api/investors`, `GET /api/investors/me`, `PATCH /api/investors/{id}` |
| RF-02 / RN-02 / RN-12 | `/api/auth/login`, `/api/auth/verify-mfa`, `MfaChallenge`, bloqueio após falhas |
| RF-03 / RN-03 / RN-04 | `GET /api/portfolio`, reservas de saldo e posição |
| RF-04 / RN-11 | `GET /api/assets`, `QuoteProvider`, cotação simulada com validade máxima de 10 s |
| RF-05 / RN-05 / RN-06 | `POST /api/orders`, validações de PIN, limites e horário |
| RF-06 / RN-07 | `POST /api/orders/{id}/cancel` |
| RF-07 / RN-13 | validações em `services.place_order` e máquina de estados em `domain.py` |
| RF-08 | adaptador `Broker` / `SimulatedBroker` e endpoint de atualização |
| RF-09 / RF-10 | consulta de ordens e histórico |
| RF-11 | registros de notificação persistidos e gateway de console |
| RF-12 / RF-13 | `AuditEvent`, `audit()` e `GET /api/audit` |
| RF-14 | `PATCH /api/admin/investors/{id}/risk-limits` |
| RF-15 | criação, consulta, atualização e desativação de ativos |

## Decisões e limites da versão

- O projeto usa SQLite para execução imediata; a variável `DATABASE_URL` permite apontar para PostgreSQL com o driver apropriado.
- A autenticação usa token HMAC didático, hash PBKDF2 e MFA simulado. Não equivale a um provedor de identidade de produção.
- A cotação e a corretora são simuladas. O envio da ordem retorna aceite, não execução; os retornos de execução são simulados pelo endpoint protegido de atualização.
- O provedor de cotações simulado carimba a cotação no instante da consulta (feed "ao vivo"); assim a regra de validade de 10 s (RN-11) só rejeita ordens quando se simula defasagem com `SimulatedQuoteProvider(fresh=False)`.
- Retornos da corretora são validados antes de alterar saldo ou carteira: `FILLED` exige a quantidade total, `PARTIALLY_FILLED` aceita execuções parciais sucessivas e `REJECTED` não pode ter execução (RN-09, RN-13). No cancelamento de ordem parcialmente executada só o saldo não executado é liberado (RN-07).
- O bloqueio de 15 minutos (RN-12) vale para login, PIN e MFA, e uma conta bloqueada também não conclui MFA nem envia ordens.
- Fora de `APP_ENV=development` a aplicação não inicia com `SECRET_KEY` de exemplo ou com menos de 32 caracteres, e `seed.py` se recusa a rodar.
- As notificações são gravadas no banco e impressas no console. Não há envio SMTP real.
- A fila é representada por persistência de notificações pendentes; não há worker externo nesta entrega.
- As retentativas exponenciais de integração e os limites de timeout estão documentados como ponto de integração; não foram simulados por um broker real.
- TLS deve ser configurado no proxy/servidor de implantação. Não se deve expor o servidor local diretamente à internet.
- O banco e os dados são fictícios. Não inserir dados pessoais ou financeiros reais.

## Verificação

Execute `pytest -q` na raiz do projeto. Os testes usam um SQLite temporário e cobrem hash de credenciais, assinatura de token, máquina de estados, janela de negociação (RN-06), autenticação com MFA e bloqueio (RN-12), envio, cancelamento e idempotência de ordens (RN-08), limites de risco (RN-05), execuções parciais e retornos da corretora, além de autorização por perfil na API.
