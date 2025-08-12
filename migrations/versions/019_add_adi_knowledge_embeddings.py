"""Add ADI knowledge embeddings support

Revision ID: 019_add_adi_knowledge_embeddings
Revises: 018_add_needs_rework_task_status
Create Date: 2025-01-11 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '019_add_adi_knowledge_embeddings'
down_revision = '018_add_needs_rework_task_status'
branch_labels = None
depends_on = None


def upgrade():
    # Check if tables exist and create only if they don't
    connection = op.get_bind()
    
    # Check if adi_knowledge table exists
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'adi_knowledge'
        );
    """))
    adi_knowledge_exists = result.scalar()
    
    if not adi_knowledge_exists:
        # Create adi_knowledge table
        op.create_table('adi_knowledge',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('project_id', sa.String(255), nullable=False, index=True),
            sa.Column('title', sa.Text, nullable=False),
            sa.Column('content', sa.Text, nullable=False),
            sa.Column('rule_yaml', sa.Text, nullable=True),
            sa.Column('scope_filters', postgresql.JSONB, default={}),
            sa.Column('source_link', sa.Text, nullable=True),
            sa.Column('author', sa.String(255), nullable=False),
            sa.Column('tags', postgresql.ARRAY(sa.String), default=[]),
            sa.Column('version', sa.Integer, default=1),
            sa.Column('embedding', postgresql.ARRAY(sa.Float), nullable=True),
            sa.Column('embedding_model', sa.String(100), nullable=True),
            sa.Column('embedding_generated_at', sa.DateTime, nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'), index=True),
            sa.Column('updated_at', sa.DateTime, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
            sa.Index('idx_project_author', 'project_id', 'author'),
            sa.Index('idx_project_version', 'project_id', 'version')
        )
    else:
        # Add embedding columns to existing table if they don't exist
        try:
            op.add_column('adi_knowledge', sa.Column('embedding', postgresql.ARRAY(sa.Float), nullable=True))
        except Exception:
            pass  # Column already exists
        try:
            op.add_column('adi_knowledge', sa.Column('embedding_model', sa.String(100), nullable=True))
        except Exception:
            pass  # Column already exists
        try:
            op.add_column('adi_knowledge', sa.Column('embedding_generated_at', sa.DateTime, nullable=True))
        except Exception:
            pass  # Column already exists
    
    # Check if document_chunks table exists
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'document_chunks'
        );
    """))
    document_chunks_exists = result.scalar()
    
    if not document_chunks_exists:
        # Create document_chunks table for general vector storage (used by existing vector service)
        op.create_table('document_chunks',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('document_id', sa.String(255), nullable=False, index=True),
            sa.Column('document_type', sa.String(100), nullable=False, index=True),
            sa.Column('chunk_index', sa.Integer, nullable=False),
            sa.Column('content', sa.Text, nullable=False),
            sa.Column('embedding', postgresql.ARRAY(sa.Float), nullable=True),
            sa.Column('metadata', postgresql.JSONB, nullable=True),
            sa.Column('token_count', sa.Integer, nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
            sa.Index('idx_document_chunks_doc_type', 'document_id', 'document_type')
        )
    
    # Create fallback functions using cosine similarity with arrays
    op.execute("""
        CREATE OR REPLACE FUNCTION array_cosine_similarity(a float[], b float[])
        RETURNS float
        LANGUAGE sql IMMUTABLE
        AS $$
            SELECT 
                CASE 
                    WHEN array_length(a, 1) IS NULL OR array_length(b, 1) IS NULL THEN 0
                    WHEN array_length(a, 1) != array_length(b, 1) THEN 0
                    ELSE (
                        SELECT COALESCE(
                            SUM(a_val * b_val) / NULLIF(
                                SQRT(SUM(a_val * a_val)) * SQRT(SUM(b_val * b_val)), 0
                            ), 0
                        )
                        FROM (
                            SELECT 
                                unnest(a) as a_val,
                                unnest(b) as b_val
                        ) t
                    )
                END;
        $$;
    """)
    
    # Create semantic search function for knowledge (fallback version)
    op.execute("""
        CREATE OR REPLACE FUNCTION adi_knowledge_semantic_search(
            query_embedding float[],
            project_filter text DEFAULT NULL,
            result_limit integer DEFAULT 10,
            similarity_threshold real DEFAULT 0.3
        )
        RETURNS TABLE (
            id uuid,
            project_id text,
            title text,
            content text,
            similarity_score real,
            author text,
            tags text[],
            version integer,
            created_at timestamp,
            updated_at timestamp
        )
        LANGUAGE sql STABLE
        AS $$
            SELECT 
                k.id,
                k.project_id,
                k.title,
                k.content,
                array_cosine_similarity(k.embedding, query_embedding) as similarity_score,
                k.author,
                k.tags,
                k.version,
                k.created_at,
                k.updated_at
            FROM adi_knowledge k
            WHERE k.embedding IS NOT NULL
                AND (project_filter IS NULL OR k.project_id = project_filter)
                AND array_cosine_similarity(k.embedding, query_embedding) >= similarity_threshold
            ORDER BY array_cosine_similarity(k.embedding, query_embedding) DESC
            LIMIT result_limit;
        $$;
    """)
    
    # Create semantic search function for document chunks (fallback version)
    # Handle both JSONB and FLOAT[] embedding columns
    op.execute("""
        CREATE OR REPLACE FUNCTION semantic_search(
            query_embedding float[],
            document_types text[] DEFAULT NULL,
            result_limit integer DEFAULT 10,
            similarity_threshold real DEFAULT 0.3
        )
        RETURNS TABLE (
            document_id text,
            document_type text,
            chunk_index integer,
            content text,
            similarity_score real,
            metadata jsonb,
            token_count integer
        )
        LANGUAGE sql STABLE
        AS $$
            SELECT 
                dc.document_id,
                dc.document_type,
                dc.chunk_index,
                dc.content,
                CASE 
                    WHEN dc.embedding IS NOT NULL AND jsonb_typeof(dc.embedding::jsonb) = 'array' THEN
                        array_cosine_similarity(
                            ARRAY(SELECT jsonb_array_elements_text(dc.embedding::jsonb)::float),
                            query_embedding
                        )
                    ELSE 0.0
                END as similarity_score,
                dc.metadata,
                dc.token_count
            FROM document_chunks dc
            WHERE dc.embedding IS NOT NULL
                AND (document_types IS NULL OR dc.document_type = ANY(document_types))
                AND CASE 
                    WHEN dc.embedding IS NOT NULL AND jsonb_typeof(dc.embedding::jsonb) = 'array' THEN
                        array_cosine_similarity(
                            ARRAY(SELECT jsonb_array_elements_text(dc.embedding::jsonb)::float),
                            query_embedding
                        ) >= similarity_threshold
                    ELSE false
                END
            ORDER BY similarity_score DESC
            LIMIT result_limit;
        $$;
    """)


def downgrade():
    # Drop functions
    op.execute('DROP FUNCTION IF EXISTS adi_knowledge_semantic_search')
    op.execute('DROP FUNCTION IF EXISTS semantic_search')
    op.execute('DROP FUNCTION IF EXISTS array_cosine_similarity')
    
    # Drop tables
    op.drop_table('document_chunks')
    op.drop_table('adi_knowledge')