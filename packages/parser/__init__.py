from .models import (
    SymbolType,
    ChunkType,
    NormalizedImport,
    NormalizedCall,
    NormalizedSymbol,
    NormalizedFile,
    NormalizedChunk,
)
from .base import BaseParser
from .python_parser import PythonParser
from .javascript_parser import JavaScriptParser
from .chunker import ASTChunker

__all__ = [
    "SymbolType",
    "ChunkType",
    "NormalizedImport",
    "NormalizedCall",
    "NormalizedSymbol",
    "NormalizedFile",
    "NormalizedChunk",
    "BaseParser",
    "PythonParser",
    "JavaScriptParser",
    "ASTChunker",
    "get_parser_for_file",
]


def get_parser_for_file(file_path: str) -> BaseParser:
    """Factory returning the appropriate parser for a given file extension."""
    lang = BaseParser.detect_language(file_path)
    if lang == "python":
        return PythonParser()
    elif lang in ("javascript", "typescript"):
        return JavaScriptParser()
    else:
        # Default to python-style or generic parsing
        return PythonParser()
