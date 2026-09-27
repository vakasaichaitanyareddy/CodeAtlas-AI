import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from .models import CitationValidationResult, GroundingStatus, ContextPack, ContextChunk

logger = logging.getLogger("codeatlas.rag.citations")


class CitationVerifier:
    """Multi-stage citation validation and grounding verification engine."""

    # Matches [path/file.py:L10-L25], [path/file.ts:L15], [path/file.py#L10-L25], [path/file.py:10-25]
    CITATION_REGEX = re.compile(
        r"\[([A-Za-z0-9_\-\./]+\.[a-zA-Z0-9]+)(?:[:#]L?(\d+)(?:-L?(\d+))?)?\]"
    )

    def extract_citations(self, text: str) -> List[Tuple[str, str, int, int]]:
        """Extract all raw citations from generated text. Returns (raw, path, start_line, end_line)."""
        results = []
        for match in self.CITATION_REGEX.finditer(text):
            raw = match.group(0)
            path = match.group(1)
            start_str = match.group(2)
            end_str = match.group(3)

            start_line = int(start_str) if start_str else 1
            end_line = int(end_str) if end_str else start_line

            results.append((raw, path, start_line, end_line))
        return results

    def validate_citations(
        self,
        citations: List[Tuple[str, str, int, int]],
        context_pack: ContextPack,
        file_records: Dict[str, Dict[str, Any]],  # path -> {"loc": int, "symbols": List[Dict]}
    ) -> List[CitationValidationResult]:
        """Validate each citation against repository physical file bounds, context overlap, and AST symbols."""
        validation_results: List[CitationValidationResult] = []

        for raw, path, start, end in citations:
            # Check 1: Inverted line range check
            if start > end or start < 1:
                validation_results.append(
                    CitationValidationResult(
                        raw_citation=raw,
                        file_path=path,
                        start_line=start,
                        end_line=end,
                        file_exists=path in file_records,
                        lines_in_bounds=False,
                        overlaps_context=False,
                        symbol_matches=False,
                        source_chunk_id=None,
                        confidence=0.0,
                        validation_reason="invalid_or_negative_line_range",
                        is_valid=False,
                    )
                )
                continue

            # Check 2: File exists in repository
            if path not in file_records:
                validation_results.append(
                    CitationValidationResult(
                        raw_citation=raw,
                        file_path=path,
                        start_line=start,
                        end_line=end,
                        file_exists=False,
                        lines_in_bounds=False,
                        overlaps_context=False,
                        symbol_matches=False,
                        source_chunk_id=None,
                        confidence=0.0,
                        validation_reason="file_does_not_exist_in_repository",
                        is_valid=False,
                    )
                )
                continue

            file_info = file_records[path]
            file_loc = file_info.get("loc", 0)

            # Check 3: Physical line bounds
            if end > file_loc and file_loc > 0:
                validation_results.append(
                    CitationValidationResult(
                        raw_citation=raw,
                        file_path=path,
                        start_line=start,
                        end_line=end,
                        file_exists=True,
                        lines_in_bounds=False,
                        overlaps_context=False,
                        symbol_matches=False,
                        source_chunk_id=None,
                        confidence=0.0,
                        validation_reason=f"end_line_{end}_exceeds_physical_loc_{file_loc}",
                        is_valid=False,
                    )
                )
                continue

            # Check 4: Overlaps retrieved context chunk
            matching_chunk: Optional[ContextChunk] = None
            for chunk in context_pack.chunks:
                if chunk.file_path == path:
                    # Check overlap between [start, end] and [chunk.start_line, chunk.end_line]
                    overlap = max(0, min(end, chunk.end_line) - max(start, chunk.start_line) + 1)
                    if overlap > 0:
                        matching_chunk = chunk
                        break

            if not matching_chunk:
                validation_results.append(
                    CitationValidationResult(
                        raw_citation=raw,
                        file_path=path,
                        start_line=start,
                        end_line=end,
                        file_exists=True,
                        lines_in_bounds=True,
                        overlaps_context=False,
                        symbol_matches=False,
                        source_chunk_id=None,
                        confidence=0.2,
                        validation_reason="citation_not_supported_by_retrieved_context",
                        is_valid=False,
                    )
                )
                continue

            # Check 5: Symbol verification (if symbol claimed in chunk)
            symbol_matches = True
            claimed_symbols = file_info.get("symbols", [])
            # If the chunk has a symbol name, check if our range intersects that symbol
            if matching_chunk.symbol_name and claimed_symbols:
                has_matching_symbol = any(
                    s.get("name") == matching_chunk.symbol_name and
                    max(0, min(end, s.get("end_line", 0)) - max(start, s.get("start_line", 0)) + 1) > 0
                    for s in claimed_symbols
                )
                symbol_matches = has_matching_symbol

            # Citation fully verified
            confidence = 1.0 if symbol_matches else 0.8
            validation_results.append(
                CitationValidationResult(
                    raw_citation=raw,
                    file_path=path,
                    start_line=start,
                    end_line=end,
                    file_exists=True,
                    lines_in_bounds=True,
                    overlaps_context=True,
                    symbol_matches=symbol_matches,
                    source_chunk_id=matching_chunk.chunk_id,
                    confidence=confidence,
                    validation_reason="fully_verified_and_grounded",
                    is_valid=True,
                )
            )

        return validation_results

    def compute_grounding_status(
        self,
        validation_results: List[CitationValidationResult],
        context_pack: ContextPack,
        answer_text: str,
    ) -> GroundingStatus:
        """Determine overall GroundingStatus (VERIFIED, PARTIALLY_VERIFIED, UNSUPPORTED)."""
        # If evidence threshold was not met, answer is UNSUPPORTED
        if not context_pack.evidence.evidence_threshold_met:
            return GroundingStatus.UNSUPPORTED

        # If answer is the insufficient-evidence fallback message
        if "couldn't find enough evidence in the indexed repository" in answer_text.lower():
            return GroundingStatus.UNSUPPORTED

        if not validation_results:
            # No citations provided. If context had chunks but LLM gave no citations for code query:
            if context_pack.chunks and context_pack.analysis.intent != "GENERAL_QA":
                return GroundingStatus.PARTIALLY_VERIFIED
            return GroundingStatus.VERIFIED

        valid_count = sum(1 for r in validation_results if r.is_valid)
        total_count = len(validation_results)

        if valid_count == total_count:
            return GroundingStatus.VERIFIED
        elif valid_count > 0:
            return GroundingStatus.PARTIALLY_VERIFIED
        else:
            return GroundingStatus.UNSUPPORTED
