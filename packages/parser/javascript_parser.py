import re
from typing import List, Optional, Dict, Any, Tuple
from .base import BaseParser
from .models import (
    NormalizedFile,
    NormalizedSymbol,
    NormalizedImport,
    NormalizedCall,
    SymbolType,
)


class JavaScriptParser(BaseParser):
    """AST & lexical parser for JavaScript and TypeScript source files."""

    # Regex patterns for imports
    IMPORT_ES6_RE = re.compile(
        r"""import\s+(?:(?P<default>[a-zA-Z_$][a-zA-Z0-9_$]*)|(?:(?P<namespace>\*\s+as\s+[a-zA-Z_$][a-zA-Z0-9_$]*))|(?:\{(?P<named>[^}]+)\}))(?:\s*,\s*(?:\{(?P<named2>[^}]+)\}))?\s+from\s+['"](?P<module>[^'"]+)['"]""",
        re.MULTILINE,
    )
    IMPORT_REQUIRE_RE = re.compile(
        r"""(?:const|let|var)\s+(?:\{(?P<named>[^}]+)\}|(?P<default>[a-zA-Z_$][a-zA-Z0-9_$]*))\s*=\s*require\(['"](?P<module>[^'"]+)['"]\)"""
    )

    # Class pattern: class Name [extends Base] {
    CLASS_RE = re.compile(
        r"""(?:export\s+)?(?:default\s+)?class\s+(?P<name>[a-zA-Z_$][a-zA-Z0-9_$]*)(?:\s+extends\s+(?P<base>[a-zA-Z0-9_$.]+))?\s*\{"""
    )

    # Interface pattern (TS)
    INTERFACE_RE = re.compile(
        r"""(?:export\s+)?interface\s+(?P<name>[a-zA-Z_$][a-zA-Z0-9_$]*)(?:\s+extends\s+(?P<base>[a-zA-Z0-9_$.]+))?\s*\{"""
    )

    # Type alias pattern (TS)
    TYPE_RE = re.compile(
        r"""(?:export\s+)?type\s+(?P<name>[a-zA-Z_$][a-zA-Z0-9_$]*)(?:<[^>]+>)?\s*="""
    )

    # Function declarations: [export] [async] function name(args) [: type] {
    FUNCTION_RE = re.compile(
        r"""(?:export\s+)?(?:default\s+)?(?P<async>async\s+)?function\s+(?P<name>[a-zA-Z_$][a-zA-Z0-9_$]*)\s*\((?P<args>[^)]*)\)"""
    )

    # Variable arrow functions: [export] const name = [async] (args) => {
    ARROW_RE = re.compile(
        r"""(?:export\s+)?(?:const|let|var)\s+(?P<name>[a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?P<async>async\s+)?(?:\((?P<args>[^)]*)\)|(?P<single_arg>[a-zA-Z_$][a-zA-Z0-9_$]*))\s*(?::\s*[^=]+)?\s*=>"""
    )

    # Method inside class: [async] methodName(args) [: type] {
    METHOD_RE = re.compile(
        r"""^\s*(?:(?:public|private|protected|static|override)\s+)*(?P<async>async\s+)?(?P<name>[a-zA-Z_$][a-zA-Z0-9_$]*)\s*\((?P<args>[^)]*)\)\s*(?::\s*[^{]+)?\s*\{"""
    )

    # Call pattern
    CALL_RE = re.compile(
        r"""(?P<target>[a-zA-Z_$][a-zA-Z0-9_$]*(?:\.[a-zA-Z_$][a-zA-Z0-9_$]*)*)\s*\("""
    )

    def parse_file(self, file_path: str, source_code: str) -> NormalizedFile:
        language = "typescript" if file_path.endswith((".ts", ".tsx")) else "javascript"
        lines = source_code.splitlines()
        loc = len(lines)
        size_bytes = len(source_code.encode("utf-8"))
        content_hash = self.compute_hash(source_code)

        imports = self._extract_imports(lines, source_code)
        symbols = self._extract_symbols(lines, source_code)
        exports = self._extract_exports(lines)

        return NormalizedFile(
            file_path=file_path,
            language=language,
            lines_of_code=loc,
            size_bytes=size_bytes,
            content_hash=content_hash,
            symbols=symbols,
            imports=imports,
            exports=exports,
        )

    def _extract_imports(self, lines: List[str], full_text: str) -> List[NormalizedImport]:
        imports: List[NormalizedImport] = []

        # ES6 imports
        for match in self.IMPORT_ES6_RE.finditer(full_text):
            module = match.group("module")
            named_symbols = []
            if match.group("default"):
                named_symbols.append(match.group("default").strip())
            if match.group("named"):
                named_symbols.extend([s.strip().split(" as ")[0].strip() for s in match.group("named").split(",") if s.strip()])
            if match.group("named2"):
                named_symbols.extend([s.strip().split(" as ")[0].strip() for s in match.group("named2").split(",") if s.strip()])

            # Find line number
            start_pos = match.start()
            line_no = full_text.count("\n", 0, start_pos) + 1

            imports.append(
                NormalizedImport(
                    module=module,
                    imported_symbols=named_symbols,
                    line_number=line_no,
                    is_relative=module.startswith("."),
                )
            )

        # CommonJS require
        for idx, line in enumerate(lines, start=1):
            for match in self.IMPORT_REQUIRE_RE.finditer(line):
                module = match.group("module")
                named_symbols = []
                if match.group("default"):
                    named_symbols.append(match.group("default").strip())
                if match.group("named"):
                    named_symbols.extend([s.strip() for s in match.group("named").split(",") if s.strip()])
                imports.append(
                    NormalizedImport(
                        module=module,
                        imported_symbols=named_symbols,
                        line_number=idx,
                        is_relative=module.startswith("."),
                    )
                )

        return imports

    def _extract_symbols(self, lines: List[str], full_text: str) -> List[NormalizedSymbol]:
        symbols: List[NormalizedSymbol] = []
        i = 0
        total_lines = len(lines)

        while i < total_lines:
            line = lines[i]
            line_no = i + 1

            # 1. Classes
            class_match = self.CLASS_RE.search(line)
            if class_match:
                class_name = class_match.group("name")
                base = class_match.group("base")
                end_line = self._find_closing_brace(lines, i)
                body_lines = lines[i : end_line]
                calls = self._extract_calls(body_lines, caller_name=class_name, start_line_offset=line_no)

                class_sym = NormalizedSymbol(
                    name=class_name,
                    qualified_name=class_name,
                    symbol_type=SymbolType.CLASS,
                    start_line=line_no,
                    end_line=end_line,
                    signature=f"class {class_name}" + (f" extends {base}" if base else ""),
                    docstring=self._extract_preceding_docstring(lines, i),
                    parent_name=None,
                    calls=calls,
                    metadata={"base_class": base} if base else {},
                )
                symbols.append(class_sym)

                # Process methods within the class
                method_symbols = self._extract_class_methods(lines, i, end_line, class_name)
                symbols.extend(method_symbols)
                i = end_line
                continue

            # 2. Interfaces (TypeScript)
            interface_match = self.INTERFACE_RE.search(line)
            if interface_match:
                iface_name = interface_match.group("name")
                end_line = self._find_closing_brace(lines, i)
                symbols.append(
                    NormalizedSymbol(
                        name=iface_name,
                        qualified_name=iface_name,
                        symbol_type=SymbolType.INTERFACE,
                        start_line=line_no,
                        end_line=end_line,
                        signature=f"interface {iface_name}",
                        docstring=self._extract_preceding_docstring(lines, i),
                        parent_name=None,
                    )
                )
                i = end_line
                continue

            # 3. Type aliases (TypeScript)
            type_match = self.TYPE_RE.search(line)
            if type_match:
                type_name = type_match.group("name")
                symbols.append(
                    NormalizedSymbol(
                        name=type_name,
                        qualified_name=type_name,
                        symbol_type=SymbolType.TYPE_ALIAS,
                        start_line=line_no,
                        end_line=line_no,
                        signature=f"type {type_name}",
                        docstring=self._extract_preceding_docstring(lines, i),
                        parent_name=None,
                    )
                )
                i += 1
                continue

            # 4. Standalone functions
            func_match = self.FUNCTION_RE.search(line)
            if func_match:
                func_name = func_match.group("name")
                args = func_match.group("args") or ""
                is_async = bool(func_match.group("async"))
                end_line = self._find_closing_brace(lines, i)
                body_lines = lines[i : end_line]
                calls = self._extract_calls(body_lines, caller_name=func_name, start_line_offset=line_no)

                symbols.append(
                    NormalizedSymbol(
                        name=func_name,
                        qualified_name=func_name,
                        symbol_type=SymbolType.FUNCTION,
                        start_line=line_no,
                        end_line=end_line,
                        signature=f"{'async ' if is_async else ''}function {func_name}({args.strip()})",
                        docstring=self._extract_preceding_docstring(lines, i),
                        parent_name=None,
                        calls=calls,
                        metadata={"is_async": is_async},
                    )
                )
                i = end_line
                continue

            # 5. Arrow functions
            arrow_match = self.ARROW_RE.search(line)
            if arrow_match:
                func_name = arrow_match.group("name")
                args = arrow_match.group("args") or arrow_match.group("single_arg") or ""
                is_async = bool(arrow_match.group("async"))
                end_line = self._find_closing_brace(lines, i) if "{" in line else line_no
                body_lines = lines[i : end_line]
                calls = self._extract_calls(body_lines, caller_name=func_name, start_line_offset=line_no)

                symbols.append(
                    NormalizedSymbol(
                        name=func_name,
                        qualified_name=func_name,
                        symbol_type=SymbolType.FUNCTION,
                        start_line=line_no,
                        end_line=end_line,
                        signature=f"const {func_name} = {'async ' if is_async else ''}({args.strip()}) =>",
                        docstring=self._extract_preceding_docstring(lines, i),
                        parent_name=None,
                        calls=calls,
                        metadata={"is_async": is_async, "is_arrow": True},
                    )
                )
                i = end_line
                continue

            i += 1

        return symbols

    def _extract_class_methods(
        self, lines: List[str], class_start_idx: int, class_end_line: int, class_name: str
    ) -> List[NormalizedSymbol]:
        methods: List[NormalizedSymbol] = []
        i = class_start_idx + 1

        while i < class_end_line - 1:
            line = lines[i]
            line_no = i + 1
            method_match = self.METHOD_RE.search(line)

            if method_match:
                method_name = method_match.group("name")
                if method_name not in ("if", "for", "while", "switch", "catch"):
                    args = method_match.group("args") or ""
                    is_async = bool(method_match.group("async"))
                    end_line = self._find_closing_brace(lines, i)
                    body_lines = lines[i : end_line]
                    qualified_name = f"{class_name}.{method_name}"
                    calls = self._extract_calls(body_lines, caller_name=qualified_name, start_line_offset=line_no)

                    methods.append(
                        NormalizedSymbol(
                            name=method_name,
                            qualified_name=qualified_name,
                            symbol_type=SymbolType.METHOD,
                            start_line=line_no,
                            end_line=end_line,
                            signature=f"{'async ' if is_async else ''}{method_name}({args.strip()})",
                            docstring=self._extract_preceding_docstring(lines, i),
                            parent_name=class_name,
                            calls=calls,
                            metadata={"is_async": is_async},
                        )
                    )
                    i = end_line
                    continue
            i += 1

        return methods

    def _extract_calls(self, body_lines: List[str], caller_name: str, start_line_offset: int) -> List[NormalizedCall]:
        calls: List[NormalizedCall] = []
        for idx, line in enumerate(body_lines):
            line_no = start_line_offset + idx
            for match in self.CALL_RE.finditer(line):
                target = match.group("target")
                # Filter out language keywords like if, for, while, switch
                if target in ("if", "for", "while", "switch", "catch", "function", "return"):
                    continue
                parts = target.split(".")
                callee_name = parts[-1]
                is_method = len(parts) > 1
                calls.append(
                    NormalizedCall(
                        caller_name=caller_name,
                        callee_name=callee_name,
                        line_number=line_no,
                        is_method=is_method,
                    )
                )
        return calls

    def _find_closing_brace(self, lines: List[str], start_idx: int) -> int:
        depth = 0
        found_open = False
        in_string: Optional[str] = None
        escaped = False

        for idx in range(start_idx, len(lines)):
            line = lines[idx]
            i = 0
            n = len(line)
            while i < n:
                ch = line[i]
                if escaped:
                    escaped = False
                    i += 1
                    continue

                if ch == "\\":
                    escaped = True
                    i += 1
                    continue

                if in_string:
                    if ch == in_string:
                        in_string = None
                else:
                    if ch in ('"', "'", "`"):
                        in_string = ch
                    elif ch == "/" and i + 1 < n and line[i + 1] == "/":
                        # Single-line comment, rest of line is ignored
                        break
                    elif ch == "{":
                        depth += 1
                        found_open = True
                    elif ch == "}":
                        depth -= 1
                        if found_open and depth == 0:
                            return idx + 1
                i += 1
        return len(lines)

    def _extract_preceding_docstring(self, lines: List[str], idx: int) -> Optional[str]:
        if idx == 0:
            return None
        prev_idx = idx - 1
        doc_lines = []

        if lines[prev_idx].strip().endswith("*/"):
            while prev_idx >= 0:
                line = lines[prev_idx].strip()
                doc_lines.insert(0, line)
                if line.startswith("/*") or line.startswith("/**"):
                    break
                prev_idx -= 1
            return "\n".join(doc_lines)
        return None

    def _extract_exports(self, lines: List[str]) -> List[str]:
        exports: List[str] = []
        export_re = re.compile(r"""export\s+(?:default\s+)?(?:class|function|const|let|var|type|interface)\s+(?P<name>[a-zA-Z_$][a-zA-Z0-9_$]*)""")
        for line in lines:
            m = export_re.search(line)
            if m:
                exports.append(m.group("name"))
        return exports
