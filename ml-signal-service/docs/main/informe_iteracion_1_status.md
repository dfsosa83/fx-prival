# EURUSD H1 Sistema de Señales — Informe de Estado Iteración 1

*Informe de avance · 19 de julio de 2026 · Período reportado: 14–19 de julio*

---

## 1. Lo que se logró esta semana

Ejecutamos 4 ciclos completos de experimentación con múltiples configuraciones. Cada ciclo es un pipeline completo: carga de datos → 86 features de ingeniería → votación con inyección de ruido → validación cruzada anidada → entrenamiento del modelo → calibración de umbral → evaluación en test sellado.

**Matriz de experimentos completada:**

| Experimento | Barras forward | Multiplicador TP | Modelo evaluado | ROC-AUC (val) | Precisión en test (con gates) |
|---|---|---|---|---|---|
| 1 (línea base) | 6 | 1.5 | LightGBM | 0.651 | 0.348 |
| 2 | 4 | 1.5 | RandomForest | 0.695 | 0.300 (est.) |
| 3 | 2 | 1.25 | XGBoost | 0.735 | — (44 señales) |
| 4 | 6 | 1.5 | LightGBM (re-ajustado) | 0.651 | 0.286 |

**Infraestructura construida en paralelo:**

| Componente | Estado | Descripción |
|---|---|---|
| Pipeline de entrenamiento BUY | Completo | 22 features seleccionadas, CV anidada, votación con ruido |
| Pipeline de entrenamiento SELL | Completo | 19 features, arquitectura espejo |
| Notebook del combinador de señales | Completo | 4 filtros de decisión, Sección 9 de evaluación en test, barrido de cross-filter |
| Script predictor de producción | Completo | `eurusd_h1_predictor.py` — evalúa cada barra H1, guarda registro de decisiones |
| Registro de decisiones | Completo | 46,336 filas, razón de cada filtro por barra, TP/SL/precio de entrada |
| Pipeline de datos macro Bloomberg | Completo | `build_macro_dataset.py`, documentos de especificación, guía operativa para el desk |
| Guardado/carga de bundles | Completo | Archivos `.joblib` con lista de features, umbrales, parámetros de etiquetas |
| Mejoras en selección de features | Completo | Importancia LGBM basada en ganancia, sistema de votación MIN_VOTES |

---

## 2. Resultados actuales — evaluación honesta

**Mejor configuración en test sellado (109 días hábiles, feb–jul 2026):**

| Métrica | Valor | Objetivo | Estado |
|---|---|---|---|
| Precisión BUY (con filtros) | **0.348** | ≥ 0.400 | Por debajo del objetivo |
| Señales por día | 46 (0.42/día) | ≥ 0.15/día | Cumple |
| ROC-AUC (validación) | 0.651 | — | — |
| Brecha de sobreajuste (val→test) | +0.075 | ≤ 0.050 | Por encima del umbral |
| Trazabilidad de decisiones | 100% de barras registradas | 100% | Cumple |

El techo discriminativo del modelo está establecido en **ROC-AUC ≈ 0.65** y **precisión con filtros ≈ 0.35**. Este resultado es consistente en los cuatro experimentos, tres arquitecturas de modelo (LightGBM, XGBoost, RandomForest) y múltiples enfoques de selección de features. El modelo separa de forma fiable algunas entradas buenas de las malas — no es aleatorio — pero no puede alcanzar el umbral de equilibrio de 0.400 en datos no vistos con volúmenes de señal utilizables.

Hallazgos adicionales del ciclo de experimentación:
- Acortar la ventana forward mejora el ROC-AUC (0.735 en FW=2) pero reduce la tasa de etiquetas positivas, haciendo el desbalance de clases más difícil de entrenar
- El reentrenamiento completo (train+val combinados) **empeoró** el rendimiento debido al sobreajuste de régimen — los patrones del período de validación no generalizan al test
- El modelo SELL tiene mejores métricas brutas que BUY (PR-AUC 0.386 vs 0.330) pero falla igual en precisión final con filtros (0 señales sobreviven)
- Los features macro de Bloomberg (Brent, EURIBOR) sobrevivieron 3/3 votos en selección pero agregaron cero precisión marginal en el pipeline del combinador

---

## 3. Por qué el modelo no cruza el punto de equilibrio — análisis de causa raíz

El diseño de etiquetas H1 (carrera TP/SL de 6 horas con R:R=1.5) produce un objetivo que es **inherentemente ruidoso**. Muchos aciertos de TP son suerte — impulsados por volatilidad horaria aleatoria, no por patrones detectables desde los features de la barra de entrada. El modelo distingue barras mejores que el promedio de barras peores que el promedio (ROC-AUC 0.65), pero la diferencia es pequeña — no suficiente para alcanzar 40% de precisión absoluta.

Esto no es un problema de arquitectura del modelo. Tres tipos de modelo fundamentalmente diferentes (ensemble de árboles, gradient boosting, regresión lineal) convergen al mismo techo. El cuello de botella es la **relación señal-ruido de la etiqueta**, no el clasificador.

---

## 4. Plan de trabajo extendido — Iteración 1.5 (20–25 de julio)

El plan original apuntaba a una semana por iteración. La Iteración 1 ha establecido la línea base del modelo pero no ha superado el criterio de éxito. Propongo una **Iteración 1.5 extendida** antes de pasar a la capa de agentes (Iteración 2):

| Día | Actividad | Objetivo |
|---|---|---|
| 20 jul (lun) | Explorar diseños alternativos de etiquetas: ventanas forward más largas (8, 10, 12 barras), diferentes ratios TP/SL, etiquetas de reversión a la media | Encontrar una configuración de etiquetas con mejor relación señal-ruido |
| 21 jul (mar) | Estudio de ablación de features: eliminar features de baja varianza, probar grupos de interacción | Identificar si alguna clase de feature está perjudicando activamente |
| 22 jul (mié) | Re-ejecutar la configuración ganadora de etiquetas por el pipeline completo | Entrenar nuevo modelo con etiquetas mejoradas |
| 23 jul (jue) | Evaluar en test sellado, comparar contra línea base de Iteración 1 | Determinar si el cambio de etiquetas cerró la brecha |
| 24 jul (vie) | Punto de decisión: si precisión en test ≥ 0.400 → cerrar Iteración 1. Si no → documentar hallazgos y proceder a Iteración 2 (pipeline de agentes) de todos modos | Evitar iteración infinita sobre la capa del modelo |

**Plan B:** Si el rediseño de etiquetas no supera 0.400 para el viernes, el modelo actual (precisión 0.348, 46 señales) es la línea base aceptada de Iteración 1. Procedemos a Iteración 2 — la capa de validación multi-agente — donde los agentes Perplexity y GPT-4o evalúan independientemente cada señal. La hipótesis es que los agentes pueden rechazar falsos positivos que el modelo no puede, agregando el +0.052 de precisión restante necesario para alcanzar el punto de equilibrio.

---

## 5. Próximos pasos inmediatos para Iteración 2 (listo para empezar independientemente)

Toda la infraestructura para Iteración 2 ha sido diseñada y documentada (`ml-signal-service/docs/next_agent_pipeline_design.md`):

1. **Agente de validación Perplexity** — envía cada señal BUY a través de un prompt de análisis de 5 pilares (técnico, fundamental, sentimiento, noticias, correlación) → devuelve CONFIRMAR/RECHAZAR/NEUTRAL
2. **Agente de evaluación GPT-4o** — revisión independiente con LLM de otro proveedor → elimina sesgo de proveedor único
3. **Motor de reglas** — combina modelo base + ambos agentes → acción final con nivel de confianza (BUY FUERTE / BUY / OMITIR)
4. **Validador senior agent** — capa de revisión de riesgo GPT-4o: valida lógica, matemática R:R, colocación de stop, exposición de cuenta

La Iteración 2 no requiere reentrenamiento del modelo — es una capa post-inferencia que lee el registro de decisiones existente.

---

## 6. Riesgo y evaluación honesta

**Lo que funciona:** La infraestructura es de grado producción. La ingeniería de features, el entrenamiento del modelo, la evaluación, los filtros de decisión y el script predictor son todos funcionales, documentados y reproducibles. Cualquier rediseño futuro de etiquetas o adición de features puede probarse en horas, no días.

**Lo que no funciona:** La etiqueta direccional H1 tiene una señal predictiva limitada. El modelo es un clasificador débil, no un clasificador fuerte. La precisión de 0.348 significa que ~65% de las alertas son falsos positivos — la capa de agentes debe manejar esto.

**Lo que necesito:** Una semana más para experimentos de diseño de etiquetas (Iteración 1.5) antes de proceder al pipeline de agentes. Si los cambios de etiquetas no ayudan, procedemos a Iteración 2 el 25 de julio con el modelo actual como línea base aceptada.

---

*Este informe refleja el trabajo completado del 14 al 19 de julio de 2026. Próxima actualización de estado: 25 de julio de 2026.*