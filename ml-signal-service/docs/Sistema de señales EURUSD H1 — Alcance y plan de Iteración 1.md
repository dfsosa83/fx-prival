# Sistema de señales EURUSD H1 — Alcance y plan de Iteración 1

*Documento de trabajo interno · 13 de julio de 2026 · Estado: Iteración 1 en curso*

------

## 1. Definición de Y₁ y criterios de éxito

**Qué predice el modelo:** En cada cierre de vela H1, el modelo responde una pregunta binaria muy concreta:

> *Si entro en largo en este momento con un trade 1:1.5 (TP = 1.5× ATR por encima de la entrada, SL = 1.0× ATR por debajo), ¿el precio llega primero al Take Profit antes de tocar el Stop Loss en las próximas 6 horas?*

- **Label = 1:** el TP se ejecuta primero → entrada históricamente favorable.
- **Label = 0:** el SL se ejecuta primero, o el trade expira sin llegar a TP ni SL → entrada desfavorable.

Uso el ATR (Average True Range) de 14 periodos como regla básica de volatilidad en lugar de objetivos fijos en pips, para que TP y SL se adapten al régimen de mercado actual.

**Criterios de éxito para la Iteración 1:**

| Criterio                              | Umbral                                     | Cómo se mide                                     |
| :------------------------------------ | :----------------------------------------- | :----------------------------------------------- |
| Precisión de la señal en test sellado | ≥ 0.40 (aprox. breakeven con R:R 1:1.5)    | Precisión = TP alcanzados ÷ total de señales     |
| Frecuencia de señales                 | ≥ 0.15 señales/día                         | Total señales ÷ días de trading                  |
| Trazabilidad de decisiones            | Cada señal registrada con razón por “gate” | Log de decisiones en CSV para revisión histórica |

La idea en esta primera iteración no es construir el sistema perfecto, sino lograr algo que cruce breakeven de forma consistente y nos sirva como base para iterar con más criterio.

## 2. Timeline del proyecto

| Fase                     | Entregable                                               | Ventana estimada |
| :----------------------- | :------------------------------------------------------- | :--------------- |
| **Iteración 1** (actual) | Modelo de señales BUY validado en test                   | 14–18 jul        |
| **Iteración 2**          | Capa de validación con agentes LLM (Perplexity + GPT-4o) | 21–25 jul        |
| **Iteración 3**          | Emisor de alertas en producción + scheduler              | 28 jul–1 ago     |
| **Iteración 4**          | Paper trading en vivo (sin capital real)                 | Desde 4 ago      |

Iteración 1 está ya en la semana de validación final. 

## 3. Componentes del sistema

## En implementación.

| Componente                         | Descripción                                                  |
| :--------------------------------- | :----------------------------------------------------------- |
| Modelo BUY LightGBM                | 22 features seleccionadas, entrenadas con datos 2019–jun 2025 |
| Modelo SELL LightGBM               | 19 features, usado solo como filtro cruzado (no genera señales independientes) |
| Pipeline de combinación de señales | Modo solo BUY con 4 “gates” de decisión: umbral → filtro cruzado → sesión → cooldown |
| Log de decisiones                  | CSV de trazabilidad completa (~46K barras): buy_proba, sell_proba, TP, SL y razón de cada gate por barra |

## En diseño / planeado

| Componente                      | Iteración | Descripción                                                  |
| :------------------------------ | :-------- | :----------------------------------------------------------- |
| Agente de validación Perplexity | 2         | LLM con acceso web que revisa cada señal y puede confirmarla o descartarla con base en análisis técnico, noticias, sentimiento y correlaciones relevantes. |
| Agente de evaluación GPT-4o     | 2         | Segundo LLM independiente para revisar las mismas señales y reducir el riesgo de depender de un solo proveedor de modelos. |
| Motor de reglas                 | 2         | Capa que combina: modelo base, Perplexity y GPT-4o, y decide la acción final con un nivel de confianza. |
| Validador “senior”              | 2         | Revisión de riesgo con GPT-4o: valida lógica, relación riesgo/beneficio y ubicación de stops antes de cualquier ejecución. |
| Emisor de alertas               | 3         | Generación de alertas estructuradas en JSON con entrada, TP, SL, confianza, deduplicación y registro histórico. |
| Scheduler horario               | 3         | Tarea programada (Windows Task Scheduler) que dispara el proceso a los :01 de cada hora. |
| Ejecutor de paper trading       | 4         | Simulación de ejecuciones con PnL y métricas de riesgo, sin capital real en juego. |

En Iteración 2 quiero usar la capa de LLM como filtro adicional de falsos positivos, más que como “oráculo”; la decisión final se mantiene basada en datos modelo principal y expertos financieros de mesa de trading.

## 4. Metodología analítica

**Pipeline de datos (versión actual):**

Parto de un CSV de MT5 con velas H1 desde 2019 hasta julio de 2026. Sobre esa base genero alrededor de 86 variables: indicadores técnicos clásicos, contexto diario (D1) y flags de sesión (Londres, NY, etc.). Luego aplico un esquema de selección de variables con “noise-injection” usando Random Forest, LightGBM y regresión logística, buscando consenso entre modelos.

La parte de modelado está montada con LightGBM como clasificador principal, optimizado para PR-AUC. El umbral de decisión se calibra en el punto de equilibrio de la curva precision–recall, para que el sistema quede alineado con la relación R:R 1:1.5 que se usa en los trades.

**Disciplina de validación:**

- Train / Val / Test por períodos:
  - Train: 2019–jun 2025
  - Val: jul 2025–ene 2026
  - Test: feb 2026–jul 2026
- La selección de features se ajusta solo en el set de entrenamiento para evitar leakage.
- El test se mantiene sellado y solo se abre una vez por iteración para la evaluación final.
- Todas las señales se registran con la razón de cada gate en el CSV, para poder auditar el comportamiento del sistema con detalle.

## Gates de decisión (post-inferencia)

Estos filtros se aplican después de la predicción del modelo, sin necesidad de reentrenar:

1. **Umbral (Gate 1):** uso buy_proba ≥ 0.678, calibrado en función de la curva PR-AUC y el punto donde precision y recall se equilibran de forma razonable.
2. **Filtro cruzado (Gate 2):** si sell_proba ≥ 0.60 considero la vela ambigua y no emito señal BUY.
3. **Sesiones (Gate 3):** limito señales a Londres (07:00–15:59 UTC) y Nueva York (13:00–21:59 UTC), evitando sesiones con menor liquidez.
4. **Cooldown (Gate 4):** máximo una señal cada 4 velas para evitar clusters de entradas muy seguidas en el tiempo.

Los umbrales actuales son tentativos; si en los tests finales veo que hay sensibilidad fuerte por sesión o régimen de volatilidad, los ajustaré antes de cerrar la iteración.

## 5. Objetivos por iteración

| Iteración | Objetivo                                                     | Métrica principal                                            |
| :-------- | :----------------------------------------------------------- | :----------------------------------------------------------- |
| 1         | El modelo BUY-only supera breakeven en el test sellado       | Precisión ≥ 0.40                                             |
| 2         | La capa de agentes LLM reduce la tasa de falsos positivos    | Al menos 10% de señales del modelo base rechazadas correctamente por los agentes |
| 3         | El sistema de alertas corre de forma autónoma y estable durante una semana | 100% de ejecuciones programadas sin fallos silenciosos       |
| 4         | El paper trading muestra PnL positivo en una ventana de dos semanas | Sharpe > 0 y drawdown máximo < 5%                            |

------

Este documento es un insumo de trabajo para la Iteración 1. Los resultados finales de la iteración se actualizarán aquí una vez termine la fase de pruebas de configuración.

------

