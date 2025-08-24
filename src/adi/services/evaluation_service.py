"""
Evaluation Service

Service for managing evaluation sets, case selection, and versioning.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from adi.models.evaluation import EvalSet, EvalResult
from adi.models.decision_log import DecisionLog
from adi.models.insight import Insight
from src.models.base import db
from adi.services.domain_pack_loader import DomainPack

logger = logging.getLogger(__name__)


@dataclass
class SelectCriteria:
    """Criteria for selecting cases for evaluation."""
    failure_mode_tags: Optional[List[str]] = None
    time_window_days: Optional[int] = None
    min_cases: int = 10
    max_cases: int = 100
    event_types: Optional[List[str]] = None
    severity_levels: Optional[List[str]] = None
    status_filters: Optional[List[str]] = None


@dataclass
class VerifyCriteria:
    """Criteria for verifying evaluation results."""
    check_types: List[str]  # e.g., ['sla', 'template', 'policy']
    custom_validators: Optional[List[str]] = None
    expected_outcomes: Optional[Dict[str, Any]] = None


@dataclass
class EvalBlueprint:
    """Blueprint for creating evaluation sets."""
    id: str
    tag: str  # Failure mode tag
    select: SelectCriteria
    verify: VerifyCriteria
    min_pass_rate: float
    description: Optional[str] = None


class EvaluationService:
    """Service for managing evaluation sets and case selection."""
    
    def __init__(self):
        pass
    
    def create_eval_set(self, project_id: str, name: str, blueprint: EvalBlueprint) -> EvalSet:
        """
        Create a new evaluation set with case selection.
        
        Args:
            project_id: Project identifier
            name: Name for the evaluation set
            blueprint: Evaluation blueprint configuration
            
        Returns:
            Created EvalSet instance
        """
        try:
            # Validate blueprint
            self._validate_blueprint(blueprint)
            
            # Select cases based on criteria
            selected_cases = self._select_cases(project_id, blueprint.select)
            
            # Create blueprint data with selected cases
            blueprint_data = {
                'id': blueprint.id,
                'tag': blueprint.tag,
                'select': {
                    'failure_mode_tags': blueprint.select.failure_mode_tags,
                    'time_window_days': blueprint.select.time_window_days,
                    'min_cases': blueprint.select.min_cases,
                    'max_cases': blueprint.select.max_cases,
                    'event_types': blueprint.select.event_types,
                    'severity_levels': blueprint.select.severity_levels,
                    'status_filters': blueprint.select.status_filters
                },
                'verify': {
                    'check_types': blueprint.verify.check_types,
                    'custom_validators': blueprint.verify.custom_validators,
                    'expected_outcomes': blueprint.verify.expected_outcomes
                },
                'min_pass_rate': blueprint.min_pass_rate,
                'description': blueprint.description,
                'selected_cases': selected_cases,
                'case_count': len(selected_cases),
                'created_timestamp': datetime.utcnow().isoformat()
            }
            
            # Create eval set
            eval_set = EvalSet(
                project_id=project_id,
                name=name,
                blueprint=blueprint_data
            )
            
            db.session.add(eval_set)
            db.session.commit()
            
            logger.info(f"Created eval set '{name}' for project {project_id} with {len(selected_cases)} cases")
            
            return eval_set
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating eval set: {str(e)}")
            raise
    
    def update_eval_set(self, eval_set_id: str, updates: Dict[str, Any]) -> EvalSet:
        """
        Update an existing evaluation set.
        
        Args:
            eval_set_id: Evaluation set ID
            updates: Dictionary of updates to apply
            
        Returns:
            Updated EvalSet instance
        """
        try:
            eval_set = EvalSet.query.get(eval_set_id)
            if not eval_set:
                raise ValueError(f"Evaluation set {eval_set_id} not found")
            
            # Create versioned backup of current blueprint
            current_blueprint = eval_set.blueprint.copy()
            current_blueprint['version_timestamp'] = datetime.utcnow().isoformat()
            
            # Store version history
            if 'version_history' not in eval_set.blueprint:
                eval_set.blueprint['version_history'] = []
            eval_set.blueprint['version_history'].append(current_blueprint)
            
            # Apply updates
            if 'name' in updates:
                eval_set.name = updates['name']
            
            if 'blueprint' in updates:
                # Merge blueprint updates
                blueprint_updates = updates['blueprint']
                for key, value in blueprint_updates.items():
                    eval_set.blueprint[key] = value
                
                # Re-select cases if selection criteria changed
                if 'select' in blueprint_updates:
                    select_criteria = SelectCriteria(**blueprint_updates['select'])
                    selected_cases = self._select_cases(eval_set.project_id, select_criteria)
                    eval_set.blueprint['selected_cases'] = selected_cases
                    eval_set.blueprint['case_count'] = len(selected_cases)
                
                eval_set.blueprint['updated_timestamp'] = datetime.utcnow().isoformat()
            
            # Mark as modified for SQLAlchemy
            db.session.merge(eval_set)
            db.session.commit()
            
            logger.info(f"Updated eval set {eval_set_id}")
            
            return eval_set
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating eval set {eval_set_id}: {str(e)}")
            raise
    
    def get_eval_set_history(self, eval_set_id: str) -> List[Dict[str, Any]]:
        """
        Get version history for an evaluation set.
        
        Args:
            eval_set_id: Evaluation set ID
            
        Returns:
            List of historical versions
        """
        try:
            eval_set = EvalSet.query.get(eval_set_id)
            if not eval_set:
                raise ValueError(f"Evaluation set {eval_set_id} not found")
            
            history = eval_set.blueprint.get('version_history', [])
            
            # Add current version
            current_version = eval_set.blueprint.copy()
            current_version.pop('version_history', None)  # Remove history from current version
            current_version['is_current'] = True
            
            return [current_version] + history
            
        except Exception as e:
            logger.error(f"Error getting eval set history {eval_set_id}: {str(e)}")
            raise
    
    def rollback_eval_set(self, eval_set_id: str, version_timestamp: str) -> EvalSet:
        """
        Rollback an evaluation set to a previous version.
        
        Args:
            eval_set_id: Evaluation set ID
            version_timestamp: Timestamp of version to rollback to
            
        Returns:
            Updated EvalSet instance
        """
        try:
            eval_set = EvalSet.query.get(eval_set_id)
            if not eval_set:
                raise ValueError(f"Evaluation set {eval_set_id} not found")
            
            # Find the version to rollback to
            history = eval_set.blueprint.get('version_history', [])
            target_version = None
            
            for version in history:
                if version.get('version_timestamp') == version_timestamp:
                    target_version = version
                    break
            
            if not target_version:
                raise ValueError(f"Version {version_timestamp} not found in history")
            
            # Create backup of current version
            current_blueprint = eval_set.blueprint.copy()
            current_blueprint['version_timestamp'] = datetime.utcnow().isoformat()
            current_blueprint['rollback_from'] = version_timestamp
            
            # Update history
            if 'version_history' not in eval_set.blueprint:
                eval_set.blueprint['version_history'] = []
            eval_set.blueprint['version_history'].append(current_blueprint)
            
            # Restore target version
            target_version.pop('version_timestamp', None)
            target_version.pop('rollback_from', None)
            target_version['restored_timestamp'] = datetime.utcnow().isoformat()
            
            eval_set.blueprint = target_version
            
            db.session.merge(eval_set)
            db.session.commit()
            
            logger.info(f"Rolled back eval set {eval_set_id} to version {version_timestamp}")
            
            return eval_set
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error rolling back eval set {eval_set_id}: {str(e)}")
            raise
    
    def _select_cases(self, project_id: str, criteria: SelectCriteria) -> List[str]:
        """
        Select cases based on selection criteria.
        
        Args:
            project_id: Project identifier
            criteria: Selection criteria
            
        Returns:
            List of selected case IDs
        """
        try:
            # Build base query for decision logs
            query = DecisionLog.query.filter(DecisionLog.project_id == project_id)
            
            # Apply time window filter
            if criteria.time_window_days:
                cutoff_date = datetime.utcnow() - timedelta(days=criteria.time_window_days)
                query = query.filter(DecisionLog.created_at >= cutoff_date)
            
            # Apply event type filter
            if criteria.event_types:
                query = query.filter(DecisionLog.event_data['type'].astext.in_(criteria.event_types))
            
            # Apply status filter
            if criteria.status_filters:
                query = query.filter(DecisionLog.decision_data['status'].astext.in_(criteria.status_filters))
            
            # Get initial case set
            cases = query.order_by(DecisionLog.created_at.desc()).limit(criteria.max_cases * 2).all()
            
            # Filter by failure mode tags if specified
            if criteria.failure_mode_tags:
                filtered_cases = []
                for case in cases:
                    # Check if case has associated insights with matching tags
                    insights = Insight.query.filter(
                        Insight.project_id == project_id,
                        Insight.evidence['case_ids'].astext.contains(case.case_id)
                    ).all()
                    
                    for insight in insights:
                        if any(tag in criteria.failure_mode_tags for tag in insight.tags):
                            filtered_cases.append(case)
                            break
                
                cases = filtered_cases
            
            # Apply severity level filter
            if criteria.severity_levels:
                filtered_cases = []
                for case in cases:
                    # Check associated insights for severity
                    insights = Insight.query.filter(
                        Insight.project_id == project_id,
                        Insight.evidence['case_ids'].astext.contains(case.case_id)
                    ).all()
                    
                    for insight in insights:
                        if insight.severity in criteria.severity_levels:
                            filtered_cases.append(case)
                            break
                
                cases = filtered_cases
            
            # Ensure we have minimum required cases
            if len(cases) < criteria.min_cases:
                logger.warning(f"Only found {len(cases)} cases, minimum required: {criteria.min_cases}")
            
            # Limit to max cases
            cases = cases[:criteria.max_cases]
            
            # Extract case IDs
            case_ids = [case.case_id for case in cases]
            
            logger.info(f"Selected {len(case_ids)} cases for evaluation")
            
            return case_ids
            
        except Exception as e:
            logger.error(f"Error selecting cases: {str(e)}")
            raise
    
    def _validate_blueprint(self, blueprint: EvalBlueprint) -> None:
        """
        Validate evaluation blueprint configuration.
        
        Args:
            blueprint: Blueprint to validate
            
        Raises:
            ValueError: If blueprint is invalid
        """
        if not blueprint.id:
            raise ValueError("Blueprint ID is required")
        
        if not blueprint.tag:
            raise ValueError("Blueprint tag is required")
        
        if not blueprint.verify.check_types:
            raise ValueError("At least one verification check type is required")
        
        if not 0 <= blueprint.min_pass_rate <= 1:
            raise ValueError("Minimum pass rate must be between 0 and 1")
        
        if blueprint.select.min_cases <= 0:
            raise ValueError("Minimum cases must be greater than 0")
        
        if blueprint.select.max_cases < blueprint.select.min_cases:
            raise ValueError("Maximum cases must be greater than or equal to minimum cases")
    
    def get_eval_sets_by_project(self, project_id: str) -> List[EvalSet]:
        """
        Get all evaluation sets for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of EvalSet instances
        """
        try:
            return EvalSet.query.filter(
                EvalSet.project_id == project_id
            ).order_by(EvalSet.created_at.desc()).all()
            
        except Exception as e:
            logger.error(f"Error getting eval sets for project {project_id}: {str(e)}")
            raise
    
    def delete_eval_set(self, eval_set_id: str) -> bool:
        """
        Delete an evaluation set and all its results.
        
        Args:
            eval_set_id: Evaluation set ID
            
        Returns:
            True if deleted successfully
        """
        try:
            eval_set = EvalSet.query.get(eval_set_id)
            if not eval_set:
                return False
            
            # Delete associated results (cascade should handle this)
            db.session.delete(eval_set)
            db.session.commit()
            
            logger.info(f"Deleted eval set {eval_set_id}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting eval set {eval_set_id}: {str(e)}")
            raise