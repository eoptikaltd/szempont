#!/usr/bin/env bash
# STAGING ONLY this wave. Laptop, named user. europe-west1 / natural-caster-496309-j3.
set -euo pipefail
PROJECT=natural-caster-496309-j3
REGION=europe-west1
TAG="${REGION}-docker.pkg.dev/${PROJECT}/szempont/catalog-sync:$(git rev-parse --short HEAD)"

gcloud builds submit --project=$PROJECT --tag "$TAG" -f infra/Dockerfile.ingest .
gcloud run jobs deploy szempont-catalog-sync-staging \
  --project=$PROJECT --region=$REGION --image "$TAG" \
  --labels tool=szempont \
  --set-env-vars GCP_PROJECT=$PROJECT
# Execute: gcloud run jobs execute szempont-catalog-sync-staging --region=$REGION
# Schedule nightly after the converter refresh:
# gcloud scheduler jobs create http szempont-catalog-sync-nightly ... (W2)
