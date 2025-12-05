"""Find files using semantic and fuzzy search.

This command searches for files using natural language queries
(semantic search) and/or approximate string matching (fuzzy search).
"""

from pathlib import Path
from typing import Any

from llm_box.commands.base import BaseCommand, CommandContext, CommandResult
from llm_box.commands.registry import CommandRegistry
from llm_box.search import SearchEngine, SearchMode


@CommandRegistry.register
class FindCommand(BaseCommand):
    """Search for files using semantic and fuzzy matching."""

    @property
    def name(self) -> str:
        return "find"

    @property
    def description(self) -> str:
        return "Search for files using semantic and fuzzy matching"

    @property
    def aliases(self) -> list[str]:
        return ["search", "grep"]

    def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
        """Execute the find command.

        Args:
            ctx: Command context with provider, cache, etc.
            **kwargs: Command arguments:
                - query: Search query string
                - path: Directory to search in (default: ".")
                - mode: Search mode (fuzzy, semantic, combined)
                - top_k: Number of results to return (default: 10)
                - extensions: Filter by extensions (e.g., [".py", ".js"])
                - index: Whether to index before searching (default: False)

        Returns:
            CommandResult with search results.
        """
        query = kwargs.get("query")
        if not query:
            return CommandResult.fail("No search query provided")

        path_str = kwargs.get("path", ".")
        mode_str = kwargs.get("mode", "combined")
        top_k = kwargs.get("top_k", 10)
        extensions = kwargs.get("extensions")
        do_index = kwargs.get("index", False)

        # Resolve path
        try:
            search_path = Path(path_str).resolve()
            if not search_path.exists():
                return CommandResult.fail(f"Path does not exist: {path_str}")
            if not search_path.is_dir():
                return CommandResult.fail(f"Not a directory: {path_str}")
        except Exception as e:
            return CommandResult.fail(f"Invalid path: {e}")

        # Parse search mode
        try:
            mode = SearchMode(mode_str.lower())
        except ValueError:
            valid_modes = [m.value for m in SearchMode]
            return CommandResult.fail(
                f"Invalid mode '{mode_str}'. Valid options: {', '.join(valid_modes)}"
            )

        # Initialize search engine
        # Use a database in the user's cache directory
        db_path = self._get_db_path()
        engine = SearchEngine(
            db_path=db_path,
            provider=ctx.provider if mode != SearchMode.FUZZY else None,
        )

        try:
            # Index if requested
            index_stats = None
            if do_index:
                index_stats = engine.index_directory(
                    search_path,
                    extensions=extensions,
                    generate_embeddings=(mode != SearchMode.FUZZY),
                )

            # Check if we have indexed files
            stats = engine.get_index_stats()
            if stats["total_files"] == 0:
                # Auto-index if no files found
                if ctx.verbose:
                    index_stats = engine.index_directory(
                        search_path,
                        extensions=extensions,
                        generate_embeddings=(mode != SearchMode.FUZZY),
                    )
                else:
                    return CommandResult.fail(
                        "No files indexed. Run with --index to index first, "
                        "or use 'llm-box index' command."
                    )

            # Perform search
            response = engine.search(
                query=query,
                path=search_path,
                mode=mode,
                top_k=top_k,
                extensions=extensions,
            )

            # Build result data
            results_data = []
            for result in response.results:
                results_data.append({
                    "file_path": result.file_path,
                    "filename": result.filename,
                    "score": round(result.score, 3),
                    "match_type": result.match_type,
                    "preview": result.preview[:200] if result.preview else "",
                    "language": result.language,
                    "line_number": result.line_number,
                    "fuzzy_score": round(result.fuzzy_score, 3) if result.fuzzy_score else None,
                    "semantic_score": round(result.semantic_score, 3) if result.semantic_score else None,
                })

            return CommandResult.ok(
                data={
                    "query": query,
                    "mode": mode.value,
                    "results": results_data,
                    "count": len(results_data),
                    "total_files_searched": response.total_files_searched,
                    "search_time_ms": round(response.search_time_ms, 2),
                    "index_stats": {
                        "files_indexed": index_stats.files_indexed if index_stats else 0,
                        "files_updated": index_stats.files_updated if index_stats else 0,
                    } if index_stats else None,
                }
            )

        except Exception as e:
            return CommandResult.fail(f"Search error: {e}")
        finally:
            engine.close()

    def _get_db_path(self) -> Path:
        """Get path to the search database."""
        cache_dir = Path.home() / ".cache" / "llm-box"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "search.duckdb"


@CommandRegistry.register
class IndexCommand(BaseCommand):
    """Index files for search."""

    @property
    def name(self) -> str:
        return "index"

    @property
    def description(self) -> str:
        return "Index files for search"

    @property
    def aliases(self) -> list[str]:
        return []

    def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
        """Execute the index command.

        Args:
            ctx: Command context with provider, cache, etc.
            **kwargs: Command arguments:
                - path: Directory to index (default: ".")
                - extensions: Filter by extensions
                - force: Force re-index all files
                - no_embeddings: Skip embedding generation

        Returns:
            CommandResult with indexing statistics.
        """
        path_str = kwargs.get("path", ".")
        extensions = kwargs.get("extensions")
        force = kwargs.get("force", False)
        no_embeddings = kwargs.get("no_embeddings", False)

        # Resolve path
        try:
            index_path = Path(path_str).resolve()
            if not index_path.exists():
                return CommandResult.fail(f"Path does not exist: {path_str}")
            if not index_path.is_dir():
                return CommandResult.fail(f"Not a directory: {path_str}")
        except Exception as e:
            return CommandResult.fail(f"Invalid path: {e}")

        # Initialize search engine
        db_path = self._get_db_path()
        engine = SearchEngine(
            db_path=db_path,
            provider=ctx.provider if not no_embeddings else None,
        )

        try:
            stats = engine.index_directory(
                index_path,
                extensions=extensions,
                force_reindex=force,
                generate_embeddings=not no_embeddings,
            )

            return CommandResult.ok(
                data={
                    "path": str(index_path),
                    "files_indexed": stats.files_indexed,
                    "files_updated": stats.files_updated,
                    "files_unchanged": stats.files_unchanged,
                    "files_skipped": stats.files_skipped,
                    "errors": stats.errors,
                    "error_details": stats.error_details[:10] if stats.error_details else [],
                }
            )

        except Exception as e:
            return CommandResult.fail(f"Indexing error: {e}")
        finally:
            engine.close()

    def _get_db_path(self) -> Path:
        """Get path to the search database."""
        cache_dir = Path.home() / ".cache" / "llm-box"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "search.duckdb"
