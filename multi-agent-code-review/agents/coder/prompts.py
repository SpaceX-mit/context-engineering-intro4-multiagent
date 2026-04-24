"""Prompts for the Coder Agent."""

CODER_PROMPT = """You are the Coder Agent for the AI Coder system.

Your role is to:
1. Implement code based on plans
2. Write clean, working code
3. Follow best practices
4. Include basic error handling

## Guidelines
1. Read the plan carefully before coding
2. Start with a basic implementation
3. Add error handling as you go
4. Keep code simple and readable
5. Write code that can be tested

## Output Format
Always output:
1. Brief description of what was implemented
2. The code with proper formatting
3. Any notes or next steps
"""

HELLO_WORLD_TEMPLATE = '''def hello_world():
    """Print hello world message."""
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
'''

CALCULATOR_TEMPLATE = '''class Calculator:
    """Basic calculator class."""

    def __init__(self):
        self.result = 0

    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        self.result = a + b
        return self.result

    def subtract(self, a: float, b: float) -> float:
        """Subtract two numbers."""
        self.result = a - b
        return self.result

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        self.result = a * b
        return self.result

    def divide(self, a: float, b: float) -> float:
        """Divide two numbers."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        self.result = a / b
        return self.result
'''
