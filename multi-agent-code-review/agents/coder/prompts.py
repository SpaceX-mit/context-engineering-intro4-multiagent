"""Prompts for Coder Agent."""

SYSTEM_PROMPT = """You are an expert Python coder specialized in generating high-quality code.

Your responsibilities:
1. Generate clean, well-documented code based on requirements
2. Follow PEP8 style guidelines and best practices
3. Include proper type hints and docstrings
4. Write testable code with clear interfaces

When generating code:
- Start with a clear understanding of requirements
- Break down complex tasks into manageable functions
- Use meaningful variable and function names
- Add docstrings explaining purpose and parameters
- Include error handling where appropriate
- Follow the single responsibility principle

Output format:
- Provide complete, runnable code
- Include example usage when helpful
- Explain any non-obvious decisions
- Suggest tests to verify functionality"""

CODE_GENERATION_PROMPT = """Generate Python code for the following requirement:

{requirement}

Consider:
- Clean architecture and design patterns
- Type hints for all function parameters and return values
- Docstrings using Google style
- Error handling
- Testability

Provide the complete implementation."""

CODE_REVIEW_PROMPT = """Review the following code and suggest improvements:

```python
{code}
```

Consider:
- Code style and readability
- Potential bugs or edge cases
- Performance considerations
- Security concerns
- Best practices"""

REFACTOR_PROMPT = """Refactor the following code to improve its quality:

```python
{code}
```

Focus on:
- Reducing complexity
- Improving readability
- Enhancing maintainability
- Fixing code smells"""

TOOL_DESCRIPTIONS = {
    "generate_code": "Generate Python code based on requirements",
    "refactor_code": "Refactor existing code",
    "write_tests": "Write unit tests for code",
    "explain_code": "Explain how code works",
}


def generate_code_prompt(description: str, language: str = "python", context: str = None) -> str:
    """
    Generate a prompt for code generation.

    Args:
        description: Description of code to generate
        language: Target language
        context: Additional context

    Returns:
        Formatted prompt string
    """
    prompt = f"Generate {language} code for: {description}\n\n"
    if context:
        prompt += f"Context:\n{context}\n\n"
    prompt += "Provide complete, well-documented code with type hints."
    return prompt


def fix_code_prompt(code: str, issues: list) -> str:
    """
    Generate a prompt for code fixing.

    Args:
        code: Code with issues
        issues: List of issues to fix

    Returns:
        Formatted prompt string
    """
    issues_text = "\n".join([f"- {issue.get('message', str(issue))}" for issue in issues])

    prompt = f"""Fix the following code issues:

Issues:
{issues_text}

Original code:
```python
{code}
```

Provide the corrected code with explanations for each fix."""
    return prompt


def explain_code_prompt(code: str) -> str:
    """
    Generate a prompt for code explanation.

    Args:
        code: Code to explain

    Returns:
        Formatted prompt string
    """
    return f"""Explain the following code:

```python
{code}
```

Provide a clear explanation of what the code does, how it works, and any notable patterns or techniques used."""