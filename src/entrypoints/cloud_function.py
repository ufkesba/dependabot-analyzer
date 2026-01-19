import os
import json
import asyncio
import functions_framework
from ..orchestrator.workflow import DependabotAnalyzer
from ..storage import FirestoreStorage
from ..config.secrets import get_secret

@functions_framework.http
def analyze_repo_http(request):
    """
    HTTP Cloud Function to analyze a repository.
    Expected JSON body:
    {
        "repo": "owner/repo",
        "min_severity": "medium",
        "max_alerts": 10,
        "model": "gemini-flash-latest",
        "provider": "google"
    }
    """
    request_json = request.get_json(silent=True)
    if not request_json or 'repo' not in request_json:
        return json.dumps({"error": "Missing 'repo' in request body"}), 400

    repo = request_json['repo']
    min_severity = request_json.get('min_severity', 'medium')
    max_alerts = request_json.get('max_alerts')
    model = request_json.get('model', 'gemini-flash-latest')
    provider = request_json.get('provider', 'google')

    # Get tokens from Secret Manager
    github_token = get_secret("GITHUB_TOKEN")
    if not github_token:
        return json.dumps({"error": "GITHUB_TOKEN not found"}), 500

    async def run():
        storage = FirestoreStorage()
        analyzer = DependabotAnalyzer(
            repo=repo,
            github_token=github_token,
            llm_model=model,
            llm_provider=provider,
            storage=storage,
            verbose=True
        )
        await analyzer.run(min_severity=min_severity, max_alerts=max_alerts)
        return {"status": "success", "alerts_analyzed": len(analyzer.reports)}

    try:
        result = asyncio.run(run())
        return json.dumps(result), 200
    except Exception as e:
        return json.dumps({"error": str(e)}), 500
