CONTINÚA OPERANDO — Frival desk, ejecución autónoma.

Contexto:
- Cuenta: 81486396 FPMarketsSC-Live (FP Markets), apalancamiento 1:500
- Leer datos con: C:\Users\david\anaconda3\python.exe
- Terminal: C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe
- Workdir para scripts: C:\Users\david\OneDrive\Documents\fx-prival\frival

PASO 1 — Verificar estado antes de operar:
  cd C:\Users\david\OneDrive\Documents\fx-prival\frival
  python order_executor.py status

PASO 2 — Revisar el ledger y qué quedó abierto:
  python log_trade.py stats
  python log_trade.py show
  python reconcile_deals.py audit
  python market_context.py audit

PASO 3 — Si hay posición abierta, actualizar el ledger con lo que hizo:
  python reconcile_deals.py apply

PASO 4 — Monitorear cada 15 minutos. Para cada par (XAUUSD, EURUSD, USDJPY):
  - Leer M5(15), M15(8), H1(6), tick, spread, EDAD DEL ÚLTIMO TICK, posiciones y órdenes
  - Registrar triple reloj: local UTC−5 / server UTC+3
  - Calcular ATR(M5) EXCLUYENDO velas congeladas (high==low o volumen < 30% de la mediana)
  - Decidir: TRADE / WAIT / OUT

PRE-CHECKS (si falla cualquiera → NO OPERAR ese par):
  - Ventana de rollover 23:00–00:30 server
  - Edad del último tick > 5 min → cotización muerta, el % de spread sobre ATR no significa nada
  - Spread como % del ATR limpio > 50%
  - ATR(M5) limpio < 1.0 → datos congelados

REGLAS (no negociables, fx-manual-trades.md §11–§13):
  - SL estructural, nunca pips arbitrarios
  - SL entre 1.0× y 4.0× ATR(M5) limpio
  - R:R ≥ 2.0 a TP1. Si solo TP2/TP3 llega, dilo explícitamente
  - Máximo 1 posición neta (las órdenes pendientes cuentan como exposición)
  - Riesgo máximo 5% del equity por trade
  - Multiplicador por símbolo: XAUUSD $100/unidad/lote, EURUSD $100,000, USDJPY $631.92

PASO 5 — COUNTERFACTUAL (obligatorio en cada revisión)
Un log que solo registra los trades tomados no puede demostrar que el filtro
tiene skill. Loguea CADA setup considerado, tomado o no:

  python counterfactual.py consider --id C0NN --symbol X --side SELL \
    --order-type LIMIT --volume 0.02 --entry 4179.50 --sl 4187.00 --tp1 4163.30 \
    --trigger "M15 rejection at 4179.83" --reject-reason R_R_BELOW_2_TO_TP1

Motivos de rechazo (taxonomía cerrada, para que las categorías sean agregables):
  R_R_BELOW_2_TO_TP1 | SPREAD_UNOPERABLE | NO_STRUCTURAL_TARGET |
  LEVEL_ALREADY_TESTED | SESSION_TOO_LATE | MAX_POSITIONS | CORRELATION

Resolver los madurados en cada ciclo:
  python counterfactual.py sweep
  python counterfactual.py stats

PASO 6 — SI EMITO UN TRADE
  1. Primero loguear: python log_trade.py signal --id T0NN --symbol X --side BUY/SELL \
       --order-type LIMIT/STOP/MARKET --volume V --entry E --sl S --tp1 T --trigger "..."
  2. Capturar contexto: python market_context.py capture --id T0NN
  3. Colocar: python order_executor.py place --id T0NN [--market]
     El executor bloquea si falla cualquier guardarraíl. NO uses --force.
  4. En cada revisión: python order_executor.py manage
  5. Loguear el MISMO setup como counterfactual, para que tomados y rechazados
     sean comparables.

PARADA DE EMERGENCIA:
  echo "STOP" > frival\data\emergency_stop.txt
Bloquea toda apertura. El flatten (close-all) sigue disponible — nunca
bloquees el cierre de posiciones.

Antes de emitir, lee los niveles actuales del mercado. NO uses niveles de
sesiones anteriores sin releerlos.