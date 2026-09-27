from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"


class RepositoryStatus(str, Enum):
    PENDING = "PENDING"
    CLONING = "CLONING"
    PARSING = "PARSING"
    INDEXING = "INDEXING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


class IndexJobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class SymbolType(str, Enum):
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    INTERFACE = "INTERFACE"
    TYPE_ALIAS = "TYPE_ALIAS"
    VARIABLE = "VARIABLE"
    IMPORT = "IMPORT"


class GraphNodeType(str, Enum):
    FILE = "FILE"
    MODULE = "MODULE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    ENDPOINT = "ENDPOINT"
    MODEL = "MODEL"


class GraphEdgeType(str, Enum):
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    INHERITS = "INHERITS"
    IMPLEMENTS = "IMPLEMENTS"
    DEPENDS_ON = "DEPENDS_ON"
    EXPOSES = "EXPOSES"
    QUERIES = "QUERIES"


class QueryIntent(str, Enum):
    FACTUAL_CODE_QUERY = "FACTUAL_CODE_QUERY"
    SYMBOL_QUERY = "SYMBOL_QUERY"
    ARCHITECTURE_QUERY = "ARCHITECTURE_QUERY"
    DEPENDENCY_QUERY = "DEPENDENCY_QUERY"
    IMPACT_QUERY = "IMPACT_QUERY"
    DEBUGGING_QUERY = "DEBUGGING_QUERY"
    SECURITY_QUERY = "SECURITY_QUERY"
    DOCUMENTATION_QUERY = "DOCUMENTATION_QUERY"
    GENERAL_QUERY = "GENERAL_QUERY"


class SecuritySeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SecurityCategory(str, Enum):
    SECRET = "SECRET"
    SQL_INJECTION = "SQL_INJECTION"
    COMMAND_INJECTION = "COMMAND_INJECTION"
    DESERIALIZATION = "DESERIALIZATION"
    CRYPTO = "CRYPTO"
    AUTH = "AUTH"


class Citation(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    symbol_name: Optional[str] = None
    commit_sha: Optional[str] = None
    snippet: Optional[str] = None
