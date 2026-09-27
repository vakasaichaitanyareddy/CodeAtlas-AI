import re
from typing import List, Set
from .models import QueryIntent, QueryAnalysis


class QueryClassifier:
    """Classifies user queries into codebase intents and extracts target entities."""

    # Intent regex patterns
    DEPENDENCY_PATTERNS = [
        r"\b(?:what|who|which)\s+(?:calls|invokes|imports|uses)\b",
        r"\b(?:callers|callees|dependencies|imports|references)\s+of\b",
        r"\bwhere\s+is\s+\w+\s+(?:used|called|imported|referenced)\b",
        r"\bfind\s+(?:callers|callees|usages|references)\b",
    ]

    IMPACT_PATTERNS = [
        r"\b(?:what\s+breaks|blast\s+radius|impact\s+of|side\s+effects)\b",
        r"\bwhat\s+(?:happens|is\s+affected)\s+if\s+I\s+(?:change|modify|delete|remove|update)\b",
        r"\bdownstream\s+(?:impact|dependencies|effects)\b",
    ]

    ARCHITECTURE_PATTERNS = [
        r"\b(?:architecture|system\s+design|high-level\s+overview|data\s+flow|workflow)\b",
        r"\bhow\s+does\s+(?:the\s+system|the\s+entire|this\s+repo|the\s+application)\s+work\b",
        r"\bexplain\s+(?:the\s+architecture|the\s+workflow|the\s+structure|how\s+\w+\s+works)\b",
        r"\bcomponent\s+(?:diagram|interaction|structure)\b",
        r"\bhow\s+does\s+.*\b(?:route|routing|dispatch|flow|handle|process|work)\b",
        r"\bhow\s+(?:is|are)\s+.*\b(?:routed|dispatched|handled|processed|generated|created)\b",
        r"\bwhat\s+happens\s+when\s+.*\b(?:pushes|pushed|invokes|invoked|called|calls)\b",
        r"\bhow\s+does\s+\w+\s+call\s+\w+\b",
        r"\brequest\s+(?:flow|routing|dispatch|lifecycle)\b",
    ]

    DOCUMENTATION_PATTERNS = [
        r"\b(?:how\s+to\s+(?:install|run|start|deploy|setup|configure|build))\b",
        r"\b(?:getting\s+started|installation\s+guide|prerequisites|requirements)\b",
        r"\b(?:readme|docker-compose|environment\s+variables|\.env)\b",
        r"\bhow\s+do\s+I\s+(?:run|start|test)\s+this\b",
    ]

    FACTUAL_PATTERNS = [
        r"\b(?:where\s+is|find|show|locate|implementation\s+of)\b",
        r"\b(?:function|method|class|struct|interface|endpoint|schema|model)\b",
        r"\b(?:how\s+is\s+\w+\s+implemented)\b",
    ]

    # Entity extraction patterns
    SYMBOL_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\b")
    FILE_PATTERN = re.compile(r"([A-Za-z0-9_\-\./]+\.[a-zA-Z0-9]{1,4})\b")

    COMMON_STOP_WORDS = {
        "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
        "the", "and", "or", "for", "with", "from", "into", "during", "including",
        "until", "against", "among", "throughout", "despite", "towards", "upon",
        "this", "that", "these", "those", "does", "done", "show", "tell", "explain",
        "find", "locate", "give", "code", "file", "repo", "repository", "system",
        "call", "calls", "used", "uses", "work", "works", "help", "please", "can",
    }

    def analyze_query(self, raw_query: str) -> QueryAnalysis:
        """Classify the intent of the query and extract symbol/file entities."""
        query_text = raw_query.strip()
        lower_query = query_text.lower()

        # 1. Determine intent by order of specificity
        intent = QueryIntent.GENERAL_QA
        confidence = 0.7

        if any(re.search(pat, lower_query) for pat in self.IMPACT_PATTERNS):
            intent = QueryIntent.IMPACT
            confidence = 0.95
        elif any(re.search(pat, lower_query) for pat in self.DEPENDENCY_PATTERNS):
            intent = QueryIntent.DEPENDENCY
            confidence = 0.95
        elif any(re.search(pat, lower_query) for pat in self.ARCHITECTURE_PATTERNS):
            intent = QueryIntent.ARCHITECTURE
            confidence = 0.90
        elif any(re.search(pat, lower_query) for pat in self.DOCUMENTATION_PATTERNS):
            intent = QueryIntent.DOCUMENTATION
            confidence = 0.90
        elif any(re.search(pat, lower_query) for pat in self.FACTUAL_PATTERNS):
            intent = QueryIntent.FACTUAL_CODE
            confidence = 0.85

        # 2. Extract potential file patterns
        file_matches = self.FILE_PATTERN.findall(query_text)
        file_patterns = [f for f in file_matches if not f.startswith("http")]

        # 3. Extract candidate symbol identifiers
        symbol_matches = self.SYMBOL_PATTERN.findall(query_text)
        target_symbols: List[str] = []
        for sym in symbol_matches:
            if sym.lower() in self.COMMON_STOP_WORDS:
                continue
            # Keep camelCase, PascalCase, or snake_case with an underscore
            is_camel = bool(re.search(r"[a-z][A-Z]", sym))
            is_snake = "_" in sym and not sym.startswith("__")
            is_pascal = sym[0].isupper() and len(sym) >= 3
            if is_camel or is_snake or is_pascal:
                target_symbols.append(sym)

        # 4. Generate expanded keywords for search
        expanded: Set[str] = set()
        for sym in target_symbols:
            expanded.add(sym)
            # Split camelCase / snake_case into sub-words
            parts = re.findall(r"[A-Za-z][a-z0-9]*", sym)
            for p in parts:
                if len(p) >= 3 and p.lower() not in self.COMMON_STOP_WORDS:
                    expanded.add(p.lower())

        return QueryAnalysis(
            raw_query=raw_query,
            intent=intent,
            target_symbols=target_symbols,
            file_patterns=file_patterns,
            expanded_terms=list(expanded),
            confidence=confidence,
        )
