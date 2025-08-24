#!/usr/bin/env python3
"""
Debug script to understand the artifact storage issue
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.models.specification_artifact import SpecificationArtifact, ArtifactStatus, ArtifactType
from src.models.base import db
from src.app import create_app
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_artifacts():
    """Debug the artifact storage and retrieval"""
    
    # Test spec_id with and without prefix
    spec_id_with_prefix = "spec_slack_C095S2NQQMV_1754978303.169829_f2419fa2"
    spec_id_without_prefix = "slack_C095S2NQQMV_1754978303.169829_f2419fa2"
    project_id = "project_1753319732860_xct3cc4z5"
    
    app = create_app()
    
    with app.app_context():
        db_instance = app.extensions['sqlalchemy']
        
        print("\n=== Checking all artifacts in database ===")
        all_artifacts = db_instance.session.query(SpecificationArtifact).all()
        print(f"Total artifacts in database: {len(all_artifacts)}")
        
        for artifact in all_artifacts[:10]:  # Show first 10
            print(f"\nArtifact ID: {artifact.id}")
            print(f"  Spec ID: {artifact.spec_id}")
            print(f"  Project ID: {artifact.project_id}")
            print(f"  Type: {artifact.artifact_type.value if hasattr(artifact.artifact_type, 'value') else artifact.artifact_type}")
            print(f"  Status: {artifact.status.value if hasattr(artifact.status, 'value') else artifact.status}")
        
        print("\n=== Testing queries ===")
        
        # Test 1: Query with full spec_id with prefix
        print(f"\n1. Querying with spec_id WITH prefix: {spec_id_with_prefix}")
        artifacts1 = db_instance.session.query(SpecificationArtifact).filter_by(
            spec_id=spec_id_with_prefix
        ).all()
        print(f"   Found: {len(artifacts1)} artifacts")
        
        # Test 2: Query with spec_id without prefix
        print(f"\n2. Querying with spec_id WITHOUT prefix: {spec_id_without_prefix}")
        artifacts2 = db_instance.session.query(SpecificationArtifact).filter_by(
            spec_id=spec_id_without_prefix
        ).all()
        print(f"   Found: {len(artifacts2)} artifacts")
        
        # Test 3: Query with project_id only
        print(f"\n3. Querying with project_id only: {project_id}")
        artifacts3 = db_instance.session.query(SpecificationArtifact).filter_by(
            project_id=project_id
        ).all()
        print(f"   Found: {len(artifacts3)} artifacts")
        for a in artifacts3:
            print(f"   - Spec ID: {a.spec_id}, Type: {a.artifact_type.value if hasattr(a.artifact_type, 'value') else a.artifact_type}")
        
        # Test 4: Query with LIKE pattern
        print(f"\n4. Querying with LIKE pattern for spec containing the Slack ID")
        pattern = "%1754978303.169829%"
        artifacts4 = db_instance.session.query(SpecificationArtifact).filter(
            SpecificationArtifact.spec_id.like(pattern)
        ).all()
        print(f"   Found: {len(artifacts4)} artifacts")
        for a in artifacts4:
            print(f"   - Full Spec ID: {a.spec_id}")
            print(f"     Project ID: {a.project_id}")
            print(f"     Type: {a.artifact_type.value if hasattr(a.artifact_type, 'value') else a.artifact_type}")
            print(f"     Status: {a.status.value if hasattr(a.status, 'value') else a.status}")

if __name__ == "__main__":
    debug_artifacts()
