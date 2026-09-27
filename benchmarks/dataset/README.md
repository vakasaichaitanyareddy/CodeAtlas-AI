# CodeAtlas Retrieval Benchmark Dataset (v1.0.0)

- **Total Queries**: 60
- **Target Repository ID**: `3f5e9cbe-c565-4565-9cdb-600597d4207e`
- **Target Commit SHA**: `commit-after-failure`
- **Dataset Hash (SHA-256)**: `37bb6165fe17450ac61ed4d0cc7cf1a3c5c5d024500f13dac033ff034502c91f`

## Category Breakdown:
- `exact_symbol`: 12 queries
- `conceptual`: 10 queries
- `architecture`: 8 queries
- `dependency`: 8 queries
- `implementation`: 8 queries
- `subword`: 8 queries
- `ambiguous`: 6 queries

## Methodology
Ground truth relevance is established through direct AST inspection of the indexed repository source files.
A candidate chunk is considered relevant if:
1. Its `file_path` matches one of the `relevant_files`.
2. AND its content contains or is associated with one of the `relevant_symbols`.
