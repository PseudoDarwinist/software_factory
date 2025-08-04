"""
PRD Drift Agent - Monitors drift between PRDs and generated specifications

This agent detects when specifications drift from their associated PRD requirements,
providing early warnings to maintain alignment between business intent and technical implementation.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

try:
    from .base import BaseAgent, AgentConfig, EventProcessingResult, ProjectContext
    from ..events.domain_events import SpecFrozenEvent, PRDUpdatedEvent
    from ..events.base import BaseEvent
    from ..models.prd import PRD
    from ..models.specification_artifact import SpecificationArtifact
    from ..models.base import db
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from agents.base import BaseAgent, AgentConfig, EventProcessingResult, ProjectContext
    from events.domain_events import SpecFrozenEvent, PRDUpdatedEvent
    from events.base import BaseEvent
    from models.prd import PRD
    from models.specification_artifact import SpecificationArtifact
    from models.base import db

logger = logging.getLogger(__name__)


class PRDDriftAgent(BaseAgent):
    """
    Background agent that monitors drift between PRDs and specifications.
    
    Responsibilities:
    - Monitor spec.frozen events to check alignment with PRDs
    - Monitor PRD updates to identify specs that need review
    - Calculate drift scores based on business requirements
    - Generate drift alerts for stakeholders
    - Track drift trends over time
    """
    
    def __init__(self, event_bus):
        config = AgentConfig(
            agent_id="prd_drift_agent",
            name="PRD Drift Monitor",
            description="Monitors drift between PRDs and generated specifications",
            version="1.0.0",
            event_types=["spec.frozen", "prd.updated"],
            priority=3,  # Lower priority than DefineAgent
            max_concurrent_events=5,
            timeout_seconds=30
        )
        super().__init__(config, event_bus)
        
        # Drift detection thresholds
        self.drift_thresholds = {
            'low': 0.3,      # 30% drift - informational
            'medium': 0.5,   # 50% drift - warning
            'high': 0.7      # 70% drift - critical
        }
    
    def process_event(self, event: BaseEvent) -> EventProcessingResult:
        """Process spec.frozen and prd.updated events for drift detection"""
        start_time = datetime.utcnow()
        
        try:
            if isinstance(event, SpecFrozenEvent):
                return self._handle_spec_frozen(event, start_time)
            elif isinstance(event, PRDUpdatedEvent):
                return self._handle_prd_updated(event, start_time)
            else:
                return EventProcessingResult(
                    success=False,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=0.0,
                    error_message=f"Unsupported event type: {event.get_event_type()}"
                )
                
        except Exception as e:
            logger.error(f"Error processing event {event.metadata.event_id}: {e}")
            return EventProcessingResult(
                success=False,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                error_message=str(e)
            )
    
    def _handle_spec_frozen(self, event: SpecFrozenEvent, start_time: datetime) -> EventProcessingResult:
        """Handle spec.frozen events by checking alignment with PRD"""
        try:
            logger.info(f"Checking PRD alignment for frozen spec {event.spec_id}")
            
            # Get the specification artifacts
            spec_artifacts = SpecificationArtifact.get_spec_artifacts(event.spec_id)
            if not spec_artifacts:
                logger.warning(f"No specification artifacts found for spec {event.spec_id}")
                return EventProcessingResult(
                    success=True,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    result_data={'message': 'No artifacts to check'}
                )
            
            # Extract idea_id from spec_id (format: spec_{idea_id})
            idea_id = event.spec_id.replace('spec_', '') if event.spec_id.startswith('spec_') else None
            
            # Get associated PRD
            prd = None
            if idea_id:
                # Try idea-specific PRD first
                prd = PRD.get_frozen_for_feed_item(idea_id)
                if not prd:
                    prd = PRD.get_for_feed_item(idea_id)  # Try draft
            
            if not prd:
                # Fallback to project-level PRD
                prd = PRD.query.filter_by(project_id=event.project_id, status='frozen')\
                             .order_by(PRD.created_at.desc()).first()
            
            if not prd:
                logger.info(f"No PRD found for spec {event.spec_id}, skipping drift check")
                return EventProcessingResult(
                    success=True,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    result_data={'message': 'No PRD available for drift check'}
                )
            
            # Calculate drift score
            drift_analysis = self._calculate_drift_score(spec_artifacts, prd)
            
            # Generate alert if drift is significant
            if drift_analysis['overall_score'] >= self.drift_thresholds['medium']:
                self._generate_drift_alert(event.spec_id, event.project_id, prd, drift_analysis)
            
            logger.info(f"Drift analysis complete for spec {event.spec_id}: {drift_analysis['overall_score']:.2f}")
            
            return EventProcessingResult(
                success=True,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                result_data={
                    'drift_score': drift_analysis['overall_score'],
                    'drift_level': drift_analysis['level'],
                    'prd_id': str(prd.id),
                    'prd_type': 'idea-specific' if idea_id and prd.feed_item_id else 'project-level'
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling spec.frozen event: {e}")
            raise
    
    def _handle_prd_updated(self, event: PRDUpdatedEvent, start_time: datetime) -> EventProcessingResult:
        """Handle prd.updated events by identifying specs that need review"""
        try:
            logger.info(f"Checking specs affected by PRD update {event.prd_id}")
            
            # Get the updated PRD
            prd = PRD.query.get(event.prd_id)
            if not prd:
                logger.warning(f"PRD {event.prd_id} not found")
                return EventProcessingResult(
                    success=False,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    error_message="PRD not found"
                )
            
            # Find related specifications
            affected_specs = self._find_affected_specs(prd)
            
            # Mark specs for review if PRD changes are significant
            review_count = 0
            for spec_id in affected_specs:
                # This would trigger a review workflow in a full implementation
                logger.info(f"Spec {spec_id} may need review due to PRD changes")
                review_count += 1
            
            return EventProcessingResult(
                success=True,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                result_data={
                    'affected_specs': len(affected_specs),
                    'specs_marked_for_review': review_count
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling prd.updated event: {e}")
            raise
    
    def _calculate_drift_score(self, spec_artifacts: List[SpecificationArtifact], prd: PRD) -> Dict[str, Any]:
        """Calculate drift score between specifications and PRD"""
        try:
            prd_summary = prd.get_summary()
            
            # Extract key elements from PRD
            prd_goals = prd_summary.get('goals', {}).get('items', [])
            prd_problem = prd_summary.get('problem', {}).get('text', '')
            prd_audience = prd_summary.get('audience', {}).get('text', '')
            
            # Extract key elements from specifications
            spec_content = ""
            for artifact in spec_artifacts:
                if artifact.content:
                    spec_content += f"\n{artifact.content}"
            
            # Simple drift detection (in production, use more sophisticated NLP)
            drift_factors = {
                'goal_alignment': self._check_goal_alignment(spec_content, prd_goals),
                'problem_coverage': self._check_problem_coverage(spec_content, prd_problem),
                'audience_match': self._check_audience_match(spec_content, prd_audience)
            }
            
            # Calculate overall drift score (0 = perfect alignment, 1 = complete drift)
            overall_score = 1.0 - (
                drift_factors['goal_alignment'] * 0.5 +
                drift_factors['problem_coverage'] * 0.3 +
                drift_factors['audience_match'] * 0.2
            )
            
            # Determine drift level
            if overall_score >= self.drift_thresholds['high']:
                level = 'high'
            elif overall_score >= self.drift_thresholds['medium']:
                level = 'medium'
            elif overall_score >= self.drift_thresholds['low']:
                level = 'low'
            else:
                level = 'none'
            
            return {
                'overall_score': overall_score,
                'level': level,
                'factors': drift_factors,
                'prd_version': prd.version,
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating drift score: {e}")
            return {
                'overall_score': 0.0,
                'level': 'unknown',
                'factors': {},
                'error': str(e)
            }
    
    def _check_goal_alignment(self, spec_content: str, prd_goals: List[str]) -> float:
        """Check how well specifications align with PRD goals"""
        if not prd_goals:
            return 1.0  # No goals to check against
        
        spec_lower = spec_content.lower()
        aligned_goals = 0
        
        for goal in prd_goals:
            # Simple keyword matching (in production, use semantic similarity)
            goal_keywords = goal.lower().split()[:3]  # Take first 3 words
            if any(keyword in spec_lower for keyword in goal_keywords):
                aligned_goals += 1
        
        return aligned_goals / len(prd_goals) if prd_goals else 1.0
    
    def _check_problem_coverage(self, spec_content: str, prd_problem: str) -> float:
        """Check how well specifications address the PRD problem statement"""
        if not prd_problem:
            return 1.0  # No problem to check against
        
        # Simple keyword matching (in production, use semantic similarity)
        problem_keywords = prd_problem.lower().split()[:5]  # Take first 5 words
        spec_lower = spec_content.lower()
        
        covered_keywords = sum(1 for keyword in problem_keywords if keyword in spec_lower)
        return covered_keywords / len(problem_keywords) if problem_keywords else 1.0
    
    def _check_audience_match(self, spec_content: str, prd_audience: str) -> float:
        """Check how well specifications consider the target audience"""
        if not prd_audience:
            return 1.0  # No audience to check against
        
        # Simple keyword matching (in production, use semantic similarity)
        audience_keywords = prd_audience.lower().split()[:3]  # Take first 3 words
        spec_lower = spec_content.lower()
        
        matched_keywords = sum(1 for keyword in audience_keywords if keyword in spec_lower)
        return matched_keywords / len(audience_keywords) if audience_keywords else 1.0
    
    def _generate_drift_alert(self, spec_id: str, project_id: str, prd: PRD, drift_analysis: Dict[str, Any]):
        """Generate drift alert for stakeholders"""
        try:
            alert_data = {
                'alert_type': 'prd_drift',
                'severity': drift_analysis['level'],
                'spec_id': spec_id,
                'project_id': project_id,
                'prd_id': str(prd.id),
                'prd_version': prd.version,
                'drift_score': drift_analysis['overall_score'],
                'factors': drift_analysis['factors'],
                'timestamp': datetime.utcnow().isoformat(),
                'message': f"Specification {spec_id} shows {drift_analysis['level']} drift from PRD requirements",
                'recommendations': self._get_drift_recommendations(drift_analysis)
            }
            
            # In production, this would send notifications via email, Slack, etc.
            logger.warning(f"DRIFT ALERT: {alert_data['message']} (score: {drift_analysis['overall_score']:.2f})")
            
            # Store alert in database for dashboard display
            # This would be implemented with an Alert model in production
            
        except Exception as e:
            logger.error(f"Error generating drift alert: {e}")
    
    def _get_drift_recommendations(self, drift_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on drift analysis"""
        recommendations = []
        factors = drift_analysis.get('factors', {})
        
        if factors.get('goal_alignment', 1.0) < 0.7:
            recommendations.append("Review specification alignment with business goals")
        
        if factors.get('problem_coverage', 1.0) < 0.7:
            recommendations.append("Ensure specification addresses the core problem statement")
        
        if factors.get('audience_match', 1.0) < 0.7:
            recommendations.append("Consider target audience needs in specification details")
        
        if drift_analysis['level'] == 'high':
            recommendations.append("Consider regenerating specification with updated PRD context")
        
        return recommendations
    
    def _find_affected_specs(self, prd: PRD) -> List[str]:
        """Find specifications that might be affected by PRD changes"""
        affected_specs = []
        
        try:
            if prd.feed_item_id:
                # Idea-specific PRD - find specs for this specific idea
                spec_id = f"spec_{prd.feed_item_id}"
                specs = SpecificationArtifact.get_spec_artifacts(spec_id)
                if specs:
                    affected_specs.append(spec_id)
            else:
                # Project-level PRD - find all specs in the project
                # This would require a more sophisticated query in production
                logger.info(f"Project-level PRD {prd.id} updated - would check all project specs")
        
        except Exception as e:
            logger.error(f"Error finding affected specs: {e}")
        
        return affected_specs