# SentinelTrade

Plataforma **simulada** de negociação de ativos financeiros (ações, ETFs e FIIs) da corretora fictícia Orion Capital. Projeto acadêmico (N1) de especificação e modelagem de um sistema de trade de alta criticidade.

> Não há bolsa real, dinheiro real nem dados pessoais reais. Todos os ativos, contas e cotações são simulados.

## Visão do projeto

O SentinelTrade permite que investidores autorizados:

- autentiquem-se com senha e MFA por e-mail;
- consultem cotações e sua carteira (posições e saldo);
- enviem ordens de compra e venda, confirmadas por PIN transacional;
- cancelem ordens e acompanhem seu ciclo de vida (criada, validada, enviada, parcialmente executada, executada, rejeitada, cancelada);
- recebam notificações e consultem o histórico de operações.

Administradores gerenciam investidores e limites de risco; auditores consultam registros de auditoria imutáveis.

Por ser um sistema crítico, o projeto prioriza **segurança, consistência de dados, resiliência (timeout, retentativa, idempotência, fila, indisponibilidade segura), auditabilidade e rastreabilidade**.

## Integrantes

| Nome | RA |
|---|---|
| Gustavo Francisco Toito | 10438660 |
| Guilherme Longo | 10736785 |
| Leonardo Assis | 10742770 |

## Tecnologias

_A definir pela equipe._ Itens previstos no escopo:

| Componente | Tecnologia |
|---|---|
| Linguagem / framework | A definir |
| Banco de dados | A definir |
| Fila de mensagens | A definir |
| Serviço de cotações (externo) | A definir |
| Corretora / sandbox (externo) | A definir |
| Serviço de e-mail (externo) | A definir |
| Modelagem UML | A definir |

## Documentação

Toda a documentação fica na pasta [`docs/`](docs/):

| Documento | Conteúdo |
|---|---|
| [`engenharia_de_requisitos.md`](docs/engenharia_de_requisitos.md) | Visão, atores, requisitos funcionais e não funcionais, regras de negócio, restrições técnicas, critérios de aceitação, casos de uso, pensamento sistêmico e matriz de rastreabilidade |
| Diagrama de casos de uso | Imagem UML na pasta `docs/` |

## Instruções de execução

_A ser preenchido quando houver implementação._ Modelo:

```bash
# 1. Clonar o repositório
git clone <url-do-repositorio>
cd sentineltrade

# 2. Configurar variáveis de ambiente
cp .env.example .env
# editar o .env com os valores locais (nunca versionar o .env)

# 3. Instalar dependências e executar
# (comandos a definir conforme as tecnologias escolhidas)
```

## Segurança e boas práticas

- **Nunca** versionar senhas, tokens, chaves de API ou dados sensíveis. Use variáveis de ambiente; o arquivo `.env.example` traz apenas os nomes das variáveis, sem valores reais.
- O `.env` e demais arquivos sensíveis devem constar no `.gitignore`.
- Mensagens de commit descritivas e coerentes com a evolução do projeto.

## Status

Fase atual: **especificação e modelagem (N1)** — requisitos e casos de uso. Implementação e testes ainda não iniciados.
