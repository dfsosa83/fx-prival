## Phase 2 Checkpoint — Containers and APIs

**Date Started:** ____________________

---

### ✅ Completed Steps

- [ ] 2.1 — What is an API? REST, JSON, HTTP verbs understood
- [ ] 2.2 — FastAPI `/health` endpoint working
- [ ] 2.3 — `/predict` endpoint returns `{probability}`
- [ ] 2.4 — Tested locally with `curl` and `requests.post()`
- [ ] 2.5 — Pydantic request/response models understood
- [ ] 2.6 — Error handling added (bad input, missing pair, model failure)
- [ ] 2.7 — FastAPI server running inside Docker
- [ ] 2.8 — `curl` hits the containerized API from outside

---

### 📝 Step 2.1 — In your own words

What is an API? Why do we use JSON as the data format?

>

Why POST for predictions and GET for health checks?

>

What does Pydantic do that plain Python type hints don't?

>

---

### 🔧 Terminal Output

**Step 2.4 — `curl /health` and `curl /predict`**
```bash
$ curl http://localhost:8000/health
[paste response]

$ curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"pair": "EURUSD", "features": {...}}'
[paste response]
```

**Step 2.8 — `curl` against the Dockerized API**
```bash
$ docker run -p 8000:8000 frival-api
# ... in another terminal:
$ curl http://localhost:8000/health
[paste response]

$ curl -X POST http://localhost:8000/health
# ^ deliberate: POST to /health should fail or return 405
[paste response]
```

---

### 🧠 Self-Test

1. My FastAPI server runs fine with `python main.py` but `docker run` says
   "connection refused." What did I forget?
   >
2. A client sends `{"pair": 123}` — what happens and why?
   >
3. Why do we bind to `0.0.0.0` inside the container, not `localhost`?
   >

---

### 🔴 Blockers / Questions

```
[Anything that stopped you.]
```