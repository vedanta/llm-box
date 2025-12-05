"""Fuzzy search implementation.

This module provides fuzzy string matching for filenames and content
using the rapidfuzz library for fast approximate matching.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

try:
    from rapidfuzz import fuzz

    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


class MatchType(str, Enum):
    """Type of fuzzy match."""

    FILENAME = "filename"
    PATH = "path"
    CONTENT = "content"


@dataclass
class FuzzyResult:
    """Result from a fuzzy search."""

    file_path: str
    filename: str
    match_type: MatchType
    matched_text: str
    score: float  # 0-100
    context: str | None = None  # Surrounding text for content matches


class FuzzySearch:
    """Fuzzy search engine for filenames and content.

    Uses rapidfuzz for fast approximate string matching with
    support for various matching algorithms.
    """

    def __init__(
        self,
        min_score: float = 60.0,
        max_results: int = 50,
    ) -> None:
        """Initialize fuzzy search.

        Args:
            min_score: Minimum score (0-100) to include in results.
            max_results: Maximum number of results to return.
        """
        if not RAPIDFUZZ_AVAILABLE:
            raise ImportError(
                "rapidfuzz is required for fuzzy search. "
                "Install with: pip install rapidfuzz"
            )
        self.min_score = min_score
        self.max_results = max_results

    def search_filenames(
        self,
        query: str,
        files: list[dict[str, Any]],
    ) -> list[FuzzyResult]:
        """Search for files by filename similarity.

        Args:
            query: Search query.
            files: List of file records with 'file_path' and 'filename' keys.

        Returns:
            List of FuzzyResult objects sorted by score.
        """
        results: list[FuzzyResult] = []

        for file_record in files:
            filename = file_record.get("filename", "")
            file_path = file_record.get("file_path", "")

            # Score against filename
            filename_score = fuzz.partial_ratio(query.lower(), filename.lower())

            if filename_score >= self.min_score:
                results.append(
                    FuzzyResult(
                        file_path=file_path,
                        filename=filename,
                        match_type=MatchType.FILENAME,
                        matched_text=filename,
                        score=filename_score,
                    )
                )
                continue

            # Also try path matching for lower-scored filename matches
            path_score = fuzz.partial_ratio(query.lower(), file_path.lower())

            if path_score >= self.min_score:
                results.append(
                    FuzzyResult(
                        file_path=file_path,
                        filename=filename,
                        match_type=MatchType.PATH,
                        matched_text=file_path,
                        score=path_score
                        * 0.9,  # Slightly lower weight for path matches
                    )
                )

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[: self.max_results]

    def search_content(
        self,
        query: str,
        files: list[dict[str, Any]],
        context_chars: int = 100,
    ) -> list[FuzzyResult]:
        """Search for files by content similarity.

        Args:
            query: Search query.
            files: List of file records with 'file_path', 'filename',
                   and 'content_preview' keys.
            context_chars: Number of characters of context to include.

        Returns:
            List of FuzzyResult objects sorted by score.
        """
        results: list[FuzzyResult] = []

        for file_record in files:
            content = file_record.get("content_preview", "")
            if not content:
                continue

            filename = file_record.get("filename", "")
            file_path = file_record.get("file_path", "")

            # Score against content
            content_score = fuzz.partial_ratio(query.lower(), content.lower())

            if content_score >= self.min_score:
                # Extract context around the match
                context = self._extract_context(content, query, context_chars)

                results.append(
                    FuzzyResult(
                        file_path=file_path,
                        filename=filename,
                        match_type=MatchType.CONTENT,
                        matched_text=query,
                        score=content_score * 0.85,  # Weight content slightly lower
                        context=context,
                    )
                )

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[: self.max_results]

    def search_combined(
        self,
        query: str,
        files: list[dict[str, Any]],
    ) -> list[FuzzyResult]:
        """Search both filenames and content.

        Args:
            query: Search query.
            files: List of file records.

        Returns:
            Combined and deduplicated results sorted by score.
        """
        # Get results from both searches
        filename_results = self.search_filenames(query, files)
        content_results = self.search_content(query, files)

        # Combine and deduplicate by file_path
        seen_paths: dict[str, FuzzyResult] = {}

        for result in filename_results + content_results:
            path = result.file_path
            if path not in seen_paths or result.score > seen_paths[path].score:
                seen_paths[path] = result

        # Sort by score
        results = list(seen_paths.values())
        results.sort(key=lambda r: r.score, reverse=True)
        return results[: self.max_results]

    def _extract_context(
        self,
        content: str,
        query: str,
        context_chars: int,
    ) -> str:
        """Extract context around a fuzzy match.

        Args:
            content: Full content string.
            query: Query to find.
            context_chars: Characters of context on each side.

        Returns:
            Context string with match highlighted.
        """
        # Try to find approximate position
        query_lower = query.lower()
        content_lower = content.lower()

        # Find best matching position
        best_pos = -1
        best_score: float = 0

        # Slide a window and find best match position
        window_size = len(query) + 10
        for i in range(len(content) - min(window_size, len(content))):
            window = content_lower[i : i + window_size]
            score = fuzz.partial_ratio(query_lower, window)
            if score > best_score:
                best_score = score
                best_pos = i

        if best_pos == -1:
            # Fallback to beginning
            return content[: context_chars * 2] + "..."

        # Extract context
        start = max(0, best_pos - context_chars)
        end = min(len(content), best_pos + len(query) + context_chars)

        context = content[start:end]

        # Add ellipsis if truncated
        if start > 0:
            context = "..." + context
        if end < len(content):
            context = context + "..."

        return context

    def rank_results(
        self,
        results: list[FuzzyResult],
        boost_filename: float = 1.2,
        boost_extension_match: str | None = None,
    ) -> list[FuzzyResult]:
        """Apply additional ranking to results.

        Args:
            results: List of fuzzy results.
            boost_filename: Multiplier for filename matches.
            boost_extension_match: Extension to boost (e.g., ".py").

        Returns:
            Re-ranked results.
        """
        for result in results:
            # Boost filename matches
            if result.match_type == MatchType.FILENAME:
                result.score *= boost_filename

            # Boost specific extension
            if boost_extension_match and result.file_path.endswith(
                boost_extension_match
            ):
                result.score *= 1.1

            # Cap at 100
            result.score = min(result.score, 100.0)

        results.sort(key=lambda r: r.score, reverse=True)
        return results
