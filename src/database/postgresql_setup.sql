-- PostgreSQL Database Setup with Graph Extensions
-- Software Factory - Architecture Simplification

-- Create database and user if they don't exist
-- Note: This should be run as postgres superuser

-- Create user
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'sf_user') THEN

      CREATE ROLE sf_user LOGIN PASSWORD 'sf_password';
   END IF;
END
$do$;

-- Create database
SELECT 'CREATE DATABASE software_factory OWNER sf_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'software_factory')\gexec

-- Connect to the software_factory database
\c software_factory;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE software_factory TO sf_user;
GRANT ALL ON SCHEMA public TO sf_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sf_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sf_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO sf_user;

-- Enable required extensions for graph queries, JSON operations, and vector search
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "ltree";
CREATE EXTENSION IF NOT EXISTS "hstore";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create custom types for graph relationships
CREATE TYPE relationship_type AS ENUM (
    'depends_on',
    'contains',
    'implements',
    'extends',
    'calls',
    'imports',
    'references',
    'owns',
    'manages',
    'triggers'
);

-- Create graph relationship table for storing entity relationships
CREATE TABLE IF NOT EXISTS entity_relationships (
    id SERIAL PRIMARY KEY,
    source_entity_type VARCHAR(50) NOT NULL,
    source_entity_id VARCHAR(100) NOT NULL,
    target_entity_type VARCHAR(50) NOT NULL,
    target_entity_id VARCHAR(100) NOT NULL,
    relationship_type relationship_type NOT NULL,
    metadata JSONB DEFAULT '{}',
    weight DECIMAL(5,2) DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for efficient graph queries
CREATE INDEX IF NOT EXISTS idx_entity_relationships_source ON entity_relationships(source_entity_type, source_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_relationships_target ON entity_relationships(target_entity_type, target_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_relationships_type ON entity_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_entity_relationships_metadata ON entity_relationships USING GIN(metadata);

-- Create composite index for bidirectional relationship queries
CREATE INDEX IF NOT EXISTS idx_entity_relationships_bidirectional ON entity_relationships(
    source_entity_type, source_entity_id, target_entity_type, target_entity_id
);

-- Create function for recursive relationship queries
CREATE OR REPLACE FUNCTION find_related_entities(
    p_entity_type VARCHAR(50),
    p_entity_id VARCHAR(100),
    p_relationship_types relationship_type[] DEFAULT NULL,
    p_max_depth INTEGER DEFAULT 3,
    p_direction VARCHAR(10) DEFAULT 'both' -- 'outgoing', 'incoming', 'both'
)
RETURNS TABLE(
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    relationship_path relationship_type[],
    depth INTEGER,
    total_weight DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE relationship_tree AS (
        -- Base case: direct relationships
        SELECT 
            CASE 
                WHEN p_direction IN ('outgoing', 'both') THEN r.target_entity_type
                WHEN p_direction = 'incoming' THEN r.source_entity_type
            END as entity_type,
            CASE 
                WHEN p_direction IN ('outgoing', 'both') THEN r.target_entity_id
                WHEN p_direction = 'incoming' THEN r.source_entity_id
            END as entity_id,
            ARRAY[r.relationship_type] as relationship_path,
            1 as depth,
            r.weight as total_weight
        FROM entity_relationships r
        WHERE 
            (p_direction IN ('outgoing', 'both') AND r.source_entity_type = p_entity_type AND r.source_entity_id = p_entity_id)
            OR
            (p_direction IN ('incoming', 'both') AND r.target_entity_type = p_entity_type AND r.target_entity_id = p_entity_id)
            AND (p_relationship_types IS NULL OR r.relationship_type = ANY(p_relationship_types))
        
        UNION ALL
        
        -- Recursive case: follow relationships
        SELECT 
            CASE 
                WHEN p_direction IN ('outgoing', 'both') THEN r.target_entity_type
                WHEN p_direction = 'incoming' THEN r.source_entity_type
            END as entity_type,
            CASE 
                WHEN p_direction IN ('outgoing', 'both') THEN r.target_entity_id
                WHEN p_direction = 'incoming' THEN r.source_entity_id
            END as entity_id,
            rt.relationship_path || r.relationship_type,
            rt.depth + 1,
            rt.total_weight + r.weight
        FROM relationship_tree rt
        JOIN entity_relationships r ON 
            (p_direction IN ('outgoing', 'both') AND r.source_entity_type = rt.entity_type AND r.source_entity_id = rt.entity_id)
            OR
            (p_direction IN ('incoming', 'both') AND r.target_entity_type = rt.entity_type AND r.target_entity_id = rt.entity_id)
        WHERE 
            rt.depth < p_max_depth
            AND (p_relationship_types IS NULL OR r.relationship_type = ANY(p_relationship_types))
            AND NOT (rt.entity_type = p_entity_type AND rt.entity_id = p_entity_id) -- Avoid cycles
    )
    SELECT DISTINCT 
        rt.entity_type,
        rt.entity_id,
        rt.relationship_path,
        rt.depth,
        rt.total_weight
    FROM relationship_tree rt
    ORDER BY rt.depth, rt.total_weight DESC;
END;
$$ LANGUAGE plpgsql;

-- Create function to find shortest path between entities
CREATE OR REPLACE FUNCTION find_shortest_path(
    p_source_type VARCHAR(50),
    p_source_id VARCHAR(100),
    p_target_type VARCHAR(50),
    p_target_id VARCHAR(100),
    p_max_depth INTEGER DEFAULT 5
)
RETURNS TABLE(
    path_length INTEGER,
    relationship_path relationship_type[],
    entity_path TEXT[],
    total_weight DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE path_search AS (
        -- Base case: direct connection
        SELECT 
            1 as path_length,
            ARRAY[r.relationship_type] as relationship_path,
            ARRAY[p_source_type || ':' || p_source_id, r.target_entity_type || ':' || r.target_entity_id] as entity_path,
            r.weight as total_weight
        FROM entity_relationships r
        WHERE r.source_entity_type = p_source_type 
            AND r.source_entity_id = p_source_id
            AND r.target_entity_type = p_target_type 
            AND r.target_entity_id = p_target_id
        
        UNION ALL
        
        -- Recursive case: extend path
        SELECT 
            ps.path_length + 1,
            ps.relationship_path || r.relationship_type,
            ps.entity_path || (r.target_entity_type || ':' || r.target_entity_id),
            ps.total_weight + r.weight
        FROM path_search ps
        JOIN entity_relationships r ON 
            r.source_entity_type = split_part(ps.entity_path[array_length(ps.entity_path, 1)], ':', 1)
            AND r.source_entity_id = split_part(ps.entity_path[array_length(ps.entity_path, 1)], ':', 2)
        WHERE 
            ps.path_length < p_max_depth
            AND r.target_entity_type = p_target_type 
            AND r.target_entity_id = p_target_id
            AND NOT (r.target_entity_type || ':' || r.target_entity_id = ANY(ps.entity_path)) -- Avoid cycles
    )
    SELECT 
        ps.path_length,
        ps.relationship_path,
        ps.entity_path,
        ps.total_weight
    FROM path_search ps
    ORDER BY ps.path_length, ps.total_weight
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Create function to analyze entity centrality (how connected an entity is)
CREATE OR REPLACE FUNCTION calculate_entity_centrality(
    p_entity_type VARCHAR(50),
    p_entity_id VARCHAR(100)
)
RETURNS TABLE(
    in_degree INTEGER,
    out_degree INTEGER,
    total_degree INTEGER,
    weighted_in_degree DECIMAL,
    weighted_out_degree DECIMAL,
    centrality_score DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(incoming.count, 0) as in_degree,
        COALESCE(outgoing.count, 0) as out_degree,
        COALESCE(incoming.count, 0) + COALESCE(outgoing.count, 0) as total_degree,
        COALESCE(incoming.weight_sum, 0) as weighted_in_degree,
        COALESCE(outgoing.weight_sum, 0) as weighted_out_degree,
        (COALESCE(incoming.weight_sum, 0) + COALESCE(outgoing.weight_sum, 0)) / 
        GREATEST(COALESCE(incoming.count, 0) + COALESCE(outgoing.count, 0), 1) as centrality_score
    FROM 
        (SELECT 
            COUNT(*)::INTEGER as count,
            SUM(weight) as weight_sum
         FROM entity_relationships 
         WHERE target_entity_type = p_entity_type AND target_entity_id = p_entity_id
        ) incoming
    CROSS JOIN
        (SELECT 
            COUNT(*)::INTEGER as count,
            SUM(weight) as weight_sum
         FROM entity_relationships 
         WHERE source_entity_type = p_entity_type AND source_entity_id = p_entity_id
        ) outgoing;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to update timestamps
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_entity_relationships_modtime
    BEFORE UPDATE ON entity_relationships
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- Create view for easy relationship browsing
CREATE OR REPLACE VIEW relationship_summary AS
SELECT 
    source_entity_type,
    source_entity_id,
    target_entity_type,
    target_entity_id,
    relationship_type,
    weight,
    metadata,
    created_at
FROM entity_relationships
ORDER BY created_at DESC;

-- Create vector database tables for semantic search
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
);

-- Create indexes for efficient vector search
CREATE INDEX IF NOT EXISTS idx_document_chunks_document ON document_chunks(document_id, document_type);
CREATE INDEX IF NOT EXISTS idx_document_chunks_type ON document_chunks(document_type);
CREATE INDEX IF NOT EXISTS idx_document_chunks_metadata ON document_chunks USING GIN(metadata);

-- Create vector similarity index using HNSW (Hierarchical Navigable Small World)
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON document_chunks 
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Create function for semantic search
CREATE OR REPLACE FUNCTION semantic_search(
    p_query_embedding vector(384),
    p_document_types VARCHAR(50)[] DEFAULT NULL,
    p_limit INTEGER DEFAULT 10,
    p_similarity_threshold DECIMAL DEFAULT 0.3
)
RETURNS TABLE(
    document_id VARCHAR(100),
    document_type VARCHAR(50),
    chunk_index INTEGER,
    content TEXT,
    similarity_score DECIMAL,
    metadata JSONB,
    token_count INTEGER
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
$$ LANGUAGE plpgsql;

-- Create function for hybrid search (combining semantic and keyword search)
CREATE OR REPLACE FUNCTION hybrid_search(
    p_query_embedding vector(384),
    p_keywords TEXT,
    p_document_types VARCHAR(50)[] DEFAULT NULL,
    p_limit INTEGER DEFAULT 10,
    p_semantic_weight DECIMAL DEFAULT 0.7,
    p_keyword_weight DECIMAL DEFAULT 0.3
)
RETURNS TABLE(
    document_id VARCHAR(100),
    document_type VARCHAR(50),
    chunk_index INTEGER,
    content TEXT,
    combined_score DECIMAL,
    semantic_score DECIMAL,
    keyword_score DECIMAL,
    metadata JSONB
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
        AND (
            (1 - (dc.embedding <=> p_query_embedding)) >= 0.2 
            OR to_tsvector('english', dc.content) @@ plainto_tsquery('english', p_keywords)
        )
    ORDER BY combined_score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Create function to find contextually related documents
CREATE OR REPLACE FUNCTION find_related_context(
    p_document_id VARCHAR(100),
    p_document_type VARCHAR(50),
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE(
    related_document_id VARCHAR(100),
    related_document_type VARCHAR(50),
    chunk_index INTEGER,
    content TEXT,
    similarity_score DECIMAL,
    metadata JSONB
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
        dc.document_id,
        dc.document_type,
        dc.chunk_index,
        dc.content,
        (1 - (dc.embedding <=> se.embedding))::DECIMAL as similarity_score,
        dc.metadata
    FROM document_chunks dc, source_embedding se
    WHERE 
        NOT (dc.document_id = p_document_id AND dc.document_type = p_document_type)
        AND (1 - (dc.embedding <=> se.embedding)) >= 0.4
    ORDER BY dc.embedding <=> se.embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to update timestamps for document_chunks
CREATE TRIGGER update_document_chunks_modtime
    BEFORE UPDATE ON document_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- Create full-text search index for keyword search
CREATE INDEX IF NOT EXISTS idx_document_chunks_fts ON document_chunks 
USING GIN(to_tsvector('english', content));

-- Grant permissions to sf_user
GRANT ALL PRIVILEGES ON entity_relationships TO sf_user;
GRANT ALL PRIVILEGES ON relationship_summary TO sf_user;
GRANT ALL PRIVILEGES ON document_chunks TO sf_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO sf_user; 