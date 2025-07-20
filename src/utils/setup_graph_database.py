"""
Graph Database Setup Utility
Sets up PostgreSQL with graph extensions and relationship tables
"""

import logging
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)


def setup_graph_database(database_url: str = None) -> bool:
    """
    Set up PostgreSQL database with graph extensions and relationship tables
    
    Args:
        database_url: PostgreSQL connection string
        
    Returns:
        bool: True if setup successful, False otherwise
    """
    if not database_url:
        database_url = os.environ.get(
            'DATABASE_URL', 
            'postgresql://sf_user:sf_password@localhost:5432/software_factory'
        )
    
    try:
        # Create engine with autocommit for DDL operations
        engine = create_engine(database_url, isolation_level="AUTOCOMMIT")
        
        logger.info("Setting up PostgreSQL graph extensions...")
        
        with engine.connect() as conn:
            # Enable required extensions
            logger.info("Enabling PostgreSQL extensions...")
            
            extensions = [
                'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
                'CREATE EXTENSION IF NOT EXISTS "ltree"',
                'CREATE EXTENSION IF NOT EXISTS "hstore"'
            ]
            
            for ext_sql in extensions:
                try:
                    conn.execute(text(ext_sql))
                    logger.info(f"Extension enabled: {ext_sql}")
                except SQLAlchemyError as e:
                    logger.warning(f"Extension may already exist: {e}")
            
            # Create custom types
            logger.info("Creating custom relationship type...")
            
            create_type_sql = """
            DO $$ BEGIN
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
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
            """
            
            conn.execute(text(create_type_sql))
            logger.info("Relationship type created")
            
            # Create entity relationships table
            logger.info("Creating entity relationships table...")
            
            create_table_sql = """
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
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(source_entity_type, source_entity_id, target_entity_type, target_entity_id, relationship_type)
            );
            """
            
            conn.execute(text(create_table_sql))
            logger.info("Entity relationships table created")
            
            # Create indexes
            logger.info("Creating indexes for graph queries...")
            
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_entity_relationships_source ON entity_relationships(source_entity_type, source_entity_id)",
                "CREATE INDEX IF NOT EXISTS idx_entity_relationships_target ON entity_relationships(target_entity_type, target_entity_id)",
                "CREATE INDEX IF NOT EXISTS idx_entity_relationships_type ON entity_relationships(relationship_type)",
                "CREATE INDEX IF NOT EXISTS idx_entity_relationships_metadata ON entity_relationships USING GIN(metadata)",
                """CREATE INDEX IF NOT EXISTS idx_entity_relationships_bidirectional ON entity_relationships(
                    source_entity_type, source_entity_id, target_entity_type, target_entity_id
                )"""
            ]
            
            for index_sql in indexes:
                conn.execute(text(index_sql))
                logger.info("Index created")
            
            # Create graph query functions
            logger.info("Creating graph query functions...")
            
            # Function for finding related entities
            find_related_function = """
            CREATE OR REPLACE FUNCTION find_related_entities(
                p_entity_type VARCHAR(50),
                p_entity_id VARCHAR(100),
                p_relationship_types relationship_type[] DEFAULT NULL,
                p_max_depth INTEGER DEFAULT 3,
                p_direction VARCHAR(10) DEFAULT 'both'
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
                        AND NOT (rt.entity_type = p_entity_type AND rt.entity_id = p_entity_id)
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
            """
            
            conn.execute(text(find_related_function))
            logger.info("find_related_entities function created")
            
            # Function for calculating centrality
            centrality_function = """
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
            """
            
            conn.execute(text(centrality_function))
            logger.info("calculate_entity_centrality function created")
            
            # Create trigger for updating timestamps
            trigger_function = """
            CREATE OR REPLACE FUNCTION update_modified_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
            
            conn.execute(text(trigger_function))
            
            trigger_sql = """
            DROP TRIGGER IF EXISTS update_entity_relationships_modtime ON entity_relationships;
            CREATE TRIGGER update_entity_relationships_modtime
                BEFORE UPDATE ON entity_relationships
                FOR EACH ROW
                EXECUTE FUNCTION update_modified_column();
            """
            
            conn.execute(text(trigger_sql))
            logger.info("Update trigger created")
            
            # Create view for easy relationship browsing
            view_sql = """
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
            """
            
            conn.execute(text(view_sql))
            logger.info("Relationship summary view created")
            
        logger.info("PostgreSQL graph database setup completed successfully!")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to set up graph database: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during graph database setup: {e}")
        return False


def verify_graph_setup(database_url: str = None) -> bool:
    """
    Verify that graph database setup is working correctly
    
    Args:
        database_url: PostgreSQL connection string
        
    Returns:
        bool: True if verification successful, False otherwise
    """
    if not database_url:
        database_url = os.environ.get(
            'DATABASE_URL', 
            'postgresql://sf_user:sf_password@localhost:5432/software_factory'
        )
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Test basic table existence
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'entity_relationships'
            """))
            
            if result.scalar() == 0:
                logger.error("entity_relationships table not found")
                return False
            
            # Test function existence
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.routines 
                WHERE routine_name = 'find_related_entities'
            """))
            
            if result.scalar() == 0:
                logger.error("find_related_entities function not found")
                return False
            
            # Test basic insert and query
            conn.execute(text("""
                INSERT INTO entity_relationships 
                (source_entity_type, source_entity_id, target_entity_type, target_entity_id, relationship_type)
                VALUES ('test', '1', 'test', '2', 'references')
                ON CONFLICT DO NOTHING
            """))
            
            result = conn.execute(text("""
                SELECT COUNT(*) FROM entity_relationships 
                WHERE source_entity_type = 'test' AND source_entity_id = '1'
            """))
            
            if result.scalar() == 0:
                logger.error("Failed to insert test relationship")
                return False
            
            # Clean up test data
            conn.execute(text("""
                DELETE FROM entity_relationships 
                WHERE source_entity_type = 'test' AND source_entity_id = '1'
            """))
            
            conn.commit()
            
        logger.info("Graph database verification completed successfully!")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Graph database verification failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during verification: {e}")
        return False


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("Setting up PostgreSQL graph database...")
    
    if setup_graph_database():
        print("✅ Graph database setup completed successfully!")
        
        print("Verifying setup...")
        if verify_graph_setup():
            print("✅ Graph database verification completed successfully!")
        else:
            print("❌ Graph database verification failed!")
            sys.exit(1)
    else:
        print("❌ Graph database setup failed!")
        sys.exit(1)