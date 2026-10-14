# Informe de Auditoría — Frival Execution Desk

**Fecha:** 2026-10-10  
**Hora local (UTC-5):** aproximadamente 12:21  
**Identificador del modelo:** deepseek/deepseek-v4-pro (via openrouter)  
**Alcance:** Revisión estática del repositorio `fx-prival`, enfoque en el escritorio de ejecución autónoma Frival (no el pipeline ML legado).  
**Estado:** Completo dentro de los límites de inspección estática. No se ejecutaron scripts del proyecto ni se realizaron acciones de trading.

---

## 1. Resumen Ejecutivo

El escritorio Frival es un sistema de trading algorítmico semidiscrecional que opera sobre la cuenta MT5 `81486396` (FP Markets Live) con los símbolos XAUUSD, EURUSD y USDJPY. Un agente autónomo evalúa estructura de mercado cada 15 minutos, emite señales sujetas a cuatro compuertas geométricas, y `order_executor.py` —el único componente autorizado para colocar órdenes— aplica guardarraíles de riesgo en código.

**El sistema funciona en producción con dinero real.** A la fecha de esta auditoría, la cuenta muestra ~$695 de equity, habiendo crecido desde ~$604 (mínimo de sesión) hasta un pico de ~$758, con un rendimiento acumulado de aproximadamente +$101 en 25 operaciones cerradas.

**Hallazgos principales:**

1. **CRÍTICO — `close-all` no cancela órdenes pendientes:** La función de aplanamiento de emergencia solo cierra posiciones abiertas, pero ignora órdenes pendientes (`orders_get`). Las órdenes límite/stop que ya fueron enviadas al broker permanecen vivas y pueden ejecutarse incluso después de activar el kill switch o el circuit breaker. Esto contradice directamente la definición de "estado seguro" (0 posiciones, 0 pendientes) en `OPERATIONS.md`.

2. **ALTO — Exposición no contabilizada de órdenes pendientes:** Las órdenes pendientes no se cuentan en `MAX_POSITIONS` ni en el cómputo de riesgo agregado (`open_risk_pct`). Es posible exceder los límites declarados colocando múltiples órdenes pendientes simultáneamente.

3. **ALTO — Verificación de margen errónea para USDJPY:** El cálculo de notional (`vol * contract_size * entry`) multiplica el precio en JPY como si fuera USD, inflando el margen requerido ~150×. Esto bloquea cualquier tamaño económicamente relevante en USDJPY, forzando concentración total en XAUUSD.

4. **ALTO — Sin prevención de órdenes duplicadas:** `cmd_place` no verifica si ya existe una orden o posición para el mismo `log_id`. La evidencia de auditoría muestra colocación triple de T010 y doble de T014.

5. **ALTO — Persistencia no atómica del ledger:** `save_log` abre el CSV en modo `"w"` sin write-then-rename y sin locking. El ledger ya fue truncado una vez (pérdida de filas de T019→T020), requiriendo reconstrucción manual desde git e historial del broker.

6. **ALTO — Evidencia contrafactual incluye operaciones que nunca se habrían ejecutado:** El 33% de los contrafactuales clasificados como TP_ONLY muestran MAE negativo (el precio nunca alcanzó el nivel de entrada). Estas operaciones "ganadoras" inflan artificialmente las estadísticas que justifican decisiones de política como bajar `MIN_RR` de 2.0 a 1.9.

7. **ALTO — `manage` marca órdenes pendientes como "stale" cada ciclo:** La lógica de retiro de filas stale itera sobre filas con status `ORDER_PLACED` y las marca CLOSED si no hay posición viva para ese símbolo — pero una orden pendiente precisamente no tiene posición hasta que se ejecuta. El audit log muestra >70 eventos `STALE_ROW_RETIRED` sobre órdenes perfectamente vivas.

El sistema ha demostrado capacidad de generar y ejecutar señales con disciplina, y las correcciones documentadas (intrabar BE, true-fill PnL, schema-tolerant save_log) reflejan aprendizaje genuino. Sin embargo, los defectos de seguridad listados arriba —particularmente la imposibilidad de aplanar completamente en emergencia y la falta de prevención de duplicados— representan riesgos materiales para el capital en cuenta viva.

---

## 2. Arquitectura del Sistema y Flujo Operacional

### 2.1 Componentes principales

| Componente | Archivo | Función |
|---|---|---|
| Executor de órdenes | `frival/order_executor.py` | ÚNICO autorizado para colocar/modificar/cerrar órdenes. Contiene guardarraíles. |
| Logger de trades | `frival/log_trade.py` | Registro de señales, fills, BE, salidas. Upsert por `log_id`. |
| Contexto de mercado | `frival/market_context.py` | Snapshot por señal (quote, ATR, barras) → `context/T0NN.{json,md}` |
| Contrafactuales | `frival/counterfactual.py` | Setups rechazados + resolución contra precio |
| Reconciliación | `frival/reconcile_deals.py` | Match log ↔ broker deals. READ-ONLY (apply prohibido). |
| Revisión EOD | `frival/eod_review.py` | Genera review diaria determinística |
| Kill switch | `frival/data/emergency_stop.txt` | Bloquea nuevas entradas si existe |
| Estado del executor | `frival/executor_state.json` | session_date, session_start_equity, consecutive_losses, daily_realised |

### 2.2 Flujo del ciclo (STEPS 1-7)

```
Cron */15 min → [STEP 1: Leer M5/M15/H1 + tick] 
  → [STEP 2: Data-quality gates] 
  → [STEP 3: Geometry gates] 
  → [STEP 4: Si ejecutable → log_trade.py signal → market_context.py capture → order_executor.py place]
  → [STEP 5: Si no → counterfactual.py consider]
  → [STEP 6: manage (BE/partial/stale)]
  → [STEP 7: Reporte ESTADO]
```

### 2.3 Flujo de datos

```
Agente (estructura) → señal → trade_log.csv (PENDING_FILL)
  → order_executor.py place → guardrail_report() → MT5 order_send()
  → execution_audit.jsonl → actualiza trade_log.csv (ORDER_PLACED/OPEN)
  → manage cada ciclo → BE/partial/stale → reconcilia con broker
```

---

## 3. Inventario de Lectura y Limitaciones de Cobertura

### 3.1 Archivos inspeccionados en profundidad

- `OPERATIONS.md` — completo (365 líneas)
- `ACTIVE MONITOR — Frival desk.md` — completo (150 líneas)
- `AGENTS.md` — completo (68 líneas)
- `frival/order_executor.py` — completo (868 líneas)
- `frival/log_trade.py` — completo (641 líneas)
- `frival/counterfactual.py` — completo (300 líneas)
- `frival/reconcile_deals.py` — completo (322 líneas)
- `frival/eod_review.py` — completo (176 líneas)
- `frival/market_context.py` — completo (274 líneas)
- `frival/mt5_path.py` — completo (85 líneas)
- `frival/test_kill_switch.py` — completo (170 líneas)
- `frival/IMPROVEMENTS.md` — completo (160 líneas)
- `frival/SETUP_NEW_MACHINE.md` — completo (194 líneas)
- `frival/trade_log.csv` — 45 filas, inspeccionadas completas (líneas largas truncadas a 2000 caracteres)
- `frival/execution_audit.jsonl` — 194 líneas, inspeccionadas por muestreo y grep dirigido
- `frival/executor_state.json` — completo
- `frival/counterfactuals.csv` — 41 filas, completas
- `frival/reviews/INDEX.md` — completo
- `frival/reviews/2026-10-07.md`, `2026-10-08.md`, `2026-10-09.md` — completos
- `continua-operando.md` — completo (238 líneas)
- `.gitignore`, `kilo.json` — completos
- `.git/logs/HEAD` — inspeccionado para verificar hashes de commit
- `C:\Users\sosap\AppData\Local\Temp\kilo\frival_read.py`, `frival_bars.py`, `frival_backfill.py` — completos

### 3.2 Archivos referenciados pero no disponibles o no inspeccionados

- `frival/data/emergency_stop.txt` — no existe al momento de la auditoría (kill switch no armado)
- `frival/config/.env` — gitignored, no inspeccionado (contiene credenciales)
- `frival/context/T0NN.{json,md}` — inventariados por nombre de archivo, no leídos individualmente
- `frival/gold_rules/run_gold_rules.py` — inspeccionado parcialmente (líneas 1-110, 255-334)
- `frival/execution_bot/core/exec_d1_terminal.py` — inspeccionado parcialmente (líneas 1-130)
- `frival/execution_bot/config/settings.yaml` — completo
- `frival/DAILY_ROUTINE.md` — inspeccionado parcialmente (líneas 1-80)

### 3.3 Áreas no revisadas

- Pipeline ML legado (`main.py`, `signal_gate.py`, `live_logger.py`, `model/`)
- `quant-personal-fund/` (fuera del alcance del desk Frival)
- `frival/gold_rules/` (motor separado, no parte del desk autónomo)
- `frival/dashboard/`
- `frival/fx_rules_backtest/`
- Tests en `frival/execution_bot/tests/` y `frival/gold_rules/tests/` (inspeccionados por existencia, no leídos)

### 3.4 Reclamos que requieren validación en runtime o en broker

- Que `order_executor.py` sea efectivamente la única vía de colocación de órdenes en producción
- Que los valores de `money_per_price_unit` del broker coincidan con los documentados
- Que los fills del broker correspondan exactamente a las entradas registradas
- Que el kill switch efectivamente bloquee todas las colocaciones
- Que el estado `executor_state.json` se reconstruya correctamente desde el ledger

---

## 4. Matriz de Cumplimiento Documentación-Implementación

| Regla documentada | Ref. documentación | Ref. implementación | Evidencia | Verificación |
|---|---|---|---|---|
| `order_executor.py` única autoridad de órdenes | OPERATIONS.md:L22-23 | `order_executor.py` docstring:L5-7 | Código; existen otros paths con `order_send` (gold_rules, execution_bot) en modo demo | PARCIALMENTE VERIFICADO — otros módulos tienen capacidad de orden pero configurados como demo |
| Riesgo por trade ≤ 5% | OPERATIONS.md:L153 | `MAX_RISK_PCT_PER_TRADE = 5.00` (L49) | guardrail_report() L360 | VERIFICADO |
| Riesgo agregado ≤ 12% | OPERATIONS.md:L154 | `MAX_RISK_PCT_TOTAL = 12.00` (L104) | guardrail_report() L369 | PARCIALMENTE VERIFICADO — solo cuenta posiciones abiertas, no órdenes pendientes |
| Max 3 posiciones | OPERATIONS.md:L155 | `MAX_POSITIONS = 3` (L57) | L367 | PARCIALMENTE VERIFICADO — no cuenta órdenes pendientes; el brief dice 1 |
| Mismo USD thesis ≤ 2 | OPERATIONS.md:L156 | `MAX_SAME_THESIS = 2` (L105) | L371 | PARCIALMENTE VERIFICADO — bug off-by-one (efectivamente 1); check ciego a dirección |
| R:R mínimo 1.9 | OPERATIONS.md:L157 | `MIN_RR = 1.9` (L103) | L373 | VERIFICADO |
| Kill switch bloquea entradas | OPERATIONS.md:L171-172 | `kill_switch_active()` (L218-219) | L402-405 | VERIFICADO |
| `reconcile_deals.py apply` prohibido | OPERATIONS.md:L23-24 | Docstring prohíbe apply; OPERATIONS y AGENTS lo prohíben | N/A — regla de política | DOCUMENTADO SOLAMENTE |
| `place --force` prohibido | OPERATIONS.md:L23 | Flag `--force` parseado (L851) pero NUNCA evaluado en cmd_place | Código — el flag se acepta pero se ignora | VERIFICADO (el flag es no-op; la prohibición se cumple por omisión) |
| Log antes de colocar | OPERATIONS.md:L290 | Docstring L16-18 | Flujo STEP 4 del brief | DOCUMENTADO SOLAMENTE — no hay enforcement en código |
| SL distance cross-check | OPERATIONS.md:L283-284 | `guardrail_report()` L304-313 | Código | VERIFICADO |
| Volume risk-based, no lotes fijos | AGENTS.md:L13-24 | `_size_volume()` L265-284 | Código | VERIFICADO |
| Money per price unit dinámico | AGENTS.md:L17-19 | `money_per_price_unit()` L246-250, `_money_per_price_unit_per_lot()` L146-174 | Código | VERIFICADO |
| Intrabar BE/partial | OPERATIONS.md:L306-308 | `cmd_manage` L603-617 | Código | VERIFICADO |
| Limit spread nudge | OPERATIONS.md:L308-310 | `cmd_place` L437-460 | Audit: eventos LIMIT_ENTRY_NUDGE | VERIFICADO |
| Circuit breaker pérdidas consecutivas = 4 | OPERATIONS.md:L162 | `MAX_CONSECUTIVE_LOSSES = 4` (L121) | `refresh_state_from_log()` (L159-200) | VERIFICADO — PERO el brief dice 999 (conflicto) |
| Pérdida diaria 10% | OPERATIONS.md:L163 | `MAX_DAILY_LOSS_PCT = 10.00` (L56) | guardrail_report() L362-363 | PARCIALMENTE VERIFICADO — solo pérdidas realizadas de cerrados, atribución por fecha de señal |
| Piso de equity 18% | OPERATIONS.md:L164 | `MAX_RISK_PCT_TOTAL_LOSS_CAP = 18.00` (L128) | guardrail_report() L364-366 | PARCIALMENTE VERIFICADO — solo intradía, resetea por sesión |
| BE al 50% hacia TP1 | OPERATIONS.md:L160 | `BE_FRACTION = 0.50` (L117) | cmd_manage L619 | VERIFICADO |
| Partial al 50% hacia TP2 | OPERATIONS.md:L161 | `PARTIAL_AT_FRACTION = 0.50` (L118) | cmd_manage L620-621 | PARCIALMENTE VERIFICADO — TP2 no se coloca en el broker, solo TP1 |
| Momentum alignment advisory | AGENTS.md:L44-51 | `_momentum_alignment()` L317-322 | Columna `mom_alignment` en ledger | VERIFICADO |
| Rollover 23:00-00:30 server → no entradas | Brief L23 | No implementado en executor | Depende del agente | CONTRADECIDO — OPERATIONS dice 00:00-01:00 |
| Spread < 50% ATR(M5) | Brief L26 | No en executor, en helper externo | `frival_read.py` | DOCUMENTADO SOLAMENTE |
| Tick age > 5 min → no trade | Brief L25 | No en executor | Depende del agente | DOCUMENTADO SOLAMENTE |

---

## 5. Registro de Hallazgos Priorizados

### 5.1 Críticos

| ID | Título | Severidad | Estado |
|---|---|---|---|
| F-01 | `close-all` no cancela órdenes pendientes — aplanamiento incompleto | Crítico | VERIFICADO |
| F-02 | Órdenes pendientes no contabilizadas en exposición ni posición máxima | Alto | VERIFICADO |
| F-03 | Verificación de margen errónea para USDJPY — bloquea sizing correcto | Alto | VERIFICADO |
| F-04 | Sin prevención de órdenes duplicadas — ejecuciones múltiples del mismo ID | Alto | VERIFICADO |
| F-05 | Persistencia no atómica del ledger — riesgo de truncación | Alto | VERIFICADO |
| F-06 | `manage` retira órdenes pendientes vivas como "stale" | Alto | VERIFICADO |
| F-07 | Data-quality gates no implementados en el executor | Alto | VERIFICADO |
| F-08 | Correlación USD ciega a dirección de la operación + bug off-by-one | Alto | VERIFICADO |
| F-09 | Semántica de sesión, piso de equity, y pérdida diaria inconsistentes | Alto | VERIFICADO |
| F-10 | Contrafactuales incluyen operaciones no ejecutables (sin fill) | Alto | VERIFICADO |
| F-11 | Gobernanza: agente puede modificar sus propios guardarraíles | Alto | VERIFICADO |
| F-12 | `test_kill_switch.py` opera sobre cuenta viva | Alto | VERIFICADO |

### 5.2 Medios

| ID | Título | Severidad | Estado |
|---|---|---|---|
| F-13 | Ledger omite o contradice ejecuciones reales | Medio | VERIFICADO |
| F-14 | PnL no incluye comisiones ni swaps | Medio | VERIFICADO |
| F-15 | Guardrail evaluado sobre precio de señal, no precio ejecutable | Medio | VERIFICADO |
| F-16 | Fallback silencioso en sizing (10,000 USD/unidad) | Medio | VERIFICADO |
| F-17 | Inconsistencia de timezone (UTC-8 en log_trade vs UTC-5 documentado) | Medio | VERIFICADO |
| F-18 | Gestión de parciales: TP2 no colocado, BE y partial al mismo precio | Medio | VERIFICADO |
| F-19 | Órdenes pendientes GTC sin expiración | Medio | VERIFICADO |
| F-20 | Gaps en audit trail y trazabilidad | Medio | VERIFICADO |
| F-21 | Conflictos entre documentos de operación | Medio | VERIFICADO |
| F-22 | Cobertura de tests casi nula para componentes core | Medio | VERIFICADO |
| F-23 | EOD review atribuye trades por fecha de señal, no de cierre | Medio | VERIFICADO |
| F-24 | Dead code, flags no operativos, umbrales inconsistentes | Bajo | VERIFICADO |

---

## 6. Hallazgos Detallados

### F-01 — CRÍTICO: `close-all` no cancela órdenes pendientes

**Categoría:** Ejecución / Safety  
**Referencias:** `order_executor.py:L765-L806`, `OPERATIONS.md:L25`  
**Verificación:** VERIFICADO en código

**Comportamiento observado:**
`cmd_close_all()` (L765-L806) itera exclusivamente sobre `mt5.positions_get()`. No llama a `mt5.orders_get()` en ningún momento. Las órdenes pendientes (límite/stop) que residen en el broker permanecen vivas después de un `close-all`. La función `cmd_cancel` sí cancela órdenes pendientes, pero requiere especificar `--id` o `--ticket` individualmente.

**Comportamiento esperado:**
`OPERATIONS.md:L25` define el estado seguro como "flat (0 positions, 0 pending)". Un `close-all` debería cancelar TODAS las órdenes pendientes además de cerrar TODAS las posiciones.

**Consecuencia:**
Tras activar el kill switch o el circuit breaker, las órdenes pendientes pueden ejecutarse, abriendo nuevas posiciones en contra de la intención de aplanamiento. Esto es particularmente grave porque el breaker de pérdidas consecutivas y el piso de equity no cancelan órdenes pendientes — solo bloquean nuevas entradas. Las órdenes ya enviadas al broker sobreviven al halt.

**Evidencia de auditoría:**
El audit log muestra `CLOSE_ALL` eventos (líneas 12, 28, 93, 98) que solo afectan posiciones abiertas. No hay eventos de cancelación de órdenes pendientes asociados a estos `CLOSE_ALL`.

**Corrección propuesta:**
Agregar al inicio de `cmd_close_all` (o como paso previo) una iteración sobre `mt5.orders_get()` que cancele cada orden pendiente mediante `TRADE_ACTION_REMOVE`, con registro en audit. Esto debe ocurrir ANTES de cerrar posiciones (para evitar que el cierre de una posición libere margen y permita que una orden pendiente se ejecute).

---

### F-02 — ALTO: Órdenes pendientes no contabilizadas en exposición

**Categoría:** Riesgo  
**Referencias:** `order_executor.py:L324`, `L343-356`, `L367`  
**Verificación:** VERIFICADO en código

**Comportamiento observado:**
- `guardrail_report()` en L324 solo llama a `mt5.positions_get()`, nunca a `mt5.orders_get()`.
- El cómputo de `open_risk_pct` (L343-356) itera exclusivamente sobre posiciones.
- `MAX_POSITIONS` (L367) compara `len(pos)` contra el límite — las órdenes pendientes no cuentan.
- `MAX_RISK_PCT_TOTAL` (L369) no incluye el riesgo de órdenes pendientes.

**Consecuencia:**
Es posible colocar múltiples órdenes límite simultáneas sobre el mismo símbolo o tesis de USD, excediendo tanto `MAX_POSITIONS` como `MAX_RISK_PCT_TOTAL` sin que ningún guardraíl lo detecte. Si todas se ejecutan, la exposición agregada puede superar ampliamente el 12% declarado.

**Corrección propuesta:**
Agregar `mt5.orders_get()` al cómputo de exposición. Contar cada orden pendiente como una "posición potencial" para `MAX_POSITIONS`. Calcular `open_risk_pct` sumando el riesgo nocional de cada orden pendiente (distancia SL × volumen × money_per_price_unit). Si `MAX_POSITIONS - len(pos) - len(orders) <= 0`, rechazar nuevas órdenes.

---

### F-03 — ALTO: Verificación de margen errónea para USDJPY

**Categoría:** Riesgo / Cálculo financiero  
**Referencias:** `order_executor.py:L326-L329`  
**Verificación:** VERIFICADO en código y audit log

**Comportamiento observado:**
```python
notional = vol * info.trade_contract_size * entry
margin_needed = notional / acct.leverage
```
Para USDJPY, `entry` está en JPY (ej. 157.754), no en USD. Multiplicar `contract_size` (100,000) por el precio en JPY produce un notional en JPY, no en USD. Esto infla el margen requerido aproximadamente por el tipo de cambio USD/JPY (~150×).

**Evidencia de auditoría:**
- Línea 34 del audit log: T017 con 0.05 lots USDJPY → `margin_level_after: 38.06%`, bloqueado por debajo de 100%.
- Línea 35: 0.02 lots → `margin_level_after: 94.56%`, todavía bloqueado.
- Solo 0.01 lots pasó (línea 38: `margin_level_after: 187.1%`).
- La guía de sizing en AGENTS.md sugiere ~0.6-0.7 lots para USDJPY con 5% de riesgo — este tamaño jamás pasaría el guardraíl de margen con el cálculo actual.

**Consecuencia:**
El escritorio está efectivamente impedido de operar USDJPY con tamaño económicamente relevante. Desde T025, todas las operaciones han sido exclusivamente XAUUSD — concentración total en un solo instrumento.

**Corrección propuesta:**
Usar `mt5.order_calc_margin()` para obtener el margen requerido directamente del broker, o convertir el notional a USD usando el tipo de cambio apropiado. `order_calc_margin` es la fuente autoritativa porque conoce las especificaciones exactas del contrato.

---

### F-04 — ALTO: Sin prevención de órdenes duplicadas

**Categoría:** Ejecución  
**Referencias:** `order_executor.py:L401-L522`  
**Verificación:** VERIFICADO en código y audit log

**Comportamiento observado:**
`cmd_place()` no verifica si ya existe una orden o posición activa para el `log_id` antes de llamar a `mt5.order_send()`. No consulta `mt5.orders_get()` ni `mt5.positions_get()` para detectar el comentario `FRIVAL_<id>`.

**Evidencia de auditoría:**
- T010 fue colocado 3 veces (tickets 254409488, 254409518, 254409594) en 6 minutos (líneas 3, 5, 10 del audit log). Dos de estas órdenes quedaron abiertas simultáneamente.
- T014 fue colocado 2 veces (tickets 254480502, 254481324) (líneas 25, 27).
- El ledger registra T010 como `CLOSED_UNFILLED` ("no broker execution existed"), lo cual es falso según el audit log.

**Consecuencia:**
Duplicación de exposición no intencionada. En un escenario sin kill switch activo, reemitir `place --id T0XX` duplica la posición.

**Corrección propuesta:**
Al inicio de `cmd_place`, buscar en `mt5.orders_get()` y `mt5.positions_get()` por el comentario `FRIVAL_<id>`. Si existe, rechazar con mensaje "ID already has a live order/position". Verificar también el status en `trade_log.csv` — si ya es OPEN/ORDER_PLACED, advertir.

---

### F-05 — ALTO: Persistencia no atómica del ledger

**Categoría:** Integridad de datos  
**Referencias:** `order_executor.py:L265-L281`, `log_trade.py:L83-L88`, `counterfactual.py:L88-L93`  
**Verificación:** VERIFICADO en código

**Comportamiento observado:**
- `save_log()` abre `trade_log.csv` en modo `"w"` (sobrescritura directa).
- No hay write-then-rename: si el proceso falla a mitad de escritura, el archivo queda truncado.
- No hay locking: ejecución concurrente de `order_executor.py manage` y `log_trade.py signal` pueden sobrescribirse mutuamente.
- `_save()` en `counterfactual.py` y en `log_trade.py` usan el mismo patrón `"w"`.
- `test_kill_switch.py` también reescribe `trade_log.csv` directamente.

**Evidencia de incidente:**
`IMPROVEMENTS.md:L104-115` documenta que `save_log` truncó el ledger durante T040 (la columna `be_executed` no estaba en el schema). Las filas T019-T020 se perdieron y tuvieron que ser reconstruidas desde git e historial del broker. `OPERATIONS.md:L313` reconoce que "write-then-rename would be even safer" pero no se implementó.

**Corrección propuesta:**
Implementar write-then-rename: escribir a `trade_log.csv.tmp`, verificar integridad (mínimo: mismo número de filas + header válido), luego `os.replace(tmp, LOG_PATH)`. Agregar un lock file (`trade_log.csv.lock`) para prevenir escritura concurrente.

---

### F-06 — ALTO: `manage` marca órdenes pendientes vivas como "stale"

**Categoría:** Gestión de posiciones  
**Referencias:** `order_executor.py:L549-L581`  
**Verificación:** VERIFICADO en código y audit log

**Comportamiento observado:**
La lógica de "stale row retirement" en `cmd_manage` (L552-L581) itera sobre filas con status `ORDER_PLACED` u `OPEN`. Si el símbolo de esa fila no está en `live` (mapeo de `positions_get()`), marca la fila como `CLOSED` con nota `AUTO-RETIRED`. Pero una orden pendiente (`ORDER_PLACED`) no tiene posición — precisamente está esperando ser ejecutada. `positions_get()` solo devuelve posiciones ya abiertas.

**Evidencia de auditoría:**
- T023 generó 17 eventos `STALE_ROW_RETIRED` consecutivos (líneas 63-83) mientras la orden estaba viva como `ORDER_PLACED`.
- T030: 6 eventos (líneas 111-116)
- T034: 7 eventos (líneas 132-138)
- T044: 3 eventos (líneas 191-193) mientras la orden estaba viva y fue posteriormente cancelada manualmente.

**Consecuencia:**
Afortunadamente, estos cambios son solo en memoria — `save_log()` no se llama después del retirement de filas stale. Pero si en el mismo ciclo ocurre un partial close (que SÍ llama a `save_log`), las filas incorrectamente marcadas CLOSED se persistirían al disco, perdiendo el rastro de órdenes legítimas.

**Corrección propuesta:**
Separar la lógica de retiro: solo retirar filas con status `OPEN` que no tengan posición viva (órdenes ya ejecutadas cuyo rastro se perdió). Para filas con status `ORDER_PLACED`, verificar contra `mt5.orders_get()` en lugar de `positions_get()`.

---

### F-07 — ALTO: Data-quality gates no implementados en el executor

**Categoría:** Ejecución / Riesgo  
**Referencias:** Brief L22-L30, `frival_read.py`  
**Verificación:** VERIFICADO por ausencia en código

**Comportamiento observado:**
El executor no implementa ninguna de las compuertas de calidad de datos listadas en el brief:
- Spread < 50% ATR(M5) — no verificado
- Tick age > 5 min — no verificado
- Rollover window — no verificado
- Clean ATR (excluyendo barras planas y bajo volumen) — no implementado; el executor usa ATR estándar que incluye la barra en formación
- Last M15 range < 2× ATR(M5) — no verificado
- Price in structural VOID — no verificado (depende del agente)

Estas compuertas dependen enteramente de que el agente las evalúe manualmente usando scripts auxiliares en `C:\Users\sosap\AppData\Local\Temp\kilo\`, que no están versionados ni son parte del repositorio.

**Consecuencia:**
Si el agente omite o evalúa incorrectamente una compuerta, el executor colocará la orden sin cuestionar. Esto es particularmente relevante para el rollover (spreads blown out, ticks stale) y para ATR contaminado por la barra en formación.

**Corrección propuesta:**
Implementar `tick_age > 300` (5 min) y `spread > 0.5 * ATR(M5)` como guardarraíles en `guardrail_report()`. Agregar una función `clean_atr()` que excluya barras con `high==low` o `tick_volume < 0.30 * median`. Verificar ventana de rollover usando el server clock.

---

### F-08 — ALTO: Correlación USD ciega a dirección + bug off-by-one

**Categoría:** Riesgo  
**Referencias:** `order_executor.py:L67-L68`, `L345-L356`  
**Verificación:** VERIFICADO en código y contrafactuales

**Comportamiento observado:**
El chequeo de correlación (L345-L356) agrupa posiciones por símbolo, no por dirección. `same_thesis` se incrementa si el símbolo de una posición abierta pertenece al mismo grupo (USD_STRONG o USD_WEAK) que el símbolo candidato, sin considerar si la posición es BUY o SELL.

- EURUSD BUY y XAUUSD SELL se cuentan como misma tesis (ambos en `USD_STRONG`), pero son apuestas opuestas sobre el dólar.
- La condición `same_thesis < MAX_SAME_THESIS` con `MAX_SAME_THESIS=2` y `same_thesis += 1` (el candidato mismo) efectivamente limita a 1 posición por tesis, no 2 como documentado.

**Evidencia:**
Los contrafactuales C028-C038 documentan setups bloqueados por "oposición" u "exposición" donde el agente aplicó manualmente una regla más estricta que la del código.

**Corrección propuesta:**
Reescribir el chequeo para considerar dirección: una posición BUY en `USD_STRONG_PAIRS` es dólar-débil; una SELL es dólar-fuerte. Agrupar por `(is_usd_strong_bet)` donde `is_usd_strong_bet = (side == 'SELL' and symbol in USD_STRONG_PAIRS) or (side == 'BUY' and symbol in USD_WEAK_PAIRS)`. Corregir el off-by-one en el límite.

---

### F-09 — ALTO: Semántica de sesión, piso de equity, y pérdida diaria

**Categoría:** Riesgo  
**Referencias:** `order_executor.py:L140-L200`, `L332-L338`, `L142`  
**Verificación:** VERIFICADO en código

**Comportamiento observado:**
1. **UTC vs server day:** `load_state()` (L142) usa `dt.datetime.utcnow()` para determinar `session_date`. `refresh_state_from_log()` (L195-198) usa server date para `daily_realised`. Si UTC y server difieren en día, la sesión se resetea a mitad de la jornada de trading del broker.
2. **daily_realised por fecha de señal, no de cierre:** `refresh_state_from_log()` filtra por `logged_at_server[:10]`. Un trade señalado a las 23:55 server del día X y cerrado a las 00:10 del día X+1 se atribuye al día X. Esto subestima/sobrestima la pérdida diaria real.
3. **Piso de equity solo intradía:** `MAX_RISK_PCT_TOTAL_LOSS_CAP` se calcula contra `session_start_equity`, que se resetea cada día UTC. Tres días consecutivos de -8% cada uno (-24% acumulado) nunca activan el piso de 18%.
4. **Consecutive-loss breaker sin reset diario:** El breaker solo se resetea con un trade ganador. Si se acumulan 4 pérdidas, el halt es permanente hasta que haya un win — pero el halt bloquea nuevas entradas, creando un deadlock.

**Corrección propuesta:**
Unificar sesión a server date. Atribuir pérdidas diarias por `exit_time` (o fecha del deal del broker), no por `logged_at_server`. Implementar un piso de equity absoluto (no reseteable) además del intradía. Agregar reset diario al breaker de pérdidas consecutivas.

---

### F-10 — ALTO: Contrafactuales incluyen operaciones no ejecutables

**Categoría:** Evidencia estadística  
**Referencias:** `counterfactual.py:L170-L222`, `counterfactuals.csv`  
**Verificación:** VERIFICADO en código y datos

**Comportamiento observado:**
`cmd_resolve()` no verifica si el precio alcanzó el nivel de entrada ANTES de evaluar TP/SL. Para una orden LIMIT, el precio debe primero tocar el entry para que la orden se ejecute. El código solo verifica `win['high'] >= tp` / `win['low'] <= sl` sin validar que `entry` estuviera en el rango.

**Evidencia en datos:**
De 12 contrafactuales con outcome TP_*, 4 muestran MAE negativo (precio nunca alcanzó entry):
- C004: mae=-4.19 → TP_ONLY pero entry nunca tocado
- C017: mae=-1.13 → TP_ONLY pero entry nunca tocado
- C037: mae=-1.31 → TP_ONLY pero entry nunca tocado
- C040: mae=-0.36 → TP_ONLY pero entry nunca tocado

Esto representa 33% de los TP contrafactuales que son falsos positivos.

**Adicional:**
- C023 tiene `would_be_r_usd = -2.273` para un outcome `TP_ONLY` — signo invertido.
- C002 tiene geometría invertida (BUY con SL arriba de entry y TP abajo).
- C001 tiene filas "BACKDATED".
- Los outcomes EXPIRED se excluyen del cálculo de mean R (sesgo de selección).

**Corrección propuesta:**
Agregar validación de fill en `cmd_resolve`: verificar que `max(high) >= entry` para BUY LIMIT o `min(low) <= entry` para SELL LIMIT antes de evaluar TP/SL. Corregir los signos de `would_be_r_usd`. Excluir filas con geometría invertida. Incluir EXPIRED como R=0 (costo de oportunidad) o excluirlos explícitamente con nota.

---

### F-11 — ALTO: Gobernanza — agente puede modificar sus propios guardarraíles

**Categoría:** Gobernanza  
**Referencias:** `kilo.json:L1-L13`, `IMPROVEMENTS.md:L5-L6`  
**Verificación:** VERIFICADO en configuración

**Comportamiento observado:**
- `kilo.json` otorga permisos `bash: allow`, `edit: allow`, `external_directory: allow`.
- El agente tiene acceso de escritura a `order_executor.py` y `AGENTS.md`.
- `IMPROVEMENTS.md:L5-L6` documenta que el operador autorizó "autonomous improvement" el 2026-10-06: "do it, do not wait for my authorization; the system should learn every time."
- El agente ha modificado `MAX_CONSECUTIVE_LOSSES` (de 999 a 4), `MIN_RR` (de 2.0 a 1.9), `MAX_RISK_PCT_PER_TRADE` (de 3.0 a 5.0), y `MIN_MARGIN_LEVEL` (de 500 a 100).

**Consecuencia:**
No existe una separación técnica entre el componente que decide trades y el componente que impone límites de riesgo. El agente puede editar `MAX_RISK_PCT_PER_TRADE` a 100% y continuar operando.

---

### F-12 — ALTO: `test_kill_switch.py` opera sobre cuenta viva

**Categoría:** Safety  
**Referencias:** `test_kill_switch.py:L40-L155`, audit log líneas 1-15, 93-98  
**Verificación:** VERIFICADO en código y audit log

**Comportamiento observado:**
El test:
1. Elimina cualquier `emergency_stop.txt` preexistente (L67-69) — si el operador había armado el kill switch, el test lo desarma.
2. Escribe una fila "decoy" en `trade_log.csv` (L77-93) — modifica el ledger de producción.
3. Ejecuta `close-all` contra la cuenta viva (L113) — cierra posiciones reales.
4. Desarma el kill switch (L128) y ejecuta `place --id TZZZ --market` (L132) — coloca una orden de mercado real (1.0 lot XAUUSD) que es bloqueada solo por los guardarraíles, no por el kill switch.
5. Si el test crashea entre pasos 1-5, el kill switch queda desarmado permanentemente.
6. SETUP_NEW_MACHINE.md:L132-134 requiere 8/8 en este test como gate para trading vivo.

**Evidencia de auditoría:**
El audit log muestra eventos en 2026-10-01 15:27-15:28 y 2026-10-05 14:56-17:11 que coinciden exactamente con la secuencia del harness: `ABORT_kill_switch`, `CLOSE_ALL`, `PLACE_ATTEMPT` con TZZZ.

**Corrección propuesta:**
Convertir el test para usar un mock de MT5 que nunca llame a la API real. Si no es posible, el test debe verificar `account_info().trade_mode == 0` (demo) y abortar si detecta cuenta viva.

---

### F-13 — MEDIO: Ledger omite o contradice ejecuciones reales

**Categoría:** Integridad de datos  
**Referencias:** `trade_log.csv`, audit log  
**Verificación:** VERIFICADO

**Evidencia:**
- T010: Ledger dice `CLOSED_UNFILLED` "no broker execution existed". Audit log muestra 3 ejecuciones reales (tickets 254409488, 254409518, 254409594) y CLOSE_ALL con profit -0.42.
- T014: Ledger dice `CLOSED_UNFILLED`. Audit log muestra 2 ejecuciones reales y CLOSE_ALL con profit +2.48.
- T016: Ledger registra pnl_usd=2.52 con r_multiple=0.40. El handoff `continua-operando.md` dice "R +0.35".
- T013: `fill_time_local` (2026-10-01 11:04:44) es anterior a `logged_at_local` (2026-10-02 05:04:15).
- T019 y T020 fueron reconstruidos desde broker history tras pérdida de filas.
- T022 usa `exit_price=4162.67000` pero en notas dice "STOP_LOSS 4162.00 (broker executed)". El pnl_usd=-33.30 usa el precio real de ejecución del broker (no 4162.00).

---

### F-14 — MEDIO: PnL no incluye comisiones ni swaps

**Categoría:** Cálculo financiero  
**Referencias:** `log_trade.py:L506-L512`, `reconcile_deals.py:L216-L219`  
**Verificación:** VERIFICADO

`log_trade.py exit` calcula PnL como suma de `deal.profit` del broker (que SÍ incluye swap y comisión en el campo profit de MT5). Sin embargo, `_resolve_realised_from_broker` solo se activa si hay historial disponible (últimos 14 días). El fallback `(exit_price - entry) * sign * volume * mv` no incluye swap ni comisión.

`reconcile_deals.py` L216-218 suma `gross + swap` pero no incluye `commission`. Si la cuenta tiene comisiones, el PnL reportado estaría sobreestimado.

---

### F-15 — MEDIO: Guardrail evaluado sobre precio de señal, no precio ejecutable

**Categoría:** Riesgo  
**Referencias:** `order_executor.py:L435-L460`, `L294-L318`  
**Verificación:** VERIFICADO

`guardrail_report()` usa `entry` del CSV (precio de señal). Pero `cmd_place()` modifica el precio para órdenes limit (spread nudge) y market (precio de mercado). El riesgo real después del nudge difiere del evaluado:
- T040: SL distance planeada 3.00, después del nudge ~3.19. El riesgo evaluado al 4.58% del equity pudo haber excedido 5% post-nudge.

---

### F-16 — MEDIO: Fallback silencioso en sizing

**Categoría:** Riesgo  
**Referencias:** `log_trade.py:L146-L174`  
**Verificación:** VERIFICADO

`_money_per_price_unit_per_lot()` tiene un fallback `CONTRACT_SIZE * TICK_VALUE_PER_LOT_PER_USD = 100 * 100 = 10000` cuando MT5 no está disponible. Este valor es correcto para XAUUSD pero 100× menor que el valor real para EURUSD (100,000) y ~16× mayor para USDJPY (~632). Si el sizing se ejecuta sin conexión a MT5, EURUSD se infra-dimensiona 100×.

---

### F-17 — MEDIO: Inconsistencia de timezone

**Categoría:** Datos  
**Referencias:** `log_trade.py:L40`, `OPERATIONS.md:L65`  
**Verificación:** VERIFICADO

`log_trade.py:L40` define `LOCAL_OFFSET_H = -8`. `OPERATIONS.md:L65` dice "Local = UTC-5". La diferencia de 3 horas afecta los timestamps `logged_at_local` en el ledger. El executor usa correctamente UTC-5 (L224).

---

### F-18 — MEDIO: Gestión de parciales — TP2 no colocado en broker

**Categoría:** Gestión de posiciones  
**Referencias:** `order_executor.py:L484-L494`, `L619-L621`  
**Verificación:** VERIFICADO

`cmd_place()` solo coloca `tp1` como take-profit en el broker (`"tp": rep["tp1"]`, L490). `tp2` no se envía al broker. Sin embargo, `cmd_manage` L620-621 calcula `partial_at` basado en `tp2` si existe. Si `tp2` está vacío en la señal, `partial_at` se calcula contra `tp1`, haciendo que el trigger de parcial y el de BE usen el mismo precio (50% de TP1).

---

### F-19 — MEDIO: Órdenes pendientes GTC sin expiración

**Categoría:** Ejecución  
**Referencias:** `order_executor.py:L493`  
**Verificación:** VERIFICADO

Las órdenes se colocan con `"type_time": mt5.ORDER_TIME_GTC` (Good-Till-Cancelled). No hay `type_expiration` configurado. Las órdenes pendientes sobreviven indefinidamente hasta que el agente las cancele manualmente o el broker las rechace. No hay un mecanismo automático de expiración por tiempo o por invalidación de estructura.

---

### F-20 — MEDIO: Gaps en audit trail

**Categoría:** Auditabilidad  
**Referencias:** `order_executor.py:L222-L230`, `L496-L505`  
**Verificación:** VERIFICADO

- `execute_pending` del pipeline legado no genera entradas en `execution_audit.jsonl`.
- `cmd_place` no audita el resultado de `order_check` (L497) — solo se incluye en `PLACE_RESULT`.
- Si `order_send` retorna `None` o `retcode != DONE`, el audit de `PLACE_RESULT` igual se escribe, pero el ledger no refleja `ORDER_FAILED` (el docstring dice que sí).
- No se almacena el `ticket` del broker en el ledger — solo en el audit log.
- El agente no persiste su razonamiento en un archivo separado; solo queda en los logs de la sesión.

---

### F-21 — MEDIO: Conflictos entre documentos de operación

**Categoría:** Documentación  
**Verificación:** VERIFICADO

| Tema | Brief | OPERATIONS.md | Código |
|---|---|---|---|
| MAX_POSITIONS | 1 neta | 3 | 3 |
| MAX_CONSECUTIVE_LOSSES | 999 (disabled) | 4 | 4 |
| Ventana rollover | 23:00-00:30 server | 00:00-01:00 server | No implementado |
| BE trigger | "on close, not on wick" | Intrabar extremes | Intrabar extremes |
| DAILY_ROUTINE.md | Referenciado para leer | Dice que es unrelated ML | Legacy pipeline |

---

### F-22 — MEDIO: Cobertura de tests casi nula

**Categoría:** Mantenibilidad  
**Verificación:** VERIFICADO

No existen tests para:
- `order_executor.py` (guardrail_report, cmd_place, cmd_manage, save_log, refresh_state_from_log)
- `log_trade.py` (_size_volume, cmd_exit, cmd_signal upsert)
- `counterfactual.py` (cmd_resolve, cmd_stats)
- `eod_review.py`
- `reconcile_deals.py`

Solo existe `test_kill_switch.py`, que como se documenta en F-12, opera sobre cuenta viva.

---

### F-23 — MEDIO: EOD review atribuye trades por fecha de señal

**Categoría:** Reporting  
**Referencias:** `eod_review.py:L93-L94`  
**Verificación:** VERIFICADO

`today = [r for r in tl if (r.get("logged_at_server") or "")[:10] == day]` atribuye trades al día de la señal, no al día en que se cerraron. Un trade señalado el día X y cerrado el día X+1 aparece en la review del día X con su PnL completo.

---

### F-24 — BAJO: Dead code e inconsistencias menores

- `extreme_stop_spacing_ok()` (L86-L102) no es llamada en ninguna parte.
- `--force` en `cmd_place` se parsea (L851) pero nunca se evalúa.
- `MIN_RR` en `log_trade.py` es 2.0, pero en `order_executor.py` es 1.9.
- `be_trigger_price` en el ledger tiene signo invertido (calculado como `entry - 0.5*sl_dist` para BUY en lugar de `entry + 0.5*tp1_dist`). No se usa en producción.

---

## 7. Evidencia de Desempeño y Limitaciones Estadísticas

### 7.1 Métricas del ledger (cálculo manual)

**Muestra completa (25 cerrados):**
- Total PnL: +$101.00 (aproximadamente)
- Total R: +2.87R
- Win rate: 10/25 = 40.0%
- Avg R: +0.11
- Best R: +2.60 (T038)
- Worst R: -1.28 (T043)

**Subconjunto autónomo consistente (T028-T043, N=12):**
- Total R: +1.27R
- Avg R: +0.106
- Win rate: 5/12 = 41.7%
- t-stat ≈ 0.24 (no significativo)

### 7.2 Concentración y sesgos

- **Concentración XAUUSD:** 100% de las operaciones desde T026 son XAUUSD. USDJPY está efectivamente excluido por el bug de margen (F-03). EURUSD no ha generado señales ejecutables en el período reciente.
- **Muestra pequeña:** 25 operaciones cerradas no constituyen evidencia estadística de edge. El intervalo de confianza del 95% para la media de R cubre valores negativos.
- **Momentum alignment:** Solo trades ALIGNED han sido ejecutados. Los trades AGAINST fueron cancelados (C040, T036). No hay muestra para evaluar el filtro.
- **Contrafactuales no fiables:** 33% de TP_ONLY son falsos positivos (sin fill). La estadística de LEVEL_ALREADY_TESTED (+0.38R) y NO_STRUCTURAL_TARGET (-0.95R) están potencialmente distorsionadas.

### 7.3 Limitaciones

- No se ejecutaron scripts; las métricas son de inspección manual del CSV.
- No se verificó que los fills del broker correspondan a los registrados.
- No se evaluó slippage, calidad de ejecución, ni costos de transacción implícitos.
- El desempeño pasado (8 días de operación) no predice desempeño futuro.
- No se realizó análisis de drawdown intradiario ni de rachas.

---

## 8. Mejoras Propuestas

### 8.1 Corrección de defectos confirmados

1. **F-01:** `close-all` debe cancelar todas las órdenes pendientes (`orders_get`) antes de cerrar posiciones.
2. **F-03:** Corregir cálculo de margen para USDJPY usando `order_calc_margin()`.
3. **F-04:** Agregar verificación de duplicados en `cmd_place` (buscar `FRIVAL_<id>` en órdenes y posiciones existentes).
4. **F-05:** Implementar write-then-rename con lock file en `save_log`, `_save` (log_trade), `_save` (counterfactual).
5. **F-06:** Corregir lógica de stale retirement para no tocar filas `ORDER_PLACED`.
6. **F-08:** Reescribir correlación USD para considerar dirección de la operación.
7. **F-10:** Agregar validación de fill en resolución de contrafactuales.
8. **F-16:** Eliminar fallback silencioso en `_money_per_price_unit_per_lot`; usar valor del broker o abortar.

### 8.2 Mejoras de seguridad y resiliencia

9. **F-02:** Contar órdenes pendientes en `MAX_POSITIONS` y `MAX_RISK_PCT_TOTAL`.
10. **F-07:** Implementar data-quality gates (tick age, spread/ATR, clean ATR) en el executor.
11. **F-09:** Unificar sesión a server date; piso de equity acumulativo; reset diario del breaker.
12. **F-12:** Migrar `test_kill_switch.py` a mock de MT5.
13. **F-19:** Agregar expiración a órdenes pendientes (ej. `ORDER_TIME_SPECIFIED` con D+1).

### 8.3 Mejoras de mantenibilidad

14. **F-22:** Agregar tests unitarios para `guardrail_report`, `_size_volume`, `cmd_manage`.
15. **F-13:** Reconciliar ledger contra audit log; corregir filas CLOSED_UNFILLED.
16. **F-20:** Almacenar `ticket` del broker en el ledger; agregar `ORDER_FAILED` como status.
17. **F-21:** Unificar documentación (MAX_POSITIONS, breaker, rollover).
18. **F-24:** Eliminar dead code (`extreme_stop_spacing_ok`); alinear `MIN_RR`.

### 8.4 Hipótesis de investigación (medir antes de implementar)

19. **Filtro de momentum:** Acumular ~20-30 muestras con trades AGAINST antes de decidir si es un veto.
20. **Filtro de whipsaw:** Medir si saltar retests cuando las últimas 3 H1 alternan con rangos >1.5× ATR mejora el desempeño.
21. **Continuación/stop-entry:** Medir frecuencia de "retest no llega" vs fills para decidir si agregar entradas de continuación.

---

## 9. Roadmap de Remediación Paso a Paso

### Fase 1 — Seguridad crítica (día 1)

| Paso | Hallazgo | Acción | Archivos | Validación |
|---|---|---|---|---|
| 1 | F-01 | Agregar cancelación de órdenes pendientes en `cmd_close_all` | `order_executor.py` | `close-all` con órdenes pendientes → 0 órdenes, 0 posiciones |
| 2 | F-03 | Usar `order_calc_margin()` en `guardrail_report` | `order_executor.py` | USDJPY 0.6 lots pasa margen con ~$700 equity |
| 3 | F-04 | Verificar duplicados `FRIVAL_<id>` antes de `order_send` | `order_executor.py` | `place --id T0XX` dos veces → segunda rechazada |
| 4 | F-12 | Envolver `test_kill_switch.py` con guarda `trade_mode==0` (demo) | `test_kill_switch.py` | Test aborta en cuenta viva |

### Fase 2 — Integridad de datos (día 2)

| Paso | Hallazgo | Acción | Archivos | Validación |
|---|---|---|---|---|
| 5 | F-05 | Write-then-rename + lock en los 3 save paths | `order_executor.py`, `log_trade.py`, `counterfactual.py` | Kill -9 durante save → archivo original intacto |
| 6 | F-06 | Separar retiro de OPEN vs ORDER_PLACED; verificar contra `orders_get` | `order_executor.py` | Cero STALE_ROW_RETIRED para órdenes vivas |
| 7 | F-13 | Corregir filas CLOSED_UNFILLED a CLOSED con PnL real (T010, T014) | `trade_log.csv` | `log_trade.py stats` refleja PnL correcto |

### Fase 3 — Riesgo y exposición (día 3)

| Paso | Hallazgo | Acción | Archivos | Validación |
|---|---|---|---|---|
| 8 | F-02 | Contar `orders_get()` en posición y riesgo | `order_executor.py` | 2 órdenes pendientes → `MAX_POSITIONS` rechaza tercera |
| 9 | F-08 | Correlación por dirección USD, corregir off-by-one | `order_executor.py` | XAUUSD BUY + EURUSD BUY = misma tesis; XAUUSD BUY + EURUSD SELL = opuestas |
| 10 | F-09 | Sesión unificada a server date, daily_realised por exit_time, piso acumulativo | `order_executor.py` | `executor_state.json` consistente con server date |

### Fase 4 — Ejecución y compuertas (día 4)

| Paso | Hallazgo | Acción | Archivos | Validación |
|---|---|---|---|---|
| 11 | F-07 | Agregar `tick_age` y `spread/ATR` a guardrail_report; clean ATR | `order_executor.py` | Tick stale → orden bloqueada |
| 12 | F-15 | Guardrail sobre precio post-nudge | `order_executor.py` | Riesgo evaluado coincide con riesgo ejecutado |
| 13 | F-19 | Agregar `type_expiration` a órdenes pendientes (D+1) | `order_executor.py` | Orden expira automáticamente |

### Fase 5 — Evidencia y medición (día 5+)

| Paso | Hallazgo | Acción | Archivos | Validación |
|---|---|---|---|---|
| 14 | F-10 | Validación de fill en contrafactuales; corregir signos | `counterfactual.py` | Resolver contrafactual existente → solo cuenta si entry fue tocado |
| 15 | F-16 | Abortar en lugar de fallback silencioso en sizing | `log_trade.py` | Sin MT5 → error explícito |

### Fase 6 — Mantenibilidad (siguiente sprint)

| Paso | Hallazgo | Acción |
|---|---|---|
| 16 | F-22 | Tests unitarios para `guardrail_report`, `_size_volume` |
| 17 | F-21 | Unificar `MAX_POSITIONS`, `MAX_CONSECUTIVE_LOSSES`, rollover en todos los docs |
| 18 | F-20 | Agregar `broker_ticket` al ledger; status `ORDER_FAILED` |
| 19 | F-24 | Eliminar dead code; alinear `MIN_RR` entre `log_trade.py` y `order_executor.py` |

---

## 10. Criterios de Aceptación y Validación Propuesta

### 10.1 F-01 (close-all cancela pendientes)

**Validación:** Ejecutar `order_executor.py close-all --force --reason "test"` con órdenes pendientes activas. Verificar que `mt5.orders_get()` retorna lista vacía y `mt5.positions_get()` retorna lista vacía. Verificar en `execution_audit.jsonl` eventos `CANCEL` para cada orden pendiente.

### 10.2 F-03 (margen USDJPY)

**Validación:** Con ~$700 equity, ejecutar `log_trade.py size --symbol USDJPY --entry 158.00 --sl 157.80 --risk-pct 5`. El output debe mostrar ~0.6 lots (no 0.01). Verificar que `order_executor.py place` acepta el tamaño.

### 10.3 F-04 (anti-duplicados)

**Validación:** Colocar una orden con `place --id T999`. Ejecutar `place --id T999` nuevamente. La segunda debe rechazar con mensaje "ID already has a live order/position". Verificar en audit log.

### 10.4 F-05 (write-then-rename)

**Validación:** Escribir una fila en `trade_log.csv`. Simular crash durante `save_log` (kill -9). Verificar que `trade_log.csv` mantiene su contenido original (sin truncar). Verificar que no existe `trade_log.csv.tmp` residual.

---

## 11. Decisiones de Política que Requieren Aprobación del Operador

1. **MAX_CONSECUTIVE_LOSSES** — ¿4 o 999? El código tiene 4; el brief dice 999 (disabled). El operador debe decidir explícitamente.
2. **MAX_POSITIONS** — ¿1 o 3? El brief dice "max 1 net position". El código tiene 3.
3. **Rollover window** — ¿23:00-00:30 o 00:00-01:00 server? Resolver la discrepancia.
4. **BE trigger** — ¿Al cierre de vela o intrabar? El brief dice "on close, not on wick". El código implementa intrabar.
5. **Piso de equity acumulativo** — ¿Mantener solo intradía (18% por sesión) o agregar piso absoluto (ej. 30% desde máximo)?
6. **Autonomía de modificaciones** — ¿Debe el agente seguir teniendo permiso de editar `order_executor.py` y `AGENTS.md`?
7. **Frecuencia de `manage` durante rollover** — ¿Debe `manage` ejecutarse durante la ventana de rollover? Actualmente se ejecuta, pero `place` está bloqueado por el agente.

---

## 12. Índice de Evidencia

| Tipo | Referencia | Descripción |
|---|---|---|
| Código | `order_executor.py:L765-L806` | cmd_close_all sin orders_get |
| Código | `order_executor.py:L324-L356` | Exposición sin órdenes pendientes |
| Código | `order_executor.py:L326-L329` | Cálculo erróneo de margen USDJPY |
| Código | `order_executor.py:L401-L420` | cmd_place sin verificación de duplicados |
| Código | `order_executor.py:L265-L281` | save_log no atómico |
| Código | `order_executor.py:L549-L581` | Stale retirement toca ORDER_PLACED |
| Código | `order_executor.py:L86-L102` | extreme_stop_spacing_ok dead code |
| Código | `order_executor.py:L332-L338` | Session UTC vs server day |
| Código | `order_executor.py:L159-L200` | daily_realised por logged_at_server |
| Código | `log_trade.py:L40` | LOCAL_OFFSET_H = -8 vs documentado -5 |
| Código | `log_trade.py:L160-L162` | Fallback silencioso 10000 USD/unidad |
| Código | `counterfactual.py:L170-L222` | Sin validación de fill |
| Código | `test_kill_switch.py:L67-L155` | Opera sobre cuenta viva |
| Código | `kilo.json:L1-L13` | Permisos bash+edit |
| Datos | `execution_audit.jsonl:L1-L15` | T010 triple ejecución |
| Datos | `execution_audit.jsonl:L25-L28` | T014 doble ejecución |
| Datos | `execution_audit.jsonl:L50-L51` | BE_MOVE y PARTIAL_CLOSE con log_id T010 (erróneo) |
| Datos | `execution_audit.jsonl:L52-L194` | >70 STALE_ROW_RETIRED |
| Datos | `trade_log.csv:L10` | T010 CLOSED_UNFILLED |
| Datos | `trade_log.csv:L14` | T014 CLOSED_UNFILLED |
| Datos | `counterfactuals.csv:L3` | C004 mae=-4.19, entry no tocado |
| Datos | `counterfactuals.csv:L40` | C040 mae=-0.36, entry no tocado |
| Datos | `counterfactuals.csv:L23` | C023 would_be_r_usd negativo para TP_ONLY |
| Datos | `executor_state.json:L2` | session_date 2026-10-10, session_start_equity 0 |
| Docs | `ACTIVE MONITOR — Frival desk.md:L23` | Rollover 23:00-00:30 |
| Docs | `ACTIVE MONITOR — Frival desk.md:L46,L85` | MAX_POSITIONS=1, MAX_CONSECUTIVE=999 |
| Docs | `OPERATIONS.md:L22-L24` | "order_executor.py is the ONLY component" |
| Docs | `OPERATIONS.md:L155,L162` | MAX_POSITIONS=3, MAX_CONSECUTIVE=4 |
| Docs | `IMPROVEMENTS.md:L5-L6,L104-L115` | Autorización autónoma; truncación del ledger |
| Docs | `SETUP_NEW_MACHINE.md:L132-L134,L159-L161` | test_kill_switch como gate; MAX_CONSECUTIVE=999 |
| Git | `.git/logs/HEAD:L4-L20` | 17 commits 2026-10-06 a 2026-10-09 |

---

## 13. Confirmación de Límites de Auditoría

- **No se ejecutó ningún script del proyecto.** Todas las conclusiones provienen de inspección estática de código, datos y documentación.
- **No se modificó ningún archivo existente del proyecto.** La única escritura autorizada fue este informe en `auditorias/`.
- **No se realizaron acciones de trading.**
- **No se inspeccionaron credenciales ni archivos de configuración con secretos.**
- Las verificaciones marcadas como "VERIFICADO" lo son respecto a la implementación inspeccionada, no respecto al comportamiento en vivo.
- Donde la evidencia fue insuficiente, se marcó explícitamente como "PARCIALMENTE VERIFICADO", "DOCUMENTADO SOLAMENTE", o "NO EVALUABLE".
- **Ningún hallazgo constituye una recomendación de trading.** Este informe es una evaluación técnica de controles y implementación.

---

*Fin del informe de auditoría.*