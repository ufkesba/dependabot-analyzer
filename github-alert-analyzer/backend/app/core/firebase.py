import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore
from app.core.config import settings

def initialize_firebase():
    """Initialize Firebase Admin SDK."""
    if not firebase_admin._apps:
        if settings.firebase_service_account_path:
            cred = credentials.Certificate(settings.firebase_service_account_path)
            firebase_admin.initialize_app(cred)
        else:
            # This will use Google Default Credentials when running on GCP
            firebase_admin.initialize_app()

def get_firestore_client():
    """Get Async Firestore client."""
    initialize_firebase()
    if settings.firebase_service_account_path:
        return firestore.AsyncClient.from_service_account_json(settings.firebase_service_account_path)
    return firestore.AsyncClient()
