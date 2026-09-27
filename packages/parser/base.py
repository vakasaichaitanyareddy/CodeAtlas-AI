from abc import ABC, abstractmethod
import hashlib
import os
from typing import Optional
from .models import NormalizedFile


class BaseParser(ABC):
    """Abstract base class for language-specific AST parsers."""

    @abstractmethod
    def parse_file(self, file_path: str, source_code: str) -> NormalizedFile:
        """Parse source code into a normalized AST intermediate representation."""
        pass

    @staticmethod
    def compute_hash(content: str) -> str:
        """Calculate standard SHA-256 hash of file content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def detect_language(file_path: str) -> str:
        """Detect programming language based on file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".java": "java",
            ".rs": "rust",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".sql": "sql",
            ".sh": "bash",
        }
        return mapping.get(ext, "text")
