## Phase 1 Checkpoint — Docker Foundations

**Date Started:** ____________________

---

### ✅ Completed Steps

- [ ] 1.1 — What is Docker? (my explanation below)
- [ ] 1.2 — Docker Desktop installed, `docker run hello-world` succeeded
- [ ] 1.3 — Minimal Dockerfile written
- [ ] 1.4 — Image built and container run successfully
- [ ] 1.5 — `COPY`, `WORKDIR`, `CMD` vs `ENTRYPOINT` understood
- [ ] 1.6 — Frival inference Dockerfile written
- [ ] 1.7 — Model bundles + CSVs copied into image
- [ ] 1.8 — Inference runs inside container, probability prints

---

### 📝 Step 1.1 — In your own words

What is Docker?

> (Write 3-5 sentences. Use "image" and "container" correctly.)

What is the difference between an image and a container?

>

Why does layer order matter in a Dockerfile?

>

---

### 🔧 Terminal Output

**Step 1.2 — `docker run hello-world`**
```
[paste output here]
```

**Step 1.4 — Build and run your first image**
```
$ docker build -t my-first-image .
[paste output]

$ docker run my-first-image
[paste output]
```

**Step 1.8 — Frival inference in container**
```
$ docker build -t frival-inference -f Dockerfile.frival .
[paste build output — or note "too long; build succeeded"]

$ docker run frival-inference
[paste the probability output]
```

---

### 🧠 Self-Test

Before moving to Phase 2, answer these without looking at the guide:

1. What command builds an image? What command runs a container?
   >
2. If I change a line in `main.py` and rebuild, do the model bundles re-copy?
   Why or why not?
   >
3. My container exits immediately after `docker run`. I used `CMD ["python",
   "main.py"]`. What's the most likely reason?
   >

---

### 🔴 Blockers / Questions

```
[Anything that stopped you — error messages, concepts you don't get. We'll
address these before Phase 2.]
```