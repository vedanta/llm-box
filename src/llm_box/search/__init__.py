"""Search system for llm-box.

This module provides semantic and fuzzy search capabilities for
finding files based on natural language queries or approximate matching.
"""

from llm_box.search.engine import SearchEngine, SearchMode, SearchResponse, SearchResult
from llm_box.search.fuzzy import FuzzyResult, FuzzySearch, MatchType
from llm_box.search.indexer import FileIndexer, FileInfo, IndexStats, TextChunk
from llm_box.search.semantic import SemanticResult, SemanticSearch

__all__ = [
    # Engine
    "SearchEngine",
    "SearchMode",
    "SearchResponse",
    "SearchResult",
    # Fuzzy
    "FuzzySearch",
    "FuzzyResult",
    "MatchType",
    # Semantic
    "SemanticSearch",
    "SemanticResult",
    # Indexer
    "FileIndexer",
    "FileInfo",
    "IndexStats",
    "TextChunk",
]
