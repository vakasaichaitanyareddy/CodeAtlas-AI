# Code Parser & AST Intermediate Representation

## Overview
CodeAtlas parses code with language-specific syntactic AST engines (Python stdlib `ast` and custom JavaScript/TypeScript syntactic scanners) into an extensible, normalized intermediate representation. This decouples retrieval, graph construction, and chunking from language syntax quirks.

---

## 1. Normalized AST Data Model

```
NormalizedFile
 ├── Path, Language, LOC, Size, Hash
 ├── Symbols: List[NormalizedSymbol]
 │    ├── Name, QualifiedName, SymbolType (CLASS, FUNCTION, METHOD, etc.)
 │    ├── StartLine, EndLine
 │    ├── Docstring, Signature, ParentSymbol
 │    └── Calls: List[NormalizedCall]
 ├── Imports: List[NormalizedImport]
 │    └── Module, Symbols, Alias, Line
 └── Exports: List[NormalizedExport]
```

---

## 2. Supported Languages & Extensibility
The `Parser` abstract base class defines:
```python
class BaseParser(ABC):
    @abstractmethod
    def parse_file(self, file_path: str, source_code: str) -> NormalizedFile:
        pass
```

Implementations:
- `PythonParser`: Handles classes, async/def functions, decorators, imports (`import x`, `from y import z`), calls.
- `JavaScriptParser`: Handles ES6 modules, CommonJS `require`, arrow functions, classes, async functions.
- `TypeScriptParser`: Extends JS parser with interfaces, types, enums, type annotations.

---

## 3. Intelligent Hierarchical Chunking
Instead of fixed character or token windows (e.g. 500 chars), CodeAtlas generates AST chunks:
- **Module Overview Chunks**: Top-level file header, imports, and module docstring.
- **Class Chunks**: Class definition, class docstring, attributes, and method signatures.
- **Method/Function Chunks**: Individual executable functions and methods, annotated with parent class context and imported dependencies.
- **Hierarchical Linking**: Child method chunks store references to their parent class chunk ID.
