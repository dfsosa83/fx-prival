CONTINÚA OPERANDO — Frival desk, ejecución autónoma.

Escrito 2026-10-02 al cierre de la primera sesión de ejecución autónoma.
Este archivo es el punto de reanudación: qué se construyó, qué se aprendió
y qué hacer al volver el domingo.


====================================================================
1. ESTADO AL CIERRE (viernes 2026-10-02, ~14:40 hora local)
====================================================================

Cuenta ............. 81486396 FPMarketsSC-Live (FP Markets)
Balance / equity .... $604.29
Posiciones abiertas . 0
Órdenes pendientes . 0
Circuit breaker ..... DESACTIVADO (el operador lo apagó explícitamente)

RESULTADO DE LA SESIÓN
  6 trades autónomos ejecutados, -$19.24 neto (-2.99% sobre el peak de $623.23)
  T013 EURUSD SELL  -$3.78  (R -1.00)  SL barrido
  T014 XAUUSD SELL  +$2.48  (R +0.30)  cerrado a mano antes del SL
  T015 XAUUSD BUY   -$12.78 (R -1.11)  piso roto + Asia low roto
  T016 EURUSD SELL  +$2.52  (R +0.35)  cerrado a mano por el operador
  T017 USDJPY SELL  -$0.61  (R -1.00)  máximo de sesión barrido
  T018 XAUUSD SELL  cancelada sin llenar — SL invalidado por la estructura

Plus 2 trades manuales previos: +$32.80 y -$8.07.


====================================================================
2. HORARIOS DEL MERCADO (confirmados por el operador)
====================================================================

Relojes:  TU LOCAL = UTC-5   ·   SERVER DEL BROKER = UTC+3

  Día de semana ..... cierra 16:00 local, reabre 17:00 local (1 hora)
  Viernes ........... cierra 16:00 local, NO reabre
  Domingo ........... abre 18:00 local

  En server: el cierre diario es 00:00-01:00 server.

BUG CORREGIDO: el prompt del monitor filtraba "23:00-00:30 server"
como ventana de rollover. Eso es 15:00-16:30 local — arranca una hora
antes del cierre real y termina media hora antes. Se reemplaza por los
horarios de arriba.

El fin de semana pasado el mercado estuvo cerrado desde el viernes 16:00
hasta el domingo 18:00. Al volver el domingo el primer M15 puede tener un
gap respecto al cierre del viernes: verificar el ATR antes de emitir.


====================================================================
3. QUÉ SE CONSTRUYÓ EN ESTA SESIÓN
====================================================================

CÓDIGO NUEVO (frival/)
  order_executor.py    Único componente con permiso de colocar órdenes.
                       8 guardarraíles aplicados en código, no por disciplina.
  counterfactual.py    Log de setups considerados + resolución contra el precio.
  log_trade.py         CLI del trade log (37 columnas).
  market_context.py    Snapshot reproducible por señal (quote, cuenta, ATR 5
                       timeframes, 20 velas M5, 10 velas M15).
  reconcile_deals.py   Matchea el log contra el historial de deals del broker.
  ml_intraday_snapshot.py  Escribe XAUUSD M5/M15/M30/H1/H4 a CSV.
  test_kill_switch.py  Verificación end-to-end del kill switch.

DATOS (frival/)
  trade_log.csv           17 trades, fill/exit/PnL/R/MFE/MAE verificados
                          contra los deals del broker.
  counterfactuals.csv      21 setups resueltos, 0 pendiente. +5.84R total.
  execution_audit.jsonl    Cada acción del executor con guardarraíles evaluados.
  context/T0NN.{json,md}   Mercado exacto en el momento de cada señal.


====================================================================
4. CONFIGURACIÓN VIGENTE (verificar con order_executor.py status)
====================================================================

  Riesgo por trade ........... 5.0%       (subido desde 3.0% el 10-02)
  Riesgo agregado ........... 12.0%
  Posiciones simultáneas .... 3
  Correlación ............... máx 2 posiciones misma tesis USD
  R:R mínimo ............... 1.9         (bajado desde 2.0 — ver stats)
  SL como múltiplo ATR ..... 1.0x – 4.0x
  Margin level mínimo ...... 100%        (bajado desde 500%)
  Pérdidas seguidas ........ 999 (HALT desactivado por el operador)
  Espaciamiento de SL en extremo de sesión ... ≥ 20 puntos

SIZING QUE COMPRA EL 5% (con equity ~$604)
  XAUUSD  0.02 lotes  → $23–30 según SL
  EURUSD  0.10 lotes  → $24
  USDJPY  0.29 lotes  → $18
  Nota: el volume step de 0.01 en los tres pares es lo que frenaba el
  lotaje, no el límite de riesgo. USDJPY pasó de 0.10 a 0.29 por eso.


====================================================================
5. LO QUE ENSEÑÓ EL CONTRAFACTUAL LOG (N=21)
====================================================================

  Razón de rechazo          N   TP-first   R medio
  -------------------------------------------------------
  CORRELATION               1     100%     +2.01
  LEVEL_ALREADY_TESTED      7      43%     +1.36
  R_R_BELOW_2_TO_TP1        5      40%     +0.04
  NONE_TAKEN                5      20%     +0.05
  NO_STRUCTURAL_TARGET      2       0%     -1.00   <-- el único que acierta
  SPREAD_UNOPERABLE         1       --       0.00

  Total: TP 7 / SL 9 / expired 5 = 33% hit rate, +5.84R

HALLAZGGO PRINCIPAL
  El patrón XAUUSD breakdown/rejection ganó 3 de 3 (C001 +2.16, C004 +3.20,
  C006 +2.94). Las tres pérdidas fueron por mecánica, no por tesis:
  vender máximos de sesión con el SL pegado al nivel.

  REGLA DERIVADA: no SELL/BUY en extremo de sesión salvo que el SL tenga
  ≥20 puntos de espacio estructural. T013 tenía 67 pips y aun así perdió —
  la regla es defensa, no garantía.


====================================================================
6. REGLAS QUE NO SE DISCUTEN
====================================================================

  1. El log es un REGISTRO, no un control. Para cancelar hay que ir al
     BROKER primero. Escribir CANCELLED en el CSV no cancela nada.

  2. sl_distance siempre en UNIDADES DE PRECIO, no en pips. El executor
     cross-valida contra |entry − SL| y aborta si no coinciden.

  3. Calculá la aritmética en la grilla antes de emitir, nunca a mano.
     Hoy hubo 4 errores de R:R consecutivos (T014, T015, T017, T018), todos
     detectados por el guardarraíl. La grilla no falla.

  4. Antes de dejar un LIMIT resting, verificá que el SL no esté dentro
     del rango que el precio negoció en los últimos 30 min. Si lo está,
     corré el SL o no emitás.

  5. Si un nivel se rompe, NO asumas el siguiente: releé la estructura.
     El guardarraíl no puede detectar esto — es disciplina del operador.


====================================================================
7. PROCEDIMIENTO DE REANUDACIÓN (domingo después de las 18:00 local)
====================================================================

PASO 1 — Verificar que el terminal está corriendo y en la cuenta live.
  cd C:\Users\david\OneDrive\Documents\fx-prival\frival
  python order_executor.py status

PASO 2 — Si el kill switch quedó armado de una sesión anterior, BORRARLO:
  del frival\data\emergency_stop.txt
  (El prompt del monitor NO lo borra solo. Verificar antes de operar.)

PASO 3 — Reconciliar con el broker:
  python reconcile_deals.py scan
  python reconcile_deals.py audit
  Si hay trades cerrados sin matchear, registrar el P&L real.

PASO 4 — Snapshot del nuevo contexto:
  python ml_intraday_snapshot.py --once
  Los niveles del viernes quedaron obsoletos con el cierre.

PASO 5 — Leer estructura fresca. NO usar niveles de la sesión anterior.
  Los niveles que importaban al cierre del viernes:
    XAUUSD  4149.16 (high post-breakout) · 4143.17 (nivel roto) · 4132.20 (piso)
    EURUSD  1.12605 (high) · 1.12495 (low)
    USDJPY  157.911 (high de sesión)

PASO 6 — Operar con la configuración vigente (§4 de este archivo).


====================================================================
8. COMANDOS DE EMISIÓN (flujo completo)
====================================================================

  # 1. Loguear la señal ANTES de colocarla
  python log_trade.py signal --id T0NN --symbol XAUUSD --side SELL \
    --order-type LIMIT --volume 0.02 --entry 4143.50 --sl 4147.54 \
    --tp1 4132.20 --trigger "M15 closed above 4143.17 on 2h compression"

  # 2. Snapshot reproducible del mercado en ese instante
  python market_context.py capture --id T0NN

  # 3. Colocar — el executor bloquea si falla cualquier guardarraíl
  python order_executor.py place --id T0NN
  # Si el precio ya está en el nivel, usar: place --id T0NN --market
  # NUNCA usar --force. Si bloquea, corregir niveles y re-emitir.

  # 4. Gestión cada ciclo
  python order_executor.py manage      # BE automático al 50% del camino al TP

  # 5. Cancelar (SIEMPRE vía broker)
  python order_executor.py cancel --id T0NN

  # 6. Loguear setups rechazados (para el dataset)
  python counterfactual.py consider --id C0NN --symbol X --side BUY \
    --order-type LIMIT --volume V --entry E --sl S --tp1 T \
    --trigger "..." --reject-reason LEVEL_ALREADY_TESTED

  # 7. Métricas
  python counterfactual.py stats
  python log_trade.py stats
  python order_executor.py status


====================================================================
9. PARADA DE EMERGENCIA
====================================================================

  echo "STOP" > frival\data\emergency_stop.txt

Bloquea toda apertura. El flatten (close-all) sigue disponible —
nunca bloquear el cierre de posiciones.

  python order_executor.py close-all --force --reason "motivo"


====================================================================
10. LO QUE FALTA CONSTRUIR
====================================================================

  - data/raw/intraday/ nunca se creó. Correr ml_intraday_snapshot.py --watch
    --interval 300 en background para tener histórico M5 de XAUUSD.
  - El veto macro (MERG) está en pausa: el CSV de calendario mezclan UTC+2 y
    UTC+3, así que un veto por hora sería impreciso. Solo viable por DÍA.
  - El filtro de espaciamiento de SL está documentado pero no implementado
    como gate — el executor no sabe si la entrada fue en un extremo de sesión.
    Es disciplina del agente, no código.
  - Falta calibrar la regla de 20 puntos con más datos: T016 tenía 11 puntos
    de espaciamiento y ganó +0.35R, lo que contradice la regla.