import sys
sys.path.insert(0, ".")
import sqlite3
from packages.retrieval.tokenizer import CodeTokenizer

conn = sqlite3.connect("codeatlas.db")
c = conn.cursor()
c.execute("""
    SELECT cs.name, cs.symbol_type, rf.path, cc.start_line, cc.end_line, cc.content
    FROM code_chunks cc
    JOIN repository_files rf ON cc.file_id = rf.id
    LEFT JOIN code_symbols cs ON cc.symbol_id = cs.id
    WHERE cs.name IN ('_get_resolved_directory', '_get_resolved_absolute_path', '_frontend_dependency_endpoint', 'solve_dependencies', 'get_dependant', 'Depends')
""")
query = "Where is dependency injection implemented?"
q_tokens = set(CodeTokenizer.expand_query_tokens(query))
print("Expanded query tokens:", q_tokens)
for r in c.fetchall():
    sym, stype, path, sl, el, content = r
    doc_toks = set(CodeTokenizer.tokenize(content))
    sym_toks = set(CodeTokenizer.tokenize(sym or ""))
    file_toks = set(CodeTokenizer.tokenize(path))
    c_overlap = q_tokens.intersection(doc_toks)
    s_overlap = q_tokens.intersection(sym_toks)
    f_overlap = q_tokens.intersection(file_toks)
    print(f"\nSymbol: {sym} ({stype}) in {path}:{sl}-{el}")
    print(f"  sym overlap: {s_overlap}")
    print(f"  file overlap: {f_overlap}")
    print(f"  content overlap count: {len(c_overlap)} -> {c_overlap}")
