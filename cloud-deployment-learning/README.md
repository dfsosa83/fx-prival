# README — Cloud Deployment Learning Journey

*Last updated: 2026-09-01 | Phase: 0 (setup)*

---

## What This Is

A guided, four-phase learning path to move Frival's model inference from your
laptop to **Google Cloud Run** — a serverless container platform that runs your
code on demand, costs nothing when idle, and teaches you Docker, cloud
architecture, and professional deployment practices along the way.

This is not a tutorial you read passively. Each section ends with a checkpoint
that requires you to *do* something before moving on. The checkpoints are tracked
in `checkpoints/` so you can see your progress at a glance.

**Prerequisites before starting Phase 1:**
- A Google Cloud account (free tier, requires a credit card for verification but
  won't be charged at our usage levels)
- Docker Desktop installed on your laptop (Windows: Docker Desktop with WSL2
  backend)
- Your existing Frival project with working models

---

## Technologies You Will Learn

| Technology | What It Does | When You Use It |
|---|---|---|
| **Docker** | Packages code into isolated, portable containers | Phase 1–4 |
| **FastAPI** | Python web framework for building APIs | Phase 2 |
| **Google Cloud Run** | Serverless container hosting (auto-scale, pay-per-request) | Phase 3 |
| **Google Container Registry (Artifact Registry)** | Stores Docker images in the cloud | Phase 3 |
| **Google Cloud Storage** | Stores model bundles, calendar CSVs, aux data | Phase 3 |
| **Google Cloud SDK (gcloud CLI)** | Command-line tool for all GCP operations | Phase 3 |
| **IAM (Identity and Access Management)** | Service accounts, permissions, least-privilege access | Phase 3–4 |
| **Google Cloud Logging** | Centralized logs from Cloud Run → searchable dashboard | Phase 4 |
| **Google Cloud Monitoring** | Uptime checks, alerting policies | Phase 4 |
| **Secret Manager** | Stores API keys securely (no hardcoded secrets) | Phase 4 |
| **Cloud Scheduler** | Triggers tasks on a schedule (cron-in-the-cloud) | Phase 4 (future) |

---

## The Big Picture: What You're Building

```
┌─────────────────────────────────────────────────────────┐
│                  YOUR LAPTOP (unchanged)                │
│  MT5 → fetch H1 bar → requests.post(cloud/predict)     │
│       ← probability → gates → agents → execute_bot      │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTPS (JSON)
                        ▼
┌─────────────────────────────────────────────────────────┐
│              GOOGLE CLOUD RUN (serverless)              │
│                                                         │
│  POST /predict                                           │
│    ├── compute_features()   [90+ indicators]            │
│    ├── load_model()         [joblib bundle from GCS]    │
│    └── predict()            [LightGBM/XGB/RF ensemble]  │
│                                                         │
│  Scales to zero when idle → costs $0 between requests   │
└─────────────────────────────────────────────────────────┘
```

The cloud endpoint replaces only the **model inference** portion of your daily
routine. MT5, the agent evaluation (Agent A/B), the senior synthesis, and the
execution bot all stay on your laptop where they belong. This separation is
deliberate: compute-heavy, deterministic ML moves to cloud; latency-sensitive,
credential-dependent logic stays local.

---

## Learning Path

### Phase 1 — Docker Foundations

**Goal:** Understand what a container is, write a Dockerfile, and run a model
inference container locally.

**Estimated time:** 2–3 sessions (3–5 hours total)

| Step | Topic | Deliverable |
|---|---|---|
| 1.1 | What is Docker? Images vs containers, layers, caching | Your own words in `checkpoints/phase-01.md` |
| 1.2 | Install Docker Desktop, verify `docker run hello-world` | Screenshot in `assets/phase-01-docker-running.png` |
| 1.3 | Write a minimal Dockerfile (Python 3.11 + numpy + pandas) | `phase-01-docker-foundations/Dockerfile.simple` |
| 1.4 | Build the image, run a container, verify Python version | Terminal output in `checkpoints/phase-01.md` |
| 1.5 | Understand `COPY`, `WORKDIR`, `CMD` vs `ENTRYPOINT` | Notes in `checkpoints/phase-01.md` |
| 1.6 | Write a Dockerfile for Frival inference (install scikit-learn, xgboost, lightgbm, joblib) | `phase-01-docker-foundations/Dockerfile.frival` |
| 1.7 | Copy model bundles + calendar CSVs into the image | `phase-01-docker-foundations/Dockerfile.frival` updated |
| 1.8 | Run inference inside the container, verify a probability prints | Terminal output in `checkpoints/phase-01.md` |

**Key concepts to master:**
- An image is a blueprint; a container is a running instance of that blueprint.
- Each `RUN` / `COPY` / `ADD` instruction creates a new *layer*. Layers are
  cached — unchanged layers don't rebuild. Put slow-changing things (model
  bundles) before fast-changing things (source code) in your Dockerfile.
- `docker build -t frival-inference .` builds. `docker run frival-inference`
  runs. `docker ps` lists running containers. `docker logs <id>` shows output.

**Checkpoint:** Before moving to Phase 2, you must be able to:
1. Build the Frival inference image from scratch (`docker build`)
2. Run a container that loads a model and produces a probability
3. Explain, in your own words, the difference between `COPY` and `RUN`, and why
   layer order matters for build speed

➜ Record answers in `checkpoints/phase-01.md`


### Phase 2 — Containers and APIs

**Goal:** Wrap the inference logic in a web server that accepts HTTP requests
and returns predictions.

**Estimated time:** 2–3 sessions (4–6 hours)

| Step | Topic | Deliverable |
|---|---|---|
| 2.1 | What is an API? REST, JSON, HTTP verbs (GET vs POST) | Notes in `checkpoints/phase-02.md` |
| 2.2 | Install FastAPI + uvicorn, write a `/health` endpoint | `phase-02-containers-and-apis/main.py` |
| 2.3 | Write the `/predict` endpoint: accept `{pair, features}`, return `{probability}` | `phase-02-containers-and-apis/main.py` updated |
| 2.4 | Test locally with `curl` and `requests.post()` from Python | Terminal output in `checkpoints/phase-02.md` |
| 2.5 | Understand request/response models with Pydantic | Notes in `checkpoints/phase-02.md` |
| 2.6 | Add error handling (missing fields, invalid pair, model load failure) | `phase-02-containers-and-apis/main.py` updated |
| 2.7 | Dockerize the FastAPI server, verify it runs as a container | `phase-02-containers-and-apis/Dockerfile` |
| 2.8 | Test the containerized API with `curl` from outside the container | Terminal output in `checkpoints/phase-02.md` |

**Key concepts to master:**
- A web server listens on a **port** (default: 8000). Inside a container, your
  app binds to `0.0.0.0:8000` so external requests can reach it.
- **POST** is for sending data (your feature vector). **GET** is for reading
  data (the `/health` check). Never use GET for predictions.
- **Pydantic models** validate input before your function runs. If the request
  body is malformed, FastAPI returns a 422 error automatically — no manual
  checking needed.
- Docker port mapping: `docker run -p 8000:8000 my-image` means "map port 8000
  on your laptop to port 8000 inside the container."

**Checkpoint:** Before moving to Phase 3, you must be able to:
1. Start the containerized API with `docker run -p 8000:8000`
2. Send a prediction request with `curl` and receive a valid probability
3. Explain why FastAPI uses Pydantic for request validation

➜ Record answers in `checkpoints/phase-02.md`


### Phase 3 — Google Cloud Platform

**Goal:** Deploy the containerized API to Google Cloud Run so it's accessible
from anywhere, not just your laptop.

**Estimated time:** 3–4 sessions (5–8 hours)

| Step | Topic | Deliverable |
|---|---|---|
| 3.1 | Create a GCP project, enable billing, install `gcloud` CLI | `gcloud projects list` output in `checkpoints/phase-03.md` |
| 3.2 | Understand GCP resource hierarchy: Organization → Project → Resources | Notes in `checkpoints/phase-03.md` |
| 3.3 | Enable required APIs: Cloud Run, Artifact Registry, Cloud Storage | `gcloud services list` output |
| 3.4 | Create an Artifact Registry repository for Docker images | `gcloud artifacts repositories create ...` command documented |
| 3.5 | Tag and push your Docker image to Artifact Registry | `gcloud builds submit` or `docker push` output |
| 3.6 | Deploy to Cloud Run: set memory (2 GB for ML models), timeout (60s), concurrency | `gcloud run deploy` command documented |
| 3.7 | Understand service accounts: what permissions your Cloud Run service needs | Notes in `checkpoints/phase-03.md` |
| 3.8 | Call your Cloud Run endpoint from your laptop with `curl` | Response in `checkpoints/phase-03.md` |
| 3.9 | Upload model bundles + calendar CSVs to Cloud Storage (rather than baking them into the image) | `gsutil cp` commands documented |
| 3.10 | Modify the Dockerfile to download models from Cloud Storage at startup | `phase-03-google-cloud-platform/Dockerfile` |
| 3.11 | Redeploy, test, verify latency is acceptable (< 2 seconds) | Response + timing in `checkpoints/phase-03.md` |

**Key concepts to master:**
- **Cloud Run** is serverless: you don't manage a VM, you don't scale anything.
  Google runs your container when a request arrives and stops it when it's idle.
  You pay only for the CPU/memory seconds used during requests.
- **Artifact Registry** is where your Docker images live in the cloud. Think of
  it as "Docker Hub, but private to your GCP project."
- **Cloud Storage** (GCS) is where your large, slow-changing files live:
  model bundles (`.joblib`), calendar CSVs, WTI/USDX data. Baking them into the
  Docker image works but makes every model update require a full image rebuild.
  Loading from GCS at startup separates concerns.
- **Service accounts** are identities for your cloud services, not humans.
  Your Cloud Run service needs a service account with `roles/storage.objectViewer`
  (to read model bundles) — nothing more. This is the principle of *least privilege*.
- **`gcloud` CLI** is your primary tool for everything GCP. Memorize:
  `gcloud auth login`, `gcloud config set project`, `gcloud run deploy`,
  `gcloud artifacts repositories create`, `gsutil cp`.

**Checkpoint:** Before moving to Phase 4, you must be able to:
1. Deploy a new version of your service with a single `gcloud run deploy`
2. Explain why Cloud Run is "serverless" and what happens when no requests arrive
3. Explain the difference between Artifact Registry and Cloud Storage, and why
   model bundles go in Cloud Storage, not baked into the Docker image

➜ Record answers in `checkpoints/phase-03.md`


### Phase 4 — Production Operations

**Goal:** Add logging, monitoring, error handling, and the local-to-cloud
integration so the daily routine works end-to-end.

**Estimated time:** 2–3 sessions (4–6 hours)

| Step | Topic | Deliverable |
|---|---|---|
| 4.1 | Understand structured logging: JSON logs → Cloud Logging | Notes in `checkpoints/phase-04.md` |
| 4.2 | Add request/response logging to the FastAPI server | `phase-04-production-operations/main.py` |
| 4.3 | View logs in Cloud Logging: filter by severity, search by request ID | Screenshot in `assets/phase-04-logging.png` |
| 4.4 | Add health-check uptime monitoring (Cloud Monitoring) | `gcloud monitoring uptime create ...` documented |
| 4.5 | Understand the local↔cloud integration: modify `main.py` to call Cloud Run | `phase-04-production-operations/frival_integration.py` |
| 4.6 | Add a fallback: if Cloud Run is unavailable, run inference locally | Code in `phase-04-production-operations/frival_integration.py` |
| 4.7 | Test the full daily routine: MT5 fetch → cloud predict → gates → agents → execute | Terminal output in `checkpoints/phase-04.md` |
| 4.8 | (Optional) Set up Cloud Scheduler for future hands-off execution | Notes in `checkpoints/phase-04.md` |

**Key concepts to master:**
- **Structured logging** means emitting JSON, not plain text. Cloud Logging
  indexes JSON fields automatically, so you can filter logs with queries like
  `severity=ERROR` or `pair=EURUSD`.
- **Uptime monitoring** pings your `/health` endpoint every minute from multiple
  global locations. If it fails, you get an email or SMS. This catches
  regressions before they affect your trading session.
- **Fallback** is the most important production pattern: if the cloud is
  unreachable (network issue, GCP outage, quota exceeded), your pipeline falls
  back to local inference. You never skip a trading session because of a cloud
  problem. The cloud is an optimization, not a dependency.
- **Cloud Scheduler** is GCP's cron service. It can trigger your Cloud Run
  endpoint on a schedule (e.g., 13:01 UTC daily), but it cannot start MT5 on
  your laptop. For a fully hands-off pipeline, you'd need a forex VPS with MT5
  running 24/7. That's a future decision.

**Checkpoint:** Before considering yourself done, you must be able to:
1. Deploy a change, view its logs in Cloud Logging, and confirm it works from
   the daily routine
2. Explain what happens when Cloud Run is down — step by step through the
   fallback path
3. Run the full daily routine with cloud inference and confirm identical results
   to local inference (same model, same features → same probability)

➜ Record answers in `checkpoints/phase-04.md`

---

## Progress Tracking

The `checkpoints/` folder contains four files, one per phase. Open each when you
start its phase and fill it in as you complete steps. A checkpoint is not "I
read the topic" — it's "I did the thing and can explain it."

Template for each checkpoint file:
```markdown
## Phase X Checkpoint — [Date Started]

### ✅ Completed Steps
- [ ] Step X.1 — [topic]  → [date + brief result]
- [ ] ...

### 📝 Comprehension Questions
Q1: [question from the checklist]
A1:

### 🔧 Terminal Output / Screenshots
[paste relevant output]
```

The `assets/` folder holds screenshots, diagrams, and terminal-capture files.
Name them by phase: `phase-02-curl-predict.png`.

---

## Folder Map

```
cloud-deployment-learning/
├── README.md                          ← you are here
├── phase-01-docker-foundations/
│   ├── exercises/                     ← small standalone practice files
│   ├── Dockerfile.simple              ← Step 1.3: minimal Python container
│   └── Dockerfile.frival              ← Step 1.6: Frival inference container
├── phase-02-containers-and-apis/
│   ├── main.py                        ← FastAPI server with /health and /predict
│   └── Dockerfile                     ← containerized API
├── phase-03-google-cloud-platform/
│   └── Dockerfile                     ← GCS-backed model loading
├── phase-04-production-operations/
│   ├── main.py                        ← production FastAPI (logging, metrics)
│   └── frival_integration.py          ← local↔cloud bridge with fallback
├── checkpoints/
│   ├── phase-01.md                    ← your answers, terminal output
│   ├── phase-02.md
│   ├── phase-03.md
│   └── phase-04.md
├── references/
│   ├── docker-cheatsheet.md           ← common Docker commands (to be written)
│   ├── gcloud-cheatsheet.md           ← common gcloud commands (to be written)
│   └── resources.md                   ← links to official docs, tutorials
└── assets/                            ← screenshots, diagrams, outputs
```

---

## How To Use This Guide

1. **Don't skip phases.** Phase 1 (local Docker) teaches you the container model
   that every cloud service is built on. Phase 2 (FastAPI) teaches you the
   request/response pattern that every cloud service uses. Phase 3 (GCP) puts
   them together. Phase 4 (production) makes them bulletproof.
2. **Fill in the checkpoints honestly.** If you can't explain a concept in your
   own words, you haven't learned it.
3. **Expect things to break.** Docker builds will fail with cryptic errors. Cloud
   Run deployments will return 403 or 500. Google's IAM permissions will block
   you. This is normal. The skill you're building is *debugging cloud
   infrastructure*, not memorizing commands.
4. **Commit your work.** After each phase checkpoint is complete, commit the
   checkpoint file and any new code to this repo. The git history is your
   learning journal.

---

## What Success Looks Like

When you finish all four phases, you will be able to:

- Write a Dockerfile from memory and explain why layer order matters
- Build a FastAPI server that validates input, returns JSON, and logs every
  request
- Deploy a container to Cloud Run with appropriate memory, timeout, and
  concurrency settings
- Diagnose a deployment failure using Cloud Logging
- Design a system with a cloud component and a local fallback — so a cloud
  outage never blocks a trading session
- Estimate monthly GCP costs for a given workload before deploying it

These skills are not specific to Frival or forex. They transfer to any project
that needs to move Python workloads from a laptop to the cloud.

---

*End of Phase 0 — let's begin Phase 1.*