## Phase 3 Checkpoint — Google Cloud Platform

**Date Started:** ____________________

---

### ✅ Completed Steps

- [ ] 3.1 — GCP project created, billing enabled, `gcloud` CLI installed
- [ ] 3.2 — GCP resource hierarchy understood
- [ ] 3.3 — APIs enabled: Cloud Run, Artifact Registry, Cloud Storage
- [ ] 3.4 — Artifact Registry repository created
- [ ] 3.5 — Docker image pushed to Artifact Registry
- [ ] 3.6 — Cloud Run deployment succeeded
- [ ] 3.7 — Service account permissions understood
- [ ] 3.8 — Cloud Run endpoint called from laptop with `curl`
- [ ] 3.9 — Model bundles + CSVs uploaded to Cloud Storage
- [ ] 3.10 — Dockerfile modified for GCS model loading
- [ ] 3.11 — Redeployed, tested, latency measured

---

### 📝 Step 3.2 — In your own words

Explain the GCP resource hierarchy (Organization → Project → Resources):

>

What is a service account? How is it different from your personal Google account?

>

Why do model bundles go in Cloud Storage instead of being baked into the Docker
image?

>

What does "serverless" mean in Cloud Run? What happens between requests?

>

---

### 🔧 Terminal Output

**Step 3.1 — `gcloud` installed and authenticated**
```
$ gcloud auth login
$ gcloud config set project [YOUR_PROJECT_ID]
$ gcloud projects list
[paste output]
```

**Step 3.5 — Push to Artifact Registry**
```
$ docker tag frival-api [REGION]-docker.pkg.dev/[PROJECT]/[REPO]/frival-api:latest
$ docker push [REGION]-docker.pkg.dev/[PROJECT]/[REPO]/frival-api:latest
[paste output]
```

**Step 3.6 — Deploy to Cloud Run**
```
$ gcloud run deploy frival-inference \
  --image=[REGION]-docker.pkg.dev/[PROJECT]/[REPO]/frival-api:latest \
  --memory=2Gi --timeout=60 --concurrency=1
[paste output — including the Service URL]
```

**Step 3.8 — `curl` against Cloud Run**
```bash
$ curl -X POST https://[SERVICE_URL]/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"pair": "EURUSD", "features": {...}}'
[paste response]
```

---

### 🧠 Self-Test

1. My Cloud Run deployment returns 403 Forbidden even though the service is up.
   What's the most likely cause?
   >
2. I updated my model bundle and pushed a new version. Do I need to rebuild the
   Docker image? Why or why not?
   >
3. Name three things `gcloud run deploy` does that `docker run` doesn't.
   >

---

### 🔴 Blockers / Questions

```
[Anything that stopped you — IAM permission errors, billing issues, 403/500 responses.]
```