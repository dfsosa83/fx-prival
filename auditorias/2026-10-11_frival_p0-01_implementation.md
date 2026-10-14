# P0-01 — Informe de implementación (D1/D2 + limpieza robusta) — 2026-10-11

**Ticket:** P0-01 (entorno de pruebas offline aislado), acotado a: corrección de
D1, D2 y — en esta última iteración — **manejo robusto de fallos de limpieza**.
Ningún otro ticket.
**Estado:** entregado en worktree aislado para revisión. **Sin commit, sin push,
sin despliegue, sin sincronización al árbol principal, sin eliminar el worktree.**

## 1. Worktree y rama
- Ruta: `C:\Users\sosap\AppData\Local\Temp\kilo\frival-p001-wt`
- Rama: `p0-01-harness` en `7f9df8e8428e239a85136b7b2a3568f40301617b`.
- El árbol principal no se modificó: sus `frival/tests_offline/*` siguen intactos
  (sin seguimiento) y con los hashes originales.

## 2. Línea base y verificación de copia
- Línea base: `7f9df8e…` (`refs/heads/main`), verificada con `git -C <wt> rev-parse HEAD`.
- Copiados los 3 archivos P0-01 y comparados por SHA-256 **antes** de editarlos
  (coincidencia 3/3): `fake_mt5.py 4B5A54D3C426`, `harness.py 141A06C2C1BB`,
  `test_isolation.py 7325BD076CE5`.

## 3. Cambios (solo en el worktree)
- **D2 — contención de rutas (`harness.py`):** `_is_within(candidate, root)`
  (compara `resolve()` por `parents`; rechaza hermanos `<root>_x`); usado por
  `verify_isolation` y `R0-1`.
- **D1 — limpieza ante fallo de `__enter__` (`harness.py`):** `__enter__` en
  `try/except BaseException` → `_cleanup()` → re-lanza el original.
- **Nuevo (esta iteración) — limpieza robusta ante fallos de limpieza
  (`harness.py`):** `CleanupError`, `_fmt_failures`, `_cleanup` con pasos
  independientes y registro de fallos, `_cleanup_complete` sólo si no hay fallos,
  y `__exit__(exc_type, exc, tb)` que reporta. Detalle íntegro en §10.
- **Nuevo:** `frival/tests_offline/test_regressions.py` (D1/D2 + limpieza).

## 4. Pruebas — invocación, intérprete, resultados
Intérprete: `C:\Users\sosap\anaconda3\envs\frival\python.exe` (env conda `frival`;
Python 3.9.x). Desde la raíz del worktree, sólo pruebas seleccionadas (sin
descubrimiento global, sin scripts del proyecto):

```
python frival\tests_offline\test_regressions.py
python frival\tests_offline\test_isolation.py
```

- **Antes de las correcciones** (harness copiado sin modificar):
  `test_regressions.py` → **Ran 9, FAILED (failures=5)** (4 fugas D1 +
  `sibling_prefix_rejected`).
- **Tras D1/D2:** `test_regressions.py` → **Ran 9, OK**; `test_isolation.py` → **Ran 6, OK**.
- **Tras la limpieza robusta (esta iteración):**
  - `test_regressions.py` → **Ran 14, OK** (9 previos + 5 nuevos de limpieza)
  - `test_isolation.py` → **Ran 6, OK** (R0-1..R0-5 + producción intacta)

## 5. Pruebas NO ejecutadas y limitaciones
- **No** se probó la creación de symlink/junction (privilegios en Windows; no
  intentado) → rechazo de enlaces **por diseño (`resolve()`), no verificado**.
- **No** se ejecutaron P0-02 ni P1+. Sin MT5 real, red, credenciales ni `config/.env`.
- La suite corre **en proceso**; el harness copia todos los módulos pero sólo
  **importa `order_executor`**.
- La inyección de fallo de limpieza se hace parcheando `shutil.rmtree`; cubre ese
  paso, no una falla simultánea de todos los pasos.

## 6. Alcance exacto de la comparación de hashes
Cubre: los 7 `.py` de `harness.MODULES` + `trade_log.csv`, `execution_audit.jsonl`,
`executor_state.json`. **No cubre**: `counterfactuals.csv`, `reviews/`, `context/`,
`config/.env`, `frival/data/`, `kilo.json`, docs, git, ni `tests_offline/`. Es una
comparación de bytes en dos instantes en proceso, **no un manifiesto durable ni
prueba de que todo recurso de producción quedara intacto**.

## 7. Desviaciones (declaradas; NO se describen como borradas)
1. La implementación **original** de P0-01 se hizo en el **árbol principal sin
   worktree aislado** y **sin informe**. **No se borra ese hecho.** Este trabajo
   posterior **sí** usó un **worktree aislado** y **creó el informe faltante**;
   ambas cosas conviven en el historial.
2. Corrección de una afirmación previa: la limpieza D1 original **no** garantizaba
   preservar la excepción si la propia limpieza fallaba; esta iteración lo corrige.

## 8. Riesgos residuales
- `verify_isolation` cubre un conjunto fijo de 4 atributos (no exhaustivo).
- Comportamiento de enlaces no verificado empíricamente.
- La limpieza sólo se probó con un fallo inyectado en `rmtree` (no fallos múltiples).
- No se afirma aislamiento universal: sólo rutas inspeccionadas y casos probados.

## 9. Revisión y rollback (corregido)
- Revisar en el worktree: `harness.py`, `test_isolation.py`, `test_regressions.py`,
  este informe.
- **Rollback:** los archivos **no rastreados no son recuperables desde la rama por
  existir en su worktree**; **eliminar el worktree NO es el rollback por defecto**.
  Antes de cualquier limpieza: **preservar los archivos y la evidencia revisados**
  (copiarlos fuera del worktree y registrar hashes). Alternativa reversible: revertir
  los archivos a las copias originales por hash. `git worktree remove` /
  `git branch -D p0-01-harness` sólo si se decide descartar, y **nunca** como
  primer paso.

## 10. Corrección final — limpieza robusta (contenido íntegro)

### 10.1 Código (`harness.py`)
```python
class CleanupError(RuntimeError):
    """Raised when global-state restoration is incomplete after a test."""
    def __init__(self, failures):
        self.failures = list(failures)
        super().__init__(f"cleanup incomplete: {_fmt_failures(self.failures)}")


def _fmt_failures(failures) -> str:
    return "; ".join(f"{name}: {err!r}" for name, err in failures)
```
```python
    def __enter__(self):
        self._cleanup_complete = False
        self._cleanup_failures = []
        self._saved = {
            "path": list(sys.path),
            "env": os.environ.get("MT5_PATH"),
            "mods": {k: sys.modules.get(k) for k in
                     ("MetaTrader5", "mt5_path", self.module_name)},
        }
        try:
            ...  # mkdtemp / _seed_tree / fake / import / verify_isolation (igual)
        except BaseException as exc:
            # _cleanup() never raises; the ORIGINAL exception stays primary even
            # if cleanup is incomplete; failures are attached AND printed.
            failures = self._cleanup()
            if failures:
                setattr(exc, "_sandbox_cleanup_failures", failures)
                print(f"[harness] cleanup incomplete after failed __enter__: "
                      f"{_fmt_failures(failures)}", file=sys.stderr)
            raise
        return self

    def _cleanup(self):
        if getattr(self, "_cleanup_complete", False):
            return []
        s = self._saved or {}
        failures = []

        def attempt(name, fn):
            try:
                fn()
            except Exception as err:                # recorded, not swallowed
                failures.append((name, err))

        if "path" in s:
            attempt("sys.path", lambda: sys.path.__setitem__(slice(None), s["path"]))
        if "env" in s:
            if s["env"] is None:
                attempt("MT5_PATH", lambda: os.environ.pop("MT5_PATH", None))
            else:
                attempt("MT5_PATH", lambda: os.environ.__setitem__("MT5_PATH", s["env"]))
        for k, v in (s.get("mods") or {}).items():
            if v is None:
                attempt(f"sys.modules[{k}]", lambda k=k: sys.modules.pop(k, None))
            else:
                attempt(f"sys.modules[{k}]", lambda k=k, v=v: sys.modules.__setitem__(k, v))
        if self.tmp and self.tmp.exists():
            attempt("rmtree", lambda: shutil.rmtree(self.tmp, ignore_errors=False))

        self._cleanup_failures = failures
        self._cleanup_complete = not failures
        return failures

    def __exit__(self, exc_type, exc, tb):
        failures = self._cleanup()
        if not failures:
            return False
        if exc_type is None:
            raise CleanupError(failures)          # successful test: report loudly
        if exc is not None:
            setattr(exc, "_sandbox_cleanup_failures", failures)   # never mask
        print(f"[harness] cleanup incomplete while handling another exception: "
              f"{_fmt_failures(failures)}", file=sys.stderr)
        return False
```
Cómo cumple cada requisito: (1) `__enter__` re-lanza el original y `_cleanup`
nunca lanza → excepción primaria preservada; (2) `attempt()` aísla cada paso, los
independientes siguen; (3) fallos registrados en `_cleanup_failures`, impresos a
stderr y en `CleanupError`; (4) `_cleanup_complete` sólo si `failures` está vacío,
y una segunda llamada reintenta; (5) `__exit__` con test correcto y limpieza
incompleta lanza `CleanupError` (no silencioso).

### 10.2 Nuevas pruebas (`test_regressions.py`, clase `TestCleanupFailureHandling`)
- `test_init_failure_with_cleanup_failure_keeps_original_primary`
- `test_one_step_failure_does_not_abort_others`
- `test_cleanup_failure_is_reported`
- `test_cleanup_failure_after_success_not_silent`
- `test_repeated_cleanup_completed_and_pending`
