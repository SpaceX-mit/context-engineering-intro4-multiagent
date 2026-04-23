"""Chat component for Gradio interface."""

from typing import List, Tuple, Optional

try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    gr = None
    GRADIO_AVAILABLE = False


def create_chat_component() -> Tuple:
    """
    Create the chat interface component.

    Returns:
        Tuple of (chatbot, textbox, send_button)
    """
    if gr is None:
        raise ImportError("Gradio is not installed. Run: pip install gradio")

    chatbot = gr.Chatbot(
        height=500,
        label="Agent Chat",
        show_copy_button=True,
    )

    with gr.Row():
        msg = gr.Textbox(
            placeholder="Enter your request... (e.g., 'Create a calculator class' or 'Review my code')",
            scale=5,
            show_label=False,
        )
        send_btn = gr.Button("Send", scale=1, variant="primary")

    return chatbot, msg, send_btn


def add_message(
    message: str,
    history: List[Tuple[str, str]],
    response: str,
) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Add a message to the chat history.

    Args:
        message: User message
        history: Current chat history
        response: Agent response

    Returns:
        Tuple of (empty message, updated history)
    """
    if message:
        history.append((message, response))
    return "", history


def clear_chat() -> List:
    """Clear the chat history."""
    return []


class ChatManager:
    """Manager for chat interactions."""

    def __init__(self):
        self.history: List[Tuple[str, str]] = []
        self.agent = None

    def set_agent(self, agent):
        """Set the agent to use for chat."""
        self.agent = agent

    async def get_response(self, message: str) -> str:
        """
        Get response from the agent.

        Args:
            message: User message

        Returns:
            Agent response
        """
        if self.agent is None:
            return "Agent not configured. Please set up the agent first."

        try:
            # This would be async in real implementation
            result = await self.agent.run(message)
            return result.output if hasattr(result, "output") else str(result)
        except Exception as e:
            return f"Error: {str(e)}"

    def get_history(self) -> List[Tuple[str, str]]:
        """Get the chat history."""
        return self.history

    def clear_history(self):
        """Clear the chat history."""
        self.history = []


# Global chat manager instance
chat_manager = ChatManager()
