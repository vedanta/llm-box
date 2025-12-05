"""Semantic search implementation.

This module provides vector-based semantic search using embeddings
for natural language queries against indexed file content.
"""

import math
from dataclasses import dataclass
from typing import Any

from llm_box.providers.base import LLMBoxProvider


@dataclass
class SemanticResult:
    """Result from a semantic search."""

    file_path: str
    filename: str
    chunk_index: int
    chunk_text: str
    similarity_score: float  # 0.0 to 1.0
    start_line: int | None = None
    end_line: int | None = None


class SemanticSearch:
    """Semantic search engine using vector embeddings.

    Uses embeddings from an LLM provider to find semantically
    similar content based on natural language queries.
    """

    def __init__(
        self,
        provider: LLMBoxProvider | None = None,
        min_score: float = 0.5,
        max_results: int = 20,
    ) -> None:
        """Initialize semantic search.

        Args:
            provider: LLM provider with embedding support.
            min_score: Minimum similarity score (0-1) to include.
            max_results: Maximum number of results to return.
        """
        self.provider = provider
        self.min_score = min_score
        self.max_results = max_results

    def set_provider(self, provider: LLMBoxProvider) -> None:
        """Set the LLM provider.

        Args:
            provider: LLM provider with embedding support.
        """
        self.provider = provider

    def embed_query(self, query: str) -> list[float] | None:
        """Generate embedding for a search query.

        Args:
            query: Search query text.

        Returns:
            Embedding vector or None if provider unavailable.
        """
        if not self.provider:
            return None

        try:
            response = self.provider.embed([query])
            if response.embeddings:
                return response.embeddings[0]
        except Exception:
            pass

        return None

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.
        """
        if not self.provider or not texts:
            return []

        try:
            response = self.provider.embed(texts)
            return response.embeddings
        except Exception:
            return []

    def cosine_similarity(
        self,
        vec1: list[float],
        vec2: list[float],
    ) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector.
            vec2: Second vector.

        Returns:
            Cosine similarity score (0-1).
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def search(
        self,
        query: str,
        indexed_chunks: list[dict[str, Any]],
    ) -> list[SemanticResult]:
        """Search indexed chunks using semantic similarity.

        Args:
            query: Natural language search query.
            indexed_chunks: List of chunk records with embeddings.
                Expected keys: file_path, filename, chunk_index,
                chunk_text, embedding, start_line, end_line

        Returns:
            List of SemanticResult objects sorted by similarity.
        """
        # Get query embedding
        query_embedding = self.embed_query(query)
        if not query_embedding:
            return []

        return self.search_with_embedding(query_embedding, indexed_chunks)

    def search_with_embedding(
        self,
        query_embedding: list[float],
        indexed_chunks: list[dict[str, Any]],
    ) -> list[SemanticResult]:
        """Search using a pre-computed query embedding.

        Args:
            query_embedding: Pre-computed embedding vector.
            indexed_chunks: List of chunk records with embeddings.

        Returns:
            List of SemanticResult objects sorted by similarity.
        """
        results: list[SemanticResult] = []

        for chunk in indexed_chunks:
            chunk_embedding = chunk.get("embedding")
            if not chunk_embedding:
                continue

            # Calculate similarity
            similarity = self.cosine_similarity(query_embedding, chunk_embedding)

            if similarity >= self.min_score:
                results.append(
                    SemanticResult(
                        file_path=chunk.get("file_path", ""),
                        filename=chunk.get("filename", ""),
                        chunk_index=chunk.get("chunk_index", 0),
                        chunk_text=chunk.get("chunk_text", ""),
                        similarity_score=similarity,
                        start_line=chunk.get("start_line"),
                        end_line=chunk.get("end_line"),
                    )
                )

        # Sort by similarity descending
        results.sort(key=lambda r: r.similarity_score, reverse=True)
        return results[: self.max_results]

    def search_files(
        self,
        query: str,
        indexed_chunks: list[dict[str, Any]],
    ) -> list[SemanticResult]:
        """Search and group results by file.

        Returns the best matching chunk for each unique file.

        Args:
            query: Natural language search query.
            indexed_chunks: List of chunk records with embeddings.

        Returns:
            List of SemanticResult objects, one per file.
        """
        all_results = self.search(query, indexed_chunks)

        # Group by file, keeping best score per file
        file_results: dict[str, SemanticResult] = {}
        for result in all_results:
            path = result.file_path
            if (
                path not in file_results
                or result.similarity_score > file_results[path].similarity_score
            ):
                file_results[path] = result

        # Sort by score
        results = list(file_results.values())
        results.sort(key=lambda r: r.similarity_score, reverse=True)
        return results[: self.max_results]

    def rerank_results(
        self,
        results: list[SemanticResult],
        query: str,
        boost_factors: dict[str, float] | None = None,
    ) -> list[SemanticResult]:
        """Apply additional ranking factors to results.

        Args:
            results: List of semantic results.
            query: Original query for context.
            boost_factors: Optional dict mapping extensions to boost factors.

        Returns:
            Re-ranked results.
        """
        if not boost_factors:
            boost_factors = {
                ".py": 1.1,
                ".md": 1.05,
                ".txt": 1.0,
            }

        for result in results:
            # Apply extension boost
            for ext, boost in boost_factors.items():
                if result.file_path.endswith(ext):
                    result.similarity_score *= boost
                    break

            # Cap at 1.0
            result.similarity_score = min(result.similarity_score, 1.0)

        results.sort(key=lambda r: r.similarity_score, reverse=True)
        return results
