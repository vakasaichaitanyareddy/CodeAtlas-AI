import os
import hashlib
from typing import List, Dict, Optional, Generator
from packages.parser.base import BaseParser


class ScannedFile:
    def __init__(self, rel_path: str, abs_path: str, size_bytes: int, language: str, content_hash: str, content: str):
        self.rel_path = rel_path.replace("\\", "/")
        self.abs_path = abs_path
        self.size_bytes = size_bytes
        self.language = language
        self.content_hash = content_hash
        self.content = content


class RepositoryScanner:
    """Scans and discovers source files in a repository directory with ignore and binary filtering."""

    DEFAULT_IGNORES = {
        ".git",
        ".github",
        ".venv",
        "venv",
        "env",
        "node_modules",
        ".next",
        "dist",
        "build",
        "out",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".turbo",
        ".vscode",
        ".idea",
        "coverage",
        ".coverage",
    }

    BINARY_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
        ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
        ".exe", ".dll", ".so", ".dylib", ".bin",
        ".woff", ".woff2", ".ttf", ".eot",
        ".mp3", ".mp4", ".wav", ".avi", ".mov",
        ".pyc", ".pyd", ".pyo", ".class",
        ".db", ".sqlite", ".sqlite3",
    }

    def __init__(self, max_file_size_bytes: int = 1_048_576):  # 1 MB limit
        self.max_file_size_bytes = max_file_size_bytes

    def scan_directory(self, root_dir: str) -> List[ScannedFile]:
        """Traverse directory and return scanned valid source files."""
        scanned_files: List[ScannedFile] = []
        root_dir = os.path.abspath(root_dir)

        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Prune ignored directories in-place
            dirnames[:] = [d for d in dirnames if d not in self.DEFAULT_IGNORES and not d.startswith(".")]

            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in self.BINARY_EXTENSIONS:
                    continue

                abs_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(abs_path, root_dir).replace("\\", "/")

                try:
                    file_size = os.path.getsize(abs_path)
                    if file_size > self.max_file_size_bytes:
                        continue

                    # Binary content heuristic check
                    with open(abs_path, "rb") as f:
                        header = f.read(1024)
                        if b"\x00" in header:
                            continue

                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()

                    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                    language = BaseParser.detect_language(rel_path)

                    scanned_files.append(
                        ScannedFile(
                            rel_path=rel_path,
                            abs_path=abs_path,
                            size_bytes=file_size,
                            language=language,
                            content_hash=content_hash,
                            content=content,
                        )
                    )
                except (IOError, OSError):
                    continue

        return scanned_files
