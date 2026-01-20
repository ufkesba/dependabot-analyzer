#!/bin/bash
set -e

# Configuration
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
SERVICE_NAME="github-alert-analyzer-backend"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "🚀 Deploying GitHub Alert Analyzer Backend to GCP..."

# Build and push Docker image
echo "📦 Building Docker image..."
docker build -t $IMAGE_NAME ./github-alert-analyzer/backend

echo "⬆️ Pushing Docker image to GCR..."
docker push $IMAGE_NAME

# Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,ENVIRONMENT=production"

echo "✅ Deployment complete!"
echo "Backend URL: $(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format='value(status.url)')"
