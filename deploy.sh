#!/bin/bash

# Configuration
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
FUNCTION_NAME="dependabot-analyzer"

echo "Deploying $FUNCTION_NAME to Google Cloud Functions in project $PROJECT_ID..."

# Deploy the Cloud Function
gcloud functions deploy $FUNCTION_NAME \
  --gen2 \
  --runtime=python311 \
  --region=$REGION \
  --source=. \
  --entry-point=src.entrypoints.cloud_function.analyze_repo_http \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID

echo "Deployment complete!"
