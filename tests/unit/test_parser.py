import pytest
from packages.parser import PythonParser, JavaScriptParser, ASTChunker, get_parser_for_file
from packages.parser.models import SymbolType, ChunkType


def test_python_parser_extraction():
    source = '''
import os
from apps.api.database import Base
from apps.api.services import AuthService

class UserService(Base):
    """Handles user authentication and account actions."""
    def __init__(self, db):
        self.db = db

    async def authenticate(self, email: str, secret: str) -> bool:
        """Verify credentials."""
        user = self.db.find_user(email)
        return AuthService.check(user, secret)

@router.get("/api/v1/users")
async def list_users():
    return UserService.get_all()
'''
    parser = PythonParser()
    res = parser.parse_file("apps/api/users.py", source)

    assert res.language == "python"
    assert res.lines_of_code == len(source.splitlines())
    assert len(res.imports) == 3
    assert any(i.module == "os" for i in res.imports)
    assert any("AuthService" in i.imported_symbols for i in res.imports)

    symbols_by_name = {s.qualified_name: s for s in res.symbols}
    assert "UserService" in symbols_by_name
    assert "UserService.__init__" in symbols_by_name
    assert "UserService.authenticate" in symbols_by_name
    assert "list_users" in symbols_by_name

    user_svc = symbols_by_name["UserService"]
    assert user_svc.symbol_type == SymbolType.MODEL # inherits from Base
    assert user_svc.docstring == "Handles user authentication and account actions."
    assert "Base" in user_svc.metadata.get("bases", [])

    auth_method = symbols_by_name["UserService.authenticate"]
    assert auth_method.symbol_type == SymbolType.METHOD
    assert auth_method.parent_name == "UserService"
    assert auth_method.metadata["is_async"] is True
    # Verify calls extracted within method
    callee_names = [c.callee_name for c in auth_method.calls]
    assert "find_user" in callee_names or "check" in callee_names

    list_users = symbols_by_name["list_users"]
    assert list_users.symbol_type == SymbolType.ENDPOINT
    assert list_users.metadata["is_endpoint"] is True


def test_javascript_typescript_parser_extraction():
    ts_source = '''
import React, { useState, useEffect } from 'react';
import { fetchUserData } from '../api/client';

export interface UserProfile {
    id: string;
    email: string;
}

export class DashboardService extends BaseService {
    async loadProfile(userId: string): Promise<UserProfile> {
        return fetchUserData(userId);
    }
}

export const useUser = (userId: string) => {
    const data = fetchUserData(userId);
    return data;
};
'''
    parser = JavaScriptParser()
    res = parser.parse_file("apps/web/src/hooks/useUser.ts", ts_source)

    assert res.language == "typescript"
    symbols_by_name = {s.qualified_name: s for s in res.symbols}
    assert "UserProfile" in symbols_by_name
    assert symbols_by_name["UserProfile"].symbol_type == SymbolType.INTERFACE

    assert "DashboardService" in symbols_by_name
    assert symbols_by_name["DashboardService"].symbol_type == SymbolType.CLASS

    assert "DashboardService.loadProfile" in symbols_by_name
    assert symbols_by_name["DashboardService.loadProfile"].symbol_type == SymbolType.METHOD

    assert "useUser" in symbols_by_name
    assert symbols_by_name["useUser"].symbol_type == SymbolType.FUNCTION


def test_javascript_parser_edge_cases_braces_in_strings_and_comments():
    """Verify that braces in string literals, template strings, and comments do not break block boundaries."""
    source = '''
export class SafeParser {
    formatTemplate(value: string): string {
        const fakeBrace = "}"; // contains closing brace
        const template = `Hello ${value} {test}`;
        // Another comment with { and } braces
        return template + fakeBrace;
    }

    getNextItem(): number {
        return 100;
    }
}
'''
    parser = JavaScriptParser()
    res = parser.parse_file("src/SafeParser.ts", source)

    symbols_by_name = {s.qualified_name: s for s in res.symbols}
    assert "SafeParser" in symbols_by_name
    assert "SafeParser.formatTemplate" in symbols_by_name
    assert "SafeParser.getNextItem" in symbols_by_name

    fmt_method = symbols_by_name["SafeParser.formatTemplate"]
    assert fmt_method.symbol_type == SymbolType.METHOD
    assert fmt_method.start_line == 3
    # Ensure formatTemplate does not terminate prematurely at fakeBrace line
    assert fmt_method.end_line >= 8

    next_method = symbols_by_name["SafeParser.getNextItem"]
    assert next_method.symbol_type == SymbolType.METHOD
    assert next_method.start_line == 10
    assert next_method.end_line == 12


def test_ast_chunker_hierarchical_linking():
    source = '''
import sys

class Engine:
    """Core physics engine."""
    def start(self):
        return True

def compute():
    return 42
'''
    parser = PythonParser()
    parsed = parser.parse_file("core/engine.py", source)

    chunker = ASTChunker()
    chunks = chunker.chunk_file(parsed, source)

    assert len(chunks) >= 4
    chunk_types = [c.chunk_type for c in chunks]
    assert ChunkType.MODULE_OVERVIEW in chunk_types
    assert ChunkType.CLASS_DECLARATION in chunk_types
    assert ChunkType.METHOD_IMPLEMENTATION in chunk_types
    assert ChunkType.FUNCTION_IMPLEMENTATION in chunk_types

    # Verify hierarchical parent links
    class_chunk = next(c for c in chunks if c.chunk_type == ChunkType.CLASS_DECLARATION)
    method_chunk = next(c for c in chunks if c.chunk_type == ChunkType.METHOD_IMPLEMENTATION)
    module_chunk = next(c for c in chunks if c.chunk_type == ChunkType.MODULE_OVERVIEW)

    assert class_chunk.parent_chunk_id == module_chunk.chunk_id
    assert method_chunk.parent_chunk_id == class_chunk.chunk_id
    assert method_chunk.start_line > 0 and method_chunk.end_line >= method_chunk.start_line
