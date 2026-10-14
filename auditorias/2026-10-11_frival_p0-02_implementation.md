# P0-02 — Informe de implementación (cuarentena del arnés kill-switch) — 2026-10-11

**Ticket:** P0-02 (cuarentena del arnés live `test_kill_switch.py` y sustitución
de sus comprobaciones por pruebas offline). Ningún otro ticket.
**Estado:** entregado en worktree aislado para revisión. **Sin commit, sin push,
sin despliegue, sin sincronización al árbol principal, sin eliminar el worktree.**

## 1. Línea base y worktree
- Worktree: `C:\Users\sosap\AppData\Local\Temp\kilo\frival-p002-wt` — rama
  `p0-02-quarantine` — HEAD `7f9df8e8428e239a85136b7b2a3568f40301617b`.
- Se copiaron al worktree los **archivos P0-01 aceptados** desde `main` y se
  verificaron por SHA-256 (4/4): `fake_mt5.py 4B5A54D3C426…`,
  `harness.py 9998F16AC92E41AD…`, `test_isolation.py FAA6565215AB9845…`,
  `test_regressions.py CB8EC8907CAEE77C…`. (Los P0-01 no se modifican aquí.)
- El arnés legacy venía del HEAD (rastreado): `frival/test_kill_switch.py`,
  SHA-256 `85D433B865E85618A815BCE1749933EF906524322F166231E0D3B2D879E60F28` (7396 B).

## 2. Archivos cambiados / añadidos (worktree)
- **Cambiado (cuarentena, único archivo de código existente tocado):**
  `frival/test_kill_switch.py` → punto de entrada bloqueado.
- **Añadido (pruebas):** `frival/tests_offline/test_kill_switch_offline.py`.
- **Añadido (evidencia):** `auditorias/2026-10-11_frival_test_kill_switch_original.txt`
  (copia byte-idéntica del original, no ejecutable).
- **Añadido (informe):** este archivo.

## 3. Archivo original y hash
- `auditorias/2026-10-11_frival_test_kill_switch_original.txt` —
  SHA-256 `85D433B865E85618A815BCE1749933EF906524322F166231E0D3B2D879E60F28`
  (idéntico al original). Recoverable.

## 4. Mapeo de las 8 comprobaciones del arnés original
| # | Comprobación legacy | Sustituto |
|---|---|---|
| 1 | kill switch file is created | offline: fixture `arm_kill_switch` (setup de R0-6/R0-10) |
| 2 | status read-only no bloqueado con switch armado | offline: `test_r0_6b_status_readonly_with_switch_armed` |
| 3 | place aborta con switch armado | offline: **R0-6** |
| 4 | close-all permitido con switch armado (sin `--force`) | offline: **R0-7** |
| 5 | nada nuevo abierto con switch armado | offline: R0-6 (sin `order_send`) + **R0-10** (ledger sin cambios) |
| 6 | kill switch file removed (disarm) | **duplicado documentado:** ciclo de fixture del sandbox (árbol temporal); no hay acción live |
| 7 | place alcanza guardarraíles tras disarm | offline: **R0-8** |
| 8 | nada abierto en ningún momento | offline: **R0-8** (sin `order_send`) |

Ningún sustituto llama al terminal real ni usa `subprocess`; todo corre en proceso
contra el fake P0-01 y datos desechables.

## 5. Pruebas ejecutadas y resultados
Intérprete: `C:\Users\sosap\anaconda3\envs\frival\python.exe`. Desde la raíz del
worktree, solo suites seleccionadas (sin descubrimiento global, sin CLI de proyecto):
- `python frival\tests_offline\test_regressions.py` → **Ran 14, OK**
- `python frival\tests_offline\test_isolation.py` → **Ran 6, OK**
- `python frival\tests_offline\test_kill_switch_offline.py` → **Ran 9, OK**
  (R0-6, R0-6b, R0-7, R0-8, R0-9, R0-10 + 3 del punto de entrada bloqueado)
- Punto de entrada bloqueado: `python frival\test_kill_switch.py` → **exit code 2**,
  mensaje `[DISABLED]…`, sin MT5.

**Defecto propio detectado y corregido (dentro de P0-02):** la primera versión de
`test_blocked_source_has_no_broker_or_subprocess` comprobaba la *palabra*
`MetaTrader5` en el fuente, que aparece en la prosa del docstring; se corrigió a
comprobar imports/usos (`import MetaTrader5`, `import subprocess`, `subprocess.run`,
`mt5.initialize`, `--force`). No afectó al código de producción.

## 6. Pruebas NO ejecutadas y motivos
- No hay validación live «8/8», ni demo, ni broker real (fuera de alcance).
- No se corrige close-all/ownership/pending-exposure/breakers/persistencia (fuera
  de P0-02). El alcance de propiedad de `close-all` queda para P2-05; R0-7 sólo
  prueba el comportamiento sobre el fixture.

## 7. Referencias de documentación pendientes de actualizar (NO autorizadas aquí)
Aún instruyen ejecutar el arnés legacy:
- `README.md:55` — `python test_kill_switch.py  # 8/8 must pass before live trading`
- `frival/SETUP_NEW_MACHINE.md:133` — `python test_kill_switch.py` (y mención en L82)
- `continua-operando.md:71` — describe `test_kill_switch.py` como verificación end-to-end

No se editan en este lote. Quedan como pendientes.

## 8. Riesgos residuales y procedimiento de incorporación
- La evidencia archivada es un `.txt` recuperable: renombrarlo a `.py` volvería a
  habilitar el código legacy (evidencia, no ejecutable por defecto). Se documenta.
- El punto de entrada bloqueado impide el comportamiento live, pero no impide que
  alguien restaure el archivo desde el archivo histórico; el control es de proceso.
- `ResourceWarning` preexistente en `order_executor.py:169` (no corregido aquí).
- **Incorporación (posterior, requiere autorización):** reemplazar
  `frival/test_kill_switch.py`; añadir `frival/tests_offline/test_kill_switch_offline.py`
  y los dos archivos de `auditorias/`; verificar hashes; ejecutar las tres suites.
  Preservar el archivo histórico y no tocar otros archivos.

**No se afirma** que el sustituto offline reproduzca una validación live «8/8» ni que
establezca corrección del broker real.
