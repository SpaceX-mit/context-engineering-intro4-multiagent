# Multi-Agent Code Development System

A production-ready multi-agent AI system for code development, review, quality assessment, and automated fixes.

## Features

- **Code Generation**: Describe requirements and get working code with proper structure
- **Code Review**: Automated analysis of code quality, correctness, and security
- **Security Scanning**: Detect potential security vulnerabilities using bandit patterns
- **Style Checking**: Lint and format code automatically
- **Auto-Fix**: Let AI fix detected issues automatically
- **WebUI**: Interactive Gradio interface for all operations
- **Multi-Agent Collaboration**: 5+ specialized agents working together

## Agents

| Agent | Responsibility |
|-------|---------------|
| Planner | Task decomposition and planning |
| Coder | Code generation and fixing |
| Reviewer | Code quality assessment |
| Linter | Code style and formatting |
| Security | Security vulnerability detection |

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Configure your API key in .env (LLM_API_KEY)
```

## Usage

### CLI

```bash
# Review a file
python -m multi_agent_code_review.cli review path/to/file.py

# Review multiple files
python -m multi_agent_code_review.cli review file1.py file2.py

# Review with auto-fix
python -m multi_agent_code_review.cli review --auto-fix path/to/file.py

# Show help
python -m multi_agent_code_review.cli --help
```

### WebUI

```bash
# Run the WebUI (Gradio interface)
python -m webui.app

# Or run with custom settings
python -m webui.app --port 7860 --host 0.0.0.0 --share

# Run with API backend
python -m webui.app --mode api
```

Then open http://localhost:7860 in your browser.

### API Server

```bash
# Run FastAPI backend
uvicorn webui.api:app --host 0.0.0.0 --port 8000

# API endpoints available at:
# - GET  /health - Health check
# - POST /api/analyze - Analyze code structure
# - POST /api/review - Review code
# - POST /api/generate - Generate code
# - POST /api/fix - Fix code issues
# - POST /api/security-scan - Security scanning
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     WebUI (Gradio) / API (FastAPI)              │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Multi-Agent Orchestrator                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Planner   │  │    Coder    │  │  Reviewer   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │   Linter   │  │  Security   │                              │
│  └─────────────┘  └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Code Analysis Tools                          │
│  - AST parsing, complexity analysis, security patterns           │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration

Edit `.env` to configure:

- `LLM_API_KEY`: Your API key (required)
- `LLM_PROVIDER`: LLM provider (openai, anthropic, etc.)
- `LLM_MODEL`: Model to use (default: gpt-4o-mini)
- `MAX_ITERATIONS`: Maximum review iterations
- `WEBUI_PORT`: WebUI port (default: 7860)
- `WEBUI_HOST`: WebUI host (default: 0.0.0.0)
- `SANDBOX_ENABLED`: Enable sandbox for code execution

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_webui.py -v
```

## License

MIT