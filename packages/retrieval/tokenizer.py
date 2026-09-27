import re
from typing import List, Set, Dict


class CodeTokenizer:
    """Specialized code tokenizer supporting compound splitting, camelCase, snake_case, and symbol preservation."""

    # Regex patterns for splitting compound identifiers
    CAMEL_CASE_PATTERN = re.compile(r"([a-z0-9])([A-Z])")
    SPECIAL_CHARS_PATTERN = re.compile(r"[^a-zA-Z0-9_\-]")
    IDENTIFIER_PATTERN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_\-]*")

    # Common programming stop words that have little discriminative value when indexing
    STOP_WORDS: Set[str] = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "it", "this", "that",
    }

    # Conversational framing words in natural language developer questions
    QUESTION_STOP_WORDS: Set[str] = {
        "how", "what", "where", "when", "why", "who", "which",
        "is", "are", "was", "were", "be", "been", "being",
        "does", "do", "did", "done",
        "can", "could", "would", "should", "will",
        "work", "works", "happen", "happens",
        "tell", "show", "explain", "give", "find", "locate",
        "implemented", "implementation",
    }

    # Architectural and process synonyms for framework execution flow and domain concepts
    PROCESS_SYNONYMS: Dict[str, List[str]] = {
        "route": ["dispatch", "dispatch_request", "url_rule", "view_functions", "router", "routing"],
        "routing": ["route", "dispatch", "dispatch_request", "url_rule", "router"],
        "router": ["route", "routing", "dispatch", "dispatch_request"],
        "dispatch": ["route", "routing", "view_functions", "handler"],
        "context": ["appcontext", "requestcontext"],
        "contexts": ["appcontext", "requestcontext"],
        "dependency": ["dependencies", "dependant", "depends", "depend", "inject", "injection", "solve_dependencies", "get_dependant"],
        "dependencies": ["dependency", "dependant", "depends", "depend", "inject", "injection", "solve_dependencies", "get_dependant"],
        "dependant": ["dependency", "dependencies", "depends", "depend", "dependants"],
        "depends": ["dependency", "dependencies", "dependant", "depend"],
        "inject": ["injection", "dependency", "dependencies", "injector", "injected"],
        "injection": ["inject", "dependency", "dependencies", "injected", "injector", "solve_dependencies", "get_dependant"],
        "openapi": ["schema", "schemas", "swagger", "openapi_path", "custom_openapi", "get_openapi_path"],
        "schema": ["openapi", "schemas", "swagger", "models", "get_openapi_path"],
        "schemas": ["openapi", "schema", "swagger", "models"],
        "auth": ["authentication", "authorize", "authorization", "security", "token", "jwt", "login"],
        "authentication": ["auth", "authorize", "security", "token", "password", "login"],
        "cookie": ["cookies", "param", "parameters"],
        "cookies": ["cookie", "param", "parameters"],
        "header": ["headers", "param", "parameters"],
        "headers": ["header", "param", "parameters"],
        "query": ["param", "parameters", "querystring"],
        "body": ["request_body", "payload", "form", "extract_form_body"],
        "form": ["form_data", "multipart", "body", "extract_form_body"],
        "file": ["upload_file", "multipart", "form"],
        "serialization": ["serialize", "serialize_response", "serialize_json", "encoders", "jsonable_encoder", "encoder"],
        "serialize": ["serialization", "serialize_response", "serialize_json", "encoders", "jsonable_encoder"],
        "encoder": ["encoders", "jsonable_encoder", "serialize", "serialization"],
        "encoders": ["encoder", "jsonable_encoder", "serialize", "serialization"],
        "validation": ["validate", "request_validation", "validate_value", "validator", "request_body_to_args", "request_params_to_args"],
        "validate": ["validation", "validator", "request_validation", "request_body_to_args", "request_params_to_args"],
        "execute": ["execution", "handle", "handler", "get_request_handler", "call", "app", "request_response"],
        "execution": ["execute", "handle", "handler", "get_request_handler", "call", "request_response"],
        "handler": ["get_request_handler", "get_route_handler", "handle", "execute", "dispatch"],
        "function": ["functions"],
        "functions": ["function"],
        "method": ["methods"],
        "methods": ["method"],
    }

    @classmethod
    def clean_query_tokens(cls, query: str) -> List[str]:
        """Extract domain code search tokens by filtering conversational question filler."""
        tokens = cls.tokenize(query)
        cleaned = [t for t in tokens if t.lower() not in cls.QUESTION_STOP_WORDS]
        return cleaned if cleaned else tokens

    @classmethod
    def expand_query_tokens(cls, query: str) -> List[str]:
        """Extract domain tokens and expand with standard framework process synonyms and morphological variations."""
        base_tokens = cls.clean_query_tokens(query)
        expanded = list(base_tokens)
        seen = set(base_tokens)

        for t in list(base_tokens):
            tl = t.lower()
            # Morphological inflections (plural/singular/verb endings)
            variants = []
            if tl.endswith("ies") and len(tl) > 4:
                variants.append(tl[:-3] + "y")
            elif tl.endswith("y") and len(tl) > 3:
                variants.append(tl[:-1] + "ies")
            if tl.endswith("s") and not tl.endswith("ss") and len(tl) > 3:
                variants.append(tl[:-1])
            elif not tl.endswith("s") and len(tl) > 2:
                variants.append(tl + "s")
            if tl.endswith("tion") and len(tl) > 5:
                variants.extend([tl[:-4] + "t", tl[:-4] + "te", tl[:-4] + "ting"])
            elif tl.endswith("ing") and len(tl) > 4:
                variants.extend([tl[:-3], tl[:-3] + "e", tl[:-3] + "tion"])

            for v in variants:
                if v not in seen:
                    expanded.append(v)
                    seen.add(v)

            # Dictionary synonyms
            synonyms = cls.PROCESS_SYNONYMS.get(tl, [])
            for syn in synonyms:
                if syn not in seen:
                    expanded.append(syn)
                    seen.add(syn)

        return expanded



    @classmethod
    def tokenize(cls, text: str, preserve_compounds: bool = True) -> List[str]:
        """Tokenize code or search query into a sequence of normalized tokens."""
        if not text:
            return []

        tokens: List[str] = []
        # Find all alphanumeric tokens and compound identifiers
        raw_words = cls.IDENTIFIER_PATTERN.findall(text)

        for word in raw_words:
            word_lower = word.lower()
            if not word_lower or word_lower in cls.STOP_WORDS:
                continue

            # Add the compound word itself if requested
            if preserve_compounds and len(word) > 1:
                tokens.append(word_lower)

            # Sub-tokenization: snake_case and kebab-case splitting
            if "_" in word or "-" in word:
                for part in word.replace("-", "_").split("_"):
                    part_lower = part.lower()
                    if len(part_lower) > 1 and part_lower not in cls.STOP_WORDS and part_lower != word_lower:
                        tokens.append(part_lower)
            elif any(c.isupper() for c in word[1:]):
                # Sub-tokenization: camelCase splitting only if uppercase characters exist inside
                split_camel = cls.CAMEL_CASE_PATTERN.sub(r"\1 \2", word)
                for sub in split_camel.split():
                    sub_lower = sub.lower()
                    if len(sub_lower) > 1 and sub_lower not in cls.STOP_WORDS and sub_lower != word_lower:
                        tokens.append(sub_lower)

        return tokens
