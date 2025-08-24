#!/usr/bin/env python3
"""
Fix script for work order generation issue
This script diagnoses and fixes the frozen spec artifact issue
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.models.specification_artifact import SpecificationArtifact, ArtifactStatus, ArtifactType
from src.models.base import db
from flask import Flask
from src.app import create_app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnose_spec_artifacts(spec_id, project_id, db):
    """Diagnose the state of spec artifacts"""
    logger.info(f"\n=== Diagnosing spec artifacts ===")
    logger.info(f"Spec ID: {spec_id}")
    logger.info(f"Project ID: {project_id}")
    
    # Query all artifacts for this spec using db.session
    all_artifacts = db.session.query(SpecificationArtifact).filter_by(spec_id=spec_id).all()
    logger.info(f"\nFound {len(all_artifacts)} total artifacts for spec {spec_id}")
    
    for artifact in all_artifacts:
        logger.info(f"\nArtifact: {artifact.id}")
        logger.info(f"  Type: {artifact.artifact_type.value if hasattr(artifact.artifact_type, 'value') else artifact.artifact_type}")
        logger.info(f"  Status: {artifact.status.value if hasattr(artifact.status, 'value') else artifact.status}")
        logger.info(f"  Project ID: {artifact.project_id}")
        logger.info(f"  Content length: {len(artifact.content) if artifact.content else 0}")
    
    # Check for frozen artifacts
    frozen_artifacts = [a for a in all_artifacts if (
        (hasattr(a.status, 'value') and a.status.value == 'frozen') or
        (isinstance(a.status, str) and a.status == 'frozen') or
        a.status == ArtifactStatus.FROZEN
    )]
    
    logger.info(f"\nFound {len(frozen_artifacts)} frozen artifacts")
    
    # Check for tasks artifact specifically
    tasks_artifacts = [a for a in all_artifacts if (
        (hasattr(a.artifact_type, 'value') and a.artifact_type.value == 'tasks') or
        (isinstance(a.artifact_type, str) and a.artifact_type == 'tasks') or
        a.artifact_type == ArtifactType.TASKS
    )]
    
    logger.info(f"Found {len(tasks_artifacts)} tasks artifacts")
    
    return all_artifacts, frozen_artifacts, tasks_artifacts

def fix_frozen_status(spec_id, project_id, db):
    """Fix the frozen status of spec artifacts"""
    logger.info(f"\n=== Fixing frozen status ===")
    
    # Find all artifacts for this spec using db.session
    artifacts = db.session.query(SpecificationArtifact).filter_by(spec_id=spec_id).all()
    
    fixed_count = 0
    for artifact in artifacts:
        # Check if the artifact should be frozen (based on your spec being frozen)
        # Update the status to FROZEN if it's not already
        if artifact.status != ArtifactStatus.FROZEN:
            logger.info(f"Updating artifact {artifact.id} status to FROZEN")
            artifact.status = ArtifactStatus.FROZEN
            artifact.updated_by = 'fix_script'
            fixed_count += 1
        
        # Ensure project_id is set correctly
        if artifact.project_id != project_id:
            logger.info(f"Updating artifact {artifact.id} project_id from {artifact.project_id} to {project_id}")
            artifact.project_id = project_id
            fixed_count += 1
    
    if fixed_count > 0:
        db.session.commit()
        logger.info(f"Fixed {fixed_count} artifacts")
    else:
        logger.info("No artifacts needed fixing")
    
    return fixed_count

def main():
    # Your specific spec and project IDs from the error
    spec_id = "spec_slack_C095S2NQQMV_1754978303.169829_f2419fa2"
    project_id = "project_1753319732860_xct3cc4z5"
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Get database instance
        db = app.extensions['sqlalchemy']
        
        # Diagnose the current state
        all_artifacts, frozen_artifacts, tasks_artifacts = diagnose_spec_artifacts(spec_id, project_id, db)
        
        if len(frozen_artifacts) == 0:
            logger.info("\n⚠️  No frozen artifacts found - this is the problem!")
            
            # Ask for confirmation before fixing
            response = input("\nDo you want to fix the frozen status? (y/n): ")
            if response.lower() == 'y':
                fixed_count = fix_frozen_status(spec_id, project_id, db)
                
                # Re-diagnose to confirm the fix
                logger.info("\n=== Verifying fix ===")
                all_artifacts, frozen_artifacts, tasks_artifacts = diagnose_spec_artifacts(spec_id, project_id, db)
                
                if len(frozen_artifacts) > 0:
                    logger.info("✅ Fix successful! Frozen artifacts are now available.")
                    logger.info("You should now be able to generate work orders.")
                else:
                    logger.info("❌ Fix may not have worked. Please check the database manually.")
        else:
            logger.info("\n✅ Frozen artifacts already exist. The problem might be elsewhere.")
            
            # Check if the issue is with project_id mismatch
            mismatched = [a for a in frozen_artifacts if a.project_id != project_id]
            if mismatched:
                logger.info(f"\n⚠️  Found {len(mismatched)} artifacts with mismatched project_id")
                response = input("\nDo you want to fix the project_id mismatch? (y/n): ")
                if response.lower() == 'y':
                    fix_frozen_status(spec_id, project_id, db)
                    logger.info("✅ Project ID mismatch fixed!")

if __name__ == "__main__":
    main()
