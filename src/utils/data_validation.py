#!/usr/bin/env python3
"""
Data Validation and Cleanup Utilities for Mission Control Migration

Provides utilities to:
- Validate JSON data structure before migration
- Clean up inconsistent data
- Verify database integrity after migration
- Generate data quality reports
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.app import create_app


class DataValidator:
    """Validates Mission Control data before and after migration"""
    
    def __init__(self):
        self.validation_results = {
            'errors': [],
            'warnings': [],
            'info': [],
            'stats': {}
        }
    
    def validate_json_structure(self, data_file_path: str) -> Dict[str, Any]:
        """Validate the structure of the JSON data file"""
        print("=== JSON Data Structure Validation ===")
        
        try:
            with open(data_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.validation_results['errors'].append(f"Failed to load JSON file: {e}")
            return self.validation_results
        
        # Check required top-level keys
        required_keys = ['projects', 'feedItems', 'conversations', 'stages', 'productBriefs', 'stageTransitions']
        for key in required_keys:
            if key not in data:
                self.validation_results['errors'].append(f"Missing required key: {key}")
            else:
                self.validation_results['info'].append(f"✓ Found {key}")
        
        # Validate projects
        self._validate_projects(data.get('projects', []))
        
        # Validate feed items
        self._validate_feed_items(data.get('feedItems', []))
        
        # Validate conversations
        self._validate_conversations(data.get('conversations', {}))
        
        # Validate stages
        self._validate_stages(data.get('stages', {}))
        
        # Validate product briefs
        self._validate_product_briefs(data.get('productBriefs', {}))
        
        # Validate stage transitions
        self._validate_stage_transitions(data.get('stageTransitions', []))
        
        return self.validation_results
    
    def _validate_projects(self, projects: List[Dict[str, Any]]):
        """Validate projects data"""
        print("\n--- Validating Projects ---")
        
        project_ids = set()
        for i, project in enumerate(projects):
            # Check required fields
            if 'id' not in project:
                self.validation_results['errors'].append(f"Project {i}: Missing 'id' field")
                continue
            
            if 'name' not in project:
                self.validation_results['errors'].append(f"Project {project['id']}: Missing 'name' field")
            
            # Check for duplicate IDs
            if project['id'] in project_ids:
                self.validation_results['errors'].append(f"Duplicate project ID: {project['id']}")
            else:
                project_ids.add(project['id'])
            
            # Validate health status
            valid_health = ['green', 'amber', 'red']
            if project.get('health') and project['health'] not in valid_health:
                self.validation_results['warnings'].append(
                    f"Project {project['id']}: Invalid health status '{project['health']}'"
                )
            
            # Validate datetime fields
            for date_field in ['lastActivity', 'createdAt']:
                if project.get(date_field):
                    try:
                        datetime.fromisoformat(project[date_field].replace('Z', '+00:00'))
                    except ValueError:
                        self.validation_results['warnings'].append(
                            f"Project {project['id']}: Invalid datetime format in {date_field}"
                        )
        
        self.validation_results['stats']['projects'] = len(projects)
        self.validation_results['stats']['unique_project_ids'] = len(project_ids)
        print(f"✓ Validated {len(projects)} projects")
    
    def _validate_feed_items(self, feed_items: List[Dict[str, Any]]):
        """Validate feed items data"""
        print("\n--- Validating Feed Items ---")
        
        feed_item_ids = set()
        project_references = set()
        
        for i, item in enumerate(feed_items):
            # Check required fields
            if 'id' not in item:
                self.validation_results['errors'].append(f"Feed item {i}: Missing 'id' field")
                continue
            
            required_fields = ['projectId', 'kind', 'title']
            for field in required_fields:
                if field not in item:
                    self.validation_results['errors'].append(f"Feed item {item['id']}: Missing '{field}' field")
            
            # Check for duplicate IDs
            if item['id'] in feed_item_ids:
                self.validation_results['errors'].append(f"Duplicate feed item ID: {item['id']}")
            else:
                feed_item_ids.add(item['id'])
            
            # Track project references
            if item.get('projectId'):
                project_references.add(item['projectId'])
            
            # Validate severity
            valid_severity = ['info', 'amber', 'red']
            if item.get('severity') and item['severity'] not in valid_severity:
                self.validation_results['warnings'].append(
                    f"Feed item {item['id']}: Invalid severity '{item['severity']}'"
                )
            
            # Validate datetime fields
            for date_field in ['createdAt', 'updatedAt']:
                if item.get(date_field):
                    try:
                        datetime.fromisoformat(item[date_field].replace('Z', '+00:00'))
                    except ValueError:
                        self.validation_results['warnings'].append(
                            f"Feed item {item['id']}: Invalid datetime format in {date_field}"
                        )
        
        self.validation_results['stats']['feed_items'] = len(feed_items)
        self.validation_results['stats']['unique_feed_item_ids'] = len(feed_item_ids)
        self.validation_results['stats']['project_references_in_feed'] = len(project_references)
        print(f"✓ Validated {len(feed_items)} feed items")
    
    def _validate_conversations(self, conversations: Dict[str, Any]):
        """Validate conversations data"""
        print("\n--- Validating Conversations ---")
        
        if not conversations:
            self.validation_results['info'].append("No conversations to validate")
            self.validation_results['stats']['conversations'] = 0
            return
        
        for conv_id, conv_data in conversations.items():
            # Validate structure
            if not isinstance(conv_data, dict):
                self.validation_results['errors'].append(f"Conversation {conv_id}: Invalid data structure")
                continue
            
            # Check for required fields if conversation has data
            if conv_data.get('messages') and not conv_data.get('projectId'):
                self.validation_results['warnings'].append(f"Conversation {conv_id}: Missing projectId")
        
        self.validation_results['stats']['conversations'] = len(conversations)
        print(f"✓ Validated {len(conversations)} conversations")
    
    def _validate_stages(self, stages: Dict[str, Any]):
        """Validate stages data"""
        print("\n--- Validating Stages ---")
        
        valid_stage_types = ['think', 'define', 'plan', 'build', 'validate']
        stage_count = 0
        
        for project_id, project_stages in stages.items():
            if not isinstance(project_stages, dict):
                self.validation_results['errors'].append(f"Stages for project {project_id}: Invalid data structure")
                continue
            
            for stage_type, item_ids in project_stages.items():
                stage_count += 1
                
                # Validate stage type
                if stage_type not in valid_stage_types:
                    self.validation_results['warnings'].append(
                        f"Project {project_id}: Invalid stage type '{stage_type}'"
                    )
                
                # Validate item IDs are array
                if not isinstance(item_ids, list):
                    self.validation_results['errors'].append(
                        f"Project {project_id}, stage {stage_type}: item_ids should be an array"
                    )
        
        self.validation_results['stats']['stages'] = stage_count
        print(f"✓ Validated {stage_count} stages")
    
    def _validate_product_briefs(self, product_briefs: Dict[str, Any]):
        """Validate product briefs data"""
        print("\n--- Validating Product Briefs ---")
        
        for brief_id, brief_data in product_briefs.items():
            # Check required fields
            required_fields = ['itemId', 'projectId']
            for field in required_fields:
                if field not in brief_data:
                    self.validation_results['errors'].append(f"Product brief {brief_id}: Missing '{field}' field")
            
            # Validate progress value
            if 'progress' in brief_data:
                progress = brief_data['progress']
                if not isinstance(progress, (int, float)) or progress < 0 or progress > 1:
                    self.validation_results['warnings'].append(
                        f"Product brief {brief_id}: Invalid progress value '{progress}'"
                    )
            
            # Validate datetime fields
            for date_field in ['createdAt', 'updatedAt']:
                if brief_data.get(date_field):
                    try:
                        datetime.fromisoformat(brief_data[date_field].replace('Z', '+00:00'))
                    except ValueError:
                        self.validation_results['warnings'].append(
                            f"Product brief {brief_id}: Invalid datetime format in {date_field}"
                        )
        
        self.validation_results['stats']['product_briefs'] = len(product_briefs)
        print(f"✓ Validated {len(product_briefs)} product briefs")
    
    def _validate_stage_transitions(self, stage_transitions: List[Dict[str, Any]]):
        """Validate stage transitions data"""
        print("\n--- Validating Stage Transitions ---")
        
        for i, transition in enumerate(stage_transitions):
            # Check required fields
            required_fields = ['itemId', 'projectId', 'toStage']
            for field in required_fields:
                if field not in transition:
                    self.validation_results['errors'].append(f"Stage transition {i}: Missing '{field}' field")
            
            # Validate timestamp
            if transition.get('timestamp'):
                try:
                    datetime.fromisoformat(transition['timestamp'].replace('Z', '+00:00'))
                except ValueError:
                    self.validation_results['warnings'].append(
                        f"Stage transition {i}: Invalid timestamp format"
                    )
        
        self.validation_results['stats']['stage_transitions'] = len(stage_transitions)
        print(f"✓ Validated {len(stage_transitions)} stage transitions")
    
    def validate_database_integrity(self) -> Dict[str, Any]:
        """Validate database integrity after migration"""
        from src.core.database import db
        from src.models.mission_control_project import MissionControlProject
        from src.models.feed_item import FeedItem
        from src.models.conversation import Conversation
        from src.models.system_map import SystemMap
        from src.models.stage import Stage, StageTransition, ProductBrief
        
        print("\n=== Database Integrity Validation ===")
        
        integrity_results = {
            'errors': [],
            'warnings': [],
            'info': [],
            'stats': {}
        }
        
        try:
            # Count records in each table
            project_count = MissionControlProject.query.count()
            feed_item_count = FeedItem.query.count()
            conversation_count = Conversation.query.count()
            stage_count = Stage.query.count()
            product_brief_count = ProductBrief.query.count()
            stage_transition_count = StageTransition.query.count()
            system_map_count = SystemMap.query.count()
            
            integrity_results['stats'] = {
                'projects': project_count,
                'feed_items': feed_item_count,
                'conversations': conversation_count,
                'stages': stage_count,
                'product_briefs': product_brief_count,
                'stage_transitions': stage_transition_count,
                'system_maps': system_map_count
            }
            
            # Check for orphaned records
            self._check_orphaned_feed_items(integrity_results)
            self._check_orphaned_stages(integrity_results)
            self._check_orphaned_product_briefs(integrity_results)
            
            # Check data consistency
            self._check_stage_item_consistency(integrity_results)
            
            print("✓ Database integrity validation completed")
            
        except Exception as e:
            integrity_results['errors'].append(f"Database validation failed: {e}")
        
        return integrity_results
    
    def _check_orphaned_feed_items(self, results: Dict[str, Any]):
        """Check for feed items without corresponding projects"""
        from src.core.database import db
        from src.models.mission_control_project import MissionControlProject
        from src.models.feed_item import FeedItem
        
        orphaned_items = db.session.query(FeedItem).filter(
            ~FeedItem.project_id.in_(
                db.session.query(MissionControlProject.id)
            )
        ).all()
        
        if orphaned_items:
            results['warnings'].append(f"Found {len(orphaned_items)} orphaned feed items")
            for item in orphaned_items[:5]:  # Show first 5
                results['warnings'].append(f"  - Feed item {item.id} references non-existent project {item.project_id}")
        else:
            results['info'].append("✓ No orphaned feed items found")
    
    def _check_orphaned_stages(self, results: Dict[str, Any]):
        """Check for stages without corresponding projects"""
        from src.core.database import db
        from src.models.mission_control_project import MissionControlProject
        from src.models.stage import Stage
        
        orphaned_stages = db.session.query(Stage).filter(
            ~Stage.project_id.in_(
                db.session.query(MissionControlProject.id)
            )
        ).all()
        
        if orphaned_stages:
            results['warnings'].append(f"Found {len(orphaned_stages)} orphaned stages")
        else:
            results['info'].append("✓ No orphaned stages found")
    
    def _check_orphaned_product_briefs(self, results: Dict[str, Any]):
        """Check for product briefs without corresponding feed items"""
        from src.core.database import db
        from src.models.feed_item import FeedItem
        from src.models.stage import ProductBrief
        
        orphaned_briefs = db.session.query(ProductBrief).filter(
            ~ProductBrief.item_id.in_(
                db.session.query(FeedItem.id)
            )
        ).all()
        
        if orphaned_briefs:
            results['warnings'].append(f"Found {len(orphaned_briefs)} orphaned product briefs")
        else:
            results['info'].append("✓ No orphaned product briefs found")
    
    def _check_stage_item_consistency(self, results: Dict[str, Any]):
        """Check consistency between stages and feed items"""
        from src.models.stage import Stage
        from src.models.feed_item import FeedItem
        
        stages = Stage.query.all()
        inconsistencies = 0
        
        for stage in stages:
            if stage.item_ids:
                for item_id in stage.item_ids:
                    feed_item = FeedItem.query.filter_by(id=item_id).first()
                    if not feed_item:
                        inconsistencies += 1
                        if inconsistencies <= 5:  # Show first 5
                            results['warnings'].append(
                                f"Stage {stage.project_id}:{stage.stage_type} references non-existent item {item_id}"
                            )
        
        if inconsistencies > 5:
            results['warnings'].append(f"... and {inconsistencies - 5} more stage-item inconsistencies")
        elif inconsistencies == 0:
            results['info'].append("✓ Stage-item references are consistent")
    
    def print_validation_results(self, results: Dict[str, Any]):
        """Print validation results in a formatted way"""
        print("\n=== Validation Results ===")
        
        if results.get('stats'):
            print("\nStatistics:")
            for key, value in results['stats'].items():
                print(f"  {key}: {value}")
        
        if results.get('info'):
            print(f"\nInfo ({len(results['info'])}):")
            for info in results['info']:
                print(f"  {info}")
        
        if results.get('warnings'):
            print(f"\nWarnings ({len(results['warnings'])}):")
            for warning in results['warnings']:
                print(f"  ⚠ {warning}")
        
        if results.get('errors'):
            print(f"\nErrors ({len(results['errors'])}):")
            for error in results['errors']:
                print(f"  ✗ {error}")
        
        # Summary
        error_count = len(results.get('errors', []))
        warning_count = len(results.get('warnings', []))
        
        if error_count == 0 and warning_count == 0:
            print("\n✅ Validation passed with no issues!")
        elif error_count == 0:
            print(f"\n⚠️  Validation passed with {warning_count} warnings")
        else:
            print(f"\n❌ Validation failed with {error_count} errors and {warning_count} warnings")


def main():
    """Main validation function"""
    if len(sys.argv) < 2:
        print("Usage: python data_validation.py <command> [data_file]")
        print("Commands:")
        print("  validate-json <data_file>  - Validate JSON data structure")
        print("  validate-db                - Validate database integrity")
        print("  validate-all <data_file>   - Run both validations")
        sys.exit(1)
    
    command = sys.argv[1]
    validator = DataValidator()
    
    if command == "validate-json":
        if len(sys.argv) < 3:
            print("Error: data_file required for validate-json command")
            sys.exit(1)
        
        data_file = sys.argv[2]
        results = validator.validate_json_structure(data_file)
        validator.print_validation_results(results)
        
    elif command == "validate-db":
        app = create_app()
        with app.app_context():
            results = validator.validate_database_integrity()
            validator.print_validation_results(results)
    
    elif command == "validate-all":
        if len(sys.argv) < 3:
            print("Error: data_file required for validate-all command")
            sys.exit(1)
        
        data_file = sys.argv[2]
        
        # Validate JSON first
        json_results = validator.validate_json_structure(data_file)
        validator.print_validation_results(json_results)
        
        # Then validate database
        app = create_app()
        with app.app_context():
            db_results = validator.validate_database_integrity()
            validator.print_validation_results(db_results)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()