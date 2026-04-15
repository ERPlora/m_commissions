# Provisionen (Modul: `commissions`)

Verkaufsprovisionsregeln, Verfolgung und Auszahlungen für Mitarbeiter.

## Zweck

Das Provisionen-Modul automatisiert die Berechnung und Auszahlung von Verkaufsprovisionen. Wenn ein Verkauf abgeschlossen ist, bewertet das Modul die passenden Provisionsregeln (nach Mitarbeiter, Dienstleistung, Produkt oder global) und generiert automatisch Provisionsbuchungen. Manager können Auszahlungen in einer konfigurierbaren Häufigkeit (wöchentlich, zweiwöchentlich, monatlich oder individuell) überprüfen, genehmigen und verarbeiten.

Provisionsregeln unterstützen drei Berechnungstypen: Festbetrag, Prozentsatz des Verkaufs und gestaffelt (basierend auf dem kumulierten Verkaufsvolumen). Die Berechnungsbasis kann Bruttoverkauf, Nettoumsatz (nach Rabatten) oder Gewinnspanne sein.

Auszahlungen können in bar, per Banküberweisung, Scheck oder in die Gehaltsabrechnung integriert erfolgen.

## Modelle

- `CommissionsSettings` — Singleton pro Hub. Steuert die standardmäßige Auszahlungshäufigkeit, Berechnungsbasis und automatische Genehmigungsschwellen.
- `CommissionRule` — Regeldefinition: Name, Typ (fest/Prozent/gestaffelt), Satz, Priorität, Zeitraum der Gültigkeit, Mitarbeiter/Dienstleistung/Produkt-Bereich.
- `CommissionTransaction` — Generierter Provisionsposten pro Verkauf pro Mitarbeiter. Status: ausstehend / genehmigt / bezahlt / storniert / angepasst.
- `CommissionPayout` — Aggregierte Auszahlung für einen Mitarbeiter über einen Zeitraum. Status: Entwurf / ausstehend / genehmigt / in Bearbeitung / abgeschlossen / fehlgeschlagen / storniert / in Gehaltsabrechnung enthalten.
- `CommissionAdjustment` — Manuelle Prämie, Korrektur, Abzug oder Rückerstattungsanpassung zusätzlich zu den berechneten Provisionen.

## Routen

`GET /m/commissions/` — Übersichtsdashboard mit Statistiken  
`GET /m/commissions/transactions` — Transaktionsliste mit Filtern  
`GET /m/commissions/payouts` — Auszahlungsübersicht  
`GET /m/commissions/rules` — Regelverwaltung  
`GET /m/commissions/adjustments` — Verwaltung manueller Anpassungen  
`GET /m/commissions/settings` — Moduleinstellungen  

## API

`GET /api/v1/m/commissions/rules` — Liste aktiver Provisionsregeln  
`GET /api/v1/m/commissions/transactions` — Liste von Provisionsbuchungen  
`GET /api/v1/m/commissions/payouts` — Liste von Auszahlungen  

## Ereignisse

### Verbraucht

`sales.completed` — Generiert automatisch `CommissionTransaction`-Einträge für passende Regeln, wenn ein Verkauf abgeschlossen ist.

## Hooks

### Ausgegeben (Aktionen, auf die andere Module abonnieren können)

`commissions.payout_completed` — Wird ausgelöst, wenn eine Auszahlung als abgeschlossen markiert wird. Payload: `payout`.

## Abhängigkeiten

- `staff`
- `services`
- `inventory`
- `sales`
- `appointments`

## Preisgestaltung

Kostenlos.