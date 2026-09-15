# gcloud — Common Commands

## Setup

```bash
# Authenticate with Google Cloud
gcloud auth login

# List authenticated accounts
gcloud auth list

# Set the active project
gcloud config set project PROJECT_ID

# View current config
gcloud config list

# List all your projects
gcloud projects list
```

## Cloud Run

```bash
# Deploy a service
gcloud run deploy SERVICE_NAME \
  --image=REGION-docker.pkg.dev/PROJECT/REPO/IMAGE:TAG \
  --memory=2Gi \
  --timeout=60 \
  --concurrency=1 \
  --region=us-central1 \
  --allow-unauthenticated   # ⚠ Only for public APIs; prefer authenticated

# List all services
gcloud run services list

# Get the URL of a deployed service
gcloud run services describe SERVICE_NAME --format="value(status.url)"

# Delete a service
gcloud run services delete SERVICE_NAME
```

## Artifact Registry

```bash
# Create a Docker repository
gcloud artifacts repositories create REPO_NAME \
  --repository-format=docker \
  --location=REGION

# List repositories
gcloud artifacts repositories list

# List images in a repository
gcloud artifacts docker images list REGION-docker.pkg.dev/PROJECT/REPO

# Delete an image
gcloud artifacts docker images delete REGION-docker.pkg.dev/PROJECT/REPO/IMAGE:TAG
```

## Cloud Storage

```bash
# Create a bucket
gsutil mb gs://BUCKET_NAME

# Copy a file to Cloud Storage
gsutil cp local-file.joblib gs://BUCKET_NAME/

# Copy a directory recursively
gsutil cp -r models/ gs://BUCKET_NAME/

# List files in a bucket
gsutil ls gs://BUCKET_NAME/

# Download a file
gsutil cp gs://BUCKET_NAME/file.joblib .
```

## IAM & Permissions

```bash
# List service accounts
gcloud iam service-accounts list

# Grant a role to a service account
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SA_NAME@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

## Cloud Logging

```bash
# Read recent logs from Cloud Run
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=SERVICE_NAME" --limit=10

# Tail logs in real time
gcloud logging read "resource.type=cloud_run_revision" --limit=10 --format="json" --freshness=1m
```

## Useful Formats

```bash
# Get just the URL of a Cloud Run service
gcloud run services describe SERVICE_NAME --format="value(status.url)"

# Get all Cloud Run services as a table
gcloud run services list --format="table(name, region, status.url)"
```