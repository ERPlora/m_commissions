# Commissions (module: `commissions`)

Règles de commission sur les ventes, suivi et paiements pour les membres du personnel.

## Purpose

Le module Commissions automatise le calcul et le paiement des commissions sur les ventes. Lorsqu'une vente est finalisée, le module évalue les règles de commission correspondantes (par employé, service, produit ou global) et génère automatiquement des transactions de commission. Les managers peuvent examiner, approuver et traiter les paiements à une fréquence configurable (hebdomadaire, bi-hebdomadaire, mensuelle ou personnalisée).

Les règles de commission prennent en charge trois types de calcul : montant fixe, pourcentage de la vente et échelonné (basé sur le volume de ventes cumulées). La base de calcul peut être les ventes brutes, les ventes nettes (après remises) ou la marge bénéficiaire.

Les paiements peuvent être effectués par espèces, virement bancaire, chèque ou intégrés à la paie.

## Models

- `CommissionsSettings` — Singleton par hub. Contrôle la fréquence de paiement par défaut, la base de calcul et les seuils d'auto-approbation.
- `CommissionRule` — Définition de la règle : nom, type (fixe/pourcentage/échelonné), taux, priorité, plage de dates d'entrée en vigueur, portée employé/service/produit.
- `CommissionTransaction` — Entrée de commission générée par vente par employé. Statut : en attente / approuvé / payé / annulé / ajusté.
- `CommissionPayout` — Lot de paiement agrégé pour un membre du personnel sur une période. Statut : brouillon / en attente / approuvé / en traitement / terminé / échoué / annulé / inclus_dans_la_fiche_de_paie.
- `CommissionAdjustment` — Bonus manuel, correction, déduction ou ajustement de remboursement en plus des commissions calculées.

## Routes

`GET /m/commissions/` — Tableau de bord d'aperçu avec statistiques  
`GET /m/commissions/transactions` — Liste des transactions avec filtres  
`GET /m/commissions/payouts` — Liste des paiements  
`GET /m/commissions/rules` — Gestion des règles  
`GET /m/commissions/adjustments` — Gestion des ajustements manuels  
`GET /m/commissions/settings` — Paramètres du module  

## API

`GET /api/v1/m/commissions/rules` — Liste des règles de commission actives  
`GET /api/v1/m/commissions/transactions` — Liste des transactions de commission  
`GET /api/v1/m/commissions/payouts` — Liste des paiements  

## Events

### Consumed

`sales.completed` — Génère automatiquement des entrées `CommissionTransaction` pour les règles correspondantes lorsqu'une vente est finalisée.

## Hooks

### Emitted (actions other modules can subscribe to)

`commissions.payout_completed` — Déclenché lorsqu'un paiement est marqué comme terminé. Payload : `payout`.

## Dependencies

- `staff`
- `services`
- `inventory`
- `sales`
- `appointments`

## Pricing

Gratuit.