"""
Vector Database Setup Utility
Sets up the necessary tables and functions for vector similarity search
"""

import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def setup_vector_database(db):
    """
    Set up vector database tables and functions
    
    Args:
        db: SQLAlchemy database instance
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Setting up vector database tables and functions...")
        
        # Try to enable pgvector extension
        logger.info("Enabling pgvector extension...")
        try:
            db.session.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
            db.session.commit()  # Commit the extension creation
            logger.info("pgvector extension enabled successfully")
            use_pgvector = True
        except Exception as e:
            logger.warning(f"pgvector extension not available: {e}")
            logger.info("Falling back to basic vector storage without pgvector optimizations")
            db.session.rollback()  # Rollback the failed transaction
            use_pgvector = False
        
        # Create document_chunks table
        logger.info("Creating document_chunks table...")
        if use_pgvector:
            create_table_sql = text("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    document_id VARCHAR(100) NOT NULL,
                    document_type VARCHAR(50) NOT NULL, -- 'code_file', 'conversation', 'system_map', 'documentation'
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(384), -- Using sentence-transformers all-MiniLM-L6-v2 model (384 dimensions)
                    metadata JSONB DEFAULT '{}',
                    token_count INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
        else:
            # Fallback table without pgvector - store embeddings as JSON
            create_table_sql = text("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    document_id VARCHAR(100) NOT NULL,
                    document_type VARCHAR(50) NOT NULL, -- 'code_file', 'conversation', 'system_map', 'documentation'
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding JSONB, -- Store embedding as JSON array when pgvector not available
                    metadata JSONB DEFAULT '{}',
                    token_count INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
        db.session.execute(create_table_sql)
        
        # Create indexes for efficient vector search
        logger.info("Creating indexes...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_document_chunks_document ON document_chunks(document_id, document_type)",
            "CREATE INDEX IF NOT EXISTS idx_document_chunks_type ON document_chunks(document_type)",
            "CREATE INDEX IF NOT EXISTS idx_document_chunks_metadata ON document_chunks USING GIN(metadata)",
            "CREATE INDEX IF NOT EXISTS idx_document_chunks_fts ON document_chunks USING GIN(to_tsvector('english', content))"
        ]
        
        for index_sql in indexes:
            db.session.execute(text(index_sql))
        
        # Create vector similarity index (HNSW) - only if pgvector is available
        if use_pgvector:
            logger.info("Creating vector similarity index...")
            vector_index_sql = text("""
                CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON document_chunks 
                USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
            """)
            db.session.execute(vector_index_sql)
        else:
            logger.info("Skipping vector index creation (pgvector not available)")
        
        # Create update trigger function
        logger.info("Creating update trigger...")
        trigger_function_sql = text("""
            CREATE OR REPLACE FUNCTION update_modified_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """)
        db.session.execute(trigger_function_sql)
        
        # Create trigger (drop first if exists)
        drop_trigger_sql = text("""
            DROP TRIGGER IF EXISTS update_document_chunks_modtime ON document_chunks
        """)
        db.session.execute(drop_trigger_sql)
        
        trigger_sql = text("""
            CREATE TRIGGER update_document_chunks_modtime
                BEFORE UPDATE ON document_chunks
                FOR EACH ROW
                EXECUTE FUNCTION update_modified_column()
        """)
        db.session.execute(trigger_sql)
        
        # Create semantic search function - only if pgvector is available
        if use_pgvector:
            logger.info("Creating semantic search function...")
            semantic_search_sql = text("""
                CREATE OR REPLACE FUNCTION semantic_search(
                    p_query_embedding vector(384),
                    p_document_types text[] DEFAULT NULL,
                    p_limit integer DEFAULT 10,
                    p_similarity_threshold decimal DEFAULT 0.3
                )
                RETURNS TABLE (
                    document_id varchar,
                    document_type varchar,
                    chunk_index integer,
                    content text,
                    similarity_score decimal,
                    metadata jsonb,
                    token_count integer
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        dc.document_id,
                        dc.document_type,
                        dc.chunk_index,
                        dc.content,
                        (1 - (dc.embedding <=> p_query_embedding))::DECIMAL as similarity_score,
                        dc.metadata,
                        dc.token_count
                    FROM document_chunks dc
                    WHERE 
                        (p_document_types IS NULL OR dc.document_type = ANY(p_document_types))
                        AND (1 - (dc.embedding <=> p_query_embedding)) >= p_similarity_threshold
                    ORDER BY dc.embedding <=> p_query_embedding
                    LIMIT p_limit;
                END;
                $$ LANGUAGE plpgsql
            """)
            db.session.execute(semantic_search_sql)
        else:
            logger.info("Skipping semantic search function creation (pgvector not available)")
        
        # Create hybrid search function - only if pgvector is available
        if use_pgvector:
            logger.info("Creating hybrid search function...")
            hybrid_search_sql = text("""
                CREATE OR REPLACE FUNCTION hybrid_search(
                    p_query_embedding vector(384),
                    p_keywords text,
                    p_document_types text[] DEFAULT NULL,
                    p_limit integer DEFAULT 10,
                    p_semantic_weight decimal DEFAULT 0.7,
                    p_keyword_weight decimal DEFAULT 0.3
                )
                RETURNS TABLE (
                    document_id varchar,
                    document_type varchar,
                    chunk_index integer,
                    content text,
                    combined_score decimal,
                    semantic_score decimal,
                    keyword_score decimal,
                    metadata jsonb
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        dc.document_id,
                        dc.document_type,
                        dc.chunk_index,
                        dc.content,
                        (p_semantic_weight * (1 - (dc.embedding <=> p_query_embedding)) + 
                         p_keyword_weight * ts_rank(to_tsvector('english', dc.content), plainto_tsquery('english', p_keywords)))::DECIMAL as combined_score,
                        (1 - (dc.embedding <=> p_query_embedding))::DECIMAL as semantic_score,
                        ts_rank(to_tsvector('english', dc.content), plainto_tsquery('english', p_keywords))::DECIMAL as keyword_score,
                        dc.metadata
                    FROM document_chunks dc
                    WHERE 
                        (p_document_types IS NULL OR dc.document_type = ANY(p_document_types))
                    ORDER BY combined_score DESC
                    LIMIT p_limit;
                END;
                $$ LANGUAGE plpgsql
            """)
            db.session.execute(hybrid_search_sql)
        else:
            logger.info("Skipping hybrid search function creation (pgvector not available)")
        
        # Create find related context function - only if pgvector is available
        if use_pgvector:
            logger.info("Creating find related context function...")
            related_context_sql = text("""
                CREATE OR REPLACE FUNCTION find_related_context(
                    p_document_id varchar,
                    p_document_type varchar,
                    p_limit integer DEFAULT 5
                )
                RETURNS TABLE (
                    related_document_id varchar,
                    related_document_type varchar,
                    chunk_index integer,
                    content text,
                    similarity_score decimal,
                    metadata jsonb
                ) AS $$
                BEGIN
                    RETURN QUERY
                    WITH source_embedding AS (
                        SELECT embedding 
                        FROM document_chunks 
                        WHERE document_id = p_document_id AND document_type = p_document_type
                        ORDER BY chunk_index
                        LIMIT 1
                    )
                    SELECT 
                        dc.document_id as related_document_id,
                        dc.document_type as related_document_type,
                        dc.chunk_index,
                        dc.content,
                        (1 - (dc.embedding <=> se.embedding))::DECIMAL as similarity_score,
                        dc.metadata
                    FROM document_chunks dc, source_embedding se
                    WHERE 
                        NOT (dc.document_id = p_document_id AND dc.document_type = p_document_type)
                    ORDER BY dc.embedding <=> se.embedding
                    LIMIT p_limit;
                END;
                $$ LANGUAGE plpgsql
            """)
            db.session.execute(related_context_sql)
        else:
            logger.info("Skipping find related context function creation (pgvector not available)")
        
        # Commit all changes
        db.session.commit()
        
        logger.info("Vector database setup completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to set up vector database: {e}")
        db.session.rollback()
        return False