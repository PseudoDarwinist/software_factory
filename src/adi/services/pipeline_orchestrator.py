"""
Pipeline Orchestrator

Orchestrates the complete scoring pipeline with error handling and monitoring.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

from ..models.finding import Finding, FindingData
from ..models.insight import Insight
from ..schemas.decision_log import DecisionLog
from .scoring_pipeline import ScoringPipeline, get_scoring_pipeline
from .insight_service import InsightService, get_insight_service
from .event_bus import ADIEventBus, ADIEvents

try:
    from ...models.base import db
except ImportError:
    try:
        from src.models.base import db
    except ImportError:
        from models.base import db

logger = logging.getLogger(__name__)


class PipelineOrchestrationError(Exception):
    """Raised when pipeline orchestration fails."""
    pass


class PipelineOrchestrator:
    """
    Orchestrates the complete ADI scoring pipeline with error handling.
    
    Coordinates scoring pipeline, finding storage, and insight generation
    with proper error handling and monitoring.
    """
    
    def __init__(self, event_bus: Optional[ADIEventBus] = None):
        self.event_bus = event_bus
        self.scoring_pipeline = get_scoring_pipeline(event_bus)
        self.insight_service = get_insight_service(event_bus)
    
    def process_decision_log(self, decision_log: DecisionLog) -> Dict[str, Any]:
        """
        Process a single decision log through the complete pipeline.
        
        Args:
            decision_log: The decision log to process
            
        Returns:
            Processing results with findings and insights
            
        Raises:
            PipelineOrchestrationError: If processing fails
        """
        start_time = datetime.utcnow()
        processing_id = f"{decision_log.project_id}:{decision_log.case_id}:{start_time.timestamp()}"
        
        logger.info(f"Processing decision log {decision_log.case_id} for project {decision_log.project_id}")
        
        try:
            with self._error_handling_context(processing_id):
                # Step 1: Score the decision log
                findings_data = self.scoring_pipeline.score_decision(decision_log)
                
                # Step 2: Store findings in database
                stored_findings = self._store_findings(decision_log, findings_data)
                
                # Step 3: Trigger insight generation (async/background)
                insights_generated = self._trigger_insight_generation(decision_log.project_id)
                
                # Calculate processing metrics
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                
                result = {
                    'processing_id': processing_id,
                    'project_id': decision_log.project_id,
                    'case_id': decision_log.case_id,
                    'findings_count': len(findings_data),
                    'stored_findings': len(stored_findings),
                    'insights_generated': insights_generated,
                    'processing_time_seconds': processing_time,
                    'timestamp': start_time.isoformat(),
                    'status': 'success'
                }
                
                # Emit processing completed event
                if self.event_bus:
                    self.event_bus.emit(ADIEvents.PIPELINE_COMPLETED, result)
                
                logger.info(f"Successfully processed {decision_log.case_id}: {len(findings_data)} findings, {insights_generated} insights")
                return result
                
        except Exception as e:
            error_result = {
                'processing_id': processing_id,
                'project_id': decision_log.project_id,
                'case_id': decision_log.case_id,
                'error': str(e),
                'processing_time_seconds': (datetime.utcnow() - start_time).total_seconds(),
                'timestamp': start_time.isoformat(),
                'status': 'error'
            }
            
            # Emit processing failed event
            if self.event_bus:
                self.event_bus.emit(ADIEvents.PIPELINE_FAILED, error_result)
            
            logger.error(f"Failed to process {decision_log.case_id}: {str(e)}")
            raise PipelineOrchestrationError(f"Pipeline processing failed: {str(e)}") from e
    
    def process_batch_decision_logs(self, decision_logs: List[DecisionLog]) -> Dict[str, Any]:
        """
        Process multiple decision logs in batch.
        
        Args:
            decision_logs: List of decision logs to process
            
        Returns:
            Batch processing results
        """
        start_time = datetime.utcnow()
        batch_id = f"batch:{start_time.timestamp()}"
        
        logger.info(f"Processing batch of {len(decision_logs)} decision logs")
        
        results = {
            'batch_id': batch_id,
            'total_logs': len(decision_logs),
            'successful': 0,
            'failed': 0,
            'findings_generated': 0,
            'insights_generated': 0,
            'errors': [],
            'start_time': start_time.isoformat()
        }
        
        # Process each log individually
        for decision_log in decision_logs:
            try:
                result = self.process_decision_log(decision_log)
                results['successful'] += 1
                results['findings_generated'] += result['findings_count']
                results['insights_generated'] += result['insights_generated']
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'case_id': decision_log.case_id,
                    'error': str(e)
                })
                logger.warning(f"Failed to process {decision_log.case_id} in batch: {str(e)}")
        
        # Final batch insight generation
        if results['successful'] > 0:
            # Group by project for insight generation
            projects = set(log.project_id for log in decision_logs)
            for project_id in projects:
                try:
                    project_insights = self.insight_service.cluster_findings_into_insights(project_id)
                    results['insights_generated'] += len(project_insights)
                except Exception as e:
                    logger.warning(f"Batch insight generation failed for project {project_id}: {str(e)}")
        
        results['end_time'] = datetime.utcnow().isoformat()
        results['processing_time_seconds'] = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"Batch processing completed: {results['successful']}/{results['total_logs']} successful")
        return results
    
    def _store_findings(self, decision_log: DecisionLog, findings_data: List[FindingData]) -> List[Finding]:
        """Store findings in the database."""
        stored_findings = []
        
        # Calculate expiration time for findings (they get clustered into insights)
        expires_at = datetime.utcnow() + timedelta(days=7)  # Keep findings for 7 days
        
        for finding_data in findings_data:
            # Generate signature for clustering
            signature = self.scoring_pipeline.generate_signature(finding_data, decision_log.project_id)
            
            # Convert to database model
            finding = finding_data.to_model(
                project_id=decision_log.project_id,
                case_id=decision_log.case_id,
                signature=signature,
                expires_at=expires_at
            )
            
            db.session.add(finding)
            stored_findings.append(finding)
        
        # Commit findings
        db.session.commit()
        
        return stored_findings
    
    def _trigger_insight_generation(self, project_id: str) -> int:
        """Trigger insight generation for a project."""
        try:
            # Generate insights from recent findings
            new_insights = self.insight_service.cluster_findings_into_insights(project_id)
            return len(new_insights)
            
        except Exception as e:
            logger.warning(f"Insight generation failed for project {project_id}: {str(e)}")
            return 0
    
    @contextmanager
    def _error_handling_context(self, processing_id: str):
        """Context manager for error handling and cleanup."""
        try:
            yield
        except Exception as e:
            # Rollback any database changes
            db.session.rollback()
            
            # Log detailed error information
            logger.error(f"Pipeline error in {processing_id}: {str(e)}", exc_info=True)
            
            # Re-raise the exception
            raise
    
    def get_pipeline_health(self) -> Dict[str, Any]:
        """Get pipeline health metrics."""
        try:
            # Get recent processing statistics
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            recent_findings = Finding.query.filter(
                Finding.created_at >= cutoff_time
            ).count()
            
            recent_insights = Insight.query.filter(
                Insight.created_at >= cutoff_time
            ).count()
            
            # Get error rates (would need error tracking table in real implementation)
            health = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': {
                    'recent_findings_1h': recent_findings,
                    'recent_insights_1h': recent_insights,
                    'pipeline_components': {
                        'scoring_pipeline': 'healthy',
                        'insight_service': 'healthy',
                        'database': 'healthy'
                    }
                }
            }
            
            return health
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    def cleanup_expired_findings(self) -> int:
        """Clean up expired findings."""
        try:
            cutoff_time = datetime.utcnow()
            
            expired_findings = Finding.query.filter(
                Finding.expires_at <= cutoff_time
            ).all()
            
            count = len(expired_findings)
            
            for finding in expired_findings:
                db.session.delete(finding)
            
            db.session.commit()
            
            logger.info(f"Cleaned up {count} expired findings")
            return count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Finding cleanup failed: {str(e)}")
            raise
    
    def reprocess_failed_cases(self, project_id: str, hours_back: int = 24) -> Dict[str, Any]:
        """Reprocess cases that may have failed."""
        # This would require error tracking - placeholder implementation
        logger.info(f"Reprocessing failed cases for project {project_id} from last {hours_back} hours")
        
        return {
            'project_id': project_id,
            'reprocessed_count': 0,
            'successful_count': 0,
            'failed_count': 0,
            'timestamp': datetime.utcnow().isoformat()
        }


# Global pipeline orchestrator instance
_pipeline_orchestrator: Optional[PipelineOrchestrator] = None


def get_pipeline_orchestrator(event_bus: Optional[ADIEventBus] = None) -> PipelineOrchestrator:
    """Get the global pipeline orchestrator instance."""
    global _pipeline_orchestrator
    
    if _pipeline_orchestrator is None:
        _pipeline_orchestrator = PipelineOrchestrator(event_bus)
    
    return _pipeline_orchestrator