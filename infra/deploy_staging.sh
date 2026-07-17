#!/usr/bin/env bash
# STAGING ONLY this wave. Laptop, named user. europe-west1 / natural-caster-496309-j3.
set -euo pipefail
PROJECT=natural-caster-496309-j3
REGION=europe-west1
SHA=$(git rev-parse --short HEAD)
REPO="${REGION}-docker.pkg.dev/${PROJECT}/szempont"

# Build both images (app + catalog-sync) from one source upload.
# NB: `gcloud builds submit` has no -f flag; non-root Dockerfiles must go
# through the cloudbuild config.
gcloud builds submit --project=$PROJECT \
  --config infra/cloudbuild.yaml \
  --substitutions=_GIT_SHA=$SHA,_REGION=$REGION .

gcloud run jobs deploy szempont-catalog-sync-staging \
  --project=$PROJECT --region=$REGION --image "$REPO/catalog-sync:$SHA" \
  --labels tool=szempont \
  --set-env-vars GCP_PROJECT=$PROJECT

gcloud run deploy szempont-app-staging \
  --project=$PROJECT --region=$REGION --image "$REPO/app:$SHA" \
  --labels tool=szempont \
  --set-env-vars GCP_PROJECT=$PROJECT,SZEMPONT_CATALOG=bq \
  --no-allow-unauthenticated

# Execute sync now:  gcloud run jobs execute szempont-catalog-sync-staging --region=$REGION
# Open the app (IAM-gated staging):
#   gcloud run services proxy szempont-app-staging --region=$REGION
# Schedule nightly sync after the converter refresh:
#   gcloud scheduler jobs create http szempont-catalog-sync-nightly ... (W2)
