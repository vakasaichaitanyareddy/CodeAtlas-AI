import ast
import re
from typing import List, Optional, Any, Dict
from .base import BaseParser
from .models import (
    NormalizedFile,
    NormalizedSymbol,
    NormalizedImport,
    NormalizedCall,
    SymbolType,
)


class CallVisitor(ast.NodeVisitor):
    """AST visitor to extract function and method calls within a function body."""

    def __init__(self, caller_name: str):
        self.caller_name = caller_name
        self.calls: List[NormalizedCall] = []

    def visit_Call(self, node: ast.Call):
        callee_name = None
        is_method = False

        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            # E.g. self.do_something() or service.calculate()
            callee_name = node.func.attr
            is_method = True
        elif isinstance(node.func, ast.Call):
            # Higher-order function call
            callee_name = "<callable>"

        if callee_name:
            self.calls.append(
                NormalizedCall(
                    caller_name=self.caller_name,
                    callee_name=callee_name,
                    line_number=node.lineno,
                    is_method=is_method,
                )
            )
        self.generic_visit(node)


class PythonParser(BaseParser):
    """AST-aware parser for Python source files."""

    ROUTE_DECORATOR_PATTERN = re.compile(r"(router|app)\.(get|post|put|delete|patch|options|head|api_route)", re.IGNORECASE)

    def parse_file(self, file_path: str, source_code: str) -> NormalizedFile:
        lines = source_code.splitlines()
        loc = len(lines)
        size_bytes = len(source_code.encode("utf-8"))
        content_hash = self.compute_hash(source_code)

        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError:
            # Graceful fallback on syntax error in unparseable files
            return NormalizedFile(
                file_path=file_path,
                language="python",
                lines_of_code=loc,
                size_bytes=size_bytes,
                content_hash=content_hash,
                symbols=[],
                imports=[],
                exports=[],
            )

        imports = self._extract_imports(tree)
        symbols = self._extract_symbols(tree, source_code)
        exports = self._extract_exports(tree)

        return NormalizedFile(
            file_path=file_path,
            language="python",
            lines_of_code=loc,
            size_bytes=size_bytes,
            content_hash=content_hash,
            symbols=symbols,
            imports=imports,
            exports=exports,
        )

    def _extract_imports(self, tree: ast.AST) -> List[NormalizedImport]:
        imports: List[NormalizedImport] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        NormalizedImport(
                            module=alias.name,
                            imported_symbols=[],
                            alias=alias.asname,
                            line_number=node.lineno,
                            is_relative=False,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                symbols = [alias.name for alias in node.names]
                is_relative = (node.level or 0) > 0
                imports.append(
                    NormalizedImport(
                        module=module,
                        imported_symbols=symbols,
                        line_number=node.lineno,
                        is_relative=is_relative,
                    )
                )
        return imports

    def _extract_symbols(self, tree: ast.AST, source_code: str) -> List[NormalizedSymbol]:
        symbols: List[NormalizedSymbol] = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                symbols.extend(self._process_class(node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(self._process_function(node, parent_name=None))

        return symbols

    def _process_class(self, node: ast.ClassDef) -> List[NormalizedSymbol]:
        class_symbols: List[NormalizedSymbol] = []
        class_name = node.name
        docstring = ast.get_docstring(node)
        decorators = [self._format_decorator(d) for d in node.decorator_list]

        # Extract base classes
        bases = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            elif isinstance(b, ast.Attribute):
                bases.append(f"{ast.unparse(b.value)}.{b.attr}")

        is_model = any(b in ("Base", "Model", "DeclarativeBase") for b in bases)
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        is_model = True

        symbol_type = SymbolType.MODEL if is_model else SymbolType.CLASS

        class_symbol = NormalizedSymbol(
            name=class_name,
            qualified_name=class_name,
            symbol_type=symbol_type,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            signature=f"class {class_name}({', '.join(bases)})" if bases else f"class {class_name}",
            docstring=docstring,
            parent_name=None,
            decorators=decorators,
            metadata={"bases": bases, "is_model": is_model},
        )
        class_symbols.append(class_symbol)

        # Process class methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_symbol = self._process_function(item, parent_name=class_name)
                class_symbols.append(method_symbol)

        return class_symbols

    def _process_function(
        self, node: Any, parent_name: Optional[str]
    ) -> NormalizedSymbol:
        func_name = node.name
        qualified_name = f"{parent_name}.{func_name}" if parent_name else func_name
        docstring = ast.get_docstring(node)
        decorators = [self._format_decorator(d) for d in node.decorator_list]

        # Signature generation
        args_repr = self._format_arguments(node.args)
        is_async = isinstance(node, ast.AsyncFunctionDef)
        prefix = "async def" if is_async else "def"
        returns_repr = f" -> {ast.unparse(node.returns)}" if getattr(node, "returns", None) else ""
        signature = f"{prefix} {func_name}({args_repr}){returns_repr}"

        # Check for API Endpoint decorators
        is_endpoint = False
        endpoint_meta = {}
        for dec in decorators:
            if self.ROUTE_DECORATOR_PATTERN.search(dec):
                is_endpoint = True
                endpoint_meta = {"route_decorator": dec}
                break

        if parent_name:
            symbol_type = SymbolType.METHOD
        elif is_endpoint:
            symbol_type = SymbolType.ENDPOINT
        else:
            symbol_type = SymbolType.FUNCTION

        # Extract calls within body
        visitor = CallVisitor(caller_name=qualified_name)
        for stmt in node.body:
            visitor.visit(stmt)

        return NormalizedSymbol(
            name=func_name,
            qualified_name=qualified_name,
            symbol_type=symbol_type,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            signature=signature,
            docstring=docstring,
            parent_name=parent_name,
            decorators=decorators,
            calls=visitor.calls,
            metadata={"is_async": is_async, "is_endpoint": is_endpoint, **endpoint_meta},
        )

    def _format_decorator(self, node: ast.AST) -> str:
        try:
            return f"@{ast.unparse(node)}"
        except Exception:
            return "@<unknown>"

    def _format_arguments(self, args: ast.arguments) -> str:
        try:
            return ast.unparse(args)
        except Exception:
            parts = [a.arg for a in args.args]
            return ", ".join(parts)

    def _extract_exports(self, tree: ast.AST) -> List[str]:
        exports: List[str] = []
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    exports.append(elt.value)
        return exports
