"""Unit tests for output formatters."""

import json
from io import StringIO

import pytest

from llm_box.output import (
    JSONFormatter,
    JSONLinesFormatter,
    OutputData,
    OutputFormat,
    PlainFormatter,
    RichFormatter,
    get_formatter,
)


class TestOutputData:
    """Tests for OutputData dataclass."""

    def test_create_output_data(self) -> None:
        """Test creating output data."""
        data = OutputData(content="Hello, world!")
        assert data.content == "Hello, world!"
        assert data.title is None
        assert data.metadata == {}
        assert data.cached is False
        assert data.error is None
        assert data.success is True

    def test_create_output_data_full(self) -> None:
        """Test creating output data with all fields."""
        data = OutputData(
            content="Content",
            title="Title",
            metadata={"key": "value"},
            cached=True,
            error=None,
            success=True,
        )
        assert data.title == "Title"
        assert data.metadata == {"key": "value"}
        assert data.cached is True

    def test_from_error(self) -> None:
        """Test creating error output data."""
        data = OutputData.from_error("Something went wrong", title="Error")
        assert data.success is False
        assert data.error == "Something went wrong"
        assert data.title == "Error"
        assert data.content == ""

    def test_from_content(self) -> None:
        """Test creating content output data."""
        data = OutputData.from_content(
            "Hello",
            title="Greeting",
            cached=True,
            tokens_used=100,
        )
        assert data.success is True
        assert data.content == "Hello"
        assert data.title == "Greeting"
        assert data.cached is True
        assert data.metadata == {"tokens_used": 100}

    def test_from_content_with_list(self) -> None:
        """Test creating output data with list content."""
        data = OutputData.from_content(["item1", "item2", "item3"])
        assert data.content == ["item1", "item2", "item3"]

    def test_from_content_with_dict(self) -> None:
        """Test creating output data with dict content."""
        data = OutputData.from_content({"key1": "value1", "key2": "value2"})
        assert data.content == {"key1": "value1", "key2": "value2"}


class TestPlainFormatter:
    """Tests for PlainFormatter."""

    @pytest.fixture
    def formatter(self) -> PlainFormatter:
        """Create a plain formatter."""
        return PlainFormatter()

    @pytest.fixture
    def verbose_formatter(self) -> PlainFormatter:
        """Create a verbose plain formatter."""
        return PlainFormatter(verbose=True)

    def test_format_type(self, formatter: PlainFormatter) -> None:
        """Test format type property."""
        assert formatter.format_type == OutputFormat.PLAIN

    def test_format_simple_content(self, formatter: PlainFormatter) -> None:
        """Test formatting simple string content."""
        data = OutputData(content="Hello, world!")
        result = formatter.format(data)
        assert result == "Hello, world!"

    def test_format_with_title(self, formatter: PlainFormatter) -> None:
        """Test formatting with title."""
        data = OutputData(content="Content here", title="My Title")
        result = formatter.format(data)
        assert "My Title" in result
        assert "Content here" in result
        assert "---" in result or "-" * len("My Title") in result

    def test_format_error(self, formatter: PlainFormatter) -> None:
        """Test formatting error output."""
        data = OutputData.from_error("Something went wrong")
        result = formatter.format(data)
        assert "Error:" in result
        assert "Something went wrong" in result

    def test_format_list_content(self, formatter: PlainFormatter) -> None:
        """Test formatting list content."""
        data = OutputData(content=["item1", "item2", "item3"])
        result = formatter.format(data)
        assert "item1" in result
        assert "item2" in result
        assert "item3" in result

    def test_format_dict_content(self, formatter: PlainFormatter) -> None:
        """Test formatting dict content."""
        data = OutputData(content={"name": "Alice", "age": 30})
        result = formatter.format(data)
        assert "name" in result
        assert "Alice" in result
        assert "age" in result
        assert "30" in result

    def test_format_with_metadata_verbose(
        self, verbose_formatter: PlainFormatter
    ) -> None:
        """Test that metadata shows in verbose mode."""
        data = OutputData(
            content="Content",
            metadata={"tokens": 100, "model": "gpt-4"},
        )
        result = verbose_formatter.format(data)
        assert "tokens" in result
        assert "100" in result

    def test_format_cached_verbose(self, verbose_formatter: PlainFormatter) -> None:
        """Test that cached indicator shows in verbose mode."""
        data = OutputData(content="Content", cached=True)
        result = verbose_formatter.format(data)
        assert "(cached)" in result

    def test_format_list(self, formatter: PlainFormatter) -> None:
        """Test format_list method."""
        result = formatter.format_list(["apple", "banana", "cherry"], title="Fruits")
        assert "Fruits" in result
        assert "apple" in result
        assert "banana" in result
        assert "cherry" in result

    def test_format_table(self, formatter: PlainFormatter) -> None:
        """Test format_table method."""
        rows = [
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "age": "25"},
        ]
        result = formatter.format_table(rows, title="People")
        assert "People" in result
        assert "name" in result
        assert "age" in result
        assert "Alice" in result
        assert "Bob" in result

    def test_format_code(self, formatter: PlainFormatter) -> None:
        """Test format_code method."""
        code = "def hello():\n    print('Hello')"
        result = formatter.format_code(code, language="python", title="Code")
        assert "Code" in result
        assert "def hello():" in result

    def test_print_to_stream(self) -> None:
        """Test printing to custom stream."""
        stream = StringIO()
        formatter = PlainFormatter(stream=stream)
        data = OutputData(content="Test output")
        formatter.print(data)
        assert "Test output" in stream.getvalue()


class TestJSONFormatter:
    """Tests for JSONFormatter."""

    @pytest.fixture
    def formatter(self) -> JSONFormatter:
        """Create a JSON formatter."""
        return JSONFormatter()

    @pytest.fixture
    def compact_formatter(self) -> JSONFormatter:
        """Create a compact JSON formatter."""
        return JSONFormatter(indent=None)

    def test_format_type(self, formatter: JSONFormatter) -> None:
        """Test format type property."""
        assert formatter.format_type == OutputFormat.JSON

    def test_format_simple_content(self, formatter: JSONFormatter) -> None:
        """Test formatting simple content."""
        data = OutputData(content="Hello, world!")
        result = formatter.format(data)
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["content"] == "Hello, world!"

    def test_format_with_title(self, formatter: JSONFormatter) -> None:
        """Test formatting with title."""
        data = OutputData(content="Content", title="Title")
        result = formatter.format(data)
        parsed = json.loads(result)
        assert parsed["title"] == "Title"

    def test_format_error(self, formatter: JSONFormatter) -> None:
        """Test formatting error."""
        data = OutputData.from_error("Something went wrong")
        result = formatter.format(data)
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert parsed["error"] == "Something went wrong"

    def test_format_cached(self, formatter: JSONFormatter) -> None:
        """Test formatting cached content."""
        data = OutputData(content="Content", cached=True)
        result = formatter.format(data)
        parsed = json.loads(result)
        assert parsed["cached"] is True

    def test_format_list(self, formatter: JSONFormatter) -> None:
        """Test format_list method."""
        result = formatter.format_list(["a", "b", "c"], title="Letters")
        parsed = json.loads(result)
        assert parsed["items"] == ["a", "b", "c"]
        assert parsed["count"] == 3
        assert parsed["title"] == "Letters"

    def test_format_table(self, formatter: JSONFormatter) -> None:
        """Test format_table method."""
        rows = [{"name": "Alice"}, {"name": "Bob"}]
        result = formatter.format_table(rows, title="People")
        parsed = json.loads(result)
        assert parsed["rows"] == rows
        assert parsed["count"] == 2

    def test_format_code(self, formatter: JSONFormatter) -> None:
        """Test format_code method."""
        result = formatter.format_code("print('hi')", language="python")
        parsed = json.loads(result)
        assert parsed["code"] == "print('hi')"
        assert parsed["language"] == "python"

    def test_compact_output(self, compact_formatter: JSONFormatter) -> None:
        """Test compact JSON output."""
        data = OutputData(content="Hello")
        result = compact_formatter.format(data)
        # Compact should have no newlines
        assert "\n" not in result


class TestJSONLinesFormatter:
    """Tests for JSONLinesFormatter."""

    @pytest.fixture
    def formatter(self) -> JSONLinesFormatter:
        """Create a JSONL formatter."""
        return JSONLinesFormatter()

    def test_format_list_as_lines(self, formatter: JSONLinesFormatter) -> None:
        """Test that list items become separate JSON lines."""
        result = formatter.format_list(["a", "b", "c"])
        lines = result.strip().split("\n")
        assert len(lines) == 3
        for line in lines:
            parsed = json.loads(line)
            assert "item" in parsed

    def test_format_table_as_lines(self, formatter: JSONLinesFormatter) -> None:
        """Test that table rows become separate JSON lines."""
        rows = [{"name": "Alice"}, {"name": "Bob"}]
        result = formatter.format_table(rows)
        lines = result.strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["name"] == "Alice"
        assert json.loads(lines[1])["name"] == "Bob"


class TestRichFormatter:
    """Tests for RichFormatter."""

    @pytest.fixture
    def formatter(self) -> RichFormatter:
        """Create a Rich formatter."""
        return RichFormatter()

    def test_format_type(self, formatter: RichFormatter) -> None:
        """Test format type property."""
        assert formatter.format_type == OutputFormat.RICH

    def test_format_simple_content(self, formatter: RichFormatter) -> None:
        """Test formatting simple content."""
        data = OutputData(content="Hello, world!")
        result = formatter.format(data)
        assert "Hello, world!" in result

    def test_format_error(self, formatter: RichFormatter) -> None:
        """Test formatting error."""
        data = OutputData.from_error("Something went wrong")
        result = formatter.format(data)
        assert "Error" in result
        assert "Something went wrong" in result

    def test_format_list_content(self, formatter: RichFormatter) -> None:
        """Test formatting list content."""
        data = OutputData(content=["item1", "item2"])
        result = formatter.format(data)
        assert "item1" in result
        assert "item2" in result

    def test_format_dict_content(self, formatter: RichFormatter) -> None:
        """Test formatting dict content."""
        data = OutputData(content={"key": "value"})
        result = formatter.format(data)
        assert "key" in result
        assert "value" in result

    def test_format_list(self, formatter: RichFormatter) -> None:
        """Test format_list method."""
        result = formatter.format_list(["apple", "banana"])
        assert "apple" in result
        assert "banana" in result

    def test_format_table(self, formatter: RichFormatter) -> None:
        """Test format_table method."""
        rows = [{"name": "Alice", "age": "30"}]
        result = formatter.format_table(rows, columns=["name", "age"])
        assert "Alice" in result
        assert "30" in result

    def test_format_code(self, formatter: RichFormatter) -> None:
        """Test format_code method."""
        code = "def hello(): pass"
        result = formatter.format_code(code, language="python")
        assert "def" in result
        assert "hello" in result

    def test_markdown_detection(self, formatter: RichFormatter) -> None:
        """Test markdown content detection."""
        # Test various markdown indicators
        assert formatter._looks_like_markdown("# Header")
        assert formatter._looks_like_markdown("## Subheader")
        assert formatter._looks_like_markdown("```python\ncode\n```")
        assert formatter._looks_like_markdown("- list item")
        assert formatter._looks_like_markdown("**bold**")
        assert not formatter._looks_like_markdown("plain text")


class TestGetFormatter:
    """Tests for get_formatter factory function."""

    def test_get_plain_formatter(self) -> None:
        """Test getting plain formatter."""
        formatter = get_formatter(OutputFormat.PLAIN)
        assert isinstance(formatter, PlainFormatter)

    def test_get_json_formatter(self) -> None:
        """Test getting JSON formatter."""
        formatter = get_formatter(OutputFormat.JSON)
        assert isinstance(formatter, JSONFormatter)

    def test_get_rich_formatter(self) -> None:
        """Test getting Rich formatter."""
        formatter = get_formatter(OutputFormat.RICH)
        assert isinstance(formatter, RichFormatter)

    def test_get_formatter_by_string(self) -> None:
        """Test getting formatter by string name."""
        formatter = get_formatter("plain")
        assert isinstance(formatter, PlainFormatter)

        formatter = get_formatter("json")
        assert isinstance(formatter, JSONFormatter)

        formatter = get_formatter("rich")
        assert isinstance(formatter, RichFormatter)

    def test_get_formatter_with_verbose(self) -> None:
        """Test getting formatter with verbose option."""
        formatter = get_formatter(OutputFormat.PLAIN, verbose=True)
        assert formatter.verbose is True

    def test_get_formatter_invalid_type(self) -> None:
        """Test getting formatter with invalid type."""
        with pytest.raises(ValueError):
            get_formatter("invalid")


class TestOutputFormatEnum:
    """Tests for OutputFormat enum."""

    def test_enum_values(self) -> None:
        """Test enum values."""
        assert OutputFormat.PLAIN == "plain"
        assert OutputFormat.JSON == "json"
        assert OutputFormat.RICH == "rich"

    def test_enum_from_string(self) -> None:
        """Test creating enum from string."""
        assert OutputFormat("plain") == OutputFormat.PLAIN
        assert OutputFormat("json") == OutputFormat.JSON
        assert OutputFormat("rich") == OutputFormat.RICH
