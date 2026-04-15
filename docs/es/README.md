# Comisiones (módulo: `commissions`)

Reglas de comisiones de ventas, seguimiento y pagos para miembros del personal.

## Propósito

El módulo de Comisiones automatiza el cálculo y pago de comisiones de ventas. Cuando se completa una venta, el módulo evalúa las reglas de comisiones correspondientes (por empleado, servicio, producto o global) y genera automáticamente transacciones de comisiones. Los gerentes pueden revisar, aprobar y procesar pagos con una frecuencia configurable (semanal, quincenal, mensual o personalizada).

Las reglas de comisiones admiten tres tipos de cálculo: monto fijo, porcentaje de la venta y escalonado (basado en el volumen de ventas acumulado). La base de cálculo puede ser ventas brutas, ventas netas (después de descuentos) o margen de beneficio.

Los pagos pueden realizarse en efectivo, transferencia bancaria, cheque o integrarse en la nómina.

## Modelos

- `CommissionsSettings` — Singleton por hub. Controla la frecuencia de pago predeterminada, la base de cálculo y los umbrales de aprobación automática.
- `CommissionRule` — Definición de regla: nombre, tipo (fijo/porcentaje/escalonado), tasa, prioridad, rango de fechas efectivas, alcance de empleado/servicio/producto.
- `CommissionTransaction` — Entrada de comisión generada por venta por empleado. Estado: pendiente / aprobado / pagado / cancelado / ajustado.
- `CommissionPayout` — Lote de pago agregado para un miembro del personal durante un período. Estado: borrador / pendiente / aprobado / en procesamiento / completado / fallido / cancelado / incluido_en_nómina.
- `CommissionAdjustment` — Ajuste manual de bonificación, corrección, deducción o reembolso sobre las comisiones calculadas.

## Rutas

`GET /m/commissions/` — Panel de control con estadísticas  
`GET /m/commissions/transactions` — Lista de transacciones con filtros  
`GET /m/commissions/payouts` — Lista de pagos  
`GET /m/commissions/rules` — Gestión de reglas  
`GET /m/commissions/adjustments` — Gestión de ajustes manuales  
`GET /m/commissions/settings` — Configuración del módulo  

## API

`GET /api/v1/m/commissions/rules` — Lista de reglas de comisiones activas  
`GET /api/v1/m/commissions/transactions` — Lista de transacciones de comisiones  
`GET /api/v1/m/commissions/payouts` — Lista de pagos  

## Eventos

### Consumido

`sales.completed` — Genera automáticamente entradas de `CommissionTransaction` para las reglas correspondientes cuando se completa una venta.

## Hooks

### Emitido (acciones a las que otros módulos pueden suscribirse)

`commissions.payout_completed` — Se activa cuando un pago se marca como completado. Carga útil: `payout`.

## Dependencias

- `staff`
- `services`
- `inventory`
- `sales`
- `appointments`

## Precios

Gratis.