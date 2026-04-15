# Commissioni (modulo: `commissions`)

Regole sulle commissioni di vendita, tracciamento e pagamenti per i membri del personale.

## Scopo

Il modulo Commissioni automatizza il calcolo e il pagamento delle commissioni di vendita. Quando una vendita viene completata, il modulo valuta le regole di commissione corrispondenti (per dipendente, servizio, prodotto o globale) e genera automaticamente le transazioni di commissione. I manager possono rivedere, approvare e elaborare i pagamenti con una frequenza configurabile (settimanale, bisettimanale, mensile o personalizzata).

Le regole di commissione supportano tre tipi di calcolo: importo fisso, percentuale di vendita e a livelli (basato sul volume di vendite cumulative). La base di calcolo può essere vendite lorde, vendite nette (dopo gli sconti) o margine di profitto.

I pagamenti possono essere effettuati tramite contante, bonifico bancario, assegno o inclusi nella busta paga.

## Modelli

- `CommissionsSettings` — Singleton per hub. Controlla la frequenza di pagamento predefinita, la base di calcolo e le soglie di approvazione automatica.
- `CommissionRule` — Definizione della regola: nome, tipo (fisso/percentuale/a livelli), tasso, priorità, intervallo di date di validità, ambito dipendente/servizio/prodotto.
- `CommissionTransaction` — Voce di commissione generata per ogni vendita per dipendente. Stato: in attesa / approvato / pagato / annullato / regolato.
- `CommissionPayout` — Lotto di pagamento aggregato per un membro del personale su un periodo. Stato: bozza / in attesa / approvato / in elaborazione / completato / fallito / annullato / incluso_nella_busta_paga.
- `CommissionAdjustment` — Bonus manuale, correzione, deduzione o rimborso aggiuntivo sulle commissioni calcolate.

## Percorsi

`GET /m/commissions/` — Dashboard di panoramica con statistiche  
`GET /m/commissions/transactions` — Elenco delle transazioni con filtri  
`GET /m/commissions/payouts` — Elenco dei pagamenti  
`GET /m/commissions/rules` — Gestione delle regole  
`GET /m/commissions/adjustments` — Gestione delle regolazioni manuali  
`GET /m/commissions/settings` — Impostazioni del modulo  

## API

`GET /api/v1/m/commissions/rules` — Elenco delle regole di commissione attive  
`GET /api/v1/m/commissions/transactions` — Elenco delle transazioni di commissione  
`GET /api/v1/m/commissions/payouts` — Elenco dei pagamenti  

## Eventi

### Consumati

`sales.completed` — Genera automaticamente voci `CommissionTransaction` per le regole corrispondenti quando una vendita è completata.

## Hook

### Emessi (azioni a cui altri moduli possono iscriversi)

`commissions.payout_completed` — Attivato quando un pagamento è contrassegnato come completato. Payload: `payout`.

## Dipendenze

- `staff`
- `services`
- `inventory`
- `sales`
- `appointments`

## Prezzo

Gratuito.