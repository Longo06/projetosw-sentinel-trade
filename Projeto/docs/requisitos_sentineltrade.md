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
| AT-01 | Investidor | Primário | Consulta carteira, saldo, cotações e histórico; envia e cancela ordens. |
| AT-02 | Administrador | Primário | Gerencia investidores, ativos, limites de risco e parâmetros operacionais. |
| AT-03 | Auditor | Primário | Consulta registros de auditoria em modo somente leitura. |
| AT-04 | Analista de Risco | Primário | Acompanha ordens bloqueadas ou rejeitadas e consulta ou ajusta limites de risco conforme suas permissões. |
| AT-05 | Serviço de Cotações / Provedor de Cotações | Secundário | Sistema externo que fornece cotações atualizadas ou simuladas dos ativos. |
| AT-06 | Corretora / Bolsa Simulada | Secundário | Sistema externo que recebe ordens válidas e devolve estados de execução, rejeição ou falha. |
| AT-07 | Serviço de Notificação | Secundário | Sistema externo responsável por enviar notificações sobre eventos relevantes ao investidor. |
| AT-08 | Serviço de Auditoria | Secundário | Componente externo ou integrado responsável por receber e manter registros de ações, decisões e alterações de estado. |
| AT-09 | Serviço de E-mail | Secundário | Serviço utilizado para entregar o código MFA e as notificações por e-mail. |

O Analista de Risco acompanha ordens bloqueadas ou rejeitadas e pode consultar limites; a alteração dos parâmetros permanece sob responsabilidade do Administrador. O Serviço de E-mail é um canal utilizado pelo Serviço de Notificação e pela autenticação MFA. O Serviço de Auditoria representa a integração responsável pela persistência dos registros; o Auditor é o usuário que consulta esses registros. Os provedores concretos dos serviços externos ainda devem ser definidos.

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
| RF-15 | Gestão de ativos | Permitir que o Administrador cadastre, consulte, atualize e desative os ativos disponíveis para negociação. |

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
| CA-22 | RF-15 | O Administrador cadastra, consulta, atualiza e desativa ativos; cada alteração é registrada em auditoria. |

## 8. Casos de Uso

### 8.1 Lista

| ID | Caso de uso | Ator primário | Atores secundários | Requisitos |
|---|---|---|---|---|
| UC-01 | Gerenciar investidor | Administrador | Serviço de Auditoria | RF-01, RF-12 |
| UC-02 | Autenticar investidor com MFA | Investidor | Serviço de E-mail, Serviço de Auditoria | RF-02, RF-12 |
| UC-03 | Consultar carteira | Investidor | — | RF-03 |
| UC-04 | Consultar cotações | Investidor | Serviço de Cotações | RF-04 |
| UC-05 | Enviar ordem de compra | Investidor | Serviço de Cotações, Corretora / Bolsa Simulada, Serviço de Auditoria | RF-05, RF-07, RF-08, RF-12 |
| UC-06 | Enviar ordem de venda | Investidor | Serviço de Cotações, Corretora / Bolsa Simulada, Serviço de Auditoria | RF-05, RF-07, RF-08, RF-12 |
| UC-07 | Cancelar ordem | Investidor | Corretora / Bolsa Simulada, Serviço de Notificação, Serviço de Auditoria | RF-06, RF-11, RF-12 |
| UC-08 | Consultar status da ordem | Investidor | — | RF-09 |
| UC-09 | Consultar histórico de operações | Investidor | — | RF-10 |
| UC-10 | Enviar notificação | Serviço de Notificação | Serviço de E-mail | RF-11 |
| UC-11 | Consultar auditoria | Auditor | Serviço de Auditoria | RF-13 |
| UC-12 | Atualizar estado da ordem | Corretora / Bolsa Simulada | Serviço de Auditoria, Serviço de Notificação | RF-08, RF-09, RF-11, RF-12 |
| UC-13 | Gerenciar limites de risco | Administrador | Analista de Risco, Serviço de Auditoria | RF-14, RF-12 |
| UC-14 | Gerenciar ativos | Administrador | Serviço de Auditoria | RF-15, RF-12 |
| UC-15 | Consultar saldo | Investidor | — | RF-03 |
| UC-16 | Validar ordem | Sistema | Serviço de Cotações, Analista de Risco | RF-07 |
| UC-17 | Transmitir ordem à corretora | Sistema | Corretora / Bolsa Simulada | RF-08 |
| UC-18 | Registrar auditoria | Sistema | Serviço de Auditoria | RF-12 |
| UC-19 | Verificar saldo ou posição | Sistema | — | RF-03, RF-07 |

**Observação:** consultar saldo também faz parte da consulta de carteira (UC-03), mas foi explicitado como caso de uso separado para atender à lista mínima do gabarito. A validação e a transmissão são etapas internas reutilizadas pelos casos de envio de compra e venda.

### 8.2 Descrições expandidas

#### UC-02 — Autenticar investidor com MFA
- **Objetivo:** permitir que o Investidor acesse o sistema após validar sua senha e o segundo fator de autenticação.
- **Ator principal:** Investidor. **Secundários:** Serviço de E-mail e Serviço de Auditoria.
- **Pré-condições:** investidor cadastrado e conta não bloqueada.
- **Fluxo principal:**
  1. O Investidor informa e-mail e senha.
  2. O sistema valida as credenciais e solicita o envio do código MFA ao Serviço de E-mail.
  3. O Investidor informa o código recebido.
  4. O sistema valida o código, cria a sessão e registra o evento de autenticação em auditoria.
- **Fluxos alternativos e de exceção:**
  - 2a. Credenciais inválidas: o sistema informa falha genérica, registra a tentativa e volta ao passo 1.
  - 4a. Código inválido ou expirado: o sistema permite nova tentativa (máx. 3) ou reenvio do código.
  - 4b. Três falhas consecutivas: a conta é bloqueada por 15 min (RN-12) e o evento é auditado.
  - 2b. Serviço de E-mail indisponível: o sistema informa a indisponibilidade e não conclui o login.
- **Pós-condições:** sessão autenticada criada; evento de autenticação registrado.
- **Regras de negócio:** RN-01, RN-02, RN-12. **RNFs:** RNF-01, RNF-02, RNF-04.

#### UC-05 — Enviar ordem de compra
- **Objetivo:** permitir que o Investidor envie uma ordem de compra de ativos, desde que saldo, horário, limites e demais validações sejam atendidos.
- **Ator principal:** Investidor. **Secundários:** Serviço de Cotações, Corretora / Bolsa Simulada e Serviço de Auditoria.
- **Pré-condições:** Investidor autenticado (UC-02); ativo disponível para negociação.
- **Fluxo principal:**
  1. O Investidor informa o ativo, a quantidade e o preço ou tipo da ordem.
  2. O sistema obtém uma cotação atualizada do Serviço de Cotações.
  3. O sistema valida saldo disponível, horário, limites de risco e frescor da cotação (UC-16).
  4. O sistema apresenta o resumo da ordem e solicita o PIN transacional.
  5. O Investidor confirma a operação com o PIN correto.
  6. O sistema registra a ordem como criada e validada, reserva o valor necessário e gera uma chave de idempotência.
  7. O sistema registra o evento de auditoria (UC-18) e transmite a ordem à corretora (UC-17).
  8. O sistema informa ao Investidor que a ordem foi aceita para processamento.
- **Fluxos alternativos e de exceção:**
  - 1a. Solicitação repetida com a mesma chave de idempotência: o sistema devolve a ordem existente, sem criar outra (RN-08).
  - 2a. Cotação indisponível ou vencida: o sistema interrompe o envio e informa o motivo (RN-11, RNF-11).
  - 3a. Saldo insuficiente, horário inválido ou limite excedido: a ordem é rejeitada com o motivo, sem reserva (RN-03, RN-05, RN-06).
  - 5a. PIN incorreto: o sistema solicita nova tentativa; após o limite, aplica RN-12.
  - 7a. Corretora indisponível ou em timeout: o sistema executa retentativas controladas (RNF-09); esgotadas, mantém o estado consistente, libera a reserva quando confirmado que não houve envio e informa o Investidor.
- **Pós-condições:** ordem persistida com estado consistente; valor reservado ou liberado; evento auditado; notificação enfileirada quando aplicável.
- **Regras de negócio:** RN-01, RN-03, RN-05, RN-06, RN-08, RN-09, RN-11, RN-13. **RNFs:** RNF-06, RNF-08 a RNF-12.

#### UC-06 — Enviar ordem de venda
- **Objetivo:** permitir que o Investidor envie uma ordem de venda de ativos que possua em quantidade disponível.
- **Ator principal:** Investidor. **Secundários:** Serviço de Cotações, Corretora / Bolsa Simulada e Serviço de Auditoria.
- **Pré-condições:** Investidor autenticado (UC-02); ativo disponível e posição suficiente na carteira.
- **Fluxo principal:**
  1. O Investidor informa o ativo, a quantidade e o preço ou tipo da ordem.
  2. O sistema obtém uma cotação atualizada do Serviço de Cotações.
  3. O sistema valida a posição disponível, o horário, os limites de risco e o frescor da cotação (UC-16).
  4. O sistema apresenta o resumo da ordem e solicita o PIN transacional.
  5. O Investidor confirma a operação com o PIN correto.
  6. O sistema registra a ordem como criada e validada, reserva a quantidade de ativos e gera uma chave de idempotência.
  7. O sistema registra o evento de auditoria (UC-18) e transmite a ordem à corretora (UC-17).
  8. O sistema informa ao Investidor que a ordem foi aceita para processamento.
- **Fluxos alternativos e de exceção:**
  - 1a. Solicitação repetida com a mesma chave de idempotência: o sistema devolve a ordem existente, sem criar outra (RN-08).
  - 2a. Cotação indisponível ou vencida: o sistema interrompe o envio e informa o motivo (RN-11, RNF-11).
  - 3a. Posição insuficiente, horário inválido ou limite excedido: a ordem é rejeitada com o motivo, sem reserva (RN-04, RN-05, RN-06).
  - 5a. PIN incorreto: o sistema solicita nova tentativa; após o limite, aplica RN-12.
  - 7a. Corretora indisponível ou em timeout: o sistema executa retentativas controladas (RNF-09); esgotadas, mantém o estado consistente, libera a reserva quando confirmado que não houve envio e informa o Investidor.
- **Pós-condições:** ordem persistida com estado consistente; quantidade reservada ou liberada; evento auditado; notificação enfileirada quando aplicável.
- **Regras de negócio:** RN-01, RN-04 a RN-06, RN-08, RN-09, RN-11, RN-13. **RNFs:** RNF-06, RNF-08 a RNF-12.

#### UC-07 — Cancelar ordem
- **Objetivo:** permitir que o Investidor solicite o cancelamento de uma ordem sua que ainda possua quantidade não executada.
- **Ator principal:** Investidor. **Secundários:** Corretora / Bolsa Simulada, Serviço de Notificação e Serviço de Auditoria.
- **Pré-condições:** Investidor autenticado; ordem pertencente a ele e em estado cancelável (RN-07).
- **Fluxo principal:**
  1. O Investidor seleciona a ordem e solicita o cancelamento.
  2. O sistema verifica o estado atual e a quantidade ainda não executada.
  3. O sistema solicita o cancelamento à corretora.
  4. A corretora confirma; o sistema atualiza o estado da ordem, libera a reserva correspondente e registra a auditoria.
  5. O Serviço de Notificação envia a confirmação ao Investidor.
- **Fluxos alternativos e de exceção:**
  - 2a. Ordem em estado final (executada, rejeitada ou cancelada): o sistema recusa e informa o motivo.
  - 3a. Ordem executada na corretora durante o pedido: o cancelamento é recusado e o estado retornado pela corretora prevalece.
  - 3b. Corretora indisponível: o sistema informa a falha e mantém a ordem no estado anterior.
  - 4a. Ordem parcialmente executada: somente a quantidade ainda não executada pode ser cancelada (RN-07).
- **Pós-condições:** ordem cancelada total ou parcialmente, com reserva correspondente liberada e evento auditado; ou ordem mantida no estado anterior.
- **Regras de negócio:** RN-07, RN-09, RN-13. **RNFs:** RNF-09, RNF-12.

#### Demais casos de uso (resumo)
- **UC-01:** o Administrador cadastra, consulta e atualiza investidores e contas; alterações relevantes são auditadas.
- **UC-03/UC-15:** o Investidor consulta sua carteira, posições e saldo; os dados são restritos ao próprio investidor.
- **UC-04:** o Investidor consulta cotações; o sistema informa indisponibilidade quando o serviço não responde dentro do timeout.
- **UC-08/UC-09:** o Investidor consulta o estado atual das ordens e o histórico de operações.
- **UC-10:** o Serviço de Notificação envia avisos de execução, rejeição, cancelamento e falha de integração; falhas de entrega geram retentativas sem bloquear a ordem.
- **UC-11:** o Auditor filtra registros por período, investidor, ordem e tipo de evento; a consulta é somente leitura.
- **UC-12:** a Corretora devolve estados (parcialmente executada, executada ou rejeitada); o sistema aplica somente transições válidas (RN-13), ignora mensagens duplicadas e atualiza saldo e carteira de forma consistente.
- **UC-13:** o Administrador define limites por investidor; alterações valem para ordens futuras e são auditadas.
- **UC-14:** o Administrador cadastra, consulta, atualiza ou desativa ativos disponíveis para negociação; alterações são auditadas.
- **UC-16:** o sistema valida os dados da ordem, cotação, saldo ou posição, horário e limites antes de permitir o envio.
- **UC-17:** o sistema transmite à corretora somente ordens validadas, utilizando a chave de idempotência.
- **UC-18:** o sistema envia ao Serviço de Auditoria os eventos de autenticação, alteração de dados, criação, validação, rejeição, cancelamento e execução de ordens.
- **UC-19:** o sistema verifica saldo disponível para compra ou posição disponível para venda, considerando reservas de ordens ainda abertas.

## 9. Pensamento Sistêmico

### 9.1 Fronteira e interações
O SentinelTrade é o sistema central. Recebe **entradas** (solicitações do Investidor, cotações, retornos da corretora) e produz **saídas** (ordens transmitidas, estados, notificações, registros de auditoria). Fora da fronteira ficam Investidor, Administrador, Auditor, Analista de Risco, Serviço de Cotações, Corretora / Bolsa Simulada, Serviço de Notificação, Serviço de Auditoria e Serviço de E-mail.

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
| Serviço de E-mail ou de Notificação indisponível | Login pode não ser concluído; notificações podem atrasar | Login não é liberado sem MFA; notificações são reenfileiradas para nova tentativa |
| Serviço de Auditoria indisponível | Eventos podem deixar de ser persistidos | Operações críticas devem seguir a política de falha segura, sem confirmar sucesso se o registro obrigatório não puder ser garantido |
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
| RF-03 | UC-03, UC-15, UC-19 | A definir | CT-03 |
| RF-04 | UC-04 | A definir | CT-04 |
| RF-05 | UC-05, UC-06 | A definir | CT-05 |
| RF-06 | UC-07 | A definir | CT-06 |
| RF-07 | UC-05, UC-06, UC-16, UC-19 | A definir | CT-07 |
| RF-08 | UC-05, UC-06, UC-12, UC-17 | A definir | CT-08 |
| RF-09 | UC-08, UC-12 | A definir | CT-09 |
| RF-10 | UC-09 | A definir | CT-10 |
| RF-11 | UC-07, UC-10, UC-12 | A definir | CT-11 |
| RF-12 | Transversal (UC-01, 02, 05, 06, 07, 12, 13, 14, 18) | A definir | CT-12 |
| RF-13 | UC-11 | A definir | CT-19 |
| RF-14 | UC-13 | A definir | CT-20 |
| RF-15 | UC-14 | A definir | CT-22 |
| RNF-01 | Transversal (UC-01, UC-02) | A definir | A definir |
| RNF-02 | UC-02 | A definir | CT-02 |
| RNF-03 | Transversal | A definir | CT-10, CT-19 |
| RNF-04 | Transversal | A definir | A definir |
| RNF-05 | Transversal | A definir | A definir |
| RNF-06 | UC-05, UC-06, UC-17 | A definir | CT-13 |
| RNF-07 | UC-18 | A definir | CT-19 |
| RNF-08 | UC-04, UC-05, UC-06, UC-07 | A definir | CT-14 |
| RNF-09 | UC-05, UC-06, UC-07, UC-10 | A definir | CT-14 |
| RNF-10 | UC-05, UC-06, UC-10, UC-17 | A definir | A definir |
| RNF-11 | UC-04, UC-05, UC-06, UC-17 | A definir | CT-15 |
| RNF-12 | UC-05, UC-06, UC-07, UC-12 | A definir | CT-16 |
| RNF-13 | Transversal | A definir | CT-10 |
| RNF-14 | Transversal | A definir | A definir |
| RNF-15 | Transversal | A definir | A definir |
| RNF-16 | Transversal | A definir | A definir |
| RNF-17 | Transversal (UC-18 e operações relacionadas) | A definir | CT-17 |
| RNF-18 | Transversal | A definir | CT-18 |
