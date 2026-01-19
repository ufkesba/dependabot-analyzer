import json
import os
from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path
from ..agents.deep_analyzer import AnalysisReport

class Storage(ABC):
    @abstractmethod
    async def save_report(self, report: AnalysisReport) -> str:
        pass

    @abstractmethod
    async def get_reports(self) -> List[AnalysisReport]:
        pass

class NullStorage(Storage):
    async def save_report(self, report: AnalysisReport) -> str:
        return ""

    async def get_reports(self) -> List[AnalysisReport]:
        return []

class FileStorage(Storage):
    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    async def save_report(self, report: AnalysisReport) -> str:
        filename = f"{self.output_dir}/alert_{report.alert_number}_{report.package}.json"
        with open(filename, 'w') as f:
            json.dump(report.model_dump(), f, indent=2)
        return filename

    async def get_reports(self) -> List[AnalysisReport]:
        reports = []
        for file in Path(self.output_dir).glob("*.json"):
            with open(file, 'r') as f:
                data = json.load(f)
                reports.append(AnalysisReport(**data))
        return reports

class FirestoreStorage(Storage):
    def __init__(self, collection: str = "analysis_reports"):
        import firebase_admin
        from firebase_admin import credentials, firestore

        try:
            # Check if already initialized
            self.app = firebase_admin.get_app()
        except ValueError:
            # Initialize with default credentials
            self.app = firebase_admin.initialize_app()

        self.db = firestore.client()
        self.collection = collection

    async def save_report(self, report: AnalysisReport) -> str:
        # Sanitize package name for use in document ID (replace / with _)
        safe_package = report.package.replace("/", "_").replace("@", "")
        doc_id = f"alert_{report.alert_number}_{safe_package}"
        doc_ref = self.db.collection(self.collection).document(doc_id)
        doc_ref.set(report.model_dump())
        return f"firestore://{self.collection}/{doc_id}"

    async def get_reports(self) -> List[AnalysisReport]:
        reports = []
        docs = self.db.collection(self.collection).stream()
        for doc in docs:
            reports.append(AnalysisReport(**doc.to_dict()))
        return reports
