# Plan de remediación Frival — documento incremental

**Estado del documento:** SPECIFICATION COMPLETE — IMPLEMENTATION NOT AUTHORIZED (ver Sección 14 para la cualificación). DESPLIEGUE NO AUTORIZADO. Solo propuesta; ninguna sección autoriza cambios. Escala de estados usada en todo el documento: Especificación completa · Ticket listo para autorización del operador · Ticket bloqueado por política · Ticket que necesita evidencia · Implementación autorizada · Implementado y validado · Despliegue autorizado. Hoy ningún ticket está en "Implementación autorizada" o posterior. No reescribe ni repite los informes `2026-10-10_frival_audit.md` ni `2026-10-11_frival_audit_v2.md`.
**Fecha:** 2026-10-11. **Modelo:** `openrouter/anthropic/claude-sonnet-5.5`.

| Etapa | Contenido | Estado |
|---|---|---|
| 1 | Revalidación de referencias y tabla de evidencia | COMPLETA (esta sección) |
| 2 | Registro de decisiones de política | COMPLETA (todas las decisiones siguen PENDING OPERATOR APPROVAL) |
| 3 | Entrega A: tickets P0 y P1 | COMPLETA (secciones 3 a 5) |
| 4 | Entrega B: tickets P2/P3 (secciones 6 a 8); Entrega C: P4, traspaso, consistencia (secciones 9 a 14) | COMPLETAS |
| 5 | Ensamblaje y verificación final | COMPLETA (Sección 14); sin implementación autorizada |

---

## Sección 1. Revalidación de referencias y tabla de evidencia

**Método:** re-lectura directa de las líneas citadas con herramientas de lectura/búsqueda (sin ejecución). Estados: `CONFIRMADO` (re-leído en esta etapa), `CORREGIDO` (la referencia o lectura previa cambia), `PARCIAL` (solo definición o parte re-leída), `NO RE-ABIERTO` (proviene de lectura anterior; requiere revalidación antes de usarse como referencia formal).

### 1.1 Tabla de evidencia priorizada (hallazgos P0/P1 candidatos)

| Hallazgo | Afirmación revalidada | Referencia | Estado | Nota |
|---|---|---|---|---|
| F-01 | `close-all` itera solo posiciones | `frival/order_executor.py:L771` | CONFIRMADO | `orders_get` aparece solo en `cmd_cancel` (L721, L728, L747) y `cmd_status` (L818, L824), no en `cmd_close_all` (L765-L806) |
| F-01 | Cierre sin filtro de propiedad; `magic` y comentario fijos en la solicitud, no en el filtro | `order_executor.py:L771-L788` | CONFIRMADO | Se cierra toda posición devuelta por `positions_get()` |
| F-01 | `res is None` → continúa; `CLOSE_ALL` se audita aunque `done` sea falso | `order_executor.py:L793-L800` | CONFIRMADO | Campo `done` distingue; no hay re-consulta final |
| F-01 | Sale del proceso si MT5 no inicializa | `order_executor.py:L206-L215` (`sys.exit(1)` en L211, L214) | CONFIRMADO | Cuerpo de `_mt5` no leído completo; líneas de `sys.exit` sí |
| F-01 | Docstring dice "breach = flat + halt" (pérdida diaria) | `order_executor.py:L12` | CONFIRMADO (doc) | Implementación de aplanado automático por breach: **no observada** en los tramos leídos (L284-L357, L401-L517) |
| F-02 | `MAX_POSITIONS = 3`, comentario "net open positions" | `order_executor.py:L57` | CONFIRMADO | Brief dice 1 neta con pendientes como exposición (doc vs doc) |
| F-02 | Riesgo agregado y conteo usan `positions_get()` | `order_executor.py:L324, L346-L352` | CONFIRMADO | Sin `orders_get` en `guardrail_report` (L284-L398) |
| F-08 | Agrupación por símbolo, ciega a lado; candidato sumado | `order_executor.py:L67-L68, L344-L356, L371-L372` | CONFIRMADO | `same_thesis < MAX_SAME_THESIS` con candidato incluido → efectivo 1 (inferencia; validar con fixture) |
| F-03 | Nocional = vol × contract_size × entry | `order_executor.py:L326-L329` | CONFIRMADO | Para USDJPY el precio es JPY |
| F-03 | Comentario del propio código usa "$157,754 notional" como justificación para bajar `MIN_MARGIN_LEVEL` 500→100 | `order_executor.py:L108-L116` | CONFIRMADO | La decisión de política de 2026-10-02 se apoyó en la cifra de la unidad errónea |
| F-03 | `order_check` se invoca pero su resultado no gobierna la decisión de colocación | `order_executor.py:L497-L498` | CONFIRMADO | Se guarda en el audit (L499) |
| F-04 | `cmd_place` no consulta órdenes/posiciones existentes ni estado de la fila antes de enviar | `order_executor.py:L401-L498` | PARCIAL | Se re-leyeron L401-L414 y L496-L517; tramo L415-L495 (nudge, solicitud) **no re-leído** en esta etapa |
| F-04 | Estado de fila se actualiza tras el envío (no reserva previa) | `order_executor.py:L511-L515` | CONFIRMADO | Fallo entre L498 y L515 deja orden en broker y fila sin actualizar |
| F-04 | Si el envío falla la fila queda `PENDING_FILL` | `order_executor.py:L504` | CONFIRMADO | Docstring L16-L18 dice `ORDER_FAILED` y "log antes de enviar": **contradicho** por L504 y por el flujo (la fila la crea otro comando) |
| F-04 | Registros locales de múltiples envíos aceptados | `frival/execution_audit.jsonl` T010 (L3, L5, L10), T014 (L25, L27) | NO RE-ABIERTO | Leídos en L1-L48 en la auditoría; coexistencia de posiciones **no establecida** |
| F-05 | `save_log` escribe en modo "w" directo | `order_executor.py:L276` | CONFIRMADO | Union de columnas (L271-L275); sin temporal, sin lock |
| F-05 | `save_state` escribe directo | `order_executor.py:L155-L156` | CONFIRMADO | |
| F-05 | `log_trade._save` en modo "w" | `frival/log_trade.py:L83-L84` | CONFIRMADO | |
| F-05 | `counterfactual._save`; `reconcile_deals._save` | `counterfactual.py:L88`; `reconcile_deals.py:L80-L85` | PARCIAL | Definiciones confirmadas por búsqueda/lectura previa; cuerpos no re-abiertos en esta etapa |
| F-05 | Precedente de escritura vía temporal + reemplazo en el repo (otro componente) | `frival/gold_rules/run_gold_rules.py:L68-L83` | CONFIRMADO | Útil como patrón de referencia interno, no como validación |
| F-06 | Filas `ORDER_PLACED`/`OPEN` sin posición del símbolo se marcan `CLOSED` en memoria | `order_executor.py:L549-L563` | CONFIRMADO | Una pendiente no figura en `positions_get()` |
| F-06 | Retiro también por desajuste de entrada con posición del mismo símbolo | `order_executor.py:L564-L581` | CONFIRMADO | Tolerancia = máx(0.005, 0.25×ATR) |
| F-06 | Persistencia solo en el camino del parcial | `order_executor.py:L687` (`save_log(rows)`) | CONFIRMADO | Otros `save_log`: L515, L759 (cancel) |
| F-09 | `load_state` usa fecha UTC; ancla = 0.0 hasta el primer envío exitoso | `order_executor.py:L140-L152, L507-L509` | CONFIRMADO | |
| F-09 | `daily_realised` por `logged_at_server` == fecha de servidor de hoy | `order_executor.py:L195-L198` | CONFIRMADO | Fecha de señal, no de cierre |
| F-09 | Orden de racha por `exit_time_local` con fallback a `logged_at_server` | `order_executor.py:L182-L185` | CONFIRMADO | Mezcla relojes (ver F-17) |
| F-09 | Filas con "CAPABILITY TEST" se excluyen del cómputo | `order_executor.py:L176-L177` | CORREGIDO | No se había señalado antes; excluye T010 y T027 |
| F-09 | `pnl_usd` vacío cuenta como 0.0 (rompe racha), no se omite | `order_executor.py:L178-L181` | CORREGIDO | Solo `ValueError` se omite; lectura previa decía lo contrario |
| F-09 | Comentario promete reset "or a new session day"; el código recomputa del ledger | `order_executor.py:L121-L127, L159-L200` | CONFIRMADO | |
| F-09 | Piso de drawdown relativo a `sess_eq` (ancla del día) | `order_executor.py:L332-L338` | CONFIRMADO | |
| F-10 | Ventana, detección TP/SL, MFE/MAE, `would_be_r_usd` | `counterfactual.py:L173-L219` | CONFIRMADO | Re-leído en turno previo y vigente |
| F-10 | `cmd_stats`: media sobre filas con R; tasa sobre todas | `counterfactual.py:L236-L249` | CONFIRMADO | |
| F-12 | Elimina kill switch preexistente | `test_kill_switch.py:L67-L69` | CONFIRMADO | |
| F-12 | Reescribe el ledger real con fila señuelo y al final la elimina | `test_kill_switch.py:L77-L93, L144-L150` | CONFIRMADO | Escritura "w" directa |
| F-12 | `close-all` real con interruptor armado; luego `place` señuelo tras desarmar | `test_kill_switch.py:L113, L128, L132` | CONFIRMADO | |
| F-12 | Restaura el kill switch al final | `test_kill_switch.py:L152-L154` | CORREGIDO | Informes previos no lo mencionaban; restauración ocurre solo si el flujo llega al final (**no se observó** try/finally en L55-L154) |
| F-14 | `d.profit` único componente sumado; ventana 14 días | `log_trade.py:L344, L356` | CONFIRMADO | Comisión/swap/fee no sumados |
| F-16 | Fallback = 100×100 | `log_trade.py:L54-L55, L160-L169` | CONFIRMADO | |
| F-16 | `_size_volume` sube a `volume_min` si el cálculo es menor | `log_trade.py:L283-L284` | CONFIRMADO | |
| F-17 | `SERVER_OFFSET_H = 3`, `LOCAL_OFFSET_H = -8` | `log_trade.py:L39-L40`; `order_executor.py:L134` | CONFIRMADO | |
| F-19 | Pendientes `ORDER_TIME_GTC` | `order_executor.py:L493` | CONFIRMADO | Mismo valor en cierres (L661, L789) |
| F-24 | `extreme_stop_spacing_ok` definida; sin llamadas | `order_executor.py:L83-L86` | CONFIRMADO | Búsqueda en `frival/` |
| F-24 | `--force` de `place` aceptado, no leído en `cmd_place`; mensaje de bloqueo lo menciona | `order_executor.py:L419, L851`; única lectura de `a.force`: L766 | CONFIRMADO | Docstring L14 dice "unless --force + reason" |

### 1.2 Correcciones a lecturas previas surgidas en esta etapa

1. **F-09:** filas `CLOSED` con `pnl_usd` vacío cuentan como 0.0 y cortan la racha; antes se describía como "se omiten".
2. **F-09:** `refresh_state_from_log` excluye filas con "CAPABILITY TEST" en notas; el efecto sobre el estado actual (racha 2) se mantiene.
3. **F-12:** el test sí restaura un kill switch preexistente al final del flujo; el riesgo residual es la interrupción a mitad (no verificado) y el uso de la cuenta conectada.
4. **F-03:** `MIN_MARGIN_LEVEL` se bajó de 500 a 100 apoyándose en el nocional de la unidad errónea (comentario en L108-L116): la política vigente depende de un cálculo defectuoso.
5. **F-04/F-20:** la docstring (L16-L18) promete "log antes de enviar" y estado `ORDER_FAILED`; el código deja `PENDING_FILL` (L504) y no escribe la fila.

### 1.3 Referencias que siguen sin re-abrir (no usar como referencia formal sin revalidar)

- `order_executor.py:L415-L495` (nudge, validaciones de lado, construcción de solicitud) y `L583-L697` (BE/parcial).
- `reconcile_deals.py` cuerpos de `_save`, `match`, `r_multiple`; `log_trade.py` cuerpos de `cmd_signal` (L371+) y `cmd_exit` (L476+); `eod_review.py:L93`.
- Líneas del audit log y filas del ledger citadas en informes previos, salvo las ya re-leídas (ledger T010, T014, T040, T041; audit L170-L171, L176-L177).
- `frival/context/*`, tests de componentes legados.

### 1.4 Dependencias para etapas siguientes

- Ítems P0 candidatos (a confirmar en etapa 3): F-01, F-04, F-05, F-06 (más F-03 como P0/P1 según decisión de política sobre margen).
- Ítems con decisión de política previa (etapa 2): F-02/F-08 (significado de exposición y tesis), F-09 (semántica de sesión, racha, piso), F-19 (expiración), F-01 (alcance de `close-all`), F-25 (momentum).

---

## Sección 2. Registro de decisiones de política

**Paquetes (identidad ≠ severidad):** P0 aislamiento seguro de pruebas y límites de permisos · P1 persistencia, concurrencia y corrección del estado de ciclo de vida · P2 idempotencia de órdenes, exposición pendiente y desmontaje de emergencia verificado · P3 margen, riesgo a precio ejecutable, relojes, breakers y PnL neto · P4 reconciliación histórica y medición contrafactual.
Asignación provisional (los tickets se definen en la etapa 3): P0 ← F-12, F-11, F-22 (parte de aislamiento) · P1 ← F-05, F-06, F-20 · P2 ← F-01, F-02, F-04, F-08, F-19 · P3 ← F-03, F-09, F-14, F-15, F-16, F-17, F-18 · P4 ← F-10, F-13, F-25, F-26, F-27, F-28. F-01 es Crítico pero pertenece a P2, no a P0.

**Regla:** ningún estado de abajo está aprobado. Las instrucciones antiguas de mejora autónoma (`IMPROVEMENTS.md`) no se interpretan como aprobación. Las "propuestas" no fijan umbrales ni política de trading.

### 2.1 Decisiones

| ID | Pregunta | Fuentes relevantes / en conflicto | Alternativas | Propuesta (no aprobada) y motivo | Afecta | Bloquea | Estado |
|---|---|---|---|---|---|---|---|
| D-01 | ¿Rige el mandato Frival actual o una adaptación a Trader1000? | Brief, `OPERATIONS.md`, `AGENTS.md` definen Frival. Búsqueda de texto: **ningún documento ni referencia a Trader1000 en el repo** | A) Frival vigente; B) adaptar a Trader1000 (requiere aportar su documento) | A, porque no hay fuente de B contra la que especificar. Si se elige B, se repite este registro | Todos | Despliegue de parámetros (P2/P3); no P0/P1 | PENDING OPERATOR APPROVAL |
| D-02 | ¿Qué instrumentos están permitidos? | Docs: XAUUSD, EURUSD, USDJPY. Código: grupos USD incluyen además USDCHF, AUDUSD, NZDUSD (`order_executor.py:L67-L68`) | A) lista cerrada de 3; B) lista mayor aprobada | A y rechazo explícito de otros símbolos: acota fixtures y la tabla de tesis | P2 (F-08), P3 (F-03, F-16) | Implementación de fixtures P2/P3; no P0/P1 | PENDING OPERATOR APPROVAL |
| D-03 | ¿Cómo cuentan las pendientes en límites y qué es "reserva de riesgo"? | Brief: 1 neta y pendientes como exposición; `OPERATIONS.md`/código: `MAX_POSITIONS = 3`, solo `positions_get()` (`L57, L324`) | A) solo abiertas (actual); B) abiertas+pendientes en el conteo; C) B más reserva de riesgo de pendientes al SL | B o C, para alinear con el brief; valores N y % los fija el operador | P2 (F-02, F-04) | Implementación de F-02; no P0/P1 | PENDING OPERATOR APPROVAL |
| D-04 | Alcance de emergencia: ¿solo actividad Frival o toda la cuenta? | `close-all` cierra toda posición de la cuenta (`L771`); "flat" en `OPERATIONS.md` | A) solo propia; B) toda la cuenta; C) dos modos, propia por defecto y cuenta completa con invocación explícita separada | C: evita cerrar actividad ajena por defecto y conserva la salida total | P2 (F-01) | Diseño del ticket F-01 | PENDING OPERATOR APPROVAL |
| D-05 | ¿Cómo se determina la propiedad de órdenes/posiciones, incluida la ambigua o mixta? | Cierres usan `magic` 20261001 y comentario `FRIVAL_CLOSE` (`L787-L788`); entradas se emparejan por comentario `FRIVAL_<id>`; el broker puede sobrescribir comentarios de salida (docstring de `reconcile_deals.py`); `magic` de la solicitud de entrada **no re-leído** (L415-L495) | A) solo `magic`; B) prefijo de comentario; C) registro en ledger + `position_id` + `magic` | C: clasificar cada orden/posición como FRIVAL_OWNED, OTHER_OWNED u OWNERSHIP_UNKNOWN (o MIXED); lo desconocido o mixto se informa y **no** se actúa sobre ello automáticamente en modo solo-Frival (corrige la formulación previa "no propios"; la regla concreta sigue pendiente del operador) | P1, P2, P4 | Implementación de P1 (claves de fila) y P2 | PENDING OPERATOR APPROVAL |
| D-06 | Semántica de "misma tesis USD" y del tope | `OPERATIONS.md` (tope 2); código agrupa por símbolo, ciego a lado, candidato incluido (`L344-L356, L371`) | A) grupos por símbolo (actual); B) tabla símbolo×lado definida por el operador; C) otro | B; el operador define la tabla y si el tope incluye al candidato | P2 (F-08) | Implementación de F-08 | PENDING OPERATOR APPROVAL |
| D-07 | Reloj de sesión, atribución del PnL diario y ancla de equity | UTC para estado (`L142`), fecha de servidor para `daily_realised` por fecha de señal (`L195-L198`), ancla = primer envío (`L507-L509`); offsets −8/−5/+3 en distintos módulos | Reloj: servidor/UTC. Atribución: señal vs cierre del broker. Ancla: primer envío, foto de inicio de día, máximo histórico | Un solo reloj aprobado; atribución por cierre confirmado por el broker; ancla fijada al primer registro del día de servidor; máximo histórico solo si el operador lo quiere | P3 (F-09, F-17) | Tickets F-09/F-17; P1 conservará el esquema sin cambiar la semántica | PENDING OPERATOR APPROVAL |
| D-08 | Definición de racha de pérdidas y procedimiento de reinicio | Comentario: reset por victoria o "nuevo día" (`L121-L127`); código: recomputa del ledger; vacío=0.0 corta la racha (`L178-L181`); excluye "CAPABILITY TEST" (`L176`) | Definir: ¿break-even, parciales, filas manuales/reconstruidas cuentan? Reinicio: automático diario / solo victoria / confirmación explícita registrada | Reinicio solo por acción explícita del operador con motivo registrado; nunca reanudación automática | P3 (F-09) | Ticket de breaker | PENDING OPERATOR APPROVAL |
| D-09 | Expiración de pendientes | Pendientes `ORDER_TIME_GTC` (`L493`); expiración manual por señal citada en brief/notas (duración **no revalidada aquí**) | A) sin expiración de broker (agente cancela); B) horizonte por señal; C) fin de sesión | B con duración fijada por el operador y solo si el broker admite el tipo de expiración (por confirmar, ver `order_check` en MQL5) | P2 (F-19) | Despliegue; implementación tras verificar soporte | PENDING OPERATOR APPROVAL |
| D-10 | ¿Quién puede modificar configuración de riesgo y ejecutor? | `kilo.json` concede `bash`/`edit`; `IMPROVEMENTS.md` documenta autonomía (no se toma como aprobación); git: un solo autor | A) agente libre (actual); B) agente propone, operador aprueba con registro; C) constantes en archivo no editable por el agente | B como mínimo; C si se quiere control técnico | P0 (F-11) | Parte de permisos de P0; no el aislamiento de pruebas | PENDING OPERATOR APPROVAL |

### 2.2 Trabajo de ingeniería que no cambia política

| Ítem | Paquete | Verificación de fuente antes de marcar READY |
|---|---|---|
| E-1 Mocks de broker y fixtures desechables | P0 | Releer `order_executor.py:L1-L140` (rutas y efectos al importar; `STATE = load_state()` en `L203`) y cómo se importa `MetaTrader5` |
| E-2 Impedir que las pruebas usen datos de producción o terminal real | P0 | Releer `test_kill_switch.py:L1-L54, L155-L170` (rutas fijas y resto del flujo, incl. manejo de interrupción) |
| E-3 Reemplazo atómico + exclusión mutua en lectura-modificación-escritura | P1 | Inventario completo de escritores de `trade_log.csv` y `executor_state.json` (`log_trade.py:L68-L88` y cmds de escritura, `reconcile_deals.py:L80-L85`, lectores simples `order_executor.py:L169, L511`) |
| E-4 Preservar originales y procedencia de migración | P1/P4 | Ninguna de código; sí inventario de artefactos y manifiesto de hashes |
| E-5 Resultado de broker desconocido tratado como `UNKNOWN`, no `FAILED` | P2 | Releer `order_executor.py:L415-L495, L583-L697, L700-L760` (todos los puntos que interpretan `result is None`; hoy `L501-L505` lo trata como fallo) |

### 2.3 Aclaración "registro antes de colocar"

El manual exige `log_trade.py signal` antes de `order_executor.py place`. Que `cmd_place` no cree la fila **no** es una contradicción. Lo relevante es cinco mecanismos distintos:

| Mecanismo | Estado observado |
|---|---|
| 1. Señal existente, válida y persistida | La existencia se exige: aborta si no hay fila (`L406-L409`, confirmado). La validez (estado de la fila, no ya colocada, campos completos): **no observada** en lo releído; pendiente inspección de `L284-L320` y `L415-L495` |
| 2. Reserva exclusiva de envío | **No observada** en `L401-L414, L496-L517`; pendiente inspección de `L415-L495` |
| 3. Registro del intento | `PLACE_ATTEMPT` se añade al audit (`L414`), no al ledger, y no es exclusivo; si precede al envío en todas las ramas: pendiente |
| 4. Registro del resultado del broker | `PLACE_RESULT` tras `order_send` (`L499`); qué ocurre si falla la escritura del audit: pendiente |
| 5. Actualización final del ciclo de vida | `L511-L515`, después del envío y no atómica con él; un fallo previo deja orden en broker y fila `PENDING_FILL` |

La contradicción acotada es otra: el docstring promete `ORDER_FAILED` (`L16-L18`) y el código deja `PENDING_FILL` (`L504`).

### 2.4 Lista mínima de aprobación para preparar P0 y P1

1. **D-01:** confirmar que el mandato vigente es Frival (acota todo el plan).
2. **D-05:** confirmar la clave de propiedad (id de ledger + `position_id` + `magic`, con ambiguos clasificados OWNERSHIP_UNKNOWN/MIXED, informados y sin actuación automática en modo solo-Frival).
3. **D-10:** elegir B o C para permisos (o aprobar solo el aislamiento de pruebas de P0 y diferir permisos).

Fuera de esta lista: D-02 a D-04 y D-06 a D-09 no bloquean P0/P1. P1 no modificará la semántica de sesión (D-07) ni de racha (D-08).

<!-- FIN-ETAPA-2 -->

---

## Sección 3. Entrega A — línea base, huecos cerrados y convenciones

### 3.1 Línea base de código
- `.git/HEAD` → `refs/heads/main`; `.git/refs/heads/main` = `7f9df8e8428e239a85136b7b2a3568f40301617b` (coincide con la última entrada del reflog: commit "docs(frival): 2026-10-09 daily review (no-trade day)").
- **Limitación:** con las herramientas permitidas no se puede ejecutar `git status`; no se sabe si el árbol de trabajo tiene cambios sin confirmar (el ledger, el audit y `executor_state.json` fueron modificados por el desk después de ese commit con alta probabilidad). El agente implementador debe contrastar el árbol con esta línea base antes de empezar (ver procedimiento de traspaso, Entrega C).
- Las referencias de línea de esta sección se tomaron de lecturas completas de las funciones citadas **en este turno**.

### 3.2 Huecos de fuente cerrados (P0/P1)
| Tema | Hallazgo verificado | Referencia |
|---|---|---|
| Rutas | Todas las rutas se derivan de `Path(__file__)`: `HERE`, `LOG_PATH`, `STATE_PATH`, `AUDIT_PATH`; `DATA = ROOT / "frival" / "data"` fija el nombre de carpeta "frival" | `order_executor.py:L39-L42, L132-L133`; `log_trade.py:L33-L34`; `counterfactual.py:L42-L43`; `reconcile_deals.py:L39-L40`; `market_context.py:L33-L35`; `test_kill_switch.py:L25-L28` |
| Efectos al importar `order_executor` | Lee `config/.env` (solo para `MT5_PATH`) y `executor_state.json`; **no** inicializa MT5 ni escribe al importar. `MetaTrader5` y `pandas` se importan de forma diferida | `order_executor.py:L44-L46, L203, L206-L215, L233-L237`; `mt5_path.py:L35-L71` |
| `status` no es de solo lectura local | `cmd_status` llama a `refresh_state_from_log` que escribe `executor_state.json`; también `place` y `manage` | `order_executor.py:L833, L199, L155-L156, L410, L539` |
| Escritores del ledger `trade_log.csv` | (1) `save_log` ← `place` L515, `manage` L687, `cancel` L759; (2) `log_trade._save` ← `signal` L444, `fill` L462, `be` L472, `exit` L519, `skip` L538; (3) `reconcile_deals._save` ← `apply` L284; (4) `test_kill_switch.py` L89, L146; (5) helpers ad hoc fuera del repo (`%TEMP%\kilo\frival_backfill.py`; no re-leído en este turno) | `order_executor.py:L265-L281`; `log_trade.py:L83-L88`; `reconcile_deals.py:L80-L85` |
| Comportamiento de esquema por escritor | Executor: unión de columnas y `extrasaction="ignore"` (preserva). `log_trade`: columnas fijas `COLUMNS` (descarta desconocidas). `reconcile`: columnas de la primera fila. `counterfactual`: `COLUMNS` fijas (otro archivo). `_load` de `log_trade` colapsa `log_id` duplicados conservando el último | `order_executor.py:L271-L278`; `log_trade.py:L68-L88`; `reconcile_deals.py:L82-L85`; `counterfactual.py:L88-L91` |
| Lectores del ledger | Lecturas simples sin lock | `order_executor.py:L169, L258, L511, L542, L715, L751`; `log_trade.py:L71`; `reconcile_deals.py:L76`; `market_context.py:L118` |
| Ventanas de lectura-modificación-escritura | `manage` lee filas (L542), hace llamadas al broker (L629, L664) y escribe después (L687); `cancel` lee tras la cancelación confirmada y escribe (L751-L759); `place` lee tras el envío y escribe (L511-L515); `log_trade exit`/`signal` llaman a MT5 antes de guardar | `order_executor.py:L542-L687, L715-L759, L511-L515`; `log_trade.py:L476-L519` |
| Estado `None` del broker | `positions_get() or []` y `orders_get() or []` convierten un fallo (`None`) en "vacío"; esto afecta `manage` (lista `live`), `guardrail_report` y `close-all` | `order_executor.py:L324, L550, L721, L771` |
| Guardia de operaciones manuales | `manage` lee `execution_mode == "OPERATOR_MANUAL"`, pero ese campo **no existe** en la cabecera del ledger ni se escribe en ningún `*.py` buscado; la guardia no puede activarse | `order_executor.py:L587`; `trade_log.csv` línea 1 |
| Emparejado fila↔posición | `live` indexa por símbolo; segunda pasada usa `positions_get(symbol=...)` y `pos[0]` | `order_executor.py:L549-L551, L590-L593` |
| Test de kill switch | Sin `try/finally`; usa `MetaTrader5` real en `snapshot()`; ejecuta `close-all` y `place` reales vía subprocess; reescribe el ledger real | `test_kill_switch.py:L35-L51, L60-L154` |
| Orden de comprobaciones en `place` | Kill switch antes de `_mt5()`; fila inexistente aborta; **no** hay reserva exclusiva; `PLACE_ATTEMPT` se audita antes de bloquear/enviar; `order_check` no gobierna; `result is None` se trata como "FAILED" | `order_executor.py:L402-L414, L497-L505` |

Cierre de la aclaración 2.3: (1) existencia de señal persistida: confirmada (L406-L409); validez del estado de la fila: **no verificada** (`guardrail_report` L284-L320 se re-leerá en la Entrega B); (2) reserva exclusiva: ausente en `cmd_place` (re-leído L401-L517); (3) intento: `PLACE_ATTEMPT` L414; (4) resultado: `PLACE_RESULT` L499 sin manejo de excepciones de serialización/escritura; (5) ciclo de vida: L511-L515 tras el envío.

### 3.3 Identificadores (definiciones separadas)
| Identificador | Qué es hoy | Observación |
|---|---|---|
| Señal / `log_id` | Columna `log_id` (p. ej. T040); `setup_id` es otra columna | Clave de fila del ledger (las filas duplicadas se colapsan al cargar con `log_trade`) |
| Intento de envío | **No existe**; el comentario `FRIVAL_<log_id>` es igual en cualquier reintento | Los tickets nuevos de P2 definirán un identificador por intento |
| Ticket de orden del broker | `result.order` en `PLACE_RESULT`; `found.ticket` en `cancel` | No se guarda en el ledger |
| Ticket de deal | Deals devueltos por historial; entrada localizada por comentario | Solo en funciones de resolución |
| Identificador de posición | `position_id` de los deals; `p.ticket` de la posición | Una **orden pendiente aún no tiene `position_id`**; se identifica por ticket de orden y comentario |

### 3.4 Propiedad (nomenclatura de los tickets)
`FRIVAL_OWNED`, `OTHER_OWNED`, `OWNERSHIP_UNKNOWN` o `MIXED`. En modo solo-Frival lo `OWNERSHIP_UNKNOWN`/`MIXED` se informa y no recibe acciones automáticas. La regla de clasificación está **pendiente de D-05** y ningún ticket la fija.

### 3.5 Lote inicial mínimo sin cambios de política
Candidatos: **P0-01, P0-02, P1-01, P1-02, P1-03**. No dependen de D-02 a D-04 ni de D-06 a D-09. P0-03 y P1-04 están bloqueados (D-10, D-05). Todos requieren autorización explícita del operador para su alcance exacto.

<!-- FIN-ENTREGA-A-PARTE-1 -->

---

## Sección 4. Tickets P0 — Aislamiento seguro de pruebas y límites de permisos

Estado de todos los tickets: **Implementación autorizada: NO**. "READY FOR AUTHORIZATION" significa que la especificación está completa y espera la aprobación explícita del operador para ese alcance.

### P0-01 — Entorno de pruebas offline aislado (mocks de broker y datos desechables)
- **Hallazgos:** F-12, F-22. **Prioridad:** máxima del lote; **severidad:** Alta (habilita todo lo demás). **Estado:** READY FOR AUTHORIZATION.
- **Comportamiento actual:** no existen pruebas del desk que importen sus módulos; la única prueba (`test_kill_switch.py`) usa terminal y ledger reales (ver 3.2). Los módulos derivan rutas de `__file__` (`order_executor.py:L39-L42, L132-L133`), lo que permite aislar copiando los archivos a un árbol temporal. `MetaTrader5` se importa solo dentro de `_mt5()` (`L206-L215`), de modo que un módulo falso inyectado antes de ejecutar un comando sustituye al real.
- **Resultado requerido:** una infraestructura de pruebas que ejecute los comandos del desk contra un árbol temporal y un broker simulado, sin tocar ledger, estado, audit, kill switch ni terminal reales, y que **falle antes de cualquier efecto** si no puede demostrar el aislamiento.
- **Dentro del alcance:** (a) árbol desechable con la estructura `<tmp>/frival/` (obligatoria por `DATA = ROOT / "frival" / "data"`, `L41`) con copias de los módulos del desk bajo prueba; (b) ledger, estado, audit y `data/` sembrados con fixtures sintéticos; (c) módulo `MetaTrader5` falso con marca identificable, que registra cada llamada y permite programar respuestas (posiciones, órdenes, ticks, símbolo, cuenta, `order_check`, `order_send`, historial, `None` y excepciones); (d) variable de entorno `MT5_PATH` fijada a un valor centinela y ausencia de `config/.env` en el árbol; (e) precondiciones de aislamiento verificadas antes de cada prueba; (f) inspección documentada de efectos al importar de cada módulo bajo prueba antes de importarlo (para `order_executor`, ya inspeccionado en 3.2; `log_trade`, `counterfactual`, `reconcile_deals`, `market_context` deben inspeccionarse íntegros antes de incluirse).
- **Fuera del alcance:** cambiar código de producción; ejecutar el desk real; validar contra una demo; elegir marco de pruebas nuevo con dependencias nuevas (usar el ya presente en el repo, estilo `unittest` observado en `dashboard/tests/test_portfolio.py:L88-L89`, si el operador lo confirma).
- **Archivos esperados:** nuevo directorio de pruebas del desk (p. ej. `frival/tests_offline/`) y fixtures; ningún archivo existente modificado.
- **Dependencias:** ninguna. **Decisiones:** ninguna.
- **Pasos:** 1) listar los módulos bajo prueba y leer cada uno completo para inventariar importaciones y efectos; 2) definir el contrato del broker simulado a partir de las llamadas realmente usadas (`initialize`, `last_error`, `shutdown`, `account_info`, `symbol_info`, `symbol_info_tick`, `positions_get`, `orders_get`, `order_check`, `order_send`, `copy_rates_from_pos`, `history_deals_get`, constantes de acción/retcode/tipo); 3) construir el verificador de aislamiento; 4) construir fixtures de ledger/estado/audit; 5) escribir las pruebas de regresión de abajo; 6) revisión independiente.
- **Pruebas de regresión (se escriben antes de cualquier corrección):**
  - R0-1 *Aislamiento verificado:* tras importar `order_executor` desde la copia, `LOG_PATH`, `STATE_PATH`, `AUDIT_PATH`, `KILL_SWITCH` resuelven dentro del árbol temporal. Esperado: pasa; si alguno queda fuera, la prueba aborta antes de ejecutar comandos y no escribe nada.
  - R0-2 *Sin terminal real:* ejecutar `status` con el broker falso. Esperado: `initialize` llamado sobre el falso con el valor centinela; el módulo `MetaTrader5` en uso es el falso; cero imports del paquete real.
  - R0-3 *Fallo seguro:* provocar el caso "paquete real presente y falso ausente". Esperado: abortar antes de cualquier efecto (sin archivos creados ni modificados).
  - R0-4 *Efecto de `status` documentado:* `status` modifica solo `executor_state.json` del árbol temporal (L833→L199).
  - R0-5 *Kill switch aislado:* con el archivo del árbol temporal presente, `place` termina sin llamar a `initialize` (L402-L405 antes de L411).
- **Criterios de aceptación:** (1) las 5 pruebas pasan en un entorno sin terminal MT5; (2) un manifiesto de hash de los archivos reales de producción (ledger, estado, audit, `data/`) tomado por el implementador antes y después de la suite es idéntico; (3) ninguna prueba abre rutas fuera del árbol temporal (comprobado con el verificador); (4) la suite falla con mensaje explícito si se ejecuta con aislamiento no establecido; (5) cero modificaciones a archivos existentes del repo.
- **Fallo/estado desconocido:** si no se puede establecer cualquiera de las precondiciones, la suite no inicia (no "continúa con advertencia").
- **Compatibilidad/migración:** ninguna; solo archivos nuevos.
- **Reversión:** eliminar los archivos nuevos (están en control de versiones).
- **Evidencia a entregar:** diff de archivos nuevos, salida real de la suite, lista de pruebas no ejecutadas, manifiesto de hashes antes/después, inventario de efectos al importar por módulo, riesgos residuales.

### P0-02 — Reemplazo y cuarentena del arnés `test_kill_switch.py`
- **Hallazgos:** F-12, F-01 (parcial: la prueba de `close-all` real). **Severidad:** Alta. **Estado:** READY FOR AUTHORIZATION (depende de P0-01; la actualización de `SETUP_NEW_MACHINE.md` queda fuera hasta aprobación documental).
- **Comportamiento actual:** `test_kill_switch.py` borra un kill switch preexistente (L67-L69), reescribe el ledger real con una fila señuelo (L77-L93), ejecuta `close-all` real (L113), desarma y ejecuta `place` real hasta el bloqueo por guardarraíl (L128-L132) y no tiene `try/finally` (L60-L154). Su cabecera afirma que "never places a REAL order" pero cierra posiciones reales. `SETUP_NEW_MACHINE.md` lo presenta como compuerta.
- **Resultado requerido:** (a) el arnés original no puede ejecutarse por accidente; (b) un conjunto offline equivalente verifica la cadena kill switch → rechazo de `place` → `close-all` permitido, sobre el broker simulado y datos desechables.
- **Dentro del alcance:** pruebas offline equivalentes (R0-5 y las siguientes); cuarentena del original. Opciones de cuarentena a decidir por el operador al autorizar: mover el archivo a una ubicación claramente marcada, o conservarlo con un rechazo inmediato por defecto salvo aislamiento verificado; no eliminarlo.
- **Fuera del alcance:** `close-all` con pendientes (P2); cambio de política del kill switch; redactar la nueva compuerta de `SETUP_NEW_MACHINE.md`.
- **Pasos:** 1) leer completo el arnés y mapear cada una de sus 8 comprobaciones; 2) escribir las equivalentes offline y verificar que **fallan o se saltan** contra el original no aislado (según opción de cuarentena); 3) aplicar la cuarentena aprobada; 4) revisión independiente.
- **Pruebas de regresión:** R0-6 con kill switch armado `place` aborta y `order_send` no se llama; R0-7 con kill switch armado `close-all` se ejecuta sin `--force` sobre el broker falso y cierra solo posiciones del fixture; R0-8 tras desarmar, `place` con fixture que viola el guardarraíl de riesgo termina `BLOCKED` sin `order_send`; R0-9 un kill switch preexistente en el árbol temporal sigue presente tras la suite, incluso si una prueba intermedia lanza una excepción; R0-10 el ledger sembrado no cambia durante la prueba del kill switch (hash).
- **Aceptación:** R0-6 a R0-10 pasan; invocar el arnés original con el entorno real queda bloqueado (según cuarentena); el manifiesto de hashes de producción no cambia; ninguna prueba depende de `close-all` real.
- **Fallo/desconocido:** si el kill switch del árbol temporal no se puede restaurar, la suite falla sin dejar el árbol en estado ambiguo.
- **Compatibilidad:** la compuerta documentada de `SETUP_NEW_MACHINE.md` queda sin sustituto aprobado hasta que el operador decida. **Reversión:** restaurar el archivo original desde control de versiones. **Evidencia:** igual que P0-01 más la tabla de equivalencia 8 comprobaciones → pruebas offline.

### P0-03 — Límites de permisos del agente (recomendación, sin cambios de configuración)
- **Hallazgos:** F-11. **Severidad:** Media. **Estado:** BLOCKED POLICY (D-10).
- **Comportamiento actual:** `kilo.json:L3-L11` concede `bash`, `edit` y `external_directory` en modo "allow"; no hay separación técnica entre decisión y límites de riesgo. Un único autor en git no permite atribuir cambios.
- **Resultado requerido (condicional a D-10):** una matriz de permisos aprobada por el operador y un procedimiento de verificación.
- **Recomendaciones (no aprobadas):** constantes de riesgo y ejecutor modificables solo mediante propuesta aprobada con registro; proteger el kill switch, el ledger y el estado frente a edición directa por el perfil autónomo; restringir `bash`; revisar `external_directory`.
- **Fuera del alcance:** editar `kilo.json` o cualquier permiso; cualquier restricción que impida operar sin aprobación del operador.
- **Pasos tras aprobar D-10:** definir matriz acción×recurso; escribir pruebas de sondeo no destructivas en un árbol desechable; aplicar solo la configuración aprobada.
- **Aceptación:** el operador firma la matriz; cada celda "denegado" se demuestra con un sondeo en árbol desechable; ninguna acción permitida deja de funcionar.
- **Reversión:** restaurar la configuración previa guardada con hash. **Evidencia:** matriz firmada, resultados de sondeo.

<!-- FIN-ENTREGA-A-PARTE-2 -->

---

## Sección 5. Tickets P1 — Persistencia, concurrencia y estado de ciclo de vida

Conceptos que se mantienen separados en todos los tickets: preservación de esquema · reemplazo atómico · durabilidad ante caída · protección de concurrencia · recuperación. Ninguno realiza migraciones históricas ni modifica semántica de sesión, racha o estrategia.

### P1-01 — Reemplazo atómico, preservación de esquema y recuperación (ledger y estado)
- **Hallazgos:** F-05, F-13 (solo prevención futura). **Severidad:** Alta. **Estado:** READY FOR AUTHORIZATION (depende de P0-01 para sus pruebas).
- **Comportamiento actual:** cinco escritores abren `trade_log.csv` en modo "w" directamente (`order_executor.py:L276`; `log_trade.py:L84`; `reconcile_deals.py:L81`; `test_kill_switch.py:L89, L146`); `save_state` escribe directo (`L155-L156`). Un fallo a mitad deja el archivo truncado (incidente documentado: truncación de T040). Esquemas: `log_trade._save` descarta columnas desconocidas (`L85-L88`); `_load` colapsa duplicados de `log_id` (`L68-L80`); `reconcile._save` usa las columnas de la primera fila y falla con lista vacía (`L82`); el executor une columnas (`L271-L278`).
- **Resultado requerido:** toda escritura del ledger y del estado hace un reemplazo atómico de un archivo completo y validado; ningún escritor descarta columnas ni registros sin dejar copia recuperable; un arranque tras una caída detecta temporales huérfanos sin perder datos.
- **Dentro del alcance:** una única rutina compartida de escritura/validación; validación previa al reemplazo (cabecera presente y contiene todas las columnas del original; número de registros no inferior al original salvo duplicados colapsados explícitamente, con aviso y copia del archivo previo); vaciado a disco del temporal antes de reemplazar; manejo de fallo de reemplazo con reintentos acotados y fallo ruidoso; procedimiento de recuperación para temporales huérfanos (ignorar y archivar, nunca promover automáticamente); uso de la rutina en `order_executor.save_log`, `save_state`, `log_trade._save` y `reconcile_deals._save`.
- **Fuera del alcance:** cambiar la política de colapsar duplicados (solo hacerla visible y recuperable); migrar datos históricos; añadir dependencias; modificar el contenido de `trade_log.csv`.
- **Archivos esperados:** `order_executor.py`, `log_trade.py`, `reconcile_deals.py`, módulo compartido nuevo, pruebas nuevas.
- **Dependencias:** P0-01. **Decisiones:** ninguna.
- **Pasos:** 1) escribir las pruebas de regresión (fallan hoy); 2) crear la rutina compartida; 3) sustituir cada escritura por la rutina, un escritor por vez, ejecutando las pruebas offline tras cada uno; 4) documentar la limitación de durabilidad en Windows (no hay sincronización de directorio garantizada).
- **Pruebas de regresión y fixtures (ledger sintético con filas PENDING_FILL, ORDER_PLACED, OPEN, CLOSED, una columna desconocida `x_extra`, y un `log_id` duplicado):**
  - R1-1 *Caída durante escritura:* inyectar un fallo tras escribir parte del temporal. Esperado: el ledger original es byte-idéntico; el temporal puede persistir.
  - R1-2 *Caída justo antes del reemplazo:* original intacto; en el siguiente arranque se informa y archiva el temporal, nunca se promueve.
  - R1-3 *Esquema:* guardar con `log_trade` un ledger con `x_extra`. Esperado: la columna y sus valores se conservan en todos los registros.
  - R1-4 *Duplicados:* cargar y guardar con `log_trade`. Esperado: aviso con la cuenta de filas colapsadas y copia previa recuperable.
  - R1-5 *Lista vacía:* `reconcile._save` con cero filas no lanza excepción ni vacía el archivo.
  - R1-6 *Fallo de reemplazo (archivo abierto por lector en Windows):* reintentos acotados y luego error explícito con original intacto.
  - R1-7 *Estado:* corrupción de `executor_state.json` (JSON inválido) se informa explícitamente y no se trata como estado válido en silencio (hoy `load_state` lo ignora, L147-L149; el comportamiento deseado lo fija el operador si cambia semántica: **no** cambiar aquí, solo informar).
- **Aceptación:** R1-1 a R1-7 pasan; ningún escritor del inventario 3.2 escribe en modo "w" sobre el archivo final; hash del original sin cambios en R1-1/R1-2; conteo de columnas y de registros preservado en R1-3.
- **Fallo/desconocido:** si no se puede validar o reemplazar, no se escribe y la operación devuelve error; nunca "éxito" parcial.
- **Compatibilidad:** formato CSV y nombres de columnas sin cambios. **Reversión:** revertir el cambio; el CSV resultante es el mismo formato. **Evidencia:** diff, resultados reales de las pruebas, inventario final de escritores, riesgo residual de durabilidad.

### P1-02 — Exclusión mutua y transacción completa de lectura-modificación-escritura
- **Hallazgos:** F-05, F-06 (prevención de actualizaciones perdidas). **Severidad:** Alta. **Estado:** READY FOR AUTHORIZATION (depende de P1-01).
- **Comportamiento actual:** sin ningún lock; `manage` mantiene una instantánea de filas durante llamadas al broker y la escribe después (`order_executor.py:L542-L687`); `cancel` y `place` releen y escriben (`L511-L515`, `L751-L759`); `log_trade signal/exit` llaman a MT5 antes de guardar (`log_trade.py:L371-L519`). Dos procesos (p. ej. `manage` y `log_trade exit`) pueden perder actualizaciones.
- **Resultado requerido:** toda modificación del ledger es una transacción: adquirir exclusión mutua entre procesos, **releer** el archivo vigente, aplicar cambios por campo con precondición sobre el estado esperado, escribir con P1-01 y liberar. **Nunca se mantiene el lock durante una llamada de red al broker**: primero se recogen los datos del broker sin lock, después se aplica la transacción breve.
- **Dentro del alcance:** el mecanismo de exclusión (el más simple que cumpla los criterios, preferiblemente de la biblioteca estándar; no se añade dependencia sin justificación escrita); tiempo máximo de espera y manejo de lock obsoleto sin romper uno vigente; actualizaciones por clave `log_id` con precondición (p. ej. "solo si el estado sigue siendo X"); informe de conflicto cuando la precondición no se cumple; cobertura del archivo de estado.
- **Fuera del alcance:** mantener un lock durante `order_send`/`order_check`; reglas de emparejado posición↔fila (P1-04); cambios en semántica de estados; migraciones.
- **Archivos esperados:** los de P1-01 más el módulo de bloqueo.
- **Dependencias:** P0-01, P1-01. **Decisiones:** ninguna.
- **Pasos:** 1) pruebas de concurrencia que fallan hoy; 2) implementar el bloqueo; 3) transformar `place` (L511-L515), `cancel` (L751-L759), `manage` (L683-L687), `log_trade` comandos (L444, L462, L472, L519, L538) y `reconcile apply` (L284) a transacciones cortas con datos de broker recogidos antes; 4) cada transformación se prueba aislada.
- **Pruebas de regresión y fixtures:**
  - R1-8 *Sin pérdida de actualizaciones:* dos procesos de prueba aplican cada uno N actualizaciones a filas distintas del mismo ledger. Esperado: todas las 2N presentes al final.
  - R1-9 *Conflicto en la misma fila:* ambos intentan pasar la misma fila desde un estado esperado distinto. Esperado: un ganador; el otro informa conflicto y no sobrescribe.
  - R1-10 *`manage` con instantánea vieja:* el broker falso responde con retardo; entretanto otro proceso cambia una fila no relacionada. Esperado: el cambio ajeno se conserva.
  - R1-11 *Lock obsoleto:* proceso muerto deja el bloqueo. Esperado: recuperación documentada sin romper uno vivo.
  - R1-12 *Timeout:* con el lock retenido, el escritor falla tras el tiempo máximo sin escribir.
  - R1-13 *Sin lock durante red:* el broker falso bloquea una llamada; otro proceso puede escribir el ledger mientras tanto.
- **Aceptación:** R1-8 a R1-13 pasan; en R1-8 el número final de actualizaciones es exactamente 2N; ninguna llamada a `order_send`, `order_check`, `history_deals_get` ni `copy_rates_*` ocurre con el lock tomado (comprobado en el broker falso).
- **Fallo/desconocido:** timeout o conflicto producen error visible, sin escritura parcial y sin tratar el resultado como éxito.
- **Compatibilidad:** orden y contenido de CSV iguales. **Reversión:** revertir el cambio; archivos de lock desechables. **Evidencia:** diff, resultados de concurrencia reales, traza de llamadas del broker falso con la marca de lock, riesgos residuales (p. ej. procesos externos que ignoran el lock, como helpers fuera del repo).

<!-- FIN-ENTREGA-A-PARTE-3 -->

### P1-03 — `manage`: no retirar pendientes por falta de posición y no interpretar estado desconocido como cierre
- **Hallazgos:** F-06, F-13 (prevención). **Severidad:** Alta. **Estado:** READY FOR AUTHORIZATION (depende de P0-01 y P1-02). La parte de emparejado por identificador está en P1-04.
- **Comportamiento actual:** `manage` construye `live` desde `positions_get() or []` (`order_executor.py:L549-L551`); toda fila `OPEN`/`ORDER_PLACED` cuyo símbolo no esté en `live` pasa a `CLOSED` en memoria con nota "AUTO-RETIRED" (`L552-L563`); si hay posición del mismo símbolo y la entrada no coincide dentro de la tolerancia (`L564-L581`), también. Una orden pendiente no es una posición, de modo que el caso normal de una pendiente viva activa el retiro. Las filas retiradas solo se escriben si ese mismo `manage` hace un parcial (`save_log` en `L687`), por lo que el estado erróneo puede persistirse de forma intermitente. Un fallo de broker (`None`) equivale a "sin posiciones".
- **Resultado requerido:** (a) ninguna fila pasa a `CLOSED` solo porque no haya posición abierta; (b) una respuesta de broker no disponible o con error se trata como **desconocida**: sin retiros, sin BE, sin parciales y con salida de error; (c) las filas no resueltas se informan y se excluyen de la gestión, sin cambiar su estado.
- **Dentro del alcance:** clasificación de cada fila `OPEN`/`ORDER_PLACED` en: con posición compatible, con orden pendiente compatible (comentario `FRIVAL_<log_id>` y símbolo, igual que ya usa `cancel`, `L720-L722`), o NO RESUELTA; evento de auditoría nuevo para NO RESUELTA (no reutilizar el nombre `STALE_ROW_RETIRED`); distinción `None` frente a lista vacía en `positions_get`/`orders_get` dentro de `manage`; prueba de caracterización del comportamiento actual de BE/parcial.
- **Fuera del alcance:** reclasificar o cerrar filas históricas T010/T014 y similares (P4); emparejado por `position_id`/propiedad (P1-04); cambiar parámetros de BE/parcial; resultados de parcial desconocidos o no persistidos tras confirmación del broker (se especifican en la Entrega B).
- **Dependencias:** P0-01, P1-02. **Decisiones:** ninguna (la clasificación NO RESUELTA es informativa; quién la resuelve queda para P4 y el operador).
- **Pasos:** 1) escribir caracterización y regresión; 2) separar la clasificación del cambio de estado; 3) sustituir el retiro por clasificación y reporte; 4) garantizar que ningún camino de `manage` escribe estados `CLOSED` por esta vía; 5) revisión independiente.
- **Pruebas de regresión y fixtures (broker falso, ledger sintético):**
  - R1-14 fila `ORDER_PLACED`, el broker devuelve una orden pendiente con su comentario y cero posiciones. Esperado: estado intacto en memoria y en archivo; sin evento de retiro.
  - R1-15 fila `ORDER_PLACED`, el broker devuelve lista vacía definitiva de órdenes y posiciones. Esperado: estado intacto; se informa NO RESUELTA; se excluye de gestión.
  - R1-16 `positions_get` devuelve `None`. Esperado: ninguna mutación, ninguna orden enviada, mensaje "estado de broker desconocido" y código de salida de error.
  - R1-17 fila `ORDER_PLACED` de XAUUSD y una posición XAUUSD ajena a esa fila con otra entrada; en la misma ejecución se dispara un parcial de otra fila. Esperado: la fila pendiente no queda `CLOSED` en el archivo.
  - R1-18 (caracterización) fila `OPEN` con posición compatible y BE/parcial pendientes. Esperado: mismas solicitudes que el comportamiento actual.
- **Aceptación:** R1-14 a R1-18 pasan; búsqueda estática confirma que no queda ninguna asignación de `CLOSED` basada solo en ausencia de posición en `manage`; la línea base de R1-18 se registró antes del cambio.
- **Fallo/desconocido:** cualquier error o respuesta `None` del broker aborta la ejecución con error, sin efectos laterales.
- **Compatibilidad:** nuevo evento de auditoría; consumidores del audit que contaban `STALE_ROW_RETIRED` deben ajustarse (ninguno identificado en el desk; `eod_review.py` no se re-leyó para esto). **Reversión:** revertir el cambio. **Evidencia:** diff, resultados, comparación de solicitudes en R1-18, riesgo residual: filas históricas "OPEN" sin resolver quedarán visibles hasta P4.

### P1-04 — Emparejado fila↔orden/posición por identificadores y clasificación de propiedad
- **Hallazgos:** F-06, F-13, F-04 (base). **Severidad:** Alta. **Estado:** BLOCKED POLICY (D-05).
- **Comportamiento actual:** índice por símbolo (`order_executor.py:L549-L551`) y `pos[0]` por símbolo (`L590-L593`); guardia `execution_mode == "OPERATOR_MANUAL"` (`L587`) sin columna ni escritor, luego inactiva; el ticket de orden y el `position_id` no se guardan en el ledger.
- **Resultado requerido (condicional):** cada fila se empareja con su orden por ticket y comentario y, tras el fill, con su posición por `position_id`; cada orden/posición del broker se clasifica `FRIVAL_OWNED`, `OTHER_OWNED` u `OWNERSHIP_UNKNOWN`/`MIXED`; lo desconocido o mixto se informa y no recibe acciones automáticas en modo solo-Frival; la guardia de operaciones manuales se define o se retira según decisión.
- **Fuera del alcance hasta aprobar D-05:** cualquier regla concreta de propiedad; añadir columnas al ledger; rellenar identificadores históricos (P4).
- **Pruebas previstas (fixtures):** R1-19 dos posiciones del mismo símbolo, una Frival y una ajena; R1-20 orden pendiente y posición del mismo símbolo; R1-21 comentario sobrescrito por el broker en una salida; R1-22 comentario Frival con `magic` distinto (→ `OWNERSHIP_UNKNOWN`); R1-23 posición sin fila en el ledger. Resultados esperados dependen de la regla aprobada y **no** se fijan aquí.
- **Dependencias:** P1-02, D-05. **Reversión y evidencia:** igual que P1-03. **Aceptación:** pendiente de la regla aprobada; mínimo: R1-19 a R1-23 con resultado fijado por escrito por el operador antes de implementar.

### 5.5 Resumen de la Entrega A
| Ticket | Paquete | Estado | Depende de | Decisión |
|---|---|---|---|---|
| P0-01 Aislamiento offline | P0 | READY FOR AUTHORIZATION | — | — |
| P0-02 Cuarentena de `test_kill_switch.py` | P0 | READY FOR AUTHORIZATION | P0-01 | — |
| P0-03 Límites de permisos | P0 | BLOCKED POLICY | — | D-10 |
| P1-01 Atomicidad y esquema | P1 | READY FOR AUTHORIZATION | P0-01 | — |
| P1-02 Exclusión mutua RMW | P1 | READY FOR AUTHORIZATION | P0-01, P1-01 | — |
| P1-03 `manage` sin retiros destructivos | P1 | READY FOR AUTHORIZATION | P0-01, P1-02 | — |
| P1-04 Emparejado por identificadores | P1 | BLOCKED POLICY | P1-02 | D-05 |

Sin ciclos de dependencia en esta entrega (orden topológico: P0-01 → P0-02, P1-01 → P1-02 → P1-03/P1-04). Cobertura de hallazgos en esta entrega: F-05, F-06, F-11, F-12, F-22 y prevención futura de F-13. Pendiente para la Entrega B: F-01, F-02, F-03, F-04, F-08, F-09, F-14 a F-20 y las rutas de resultado desconocido de `place`, `manage` y `close-all`. Pendiente para la Entrega C: F-10, F-13 (histórico), F-25 a F-28, y el procedimiento de traspaso.

**Estado del documento tras la Entrega A:** ESPECIFICACIÓN PARCIAL. IMPLEMENTACIÓN NO AUTORIZADA.

<!-- FIN-ENTREGA-A -->

---

## Sección 6. Entrega B — huecos de fuente, decisiones complementarias y convenciones (P2/P3)

**Estado del documento durante la Entrega B:** ESPECIFICACIÓN PARCIAL. IMPLEMENTACIÓN NO AUTORIZADA. Línea base de código sin cambios: `7f9df8e8428e239a85136b7b2a3568f40301617b` (árbol de trabajo no verificable con las herramientas permitidas).

### 6.1 Huecos de fuente cerrados para P2/P3
| Tema | Hallazgo verificado en este turno | Referencia |
|---|---|---|
| Validación de estado de fila antes de enviar | `cmd_place` y `guardrail_report` (releído completo) **no comprueban el estado de la fila**: una fila `PENDING_FILL` obsoleta (p. ej. T008, T012) o una fila ya colocada puede enviarse de nuevo | `order_executor.py:L401-L414, L284-L398` |
| Reserva exclusiva | Ausente; `PLACE_ATTEMPT` es solo un registro de auditoría | `L414`; ver 3.2 |
| `order_check` | Su resultado se guarda en el audit; no gobierna la decisión | `L497-L500` |
| Resultado `None`/fallo | `result is None or retcode != DONE` se informa como fallo ("FAILED... stays PENDING_FILL"); no distingue rechazo definitivo de resultado desconocido | `L501-L505` |
| `audit()` | Escritura sin manejo de errores; `PLACE_RESULT` se escribe entre el envío y la actualización de fila | `L222-L230, L499-L515` |
| Forma de retorno de `guardrail_report` | Con símbolo o tick no disponibles devuelve `{"ok": False, "reason": ...}` sin clave `failed`, y `cmd_place` accede a `rep['failed']` → `KeyError` (fallo cerrado, pero sin auditoría) | `L291-L292` vs `L415-L418` |
| Estado `None` del broker en guardarraíles | `positions_get() or []` convierte `None` en "sin posiciones"; no hay `orders_get` en el cálculo | `L324, L346-L356` |
| `close-all` | Solo `positions_get`; un resultado `DONE_PARTIAL` o rechazo se informa como `REJECT` sin acción; sin re-consulta final; cierra toda posición de la cuenta; usa `magic` 20261001 solo en la solicitud | `L765-L806` |
| `cancel` | Considera éxito `DONE` o `DONE_PARTIAL`; lee `orders_get` después solo para contar; empareja por símbolo y comentario | `L720-L760` |
| BE/parcial | Volumen parcial `round(vol*0.5, 2)` sin consultar paso/mínimo del broker; PnL del parcial estimado con precio de tick; `realised_r` usa `abs(partial_at - entry)` como denominador; el estado `PARTIAL_DONE` se guarda tras el envío y solo si `save_log` funciona; BE no deja registro propio en el ledger; `p.sl` es el valor previo a la modificación de la misma iteración | `L603-L689` |
| Funciones con valores por defecto silenciosos | `_money_per_price_unit_per_lot` (L146-L169), `_account_equity` (L246-L262, defecto `EQUITY_REFERENCE` = 600), `_broker_field` (L224-L243). Llamadas: `_size_volume` L277-L282; `cmd_signal` L382, L392-L393; `cmd_exit` L503, L511; `cmd_size` L580-L583 | `log_trade.py` |
| Atribución diaria y estado | `eod_review` agrupa por `logged_at_server`[:10]; el estado usa fecha UTC; `daily_realised` por fecha de servidor de la señal | `eod_review.py:L76-L96`; `order_executor.py:L142, L195-L198` |
| Documentación primaria | MQL5: `positions_get` devuelve `None` en error; `history_deals_get` admite filtro por `position`; `order_calc_margin` no considera pendientes ni posiciones actuales; `order_check` devuelve estructura con margin/margin_free/margin_level; tipos de expiración `ORDER_TIME_GTC/DAY/SPECIFIED/SPECIFIED_DAY`; en `order_send` el campo `expiration` aplica a `TIME_SPECIFIED` | URLs en el informe v2, más `https://www.mql5.com/en/docs/python_metatrader5/mt5positionsget_py` y `.../mt5ordersend_py` |
| **Aún sin confirmar** | La documentación de `order_send` no declara que pueda devolver `None`; solo los comentarios del código lo afirman (`L650`, `L777-L778`). Los tickets lo tratan como **desconocido**, por prudencia; confirmar en demo aislada | — |

### 6.2 Decisiones complementarias (todas PENDING OPERATOR APPROVAL)
Se añaden sin reescribir la Sección 2.

| ID | Pregunta | Fuentes | Alternativas | Propuesta (no aprobada) | Afecta | Bloquea |
|---|---|---|---|---|---|---|
| D-11 | Semántica del piso de margen una vez corregida la estimación | `MIN_MARGIN_LEVEL = 100` fue fijado el 2026-10-02 sobre una estimación defectuosa (`order_executor.py:L108-L116`); en la misma orden el audit mostró 187% frente a 6883.56% del broker | Mantener 100 con el cálculo corregido; fijar otro valor; basarse solo en aceptación del broker | Medir primero en modo sombra; el operador decide el piso con datos | P3-02 | Cambio del criterio de bloqueo (no la medición en sombra) |
| D-12 | Tratamiento del riesgo a precio ejecutable | Nudge de spread y precio de mercado (`L437-L482`); riesgo evaluado sobre precio de señal (`L316-L319`) | Bloquear si excede; reducir volumen; tolerancia explícita | Recalcular al precio real incluyendo el spread como componente informado y bloquear si supera el tope, sin redimensionar automáticamente | P3-03 | Implementación del bloqueo |
| D-13 | Definición de PnL neto y de R | `pnl_usd` suma solo `profit` (`log_trade.py:L356`); costos separados en la API | Mantener bruto; añadir columnas netas en paralelo; sustituir `pnl_usd` y alimentar breakers con neto | Añadir columnas netas en paralelo; no cambiar `pnl_usd`, breakers ni denominadores hasta aprobar | P3-07 | Uso del neto en breakers, estadísticas o R |
| D-14 | ¿Se imponen en el ejecutor las compuertas de datos documentadas en el brief (edad de tick, spread/ATR, rollover, M15/ATR, ATR limpio)? | Brief; ausentes en el ejecutor; helper en `%TEMP%` no versionado; unidades de oro en reglas de ATR | Dejar al agente; medir en sombra; imponer por símbolo con umbrales aprobados | Medir en sombra primero; umbrales y unidades por símbolo los fija el operador | P3-09 | Cualquier bloqueo por estas compuertas |

### 6.3 Reglas comunes de los tickets P2/P3
Lo definido en la Sección 3 (identificadores, propiedad, estados) y en P0/P1 sigue vigente. Ningún ticket mantiene un lock durante una llamada al broker. "Aceptado" nunca implica "llenado"; "plano" solo se declara tras una verificación de estado final; un estado de broker desconocido nunca se interpreta como cierre ni como ausencia de exposición; un PnL ausente nunca se interpreta como cero.

<!-- FIN-ENTREGA-B-PARTE-1 -->

---

## Sección 7. Tickets P2 — Idempotencia, exposición pendiente y desmontaje verificado

### P2-01 — Reserva exclusiva de envío, identidad de intento y validación de estado de fila
- **Hallazgos:** F-04, F-20. **Prioridad:** alta; **severidad:** Alta. **Estado:** READY FOR AUTHORIZATION (depende de P1-01 y P1-02).
- **Comportamiento actual:** `place` solo exige que la fila exista (`L406-L409`); no valida su estado (`L401-L414`, `guardrail_report` L284-L398); no reserva; actualiza el estado tras el envío (`L511-L515`). `log_trade signal` reemplaza la fila existente con el mismo `log_id` y la devuelve a `PENDING_FILL` (`log_trade.py:L435-L443`). Registros locales: múltiples envíos aceptados para T010 y T014 (audit L3, L5, L10, L25, L27 en la lectura previa; **no establecen posiciones simultáneas**).
- **Resultado requerido:** (a) solo una fila en estado `PENDING_FILL` puede someterse a envío; (b) antes de `order_send` se persiste una reserva con un identificador de intento único; (c) mientras exista un intento no resuelto (`RESERVED`, `SENT_UNKNOWN`) para ese `log_id`, ningún otro envío es posible; (d) `signal` no puede sobrescribir una fila que ya salió de `PENDING_FILL`.
- **Dentro del alcance:** columnas nuevas conservando el esquema (identificador de intento, estado de envío, ticket de orden del broker), añadidas con la unión de columnas de P1-01; transacción corta de reserva (P1-02) **antes** de la llamada al broker y transacción corta de actualización **después**; estados de envío `RESERVED`, `ACCEPTED`, `REJECTED`, `SENT_UNKNOWN`; el ticket de orden se guarda en el ledger.
- **Fuera del alcance:** reemplazo tras cancelación confirmada (requiere una nueva señal con nuevo `log_id` y es política del operador); reconciliación de intentos desconocidos (P2-02); migración de filas históricas; cambio de guardarraíles.
- **Dependencias:** P1-01, P1-02. **Decisiones:** ninguna (no fija propiedad: opera sobre `log_id`).
- **Pasos:** 1) pruebas de regresión que fallan hoy; 2) validación de estado y reserva; 3) actualización post-envío; 4) endurecer `signal`; 5) revisión independiente.
- **Pruebas de regresión y fixtures (broker falso, ledger sintético):**
  - R2-1 dos `place` secuenciales del mismo `log_id` en `PENDING_FILL`. Esperado: un `order_send`; el segundo se rechaza antes de llamar al broker.
  - R2-2 `place` de una fila `CANCELLED_UNFILLED`, `OPEN` o `CLOSED`. Esperado: rechazo sin `order_send`.
  - R2-3 dos procesos simultáneos sobre el mismo `log_id`. Esperado: exactamente un `order_send`.
  - R2-4 caída simulada tras la reserva y antes del envío. Esperado: fila `RESERVED`; el siguiente `place` se rechaza informando intento no resuelto.
  - R2-5 `signal` sobre una fila `ORDER_PLACED`. Esperado: rechazo sin modificar la fila.
  - R2-6 `place` con fila obsoleta `PENDING_FILL` marcada por el operador como no vigente (fixture T008/T012). Esperado: la regla de rechazo debe poder expresarse con un estado explícito; si el operador no define el estado, el caso queda documentado como riesgo residual.
- **Aceptación:** R2-1 a R2-5 pasan; el broker falso registra como máximo un `order_send` por `log_id` en R2-1/R2-3; el ticket de orden aparece en el ledger tras R2-1; ninguna llamada al broker ocurre con la transacción de reserva abierta.
- **Fallo/desconocido:** si la reserva no se puede persistir, no se envía. Si el envío ocurre y la actualización posterior falla, la fila permanece `RESERVED` y se emite un registro de auditoría de reparación (ver P2-02).
- **Compatibilidad:** columnas nuevas opcionales para filas antiguas (vacías = sin intento previo); `place` documentado. **Reversión:** revertir cambio; las columnas nuevas se ignoran. **Evidencia:** diff, resultados reales, traza del broker falso con orden de llamadas, riesgo residual (idempotencia a nivel de aplicación; el broker no expone clave de idempotencia en la documentación consultada).

### P2-02 — Resultados desconocidos del broker y fallos de auditoría
- **Hallazgos:** F-04, F-20, F-01 (parcial). **Severidad:** Alta. **Estado:** READY FOR AUTHORIZATION (depende de P2-01 y P1-02). La documentación de `order_send` no declara `None`; el ticket lo trata como desconocido por prudencia (ver 6.1).
- **Comportamiento actual:** `result is None` o retcode distinto de `DONE` se muestran como "FAILED" y la fila queda `PENDING_FILL` (`L501-L505`); `audit()` no maneja errores (`L222-L230`); `guardrail_report` devuelve una forma sin clave `failed` (`L291-L292`, `L415-L418` → `KeyError`); `positions_get() or []` y `orders_get() or []` equivalen "error" a "vacío" (`L324, L550, L721, L771`); `cancel` acepta `DONE_PARTIAL` como éxito (`L738-L739`).
- **Resultado requerido:** una taxonomía común de resultados (ACEPTADO, RECHAZADO definitivo, DESCONOCIDO) aplicada a `place`, `cancel`, cierres de `close-all` y de parcial; los estados DESCONOCIDO impiden nuevas acciones sobre el mismo objeto hasta resolverse; un fallo de auditoría tras un envío no deja silenciosamente la fila inconsistente; un `None` de consulta de broker en guardarraíles bloquea la colocación (fallo cerrado) en lugar de contar como "sin exposición".
- **Dentro del alcance:** clasificación de retcodes (lista de retcodes por categoría aprobada por el operador al autorizar, derivada de la documentación MQL5 de códigos de retorno, que **debe consultarse** antes de implementar); manejo de excepciones de `order_send`; escritura de auditoría con manejo de error y reintento acotado que, si falla, marca la fila `SENT_UNKNOWN` o `RESERVED` por el camino de P2-01; corrección de la forma de retorno de `guardrail_report`.
- **Fuera del alcance:** reconciliación automática de un intento desconocido contra el historial (se informa; la resolución es manual o parte de P4); cambios de umbrales.
- **Dependencias:** P2-01, P1-02. **Decisiones:** ninguna.
- **Pruebas de regresión y fixtures:**
  - R2-7 `order_send` devuelve `None`. Esperado: fila `SENT_UNKNOWN`; ningún reenvío; mensaje de resultado desconocido; salida de error.
  - R2-8 `order_send` lanza una excepción. Esperado: igual que R2-7.
  - R2-9 retcode de rechazo definitivo (p. ej. parámetros inválidos). Esperado: fila `REJECTED` con el retcode; reenvío posible solo por nueva señal.
  - R2-10 `order_send` acepta y la escritura de auditoría lanza error. Esperado: la fila no queda en `PENDING_FILL`; se registra la reparación; no hay segundo envío.
  - R2-11 `positions_get` devuelve `None` en `guardrail_report`. Esperado: colocación bloqueada con motivo "estado de broker desconocido".
  - R2-12 símbolo/tick no disponible. Esperado: bloqueo con mensaje, sin `KeyError`.
  - R2-13 `cancel` con `DONE_PARTIAL`. Esperado: resultado DESCONOCIDO hasta una verificación de estado final del objeto.
- **Aceptación:** R2-7 a R2-13 pasan; ningún camino interpreta `None` como éxito, cierre o ausencia de exposición.
- **Fallo/desconocido:** el propio ticket define el comportamiento: informar y no actuar.
- **Compatibilidad:** nuevos valores de estado de envío; textos de salida pueden cambiar. **Reversión:** revertir. **Evidencia:** tabla retcode→categoría aprobada, diff, resultados reales, riesgo residual (no se fuerza reconciliación automática).

### P2-03 — Persistencia write-ahead del parcial y no repetición
- **Hallazgos:** F-18, F-20. **Severidad:** Media. **Estado:** READY FOR AUTHORIZATION (depende de P1-02, P2-02). La reconciliación por historial del broker depende de P1-04/D-05 y queda fuera.
- **Comportamiento actual:** tras un parcial aceptado, `be_executed = "PARTIAL_DONE"` se guarda solo si `save_log` funciona (`L682-L687`); si falla, el siguiente ciclo puede repetir el parcial (la condición `be_executed != "PARTIAL_DONE"` sigue cumpliéndose, `L641`). El PnL del parcial es estimación con precio de tick (`L673`).
- **Resultado requerido:** antes de enviar el cierre parcial se persiste `PARTIAL_SENDING`; tras el resultado se pasa a `PARTIAL_DONE` (aceptado), se limpia (rechazo definitivo) o `PARTIAL_UNKNOWN` (desconocido); un estado distinto de vacío impide repetir el parcial.
- **Fuera del alcance:** parámetros de BE/parcial; emparejado por posición (P1-04); resolución de `PARTIAL_UNKNOWN`.
- **Pruebas:** R2-14 parcial aceptado y fallo de persistencia inyectado → el siguiente ciclo no reenvía; R2-15 resultado `None` → `PARTIAL_UNKNOWN`, sin reenvío; R2-16 rechazo definitivo → estado limpio y reintento permitido; R2-17 dos procesos `manage` simultáneos → un solo cierre.
- **Aceptación:** R2-14 a R2-17 pasan; el broker falso registra a lo sumo un cierre parcial por fila; el estado final del ledger refleja cada caso.
- **Compatibilidad:** nuevos valores de `be_executed`. **Reversión:** revertir. **Evidencia:** como P2-02.

<!-- FIN-ENTREGA-B-PARTE-2 -->

### P2-04 — `close-all`: verificación de estado final en el alcance actual
- **Hallazgos:** F-01. **Severidad:** Crítica (el hallazgo); **paquete** P2. **Estado:** READY FOR AUTHORIZATION (depende de P0-01 y P2-02). No cambia el alcance (sigue operando sobre todas las posiciones, como hoy); el alcance es D-04/P2-05.
- **Comportamiento actual:** `cmd_close_all` (`L765-L806`) envía un cierre por posición devuelta por `positions_get()`; trata solo `DONE` como éxito (`L798`); un `DONE_PARTIAL` o rechazo se imprime como `REJECT`; no vuelve a consultar; no mira órdenes pendientes; `_mt5()` termina el proceso si no hay conexión (`L206-L215`); el evento `CLOSE_ALL` se audita aun sin éxito.
- **Resultado requerido:** tras los envíos, el comando consulta de nuevo posiciones y órdenes, repite hasta un máximo acotado de intentos y termina con un resultado explícito: `POSICIONES_CERRADAS_SIN_PENDIENTES_VERIFICADO` (0 posiciones y 0 órdenes confirmadas por consulta no nula), `POSICIONES_CERRADAS_CON_PENDIENTES` (se informan) o `NO_PLANO_O_DESCONOCIDO` (posiciones restantes, consulta `None` o broker no disponible), con código de salida distinto de cero salvo en el primer caso. Nunca se imprime "plano" sin esa verificación.
- **Dentro del alcance:** re-consulta y reintentos acotados; manejo de `DONE_PARTIAL`, rechazo, `None` y excepción por posición; salida de broker no disponible como DESCONOCIDO (sin `sys.exit(1)` silencioso a mitad de proceso: el fallo de conexión inicial devuelve DESCONOCIDO con el mensaje correspondiente); idempotencia en invocaciones repetidas; registro de la lista residual en la auditoría.
- **Fuera del alcance:** cancelar pendientes y filtrar por propiedad (P2-05); modificar el kill switch.
- **Pruebas (broker falso):** R2-18 una posición, cierre aceptado, re-consulta vacía y sin órdenes → resultado verificado; R2-19 cierre aceptado pero la re-consulta aún devuelve la posición → reintento y, agotado el máximo, `NO_PLANO_O_DESCONOCIDO`; R2-20 `DONE_PARTIAL` → se reintenta con el volumen restante; R2-21 `positions_get` devuelve `None` en la re-consulta → DESCONOCIDO; R2-22 una orden pendiente presente → `POSICIONES_CERRADAS_CON_PENDIENTES`; R2-23 segunda invocación sin posiciones → mismo resultado verificado y sin envíos; R2-24 `initialize` falla → DESCONOCIDO con código de error, sin envíos.
- **Aceptación:** R2-18 a R2-24 pasan; el código de salida es cero solo en R2-18 y R2-23; ninguna cadena "flat" aparece sin verificación; cada envío tiene registro de auditoría con su categoría de resultado.
- **Reversión:** revertir. **Evidencia:** diff, resultados, trazas del broker falso, riesgo residual (una orden pendiente puede llenarse entre la verificación y el fin del proceso; se informa, no se elimina).

### P2-05 — Desmontaje de emergencia: alcance y cancelación de pendientes
- **Hallazgos:** F-01. **Estado:** BLOCKED POLICY (D-04, D-05).
- **Resultado requerido (condicional):** orden fijo: impedir nuevas colocaciones; cancelar pendientes del alcance aprobado; cerrar posiciones del alcance; re-consultar y repetir hasta `PLANO` o agotar intentos; informar `OWNERSHIP_UNKNOWN`/`MIXED` sin actuar en modo solo-Frival; manejar fallo de cancelación, pendiente que se llena durante la cancelación (la posición nueva se detecta en la re-consulta y se cierra), fallo de cierre parcial, repetición y broker no disponible.
- **Pruebas previstas:** R2-25 pendiente propia cancelada y posición propia cerrada → `PLANO` solo tras re-consulta; R2-26 pendiente que se llena durante la cancelación; R2-27 fallo de cancelación → no se afirma `PLANO`; R2-28 orden/posición ajena presente → se informa y no se toca; R2-29 propiedad desconocida/mixta → se informa y no se toca.
- **Aceptación:** pendiente de D-04 y D-05; mínimo R2-25 a R2-29 con resultados fijados por el operador. **Dependencias:** P2-04, P1-04, P2-02.

### P2-06 — Exposición pendiente y reserva de riesgo en los límites
- **Hallazgos:** F-02. **Estado:** BLOCKED POLICY (D-03; D-02 para fixtures).
- **Comportamiento actual:** `guardrail_report` cuenta solo `positions_get()` en `max_positions` y en `open_risk_pct` (`L324, L346-L352, L367-L370`); no hay `orders_get`.
- **Resultado requerido (condicional):** según la alternativa de D-03 (solo abiertas / abiertas+pendientes / reserva de riesgo de pendientes al SL), con consultas no nulas (P2-02) y fixtures explícitos de N, posiciones y pendientes fijados por el operador.
- **Pruebas previstas:** R2-30 con la política aprobada, 1 posición + 2 pendientes y límite N; la solicitud siguiente se rechaza solo si excede N bajo esa política; R2-31 reserva de riesgo sumada al agregado.
- **Aceptación:** pendiente de D-03; **no** se reutiliza el ejemplo "2 pendientes → la tercera se rechaza" del informe v1 (era inconsistente con `MAX_POSITIONS = 3`).

### P2-07 — Semántica de "misma tesis USD"
- **Hallazgos:** F-08. **Estado:** BLOCKED POLICY (D-06).
- **Comportamiento actual:** agrupación por símbolo ciega al lado (`L67-L68, L344-L356`); el candidato se suma al contador (`L356`) y el criterio es `< MAX_SAME_THESIS` (`L371`), lo que da un tope efectivo distinto del valor numérico (a confirmar con fixture).
- **Resultado requerido (condicional):** tabla símbolo×lado aprobada por el operador y definición de si el tope incluye al candidato.
- **Pruebas previstas:** R2-32 a R2-35 con fixtures símbolo×lado de la tabla aprobada, incluidos casos opuestos y casos de la misma tesis.
- **Aceptación:** pendiente de D-06.

### P2-08 — Expiración de órdenes pendientes
- **Hallazgos:** F-19. **Estado:** BLOCKED POLICY (D-09) y NEEDS EVIDENCE (modos de expiración soportados por el broker/símbolo).
- **Comportamiento actual:** pendientes con `ORDER_TIME_GTC`, sin expiración de broker (`L493`).
- **Evidencia que falta:** confirmación, en demo aislada y autorizada, de que `ORDER_TIME_SPECIFIED` es aceptado para cada símbolo del alcance (la referencia MQL5 lista los tipos pero no su soporte por símbolo).
- **Resultado requerido (condicional):** expiración ligada al horizonte por señal aprobado por el operador; duración la fija el operador; cancelación a cargo del broker coherente con el registro del ledger.
- **Pruebas previstas:** R2-36 orden con expiración aceptada en el fixture; R2-37 símbolo sin soporte → se rechaza en lugar de caer a GTC silenciosamente; R2-38 coherencia entre tiempo de expiración y estado del ledger.
- **Aceptación:** pendiente de D-09 y de la evidencia.

### 7.9 Resumen P2
| Ticket | Estado | Depende de | Decisión |
|---|---|---|---|
| P2-01 Reserva e identidad de intento | READY FOR AUTHORIZATION | P1-01, P1-02 | — |
| P2-02 Resultados desconocidos | READY FOR AUTHORIZATION | P2-01, P1-02 | — |
| P2-03 Parcial write-ahead | READY FOR AUTHORIZATION | P1-02, P2-02 | — |
| P2-04 Verificación final de `close-all` | READY FOR AUTHORIZATION | P0-01, P2-02 | — |
| P2-05 Alcance y pendientes en emergencia | BLOCKED POLICY | P2-04, P1-04, P2-02 | D-04, D-05 |
| P2-06 Exposición pendiente | BLOCKED POLICY | P2-02 | D-03 (D-02) |
| P2-07 Tesis USD | BLOCKED POLICY | P2-02 | D-06 |
| P2-08 Expiración | BLOCKED POLICY / NEEDS EVIDENCE | P2-02 | D-09 |

<!-- FIN-ENTREGA-B-PARTE-3 -->

---

## Sección 8. Tickets P3 — Margen, riesgo a precio ejecutable, relojes, breakers y PnL neto

### P3-01 — Medición en sombra de la estimación de margen (sin cambiar el bloqueo)
- **Hallazgos:** F-03. **Severidad:** Alta. **Estado:** READY FOR AUTHORIZATION (depende de P0-01 y P2-02).
- **Comportamiento actual:** `notional = vol × trade_contract_size × entry` y `margin_needed = notional / leverage` (`L326-L329`), usados en el guardarraíl `margin` (`L377-L378`). Para USDJPY el precio está en JPY. Evidencia local: nocional 157754 y `margin_level_after` 187% frente a margen 8.76 y nivel 6883.56% devueltos por `order_check` en la misma ventana (audit L36-L39, lectura previa). El comentario de `L108-L116` justificó bajar el piso con ese cálculo. `order_calc_margin` no considera pendientes ni posiciones actuales (doc MQL5).
- **Resultado requerido:** cada `PLACE_ATTEMPT` registra, sin afectar la decisión: la estimación actual, la estimación de `order_calc_margin` para la misma acción/símbolo/volumen/precio, y —cuando se invoque `order_check`— su margen y nivel de margen. Los datos permiten calibrar sin cambiar nada.
- **Dentro del alcance:** campos de auditoría nuevos; invocación de `order_calc_margin` con manejo de `None` (registrar "no disponible"); comparación en el broker falso.
- **Fuera del alcance:** cambiar el umbral o el criterio de bloqueo (P3-02/D-11); reescribir la fórmula propia del repositorio.
- **Pasos:** pruebas con tres fixtures de símbolo (USD base, USD cotizada, metal) donde el broker falso devuelve valores conocidos; implementar el registro; revisión.
- **Pruebas:** R3-1 USDJPY: los tres valores registrados y la decisión de bloqueo idéntica a la actual; R3-2 `order_calc_margin` devuelve `None` → registro "no disponible" y decisión sin cambios; R3-3 EURUSD y XAUUSD con valores del fixture registrados.
- **Aceptación:** R3-1 a R3-3 pasan; la decisión (pasa/bloquea) de cada fixture coincide con la del código de línea base (prueba de caracterización); los campos nuevos están presentes en el audit.
- **Reversión:** revertir. **Evidencia:** diff, resultados, tabla comparativa sintética. **Nota:** no se fija un tamaño de lote que deba pasar.

### P3-02 — Cambio del criterio de margen a la verificación del broker
- **Hallazgos:** F-03. **Estado:** BLOCKED POLICY (D-11) y NEEDS EVIDENCE (datos de P3-01 y verificación en demo aislada autorizada).
- **Resultado requerido (condicional):** el bloqueo por margen usa el resultado de `order_check` para la solicitud (que incorpora cuenta, posiciones y pendientes) y el criterio que apruebe D-11; `None`/error → DESCONOCIDO → bloqueo.
- **Pruebas previstas:** R3-4 `order_check` con rechazo por margen insuficiente → bloqueo; R3-5 `None` → bloqueo; R3-6 nivel de margen sobre el piso aprobado → permitido; R3-7 comparación con estimación independiente dentro de la tolerancia que fije el operador.
- **Aceptación:** pendiente de D-11 y de la tolerancia. **Dependencias:** P3-01, P2-02.

### P3-03 — Riesgo recalculado al precio ejecutable
- **Hallazgos:** F-15. **Estado:** BLOCKED POLICY (D-12).
- **Comportamiento actual:** el riesgo (`L316-L319`) y el R:R se calculan con `entry` de la fila; después `place` fija el precio real (mercado `L431-L433`; nudge de spread `L437-L460`) y solo audita `LIMIT_ENTRY_NUDGE` (`L478-L482`). Evidencia local: T040 nivel 4119.50 colocado a 4119.31 con SL 4122.50 (distancia efectiva 3.19 frente a 3.00 evaluada).
- **Resultado requerido (condicional):** recalcular distancia, riesgo y R:R al precio final de la solicitud y aplicar el tratamiento que apruebe D-12, antes de `order_send`.
- **Pruebas previstas:** R3-8 nudge que lleva el riesgo sobre el tope; R3-9 mercado con ask distinto del `entry`; R3-10 spread informado como componente separado.
- **Aceptación:** pendiente de D-12. **Dependencias:** P2-02.

### P3-04 — Fallos explícitos en lugar de valores por defecto silenciosos
- **Hallazgos:** F-16. **Severidad:** Baja (corregida). **Estado:** READY FOR AUTHORIZATION (depende de P0-01).
- **Comportamiento actual:** si falla el import de MT5, `initialize`, la información del símbolo o salta una excepción, `_money_per_price_unit_per_lot` devuelve 10 000 (`log_trade.py:L146-L169`); `_account_equity` devuelve `EQUITY_REFERENCE` = 600 (`L246-L262`); `_broker_field` devuelve el valor por defecto (`L224-L243`). Afecta `_size_volume` (L277-L282), `cmd_signal` (L382, L392-L393), `cmd_exit` (L503, L511), `cmd_size` (L580-L583). Con volumen ∝ 1/valor monetario, el defecto sobredimensiona EURUSD ≈10× y subdimensiona XAUUSD ≈100× y USDJPY ≈16× (valores de referencia históricos: 100, 100000, ~632; no constantes universales).
- **Resultado requerido:** en las rutas de dimensionamiento, riesgo y PnL no existe valor monetario ni equity por defecto: si el broker no responde, el comando falla con un error explícito y sin escribir en el ledger.
- **Fuera del alcance:** `cmd_exit` con historial no disponible (P3-07); cambiar la fórmula de sizing.
- **Pruebas:** R3-11 `MetaTrader5` no disponible en `signal --risk-pct` → error y ledger intacto; R3-12 `trade_tick_size` cero → error; R3-13 `account_info` `None` → error (no 600); R3-14 caso normal → volumen igual al de la línea base.
- **Aceptación:** R3-11 a R3-14 pasan; ninguna ruta de sizing devuelve un valor monetario o equity por defecto; hash del ledger sin cambios en los casos de error.
- **Compatibilidad:** `signal` sin MT5 ya no escribe filas con valores inventados. **Reversión:** revertir. **Evidencia:** diff, resultados, lista de llamadas revisadas.

### P3-05 — Reloj único y offsets
- **Hallazgos:** F-17. **Estado:** BLOCKED POLICY (D-07) y NEEDS EVIDENCE (calendario/zona horaria del servidor).
- **Comportamiento actual:** `log_trade.py:L40` usa `LOCAL_OFFSET_H = -8`; los demás módulos usan −5 (`order_executor.py:L224`, `counterfactual.py:L77`, `reconcile_deals.py:L46`, `market_context.py:L41`); el servidor es +3 fijo en todos (`order_executor.py:L134`, `log_trade.py:L39`, `eod_review.py:L29`, etc.). Las columnas `*_local` del ledger usan −8 y el audit −5.
- **Resultado requerido (condicional):** una única definición de reloj y conversión aprobada; las columnas históricas no se reescriben (P4).
- **Evidencia que falta:** calendario del servidor del broker (cambio de horario) y confirmación de la zona local del operador.
- **Pruebas previstas:** R3-15 un mismo instante produce el mismo texto local y de servidor en todos los módulos; R3-16 fecha de servidor alrededor de la medianoche del servidor; R3-17 transición de horario con fixture.
- **Aceptación:** pendiente de D-07 y de la evidencia.

### P3-06 — Sesión, PnL diario, ancla de equity y breaker de racha
- **Hallazgos:** F-09, F-23. **Estado:** BLOCKED POLICY (D-07, D-08).
- **Comportamiento actual:** estado por fecha UTC (`order_executor.py:L142`); ancla = equity del primer envío exitoso (`L507-L509`), hoy 0.0 en `executor_state.json`; `daily_realised` por `logged_at_server` (fecha de señal; `L195-L198`); racha ordenada por `exit_time_local` con respaldo en `logged_at_server` (`L182-L185`); `pnl_usd` vacío se cuenta como 0.0 y corta la racha (`L178-L181`); comentario promete reinicio por "nuevo día" (`L121-L127`) que el código no hace; `eod_review.py:L76-L96` agrupa por fecha de señal.
- **Resultado requerido (condicional):** semántica fijada por D-07/D-08: reloj, atribución (cierre confirmado por el broker o señal), ancla, definición de pérdida y procedimiento explícito de reinicio con registro; un cierre con PnL ausente se marca DESCONOCIDO, se informa y **no** se cuenta como cero; el breaker nunca se reinicia automáticamente.
- **Pruebas previstas:** R3-18 cierre con `pnl_usd` vacío → DESCONOCIDO informado; R3-19 operaciones que cruzan la medianoche de servidor y la UTC; R3-20 orden de cierres con relojes mezclados; R3-21 reinicio solo con la acción explícita registrada; R3-22 `eod_review` con la atribución aprobada.
- **Aceptación:** pendiente de D-07 y D-08. **Dependencias:** P1-02, P3-05.

### P3-07 — Componentes de PnL neto y tratamiento de datos ausentes
- **Hallazgos:** F-14, F-28. **Severidad:** Media. **Estado:** READY FOR AUTHORIZATION para el cálculo y el registro en columnas nuevas; BLOCKED POLICY (D-13) para usar el neto en `pnl_usd`, breakers, estadísticas o R. Depende de P1-01.
- **Comportamiento actual:** `_resolve_realised_from_broker` suma solo `d.profit` de los deals del `position_id` de la entrada (`log_trade.py:L355-L356`), con ventana de 14 días (`L344`); `reconcile_deals` suma profit de los OUT y swap, sin comisión ni fee; sin historial, `cmd_exit` usa una estimación por precio (`L507-L510`). La documentación MQL5 de `history_deals_get` separa `commission`, `swap`, `profit` y `fee` y permite filtrar por `position`.
- **Resultado requerido:** por posición, registrar en columnas nuevas (junto a `pnl_usd`, que no cambia) las sumas de `profit`, `commission`, `swap` y `fee` y el neto; si algún componente o el historial no está disponible, el campo queda marcado DESCONOCIDO y se informa; nunca se asume cero; se informa cuando se usó la ventana de respaldo o la estimación por precio.
- **Fuera del alcance:** cambiar `pnl_usd`, breakers, R o estadísticas (D-13); migrar filas históricas (P4); emparejado por propiedad (P1-04/D-05; hoy la entrada se localiza por comentario exacto y, en respaldo, por subcadena del `log_id`, `L199-L210`).
- **Pruebas (deals sintéticos):** R3-23 profit, commission, swap, fee en entrada, parcial y salida → sumas por componente y neto exactos; R3-24 comisión como deal separado (si aplica según el fixture) → sin doble conteo; R3-25 historial fuera de ventana → DESCONOCIDO, no cero; R3-26 `history_deals_get` devuelve `None` → DESCONOCIDO; R3-27 parcial y cierre final del mismo `position_id`.
- **Aceptación:** R3-23 a R3-27 pasan; `pnl_usd` y `r_multiple` de los fixtures coinciden con la línea base; ningún campo ausente se escribe como 0.
- **Compatibilidad:** columnas nuevas (P1-01). **Reversión:** revertir. **Evidencia:** diff, resultados, supuestos sobre la liquidación de comisión del broker (no verificable localmente).

### P3-08 — Gestión: volumen del parcial y métricas de evento
- **Hallazgos:** F-18. **Severidad:** Media. **Estado:** READY FOR AUTHORIZATION (depende de P2-03).
- **Comportamiento actual:** `close_vol = round(vol × 0.5, 2)` sin consultar `volume_step`/`volume_min` del símbolo (`L642-L643`); el PnL del evento se estima con el precio de tick (`L673`) y `realised_r` divide por `abs(partial_at − entry) × mv` (`L674-L678`), no por el riesgo planificado: en el audit, T040 registra 0.02 frente a un R de ledger de 0.38 para la operación completa. Con `tp2` vacío el nivel del parcial coincide con el del BE (`L619-L621`).
- **Resultado requerido:** (a) el volumen del parcial se ajusta al paso y mínimo del broker; si no es factible se omite y se informa; (b) el evento de auditoría etiqueta `realised_usd` como estimación y define `realised_r` con el riesgo planificado de la fila como denominador o lo renombra para evitar confusión (el operador elige al autorizar).
- **Fuera del alcance:** parámetros BE/parcial, `tp2`, momento del parcial (estrategia).
- **Pruebas:** R3-28 volumen 0.03 con paso 0.01 y mínimo 0.01; R3-29 volumen que no permite parcial → omisión informada; R3-30 etiqueta de estimación y denominador en el evento; R3-31 caracterización: BE y parcial con las mismas solicitudes que la línea base cuando el volumen es compatible.
- **Aceptación:** R3-28 a R3-31 pasan. **Reversión:** revertir. **Evidencia:** diff, resultados.

### P3-09 — Compuertas de datos documentadas
- **Hallazgos:** F-07. **Estado:** BLOCKED POLICY (D-14) y NEEDS EVIDENCE (semántica horaria de `tick.time`; helper `%TEMP%\kilo\frival_read.py` no versionado).
- **Comportamiento actual:** el ATR del ejecutor usa `copy_rates_from_pos(…, 0, …)` con la barra en formación incluida (`L233-L243`); no hay compuertas de tick, spread/ATR, rollover ni M15/ATR en el ejecutor; el ATR "limpio" existe solo en `counterfactual.py:L119-L124` y en el helper.
- **Resultado requerido (condicional):** medición en sombra de cada compuerta; imposición solo con umbrales y unidades por símbolo aprobados.
- **Pruebas previstas:** R3-32 barra en formación excluida del ATR; R3-33 tick antiguo/sin hora válida → DESCONOCIDO; R3-34 unidades por símbolo.
- **Aceptación:** pendiente de D-14.

### 8.10 Resumen P3 y estado de la Entrega B
| Ticket | Estado | Depende de | Decisión |
|---|---|---|---|
| P3-01 Margen en sombra | READY FOR AUTHORIZATION | P0-01, P2-02 | — |
| P3-02 Criterio de margen | BLOCKED POLICY / NEEDS EVIDENCE | P3-01, P2-02 | D-11 |
| P3-03 Riesgo a precio ejecutable | BLOCKED POLICY | P2-02 | D-12 |
| P3-04 Sin valores por defecto silenciosos | READY FOR AUTHORIZATION | P0-01 | — |
| P3-05 Reloj único | BLOCKED POLICY / NEEDS EVIDENCE | — | D-07 |
| P3-06 Sesión, PnL diario, breaker | BLOCKED POLICY | P1-02, P3-05 | D-07, D-08 |
| P3-07 PnL neto (componentes) | READY FOR AUTHORIZATION (parte) / BLOCKED POLICY (uso del neto) | P1-01 | D-13 |
| P3-08 Parcial y métricas | READY FOR AUTHORIZATION | P2-03 | — |
| P3-09 Compuertas de datos | BLOCKED POLICY / NEEDS EVIDENCE | — | D-14 |

Sin ciclos de dependencia en P2/P3 (orden: P0-01 → P1-01 → P1-02 → P2-01 → P2-02 → P2-03/P2-04 → P3-01/P3-08; P3-04 depende solo de P0-01; las dependencias de P3-02, P3-05 y P3-06 fluyen hacia adelante).

**Lote candidato ampliado listo para autorización (sin cambios de política):** P0-01, P0-02, P1-01, P1-02, P1-03, P2-01, P2-02, P2-03, P2-04, P3-01, P3-04, P3-07 (parte de cálculo), P3-08. Se recomienda autorizar por tandas pequeñas en el orden de dependencias.

Cobertura acumulada de hallazgos: F-01 (P2-04, P2-05), F-02 (P2-06), F-03 (P3-01, P3-02), F-04 (P2-01, P2-02), F-05 (P1-01, P1-02), F-06 (P1-03, P1-04), F-07 (P3-09), F-08 (P2-07), F-09 y F-23 (P3-06), F-11 (P0-03), F-12 (P0-01, P0-02), F-14 (P3-07), F-15 (P3-03), F-16 (P3-04), F-17 (P3-05), F-18 (P3-08, P2-03), F-19 (P2-08), F-20 (P2-01, P2-02), F-22 (P0-01). **Pendiente para la Entrega C:** F-10, F-13 (histórico), F-21, F-24, F-25, F-26, F-27, F-28 (parte histórica), tickets P4, procedimiento de traspaso, verificación de consistencia y checklist final.

**Estado del documento tras la Entrega B:** ESPECIFICACIÓN PARCIAL. IMPLEMENTACIÓN NO AUTORIZADA. DESPLIEGUE NO AUTORIZADO.

<!-- FIN-ENTREGA-B -->

---

## Sección 9. Entrega C — tickets P4 (reconciliación histórica y medición contrafactual)

**Estado durante la Entrega C:** cerrada en la Sección 14. IMPLEMENTACIÓN NO AUTORIZADA.

### 9.0 Corrección a un enunciado del informe v2 (el v2 no se modifica)
En `2026-10-11_frival_audit_v2.md`, F-27 afirma que no se pudo reconciliar la cifra de `OPERATIONS.md` (22 cerradas, +$124.9, +3.92R; L269-L270). Un recuento manual de las filas `CLOSED` con PnL hasta T040 (que es el conjunto de 40 filas que cita ese párrafo) sí reproduce 22 cerradas, 9 ganadoras, +124.93 y +3.92R. La cifra era coherente **a esa fecha** y está desactualizada desde T041 (el ledger tiene hoy 44 filas). Se trata de una comprobación manual, no de un cálculo ejecutado. F-27 queda reclasificado: *cifras de `OPERATIONS.md` con fecha de corte no declarada* (P4-07), no "no reconciliables".

### 9.1 Huecos de fuente cerrados para P4
| Tema | Hallazgo verificado | Referencia |
|---|---|---|
| Resolución contrafactual | Ventana de 30 barras tras la barra de señal; sin modelo de fill; MFE/MAE sobre toda la ventana; `would_be_r_usd` vacío en EXPIRED; `RESOLVE_GRACE_BARS` definido y sin usar | `counterfactual.py:L48-L49, L158-L226` |
| Alta de contrafactuales | `rr_tp1` con valor absoluto; sin validación de geometría (lado de SL/TP respecto a la entrada) ni de ID duplicado | `counterfactual.py:L105-L155` |
| Filas hechas a mano | C022 y C023 con `rr_tp1` negativo y ATR vacío; C023 con `logged_at_local` posterior a `logged_at_server`, resultado TP_ONLY y `would_be_r_usd` −2.273; C002 con geometría invertida (BUY, SL 158.092 sobre la entrada 158.03, TP 157.9) | `counterfactuals.csv` líneas 3, 23, 24 |
| Entrada nunca tocada | C004, C017, C037 y C040 (SELL LIMIT) con `mae` negativo y resultado TP_ONLY; C040: entrada 4163.0, `mae` −0.36, `signal_close` 4157.24, `spread_at_signal` 24.0, nota "last COMPLETED H1 (02:00) bullish" | `counterfactuals.csv` líneas 5, 41 (y filas C017, C037 no re-impresas aquí) |
| `reconcile_deals` | Agrupa por (símbolo, comentario); asocia salidas `[sl]`/`[tp]` al grupo del mismo símbolo con la entrada previa más cercana, sin `position_id`; empareja con prefijo en ambos sentidos; PnL = profit de salidas + swap de todos los deals (sin comisión ni fee); R usa `trade_contract_size` | `reconcile_deals.py:L107-L155, L163-L238` |
| Documentos | Brief: L14 (lee SETUP y DAILY_ROUTINE), L23 (rollover 23:00-00:30), L46 (1 posición neta, pendientes como exposición), L85 (racha 999), L89-L90 (BE "al cierre, no a la mecha"), L27/L30 (ATR limpio, unidades de oro). `OPERATIONS.md`: L25 (estado plano 0/0), L43 (`DAILY_ROUTINE.md` no es este desk), L72 (corrección del rollover), L155 (3 posiciones), L162 (racha 4), L305 (BE intrabarra), L269-L270 (cifras). `SETUP_NEW_MACHINE.md`: L18 (Python 3.9.21), L130-L133 (compuerta 8/8), L159 (999) | Archivos citados |
| Pendiente de lectura | Filas C017 y C037; artefactos `context/*`; `eod_review.py` más allá de L70-L109 | — |

### P4-01 — Línea base inmutable de artefactos y manifiesto de procedencia
- **Hallazgos:** F-13, F-26, F-27 (base de todo P4). **Severidad:** Media. **Estado:** READY FOR AUTHORIZATION (no requiere código; depende solo de autorización para crear archivos nuevos).
- **Comportamiento actual:** el ledger, el audit, los contrafactuales, el estado, las reviews y el contexto son archivos mutables modificados por el desk; no hay manifiesto de hashes; los helpers `%TEMP%\kilo\*.py` están fuera del repositorio.
- **Resultado requerido:** copia de solo lectura de los artefactos con un manifiesto (ruta, tamaño, hash, instante de copia, hash del commit `7f9df8e8428e239a85136b7b2a3568f40301617b`, indicación de si el árbol tenía cambios sin confirmar si el operador puede verificarlo) y registro de procedencia de los helpers temporales.
- **Dentro del alcance:** copias, manifiesto, procedimiento de verificación de integridad posterior.
- **Fuera del alcance:** modificar los originales; interpretar o corregir contenido.
- **Pasos:** el operador detiene o pausa el desk durante la copia (decisión suya); copiar; calcular hashes; verificar; marcar solo lectura; registrar.
- **Pruebas/aceptación:** (1) cada archivo del inventario tiene entrada de manifiesto; (2) la verificación recalcula los hashes y coinciden; (3) un archivo modificado deliberadamente en una copia de ensayo hace fallar la verificación; (4) los originales conservan su hash tras la copia.
- **Fallo/desconocido:** una copia con hash discordante invalida el lote y se repite. **Reversión:** borrar las copias. **Evidencia:** manifiesto, salida de verificación.

### P4-02 — Exportación de evidencia del broker (órdenes, deals, posiciones)
- **Hallazgos:** F-13, F-14. **Estado:** NEEDS EVIDENCE (depende de P4-01 y de datos que solo el operador o una lectura de broker explícitamente autorizada puede aportar).
- **Resultado requerido:** conjunto de datos del broker, de solo lectura, con tickets de orden, tickets de deal, `position_id`, tipo/entrada de deal, `profit`, `commission`, `swap`, `fee`, comentario, hora y volumen, que cubra todo el periodo del ledger (más amplio que las ventanas de 14/30 días del código).
- **Fuera del alcance:** acceder a la cuenta sin autorización escrita; ejecutar `reconcile_deals.py apply`.
- **Aceptación:** el conjunto de datos tiene hash y procedencia; cubre desde la primera fila del ledger; incluye todos los campos listados; el operador confirma su origen.

### P4-03 — Migración trazable de correcciones del ledger
- **Hallazgos:** F-13, F-26. **Estado:** BLOCKED POLICY (D-05) y NEEDS EVIDENCE (P4-02).
- **Resultado requerido (condicional):** una tabla de correcciones **separada** del ledger original, con: fila afectada, campo, valor original, valor propuesto, motivo, referencia al deal/orden/posición del broker, estado de verificación. El ledger original no se edita; cualquier ledger "corregido" es una proyección regenerable. **Prohibido** corregir filas solo a partir de registros de envío del audit.
- **Casos conocidos (candidatos, no correcciones):** T010 y T014 (`CLOSED_UNFILLED` con "no broker execution existed" frente a envíos aceptados en el audit y a PnL citado en `continua-operando.md`); T040 (`volume` = remanente, `risk_usd` implica volumen original, `trade_log.csv` línea 41); T042/T043 (`exit_price` frente a PnL de broker); filas reconstruidas T019/T020; marcas de tiempo con relojes mezclados.
- **Pruebas previstas (fixtures):** R4-1 una corrección sin referencia de broker se rechaza; R4-2 aplicar y revertir la proyección reproduce el original; R4-3 un deal con `position_id` ambiguo queda `OWNERSHIP_UNKNOWN` y no se corrige.
- **Aceptación:** pendiente de D-05 y de P4-02; mínimo R4-1 a R4-3.

### P4-04 — Resolución contrafactual con modelo de fill (salida nueva y separada)
- **Hallazgos:** F-10, F-26. **Severidad:** Alta. **Estado:** READY FOR AUTHORIZATION (depende de P0-01 y P1-01). La serie de precios (Bid o Ask/Last) **no está confirmada** (`SYMBOL_CHART_MODE`): el ticket registra el supuesto y marca las filas afectadas.
- **Comportamiento actual:** ver 9.1.
- **Resultado requerido:** un resolvedor que, sin sobrescribir `outcome`/`would_be_r_usd` históricos, escribe columnas **nuevas**: tipo de activación, índice de la barra de activación, estado de fill (`FILLED`, `NOT_FILLED`, `FILL_AMBIGUOUS`), MFE/MAE medidos desde la barra de activación, estado de salida (`TP_FIRST`, `SL_FIRST`, `EXIT_AMBIGUOUS`, `OPEN_AT_HORIZON`, `NO_FILL`) y R solo para fills con salida resuelta. Reglas de activación (supuesto de barras Bid y spread declarado): SELL LIMIT `max(high) ≥ entry`; BUY LIMIT `min(low) ≤ entry − spread`; SELL STOP `min(low) ≤ entry`; BUY STOP `max(high) ≥ entry − spread`; MARKET inmediato. Una barra con activación y salida, o con SL y TP, se marca ambigua.
- **Dentro del alcance:** validación de geometría y signo en `consider` (lado de SL y TP respecto a la entrada, `rr_tp1` ≥ 0, ID único); métricas con denominadores explícitos (tasa de fill, expectativa condicional al fill, resultado por setup considerado, tasa de no activación); uso del `RESOLVE_GRACE_BARS` o su eliminación documentada.
- **Fuera del alcance:** recalcular o reescribir las 40 filas históricas (P4-05); cambiar el horizonte; asignar R a EXPIRED; cambiar reglas de trading.
- **Pasos:** pruebas con series sintéticas de barras; resolvedor nuevo; validación en `consider`; revisión.
- **Pruebas y fixtures (barras sintéticas):** R4-4 SELL LIMIT cuyo máximo queda por debajo de la entrada → `NOT_FILLED`, sin R; R4-5 SELL LIMIT con toque de 0.01 por encima → `FILLED`; R4-6 BUY LIMIT con `low` entre `entry − spread` y `entry` → no activado bajo el supuesto Bid; R4-7 barra con activación y TP → `FILL_AMBIGUOUS`; R4-8 barra con SL y TP tras fill → `EXIT_AMBIGUOUS`; R4-9 BUY con SL sobre la entrada (geometría de C002) → rechazo en `consider`; R4-10 `rr_tp1` negativo → rechazo; R4-11 ID duplicado → rechazo; R4-12 fill sin salida en el horizonte → `OPEN_AT_HORIZON`, sin R; R4-13 gap sobre el SL → estado marcado, sin asumir −1.000 exacto (parámetro de deslizamiento declarado).
- **Aceptación:** R4-4 a R4-13 pasan; las columnas históricas permanecen idénticas (hash por columna); cada métrica de salida declara su denominador.
- **Fallo/desconocido:** serie de barras incompleta → `UNKNOWN` sin R. **Compatibilidad:** columnas nuevas (P1-01). **Reversión:** revertir. **Evidencia:** diff, resultados reales, tabla de supuestos.

<!-- FIN-ENTREGA-C-PARTE-1 -->

### P4-05 — Reevaluación offline de la evidencia contrafactual y del filtro de momentum
- **Hallazgos:** F-10, F-25, F-26. **Estado:** NEEDS EVIDENCE (depende de P4-04 y de series históricas de barras M5 que debe aportar una exportación autorizada; no se asume acceso a MT5).
- **Resultado requerido:** informe offline reproducible que recalcula las estadísticas contrafactuales con el modelo de fill de P4-04: tasa de fill, expectativa condicional al fill, resultado por setup considerado, tasa de no activación y de `EXPIRED` separados; sensibilidad a spread, deslizamiento y horizonte; tratamiento explícito de filas inválidas (C002, C022, C023) y de filas sin fill (C004, C017, C037, C040); comparación del filtro `mom_alignment` solo con muestras comparables.
- **Fuera del alcance:** decidir la política de momentum; operar en vivo para generar muestras; modificar `OPERATIONS.md`/`AGENTS.md`. La política de momentum (F-25) queda como **hipótesis de investigación**: la observación futura se hace en sombra, en simulación o en demo aislada autorizada, nunca con operaciones reales para generar datos. No se asume que 20–30 observaciones establezcan una ventaja.
- **Aceptación:** el informe declara fuente de datos, reglas de inclusión, numerador y denominador de cada métrica, tratamiento de costos y de deslizamiento; reproduce el recuento 4/12 de filas TP sin toque de entrada como control; no incluye t-estadísticos ni intervalos sin una base de cálculo declarada y reproducible. **Reversión:** n/a (solo lectura). **Evidencia:** informe, datos de entrada con hash.

### P4-06 — Herramienta de reconciliación `reconcile_deals`
- **Hallazgos:** F-13, F-14, F-28. **Estado:** BLOCKED POLICY (D-05, D-13).
- **Comportamiento actual:** emparejado con prefijo en ambos sentidos y por (símbolo, comentario) (`L163-L176`); salidas `[sl]`/`[tp]` atadas por símbolo y cercanía temporal, sin `position_id` (`L129-L145`); PnL sin comisión ni fee (`L216-L218`); R con `trade_contract_size` (`L236-L238`); `apply` escribe el ledger y marca filas sin salida como `OPEN` (`L259-L285`).
- **Resultado requerido (condicional):** emparejado por `position_id`/ticket con clasificación de propiedad; componentes de costo separados; `apply` fuera de uso (cuarentena) hasta que exista la proyección de P4-03; R con definición aprobada.
- **Pruebas previstas:** R4-14 dos posiciones del mismo símbolo con salidas por SL; R4-15 parciales y cierre final; R4-16 comentario sobrescrito por el broker; R4-17 sin deals → sin escritura.
- **Aceptación:** pendiente de D-05 y D-13.

### P4-07 — Etiquetado factual de documentos (fecha de corte y estado histórico)
- **Hallazgos:** F-21, F-27. **Severidad:** Media. **Estado:** READY FOR AUTHORIZATION (solo adiciones de etiqueta; no cambia ninguna regla).
- **Comportamiento actual:** cifras de `OPERATIONS.md` L269-L270 sin fecha de corte; `SETUP_NEW_MACHINE.md` L159 afirma racha 999 y L130-L133 presenta `test_kill_switch.py` como compuerta; el brief L14 manda leer `DAILY_ROUTINE.md`, que `OPERATIONS.md` L43 declara ajeno a este desk.
- **Resultado requerido:** cada afirmación obsoleta o histórica lleva una nota explícita con fecha y fuente ("histórico; ver `OPERATIONS.md` §…"), sin modificar valores de política.
- **Fuera del alcance:** decidir cuál valor rige (P4-08); editar cualquier constante.
- **Pruebas/aceptación:** lista de verificación con cada línea citada y su etiqueta; una segunda lectura independiente confirma que ninguna regla cambió de valor (comparación línea a línea del diff: solo adiciones de nota). **Reversión:** revertir. **Nota:** estos documentos son instrucciones del agente: se requiere autorización explícita para editarlos.

### P4-08 — Alineación de reglas en documentos y comentarios
- **Hallazgos:** F-21. **Estado:** BLOCKED POLICY (D-01, D-03, D-04, D-07, D-08, D-09 según el punto).
- **Conflictos a resolver por decisión (valores sin elegir aquí):** posiciones máximas y tratamiento de pendientes (brief L46 frente a `OPERATIONS.md` L155 y `L57` del código); racha (brief L85 y SETUP L159 frente a `OPERATIONS.md` L162 y `L121`); ventana de rollover (brief L23 frente a `OPERATIONS.md` L72/L348); BE al cierre o intrabarra (brief L89-L90 frente a `OPERATIONS.md` L305); unidades de las reglas de ATR limpio del brief (L27, L30, expresadas en unidades de oro); umbral `MIN_RR` mostrado por `log_trade.py` (2.0) frente al del ejecutor (1.9).
- **Aceptación:** un documento maestro declarado por el operador, conflicto por conflicto, con el valor y la fuente; ninguna regla queda con dos valores.

### P4-09 — Higiene de código y comentarios sin efecto de política
- **Hallazgos:** F-24. **Severidad:** Baja. **Estado:** READY FOR AUTHORIZATION (depende de P0-01 y de que P4-08 no cambie los mismos pasajes).
- **Comportamiento actual:** `extreme_stop_spacing_ok` definida sin llamadas (`order_executor.py:L83-L102`); `--force` aceptado en `place` (`L851`) y mencionado en el mensaje de bloqueo (`L419`) y en el docstring (`L14`) sin efecto, ya que `a.force` solo se lee en `close-all` (`L766`); docstring que promete `ORDER_FAILED` y registro previo al envío (`L16-L18`) frente a `L504`; `be_trigger_price` del ledger con signo contrario al de `be_trigger` del ejecutor (`log_trade.py:L427` frente a `order_executor.py:L397`); `RESOLVE_GRACE_BARS` sin uso (`counterfactual.py:L49`).
- **Resultado requerido:** los comentarios y docstrings describen el comportamiento real; el signo de `be_trigger_price` en filas nuevas es coherente con el del ejecutor (solo filas nuevas; sin migrar históricas); ninguna conexión nueva de compuertas inactivas (`extreme_stop_spacing_ok` se documenta como inactiva; cablearla es política y queda excluida).
- **Pruebas:** R4-18 `be_trigger_price` de una fila BUY y una SELL frente al valor de `be_trigger`; R4-19 caracterización: `place --force` mantiene su comportamiento actual (ignorado) y su mensaje describe esa realidad.
- **Aceptación:** R4-18 y R4-19 pasan; diff sin cambios de lógica fuera de `be_trigger_price`. **Reversión:** revertir.

### 9.2 Resumen P4
| Ticket | Estado | Depende de | Decisión |
|---|---|---|---|
| P4-01 Línea base inmutable | READY FOR AUTHORIZATION | — | — |
| P4-02 Exportación de evidencia del broker | NEEDS EVIDENCE | P4-01 | autorización de acceso de lectura |
| P4-03 Migración trazable | BLOCKED POLICY / NEEDS EVIDENCE | P4-01, P4-02, P1-01 | D-05 |
| P4-04 Resolución contrafactual con fill | READY FOR AUTHORIZATION | P0-01, P1-01 | — |
| P4-05 Reevaluación offline | NEEDS EVIDENCE | P4-04, P4-02 (barras) | — |
| P4-06 `reconcile_deals` | BLOCKED POLICY | P1-01 | D-05, D-13 |
| P4-07 Etiquetado factual de docs | READY FOR AUTHORIZATION | P4-01 | — |
| P4-08 Alineación de reglas | BLOCKED POLICY | — | D-01, D-03, D-04, D-07, D-08, D-09 |
| P4-09 Higiene de código | READY FOR AUTHORIZATION | P0-01 | — |

<!-- FIN-ENTREGA-C-PARTE-2 -->

---

## Sección 10. Procedimiento de traspaso para el agente implementador

Este procedimiento es obligatorio. Ningún paso autoriza, por sí mismo, tocar la cuenta live ni cambiar política.

1. **Leer** `OPERATIONS.md`, `ACTIVE MONITOR — Frival desk.md`, `AGENTS.md`, el informe `auditorias/2026-10-11_frival_audit_v2.md` y este plan completo. Los conflictos entre documentos están en el ticket P4-08; no se resuelven por cuenta propia.
2. **Comprobar deriva de fuente** frente a la línea base: commit `7f9df8e8428e239a85136b7b2a3568f40301617b` en `main` y las referencias de línea citadas en el ticket. El plan no pudo comprobar cambios sin confirmar en el árbol de trabajo; si hay discrepancia (líneas movidas, funciones distintas), detener **ese ticket**, releer las funciones completas y pedir revalidación antes de seguir.
3. **Obtener autorización explícita** del operador para un ticket o un lote acotado, citando los IDs exactos. No se infiere autorización de instrucciones anteriores de mejora autónoma ni de este documento. Los parámetros de ingeniería (tiempos máximos de espera de lock, número de reintentos, máximo de intentos de verificación, ubicación de pruebas) se acuerdan en esta autorización.
4. **Preparar un entorno aislado:** una rama o copia de trabajo y datos desechables (P0-01). Antes de cualquier ejecución, comprobar que ninguna ruta de producción (ledger, estado, audit, kill switch, `config/.env`) es alcanzable por las pruebas.
5. **Inspeccionar importaciones y efectos laterales** de cada módulo que vaya a importarse o ejecutarse (por ejemplo, el ejecutor lee `config/.env` y `executor_state.json` al importar; `status` escribe el estado). No ejecutar nada antes de completar esta inspección.
6. **Añadir primero las pruebas de regresión** especificadas en el ticket y comprobar que fallan por el motivo descrito (o que caracterizan el comportamiento actual cuando el ticket lo pide).
7. **Implementar la corrección mínima dentro del alcance.** Sin refactorizaciones, sin cambios de umbrales, sin ajustes de estrategia, sin reinicios automáticos de breakers, sin adaptar a otro mandato.
8. **Ejecutar solo las pruebas offline autorizadas.** Nada contra MT5 real, ni siquiera de lectura, ni contra la cuenta live. La integración en demo y el despliegue live requieren autorizaciones separadas y por escrito.
9. **Informar:** diff, resultados reales de las pruebas, pruebas no ejecutadas y motivo, riesgos residuales, manifiesto de hashes de producción antes y después (cuando el ticket lo exige) y referencias exactas modificadas.
10. **Detenerse** para revisión independiente. No encadenar al siguiente ticket sin nueva autorización.

**Reglas adicionales:**
- Cambiar política o estrategia no relacionada invalida el alcance aprobado y exige nueva aprobación.
- Si falta una fuente o una decisión requerida por un ticket, detener solo ese ticket y continuar con el trabajo READY no relacionado.
- Los tickets BLOCKED POLICY no se implementan "con una propuesta por defecto".
- Ningún ticket mantiene un lock durante una llamada al broker; "aceptado" no significa "llenado"; "plano" requiere verificación de estado final; un estado de broker desconocido no es cierre ni ausencia de exposición; un PnL ausente no es cero.
- Ningún ticket modifica ni migra datos históricos salvo P4-03, y solo mediante la tabla de correcciones trazable.

<!-- FIN-ENTREGA-C-PARTE-3 -->

---

## Sección 11. Mapa de cobertura de hallazgos

Cada hallazgo retenido del informe v2 (F-01 a F-28) queda asignado a un ticket, a un elemento diferido o a una exclusión documentada.

| Hallazgo | Ticket(s) | Notas / exclusiones |
|---|---|---|
| F-01 | P2-04, P2-05 (con P2-02) | Alcance de emergencia y pendientes bloqueados por D-04/D-05 |
| F-02 | P2-06 | Bloqueado por D-03 |
| F-03 | P3-01, P3-02 | Gating bloqueado por D-11 |
| F-04 | P2-01, P2-02 | Idempotencia a nivel de aplicación |
| F-05 | P1-01, P1-02 | |
| F-06 | P1-03, P1-04 | Emparejado bloqueado por D-05 |
| F-07 | P3-09 | Bloqueado por D-14 y evidencia horaria |
| F-08 | P2-07 | Bloqueado por D-06 |
| F-09 | P3-06, P3-05 | Bloqueado por D-07/D-08 |
| F-10 | P4-04, P4-05 | |
| F-11 | P0-03 | Bloqueado por D-10 |
| F-12 | P0-01, P0-02 | |
| F-13 | P4-01, P4-02, P4-03 | Corrección histórica bloqueada por D-05 y evidencia de broker |
| F-14 | P3-07, P4-06 | Uso del neto bloqueado por D-13 |
| F-15 | P3-03 | Bloqueado por D-12 |
| F-16 | P3-04 | |
| F-17 | P3-05 | Bloqueado por D-07 y evidencia |
| F-18 | P2-03, P3-08 | Parámetros de BE/parcial excluidos (estrategia) |
| F-19 | P2-08 | Bloqueado por D-09 y evidencia |
| F-20 | P2-01, P2-02 | |
| F-21 | P4-07, P4-08 | Alineación bloqueada por decisiones |
| F-22 | P0-01, P0-02 | **Exclusión:** pruebas unitarias adicionales de `eod_review.py`, `market_context.py` y del resto de comandos de `log_trade.py` no se especifican en este plan; se añaden al abrir cada ticket correspondiente |
| F-23 | P3-06 | Atribución diaria de `eod_review` |
| F-24 | P4-09 | **Exclusión:** cablear `extreme_stop_spacing_ok` o retirar `--force` son decisiones de política/interfaz, no corrección de defecto |
| F-25 | P4-05 | **Diferido:** es una hipótesis de investigación; la política de momentum no se toca |
| F-26 | P4-03, P4-04 | |
| F-27 | P4-07 (corrección en 9.0) | |
| F-28 | P3-07, P4-02 | |

**Hallazgos surgidos durante la especificación (ya cubiertos):** filas `PENDING_FILL` obsoletas enviables (P2-01); `status` escribe el estado (P0-01, R0-4); guardia `OPERATOR_MANUAL` inactiva (P1-04); `KeyError` en `guardrail_report` (P2-02); `log_trade._save` descarta columnas (P1-01); `positions_get() or []` (P1-03, P2-02, P2-04).

## Sección 12. Comprobación de dependencias y de política

**Aristas:** P0-02←P0-01 · P1-01←P0-01 · P1-02←P0-01, P1-01 · P1-03←P0-01, P1-02 · P1-04←P1-02, D-05 · P2-01←P1-01, P1-02 · P2-02←P2-01, P1-02 · P2-03←P1-02, P2-02 · P2-04←P0-01, P2-02 · P2-05←P2-04, P1-04, P2-02 · P2-06/07/08←P2-02 · P3-01←P0-01, P2-02 · P3-02←P3-01, P2-02 · P3-03←P2-02 · P3-04←P0-01 · P3-06←P1-02, P3-05 · P3-07←P1-01 · P3-08←P2-03 · P4-02←P4-01 · P4-03←P4-01, P4-02, P1-01 · P4-04←P0-01, P1-01 · P4-05←P4-04, P4-02 · P4-06←P1-01 · P4-07←P4-01 · P4-09←P0-01.
**Resultado:** el grafo no contiene ciclos (todas las aristas van de un ticket a otro de numeración o paquete anterior, o hacia una decisión). Orden topológico válido: P4-01, P0-01, P0-02, P1-01, P1-02, P1-03, P2-01, P2-02, P2-03, P2-04, P3-01, P3-04, P3-07 (parte), P3-08, P4-04, P4-07, P4-09; después los tickets bloqueados cuando se resuelvan sus decisiones.

**Política:** ningún ticket READY depende de una propuesta de política no aprobada. Casos revisados: P2-01 (la regla para filas `PENDING_FILL` obsoletas queda documentada como riesgo residual hasta que el operador defina un estado explícito); P2-02 (la tabla retcode→categoría la aprueba el operador al autorizar); P3-01 (solo medición); P3-07 (columnas paralelas; sin cambiar `pnl_usd`, breakers ni R); P3-08 (el operador elige la definición de `realised_r` al autorizar); P4-07 (solo etiquetas). Los parámetros de ingeniería se acuerdan en la autorización de cada lote (Sección 10, paso 3).

## Sección 13. Lote inicial mínimo y lista de aprobación del operador

**Lote 1 mínimo, listo para autorización:** **P0-01** (entorno offline aislado). Acompañante recomendado, sin código: **P4-01** (línea base inmutable de artefactos). **Lote 2:** P0-02 y P1-01. **Lote 3:** P1-02 y P1-03. **Lote 4:** P2-01 y P2-02. Después, según dependencias: P2-03, P2-04, P3-01, P3-04, P3-07 (parte), P3-08, P4-04, P4-07, P4-09.

**Lista compacta de aprobación (para el Lote 1):**
1. Autorizar por escrito los IDs exactos del lote (P0-01, y P4-01 si se desea) y nada más.
2. Confirmar que el mandato vigente es Frival (D-01).
3. Confirmar el marco de pruebas y la ubicación de los archivos nuevos (el repo usa estilo `unittest` en `dashboard/tests/test_portfolio.py`).
4. Autorizar la creación de archivos nuevos y de una rama o copia de trabajo aislada; confirmar que no se tocará ningún archivo existente.
5. Para P4-01: decidir si se pausa el desk durante la copia y quién verifica si el árbol tiene cambios sin confirmar.

**Decisiones que no son necesarias para el Lote 1** (se piden cuando se autorice el ticket que las usa): D-10 (P0-03), D-05 (P1-04, P2-05, P4-03, P4-06), D-02, D-03, D-04, D-06, D-07, D-08, D-09, D-11, D-12, D-13, D-14.

**Hallazgos que no bloquean el Lote 1:** todos salvo F-12 y F-22 (P0-01). F-13, F-26 y F-27 solo dependen de P4-01 como base y no bloquean P0-01.

## Sección 14. Estado final de tickets y del documento

| Escala de estado | Tickets |
|---|---|
| Especificación completa | 33 tickets especificados (17 listos; 16 con criterios condicionales a decisión o evidencia, sin inventar política) |
| Ticket listo para autorización del operador | 17: P0-01, P0-02, P1-01, P1-02, P1-03, P2-01, P2-02, P2-03, P2-04, P3-01, P3-04, P3-07 (parte), P3-08, P4-01, P4-04, P4-07, P4-09 |
| Ticket bloqueado por política (total o parcialmente) | 14: P0-03, P1-04, P2-05, P2-06, P2-07, P2-08, P3-02, P3-03, P3-05, P3-06, P3-09, P4-03, P4-06, P4-08 (y P3-07 en su parte de uso del neto) |
| Ticket que necesita evidencia (principal) | 2: P4-02, P4-05 (más evidencia adicional en P2-08, P3-02, P3-05, P3-09, P4-03) |
| Implementación autorizada | **0** |
| Implementado y validado | **0** |
| Despliegue autorizado | **0** |

**Estado del documento: SPECIFICATION COMPLETE — IMPLEMENTATION NOT AUTHORIZED.**
Cualificación: la especificación es completa en el sentido de que cada hallazgo retenido tiene ticket, aplazamiento o exclusión documentada, y de que no se inventó política ni criterios. Los tickets bloqueados no pueden implementarse hasta que el operador resuelva las decisiones D-xx indicadas o se aporte la evidencia señalada.

**Confirmaciones:** durante la elaboración de este plan no se ejecutó ningún script ni prueba, no se usó terminal, no se conectó a MT5, no se realizó ninguna acción de trading y no se modificó código fuente, configuración ni datos de producción. La única escritura fue este documento (más la creación previa de los dos informes de auditoría). La línea base `7f9df8e8428e239a85136b7b2a3568f40301617b` es la de `refs/heads/main`; no se pudo verificar si el árbol de trabajo tiene cambios sin confirmar.

<!-- FIN-ENTREGA-C -->
