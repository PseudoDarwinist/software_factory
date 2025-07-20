"""
Graph Database Demo Script
Demonstrates PostgreSQL graph query capabilities
"""

import os
import sys
import logging
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.graph_service import GraphService, ProjectGraphService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_basic_relationships():
    """Demonstrate basic relationship operations"""
    print("\n=== Basic Relationship Operations ===")
    
    # Add some sample relationships
    print("Adding sample relationships...")
    
    # Project -> Mission Control Project relationship
    GraphService.add_relationship(
        'project', '1',
        'mission_control_project', 'proj-1',
        'references',
        {'sync_type': 'bidirectional', 'created_by': 'demo'},
        weight=1.0
    )
    
    # Project -> Conversations relationships
    GraphService.add_relationship(
        'project', '1',
        'conversation', '1',
        'owns',
        {'context': 'project_discussion'},
        weight=0.8
    )
    
    GraphService.add_relationship(
        'project', '1',
        'conversation', '2',
        'owns',
        {'context': 'requirements_gathering'},
        weight=0.9
    )
    
    # Project -> System Map relationship
    GraphService.add_relationship(
        'project', '1',
        'system_map', '1',
        'contains',
        {'analysis_type': 'architecture_overview'},
        weight=1.0
    )
    
    # Conversation -> System Map relationship (conversation led to system map)
    GraphService.add_relationship(
        'conversation', '1',
        'system_map', '1',
        'triggers',
        {'trigger_type': 'analysis_request'},
        weight=0.7
    )
    
    print("✅ Sample relationships added")


def demo_graph_queries():
    """Demonstrate graph query operations"""
    print("\n=== Graph Query Operations ===")
    
    # Find entities related to project 1
    print("Finding entities related to project 1...")
    related = GraphService.find_related_entities(
        entity_type='project',
        entity_id='1',
        max_depth=2
    )
    
    print(f"Found {len(related)} related entities:")
    for entity in related:
        print(f"  - {entity['entity_type']}:{entity['entity_id']} "
              f"(depth: {entity['depth']}, weight: {entity['total_weight']})")
        print(f"    Path: {' -> '.join(entity['relationship_path'])}")
    
    # Calculate centrality for project 1
    print("\nCalculating centrality metrics for project 1...")
    centrality = GraphService.calculate_entity_centrality(
        entity_type='project',
        entity_id='1'
    )
    
    if centrality:
        print(f"Centrality metrics:")
        print(f"  - In-degree: {centrality['in_degree']}")
        print(f"  - Out-degree: {centrality['out_degree']}")
        print(f"  - Total degree: {centrality['total_degree']}")
        print(f"  - Centrality score: {centrality['centrality_score']:.2f}")
    
    # Get direct relationships for project 1
    print("\nGetting direct relationships for project 1...")
    relationships = GraphService.get_entity_relationships(
        entity_type='project',
        entity_id='1'
    )
    
    print(f"Found {len(relationships)} direct relationships:")
    for rel in relationships:
        print(f"  - {rel['source_entity_type']}:{rel['source_entity_id']} "
              f"--[{rel['relationship_type']}]--> "
              f"{rel['target_entity_type']}:{rel['target_entity_id']}")
        if rel['metadata']:
            print(f"    Metadata: {rel['metadata']}")


def demo_path_finding():
    """Demonstrate path finding between entities"""
    print("\n=== Path Finding Operations ===")
    
    # Find path from conversation 1 to system map 1
    print("Finding path from conversation 1 to system map 1...")
    path = GraphService.find_shortest_path(
        source_type='conversation',
        source_id='1',
        target_type='system_map',
        target_id='1'
    )
    
    if path:
        print(f"Shortest path found (length: {path['path_length']}):")
        print(f"  - Entity path: {' -> '.join(path['entity_path'])}")
        print(f"  - Relationship path: {' -> '.join(path['relationship_path'])}")
        print(f"  - Total weight: {path['total_weight']}")
    else:
        print("No path found")


def demo_project_ecosystem():
    """Demonstrate project ecosystem analysis"""
    print("\n=== Project Ecosystem Analysis ===")
    
    # Get complete ecosystem for project 1
    print("Analyzing ecosystem for project 1...")
    ecosystem = ProjectGraphService.get_project_ecosystem(
        project_id=1,
        max_depth=2
    )
    
    print(f"Project ecosystem analysis:")
    print(f"  - Project ID: {ecosystem['project_id']}")
    print(f"  - Ecosystem size: {ecosystem['ecosystem_size']} entities")
    
    if ecosystem['centrality_metrics']:
        centrality = ecosystem['centrality_metrics']
        print(f"  - Centrality score: {centrality['centrality_score']:.2f}")
    
    print(f"  - Related entities by type:")
    entity_types = {}
    for entity in ecosystem['related_entities']:
        entity_type = entity['entity_type']
        if entity_type not in entity_types:
            entity_types[entity_type] = 0
        entity_types[entity_type] += 1
    
    for entity_type, count in entity_types.items():
        print(f"    - {entity_type}: {count}")


def demo_statistics():
    """Demonstrate relationship statistics"""
    print("\n=== Relationship Statistics ===")
    
    stats = GraphService.get_relationship_statistics()
    
    if stats:
        print("Overall relationship statistics:")
        print(f"  - Total relationships: {stats.get('total_relationships', 0)}")
        print(f"  - Unique source entities: {stats.get('unique_source_entities', 0)}")
        print(f"  - Unique target entities: {stats.get('unique_target_entities', 0)}")
        print(f"  - Unique relationship types: {stats.get('unique_relationship_types', 0)}")
        print(f"  - Average weight: {stats.get('average_weight', 0):.2f}")
    else:
        print("No statistics available")


def cleanup_demo_data():
    """Clean up demo data"""
    print("\n=== Cleanup Demo Data ===")
    
    # Remove all relationships for demo entities
    entities_to_cleanup = [
        ('project', '1'),
        ('mission_control_project', 'proj-1'),
        ('conversation', '1'),
        ('conversation', '2'),
        ('system_map', '1')
    ]
    
    for entity_type, entity_id in entities_to_cleanup:
        GraphService.remove_entity_relationships(entity_type, entity_id)
    
    print("✅ Demo data cleaned up")


def main():
    """Run the complete graph database demo"""
    print("🔗 PostgreSQL Graph Database Demo")
    print("=" * 50)
    
    try:
        # Set up demo data
        demo_basic_relationships()
        
        # Run demonstrations
        demo_graph_queries()
        demo_path_finding()
        demo_project_ecosystem()
        demo_statistics()
        
        # Clean up
        cleanup_demo_data()
        
        print("\n✅ Graph database demo completed successfully!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        
        # Try to clean up even if demo failed
        try:
            cleanup_demo_data()
        except:
            pass


if __name__ == '__main__':
    main()