"""File browser component for Gradio interface."""

from typing import List, Tuple

try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    gr = None
    GRADIO_AVAILABLE = False


def create_file_browser_component(
    root_path: str = ".",
) -> Tuple:
    """
    Create the file browser component.

    Args:
        root_path: Root directory to browse

    Returns:
        Tuple of (file_explorer, path_input, refresh_button)
    """
    if gr is None:
        raise ImportError("Gradio is not installed. Run: pip install gradio")

    with gr.Column():
        gr.Markdown("### Project Files")

        file_explorer = gr.FileExplorer(
            root_dir=root_path,
            label="Files",
            height=300,
            file_count="multiple",
        )

        with gr.Row():
            path_input = gr.Textbox(
                placeholder="Enter file path...",
                scale=4,
            )
            refresh_btn = gr.Button("Refresh", scale=1)

        with gr.Row():
            new_file_btn = gr.Button("New File", variant="secondary")
            delete_btn = gr.Button("Delete", variant="stop")

    return file_explorer, path_input, refresh_btn, new_file_btn, delete_btn


def list_project_files(root_path: str, extensions: List[str] = None) -> List[str]:
    """
    List files in a project directory.

    Args:
        root_path: Root directory to scan
        extensions: List of file extensions to include (e.g., ['.py', '.js'])

    Returns:
        List of file paths
    """
    import os

    if extensions is None:
        extensions = [".py", ".js", ".ts", ".html", ".css", ".json", ".md"]

    files = []
    for root, dirs, filenames in os.walk(root_path):
        # Skip hidden directories and common non-source directories
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".") and d not in ["__pycache__", "node_modules", "venv"]
        ]

        for filename in filenames:
            if any(filename.endswith(ext) for ext in extensions):
                filepath = os.path.join(root, filename)
                files.append(filepath)

    return sorted(files)


def get_file_tree(root_path: str) -> dict:
    """
    Get a tree structure of files.

    Args:
        root_path: Root directory

    Returns:
        Dictionary representing file tree
    """
    import os

    tree = {"name": os.path.basename(root_path) or root_path, "type": "folder", "children": []}

    try:
        for item in sorted(os.listdir(root_path)):
            if item.startswith("."):
                continue

            item_path = os.path.join(root_path, item)
            if os.path.isdir(item_path):
                if item not in ["__pycache__", "node_modules", "venv", ".git"]:
                    subtree = get_file_tree(item_path)
                    tree["children"].append(subtree)
            else:
                tree["children"].append({"name": item, "type": "file"})
    except PermissionError:
        pass

    return tree


class FileBrowserManager:
    """Manager for file browser operations."""

    def __init__(self, root_path: str = "."):
        self.root_path = root_path
        self.selected_files: List[str] = []

    def get_files(self) -> List[str]:
        """Get list of files in the project."""
        return list_project_files(self.root_path)

    def select_file(self, filepath: str) -> str:
        """Select a file and return its content."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"# Error: {e}"

    def create_file(self, filepath: str, content: str = "") -> str:
        """Create a new file."""
        import os

        try:
            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Created: {filepath}"
        except Exception as e:
            return f"Error: {e}"

    def delete_file(self, filepath: str) -> str:
        """Delete a file."""
        import os

        try:
            os.remove(filepath)
            return f"Deleted: {filepath}"
        except Exception as e:
            return f"Error: {e}"


# Global file browser manager
file_browser_manager = FileBrowserManager()
