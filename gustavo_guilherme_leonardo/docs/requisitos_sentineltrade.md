# SentinelTrade — Engenharia de Requisitos

> Legenda: itens marcados **(proposto)** são valores sugeridos que a equipe deve validar. O diagrama UML e a estrutura do repositório estão em documentos separados; aqui constam os casos de uso textuais que os alimentam.

## 1. Visão e objetivo

O SentinelTrade é uma plataforma simulada de negociação de ativos financeiros (ações, ETFs e FIIs) da corretora fictícia Orion Capital. Permite que investidores consultem cotações, acompanhem a carteira, enviem e acompanhem ordens de compra e venda e consultem o histórico.

Por ser um sistema de alta criticidade (impacto financeiro, regulatório e reputacional), deve ser seguro, consistente, resiliente, auditável e rastreável. Opera apenas com ativos, contas e cotações **simulados**.

**Escopo:** cadastro, autenticação com MFA, carteira, cotações, ordens (envio, cancelamento, ciclo de vida), notificações, histórico, auditoria e gestão de limites.
**Fora do escopo:** bolsa real, dinheiro real, liquidação financeira real.

## 2. Atores

| ID | Ator | Tipo | Descrição |
|---|---|---|---|
| AT-01 | Investidor | Primário | Consulta carteira, cotações e histórico; envia e cancela ordens. |
| AT-02 | Administrador | Primário | Gerencia investidores, limites de risco e parâmetros operacionais. |
| AT-03 | Auditor | Primário | Consulta registros de auditoria (somente leitura). |
| AT-04 | Serviço de Cotações | Secundário | Sistema externo que fornece cotações. |
| AT-05 | Corretora / Sandbox | Secundário | Sistema externo que recebe ordens e devolve estados de execução. |
| AT-06 | Serviço de E-mail | Secundário | Envia o código MFA e as notificações. |

> Os provedores concretos de AT-04, AT-05 e AT-06 ainda devem ser definidos (ver seção 10).

## 3. Requisitos Funcionais

| ID | Nome | Descrição |
|---|---|---|
| RF-01 | Cadastro e gestão de investidores | Cadastrar, consultar e atualizar dados de investidores e suas contas. |
| RF-02 | Autenticação com MFA | Autenticar com senha e segundo fator enviado por e-mail. |
| RF-03 | Consulta de carteira | Consultar posições e saldo disponível. |
| RF-04 | Consulta de cotações | Consultar cotações atualizadas via serviço externo. |
| RF-05 | Envio de ordens | Enviar ordens de compra e venda, com confirmação por **PIN transacional**. |
| RF-06 | Cancelamento de ordem | Solicitar cancelamento de ordem em estado cancelável. |
| RF-07 | Validação de ordens | Validar cotação, saldo, posição, horário e limites antes do envio; informar o motivo da rejeição. |
| RF-08 | Integração com corretora | Enviar ordens aprovadas ao ambiente sandbox e receber os retornos de estado. |
| RF-09 | Ciclo da ordem | Registrar e consultar os estados: criada, validada, enviada, parcialmente executada, executada, rejeitada, cancelada. |
| RF-10 | Consulta de histórico | Consultar ordens e operações anteriores. |
| RF-11 | Notificações | Notificar execução, rejeição, cancelamento e indisponibilidade de integração. |
| RF-12 | Auditoria | Registrar eventos de segurança e de operações (autenticação, alteração de dados, ordens). |
| RF-13 | Consulta de auditoria | Permitir que o Auditor consulte e filtre registros de auditoria. |
| RF-14 | Gestão de limites de risco | Permitir que o Administrador defina limites por investidor (por ordem, exposição diária). |

**Esclarecimento senha × PIN:** a *senha* (com MFA por e-mail) autentica o acesso; o *PIN transacional* é uma confirmação adicional exigida apenas para enviar ordens (RF-05). Ambos são armazenados com hash (RNF-01).

## 4. Requisitos Não Funcionais

### 4.1 Segurança

| ID | Nome | Descrição |
|---|---|---|
| RNF-01 | Proteção de credenciais | Senhas e PINs armazenados com hash seguro (ex.: bcrypt/Argon2), nunca em texto puro. |
| RNF-02 | Autenticação multifator | Código MFA de 6 dígitos por e-mail, validade de 5 min, máx. 3 tentativas. |
| RNF-03 | Controle de acesso | Acesso por perfil (Investidor, Administrador, Auditor); investidor só acessa seus próprios dados. |
| RNF-04 | Validação de entradas | Validar entradas, tratar exceções sem expor detalhes internos e prevenir injeção (consultas parametrizadas). |
| RNF-05 | Comunicação segura | TLS em toda comunicação cliente-servidor e entre componentes. |
| RNF-06 | Proteção contra duplicidade | Chave de idempotência por ordem; reenvio da mesma solicitação não gera nova ordem. |
| RNF-07 | Auditoria protegida | Registros de auditoria append-only, sem alteração/exclusão por usuários comuns; retenção mínima de 5 anos. |

### 4.2 Resiliência

| ID | Nome | Descrição |
|---|---|---|
| RNF-08 | Timeout de integração | Cotações: 3 s; corretora: 5 s. |
| RNF-09 | Retentativa controlada | Até 3 retentativas com backoff exponencial (1 s, 2 s, 4 s), sempre com a mesma chave de idempotência. |
| RNF-10 | Processamento assíncrono | Envio à corretora e notificações via fila de mensagens ou mecanismo equivalente. |
| RNF-11 | Indisponibilidade segura | Com integração crítica indisponível, ordens não são enviadas; o investidor é informado. |
| RNF-12 | Consistência de dados | Saldo, carteira e ordem atualizados atomicamente (transação) ou compensados em falha. |

### 4.3 Qualidade

| ID | Nome | Descrição |
|---|---|---|
| RNF-13 | Confidencialidade | Dados financeiros acessíveis apenas a usuários autorizados. |
| RNF-14 | Integridade | Ordens, posições, saldos e auditoria protegidos contra alteração indevida. |
| RNF-15 | Disponibilidade | Meta de 99,5% no horário de negociação, exceto manutenção planejada e falhas de serviços externos. |
| RNF-16 | Desempenho | Operações interativas com p95 ≤ 2 s, sem bloqueio por integrações externas (uso de fila). |
| RNF-17 | Rastreabilidade | Toda operação relevante vinculada a investidor, ordem e eventos registrados. |
| RNF-18 | Manutenibilidade | Código e documentação organizados; cobertura de testes automatizados nas regras de negócio críticas. |

## 5. Regras de Negócio

| ID | Regra | Descrição |
|---|---|---|
| RN-01 | Autenticação obrigatória | Acesso a dados ou operações financeiras exige autenticação prévia. |
| RN-02 | MFA | O segundo fator deve ser validado para concluir o login. |
| RN-03 | Saldo para compra | Compra só é aprovada com saldo ≥ quantidade × preço + custos. |
| RN-04 | Posição para venda | Venda só é aprovada com quantidade disponível na carteira (descontadas ordens de venda abertas). |
| RN-05 | Limites de risco | Valor por ordem ≤ R$ 50.000 e exposição diária ≤ R$ 200.000 por investidor (ajustáveis pelo Administrador). |
| RN-06 | Horário de negociação | Ordens aceitas em dias úteis, 10:00–17:55 (fuso America/Sao_Paulo). |
| RN-07 | Ordem cancelável | Cancelamento permitido nos estados criada, validada, enviada e parcialmente executada (apenas o saldo não executado). |
| RN-08 | Não duplicidade | Uma mesma solicitação resulta em no máximo um envio efetivo. |
| RN-09 | Integridade da ordem | Ordem rejeitada nunca é tratada como executada. |
| RN-10 | Rastreabilidade | Operações relevantes mantêm vínculo com investidor, ordem e eventos. |
| RN-11 | Frescor da cotação | Cotação com mais de 10 s de idade invalida a validação da ordem. |
| RN-12 | Bloqueio de acesso | Após 3 falhas consecutivas de senha, PIN ou MFA, a conta é bloqueada por 15 min. |
| RN-13 | Ciclo de vida da ordem | Transições permitidas: criada→validada→enviada→(parcialmente executada)→executada; criada/validada→rejeitada; criada/validada/enviada/parcial→cancelada. Estados finais não retornam. |

## 6. Restrições Técnicas

| ID | Restrição | Descrição |
|---|---|---|
| RT-01 | Integração de cotações | Uso de serviço externo de cotações. |
| RT-02 | Corretora em sandbox | Envio de ordens somente a ambiente sandbox. |
| RT-03 | Serviço de e-mail | Uso de serviço de e-mail para MFA e notificações. |
| RT-04 | Comunicação segura | TLS em comunicações que transportem dados protegidos. |
| RT-05 | Segredos fora do repositório | Tokens, chaves e credenciais via variáveis de ambiente (`.env.example` sem valores reais). |
| RT-06 | Controle de versão | Repositório Git com documentação organizada e commits coerentes. |
| RT-07 | Dados simulados | Nenhum dinheiro, conta ou dado pessoal real. |

## 7. Critérios de Aceitação

| ID | Requisito | Critério de aceitação |
|---|---|---|
| CA-01 | RF-01 | É possível cadastrar um investidor e consultar/atualizar seus dados. |
| CA-02 | RF-02 | O login só conclui após validar o código MFA; código expirado ou errado é recusado. |
| CA-03 | RF-03 | O investidor autenticado vê seu saldo e suas posições. |
| CA-04 | RF-04 | A cotação exibida corresponde à retornada pelo serviço externo. |
| CA-05 | RF-05 | Ordem válida é criada e só é confirmada com o PIN correto. |
| CA-06 | RF-06 | Ordem em estado cancelável é cancelada; em estado final, o cancelamento é recusado com motivo. |
| CA-07 | RF-07 | Ordem sem saldo, sem posição, fora do horário, acima do limite ou com cotação vencida é rejeitada com o motivo. |
| CA-08 | RF-08 | Ordem validada é enviada ao sandbox e o retorno atualiza seu estado. |
| CA-09 | RF-09 | O investidor consulta o estado atual e o histórico de transições da ordem. |
| CA-10 | RF-10 | O investidor consulta suas ordens e operações anteriores, sem ver as de outros. |
| CA-11 | RF-11 | Execução, rejeição, cancelamento e indisponibilidade geram notificação. |
| CA-12 | RF-12 | Login, falhas de login, alteração de dados e eventos de ordem geram registro de auditoria. |
| CA-13 | RNF-06 | O reenvio da mesma solicitação não gera segunda ordem nem segundo envio. |
| CA-14 | RNF-08/09 | Falha temporária respeita o timeout e no máximo 3 retentativas. |
| CA-15 | RNF-11 | Com integração crítica fora do ar, a ordem não é processada e o investidor é informado. |
| CA-16 | RNF-12 | Falha durante o processamento não deixa saldo, carteira e ordem inconsistentes. |
| CA-17 | RNF-17 | Dada uma ordem, é possível listar investidor e todos os eventos relacionados. |
| CA-18 | RNF-18 | O repositório possui organização e documentação que permitem que um novo integrante execute e teste o projeto. |
| CA-19 | RF-13 | O Auditor filtra registros por período, investidor e tipo de evento; um investidor comum não acessa a auditoria. |
| CA-20 | RF-14 | O Administrador altera limites e a alteração passa a valer nas ordens seguintes e é auditada. |
| CA-21 | RN-12 | A terceira falha consecutiva bloqueia a conta por 15 min. |

## 8. Casos de Uso

### 8.1 Lista

| ID | Caso de uso | Ator primário | Atores secundários | Requisitos |
|---|---|---|---|---|
| UC-01 | Gerenciar investidor | Administrador | — | RF-01 |
| UC-02 | Autenticar investidor | Investidor | Serviço de E-mail | RF-02 |
| UC-03 | Consultar carteira | Investidor | — | RF-03 |
| UC-04 | Consultar cotações | Investidor | Serviço de Cotações | RF-04 |
| UC-05 | Enviar ordem de compra/venda | Investidor | Serviço de Cotações, Corretora | RF-05, RF-07, RF-08 |
| UC-06 | Cancelar ordem | Investidor | Corretora | RF-06 |
| UC-07 | Consultar status da ordem | Investidor | — | RF-09 |
| UC-08 | Consultar histórico | Investidor | — | RF-10 |
| UC-09 | Notificar investidor | Corretora (evento) | Serviço de E-mail | RF-11 |
| UC-10 | Consultar auditoria | Auditor | — | RF-12, RF-13 |
| UC-11 | Atualizar estado da ordem | Corretora | — | RF-08, RF-09 |
| UC-12 | Gerenciar limites de risco | Administrador | — | RF-14 |

### 8.2 Descrições expandidas

#### UC-02 — Autenticar investidor
- **Sumário:** o Investidor acessa o sistema com senha e segundo fator.
- **Ator primário:** Investidor. **Secundário:** Serviço de E-mail.
- **Precondições:** investidor cadastrado e conta não bloqueada.
- **Fluxo principal:**
  1. O Investidor informa e-mail e senha.
  2. O sistema valida as credenciais e envia o código MFA por e-mail.
  3. O Investidor informa o código.
  4. O sistema valida o código, cria a sessão e registra o evento em auditoria.
- **Fluxos de exceção:**
  - 2a. Credenciais inválidas: o sistema informa falha genérica, registra a tentativa e volta ao passo 1.
  - 4a. Código inválido ou expirado: o sistema permite nova tentativa (máx. 3) ou reenvio do código.
  - 4b. Três falhas consecutivas: a conta é bloqueada por 15 min (RN-12) e o evento é auditado.
  - 2b. Serviço de e-mail indisponível: o sistema informa a indisponibilidade e não conclui o login.
- **Pós-condições:** sessão autenticada criada; evento auditado.
- **Regras de negócio:** RN-01, RN-02, RN-12. **RNFs:** RNF-01, RNF-02, RNF-04.

#### UC-05 — Enviar ordem de compra/venda
- **Sumário:** o Investidor cria e confirma uma ordem que é validada e transmitida à corretora.
- **Ator primário:** Investidor. **Secundários:** Serviço de Cotações, Corretora.
- **Precondições:** Investidor autenticado (UC-02).
- **Fluxo principal:**
  1. O Investidor informa ativo, tipo (compra/venda), quantidade e preço/tipo de ordem.
  2. O sistema obtém a cotação atualizada.
  3. O sistema valida saldo ou posição, horário, limites e frescor da cotação.
  4. O sistema apresenta o resumo e solicita o PIN.
  5. O Investidor confirma com o PIN.
  6. O sistema registra a ordem (estado *criada→validada*), reserva saldo ou posição e a coloca na fila de envio com chave de idempotência.
  7. O sistema envia a ordem à corretora (estado *enviada*) e informa o Investidor que a ordem foi aceita para processamento.
- **Fluxos alternativos:**
  - 1a. Solicitação repetida com a mesma chave de idempotência: o sistema devolve a ordem já existente, sem criar outra (RN-08).
- **Fluxos de exceção:**
  - 2a. Cotação indisponível ou vencida: o sistema rejeita a solicitação e informa o motivo (RN-11, RNF-11).
  - 3a. Validação falha (RN-03, RN-04, RN-05, RN-06): a ordem é *rejeitada* com o motivo, sem reserva; o caso de uso termina.
  - 5a. PIN incorreto: o sistema pede novamente (máx. 3, depois RN-12).
  - 7a. Corretora indisponível ou em timeout: o sistema executa retentativas controladas (RNF-09); esgotadas, a ordem é *rejeitada*, a reserva é liberada e o Investidor é notificado.
- **Pós-condições:** ordem persistida com estado consistente; saldo/posição reservados ou liberados; eventos auditados; notificação enfileirada.
- **Regras de negócio:** RN-01, RN-03 a RN-06, RN-08, RN-09, RN-11, RN-13. **RNFs:** RNF-06, RNF-08 a RNF-12.

#### UC-06 — Cancelar ordem
- **Sumário:** o Investidor solicita o cancelamento de uma ordem ainda ativa.
- **Ator primário:** Investidor. **Secundário:** Corretora.
- **Precondições:** Investidor autenticado; ordem sua e em estado cancelável (RN-07).
- **Fluxo principal:**
  1. O Investidor seleciona a ordem e solicita o cancelamento.
  2. O sistema verifica o estado atual da ordem.
  3. O sistema solicita o cancelamento à corretora.
  4. A corretora confirma; o sistema marca a ordem como *cancelada*, libera a reserva e audita o evento.
  5. O sistema notifica o Investidor.
- **Fluxos de exceção:**
  - 2a. Ordem em estado final (executada, rejeitada, cancelada): o sistema recusa e informa o motivo.
  - 3a. Ordem executada na corretora durante o pedido: o cancelamento é recusado e a ordem segue como *executada* (a corretora prevalece).
  - 3b. Corretora indisponível: o sistema informa e mantém a ordem no estado anterior.
- **Pós-condições:** ordem cancelada e reserva liberada, ou ordem inalterada.
- **Regras de negócio:** RN-07, RN-09, RN-13. **RNFs:** RNF-09, RNF-12.

#### Demais casos de uso (resumo)
- **UC-01:** o Administrador cadastra, consulta e atualiza investidores e contas; validações de entrada e auditoria de cada alteração.
- **UC-03/UC-04/UC-07/UC-08:** consultas do Investidor autenticado, restritas aos seus dados. UC-04 exibe indisponibilidade quando o serviço de cotações não responde no timeout.
- **UC-09:** a cada mudança relevante de estado, o sistema enfileira e-mail ao Investidor; falha de envio gera retentativa sem bloquear a ordem.
- **UC-10:** o Auditor filtra registros por período, investidor, ordem e tipo de evento; somente leitura.
- **UC-11:** a Corretora devolve estados (parcialmente executada, executada, rejeitada); o sistema aplica somente transições válidas (RN-13), ignora mensagens duplicadas e atualiza saldo e carteira de forma atômica.
- **UC-12:** o Administrador define limites por investidor; alterações valem para ordens futuras e são auditadas.

## 9. Pensamento Sistêmico

### 9.1 Fronteira e interações
O SentinelTrade é o sistema central. Recebe **entradas** (solicitações do Investidor, cotações, retornos da corretora) e produz **saídas** (ordens transmitidas, estados, notificações, registros de auditoria). Fora da fronteira ficam Investidor, Administrador, Auditor, Serviço de Cotações, Corretora e Serviço de E-mail.

### 9.2 Fluxo ponta a ponta da ordem
```
Investidor → [Autenticação MFA] → [Nova ordem] → Cotação (externo)
   → Validação (saldo, posição, horário, limites) → Confirmação por PIN
   → Reserva de saldo/posição → Fila → Corretora (externo)
   → Retorno de estado → Atualização de carteira → Notificação → Auditoria
```
Cada etapa gera evento de auditoria e depende da anterior; uma falha em qualquer ponto deve terminar em estado consistente (ordem rejeitada e reserva liberada, ou ordem concluída).

### 9.3 Interdependências e riscos

| Componente / evento | Impacto no sistema | Resposta prevista |
|---|---|---|
| Cotações indisponíveis | Impede a validação e o envio de ordens | Timeout 3 s, ordem recusada, aviso ao investidor (RNF-08, RNF-11) |
| Corretora lenta ou fora do ar | Ordens paradas, risco de reenvio | Fila, retentativas com idempotência, rejeição após limite e liberação de reserva (RNF-06, 09, 10) |
| Falha após reservar saldo | Saldo bloqueado sem ordem ativa | Transação atômica ou compensação (RNF-12) |
| E-mail indisponível | Login impossível; notificações atrasadas | Login bloqueado com aviso; notificações reenfileiradas |
| Retorno duplicado da corretora | Execução contada duas vezes | Idempotência no processamento de retornos (UC-11) |
| Cancelamento concorrente com execução | Estados divergentes | Corretora como fonte da verdade; transições validadas (RN-13) |

### 9.4 Laços de realimentação
- **Limites de risco:** exposição acumulada do dia reduz o que pode ser enviado nas ordens seguintes (RN-05).
- **Bloqueio de acesso:** falhas repetidas de autenticação bloqueiam a conta, protegendo o sistema (RN-12).
- **Retentativas:** o excesso de falhas da corretora não gera repetição infinita; o limite de 3 corta o ciclo.

### 9.5 Compromissos entre requisitos
- **Segurança × desempenho:** MFA, PIN e hash lento acrescentam latência; aceitável nas operações de acesso e confirmação, mas não nas consultas.
- **Resiliência × consistência:** retentativas e fila aumentam a disponibilidade, mas exigem idempotência e reservas para não duplicar ou perder saldo.
- **Auditoria × privacidade:** registros imutáveis não devem conter senha, PIN, código MFA nem tokens.
- **Disponibilidade × segurança:** em dúvida (integração crítica fora), o sistema falha de forma segura e recusa ordens em vez de arriscar inconsistência (RNF-11).

## 10. Matriz de Rastreabilidade

Casos de uso conforme a seção 8. Os testes são planejados (CT-nn corresponde ao critério CA-nn). Implementação permanece "A definir" até existir código real.

| Requisito | Caso de uso | Implementação | Teste |
|---|---|---|---|
| RF-01 | UC-01 | A definir | CT-01 |
| RF-02 | UC-02 | A definir | CT-02, CT-21 |
| RF-03 | UC-03 | A definir | CT-03 |
| RF-04 | UC-04 | A definir | CT-04 |
| RF-05 | UC-05 | A definir | CT-05 |
| RF-06 | UC-06 | A definir | CT-06 |
| RF-07 | UC-05 | A definir | CT-07 |
| RF-08 | UC-05, UC-11 | A definir | CT-08 |
| RF-09 | UC-07, UC-11 | A definir | CT-09 |
| RF-10 | UC-08 | A definir | CT-10 |
| RF-11 | UC-09 | A definir | CT-11 |
| RF-12 | Transversal (UC-02, 05, 06, 11) | A definir | CT-12 |
| RF-13 | UC-10 | A definir | CT-19 |
| RF-14 | UC-12 | A definir | CT-20 |
| RNF-01 | Transversal (UC-01, UC-02) | A definir | A definir |
| RNF-02 | UC-02 | A definir | CT-02 |
| RNF-03 | Transversal | A definir | CT-10, CT-19 |
| RNF-04 | Transversal | A definir | A definir |
| RNF-05 | Transversal | A definir | A definir |
| RNF-06 | UC-05 | A definir | CT-13 |
| RNF-07 | UC-10 | A definir | CT-19 |
| RNF-08 | UC-04, UC-05, UC-06 | A definir | CT-14 |
| RNF-09 | UC-05, UC-06 | A definir | CT-14 |
| RNF-10 | UC-05, UC-09 | A definir | A definir |
| RNF-11 | UC-04, UC-05 | A definir | CT-15 |
| RNF-12 | UC-05, UC-06, UC-11 | A definir | CT-16 |
| RNF-13 | Transversal | A definir | CT-10 |
| RNF-14 | Transversal | A definir | A definir |
| RNF-15 | Transversal | A definir | A definir |
| RNF-16 | Transversal | A definir | A definir |
| RNF-17 | Transversal | A definir | CT-17 |
| RNF-18 | Transversal | A definir | CT-18 |
