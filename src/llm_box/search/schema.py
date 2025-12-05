"""DuckDB schema for search functionality.

This module defines the database schema for file indexing and
vector embeddings used by the search system.
"""

# Sequences for auto-incrementing IDs
CREATE_SEQUENCES = [
    "CREATE SEQUENCE IF NOT EXISTS file_index_seq START 1",
    "CREATE SEQUENCE IF NOT EXISTS embeddings_seq START 1",
    "CREATE SEQUENCE IF NOT EXISTS search_history_seq START 1",
]

# SQL statements for file index table
CREATE_FILE_INDEX_TABLE = """
    CREATE TABLE IF NOT EXISTS file_index (
        id INTEGER PRIMARY KEY DEFAULT nextval('file_index_seq'),
        file_path VARCHAR NOT NULL UNIQUE,
        filename VARCHAR NOT NULL,
        extension VARCHAR,
        file_hash VARCHAR NOT NULL,
        size_bytes INTEGER,
        modified_at TIMESTAMP,
        indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        content_preview VARCHAR(2000),
        is_hidden BOOLEAN DEFAULT FALSE,
        is_binary BOOLEAN DEFAULT FALSE,
        language VARCHAR,
        line_count INTEGER
    )
"""

CREATE_FILE_INDEX_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_file_filename ON file_index(filename)",
    "CREATE INDEX IF NOT EXISTS idx_file_extension ON file_index(extension)",
    "CREATE INDEX IF NOT EXISTS idx_file_hash ON file_index(file_hash)",
    "CREATE INDEX IF NOT EXISTS idx_file_language ON file_index(language)",
]

# SQL statements for embeddings table
CREATE_EMBEDDINGS_TABLE = """
    CREATE TABLE IF NOT EXISTS embeddings (
        id INTEGER PRIMARY KEY DEFAULT nextval('embeddings_seq'),
        file_id INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        chunk_text VARCHAR(2000),
        embedding FLOAT[],
        model VARCHAR NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(file_id, chunk_index)
    )
"""

CREATE_EMBEDDINGS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_emb_file_id ON embeddings(file_id)",
    "CREATE INDEX IF NOT EXISTS idx_emb_model ON embeddings(model)",
]

# SQL statements for search history (optional, for suggestions)
CREATE_SEARCH_HISTORY_TABLE = """
    CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY DEFAULT nextval('search_history_seq'),
        query VARCHAR NOT NULL,
        search_type VARCHAR,
        result_count INTEGER,
        searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

# All schema creation statements (sequences must come first)
ALL_TABLES = CREATE_SEQUENCES + [
    CREATE_FILE_INDEX_TABLE,
    CREATE_EMBEDDINGS_TABLE,
    CREATE_SEARCH_HISTORY_TABLE,
]

ALL_INDEXES = CREATE_FILE_INDEX_INDEXES + CREATE_EMBEDDINGS_INDEXES
