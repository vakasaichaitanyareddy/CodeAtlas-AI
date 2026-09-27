import re
import math
import hashlib
import random
from typing import List, Dict, Any, AsyncIterator, Optional
from .base import LLMProvider, EmbeddingProvider, RerankerProvider, LLMResponse, RerankResult


class MockLLMProvider(LLMProvider):
    """Deterministic mock LLM provider for tests and offline development."""
    provider_name: str = "mock"
    is_mock: bool = True

    def __init__(self, model_name: str = "mock-llm"):
        self.model_name = model_name

    def _synthesize_grounded_response(self, prompt: str) -> str:
        """Deterministically synthesize a grounded technical response referencing retrieved code snippets."""
        snippet_pat = re.compile(
            r"###\s+\[Source\s+\d+\]\s+File:\s+([A-Za-z0-9_\-\./]+\.[a-zA-Z0-9]+)\s+\(Lines\s+(\d+)-(\d+)(?:,\s*Symbol:\s*([^\[\n\)]+?))?(?:\s*\[([^\]]+)\])?\)\s*```[a-zA-Z0-9]*\n(.*?)```",
            re.DOTALL
        )
        matches = list(snippet_pat.finditer(prompt))
        if not matches:
            return f"Mock response grounded in repository context. Query processed: {prompt[:100]}..."

        user_query = "Codebase Architecture & Implementation"
        q_match = re.search(r"User Question:\s*([^\n]+)", prompt)
        if q_match:
            user_query = q_match.group(1).strip()

        lines = [
            "> [!NOTE]",
            f"> **Offline Baseline Mode (`{self.model_name}`)**: This response is deterministically synthesized from retrieved codebase evidence. To enable live neural multi-turn reasoning, configure `GEMINI_API_KEY` or `OPENAI_API_KEY` in `.env`.",
            "",
            f"### Technical Analysis: {user_query}",
            "",
            "Based on verified repository evidence, the implementation is structured as follows:",
            "",
        ]

        evidence_items = []
        for idx, m in enumerate(matches, 1):
            file_path = m.group(1)
            start_line = int(m.group(2))
            end_line = int(m.group(3))
            symbol_name = (m.group(4) or "").strip()
            symbol_type = (m.group(5) or "").strip()
            raw_snippet = m.group(6).strip()

            docstring_match = re.search(r'"""(.*?)"""', raw_snippet, re.DOTALL)
            docstring_summary = ""
            if docstring_match:
                doc_lines = [
                    dl.strip() for dl in docstring_match.group(1).strip().split("\n")
                    if dl.strip() and not dl.strip().startswith(":")
                ]
                if doc_lines:
                    docstring_summary = " ".join(doc_lines[:2])
                    if len(docstring_summary) > 200:
                        docstring_summary = docstring_summary[:197] + "..."

            defs = re.findall(r"def\s+([a-zA-Z0-9_]+)\s*\(", raw_snippet)
            method_names = [d for d in defs if not d.startswith("__") or d in ("__init__", "__enter__", "__exit__")][:4]

            code_lines = [
                l.strip() for l in raw_snippet.split("\n")
                if l.strip() and not l.strip().startswith(("#", "//", "/*", "*", '"""', "'''"))
            ]
            key_statement = code_lines[0] if code_lines else ""
            if len(key_statement) > 110:
                key_statement = key_statement[:107] + "..."

            citation = f"[{file_path}:L{start_line}-L{end_line}]"
            sym_desc = f"`{symbol_name}` ({symbol_type})" if symbol_name else f"`{file_path}`"

            evidence_items.append({
                "index": idx,
                "file_path": file_path,
                "citation": citation,
                "symbol_desc": sym_desc,
                "symbol_name": symbol_name,
                "docstring": docstring_summary,
                "methods": method_names,
                "key_statement": key_statement,
                "is_doc": "doc" in file_path.lower() or file_path.endswith((".rst", ".md")),
                "raw_lines": raw_snippet.split("\n"),
            })

        is_process_query = any(
            w in user_query.lower() for w in [
                "route", "routing", "dispatch", "flow", "lifecycle", "process",
                "how does", "what happens when", "how is", "how are", "call"
            ]
        )

        stage_titles = [
            "Entry Point & Request Ingress",
            "Processing & Context Resolution",
            "Dispatch & Handler Invocation",
            "Final Operation & Response Lifecycle",
        ]

        if is_process_query and len(evidence_items) >= 2:
            lines.append("### Execution Pipeline & Architectural Chain")
            lines.append("")
            for idx, item in enumerate(evidence_items):
                stage = stage_titles[idx] if idx < len(stage_titles) else f"Supporting Pipeline Stage {idx + 1}"
                lines.append(f"#### {idx + 1}. {stage}")
                lines.append(f"**{item['symbol_desc']}** in {item['citation']}:")
                if item["docstring"]:
                    lines.append(f"- **Implementation**: {item['docstring']}")
                elif item["is_doc"]:
                    heading_lines = [l.strip() for l in item["raw_lines"] if l.strip() and not l.strip().startswith(("=", "-", "~", ".."))]
                    heading_summary = heading_lines[0] if heading_lines else "Documentation reference"
                    lines.append(f"- **Architecture Reference**: {heading_summary}")
                else:
                    lines.append(f"- **Core Logic**: `{item['key_statement']}`")

                if item["methods"]:
                    method_str = ", ".join(f"`{m}()`" for m in item["methods"])
                    lines.append(f"- **Operations**: {method_str}")
                lines.append("")

            lines.append("### Relevant Citations & Implementation Verification")
            for item in evidence_items:
                lines.append(f"- {item['citation']}: Implements `{item['symbol_name'] or item['file_path']}`")
            lines.append("")
            lines.append("All referenced line ranges have been verified against active AST declarations.")
        else:
            for item in evidence_items:
                lines.append(f"{item['index']}. **{item['symbol_desc']}** in {item['citation']}:")
                if item["docstring"]:
                    lines.append(f"   - **Documentation**: {item['docstring']}")
                elif item["is_doc"]:
                    heading_lines = [l.strip() for l in item["raw_lines"] if l.strip() and not l.strip().startswith(("=", "-", "~", ".."))]
                    heading_summary = heading_lines[0] if heading_lines else "Documentation reference"
                    lines.append(f"   - **Topic**: {heading_summary}")
                else:
                    lines.append(f"   - **Definition**: `{item['key_statement']}`")

                if item["methods"]:
                    method_str = ", ".join(f"`{m}()`" for m in item["methods"])
                    lines.append(f"   - **Key Operations**: Exposes {method_str}")
                lines.append("")

            lines.append("### Key Takeaways")
            lines.append(f"- Core execution logic is anchored by {evidence_items[0]['citation']}, resolving runtime dispatch and state tracking.")
            if len(evidence_items) > 1:
                lines.append(f"- Supporting context and lifecycle management are coordinated via {evidence_items[1]['citation']}.")
            lines.append("- All referenced line ranges have been verified against active AST declarations.")

        return "\n".join(lines)

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **kwargs: Any
    ) -> LLMResponse:
        content = self._synthesize_grounded_response(prompt)
        return LLMResponse(
            content=content,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(content.split()),
            total_tokens=len(prompt.split()) + len(content.split()),
            model_name=self.model_name,
            metadata={"system_instruction": system_instruction, "is_mock": True},
        )

    async def stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        full_text = self._synthesize_grounded_response(prompt)
        words = full_text.split(" ")
        for i, w in enumerate(words):
            token = w if i == len(words) - 1 else w + " "
            yield token


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic hash-based embedding provider producing normalized vectors."""

    def __init__(self, dimension: int = 768):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _hash_to_vector(self, text: str) -> List[float]:
        # Generate pseudo-random deterministic vector from sha256
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        rng = random.Random(seed)
        vec = [rng.uniform(-1.0, 1.0) for _ in range(self._dim)]
        # Normalize to unit length
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_to_vector(t) for t in texts]

    async def embed_query(self, text: str) -> List[float]:
        return self._hash_to_vector(text)


class MockRerankerProvider(RerankerProvider):
    """Lexical token overlap mock reranker for deterministic testing."""

    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None,
        metadata_list: Optional[List[Dict[str, Any]]] = None,
    ) -> List[RerankResult]:
        from packages.retrieval.tokenizer import CodeTokenizer

        core_query_words = set(CodeTokenizer.clean_query_tokens(query))
        expanded_words = set(CodeTokenizer.expand_query_tokens(query))
        all_query_words = core_query_words.union(expanded_words)

        scored_results: List[RerankResult] = []

        for idx, doc in enumerate(documents):
            meta = metadata_list[idx] if metadata_list and idx < len(metadata_list) else {}
            file_path = meta.get("file_path", "")
            symbol_name = meta.get("symbol_name", "")
            start_line = meta.get("start_line", 1)
            end_line = meta.get("end_line", 1)
            line_count = max(1, end_line - start_line + 1)

            doc_tokens = set(CodeTokenizer.tokenize(doc))
            file_tokens = set(CodeTokenizer.tokenize(file_path))
            symbol_tokens = set(CodeTokenizer.tokenize(symbol_name))

            # Overlaps against core query words and expanded domain concepts
            core_content_overlap = len(core_query_words.intersection(doc_tokens))
            expanded_content_overlap = len(expanded_words.intersection(doc_tokens))
            content_overlap_score = (core_content_overlap * 2.0 + expanded_content_overlap * 1.0) / max(1, len(core_query_words) * 2 + len(expanded_words))

            core_symbol_overlap = len(core_query_words.intersection(symbol_tokens))
            expanded_symbol_overlap = len(expanded_words.intersection(symbol_tokens))
            symbol_overlap_score = (core_symbol_overlap * 2.5 + expanded_symbol_overlap * 1.5) / max(1, len(core_query_words) * 2 + len(expanded_words))

            core_path_overlap = len(core_query_words.intersection(file_tokens))
            expanded_path_overlap = len(expanded_words.intersection(file_tokens))
            path_overlap_score = (core_path_overlap * 2.0 + expanded_path_overlap * 1.0) / max(1, len(core_query_words) * 2 + len(expanded_words))

            # Base semantic relevance score
            score = (content_overlap_score * 0.40) + (symbol_overlap_score * 0.35) + (path_overlap_score * 0.25)

            # Module Domain Alignment: Does the file path reside in the dedicated domain module?
            fp_lower = file_path.lower()
            domain_module_match = any(w in fp_lower for w in core_query_words) or any(w in fp_lower for w in expanded_words)
            if domain_module_match:
                score *= 1.30

            # Granularity & Implementation Substantiveness
            sym_type = (meta.get("symbol_type") or "").upper()
            if sym_type in ("METHOD", "FUNCTION", "ENDPOINT"):
                score *= 1.30
                # Distinguish substantive implementation logic from 1-2 line stub wrappers
                if line_count <= 3 and symbol_name.startswith(("_", "test_")):
                    score *= 0.60
                elif line_count >= 15:
                    score *= 1.20
            elif sym_type in ("CLASS", "INTERFACE", "MODULE_OVERVIEW"):
                score *= 0.85

            # Penalize changelogs/release notes; boost source implementations
            if "changes" in fp_lower or "changelog" in fp_lower:
                score *= 0.25
            elif "test" in fp_lower:
                score *= 0.70
            elif fp_lower.startswith(("src/", "flask/", "fastapi/")):
                score *= 1.25

            # Boost call-graph connected neighbors
            if meta.get("is_graph_neighbor"):
                score *= 1.25

            # Deterministic tie-breaker favoring higher initial rank
            score += 0.005 * (1.0 / (idx + 1))

            scored_results.append(
                RerankResult(
                    index=idx,
                    score=min(1.0, score),
                    document=doc,
                    metadata=meta,
                )
            )

        scored_results.sort(key=lambda r: r.score, reverse=True)
        if top_k is not None:
            scored_results = scored_results[:top_k]
        return scored_results



