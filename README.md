# Dependabot Alert Analyzer

AI-powered tool that analyzes Dependabot security alerts to determine actual exploitability in your codebase. Reduces false positives and helps prioritize security work.

## Features

- 🔍 Fetches Dependabot alerts from GitHub repositories
- 🤖 Uses AI (Gemini/Claude/GPT) to analyze exploitability
- 🎯 Identifies false positives and non-exploitable vulnerabilities
- 📊 Generates detailed reports with reasoning and test cases
- 🚨 Prioritizes alerts based on actual risk

## Architecture

```
Orchestrator
├─ Alert Fetcher (GitHub API)
└─ Deep Analyzer (LLM-powered)
    ├─ Usage analysis
    ├─ Impact assessment
    ├─ Exploitability check
    └─ Test case generation
```

## Quick Start

### 1. Installation

```bash
cd dependabot-analyzer
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file with your API keys:

```bash
python main.py init
```

Edit `.env` and add:
- **GOOGLE_API_KEY**: Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
- **GITHUB_TOKEN**: Create at [GitHub Settings](https://github.com/settings/tokens) (needs `repo` scope)

### 3. Run Analysis

```bash
python main.py analyze owner/repo-name
```

Example with options:
```bash
python main.py analyze owner/repo-name \
  --min-severity high \
  --max-alerts 5 \
  --state open
```

## Usage

### Basic Analysis

```bash
# Analyze all open alerts
python main.py analyze myorg/myrepo

# Only analyze high/critical severity
python main.py analyze myorg/myrepo --min-severity high

# Limit to first 10 alerts
python main.py analyze myorg/myrepo --max-alerts 10
```

### Single Alert Analysis

```bash
# Analyze a specific alert by ID
python main.py analyze-alert myorg/myrepo 7

# The alert ID is the number shown in GitHub's Dependabot alerts
# Example: https://github.com/owner/repo/security/dependabot/7
```

### Advanced Options

```bash
python main.py analyze owner/repo [OPTIONS]

Options:
  --state, -s         Alert state: open, fixed, dismissed, all [default: open]
  --min-severity      Minimum severity: critical, high, medium, low [default: medium]
  --max-alerts, -n    Maximum number of alerts to analyze
  --model, -m         LLM model [default: gemini-2.0-flash-exp]
  --provider, -p      LLM provider: google, anthropic, openai [default: google]
  --save/--no-save    Save reports to ./reports/ [default: save]
```

### Output

The tool generates:

1. **Console output**: Rich formatted analysis with color-coded results
2. **JSON reports**: Detailed reports saved to `./reports/` directory

Example report structure:
```json
{
  "alert_number": 42,
  "package": "lodash",
  "vulnerability_id": "GHSA-xxxx-yyyy-zzzz",
  "is_exploitable": false,
  "confidence": "high",
  "reasoning": "While lodash has a prototype pollution vulnerability...",
  "impact_assessment": "Low - only used in test utilities",
  "code_paths_affected": ["test/utils.js"],
  "recommended_action": "Upgrade during next maintenance cycle",
  "priority": "low"
}
```

## Configuration

### Using Different LLM Providers

**Google Gemini** (default, free via AI Studio):
```bash
python main.py analyze owner/repo --provider google --model gemini-2.0-flash-exp
```

**Anthropic Claude** (requires API key):
```bash
# Add to .env: ANTHROPIC_API_KEY=your_key
python main.py analyze owner/repo --provider anthropic --model claude-haiku-4-5-20251001
```

**OpenAI GPT** (requires API key):
```bash
# Add to .env: OPENAI_API_KEY=your_key
python main.py analyze owner/repo --provider openai --model gpt-4o
```

### Custom Configuration

Edit `config/config.yaml` to customize:
- Default models and providers
- Analysis settings (severity thresholds, context size)
- Output preferences

## Project Structure

```
dependabot-analyzer/
├── src/
│   ├── agents/
│   │   ├── alert_fetcher.py    # GitHub API integration
│   │   └── deep_analyzer.py    # LLM-powered analysis
│   ├── llm/
│   │   └── client.py            # LLM provider wrapper
│   └── orchestrator/
│       └── workflow.py          # Main coordination logic
├── config/
│   └── config.yaml              # Configuration
├── reports/                     # Generated analysis reports
├── requirements.txt
├── main.py                      # CLI entry point
└── README.md
```

## How It Works

1. **Fetch Alerts**: Uses GitHub API to retrieve Dependabot security alerts
2. **Analyze Context**: Examines how the vulnerable dependency is used in your code
3. **LLM Assessment**: AI analyzes:
   - Is the vulnerable code path actually executed?
   - Can attacker input reach the vulnerability?
   - What's the real-world impact in your context?
4. **Generate Report**: Provides exploitability verdict, reasoning, and recommendations

## Development

### Running Tests

```bash
pytest tests/
```

### Adding New Features

The architecture is modular:
- Add new agents in `src/agents/`
- Extend LLM support in `src/llm/client.py`
- Modify workflow in `src/orchestrator/workflow.py`

## Troubleshooting

**"GitHub token not found"**
- Create token at https://github.com/settings/tokens
- Add to `.env`: `GITHUB_TOKEN=your_token`
- Token needs `repo` scope

**"API key not found"**
- Get Google AI Studio key: https://aistudio.google.com/app/apikey
- Add to `.env`: `GOOGLE_API_KEY=your_key`

**Rate limiting**
- Use `--max-alerts` to limit processing
- Add delays between requests in `alert_fetcher.py`

## Roadmap

- [ ] Multi-agent triage layer (fast pre-filtering)
- [ ] Automatic PR creation with fixes
- [ ] Integration with dependency graph analysis
- [ ] Support for more languages/ecosystems
- [ ] Learning from past false positives
- [ ] Web dashboard for results

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.
