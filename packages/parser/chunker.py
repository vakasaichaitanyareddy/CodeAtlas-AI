import hashlib
from typing import List, Dict, Optional
from .models import NormalizedFile, NormalizedSymbol, NormalizedChunk, ChunkType, SymbolType


class ASTChunker:
    """Hierarchical semantic chunker generating AST-aware code chunks with parent-child context links."""

    def __init__(self, max_chunk_lines: int = 150):
        self.max_chunk_lines = max_chunk_lines

    def chunk_file(self, parsed_file: NormalizedFile, source_code: str) -> List[NormalizedChunk]:
        """Convert a NormalizedFile and its source code into a hierarchical list of NormalizedChunks."""
        chunks: List[NormalizedChunk] = []
        source_lines = source_code.splitlines()
        file_path = parsed_file.file_path
        total_lines = len(source_lines)

        if total_lines == 0:
            return chunks

        # Collect summary of imports for contextual injection into child chunks
        imported_modules = [imp.module for imp in parsed_file.imports]
        import_summary_str = ", ".join(imported_modules[:8]) if imported_modules else "none"

        # 1. Module Overview Chunk
        module_chunk_id = f"{file_path}::module_overview"
        first_symbol_line = min((s.start_line for s in parsed_file.symbols), default=min(30, total_lines))
        overview_end_line = max(1, min(first_symbol_line, min(total_lines, 50)))
        overview_code = "\n".join(source_lines[:overview_end_line])

        context_header = f"File: {file_path} | Language: {parsed_file.language} | Module Overview"
        module_chunk = NormalizedChunk(
            chunk_id=module_chunk_id,
            file_path=file_path,
            chunk_type=ChunkType.MODULE_OVERVIEW,
            start_line=1,
            end_line=overview_end_line,
            content=overview_code,
            content_hash=self._hash_text(overview_code),
            context_header=context_header,
            symbol_name=None,
            parent_chunk_id=None,
            imported_dependencies=imported_modules,
            metadata={
                "total_loc": parsed_file.lines_of_code,
                "symbols_count": len(parsed_file.symbols),
                "exports": parsed_file.exports,
            },
        )
        chunks.append(module_chunk)

        # Map class names to their generated chunk IDs for hierarchical linking
        class_chunk_id_map: Dict[str, str] = {}

        # 2. Class Declaration Chunks
        classes = [s for s in parsed_file.symbols if s.symbol_type in (SymbolType.CLASS, SymbolType.MODEL, SymbolType.INTERFACE)]
        for cls in classes:
            class_chunk_id = f"{file_path}::{cls.name}::class"
            class_chunk_id_map[cls.name] = class_chunk_id

            # Extract class body preview (header + docstring + method signatures)
            cls_start = max(1, cls.start_line)
            methods_in_class = [s for s in parsed_file.symbols if s.parent_name == cls.name]
            method_signatures = [f"  - {m.signature or m.name}" for m in methods_in_class]

            first_method_start = min((m.start_line for m in methods_in_class if m.start_line > cls_start), default=cls.end_line)
            decl_end = max(cls_start, first_method_start - 1 if first_method_start > cls_start else min(cls_start + 40, cls.end_line))

            summary_content = (
                f"{cls.signature or f'class {cls.name}'}\n"
                f'"""{cls.docstring or "No class docstring."}"""\n'
                f"# Methods ({len(methods_in_class)}):\n"
                + "\n".join(method_signatures)
            )

            chunks.append(
                NormalizedChunk(
                    chunk_id=class_chunk_id,
                    file_path=file_path,
                    chunk_type=ChunkType.CLASS_DECLARATION,
                    start_line=cls_start,
                    end_line=decl_end,
                    content=summary_content,
                    content_hash=self._hash_text(summary_content),
                    context_header=f"File: {file_path} | Class: {cls.name}",
                    symbol_name=cls.name,
                    parent_chunk_id=module_chunk_id,
                    imported_dependencies=imported_modules,
                    metadata={
                        "symbol_type": cls.symbol_type.value,
                        "methods_count": len(methods_in_class),
                        "bases": cls.metadata.get("bases", []),
                    },
                )
            )

        # 3. Method & Function Implementation Chunks
        executable_symbols = [
            s for s in parsed_file.symbols
            if s.symbol_type in (SymbolType.FUNCTION, SymbolType.METHOD, SymbolType.ENDPOINT)
        ]

        for sym in executable_symbols:
            s_start = max(1, sym.start_line)
            s_end = min(total_lines, sym.end_line)
            func_code = "\n".join(source_lines[s_start - 1 : s_end])

            parent_chunk_id = class_chunk_id_map.get(sym.parent_name) if sym.parent_name else module_chunk_id
            chunk_type = (
                ChunkType.METHOD_IMPLEMENTATION if sym.parent_name else ChunkType.FUNCTION_IMPLEMENTATION
            )
            chunk_id = f"{file_path}::{sym.qualified_name}::implementation"

            scope_str = f"Class: {sym.parent_name}" if sym.parent_name else "Scope: Global"
            header = (
                f"# File: {file_path} (Lines {s_start}-{s_end})\n"
                f"# {scope_str} | Symbol: {sym.qualified_name}\n"
                f"# Imports: {import_summary_str}\n"
            )
            full_chunk_content = f"{header}\n{func_code}"

            chunks.append(
                NormalizedChunk(
                    chunk_id=chunk_id,
                    file_path=file_path,
                    chunk_type=chunk_type,
                    start_line=s_start,
                    end_line=s_end,
                    content=full_chunk_content,
                    content_hash=self._hash_text(full_chunk_content),
                    context_header=f"File: {file_path} | {scope_str} | {sym.signature or sym.name}",
                    symbol_name=sym.qualified_name,
                    parent_chunk_id=parent_chunk_id,
                    imported_dependencies=imported_modules,
                    metadata={
                        "is_endpoint": sym.symbol_type == SymbolType.ENDPOINT,
                        "decorators": sym.decorators,
                        "calls_count": len(sym.calls),
                    },
                )
            )

        # 4. Fallback for files with zero extracted symbols (e.g., config files, SQL, shell scripts, Markdown)
        if not parsed_file.symbols:
            step = self.max_chunk_lines
            overlap = 15
            start = 0
            block_idx = 1

            while start < total_lines:
                end = min(total_lines, start + step)
                block_code = "\n".join(source_lines[start:end])
                chunk_id = f"{file_path}::block_{block_idx}"

                chunks.append(
                    NormalizedChunk(
                        chunk_id=chunk_id,
                        file_path=file_path,
                        chunk_type=ChunkType.CODE_BLOCK,
                        start_line=start + 1,
                        end_line=end,
                        content=block_code,
                        content_hash=self._hash_text(block_code),
                        context_header=f"File: {file_path} (Lines {start + 1}-{end})",
                        symbol_name=None,
                        parent_chunk_id=module_chunk_id if block_idx > 1 else None,
                        imported_dependencies=[],
                        metadata={"block_index": block_idx},
                    )
                )
                if end == total_lines:
                    break
                start += step - overlap
                block_idx += 1

        return chunks

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
