"""FastAPI backend for the multi-agent code review system."""

import os
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents import get_agent
from agents.planner import planner_agent
from agents.coder import coder_agent
from agents.reviewer import reviewer_agent
from agents.linter import linter_agent
from agents.security import security_agent
from agents.orchestrator import SequentialBuilder, WorkflowBuilder
from agents.orchestrator.builder import ConcurrentBuilder
from agents.orchestrator.magical import MagenticBuilder
from models import CodeFile, ReviewResult, ReviewReport
from tools.code_analysis import analyze_code_structure, parse_python_ast
from tools.security import security_scan


# Global agent instances (lazy initialization)
agents = {}


def get_agent_instance(agent_type: str):
    """Get or create an agent instance."""
    if agent_type not in agents:
        agents[agent_type] = get_agent(agent_type)
    return agents[agent_type]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Initialize agents on startup (lazy)
    yield
    # Cleanup on shutdown
    agents.clear()


# Create FastAPI app
app = FastAPI(
    title="Multi-Agent Code Review API",
    description="API for multi-agent code review and development system",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class AnalyzeRequest(BaseModel):
    """Request model for code analysis."""
    code: str = Field(..., description="Source code to analyze")
    file_path: Optional[str] = Field(None, description="File path if available")
    language: Optional[str] = Field(None, description="Programming language")


class ReviewRequest(BaseModel):
    """Request model for code review."""
    code: str = Field(..., description="Source code to review")
    file_path: Optional[str] = Field(None, description="File path")
    language: str = Field(default="python", description="Programming language")
    review_type: str = Field(default="full", description="Type: full, security, style, correctness")


class GenerateRequest(BaseModel):
    """Request model for code generation."""
    description: str = Field(..., description="Description of code to generate")
    language: str = Field(default="python", description="Target language")
    context: Optional[str] = Field(None, description="Additional context")


class FixRequest(BaseModel):
    """Request model for code fixing."""
    code: str = Field(..., description="Code with issues")
    issues: list = Field(..., description="List of issues to fix")
    language: str = Field(default="python", description="Programming language")


class AgentResponse(BaseModel):
    """Generic agent response."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    agent_type: Optional[str] = None


# API Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Multi-Agent Code Review API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agents": list(agents.keys())}


@app.post("/api/analyze", response_model=AgentResponse)
async def analyze_code(request: AnalyzeRequest):
    """Analyze code structure and complexity."""
    try:
        result = analyze_code_structure(request.code, request.language or "python")
        return AgentResponse(success=True, result=result, agent_type="analyzer")
    except Exception as e:
        return AgentResponse(success=False, error=str(e), agent_type="analyzer")


@app.post("/api/review", response_model=AgentResponse)
async def review_code(request: ReviewRequest):
    """Review code for issues."""
    try:
        agent = get_agent_instance("reviewer")

        # Build review prompt
        prompt = f"""
Review the following {request.language} code{' at ' + request.file_path if request.file_path else ''}.

Focus on: {request.review_type}

```python
{request.code}
```
"""

        result = await agent.run(prompt)

        return AgentResponse(
            success=True,
            result={"review": result.output if hasattr(result, "output") else str(result)},
            agent_type="reviewer"
        )
    except Exception as e:
        return AgentResponse(success=False, error=str(e), agent_type="reviewer")


@app.post("/api/generate", response_model=AgentResponse)
async def generate_code(request: GenerateRequest):
    """Generate code based on description."""
    try:
        agent = get_agent_instance("coder")

        prompt = f"""
Generate {request.language} code based on this description:

{request.description}

{f"Context:\n{request.context}" if request.context else ""}
"""

        result = await agent.run(prompt)

        return AgentResponse(
            success=True,
            result={"code": result.output if hasattr(result, "output") else str(result)},
            agent_type="coder"
        )
    except Exception as e:
        return AgentResponse(success=False, error=str(e), agent_type="coder")


@app.post("/api/fix", response_model=AgentResponse)
async def fix_code(request: FixRequest):
    """Fix code issues."""
    try:
        agent = get_agent_instance("coder")

        issues_text = "\n".join([f"- {issue.get('message', str(issue))}" for issue in request.issues])

        prompt = f"""
Fix the following {request.language} code based on these issues:

Issues:
{issues_text}

```python
{request.code}
```
"""

        result = await agent.run(prompt)

        return AgentResponse(
            success=True,
            result={"fixed_code": result.output if hasattr(result, "output") else str(result)},
            agent_type="coder"
        )
    except Exception as e:
        return AgentResponse(success=False, error=str(e), agent_type="coder")


@app.post("/api/security-scan", response_model=AgentResponse)
async def security_scan_endpoint(request: AnalyzeRequest):
    """Scan code for security issues."""
    try:
        result = security_scan(request.code, request.language or "python")
        return AgentResponse(
            success=True,
            result={"security_issues": result},
            agent_type="security"
        )
    except Exception as e:
        return AgentResponse(success=False, error=str(e), agent_type="security")


@app.post("/api/lint", response_model=AgentResponse)
async def lint_code(request: AnalyzeRequest):
    """Lint code for style issues."""
    try:
        agent = get_agent_instance("linter")

        prompt = f"""
Lint the following {request.language} code and report style issues:

```python
{request.code}
```
"""

        result = await agent.run(prompt)

        return AgentResponse(
            success=True,
            result={"lint_results": result.output if hasattr(result, "output") else str(result)},
            agent_type="linter"
        )
    except Exception as e:
        return AgentResponse(success=False, error=str(e), agent_type="linter")


@app.get("/api/agents")
async def list_agents():
    """List available agents."""
    return {
        "agents": [
            {"name": "planner", "description": "Task planning and decomposition"},
            {"name": "coder", "description": "Code generation and fixing"},
            {"name": "reviewer", "description": "Code review and quality checking"},
            {"name": "linter", "description": "Code style and formatting"},
            {"name": "security", "description": "Security vulnerability detection"},
        ]
    }


@app.post("/api/workflow/sequential")
async def run_sequential_workflow(code: str = "", file_path: str = None):
    """Run sequential workflow: plan -> code -> review."""
    try:
        builder = SequentialBuilder()
        workflow = builder.build()

        context = {"code": code, "file_path": file_path}
        result = await workflow.execute(context)

        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/workflow/concurrent")
async def run_concurrent_workflow(tasks: list):
    """Run concurrent workflow: execute multiple tasks in parallel."""
    try:
        builder = ConcurrentBuilder()
        workflow = builder.build()

        result = await workflow.execute(tasks)

        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/workflow/full")
async def run_full_workflow(code: str = "", file_path: str = None):
    """Run full workflow: plan -> code -> review -> lint -> security."""
    try:
        builder = WorkflowBuilder()
        workflow = builder.build()

        context = {"code": code, "file_path": file_path}
        result = await workflow.execute(context)

        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# File upload endpoint
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and analyze a code file."""
    try:
        content = await file.read()
        code = content.decode("utf-8")

        # Detect language from extension
        ext = os.path.splitext(file.filename)[1].lower()
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".go": "go",
            ".rs": "rust",
        }
        language = lang_map.get(ext, "python")

        # Analyze the code
        result = analyze_code_structure(code, language)

        return {
            "success": True,
            "filename": file.filename,
            "language": language,
            "analysis": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)