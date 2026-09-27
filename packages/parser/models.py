from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SymbolType(str, Enum):
    MODULE = "MODULE"
    CLASS = "CLASS"
    INTERFACE = "INTERFACE"
    TYPE_ALIAS = "TYPE_ALIAS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    VARIABLE = "VARIABLE"
    ENDPOINT = "ENDPOINT"
    MODEL = "MODEL"


class ChunkType(str, Enum):
    MODULE_OVERVIEW = "MODULE_OVERVIEW"
    CLASS_DECLARATION = "CLASS_DECLARATION"
    FUNCTION_IMPLEMENTATION = "FUNCTION_IMPLEMENTATION"
    METHOD_IMPLEMENTATION = "METHOD_IMPLEMENTATION"
    CODE_BLOCK = "CODE_BLOCK"


class NormalizedImport(BaseModel):
    module: str
    imported_symbols: List[str] = Field(default_factory=list)
    alias: Optional[str] = None
    line_number: int = 1
    is_relative: bool = False


class NormalizedCall(BaseModel):
    caller_name: str
    callee_name: str
    line_number: int = 1
    is_method: bool = False
    context_code: Optional[str] = None


class NormalizedSymbol(BaseModel):
    name: str
    qualified_name: str
    symbol_type: SymbolType
    start_line: int
    end_line: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    parent_name: Optional[str] = None
    decorators: List[str] = Field(default_factory=list)
    calls: List[NormalizedCall] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedFile(BaseModel):
    file_path: str
    language: str
    lines_of_code: int
    size_bytes: int
    content_hash: str
    symbols: List[NormalizedSymbol] = Field(default_factory=list)
    imports: List[NormalizedImport] = Field(default_factory=list)
    exports: List[str] = Field(default_factory=list)


class NormalizedChunk(BaseModel):
    chunk_id: str
    file_path: str
    chunk_type: ChunkType
    start_line: int
    end_line: int
    content: str
    content_hash: str
    context_header: str
    symbol_name: Optional[str] = None
    parent_chunk_id: Optional[str] = None
    imported_dependencies: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
