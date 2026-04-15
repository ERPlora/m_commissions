# Comissões (módulo: `commissions`)

Regras de comissão de vendas, rastreamento e pagamentos para membros da equipe.

## Propósito

O módulo Comissões automatiza o cálculo e o pagamento das comissões de vendas. Quando uma venda é concluída, o módulo avalia as regras de comissão correspondentes (por funcionário, serviço, produto ou global) e gera automaticamente transações de comissão. Os gerentes podem revisar, aprovar e processar pagamentos em uma frequência configurável (semanal, quinzenal, mensal ou personalizada).

As regras de comissão suportam três tipos de cálculo: valor fixo, percentual da venda e escalonado (com base no volume de vendas acumulado). A base de cálculo pode ser vendas brutas, vendas líquidas (após descontos) ou margem de lucro.

Os pagamentos podem ser feitos via dinheiro, transferência bancária, cheque ou incorporados à folha de pagamento.

## Modelos

- `CommissionsSettings` — Singleton por hub. Controla a frequência padrão de pagamento, a base de cálculo e os limites de aprovação automática.
- `CommissionRule` — Definição da regra: nome, tipo (fixo/percentual/escalonado), taxa, prioridade, intervalo de datas efetivas, escopo de funcionário/serviço/produto.
- `CommissionTransaction` — Entrada de comissão gerada por venda por funcionário. Status: pendente / aprovado / pago / cancelado / ajustado.
- `CommissionPayout` — Lote de pagamento agregado para um membro da equipe durante um período. Status: rascunho / pendente / aprovado / processando / concluído / falhou / cancelado / incluído_na_folha_de_pagamento.
- `CommissionAdjustment` — Bônus manual, correção, dedução ou ajuste de reembolso sobre comissões calculadas.

## Rotas

`GET /m/commissions/` — Painel de visão geral com estatísticas  
`GET /m/commissions/transactions` — Lista de transações com filtros  
`GET /m/commissions/payouts` — Lista de pagamentos  
`GET /m/commissions/rules` — Gerenciamento de regras  
`GET /m/commissions/adjustments` — Gerenciamento de ajustes manuais  
`GET /m/commissions/settings` — Configurações do módulo  

## API

`GET /api/v1/m/commissions/rules` — Lista de regras de comissão ativas  
`GET /api/v1/m/commissions/transactions` — Lista de transações de comissão  
`GET /api/v1/m/commissions/payouts` — Lista de pagamentos  

## Eventos

### Consumido

`sales.completed` — Gera automaticamente entradas de `CommissionTransaction` para regras correspondentes quando uma venda é concluída.

## Hooks

### Emitido (ações que outros módulos podem assinar)

`commissions.payout_completed` — Disparado quando um pagamento é marcado como concluído. Payload: `payout`.

## Dependências

- `staff`
- `services`
- `inventory`
- `sales`
- `appointments`

## Preço

Gratuito.