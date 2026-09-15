## Phase 4 Checkpoint — Production Operations

**Date Started:** ____________________

---

### ✅ Completed Steps

- [ ] 4.1 — Structured logging understood (JSON → Cloud Logging)
- [ ] 4.2 — Request/response logging added to FastAPI
- [ ] 4.3 — Logs visible in Cloud Logging, filtering works
- [ ] 4.4 — Uptime monitoring configured for `/health`
- [ ] 4.5 — Local `main.py` modified to call Cloud Run
- [ ] 4.6 — Fallback path works (local inference when cloud is down)
- [ ] 4.7 — Full daily routine end-to-end tested
- [ ] 4.8 — (Optional) Cloud Scheduler evaluated

---

### 📝 Step 4.1 — In your own words

Why JSON logs instead of plain text?

>

What is the fallback path and why is it essential?

>

If Cloud Run is down for 10 minutes during your trading window, what happens —
step by step?

>

---

### 🔧 Terminal Output

**Step 4.7 — Full daily routine**
```
$ MERG_ENABLED=true MERG_SHADOW_ONLY=true python -c "..."
[paste the relevant output showing cloud inference + agents + execution]
```

**Step 4.6 — Fallback test**
```
# Simulate cloud outage: stop Cloud Run or use a bad URL
$ python frival_integration.py
[paste output showing fallback to local inference]
```

---

### 🧠 Self-Test

1. I deployed a change to Cloud Run but the old version is still responding.
   What went wrong?
   >
2. My Cloud Run logs show `severity=ERROR` but I don't get an alert. What
   haven't I configured?
   >
3. If I want to know the exact latency of every `/predict` request over the last
   24 hours, where do I look?
   >

---

### 📊 Latency Baseline

Measure 10 consecutive calls to Cloud Run and record:

| # | Pair | Latency (ms) |
|---|---|---|
| 1 | EURUSD | |
| 2 | GBPUSD | |
| 3 | USDCHF | |
| 4 | USDCAD | |
| ... | ... | |

Average: _____ ms
Max: _____ ms

---

### 🔴 Blockers / Questions

```
[Anything that stopped you.]
```