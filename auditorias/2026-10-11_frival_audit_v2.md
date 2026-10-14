# Informe de Auditoría v2 (segunda pasada) — Frival Execution Desk

## 1. Metadatos, alcance y límites de solo-auditoría

| Campo | Valor |
|---|---|
| Fecha | 2026-10-11 (hora del entorno 18:42 UTC; la zona horaria local no está expuesta por el entorno) |
| Modelo | `openrouter/anthropic/claude-sonnet-5.5` (identificador expuesto por el entorno) |
| Tipo | Refinamiento de auditoría. Revisión estática de fuentes, datos locales y documentación primaria MQL5. |
| Informe original | `auditorias/2026-10-10_frival_audit.md` (no modificado) |
| Alcance | Escritorio de ejecución autónoma Frival (`frival/order_executor.py`, `log_trade.py`, `counterfactual.py`, `reconcile_deals.py`, `eod_review.py`, `market_context.py`, `test_kill_switch.py`) y sus artefactos. El pipeline ML legado (`main.py`, `run_daily*.{py,bat}`, `DAILY_ROUTINE.md`) y `execution_bot/`, `gold_rules/` se tratan solo como superficie de riesgo, no como desk. |
| Documentación primaria consultada | MQL5 Python: `history_deals_get` https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py ; `order_calc_margin` https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcmargin_py ; `order_check` https://www.mql5.com/en/docs/python_metatrader5/mt5ordercheck_py (solo lectura; no se envió contenido del repositorio). |

**Límites respetados:** no se ejecutó ningún script, test ni comando de proyecto; no se conectó a MT5; no se colocó, modificó ni canceló ninguna orden; no se tocó el kill switch; no se modificó ningún archivo existente. Única escritura: este informe.

**Declaración de transparencia sobre el informe v1.** Al revisar mi propio trabajo encontré fallas que quedan corregidas aquí:
1. v1 declaró como modelo `deepseek/deepseek-v4-pro`; el identificador real expuesto es el indicado arriba. Era un metadato incorrecto.
2. v1 usó un comando de terminal (creación del directorio `auditorias/`) pese a la instrucción de no usar terminal en esa tarea. No tuvo efectos sobre archivos del proyecto, pero es una desviación de procedimiento.
3. v1 se rotuló "Completo" a pesar de muestreos, filas truncadas y componentes sin leer. Esa etiqueta se retira.
4. v1 citó rangos de líneas del audit log (p. ej. "L52-L194", conteos por orden) que no verifiqué individualmente. Aquí solo se citan líneas efectivamente leídas o devueltas por búsqueda, y se marcan las no re-verificadas.

**Convención de estados de evidencia** (por mecanismo / ocurrencia histórica / consecuencia financiera):
`DOC` documentación confirmada · `EST` implementación estática confirmada · `LOC` registros locales respaldan · `BRK` broker/runtime confirmado (esta auditoría **no** tiene evidencia BRK propia; solo la que quedó en artefactos locales) · `HIP` hipótesis / no evaluable.

---

## 2. Resumen ejecutivo

Lo que sigue respaldado tras la segunda pasada:

- **F-01 (Crítico, retenido y ampliado):** `cmd_close_all` solo itera `positions_get()` (`order_executor.py:L771`). No cancela órdenes pendientes, no verifica estado final plano, no filtra por propiedad (cierra toda posición de la cuenta), no reintenta, y trata solo `TRADE_RETCODE_DONE` como éxito (`L798`). El kill switch bloquea nuevas colocaciones pero no retira pendientes ya aceptadas.
- **F-03 (Alto, retenido, corregido en magnitud):** el nocional para USDJPY se calcula multiplicando por el precio en JPY. El propio audit log lo evidencia: nocional 157754 para 0.01 lot y `margin_level_after` 187% frente a `order_check` del broker (margen 8.76, nivel 6883.56%) en la misma ventana. La sobreestimación del margen respecto al broker es ~37× en ese caso, no "~150×" como dijo v1.
- **F-04 (Alto, corregido):** no hay prevención de reenvío; hay evidencia local de **múltiples envíos aceptados** para T010 (3) y T014 (2). Que hayan coexistido como posiciones simultáneas **no está establecido** por los registros locales.
- **F-05 (Alto, corregido):** escritura no atómica y sin lock del ledger; hay incidente documentado de truncación. La criterio de aceptación de v1 ("no queda `.tmp` tras un crash") era incorrecto y se reemplaza.
- **F-10 (Alto, corregido):** el resolvedor contrafactual no modela el fill, **pero la corrección de v1 estaba invertida** (BUY LIMIT / SELL LIMIT intercambiados). Se corrige y se recalcula el "33%" con su denominador exacto (4 de 12 resultados TP, todos SELL LIMIT con MAE negativo).
- **F-25 (nuevo, Alto):** la reversión del filtro de momentum a "advisory" se justificó con C040 (+3.14R), pero C040 tiene MAE −0.36: el nivel de entrada nunca fue tocado en la ventana de 30 barras. La evidencia citada no respalda la decisión.

Retrocedidos o retirados: **F-16** (aritmética y dirección de v1 eran erróneas; baja a Bajo), **F-11** (baja a Medio; atribución de cambios al agente no establecida), **F-09** (se divide; se retira el "deadlock permanente"), **F-07** (corregido: el ATR "clean" sí existe, pero fuera del executor), **F-14** (corregido en sentido contrario: `deal.profit` **no** incluye comisión/swap/fee), **F-22** (matizado).

No se afirma ningún edge estadístico. Los estadísticos t e intervalos de confianza de v1 se **retiran** por no tener base reproducible.

---

## 3. Cambios respecto al informe original

| Hallazgo / afirmación | Afirmación original | Conclusión revisada | Motivo | Evidencia |
|---|---|---|---|---|
| Metadatos | Modelo `deepseek/deepseek-v4-pro`; "Completo" | Modelo `openrouter/anthropic/claude-sonnet-5.5`; cobertura parcial | Metadato inventado/incorrecto; muestreo y componentes sin leer | Entorno de la sesión; sección 4 |
| Equity "~$695 a la fecha de la auditoría" | Presentado como actual | Observación histórica: $695.21 en `frival/reviews/2026-10-09.md` (sección Result), generada 2026-10-09 ~23:24 server. Equity actual **no evaluable**. `executor_state.json` tiene `session_start_equity: 0.0` | Sin lectura de cuenta; el artefacto es del día previo | `reviews/2026-10-09.md`; `executor_state.json` |
| "+$101 en 25 cerradas", t≈0.24/0.41, IC 95% | Métricas y estadísticos presentados | Suma manual **no verificada**; t e IC **retirados** | Cálculo a mano sin base reproducible | Sección 9 |
| F-10 condiciones de fill | BUY LIMIT: `max(high) >= entry`; SELL LIMIT: `min(low) <= entry` | **Invertidas.** SELL LIMIT (Bid ≥ entry) → `max(high) >= entry`; BUY LIMIT (Ask ≤ entry) → `min(low)` ≤ entry − spread (si barras son Bid) | Semántica de órdenes límite; v1 contradecía incluso su propio uso de MAE | `counterfactual.py:L200-L205`; sección 8.1 |
| F-10 "33% falsos positivos" | 4/12 = tasa de falsos positivos | 4/12 = 33.3% de las filas con resultado TP cuya ventana nunca tocó la entrada (todas SELL LIMIT). No es tasa de error del método, ni se extrapola | Denominador explicitado | `counterfactuals.csv` filas C004, C017, C037, C040 |
| F-10 "EXPIRED = R 0" | Propuesto como opción | **Retirado.** EXPIRED mezcla "sin fill" y "con fill sin resolver en el horizonte" | No se puede asignar R sin MTM/horizonte | `counterfactual.py:L186-L198, L216-L219` |
| F-16 fallback 10,000 | "Correcto para XAUUSD; 100× menor que EURUSD; infra-dimensiona EURUSD" | 10,000 = 100×100 (`log_trade.py:L54-L55,L160-L169`). Valor de referencia XAUUSD = 100 → fallback **100× mayor**. EURUSD ≈ 100000 → fallback **10× menor** → sobre-dimensiona 10×. USDJPY ≈ 632–635 → fallback ≈16× mayor → infra-dimensiona | Volumen ∝ 1/valor; v1 invirtió dirección y razones | `log_trade.py:L146-L169, L265-L284`; `AGENTS.md` (valores vivos citados) |
| F-14 PnL | "`deal.profit` incluye swap y comisión" | **Falso.** La API define campos separados `commission`, `swap`, `profit`, `fee`. El código suma solo `d.profit` (`log_trade.py:L356`) | Documentación primaria | URL `history_deals_get`; `log_trade.py:L356` |
| F-03 ejemplo USDJPY | "≈0.6 lots" para ~$700, entry 158.00, SL 157.80, 5% | ≈0.27 lots con valor ≈632/lot/1.00. 0.6–0.7 de `AGENTS.md` corresponde a SL ≈ 0.09 (1.5×ATR M5), no a 0.20 | Aritmética (sección 8.2) | `AGENTS.md` tabla de sizing |
| F-03 factor | "~150×" | Nocional ≈ 158× (precio JPY); margen vs `order_check` ≈ 37× en la muestra | Comparación con broker local | audit L36–L39 (lectura L1–L48) |
| F-03 "causó concentración en XAUUSD" | Atribución causal general | Solo respaldado para USDJPY T017/T024/T025; causalidad general **no establecida** | Sin evidencia que conecte todos los eventos posteriores | audit L34–L39; ledger T017/T025 |
| F-02 criterio de aceptación | "2 pendientes → la tercera rechazada" con `MAX_POSITIONS=3` | Incorrecto. Con política documentada (3), 2+1=3 se permite; se rechaza la cuarta bajo política estricta propuesta | Aritmética | `order_executor.py:L57`; `OPERATIONS.md` |
| F-04 | Múltiples tickets = exposición duplicada | Múltiples envíos aceptados; coexistencia **no establecida** | Sin deals/positions en el broker | audit L3,L5,L10 (T010), L25,L27 (T014) |
| F-05 | "No queda `.tmp` residual tras crash" | Retirado; atomicidad ≠ concurrencia; `.tmp` huérfano es aceptable si la recuperación lo tolera | Semántica de `replace` + crash | sección 12 |
| F-07 "clean ATR no implementado" | Ausente | Implementado en `counterfactual.py:L119-L124` y helper temporal; **no** usado por el executor | Lectura directa | `counterfactual.py:L119-L124`; `order_executor.py` ATR |
| F-09 "deadlock permanente" | Breaker 4 pérdidas = halt permanente | Se retira: la racha se recomputa del ledger cada ciclo; reanuda con una victoria o intervención del operador. Hallazgo real: comentario documenta reset por "nuevo día" que no existe | Código vs comentario | `order_executor.py:L121,L159-L200` |
| F-11 | "El agente modificó constantes" | Capacidad técnica confirmada; atribución **no establecida** (un solo autor git; comentarios citan decisiones del operador) | Metadatos git | `.git/logs/HEAD`; `kilo.json` |
| F-19 expiración | D+1 | Sin duración propuesta; alinear con horizonte aprobado (VENCIMIENTO por señal en notas) y con `ORDER_TIME_SPECIFIED` si el broker lo admite | Requiere decisión del operador | `order_check` doc (ORDER_TIME_*) |
| F-22 tests | "Casi nula/no existen" | No hay evidencia de tests que importen los módulos del desk (búsqueda repo-wide de imports); `test_kill_switch.py` los invoca por subprocess contra cuenta viva. Directorios de tests de otros componentes no leídos | Búsqueda acotada | grep imports (sin resultados) |
| F-06 conteos | "17 / 6 / 7 / 3 eventos" por orden | Solo T044 (3 eventos, ventana viva) y T023 (muchos eventos, líneas ~63–83 devueltas por búsqueda) están respaldados; los demás conteos no se re-verificaron | Verificabilidad | sección 7 |
| F-18 | "tp2 vacío hace partial = BE" y TP2 no colocado | Confirmado con datos: BE→partial separados por un ciclo (T040 13:45:29→14:00:25; T041 19:30:40→19:45:18). Nuevo: `realised_r` del audit ≠ R del ledger (0.02 vs 0.40 en T040) | Datos | audit L170–L171, L176–L177; ledger T040/T041 |

---

## 4. Inventario de cobertura y limitaciones

**Leído completo (en la sesión de auditoría, dos pasadas):** `OPERATIONS.md`, `ACTIVE MONITOR — Frival desk.md`, `AGENTS.md`, `order_executor.py`, `log_trade.py`, `counterfactual.py`, `reconcile_deals.py`, `eod_review.py`, `market_context.py`, `mt5_path.py`, `test_kill_switch.py`, `IMPROVEMENTS.md`, `SETUP_NEW_MACHINE.md`, `reviews/INDEX.md` y reviews 2026-10-07/08/09, `executor_state.json`, `counterfactuals.csv` (41 líneas), `kilo.json`, `.gitignore`, `continua-operando.md` (parcial: L1–L70 + búsquedas), helpers temporales `frival_read.py`, `frival_bars.py`, `frival_backfill.py` (en `%TEMP%\kilo`, fuera del repo).

**Muestreado o parcial:** `trade_log.csv` (45 líneas; algunas filas truncadas a 2000 caracteres por la herramienta); `execution_audit.jsonl` (L1–L48 leídas; resto por búsquedas dirigidas de eventos); `gold_rules/run_gold_rules.py` (L1–L110, L255–L334); `execution_bot/core/exec_d1_terminal.py` (L1–L130); `DAILY_ROUTINE.md` (L1–L80); `execution_bot/config/settings.yaml` (completo).

**No leído:** `frival/context/*.json|md` (solo listado por nombre); `main.py` y modelos ML; `dashboard/`; `fx_rules_backtest/`; `quant-personal-fund/`; tests en `execution_bot/tests`, `gold_rules/tests` y de otros componentes; `frival/config/.env` (credenciales; no se accede).

**Limitaciones de esta segunda pasada:** los números de línea de `order_executor.py` fuera de L765–L806 y `log_trade.py` fuera de los rangos re-leídos provienen de mi lectura de la primera pasada y **no se re-abrieron**; deben re-validarse antes de usarse como referencia formal. No se pudo ejecutar `git status/diff`, por lo que **no puedo demostrar con git** que los archivos existentes están sin cambios; solo que mis herramientas fueron de lectura más esta escritura.

**Requieren validación en runtime/broker (no disponible aquí):** semántica real de `ORDER_TIME_SPECIFIED` por símbolo (`SYMBOL_EXPIRATION_MODE`); tipo de barra (Bid/Last) del feed (`SYMBOL_CHART_MODE`); si la cuenta cobra comisión; leverage efectivo por símbolo; existencia de órdenes/posiciones actuales; correspondencia de tickets de T010/T014 con deals; zona horaria/DST del servidor tras el cambio de horario.

---

## 5. Matriz revisada documentación → implementación

Leyenda: V = verificado (estático) · P = parcial · D = solo documentado · C = contradicho · N = no evaluable.

| Regla documentada | Documentación | Implementación | Evidencia local | Estado | Brecha / matiz |
|---|---|---|---|---|---|
| `order_executor.py` única autoridad de órdenes | `AGENTS.md`; `OPERATIONS.md` | Docstring del executor; otros módulos con `order_send`: `gold_rules/run_gold_rules.py` (`TRADE_ACTION_SLTP`), `execution_bot/core/order_manager.py`, `exec_d1_terminal.py` | Config `execution_bot/config/settings.yaml`: `mode: demo`, `terminal_scope: demo` | P | Es regla de política; existen rutas de código con capacidad de orden. Su activación contra la cuenta live **no evaluada** |
| Riesgo por trade ≤ 5% | `AGENTS.md` | `MAX_RISK_PCT_PER_TRADE` en `guardrail_report` | Ledger: risk_pct hasta 5.00 (T022) | V | Calculado sobre precio de señal, no precio ejecutable (F-15) |
| Máx. posiciones | Brief: "Max 1 net position… pending orders count as exposure"; `OPERATIONS.md`: 3 | `MAX_POSITIONS = 3` (L57); solo `positions_get()` | — | C (doc vs doc) y P | Conflicto documental; el código sigue `OPERATIONS.md` e ignora pendientes |
| Riesgo agregado ≤ 12% | `OPERATIONS.md` | `open_risk_pct` sobre posiciones | — | P | No incluye pendientes |
| Cap tesis USD = 2 | `OPERATIONS.md` | `MAX_SAME_THESIS=2`, candidato incluido en el conteo → efectivo 1; agrupa por símbolo, ciego a dirección | CF C028–C038 describen bloqueos coherentes con "efectivo 1" | P | Interpretación del off-by-one a confirmar con fixture |
| R:R ≥ 1.9 | `AGENTS.md` | `MIN_RR = 1.9` | Ledger T031 rr 1.96 | V | `log_trade.py` usa 2.0 solo para una etiqueta |
| Kill switch bloquea entradas | `OPERATIONS.md` | `kill_switch_active()` en `cmd_place` | Audit L11 `ABORT_kill_switch` (T ZZZ) | V | No retira pendientes ni toca `manage` |
| `close-all` lleva a estado seguro "flat (0 pos, 0 pend)" | `OPERATIONS.md` | `cmd_close_all` solo posiciones | — | C | F-01 |
| `place --force` prohibido | `AGENTS.md` | `--force` parseado, no leído en `cmd_place` | — | V | No-op; el mensaje de bloqueo lo sugiere |
| `reconcile_deals.py` solo lectura | `AGENTS.md` | Lectura de MT5, pero `apply` **escribe** `trade_log.csv` | — | P | "Solo lectura" es respecto a MT5, no al ledger |
| Sizing por riesgo, no lotes fijos | `AGENTS.md` | `_size_volume` (`log_trade.py:L265-L284`) | Ledger | V | Fallbacks silenciosos (F-16); ejemplo USDJPY de `AGENTS.md` choca con F-03 |
| BE al 50% de TP1; partial al 50% de TP2 | `OPERATIONS.md` | `cmd_manage` | Audit BE_MOVE→PARTIAL_CLOSE separados un ciclo | P | Sin tp2 el partial usa el mismo nivel que BE |
| Breaker 4 pérdidas | `OPERATIONS.md`; brief dice 999 | `MAX_CONSECUTIVE_LOSSES = 4` | `executor_state.json`: 2 | C (doc vs doc) | Brief y `SETUP_NEW_MACHINE.md` desactualizados |
| Pérdida diaria 10% / piso 18% | `OPERATIONS.md` | `refresh_state_from_log`, `guardrail_report` | `executor_state.json` | P | Ancla = equity del primer envío del día UTC; ver F-09 |
| Gates de datos (spread/ATR, tick age, rollover, M15/ATR) | Brief | No están en el executor | Helper `%TEMP%\kilo\frival_read.py` | D | Dependen del agente y de un helper no versionado |
| Rollover | Brief: 23:00–00:30 server; `continua-operando.md`: corregido a 00:00–01:00 | No implementado | — | C (doc vs doc) | |
| Clean ATR | Brief | Solo `counterfactual.py` y helper | — | P | Executor usa ATR simple con barra en formación |
| Momentum AGAINST no es veto | `AGENTS.md` | Solo registro `mom_alignment` | Todas las ejecutadas del subconjunto reciente son ALIGNED | V | Base de la decisión cuestionada (F-25) |
| EOD review diaria | `OPERATIONS.md` | `eod_review.py` | `reviews/` | P | Atribución por fecha de señal |

---

## 6. Registro priorizado de hallazgos (revisado)

Estados respecto a v1: **R** retenido · **C** corregido · **D** degradado · **S** dividido · **W** retirado · **P** pendiente de evidencia · **N** nuevo.

| ID | Título | Sev. | Estado v1→v2 | EST | LOC | BRK/HIP | Confianza |
|---|---|---|---|---|---|---|---|
| F-01 | `close-all` incompleto (sin pendientes, sin verificación, sin ámbito) | Crítico | R+ampliado | Sí | Parcial | HIP: estado real en broker | Alta (mecanismo) |
| F-02 | Pendientes fuera de límites de exposición | Alto→Medio-Alto | S: 2a defecto de implementación vs brief; 2b decisión de política | Sí | — | HIP | Alta (mecanismo) |
| F-03 | Margen USDJPY: unidades erróneas | Alto | R+C | Sí | Sí (audit L34–L39) | HIP: leverage efectivo | Alta |
| F-04 | Sin idempotencia en `place` | Alto | C | Sí | Sí (múltiples envíos aceptados) | HIP: coexistencia | Alta (mecanismo) / Media (impacto) |
| F-05 | Persistencia no atómica y sin lock | Alto | C | Sí | Sí (truncación documentada) | — | Alta |
| F-06 | `manage` trata pendientes `ORDER_PLACED` como stale | Alto→Medio-Alto | C | Sí | Sí (T044) | — | Alta |
| F-07 | Gates de calidad de datos fuera del executor; ATR con barra en formación | Alto→Medio | C | Sí | — | HIP: edad de tick | Media |
| F-08 | Tesis USD ciega a dirección; off-by-one probable | Alto | R | Sí | Indirecta | — | Media-Alta |
| F-09 | Semántica de sesión/diaria/piso/racha | Alto | S (9a–9d) | Sí | Sí | — | Media-Alta |
| F-10 | Contrafactuales sin modelo de fill | Alto | C | Sí | Sí | HIP: serie Bid/Ask | Alta (mecanismo) |
| F-11 | Gobernanza: sin separación decisión/límites | Medio | D | Sí | No atribuible | — | Media |
| F-12 | `test_kill_switch.py` opera contra la cuenta conectada | Alto | R | Sí | Sí (L11–L15) | HIP: qué cuenta | Alta |
| F-13 | Ledger contradice/omite ejecuciones | Medio-Alto | R+reforzado | — | Sí | HIP: deals reales | Media |
| F-14 | PnL excluye comisión/swap/fee | Medio | C | Sí | — | HIP: costos reales | Alta (mecanismo) |
| F-15 | Guardrails sobre precio de señal | Medio | R | Sí | Sí (nudge) | — | Alta |
| F-16 | Fallback silencioso de valor monetario | Bajo | C+D | Sí | — | HIP: alcanzabilidad | Alta (aritmética) |
| F-17 | Offsets de reloj inconsistentes y fijos | Medio | R | Sí | Sí (columnas locales) | HIP: DST | Alta |
| F-18 | Partial/BE/R de eventos | Medio | C | Sí | Sí | — | Alta |
| F-19 | Pendientes GTC sin expiración de broker | Medio | R (sin D+1) | Sí | — | HIP: modos de expiración | Alta |
| F-20 | Trazabilidad incompleta (ticket, ORDER_FAILED) | Medio | R | Sí | — | — | Alta |
| F-21 | Conflictos documentales | Medio | R+ampliado | — | Sí | — | Alta |
| F-22 | Cobertura de tests del desk | Medio | D | Búsqueda acotada | — | HIP | Media |
| F-23 | EOD por fecha de señal; "session-start" = primer envío | Medio | R | Sí | Sí | — | Alta |
| F-24 | Código muerto / flags / umbrales | Bajo | R | Sí | — | — | Alta |
| F-25 | Decisión del filtro de momentum apoyada en C040 sin fill | Alto | N | — | Sí | — | Alta |
| F-26 | Filas contrafactuales escritas a mano (signo, tiempos, campos vacíos) | Medio-Alto | N | — | Sí | — | Alta |
| F-27 | Cifras de `OPERATIONS.md` §11 no reconciliadas con el ledger | Medio | N | — | Parcial | HIP | Media |
| F-28 | Ventanas de historial distintas (14 d vs 30 d) con degradación silenciosa | Bajo-Medio | N | Sí | — | — | Media |

---

## 7. Hallazgos detallados

Formato por hallazgo: mecanismo (EST) · ocurrencia (LOC) · consecuencia (BRK/HIP) · supuestos · validación pendiente · propuesta (en prosa, sin código).

### F-01 — `close-all` no garantiza estado seguro (Crítico; retenido y ampliado)
- **Documentación (DOC):** `OPERATIONS.md` define estado seguro como plano (0 posiciones, 0 pendientes). `close-all` exige `--force` o kill switch armado (`order_executor.py:L766-L768`).
- **EST:** itera solo `mt5.positions_get()` (`L771`); envía un cierre por posición (`L779-L792`) con `magic` 20261001 y comentario `FRIVAL_CLOSE`, **pero no filtra** por propiedad: cierra toda posición de la cuenta. `res is None` → registra `CLOSE_FAILED` y continúa (`L793-L797`). El evento `CLOSE_ALL` se escribe aunque `done` sea falso (`L798-L800`; el campo `done` distingue). No hay reintento, ni segunda consulta de posiciones/órdenes, ni resultado de proceso que indique "no plano". Si `_mt5()` no inicializa, el proceso termina (patrón `sys.exit(1)` documentado en la lectura de `_mt5`; no re-abierto en esta pasada).
- **Distinciones:** (a) *bloquear nuevas colocaciones*: lo hace `cmd_place` con el kill switch; (b) *cancelar pendientes*: solo `cmd_cancel` y por orden; (c) *cerrar posiciones*: `close-all`; (d) *confirmar estado final*: nadie.
- **LOC:** el audit local muestra eventos `CLOSE_ALL`/`CLOSE_FAILED` (L7, L12 en lectura de L1–L48). No hay evento de cancelación asociado a `close-all` en lo leído.
- **Consecuencia (HIP):** una pendiente ya aceptada puede llenarse después de un aplanamiento; un cierre rechazado o `DONE_PARTIAL` queda reportado como `REJECT` sin acción; broker no disponible aborta a mitad.
- **Propuesta (política y diseño, no código):** separar tres capacidades: *bloqueo*, *desmontaje* y *verificación*. El desmontaje debe, en orden: impedir nuevas colocaciones; cancelar pendientes **propias** (identificadas por `magic`/prefijo de comentario, con opción explícita y separada para "toda la cuenta"); cerrar posiciones propias; volver a consultar broker y repetir hasta plano o hasta agotar un máximo de intentos; terminar con un resultado explícito *PLANO / NO PLANO* y registro de la lista residual. Manejar: fallo de cancelación (reintentar y escalar), pendiente que se llena durante la cancelación (la nueva posición aparece en la re-consulta y se cierra), cierre parcial (reintentar con volumen remanente), invocación repetida (idempotente), broker inaccesible (salida con estado "desconocido", nunca "plano").
- **Validación pendiente:** solo en mock offline y, con autorización expresa, en demo aislada (sección 12).

### F-02 — Exposición por órdenes pendientes (S: 2a defecto vs brief; 2b política)
- **2a (EST + DOC conflictiva):** el brief dice "Max 1 net position… Pending orders count as exposure". `OPERATIONS.md` y el código fijan `MAX_POSITIONS = 3` y comparan contra `len(positions_get())`; `open_risk_pct` también se calcula solo sobre posiciones. Los pendientes no se cuentan.
- **2b (política):** si `MAX_POSITIONS` significa "posiciones abiertas" (lectura literal del código) o "exposición potencial" (lectura del brief) es **decisión del operador**. La propuesta de contar pendientes es una política más estricta, no un bug confirmado, salvo que el brief se declare vinculante.
- **Corrección del criterio v1:** con límite documentado de 3, "2 pendientes + 1 nueva" = 3 → permitida. Para la política estricta propuesta ("abiertas + pendientes ≤ N") la prueba debe usar fixtures explícitos: p. ej. N=3, 1 posición + 2 pendientes → la candidata (cuarta) se rechaza; 1 posición + 1 pendiente → se acepta.
- **Consecuencia (HIP):** si todas las pendientes se llenan, el riesgo agregado puede exceder 12%. No hay evidencia local de que haya ocurrido.

### F-03 — Estimación de margen con unidades incorrectas (Alto; retenido)
- **EST:** el nocional se calcula como volumen × `trade_contract_size` × precio de entrada y luego se divide por apalancamiento (`order_executor.py:~L326-L329`, líneas no re-abiertas). Para un par con USD como moneda base (USDJPY), 1 lot = 100 000 USD; multiplicar por el precio JPY produce un valor no expresado en USD.
- **LOC (lectura audit L34–L39):** USDJPY 0.01 lot: nocional registrado 157754; `margin_level_after` 187%; el `order_check` del broker en la misma ventana devolvió margen 8.76 y `margin_level` 6883.56% (campos en el orden documentado de `MqlTradeCheckResult`: retcode, balance, equity, profit, margin, margin_free, margin_level). El `order_check` ya se invoca (`L497`) pero su resultado no gobierna la decisión.
- **Aritmética:** nocional real ≈ 1 000 USD; con 500:1 sería 2 USD, no 8.76 − existente. Por tanto ni la fórmula "corregida" con el apalancamiento de cuenta replica al broker (leverage efectivo por símbolo/nivel **no evaluable** aquí).
- **Distinciones:** margen requerido de la orden propuesta (`order_calc_margin`), margen existente (`account_info().margin`), margen libre, nivel de margen post-trade estimado (`equity/(margen existente + nuevo)`), y aceptación del broker (`order_check`/`order_send`).
- **Limitación de `order_calc_margin` (DOC):** la referencia MQL5 indica que estima el margen "sin considerar las órdenes pendientes y posiciones abiertas actuales". Por sí solo no da el nivel post-trade; hay que combinarlo con el estado de la cuenta, o usar `order_check` (que sí devuelve margin, margin_free y margin_level post-solicitud) como verificación primaria, y `order_calc_margin` como estimación independiente.
- **Ejemplo recalculado:** equity ≈ 700 USD, riesgo 5% = 35 USD; entrada 158.00, SL 157.80 → distancia 0.20; valor monetario histórico documentado ≈ 632 USD por 1.00 por lot (valor del broker en el momento; **no** constante universal) → volumen = 35 / (0.20 × 632) ≈ 0.277 → ~0.27 lot tras redondeo hacia abajo. Los "0.6–0.7 lots" de `AGENTS.md` corresponden a SL ≈ 0.09 (≈1.5×ATR(M5)): 35/(0.09×632) ≈ 0.62. **v1 queda corregido:** no se conserva "≈0.6 lots" para ese ejemplo.
- **Causalidad:** el margen bloqueó tamaños USDJPY en T017/T024/T025 (audit L34–L39 y notas del ledger). Que haya causado la concentración posterior en XAUUSD **no está evidenciado**; la concentración puede deberse a selección del agente, estructura de mercado u otros gates.
- **Criterio de aceptación (sin lote predeterminado):** el cálculo corregido debe coincidir, dentro de una tolerancia definida por el operador, con un fixture controlado y con la estimación del broker en una demo aislada, para USDJPY, EURUSD y XAUUSD, y la decisión final debe usar el resultado post-solicitud del broker cuando exista.

### F-04 — Idempotencia de `place` (Alto; corregido)
- **EST:** `cmd_place` no consulta órdenes/posiciones existentes con el comentario `FRIVAL_<id>` ni el estado de la fila antes de `order_send` (`L401-L522`; sin chequeo en lo leído). Un `signal` repetido con el mismo `log_id` hace upsert y puede revertir el estado de una fila (`log_trade.py` cmd_signal), lo que reabre el camino a un segundo `place`.
- **LOC:** T010: tres `PLACE_RESULT` con retcode 10009 (audit L3, L5, L10) en ~6 minutos; hay además `CLOSE_FAILED` (L7) y `CLOSE_ALL` (L12). T014: dos envíos (L25, L27) y un `CLOSE_ALL` con profit +2.48 (L28). **Estos registros establecen envíos aceptados, no necesariamente posiciones simultáneas ni fills distintos;** la coexistencia requiere deals/positions del broker (NO EVALUABLE). T010 fue declarado por el operador como prueba de capacidad.
- **Distinciones necesarias:** reintento tras timeout (resultado desconocido), orden pendiente aceptada, fill, posición concurrente, y reemplazo tras cancelación **confirmada**.
- **Límite de un pre-check simple:** consultar solo estado actual deja ambigüedad si la orden se llenó y cerró (SL/TP) antes del reintento, o si el timeout ocurrió tras la aceptación del broker. Además, el intervalo entre verificación y envío no es atómico: dos procesos pueden pasar ambos el chequeo.
- **Propuesta:** una *reserva* persistente por `log_id` (estado `ENVIANDO` con identificador de solicitud) creada de forma exclusiva antes del envío; reconciliación obligatoria de resultado desconocido contra historial de órdenes/deals (por comentario y por `position_id`) antes de permitir reintento; un `log_id` en estado terminal o ya enviado no puede volver a colocarse sin una transición explícita aprobada. Esto da idempotencia a nivel de aplicación; el broker no ofrece clave de idempotencia nativa en lo consultado (confirmar).

### F-05 — Persistencia del ledger (Alto; corregido)
- **EST:** `save_log` (`order_executor.py:L265-L281`), `_save` de `log_trade.py` y de `counterfactual.py` y `reconcile_deals.py:L80-L85` escriben el CSV en modo "w" directamente, con columnas derivadas de la primera fila; sin lock, sin copia de seguridad previa.
- **LOC:** `IMPROVEMENTS.md` y notas del ledger (T040) documentan truncación por esquema (`be_executed`) y reconstrucción manual; hay un script ad hoc (`%TEMP%\kilo\frival_backfill.py`) que reescribe el ledger en bloque.
- **Distinciones:** (1) *atomicidad de reemplazo* (escribir a archivo temporal en el mismo volumen y reemplazar) protege contra truncación por crash, **no** contra pérdida de actualizaciones; (2) *exclusión mutua* con ciclo leer-modificar-escribir bajo lock protege contra actualizaciones perdidas entre `manage`, `log_trade` y `counterfactual`; (3) *recuperación*: un temporal huérfano tras crash es aceptable si el arranque lo detecta, lo ignora o lo archiva y el original permanece válido y verificable.
- **Corrección de v1:** no se exige ausencia de temporal inmediatamente tras cada crash; se exige que el original permanezca íntegro y que la recuperación sea determinista.
- **Propuesta:** originales inmutables y copias con procedencia antes de cualquier migración; validación de esquema y de número de filas antes del reemplazo; registro de quién/cuándo modificó cada fila.

### F-06 — Retiro de filas stale (Alto→Medio-Alto; corregido)
- **EST:** en `cmd_manage` (`L552-L581`, lectura de la primera pasada) las filas con estado `ORDER_PLACED`/`OPEN` cuyo símbolo no está en `live` (posiciones abiertas) se marcan `CLOSED` en memoria. Una orden pendiente no es posición, luego el caso normal de una pendiente viva dispara el retiro. `save_log` solo se invoca en el camino del cierre parcial, de modo que el estado erróneo se persiste solo si coincide un partial en la misma ejecución.
- **LOC:** T044 está bien acotada: STALE_ROW_RETIRED a 05:45, 06:01 y 06:16 (hora local del executor) mientras la orden estaba colocada (05:32) y fue cancelada a las 06:18; evidencia de línea ~L189–L194 (L190 no individualmente leída). T023 muestra muchos eventos en ~L63–L83 (conteo no re-verificado). Comparar tiempos de T023 con el ledger no es fiable por el desfase de relojes (F-17).
- **Matiz:** v1 llamó "viva" a una orden basándose en eventos de este tipo; en lo estricto, el audit local acredita lo que el código creía, y solo T044 tiene colocación y cancelación confirmadas por retcode en la misma ventana.
- **Propuesta:** contrastar `ORDER_PLACED` con `orders_get()` y `OPEN` con `positions_get()`/deals; no cerrar filas por ausencia de posición.

### F-07 — Gates de datos y ATR (Alto→Medio; corregido)
- **EST:** el executor no implementa edad de tick, spread/ATR, rollover ni M15/ATR; el ATR del executor usa `copy_rates_from_pos(...,0,...)`, que incluye la barra en formación en el promedio de 14 (efecto: ATR sesgado, dirección dependiente del rango parcial). El ATR "clean" existe en `counterfactual.py:L119-L124` y en el helper temporal, no en el executor.
- **HIP:** el helper temporal calcula la edad del tick como `now_utc − tick.time`; si `tick.time` está en reloj de servidor, el resultado se desplaza horas y el gate de "5 minutos" podría no funcionar. No evaluable sin ejecución; y el helper `last_M15_range` usa la barra en formación.
- **Matiz:** ausencia en el executor ≠ ausencia en el sistema: los gates están en el prompt del agente. Se clasifica como "dependiente del agente y de un helper no versionado en `%TEMP%`".

### F-08 — Correlación de tesis USD (Alto; retenido)
- **EST:** las posiciones se agrupan por pertenencia del símbolo a `USD_STRONG`/`USD_WEAK` sin considerar el lado; el candidato se cuenta dentro del conteo, y el criterio `< MAX_SAME_THESIS` → efectivo 1 con valor 2 (inferencia de lectura; confirmar con fixture).
- **LOC:** los contrafactuales C028–C038 describen bloqueos "por exposición/oposición" que coinciden con esa lectura, pero son notas del agente, no ejecución del guardrail.
- **Propuesta:** definir primero la política (qué es "misma tesis"), luego expresarla como tabla de decisión por símbolo×lado.

### F-09 — Semántica de sesión, pérdida diaria, piso y racha (S)
- **9a Ancla de sesión (EST+LOC):** `session_start_equity` se fija tras el primer envío exitoso del día UTC; hoy vale 0.0 (`executor_state.json`). En `reviews/2026-10-09.md`, "session-start equity" coincide con el equity del día (695.21), coherente con esa semántica. No es el equity de apertura del día.
- **9b Reloj (EST):** `load_state` usa fecha UTC; `daily_realised` usa fecha de servidor sobre `logged_at_server` (fecha de la señal, no del cierre).
- **9c Piso 18% (EST):** relativo al ancla del día; no limita drawdown multi-día. Si debe hacerlo es **decisión de política**.
- **9d Racha (EST+DOC):** el comentario documenta reset por "nuevo día"; el código recomputa la racha desde el ledger y no resetea por día. Se retira el término "deadlock permanente": la racha termina con una victoria o intervención. Orden de eventos por `exit_time_local` (reloj −8) con fallback a `logged_at_server` (+3) mezcla relojes; T019 tiene ambos vacíos (ordena primero). El valor actual (2) es consistente con los dos últimos cierres perdedores (T042, T043).
- **Propuesta:** documentar semántica deseada primero; cualquier reseteo de racha debe ser una acción explícita del operador con registro, no automático.

### F-10 — Resolución contrafactual sin modelo de fill (Alto; corregido)
- **EST (`counterfactual.py:L158-L226`):** la ventana son las `horizon_bars` (30) barras M5 posteriores a la barra de la señal (`L173-L177`); `tp_hit`/`sl_hit` se evalúan sobre toda la ventana sin exigir fill previo (`L183-L198`); si TP y SL aparecen y el primer índice de TP es estrictamente menor, TP_FIRST, en caso contrario (incluido misma barra) SL_FIRST — desempate conservador no documentado; MFE/MAE se miden desde `entry` sobre **toda** la ventana, incluida la parte previa al fill (`L200-L205`); `would_be_r_usd` = `rr_tp1` si TP, −1.000 si SL, vacío si EXPIRED (`L216-L219`). `cmd_stats` calcula la media sobre filas con R no vacío y el "naive hit rate" sobre todas las resueltas, es decir, **denominadores distintos** (`L236-L249`).
- **Definición de MAE:** SELL: `max(high) − entry`; BUY: `entry − min(low)`. Un MAE negativo significa que, en la ventana, el extremo adverso nunca alcanzó la entrada.
- **Reglas de fill correctas (supuesto: barras = Bid; tipo de barra del feed **no confirmado**, `SYMBOL_CHART_MODE`):**
  - SELL LIMIT (por encima del mercado) se activa al Bid ≥ entry → condición necesaria `max(high) ≥ entry`. Con barras Bid no requiere ajuste de spread.
  - BUY LIMIT (por debajo) se activa al Ask ≤ entry → Bid ≤ entry − spread → `min(low) ≤ entry − spread`. Sin serie Ask, usar spread conocido (o conservador) y declararlo.
  - SELL STOP se activa al Bid ≤ entry → `min(low) ≤ entry`.
  - BUY STOP se activa al Ask ≥ entry → Bid ≥ entry − spread → `max(high) ≥ entry − spread`.
  - MARKET: sin espera, con spread y slippage; el precio de fill no es el de la señal.
  - **v1 estaba equivocado:** había intercambiado BUY LIMIT y SELL LIMIT.
- **Condiciones adicionales que ningún criterio de barra resuelve:** (i) el fill debe ocurrir **antes** de evaluar salidas, y MFE/MAE del trade deben calcularse solo desde el fill; (ii) una barra que contenga entrada y salida posible no permite conocer el orden intrabarra; (iii) una barra que contenga SL y TP tras el fill es ambigua (el código asume SL); (iv) gaps y slippage de stop (el ledger muestra −1.28R en T043) no están modelados; (v) tocar el precio no garantiza fill en cola; (vi) la elegibilidad del setup antes del supuesto fill (la orden no existía hasta la señal) está respetada por la ventana `time > sig_ts` pero la parte restante de la barra de señal se excluye.
- **LOC — recuento reproducible (manual, desde las columnas `side, order_type, outcome, mae, mfe` de `counterfactuals.csv`):** hay 12 filas con resultado TP (C001, C004, C006, C014, C015, C016, C017, C023, C027, C034, C037, C040). De ellas, 4 son SELL LIMIT con MAE negativo (C004 −4.19; C017 −1.13; C037 −1.31; C040 −0.36): la entrada no fue tocada en la ventana. C023 (SELL STOP) tiene MFE 0.00844 > 0 y C027 (BUY STOP) MFE 11.76 > 0: consistentes con activación. C034 tiene MAE 0.26 (toque marginal). **4/12 = 33.3% es un recuento descriptivo de filas, no una tasa de falsos positivos del método ni extrapolable.** Sobre las 33 filas LIMIT, 5 no tocaron la entrada (también C036, resultado EXPIRED).
- **EXPIRED:** mezcla "sin fill" (p. ej. C036) con "fill sin resolución en el horizonte" (varias con MAE > 0). No se asigna 0R automáticamente.
- **Métricas que deben separarse (denominadores):** (a) tasa de fill = filas con activación / filas consideradas; (b) expectativa condicional al fill = R medio de filas con fill y salida resuelta / esas filas; (c) resultado por setup considerado = incluye no llenadas (R=0 por no operar) y llenadas sin resolver (necesita MTM o horizonte extendido), reportado aparte; (d) tasa de expiración.
- **Propuesta de definición de pendiente, no código:** modelar fill por tipo de orden con la regla anterior y spread declarado; iniciar excursiones y salidas en la barra de fill; marcar `FILL_AMBIGUOUS` cuando entrada y salida cohabiten barra; marcar `EXIT_AMBIGUOUS` cuando TP y SL cohabiten; registrar costos y slippage de stop como parámetros.

### F-11 — Gobernanza (Medio; degradado)
- **EST/DOC:** `kilo.json` concede `bash`, `edit` y `external_directory` (según lectura); `IMPROVEMENTS.md` documenta autorización del operador para mejoras autónomas. No existe separación técnica entre quien decide operaciones y quien puede editar límites.
- **LOC:** `.git/logs/HEAD` muestra un único autor para todos los commits; por lo tanto **no** se puede atribuir al agente (frente al operador) cada cambio de constante. Los comentarios de código citan decisiones del operador (p. ej. umbral de 4).
- **Decisión de política:** si el desk debe poder modificar su propio executor. Propuesta de control compensatorio: revisión humana de cambios a constantes de riesgo, no prohibición automática.

### F-12 — `test_kill_switch.py` (Alto; retenido)
- **EST:** el script (a) elimina un `emergency_stop.txt` preexistente, (b) reescribe `trade_log.csv` añadiendo una fila señuelo, (c) ejecuta `close-all` con el kill switch armado, (d) lo desarma y (e) envía `place` con una orden de mercado señuelo de gran tamaño que debe ser bloqueada por guardrails. `SETUP_NEW_MACHINE.md` y el brief lo presentan como compuerta previa a operar en vivo.
- **LOC:** la secuencia `ABORT_kill_switch`, `CLOSE_ALL`, `PLACE_ATTEMPT` con `TZZZ` aparece en el audit (L11–L13 en lectura L1–L48), compatible con una ejecución del harness el 2026-10-01; no existe artefacto con resultado "8/8".
- **Matiz:** que opere sobre "la cuenta live" depende de a qué cuenta esté conectado el terminal; el desk documenta cuenta live. No evaluable aquí.
- **Propuesta:** sustituir por prueba con broker simulado y, para integración, demo aislada con guardas de tipo de cuenta; el original queda como evidencia histórica.

### F-13 — Ledger vs audit (Medio-Alto; reforzado)
- **LOC:** T010 y T014 figuran `CLOSED_UNFILLED` con la nota "no broker execution existed" (`trade_log.csv` líneas 11 y 15), mientras que (i) el audit registra envíos aceptados y `CLOSE_ALL` para ambos (L3, L5, L10, L12; L25, L27, L28), (ii) la propia nota de T010 dice que fue cerrado inmediatamente tras el fill y que el PnL realizado es costo de ejecución, y (iii) `continua-operando.md` reporta T014 +$2.48. Las notas de T010 y T014 repiten el mismo texto de retiro.
- **T040 (línea 41):** `volume` = 0.05 (remanente), `risk_usd` = 33.00 con `sl_distance` 3.0 (implica 0.11 lots originales = 0.06 + 0.05) y R = 0.38 = 12.66/33. Reconstrucción manual tras truncación; el campo `volume` no representa el volumen original.
- **Corrección de la remediación:** **no** editar filas a partir de logs de envío. Exigir evidencia de orden/deal/posición del broker (ticket, `position_id`, deals de entrada y salida con profit, commission, swap, fee), preservar valores originales, motivo y referencia de evidencia en una tabla de migración separada.

### F-14 — PnL realizado y costos (Medio; corregido)
- **DOC (primaria):** `TradeDeal` expone `commission`, `swap`, `profit` y `fee` como campos separados.
- **EST:** `log_trade._resolve_realised_from_broker` suma `d.profit` de todos los deals del `position_id` de entrada (`L355-L356`), ventana de 14 días (`L344`), emparejando el deal de entrada por símbolo, `DEAL_ENTRY_IN` y comentario exacto `FRIVAL_<id>` (`L349-L350`). `reconcile_deals.py` suma profit de los deals OUT más swap de todos los deals (según lectura previa), sin comisión ni fee. Los eventos de audit `PARTIAL_CLOSE`/`CLOSE_ALL` usan `position.profit`/estimaciones por tick, no deals (p. ej. T040: audit 13.08 vs ledger 12.96 por deal 238755649).
- **LOC/HIP:** no se puede determinar con artefactos locales si la cuenta cobra comisión ni su cuantía. Subestimación o sobreestimación de PnL: **no evaluable**.
- **Definición propuesta de PnL neto realizado por posición:** suma, sobre todos los deals con el mismo `position_id`, de `profit + commission + swap + fee`, sin doble conteo de transacciones de costo separadas (si el broker liquida comisión en un deal de balance independiente, se debe vincular o declarar). Supuestos: el broker informa costos en la moneda de la cuenta; todos los deals de la posición caen dentro de la ventana consultada; R = PnL neto / riesgo planificado (definir si el denominador incluye spread/costos estimados).
- **Limitaciones:** la ventana de 14/30 días degrada a estimación por precio sin aviso fuerte (F-28); los parciales se asocian por posición, no por comentario.

### F-15 — Guardrails evaluados sobre el precio de señal (Medio; retenido)
- **EST+LOC:** `guardrail_report` usa `entry` de la fila; `cmd_place` aplica nudge de spread (LIMIT) o precio de mercado y no recalcula riesgo/RR. T040: nivel 4119.50 colocado a 4119.31 (SELL LIMIT), SL 4122.50 → distancia efectiva 3.19 frente a 3.00 evaluada. Con riesgo planificado cercano al tope, el nudge puede excederlo. Para MARKET, el precio de la solicitud difiere del `entry` (audit T010: 4178.86/4178.37/4175.44 vs 4178.19). Magnitud sobre el riesgo en %: **no calculada**, depende del volumen original (ver F-13).

### F-16 — Fallback de valor monetario (Bajo; corregido y degradado)
- **EST:** `CONTRACT_SIZE = 100.0` y `TICK_VALUE_PER_LOT_PER_USD = 100.0` (`log_trade.py:L54-L55`); el fallback devuelve su producto = **10 000 USD por 1.00 de precio por lot** (`L160, L162, L166, L169`) cuando falla el import, `initialize`, la información de símbolo o `trade_tick_size`, o salta una excepción.
- **Unidades y supuestos:** el valor correcto es `trade_tick_value / trade_tick_size` por símbolo (`L167`). Valores de referencia citados en el propio código y en `AGENTS.md` (observación histórica del broker, no constantes universales): XAUUSD 100; EURUSD 100 000; USDJPY ≈ 632–635.
- **Razones:** fallback/valor = XAUUSD 100×; EURUSD 0.1×; USDJPY ≈ 15.8×. Como volumen = presupuesto / (distancia × valor), un valor sobrestimado reduce el volumen y uno subestimado lo aumenta: XAUUSD infra-dimensionado ≈100×; **EURUSD sobre-dimensionado ≈10×**; USDJPY infra-dimensionado ≈16×. v1 afirmó lo contrario para EURUSD y presentó 10 000 como correcto para XAUUSD.
- **Mitigaciones:** el executor recomputa el valor con su propia conexión y bloquea riesgo > tope; el piso `volume_min` (`L283-L284`) puede en cambio superar el tope y debe ser bloqueado por el executor. Alcanzabilidad: solo si `log_trade` corre sin MT5 operativo; entonces `risk_usd`, `risk_pct_equity` y R del ledger se escriben con valores inconsistentes y el equity cae al fallback de referencia. **Hallazgo válido y de menor severidad:** fallo silencioso en vez de error explícito.

### F-17 — Relojes (Medio; retenido)
- **EST:** `log_trade.py:L39-L40`: `SERVER_OFFSET_H = 3`, `LOCAL_OFFSET_H = -8`; otros módulos usan −5 como local. `executor` fija +3 sin DST. El audit usa −5 para `ts_local`; las columnas `*_local` del ledger pueden estar en −8. Los tiempos del ledger y del audit no son directamente comparables. Cambio de horario del servidor: **no evaluable** sin confirmar el calendario del broker.

### F-18 — BE, partial y R de eventos (Medio; corregido)
- **LOC:** BE_MOVE y PARTIAL_CLOSE separados por un ciclo (T040: L170→L171; T041: L176→L177). `realised_r` del audit usa como denominador la distancia al nivel del partial: T040 0.02 vs R de ledger sobre riesgo 33 → ≈0.40 para ese tramo; T041 0.01 vs ≈0.22; T019 0.16. No es comparable con el R del ledger. Con `tp2` vacío (T019, T040, T041) el nivel del partial coincide con el de BE.
- **EST (lectura previa):** la condición de partial requiere que el SL ya sea igual a la entrada; el valor `p.sl` de la iteración actual es previo al movimiento, lo que difiere el partial al siguiente ciclo. El precio del partial es el de tick en ese momento, no el precio histórico del cruce intrabarra, lo cual es correcto respecto a la advertencia de no confundir cruce histórico con precio de ejecución, pero el `realised_usd` del audit sigue siendo estimación.
- **Pendiente:** validar con fixture (precio actual ya retrocedido bajo la entrada cuando el trigger histórico se cumple; rechazo por distancia de stops/freeze; volumen mínimo; repetición tras fallo de persistencia).

### F-19 — Expiración de pendientes (Medio; retenido sin duración)
- **EST:** pendientes con `ORDER_TIME_GTC` y sin expiración (según lectura). Las notas del ledger citan un VENCIMIENTO por señal gestionado por el agente. La documentación MQL5 de `order_check` lista `ORDER_TIME_GTC/DAY/SPECIFIED/SPECIFIED_DAY`.
- **Propuesta:** vincular la expiración al horizonte operativo aprobado por señal (no a un D+1 genérico), usando el tipo de expiración que cada símbolo admita (**requiere confirmación** del modo de expiración del símbolo). Es decisión de política; la duración la fija el operador.

### F-20 — Trazabilidad (Medio; retenido)
- Docstring dice `ORDER_FAILED` en fallo de envío; el código deja la fila `PENDING_FILL` con el motivo (según lectura). El ticket del broker no se almacena en el ledger. Si `order_send` tiene éxito y falla la persistencia posterior, no hay registro de reparación. El razonamiento del agente vive en notas del ledger y en la sesión, no en un archivo propio.

### F-21 — Conflictos documentales (Medio; ampliado)
| Tema | Brief | `OPERATIONS.md` | Código |
|---|---|---|---|
| Posiciones | 1 neta + pendientes | 3 | 3, solo abiertas |
| Racha | 999 desactivado | 4 | 4 |
| Rollover | 23:00–00:30 server | 00:00–01:00 server (corrección) | No implementado |
| BE | "al cierre, no mecha" | extremos intrabarra | extremos intrabarra |
| `DAILY_ROUTINE.md` | lectura previa al primer ciclo | pipeline ML no relacionado | `DAILY_ROUTINE.md` declara ejecución LIVE |
| Gates en unidades | "Clean ATR(M5) < 1.0 → datos congelados" | — | Valor expresado en unidades de oro; aplicado a FX bloquearía todo |
| Mandato adicional | — | — | No se encontró referencia a Trader1000 en el repositorio (búsqueda de texto) |

### F-22 — Tests (Medio; degradado)
No hay evidencia, en una búsqueda repo-wide de imports (`import/from order_executor|log_trade|counterfactual|eod_review`), de tests unitarios de los módulos del desk. `test_kill_switch.py` los ejercita por subprocess. Existen tests de componentes legados (p. ej. `execution_bot/tests/test_exec_d1_terminal.py`) que no se leyeron. La búsqueda no cubre importaciones dinámicas ni invocaciones por subprocess.

### F-23 — EOD (Medio; retenido)
`eod_review.py` atribuye por `logged_at_server` (fecha de señal), se genera una vez por día y su "session-start equity" es el valor de `executor_state.json` (F-09a). Las cifras diarias de `INDEX.md` (10-07: +123.93, +4.26R; 10-08: −62.40, −2.33R) son consistentes con las filas del ledger y con las variaciones de equity de los reviews (633.68→757.61; 757.61→695.21), pero **no** equivalen al resultado del día natural de cierre.

### F-24 — Código muerto y detalles (Bajo; retenido)
`extreme_stop_spacing_ok` (def. L86) sin llamadas en la búsqueda; `--force` en `cmd_place` aceptado y no usado (única lectura de `a.force`: `L766`, en `close-all`); `MIN_RR` 2.0 en `log_trade` vs 1.9 en el executor; columna `be_trigger_price` con signo opuesto al del executor (no usada en lógica).

### F-25 — Reversión del filtro de momentum apoyada en C040 (Alto; nuevo)
- **Documentación:** `AGENTS.md` y `IMPROVEMENTS.md` justifican dejar `mom_alignment=AGAINST` como no-veto porque C040 "resolvió TP_ONLY ~+3.1R".
- **LOC:** C040: SELL LIMIT 4163.0, `mae` −0.36, `mfe` 22.8, TP_ONLY, ventana 30 barras M5 (2.5 h). El máximo de la ventana quedó 0.36 por debajo de la entrada: **no hubo fill dentro de la ventana** (el nudge de spread de ~0.24 no cierra esa distancia). T036 se canceló de inmediato. Un fill posterior fuera de la ventana no está evaluado.
- **Conclusión:** la evidencia citada no demuestra que el filtro habría bloqueado un ganador. No se concluye lo contrario (que el filtro funcione). Además, las filas ejecutadas con `mom_alignment` registrado son todas ALIGNED; no hay muestra ejecutada de AGAINST.
- **Remediación (investigación, no política inmediata):** observación prospectiva en sombra o simulación fuera de línea con modelo de fill correcto; nunca ejecutar operaciones live solo para generar muestras.

### F-26 — Filas contrafactuales a mano (Medio-Alto; nuevo)
`cmd_consider` calcula `rr_tp1` con valor absoluto (`L134`) y completa ATR, cierre y spread (`L119-L145`). C022 y C023 tienen `rr_tp1` negativo (−2.872, −2.273), `signal_atr_m5` vacío, y C023 tiene `logged_at_local` posterior a `logged_at_server`; C022–C027 tienen ATR vacío. C023 tiene `would_be_r_usd` = −2.273 con resultado TP_ONLY (signo incoherente con `L216-L217`). C002 es BUY con SL arriba y TP abajo de la entrada (geometría invertida) y no hay validación de geometría en `counterfactual.py` (el executor sí valida lado de SL). C001 declara filas "BACKDATED". Efecto aritmético: el grupo NO_STRUCTURAL_TARGET (C002, C005, C023, C027) tiene media almacenada (−1.000, −1.000, −2.273, +0.480) = −0.948, igual que el −0.95 del brief; con C023 en +2.273 sería +0.188; excluyendo además C002 daría +0.584. Esto muestra fragilidad, **no** que el filtro sea bueno o malo.

### F-27 — Cifras de `OPERATIONS.md` vs ledger (Medio; nuevo)
`OPERATIONS.md` §11 indica 22 cerradas, +$124.9 y +3.92R. Mi recuento manual de filas `CLOSED` con PnL hasta T041 no reproduce 22/$124.9; las cifras diarias de `INDEX.md` sí cuadran con sus filas. No se pudo reconciliar sin cálculo reproducible. Tabla por motivo del brief (N=36, 9/15/17…) no coincide con las 40 filas del CSV actual (resueltas 40; 31 con R no vacío; 9 EXPIRED).

### F-28 — Ventanas de historial (Bajo-Medio; nuevo)
`log_trade` resuelve fill y PnL con 14 días (`L344`), `reconcile_deals` usa 30 por defecto; fuera de ventana se cae a estimación por precio (que ya causó un error de PnL con parciales en T041 según el propio docstring `L330-L333`) sin advertencia prominente.

---

## 8. Semántica financiera y de ejecución corregida

### 8.1 Reglas de activación para el modelo contrafactual (supuestos explícitos)
Supuesto de partida: las barras M5 de MT5 son series de Bid salvo confirmación (`SYMBOL_CHART_MODE`). Spread = valor conocido o conservador declarado.

| Tipo | Activa cuando | Condición sobre barras Bid | Observaciones |
|---|---|---|---|
| SELL LIMIT | Bid ≥ entry | `max(high) ≥ entry` | MAE negativo ⇒ no activación en la ventana |
| BUY LIMIT | Ask ≤ entry | `min(low) ≤ entry − spread` | `min(low) ≤ entry` es necesaria pero insuficiente |
| SELL STOP | Bid ≤ entry | `min(low) ≤ entry` | MAE/MFE no son la prueba de activación |
| BUY STOP | Ask ≥ entry | `max(high) ≥ entry − spread` | idem |
| MARKET | inmediato | — | fill = ask/bid del momento ± slippage |

Todas: la activación debe ser cronológicamente anterior a cualquier evaluación de salida; las excursiones del trade empiezan en la barra de activación; barra con activación y salida ⇒ orden intrabarra no determinable (marcar ambigua); barra con SL y TP tras activación ⇒ ambigua (el código actual asume SL); gaps y slippage de stop requieren parámetro; EXPIRED se divide en "sin activación" y "activada sin resolver".

### 8.2 Dimensionamiento
Fórmula documentada: volumen = presupuesto de riesgo / (distancia SL × valor monetario por unidad de precio por lot), redondeo hacia abajo al paso; valor monetario = `trade_tick_value / trade_tick_size` del broker. Volumen es inversamente proporcional al valor monetario. Ejemplo USDJPY: ver F-03 (≈0.27 lot con SL 0.20; ≈0.62 con SL 0.09), siempre dependiente del valor vigente del broker y del equity.

### 8.3 Margen
Requerido (propuesta) vs. existente vs. libre vs. nivel post-trade: usar el resultado de `order_check` (incluye cuenta) como verificación primaria y `order_calc_margin` como estimación independiente; ninguno equivale a aceptación del broker en `order_send`.

### 8.4 PnL neto realizado propuesto
`PnL_neto(posición) = Σ(profit + commission + swap + fee)` sobre todos los deals con el mismo `position_id`; moneda de cuenta; R = PnL_neto / riesgo planificado con denominador declarado. Excluye PnL no realizado y depósitos/retiros.

### 8.5 Estimación de riesgo vs pérdida máxima
El riesgo a SL es una estimación, no un máximo garantizado: T043 pagó −1.28R por deslizamiento del stop (ledger/`IMPROVEMENTS.md`).

---

## 9. Evidencia de desempeño y cálculos no verificados

**Hechos descriptivos respaldados por artefactos** (cálculo manual de aritmética simple, repetible):
- `INDEX.md`/reviews: 10-07 → 3 cerradas, +$123.93, +4.26R (T038 +72.80/2.60; T040 +12.66/0.38; T041 +38.47/1.28 — suma coherente); 10-08 → 2 cerradas, −$62.40, −2.33R (T042 −31.62/−1.05; T043 −30.78/−1.28); 10-09 → 0 cerradas.
- Variación de equity en esos reviews: 633.68→757.61 (+123.93) y 757.61→695.21 (−62.40): coincide con el PnL de las filas, lo que sugiere que no hubo depósitos/retiros esos días (**no confirmado** por extractos).
- Observación de equity más reciente disponible: **$695.21** en `reviews/2026-10-09.md` (histórica; actual no evaluable).

**Retirado:** "+$101 en 25 cerradas", win rate 40%, R medio, t-stat, intervalo de confianza. Mi suma manual de filas `CLOSED` es una estimación no reproducible, y no coincide con la cifra de `OPERATIONS.md` (F-27). La muestra mezcla operaciones manuales (T004, T009, T016), una prueba de capacidad (T027), tamaños sub-dólar (T013, T015, T017, T025), filas reconstruidas (T019, T020, T040) y cambios de reglas durante el periodo. No procede inferir edge.

**Distinciones obligatorias:** PnL en efectivo ≠ variación de equity (incluye flotante, depósitos y retiros) ≠ R agregado (depende del denominador) ≠ rentabilidad monetaria. R y PnL de T040 incluyen un remanente de 0.05 con `volume` reportado como remanente.

**Especificación de análisis offline (para otra tarea autorizada):** (1) congelar copia inmutable del ledger, audit y contrafactuales con hash; (2) reconstruir por posición los deals del broker (exportación autorizada) con costos; (3) definir población: operaciones autónomas bajo reglas constantes, excluyendo manuales, pruebas y filas reconstruidas, y analizar también con ellas; (4) calcular R con denominador declarado; (5) reportar N, media, desviación, errores por bootstrap por bloques o por día (observaciones correlacionadas, un único instrumento dominante) y sensibilidad a costos/slippage; (6) cuantificar tasa de fill y expiración de contrafactuales con el modelo de la sección 8.1; (7) comparar filtros solo con datos que permitan comparación justa (sin etiquetado discrecional posterior al resultado). 20–30 observaciones no bastan para establecer un edge.

---

## 10. Decisiones de política que requieren aprobación del operador

No son correcciones de errores; son decisiones.
1. **Significado de `MAX_POSITIONS`:** ¿posiciones abiertas (código) o exposición abierta+pendiente (brief)? Y su valor (1 o 3).
2. **Semántica de "misma tesis USD":** por lado y símbolo; valor de `MAX_SAME_THESIS`.
3. **Racha de pérdidas:** si debe haber reseteo; si lo hay, solo mediante acción explícita del operador con registro (no reanudación automática). Qué cuenta como pérdida (¿break-even?).
4. **Piso de equity / drawdown:** mantener intradía, añadir piso absoluto o desde máximo (high-water mark). Cualquier umbral lo fija el operador.
5. **Riesgo por trade, R:R mínimo (1.9 vs 2.0) y límites:** sin cambios propuestos; los datos no justifican relajar ni endurecer.
6. **Expiración de pendientes:** duración y tipo, ligados al horizonte aprobado y a lo que admita cada símbolo.
7. **Momentum AGAINST:** mantener advisory hasta tener evidencia válida (F-25); investigación solo en sombra/simulación/demo aislada.
8. **Alcance de `close-all`:** solo posiciones/órdenes de Frival (por `magic`/comentario) o toda la cuenta.
9. **Autonomía de edición:** si el agente puede modificar `order_executor.py` y constantes de riesgo sin revisión humana.
10. **Documentos vigentes:** declarar cuál manda (brief vs `OPERATIONS.md`) y retirar o marcar lo histórico (`SETUP_NEW_MACHINE.md`, `DAILY_ROUTINE.md`).

---

## 11. Hoja de ruta de remediación segura (propuesta; nada de esto está autorizado)

Sin plazos arbitrarios. Cada fase indica dependencias y esfuerzo relativo (S/M/L) a confirmar por quien implemente. La validación precede al despliegue; la cuenta live nunca es el entorno de validación por defecto.

| Fase | Objetivo | Hallazgos | Depende de | Esfuerzo | Validación previa a avanzar |
|---|---|---|---|---|---|
| 0 | Confirmar hallazgos y resolver ambigüedades de política críticas (sección 10: 1, 2, 3, 8, 10) | F-01, F-02, F-08, F-09, F-21 | Decisión del operador | S | Registro firmado de decisiones |
| 1 | Preservar datos y fijar línea base reproducible: copias inmutables con hash de ledger, audit, contrafactuales, estado, reviews, contexto; inventario de tickets/deals autorizados desde el broker | F-05, F-13, F-27 | Fase 0 | M | Hashes y manifiesto verificados; procedencia registrada |
| 2 | Diseñar fixtures, simulador de broker y escenarios de regresión (sección 12), incluidos casos históricos (T010 envíos múltiples, T043 slippage, T040/T041 parciales, T044 pendiente viva) | F-22 y todos | Fase 1 | L | Escenarios revisados por el operador |
| 3 | Proponer correcciones: estado seguro de `close-all` (F-01); idempotencia por reserva y reconciliación de resultado desconocido (F-04); exposición pendiente según política (F-02); stale por tipo de objeto (F-06); persistencia atómica + exclusión mutua + recuperación (F-05); estado de sesión/diario/racha (F-09); margen basado en `order_check`/`order_calc_margin` (F-03); fallos explícitos en lugar de fallbacks (F-16); relojes (F-17) | F-01–F-06, F-09, F-15–F-17 | Fase 2 | L | Revisión de diseño |
| 4 | Validar correcciones **offline** con mocks y fixtures | Todas las de fase 3 | Fase 3 | M–L | Todos los escenarios pasan; evidencia retenida |
| 5 | Validar integración en **demo aislada y explícitamente autorizada** (cuenta demo distinta de la live, guarda de tipo de cuenta) | F-01, F-03, F-04, F-14, F-19 | Fase 4 + autorización | M | Comparación con estimaciones del broker; evidencia retenida |
| 6 | Reconciliar el histórico con migración trazable: ledger original inmutable; tabla de correcciones con valor original, nuevo, motivo y referencia a deal/orden/posición del broker; sin editar filas a partir de logs de envío | F-13, F-14, F-26, F-27 | Fase 1, 5 | M | Auditoría de la migración; reversible |
| 7 | Reevaluar la evidencia estadística con el modelo de fill y costos correctos (sección 9) | F-10, F-25, F-26 | Fase 6 | M | Informe offline reproducible |
| 8 | Considerar cambios de estrategia/política solo tras medición confiable | F-25 y política | Fase 7 | — | Decisión del operador |

**Prerrequisitos transversales:** definición oficial de identificadores (log_id, comentario, `position_id`, ticket); decisión sobre dónde viven los helpers hoy en `%TEMP%\kilo` (versionarlos o retirarlos); confirmación del calendario/zona horaria del servidor.

**Riesgos y reversión:** cada corrección debe poder desactivarse sin perder datos; migraciones solo-anexar; ninguna fase habilita operar en cuentas live.

---

## 12. Pruebas propuestas y criterios de aceptación

Entorno: **M** = simulador/mock offline; **F** = fixture de archivos; **D** = demo aislada autorizada (nunca live). Evidencia a retener en todas: entradas, salidas, registro de auditoría resultante y hash de artefactos antes/después.

| # | Hallazgo | Entorno | Precondiciones | Escenario | Resultado esperado | Condición de fallo |
|---|---|---|---|---|---|---|
| T-01 | F-01 | M | 1 posición propia, 2 pendientes propias, 1 pendiente ajena | Desmontaje | Propias retiradas y cerradas; ajena intacta (si política = solo Frival); estado final "PLANO" tras re-consulta | Resultado "plano" sin re-consulta; ajena afectada sin opción explícita |
| T-02 | F-01 | M | Pendiente que se llena durante la cancelación | Desmontaje | Nueva posición detectada en re-consulta y cerrada; final PLANO | Posición residual no detectada |
| T-03 | F-01 | M | Cierre rechazado / `DONE_PARTIAL` / broker inaccesible | Desmontaje repetido | Reintentos acotados; resultado "NO PLANO/DESCONOCIDO" con lista residual; segunda invocación idempotente | Reporta plano; proceso aborta sin dejar estado |
| T-04 | F-02 | M+F | Política decidida (p. ej. N=3 abiertas+pendientes); 1 posición + 2 pendientes | 4.ª solicitud | Rechazada; con 1+1 la solicitud se acepta | Aceptación sobre el tope o rechazo bajo el tope |
| T-05 | F-03 | M+D | Fixtures por símbolo (USDJPY, EURUSD, XAUUSD) y estimaciones del broker en demo | Cálculo de margen requerido y nivel post-trade | Coincide con fixture/broker dentro de la tolerancia aprobada; la decisión usa el resultado post-solicitud | Diferencia fuera de tolerancia; uso de multiplicación por precio en pares con USD base |
| T-06 | F-04 | M | Orden aceptada con respuesta perdida (timeout) | Reintento del mismo `log_id` | Se bloquea hasta reconciliar por comentario y `position_id`; sin segundo envío | Segundo envío |
| T-07 | F-04 | M | Orden llenada y cerrada antes del reintento | Reintento | Bloqueado por historial/estado terminal | Reenvío por ver "nada vivo" |
| T-08 | F-04 | M (concurrencia) | Dos procesos simultáneos mismo `log_id` | Reserva exclusiva | Solo uno envía | Dos envíos |
| T-09 | F-05 | F | Ledger de prueba | Crash simulado durante escritura | Original íntegro; temporal huérfano ignorado/archivado; recuperación determinista | Original truncado o inválido |
| T-10 | F-05 | F (concurrencia) | Dos escritores | Actualizaciones intercaladas | Ninguna actualización perdida | Pérdida de actualización |
| T-11 | F-06 | M | Pendiente viva y posición de otro símbolo | `manage` con partial en la misma pasada | Fila de pendiente no cambia | Fila marcada `CLOSED` |
| T-12 | F-09 | F | Operaciones cruzando medianoche UTC y de servidor | Cálculo diario | Atribución según política (cierre vs señal) y ancla definida | Reset a mitad del día de servidor sin política |
| T-13 | F-10 | F | Series de barras sintéticas con SELL LIMIT sin toque, BUY LIMIT con toque < spread, STOP, barra con entrada+salida, barra con SL+TP, gap | Resolución | Estados: sin fill, fill, ambiguo; R solo para fills resueltos; denominadores reportados | Resultado TP sin activación; BUY LIMIT activado con `low` entre entry−spread y entry |
| T-14 | F-14 | F/M | Deals sintéticos con profit, commission, swap, fee, parciales, ventana excedida | PnL neto | Coincide con la definición 8.4; advertencia si fuera de ventana | Suma solo de profit |
| T-15 | F-16 | M | Fallos de import/initialize/símbolo | Dimensionamiento | Error explícito, sin volumen | Volumen calculado con valor por defecto |
| T-16 | F-18 | M | Trigger histórico cumplido, precio actual retrocedido; rechazo por distancia de stops; volumen mínimo | `manage` | Sin acción engañosa; estado refleja resultado confirmado | Evento de éxito sin confirmación |
| T-17 | F-12 | M | Kill switch armado de antemano | Prueba de kill switch | Estado original restaurado; no toca ledger real | Kill switch desarmado al finalizar |

**Criterios de aceptación pendientes de decisión:** tolerancias numéricas, N máximo de posiciones/pendientes, semántica de reset de racha, duración de expiración: **dependen de la sección 10** y no se fijan aquí.

---

## 13. Preguntas abiertas y evidencia faltante

1. Estado actual de la cuenta (posiciones, pendientes, equity): no evaluable.
2. Deals reales de T010 y T014 (tickets, `position_id`, costos): no disponibles localmente.
3. ¿La cuenta cobra comisión? Leverage efectivo por símbolo.
4. Tipo de barra del feed (Bid/Last) y si el timestamp de tick está en reloj de servidor.
5. Calendario/DST del servidor tras el próximo cambio de horario.
6. Si los módulos de `execution_bot/` y `gold_rules/` pueden activarse contra la cuenta live (solo se vio configuración demo).
7. Estado de git (cambios sin confirmar) — no se pudo consultar; solo se revisó el reflog de commits.
8. Contenido de `frival/context/*` y de tests de otros componentes: no leído.
9. Re-validación de números de línea de `order_executor.py` fuera de L765–L806 y de `log_trade.py` fuera de los rangos re-leídos.
10. Reconciliación de las cifras de `OPERATIONS.md` con el ledger actual.

---

## 14. Índice de evidencia

| Ref. | Contenido |
|---|---|
| `frival/order_executor.py:L765-L806` | `cmd_close_all` (re-leído); `L766` condición `--force`/kill switch; `L771` `positions_get`; `L787-L788` `magic`/comentario; `L793-L800` manejo de resultado |
| `frival/order_executor.py` (L57, L121, L159-L200, L265-L281, L326-L329, L401-L522, L552-L581) | Lectura de la primera pasada; no re-abiertas en esta |
| `frival/log_trade.py:L39-L40, L54-L55, L146-L169, L265-L284, L325-L358` | Offsets, constantes del fallback, sizing, PnL realizado (re-leídos) |
| `frival/counterfactual.py:L105-L155, L158-L226, L229-L249` | `consider`, `resolve`, `stats` (re-leídos) |
| `frival/reconcile_deals.py:L80-L85, L216-L219` | `_save` y PnL (primera pasada) |
| `frival/test_kill_switch.py` | Harness (primera pasada) |
| `frival/execution_audit.jsonl` L1–L48; L45, L50–L51, L170–L171, L176–L177 | T010 (L3, L5, L10), `CLOSE_FAILED` (L7), kill switch (L11–L13), T014 (L25–L28), margen USDJPY (L34–L39), parciales/BE (búsqueda) |
| `frival/trade_log.csv` líneas 11, 15, 41, 42 | T010, T014, T040, T041 |
| `frival/counterfactuals.csv` | C001–C040 (41 líneas) |
| `frival/executor_state.json` | `session_start_equity` 0.0, `consecutive_losses` 2 |
| `frival/reviews/INDEX.md`; `2026-10-07/08/09.md` | Cifras diarias y equity |
| `.git/logs/HEAD` | Commits 2026-10-06→2026-10-09, único autor |
| `kilo.json`, `.gitignore` | Permisos y exclusiones |
| `C:\Users\sosap\AppData\Local\Temp\kilo\frival_read.py`, `frival_bars.py`, `frival_backfill.py` | Helpers fuera del repo |
| MQL5 `history_deals_get` | https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py (campos commission/swap/profit/fee separados; filtro por `position`) |
| MQL5 `order_calc_margin` | https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcmargin_py (margen sin considerar pendientes ni posiciones actuales) |
| MQL5 `order_check` | https://www.mql5.com/en/docs/python_metatrader5/mt5ordercheck_py (estructura de resultado; tipos de expiración) |

---

## Confirmaciones finales

- Este informe es independiente y no sobrescribe `auditorias/2026-10-10_frival_audit.md`.
- No se ejecutaron scripts, tests ni comandos; no se accedió a MT5; no se realizó ninguna acción de trading ni se modificó el kill switch.
- No se pudo verificar con git que los archivos existentes estén sin cambios; la única escritura de esta tarea fue este archivo (creado en dos pasos: escritura inicial y adiciones sobre el mismo archivo).
- Ninguna propuesta autoriza cambios en el comportamiento live.
