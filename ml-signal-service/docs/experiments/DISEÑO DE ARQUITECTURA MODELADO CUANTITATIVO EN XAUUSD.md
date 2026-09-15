DISEÑO DE ARQUITECTURA: MODELADO CUANTITATIVO EN XAUUSD

Especificaciones de Target, Horizonte Dinámico y Feature Engineering Tabular

Este documento describe la especificación metodológica de un modelo predictivo diario diseñado para explotar regularidades estadísticas e inyecciones de liquidez en el par **XAUUSD** (Oro frente al Dólar Estadounidense) durante días de operación normal, mitigando de forma estricta las vulnerabilidades de *data leakage* y sobreajuste cronológico.

------

1. Justificación del Activo: ¿Por qué XAUUSD?

El oro no se comporta como un par de divisas tradicional (como el EURUSD). Desde una perspectiva microestructural, posee características idóneas para el modelado con algoritmos basados en árboles de decisión (*LightGBM*, *XGBoost*):

- **Volatilidad Asimétrica (Alta Relación Señal/Ruido):** XAUUSD tiene un ATR (*Average True Range*) diario sustancialmente mayor que las divisas G10. Esto significa que las fases de expansión son altamente direccionales y verticales, lo que permite mapear etiquetas discretas (\(Y = 1, -1\)) con menor contaminación de ruido blanco microestructural.
- **Comportamiento Híbrido (Commodity / Refugio):** Reacciona con extrema sensibilidad a los flujos de liquidez de las aperturas de mercado, lo que genera regularidades cíclicas horarias ideales para el desarrollo de *Cyclical Time Features*.
- **Concentración de Liquidez Institucional:** Al ser un mercado altamente centralizado a nivel interbancario, las fases de acumulación lateral concentran grandes volúmenes de órdenes pendientes en sus extremos (*Liquidity Sweeps*), permitiendo modelar reversiones con alta ventaja estadística.

------

2. Definición Formal de la Variable Objetivo (\(Y\))

El Método de la Triple Barrera (Triple Barrier Method)

Intentar predecir el precio neto o el retorno continuo de la siguiente vela (\(t+1\)) es un error clásico que condena al modelo al subajuste debido al ruido de alta frecuencia. En su lugar, el target se define mediante un proceso de **clasificación multiclase indexado a la volatilidad**.

Establecemos tres barreras dinámicas a partir del momento de activación de la muestra (\(t_0 = \text{08:01 AM Colombia}\)):

\(\text{Barrera\ Alcista\ (Take\ Profit)}=P_{t_{0}}+(1.5\times \text{ATR}_{M15})\)
\(\text{Barrera\ Bajista\ (Stop\ Loss)}=P_{t_{0}}-(1.0\times \text{ATR}_{M15})\)
\(\text{Barrera\ Temporal\ (Time\ Out)}=t_{0}+24\text{\ barras\ de\ M15\ }(\text{6\ Horas})\)

El vector objetivo \(Y\) se etiqueta de forma determinista bajo la siguiente lógica condicional:

\(Y=\begin{cases}1&\text{Si\ el\ precio\ toca\ la\ Barrera\ Alcista\ primero}\\ -1&\text{Si\ el\ precio\ toca\ la\ Barrera\ Bajista\ primero}\\ 0&\text{Si\ el\ precio\ agota\ las\ 6\ horas\ sin\ tocar\ ninguna\ barrera}\end{cases}\)

text

```
                       [ Barrera Temporal: 6 Horas ]
                                     |
+1.5 ATR (Take Profit) ------------->|  ===> Y = 1  (Compra Exitosa)
                                     |
Precio Base (08:01 AM) ------------->|  ===> Y = 0  (Inercia / Cierre Manual)
                                     |
-1.0 ATR (Stop Loss)   ------------->|  ===> Y = -1 (Venta / Invalidez)
```

Use code with caution.

------

3. Horizonte Temporal y Ventana de Predicción

El modelo procesa la información y emite su predicción exactamente a las **08:01 AM (Hora Colombia)**, dejando que los primeros 60 segundos de la sesión de Nueva York absorban el impacto inicial de las órdenes de mercado de alta frecuencia.

- **Ventana de Observación (Pasado):** 16 barras de M15 (Últimas 4 horas de la sesión de Londres) para extraer el momentum de la pre-apertura.
- **Horizonte de Proyección (Futuro):** Máximo 6 horas (24 barras de M15).
- **Justificación Matemática del Horizonte:** El momentum inyectado por las instituciones de Wall Street tiene una vida media transaccional que decae exponencialmente después de las 12:00 PM - 02:00 PM (Hora Colombia). Mantener operaciones abiertas en la sesión de la tarde introduce un coste por arrastre (*swap intraday*) e incrementa el riesgo de caer en la zona de ruido horizontal del mercado americano.