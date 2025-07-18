#!/usr/bin/env python3
"""
Mission Control Data Migration Script

Migrates data from JSON files to SQLite database:
- Projects from mission-control/server/data.json
- Feed items from mission-control/server/data.json  
- Conversations from mission-control/server/data.json
- Stages from mission-control/server/data.json
- Product briefs from mission-control/server/data.json
- Stage transitions from mission-control/server/data.json
- System maps from mission-control/artifacts/*/system-map.json
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.app import create_app


class MissionControlDataMigrator:
    """Handles migration of Mission Control data from JSON to SQLite"""
    
    def __init__(self, data_file_path, artifacts_dir_path):
        self.data_file_path = Path(data_file_path)
        self.artifacts_dir_path = Path(artifacts_dir_path)
        self.data = None
        self.migration_stats = {
            'projects': 0,
            'feed_items': 0,
            'conversations': 0,
            'stages': 0,
            'product_briefs': 0,
            'stage_transitions': 0,
            'system_maps': 0,
            'errors': []
        }
    
    def load_json_data(self):
        """Load the main data.json file"""
        try:
            with open(self.data_file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            print(f"✓ Loaded data from {self.data_file_path}")
        except Exception as e:
            error_msg = f"Failed to load {self.data_file_path}: {e}"
            self.migration_stats['errors'].append(error_msg)
            raise Exception(error_msg)
    
    def validate_data_structure(self):
        """Validate that the JSON data has expected structure"""
        required_keys = ['projects', 'feedItems', 'conversations', 'stages', 'productBriefs', 'stageTransitions']
        missing_keys = [key for key in required_keys if key not in self.data]
        
        if missing_keys:
            error_msg = f"Missing required keys in data.json: {missing_keys}"
            self.migration_stats['errors'].append(error_msg)
            raise Exception(error_msg)
        
        print("✓ Data structure validation passed")
    
    def migrate_projects(self):
        """Migrate projects to MissionControlProject model"""
        from src.models.mission_control_project import MissionControlProject
        from src.core.database import db
        
        print("\n--- Migrating Projects ---")
        
        for project_data in self.data['projects']:
            try:
                # Parse datetime fields
                last_activity = None
                if project_data.get('lastActivity'):
                    last_activity = datetime.fromisoformat(project_data['lastActivity'].replace('Z', '+00:00'))
                
                created_at = None
                if project_data.get('createdAt'):
                    created_at = datetime.fromisoformat(project_data['createdAt'].replace('Z', '+00:00'))
                
                # Check if project already exists
                existing = MissionControlProject.query.filter_by(id=project_data['id']).first()
                if existing:
                    print(f"  ⚠ Project {project_data['id']} already exists, skipping")
                    continue
                
                # Create project
                project = MissionControlProject(
                    id=project_data['id'],
                    name=project_data['name'],
                    description=project_data.get('description'),
                    repo_url=project_data.get('repoUrl'),
                    health=project_data.get('health', 'amber'),
                    unread_count=project_data.get('unreadCount', 0),
                    last_activity=last_activity,
                    system_map_status=project_data.get('systemMapStatus', 'pending'),
                    meta_data=project_data.get('metadata', {}),
                    created_at=created_at or datetime.utcnow()
                )
                
                db.session.add(project)
                self.migration_stats['projects'] += 1
                print(f"  ✓ Migrated project: {project_data['id']} - {project_data['name']}")
                
            except Exception as e:
                error_msg = f"Failed to migrate project {project_data.get('id', 'unknown')}: {e}"
                self.migration_stats['errors'].append(error_msg)
                print(f"  ✗ {error_msg}")
        
        db.session.commit()
        print(f"✓ Migrated {self.migration_stats['projects']} projects")
    
    def migrate_feed_items(self):
        """Migrate feed items to FeedItem model"""
        from src.models.feed_item import FeedItem
        from src.core.database import db
        
        print("\n--- Migrating Feed Items ---")
        
        for feed_item_data in self.data['feedItems']:
            try:
                # Parse datetime fields
                created_at = None
                if feed_item_data.get('createdAt'):
                    created_at = datetime.fromisoformat(feed_item_data['createdAt'].replace('Z', '+00:00'))
                
                updated_at = None
                if feed_item_data.get('updatedAt'):
                    updated_at = datetime.fromisoformat(feed_item_data['updatedAt'].replace('Z', '+00:00'))
                
                # Check if feed item already exists
                existing = FeedItem.query.filter_by(id=feed_item_data['id']).first()
                if existing:
                    print(f"  ⚠ Feed item {feed_item_data['id']} already exists, skipping")
                    continue
                
                # Create feed item
                feed_item = FeedItem(
                    id=feed_item_data['id'],
                    project_id=feed_item_data['projectId'],
                    severity=feed_item_data.get('severity', 'info'),
                    kind=feed_item_data['kind'],
                    title=feed_item_data['title'],
                    summary=feed_item_data.get('summary'),
                    actor=feed_item_data.get('actor'),
                    unread=feed_item_data.get('unread', True),
                    linked_artifact_ids=feed_item_data.get('linkedArtifactIds', []),
                    meta_data=feed_item_data.get('metadata', {}),
                    created_at=created_at or datetime.utcnow(),
                    updated_at=updated_at or datetime.utcnow()
                )
                
                db.session.add(feed_item)
                self.migration_stats['feed_items'] += 1
                print(f"  ✓ Migrated feed item: {feed_item_data['id']} - {feed_item_data['title'][:50]}")
                
            except Exception as e:
                error_msg = f"Failed to migrate feed item {feed_item_data.get('id', 'unknown')}: {e}"
                self.migration_stats['errors'].append(error_msg)
                print(f"  ✗ {error_msg}")
        
        db.session.commit()
        print(f"✓ Migrated {self.migration_stats['feed_items']} feed items")
    
    def migrate_conversations(self):
        """Migrate conversations to Conversation model"""
        from src.models.conversation import Conversation
        from src.core.database import db
        
        print("\n--- Migrating Conversations ---")
        
        # The conversations object in data.json appears to be empty in current data
        # but we'll handle it in case there's data
        conversations_data = self.data.get('conversations', {})
        
        if not conversations_data:
            print("  ℹ No conversations to migrate")
            return
        
        for conv_id, conv_data in conversations_data.items():
            try:
                # Check if conversation already exists
                existing = Conversation.query.filter_by(id=conv_id).first()
                if existing:
                    print(f"  ⚠ Conversation {conv_id} already exists, skipping")
                    continue
                
                # Create conversation
                conversation = Conversation(
                    project_id=conv_data.get('projectId'),
                    title=conv_data.get('title'),
                    messages=conv_data.get('messages', []),
                    ai_model=conv_data.get('aiModel')
                )
                
                db.session.add(conversation)
                self.migration_stats['conversations'] += 1
                print(f"  ✓ Migrated conversation: {conv_id}")
                
            except Exception as e:
                error_msg = f"Failed to migrate conversation {conv_id}: {e}"
                self.migration_stats['errors'].append(error_msg)
                print(f"  ✗ {error_msg}")
        
        db.session.commit()
        print(f"✓ Migrated {self.migration_stats['conversations']} conversations")
    
    def migrate_stages(self):
        """Migrate stages to Stage model"""
        from src.models.stage import Stage
        from src.core.database import db
        
        print("\n--- Migrating Stages ---")
        
        stages_data = self.data.get('stages', {})
        
        for project_id, project_stages in stages_data.items():
            try:
                for stage_type, item_ids in project_stages.items():
                    # Check if stage already exists
                    existing = Stage.query.filter_by(project_id=project_id, stage_type=stage_type).first()
                    if existing:
                        print(f"  ⚠ Stage {project_id}:{stage_type} already exists, skipping")
                        continue
                    
                    # Create stage
                    stage = Stage(
                        project_id=project_id,
                        stage_type=stage_type,
                        item_ids=item_ids
                    )
                    
                    db.session.add(stage)
                    self.migration_stats['stages'] += 1
                    print(f"  ✓ Migrated stage: {project_id}:{stage_type} ({len(item_ids)} items)")
                    
            except Exception as e:
                error_msg = f"Failed to migrate stages for project {project_id}: {e}"
                self.migration_stats['errors'].append(error_msg)
                print(f"  ✗ {error_msg}")
        
        db.session.commit()
        print(f"✓ Migrated {self.migration_stats['stages']} stages")
    
    def migrate_product_briefs(self):
        """Migrate product briefs to ProductBrief model"""
        from src.models.stage import ProductBrief
        from src.core.database import db
        
        print("\n--- Migrating Product Briefs ---")
        
        product_briefs_data = self.data.get('productBriefs', {})
        
        for brief_id, brief_data in product_briefs_data.items():
            try:
                # Parse datetime fields
                created_at = None
                if brief_data.get('createdAt'):
                    created_at = datetime.fromisoformat(brief_data['createdAt'].replace('Z', '+00:00'))
                
                updated_at = None
                if brief_data.get('updatedAt'):
                    updated_at = datetime.fromisoformat(brief_data['updatedAt'].replace('Z', '+00:00'))
                
                # Check if product brief already exists
                existing = ProductBrief.query.filter_by(id=brief_id).first()
                if existing:
                    print(f"  ⚠ Product brief {brief_id} already exists, skipping")
                    continue
                
                # Create product brief
                product_brief = ProductBrief(
                    id=brief_id,
                    item_id=brief_data['itemId'],
                    project_id=brief_data['projectId'],
                    problem_statement=brief_data.get('problemStatement'),
                    success_metrics=brief_data.get('successMetrics', []),
                    risks=brief_data.get('risks', []),
                    competitive_analysis=brief_data.get('competitiveAnalysis'),
                    user_stories=brief_data.get('userStories', []),
                    progress=brief_data.get('progress', 0.0),
                    status=brief_data.get('status', 'draft'),
                    version=brief_data.get('version', 1),
                    created_at=created_at or datetime.utcnow(),
                    updated_at=updated_at or datetime.utcnow()
                )
                
                db.session.add(product_brief)
                self.migration_stats['product_briefs'] += 1
                print(f"  ✓ Migrated product brief: {brief_id}")
                
            except Exception as e:
                error_msg = f"Failed to migrate product brief {brief_id}: {e}"
                self.migration_stats['errors'].append(error_msg)
                print(f"  ✗ {error_msg}")
        
        db.session.commit()
        print(f"✓ Migrated {self.migration_stats['product_briefs']} product briefs")
    
    def migrate_stage_transitions(self):
        """Migrate stage transitions to StageTransition model"""
        from src.models.stage import StageTransition
        from src.core.database import db
        
        print("\n--- Migrating Stage Transitions ---")
        
        stage_transitions_data = self.data.get('stageTransitions', [])
        
        for transition_data in stage_transitions_data:
            try:
                # Parse datetime field
                timestamp = None
                if transition_data.get('timestamp'):
                    timestamp = datetime.fromisoformat(transition_data['timestamp'].replace('Z', '+00:00'))
                
                # Check if stage transition already exists (by unique combination)
                existing = StageTransition.query.filter_by(
                    item_id=transition_data['itemId'],
                    project_id=transition_data['projectId'],
                    from_stage=transition_data.get('fromStage'),
                    to_stage=transition_data['toStage'],
                    timestamp=timestamp
                ).first()
                
                if existing:
                    print(f"  ⚠ Stage transition for {transition_data['itemId']} already exists, skipping")
                    continue
                
                # Create stage transition
                stage_transition = StageTransition(
                    item_id=transition_data['itemId'],
                    project_id=transition_data['projectId'],
                    from_stage=transition_data.get('fromStage'),
                    to_stage=transition_data['toStage'],
                    actor=transition_data.get('actor', 'system'),
                    timestamp=timestamp or datetime.utcnow()
                )
                
                db.session.add(stage_transition)
                self.migration_stats['stage_transitions'] += 1
                print(f"  ✓ Migrated stage transition: {transition_data['itemId']} -> {transition_data['toStage']}")
                
            except Exception as e:
                error_msg = f"Failed to migrate stage transition for {transition_data.get('itemId', 'unknown')}: {e}"
                self.migration_stats['errors'].append(error_msg)
                print(f"  ✗ {error_msg}")
        
        db.session.commit()
        print(f"✓ Migrated {self.migration_stats['stage_transitions']} stage transitions")
    
    def migrate_system_maps(self):
        """Migrate system maps from artifact files to SystemMap model"""
        from src.models.system_map import SystemMap
        from src.core.database import db
        
        print("\n--- Migrating System Maps ---")
        
        if not self.artifacts_dir_path.exists():
            print(f"  ℹ Artifacts directory {self.artifacts_dir_path} does not exist")
            return
        
        # Find all system-map.json files in artifact directories
        system_map_files = list(self.artifacts_dir_path.glob("*/system-map.json"))
        
        for system_map_file in system_map_files:
            try:
                # Extract project ID from directory name
                project_dir = system_map_file.parent.name
                
                # Load system map data
                with open(system_map_file, 'r', encoding='utf-8') as f:
                    system_map_data = json.load(f)
                
                # Parse timestamp
                generated_at = None
                if system_map_data.get('timestamp'):
                    generated_at = datetime.fromisoformat(system_map_data['timestamp'].replace('Z', '+00:00'))
                
                # Check if system map already exists for this project
                existing = SystemMap.query.filter_by(project_id=project_dir).first()
                if existing:
                    print(f"  ⚠ System map for project {project_dir} already exists, skipping")
                    continue
                
                # Create system map
                system_map = SystemMap(
                    project_id=project_dir,  # Use directory name as project ID
                    content=system_map_data,
                    version=system_map_data.get('version', '1.0'),
                    generated_at=generated_at or datetime.utcnow()
                )
                
                db.session.add(system_map)
                self.migration_stats['system_maps'] += 1
                print(f"  ✓ Migrated system map: {project_dir}")
                
            except Exception as e:
                error_msg = f"Failed to migrate system map from {system_map_file}: {e}"
                self.migration_stats['errors'].append(error_msg)
                print(f"  ✗ {error_msg}")
        
        db.session.commit()
        print(f"✓ Migrated {self.migration_stats['system_maps']} system maps")
    
    def run_migration(self):
        """Run the complete migration process"""
        from src.core.database import db
        
        print("=== Mission Control Data Migration ===")
        print(f"Data file: {self.data_file_path}")
        print(f"Artifacts directory: {self.artifacts_dir_path}")
        
        try:
            # Load and validate data
            self.load_json_data()
            self.validate_data_structure()
            
            # Run migrations in order
            self.migrate_projects()
            self.migrate_feed_items()
            self.migrate_conversations()
            self.migrate_stages()
            self.migrate_product_briefs()
            self.migrate_stage_transitions()
            self.migrate_system_maps()
            
            # Print summary
            self.print_migration_summary()
            
        except Exception as e:
            print(f"\n✗ Migration failed: {e}")
            db.session.rollback()
            return False
        
        return True
    
    def print_migration_summary(self):
        """Print migration summary"""
        print("\n=== Migration Summary ===")
        print(f"Projects: {self.migration_stats['projects']}")
        print(f"Feed Items: {self.migration_stats['feed_items']}")
        print(f"Conversations: {self.migration_stats['conversations']}")
        print(f"Stages: {self.migration_stats['stages']}")
        print(f"Product Briefs: {self.migration_stats['product_briefs']}")
        print(f"Stage Transitions: {self.migration_stats['stage_transitions']}")
        print(f"System Maps: {self.migration_stats['system_maps']}")
        
        if self.migration_stats['errors']:
            print(f"\nErrors ({len(self.migration_stats['errors'])}):")
            for error in self.migration_stats['errors']:
                print(f"  - {error}")
        else:
            print("\n✓ Migration completed successfully with no errors!")


def main():
    """Main migration function"""
    # Default paths
    data_file = "mission-control/server/data.json"
    artifacts_dir = "mission-control/artifacts"
    
    # Allow command line arguments
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    if len(sys.argv) > 2:
        artifacts_dir = sys.argv[2]
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Import db after app context is created
        from src.core.database import db
        
        # Create database tables if they don't exist
        db.create_all()
        
        # Run migration
        migrator = MissionControlDataMigrator(data_file, artifacts_dir)
        success = migrator.run_migration()
        
        if success:
            print("\n🎉 Migration completed successfully!")
            sys.exit(0)
        else:
            print("\n💥 Migration failed!")
            sys.exit(1)


if __name__ == "__main__":
    main()