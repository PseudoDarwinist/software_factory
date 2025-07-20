"""
Test Graph Service functionality
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock the database import before importing the service
sys.modules['models.base'] = MagicMock()
sys.modules['models'] = MagicMock()

from services.graph_service import GraphService, ProjectGraphService


class TestGraphService(unittest.TestCase):
    """Test cases for GraphService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_session = MagicMock()
        
    @patch('services.graph_service.db')
    def test_add_relationship(self, mock_db):
        """Test adding a relationship between entities"""
        mock_db.session = self.mock_db_session
        
        # Test successful relationship addition
        result = GraphService.add_relationship(
            source_entity_type='project',
            source_entity_id='1',
            target_entity_type='conversation',
            target_entity_id='2',
            relationship_type='references'
        )
        
        # Verify database operations were called
        self.mock_db_session.execute.assert_called_once()
        self.mock_db_session.commit.assert_called_once()
        self.assertTrue(result)
    
    @patch('services.graph_service.db')
    def test_remove_relationship(self, mock_db):
        """Test removing a relationship between entities"""
        mock_db.session = self.mock_db_session
        mock_result = MagicMock()
        mock_result.rowcount = 1
        self.mock_db_session.execute.return_value = mock_result
        
        # Test successful relationship removal
        result = GraphService.remove_relationship(
            source_entity_type='project',
            source_entity_id='1',
            target_entity_type='conversation',
            target_entity_id='2',
            relationship_type='references'
        )
        
        # Verify database operations were called
        self.mock_db_session.execute.assert_called_once()
        self.mock_db_session.commit.assert_called_once()
        self.assertTrue(result)
    
    @patch('services.graph_service.db')
    def test_find_related_entities(self, mock_db):
        """Test finding related entities"""
        mock_db.session = self.mock_db_session
        
        # Mock database result
        mock_row = MagicMock()
        mock_row.entity_type = 'conversation'
        mock_row.entity_id = '2'
        mock_row.relationship_path = ['references']
        mock_row.depth = 1
        mock_row.total_weight = 1.0
        
        mock_result = MagicMock()
        mock_result.__iter__ = lambda x: iter([mock_row])
        self.mock_db_session.execute.return_value = mock_result
        
        # Test finding related entities
        related = GraphService.find_related_entities(
            entity_type='project',
            entity_id='1',
            max_depth=2
        )
        
        # Verify result structure
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]['entity_type'], 'conversation')
        self.assertEqual(related[0]['entity_id'], '2')
        self.assertEqual(related[0]['depth'], 1)
    
    @patch('services.graph_service.db')
    def test_calculate_entity_centrality(self, mock_db):
        """Test calculating entity centrality metrics"""
        mock_db.session = self.mock_db_session
        
        # Mock database result
        mock_row = MagicMock()
        mock_row.in_degree = 2
        mock_row.out_degree = 3
        mock_row.total_degree = 5
        mock_row.weighted_in_degree = 2.5
        mock_row.weighted_out_degree = 3.5
        mock_row.centrality_score = 1.2
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        self.mock_db_session.execute.return_value = mock_result
        
        # Test centrality calculation
        centrality = GraphService.calculate_entity_centrality(
            entity_type='project',
            entity_id='1'
        )
        
        # Verify result structure
        self.assertIsNotNone(centrality)
        self.assertEqual(centrality['in_degree'], 2)
        self.assertEqual(centrality['out_degree'], 3)
        self.assertEqual(centrality['total_degree'], 5)
        self.assertEqual(centrality['centrality_score'], 1.2)


class TestProjectGraphService(unittest.TestCase):
    """Test cases for ProjectGraphService"""
    
    @patch('services.graph_service.GraphService.add_relationship')
    def test_link_project_to_mission_control(self, mock_add_relationship):
        """Test linking project to mission control"""
        mock_add_relationship.return_value = True
        
        result = ProjectGraphService.link_project_to_mission_control(
            project_id=1,
            mission_control_id='proj-1'
        )
        
        # Verify GraphService.add_relationship was called with correct parameters
        mock_add_relationship.assert_called_once_with(
            GraphService.ENTITY_PROJECT, '1',
            GraphService.ENTITY_MISSION_CONTROL_PROJECT, 'proj-1',
            GraphService.REL_REFERENCES,
            {'sync_type': 'bidirectional'}
        )
        self.assertTrue(result)
    
    @patch('services.graph_service.GraphService.add_relationship')
    def test_link_conversation_to_project(self, mock_add_relationship):
        """Test linking conversation to project"""
        mock_add_relationship.return_value = True
        
        result = ProjectGraphService.link_conversation_to_project(
            conversation_id=1,
            project_id=2
        )
        
        # Verify GraphService.add_relationship was called with correct parameters
        mock_add_relationship.assert_called_once_with(
            GraphService.ENTITY_CONVERSATION, '1',
            GraphService.ENTITY_PROJECT, '2',
            GraphService.REL_REFERENCES,
            {'context': 'project_conversation'}
        )
        self.assertTrue(result)
    
    @patch('services.graph_service.GraphService.find_related_entities')
    @patch('services.graph_service.GraphService.calculate_entity_centrality')
    def test_get_project_ecosystem(self, mock_centrality, mock_related):
        """Test getting project ecosystem"""
        # Mock related entities
        mock_related.return_value = [
            {'entity_type': 'conversation', 'entity_id': '1', 'depth': 1},
            {'entity_type': 'system_map', 'entity_id': '1', 'depth': 1}
        ]
        
        # Mock centrality metrics
        mock_centrality.return_value = {
            'in_degree': 2,
            'out_degree': 3,
            'centrality_score': 1.5
        }
        
        ecosystem = ProjectGraphService.get_project_ecosystem(project_id=1)
        
        # Verify result structure
        self.assertEqual(ecosystem['project_id'], 1)
        self.assertEqual(len(ecosystem['related_entities']), 2)
        self.assertEqual(ecosystem['ecosystem_size'], 2)
        self.assertIsNotNone(ecosystem['centrality_metrics'])


if __name__ == '__main__':
    unittest.main()