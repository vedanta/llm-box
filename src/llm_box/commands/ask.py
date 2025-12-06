"""Ask questions about files or code using LLM.

This command allows users to ask natural language questions about
files, code, or project context.
"""

from pathlib import Path
from typing import Any

from llm_box.cache import generate_cache_key
from llm_box.commands.base import BaseCommand, CommandContext, CommandResult
from llm_box.commands.registry import CommandRegistry
from llm_box.utils.hashing import hash_content


@CommandRegistry.register
class AskCommand(BaseCommand):
    """Ask questions about files or code using LLM."""

    @property
    def name(self) -> str:
        return "ask"

    @property
    def description(self) -> str:
        return "Ask questions about files or code"

    @property
    def aliases(self) -> list[str]:
        return ["question", "q"]

    def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
        """Execute the ask command.

        Args:
            ctx: Command context with provider, cache, etc.
            **kwargs: Command arguments:
                - question: The question to ask
                - file: Optional file to provide as context
                - files: Optional list of files to provide as context
                - context: Additional context string

        Returns:
            CommandResult with the answer.
        """
        question = kwargs.get("question")
        if not question:
            return CommandResult.fail("No question specified")

        file_str = kwargs.get("file")
        files_list = kwargs.get("files", [])
        extra_context = kwargs.get("context", "")

        # Gather file contents for context
        file_contexts = []

        # Single file
        if file_str:
            file_context = self._read_file_context(file_str)
            if file_context:
                file_contexts.append(file_context)

        # Multiple files
        for f in files_list:
            file_context = self._read_file_context(f)
            if file_context:
                file_contexts.append(file_context)

        # Build context string
        context_str = ""
        if file_contexts:
            context_str = "\n\n".join(file_contexts)
        if extra_context:
            context_str += f"\n\nAdditional context:\n{extra_context}"

        # Generate cache key
        cache_key = generate_cache_key(
            command="ask",
            provider=ctx.provider.provider_type.value,
            model=ctx.provider.model_name,
            extra_params={
                "question_hash": hash_content(question),
                "context_hash": hash_content(context_str) if context_str else "",
            },
        )

        cached = None
        if ctx.use_cache:
            cached = ctx.cache.get(cache_key)

        if cached:
            answer = cached.response
            from_cache = True
        else:
            # Generate answer via LLM
            answer = self._generate_answer(ctx, question, context_str)
            from_cache = False

            # Cache the answer
            if ctx.use_cache and answer:
                ctx.cache.set(
                    key=cache_key,
                    command="ask",
                    provider=ctx.provider.provider_type.value,
                    model=ctx.provider.model_name,
                    response=answer,
                )

        return CommandResult.ok(
            data=answer,
            cached=from_cache,
            question=question,
            files_used=len(file_contexts),
        )

    def _read_file_context(self, file_str: str) -> str | None:
        """Read a file and format it as context."""
        try:
            file_path = Path(file_str).resolve()
            if not file_path.exists() or file_path.is_dir():
                return None

            content = self._read_file(file_path)
            if content is None:
                return None

            # Truncate if needed
            max_content = 6000
            if len(content) > max_content:
                content = content[:max_content] + "\n[... truncated ...]"

            return f"File: {file_path.name}\n```\n{content}\n```"
        except Exception:
            return None

    def _read_file(self, file_path: Path, max_size: int = 100_000) -> str | None:
        """Read file contents."""
        try:
            size = file_path.stat().st_size
            if size > max_size:
                return None
        except OSError:
            return None

        binary_extensions = {
            ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp",
            ".mp3", ".wav", ".ogg", ".flac", ".aac",
            ".mp4", ".avi", ".mkv", ".mov", ".webm",
            ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".pyc", ".pyo", ".class", ".o", ".a",
        }

        if file_path.suffix.lower() in binary_extensions:
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception:
                return None

    def _generate_answer(
        self,
        ctx: CommandContext,
        question: str,
        context_str: str,
    ) -> str:
        """Generate answer using LLM."""
        if context_str:
            prompt = f"""Answer the following question based on the provided context.

Context:
{context_str}

Question: {question}

Provide a clear, helpful answer. Use markdown formatting where appropriate.
If the question cannot be answered from the provided context, say so and provide any relevant insights you can."""
        else:
            prompt = f"""Answer the following question about software development or programming.

Question: {question}

Provide a clear, helpful answer. Use markdown formatting where appropriate.
Include code examples if relevant."""

        response = ctx.provider.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
