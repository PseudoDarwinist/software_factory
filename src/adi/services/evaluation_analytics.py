"""
Evaluation Analytics Service

Service for analyzing evaluation results, trends, and deployment confidence.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from adi.models.evaluation import EvalSet, EvalResult
from adi.models.trend import Trend
from src.models.base import db
from sqlalchemy import func, desc, and_

logger = logging.getLogger(__name__)


@dataclass
class TrendPoint:
    """A single point in a trend analysis."""
    timestamp: datetime
    pass_rate: float
    total_cases: int
    pack_version: str
    run_id: str


@dataclass
class FailingCaseAnalysis:
    """Analysis of failing cases."""
    case_id: str
    failure_count: int
    last_failure: datetime
    failure_types: List[str]
    pack_versions: List[str]
    details: Dict[str, Any]


@dataclass
class DeploymentConfidence:
    """Confidence metrics for deployment decisions."""
    confidence_score: float  # 0.0 to 1.0
    pass_rate_trend: str  # 'improving', 'stable', 'declining'
    recent_pass_rate: float
    baseline_pass_rate: float
    recommendation: str  # 'deploy', 'hold', 'rollback'
    factors: List[str]  # Factors influencing the confidence


@dataclass
class EvaluationDashboard:
    """Complete dashboard data for evaluation results."""
    project_id: str
    eval_sets: List[Dict[str, Any]]
    recent_results: List[Dict[str, Any]]
    trend_analysis: List[TrendPoint]
    failing_cases: List[FailingCaseAnalysis]
    deployment_confidence: DeploymentConfidence
    summary_stats: Dict[str, Any]


class EvaluationAnalytics:
    """Service for evaluation analytics and insights."""
    
    def __init__(self):
        pass
    
    def get_evaluation_dashboard(self, project_id: str, days: int = 30) -> EvaluationDashboard:
        """
        Get comprehensive evaluation dashboard for a project.
        
        Args:
            project_id: Project identifier
            days: Number of days to analyze (default: 30)
            
        Returns:
            EvaluationDashboard with complete analytics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get eval sets
            eval_sets = self._get_eval_sets_summary(project_id)
            
            # Get recent results
            recent_results = self._get_recent_results(project_id, cutoff_date)
            
            # Get trend analysis
            trend_analysis = self._get_trend_analysis(project_id, cutoff_date)
            
            # Get failing cases analysis
            failing_cases = self._get_failing_cases_analysis(project_id, cutoff_date)
            
            # Calculate deployment confidence
            deployment_confidence = self._calculate_deployment_confidence(project_id, trend_analysis)
            
            # Get summary statistics
            summary_stats = self._get_summary_statistics(project_id, cutoff_date)
            
            return EvaluationDashboard(
                project_id=project_id,
                eval_sets=eval_sets,
                recent_results=recent_results,
                trend_analysis=trend_analysis,
                failing_cases=failing_cases,
                deployment_confidence=deployment_confidence,
                summary_stats=summary_stats
            )
            
        except Exception as e:
            logger.error(f"Error creating evaluation dashboard for {project_id}: {str(e)}")
            raise
    
    def get_trend_analysis(
        self, 
        project_id: str, 
        eval_set_id: Optional[str] = None, 
        days: int = 30
    ) -> List[TrendPoint]:
        """
        Get trend analysis for evaluation results.
        
        Args:
            project_id: Project identifier
            eval_set_id: Optional specific eval set ID
            days: Number of days to analyze
            
        Returns:
            List of trend points
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Build query
            query = db.session.query(EvalResult).join(EvalSet).filter(
                EvalSet.project_id == project_id,
                EvalResult.run_timestamp >= cutoff_date
            )
            
            if eval_set_id:
                query = query.filter(EvalResult.eval_set_id == eval_set_id)
            
            # Get results ordered by timestamp
            results = query.order_by(EvalResult.run_timestamp.asc()).all()
            
            # Convert to trend points
            trend_points = []
            for result in results:
                trend_points.append(TrendPoint(
                    timestamp=result.run_timestamp,
                    pass_rate=float(result.pass_rate),
                    total_cases=result.total_cases,
                    pack_version=result.pack_version,
                    run_id=result.run_id
                ))
            
            return trend_points
            
        except Exception as e:
            logger.error(f"Error getting trend analysis: {str(e)}")
            return []
    
    def get_failing_cases_analysis(
        self, 
        project_id: str, 
        days: int = 30
    ) -> List[FailingCaseAnalysis]:
        """
        Analyze failing cases to identify patterns.
        
        Args:
            project_id: Project identifier
            days: Number of days to analyze
            
        Returns:
            List of failing case analyses
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get recent results with failed cases
            results = db.session.query(EvalResult).join(EvalSet).filter(
                EvalSet.project_id == project_id,
                EvalResult.run_timestamp >= cutoff_date,
                EvalResult.failed_cases != []
            ).all()
            
            # Aggregate failing cases
            case_failures = defaultdict(list)
            
            for result in results:
                failed_cases = result.failed_cases or []
                for case_id in failed_cases:
                    case_failures[case_id].append({
                        'timestamp': result.run_timestamp,
                        'pack_version': result.pack_version,
                        'run_id': result.run_id
                    })
            
            # Create analysis for each failing case
            analyses = []
            for case_id, failures in case_failures.items():
                if len(failures) > 1:  # Only include cases that failed multiple times
                    analyses.append(FailingCaseAnalysis(
                        case_id=case_id,
                        failure_count=len(failures),
                        last_failure=max(f['timestamp'] for f in failures),
                        failure_types=[],  # Would need more detailed failure data
                        pack_versions=list(set(f['pack_version'] for f in failures)),
                        details={
                            'failures': failures,
                            'first_failure': min(f['timestamp'] for f in failures)
                        }
                    ))
            
            # Sort by failure count (most problematic first)
            analyses.sort(key=lambda x: x.failure_count, reverse=True)
            
            return analyses[:20]  # Return top 20 most problematic cases
            
        except Exception as e:
            logger.error(f"Error analyzing failing cases: {str(e)}")
            return []
    
    def calculate_deployment_confidence(
        self, 
        project_id: str, 
        pack_version: Optional[str] = None
    ) -> DeploymentConfidence:
        """
        Calculate deployment confidence based on evaluation trends.
        
        Args:
            project_id: Project identifier
            pack_version: Optional specific pack version to analyze
            
        Returns:
            DeploymentConfidence metrics
        """
        try:
            # Get recent trend data
            trend_points = self.get_trend_analysis(project_id, days=14)
            
            if len(trend_points) < 2:
                return DeploymentConfidence(
                    confidence_score=0.5,
                    pass_rate_trend='unknown',
                    recent_pass_rate=0.0,
                    baseline_pass_rate=0.0,
                    recommendation='hold',
                    factors=['Insufficient evaluation data']
                )
            
            # Calculate metrics
            recent_pass_rate = trend_points[-1].pass_rate
            baseline_pass_rate = sum(p.pass_rate for p in trend_points[:3]) / min(3, len(trend_points))
            
            # Determine trend
            if len(trend_points) >= 3:
                recent_avg = sum(p.pass_rate for p in trend_points[-3:]) / 3
                older_avg = sum(p.pass_rate for p in trend_points[:-3]) / max(1, len(trend_points) - 3)
                
                if recent_avg > older_avg + 0.02:  # 2% improvement
                    trend = 'improving'
                elif recent_avg < older_avg - 0.02:  # 2% decline
                    trend = 'declining'
                else:
                    trend = 'stable'
            else:
                trend = 'stable'
            
            # Calculate confidence score
            confidence_factors = []
            confidence_score = 0.5  # Base confidence
            
            # Factor 1: Recent pass rate
            if recent_pass_rate >= 0.95:
                confidence_score += 0.3
                confidence_factors.append('High recent pass rate (≥95%)')
            elif recent_pass_rate >= 0.90:
                confidence_score += 0.2
                confidence_factors.append('Good recent pass rate (≥90%)')
            elif recent_pass_rate >= 0.80:
                confidence_score += 0.1
                confidence_factors.append('Acceptable recent pass rate (≥80%)')
            else:
                confidence_score -= 0.2
                confidence_factors.append('Low recent pass rate (<80%)')
            
            # Factor 2: Trend direction
            if trend == 'improving':
                confidence_score += 0.2
                confidence_factors.append('Improving trend')
            elif trend == 'declining':
                confidence_score -= 0.3
                confidence_factors.append('Declining trend')
            else:
                confidence_factors.append('Stable trend')
            
            # Factor 3: Consistency
            pass_rates = [p.pass_rate for p in trend_points[-5:]]  # Last 5 runs
            if len(pass_rates) > 1:
                variance = sum((x - sum(pass_rates)/len(pass_rates))**2 for x in pass_rates) / len(pass_rates)
                if variance < 0.01:  # Low variance
                    confidence_score += 0.1
                    confidence_factors.append('Consistent results')
                elif variance > 0.05:  # High variance
                    confidence_score -= 0.1
                    confidence_factors.append('Inconsistent results')
            
            # Clamp confidence score
            confidence_score = max(0.0, min(1.0, confidence_score))
            
            # Make recommendation
            if confidence_score >= 0.8 and trend != 'declining':
                recommendation = 'deploy'
            elif confidence_score >= 0.6 and trend == 'improving':
                recommendation = 'deploy'
            elif confidence_score < 0.4 or trend == 'declining':
                recommendation = 'rollback'
            else:
                recommendation = 'hold'
            
            return DeploymentConfidence(
                confidence_score=confidence_score,
                pass_rate_trend=trend,
                recent_pass_rate=recent_pass_rate,
                baseline_pass_rate=baseline_pass_rate,
                recommendation=recommendation,
                factors=confidence_factors
            )
            
        except Exception as e:
            logger.error(f"Error calculating deployment confidence: {str(e)}")
            return DeploymentConfidence(
                confidence_score=0.0,
                pass_rate_trend='unknown',
                recent_pass_rate=0.0,
                baseline_pass_rate=0.0,
                recommendation='hold',
                factors=[f'Error: {str(e)}']
            )
    
    def _get_eval_sets_summary(self, project_id: str) -> List[Dict[str, Any]]:
        """Get summary of evaluation sets for a project."""
        try:
            eval_sets = EvalSet.query.filter(EvalSet.project_id == project_id).all()
            
            summaries = []
            for eval_set in eval_sets:
                # Get latest result
                latest_result = EvalResult.query.filter(
                    EvalResult.eval_set_id == eval_set.id
                ).order_by(desc(EvalResult.run_timestamp)).first()
                
                # Get result count
                result_count = EvalResult.query.filter(
                    EvalResult.eval_set_id == eval_set.id
                ).count()
                
                summaries.append({
                    'id': str(eval_set.id),
                    'name': eval_set.name,
                    'created_at': eval_set.created_at.isoformat() if eval_set.created_at else None,
                    'case_count': eval_set.blueprint.get('case_count', 0),
                    'result_count': result_count,
                    'latest_pass_rate': float(latest_result.pass_rate) if latest_result else None,
                    'latest_run': latest_result.run_timestamp.isoformat() if latest_result and latest_result.run_timestamp else None
                })
            
            return summaries
            
        except Exception as e:
            logger.error(f"Error getting eval sets summary: {str(e)}")
            return []
    
    def _get_recent_results(self, project_id: str, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """Get recent evaluation results."""
        try:
            results = db.session.query(EvalResult).join(EvalSet).filter(
                EvalSet.project_id == project_id,
                EvalResult.run_timestamp >= cutoff_date
            ).order_by(desc(EvalResult.run_timestamp)).limit(20).all()
            
            return [
                {
                    'id': str(result.id),
                    'eval_set_id': str(result.eval_set_id),
                    'run_id': result.run_id,
                    'pass_rate': float(result.pass_rate),
                    'total_cases': result.total_cases,
                    'passed_cases': result.passed_cases,
                    'failed_cases_count': len(result.failed_cases or []),
                    'pack_version': result.pack_version,
                    'run_timestamp': result.run_timestamp.isoformat() if result.run_timestamp else None
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting recent results: {str(e)}")
            return []
    
    def _get_trend_analysis(self, project_id: str, cutoff_date: datetime) -> List[TrendPoint]:
        """Get trend analysis data."""
        return self.get_trend_analysis(project_id, days=(datetime.utcnow() - cutoff_date).days)
    
    def _get_failing_cases_analysis(self, project_id: str, cutoff_date: datetime) -> List[FailingCaseAnalysis]:
        """Get failing cases analysis."""
        return self.get_failing_cases_analysis(project_id, days=(datetime.utcnow() - cutoff_date).days)
    
    def _calculate_deployment_confidence(self, project_id: str, trend_analysis: List[TrendPoint]) -> DeploymentConfidence:
        """Calculate deployment confidence from trend data."""
        return self.calculate_deployment_confidence(project_id)
    
    def _get_summary_statistics(self, project_id: str, cutoff_date: datetime) -> Dict[str, Any]:
        """Get summary statistics for the dashboard."""
        try:
            # Get total eval sets
            total_eval_sets = EvalSet.query.filter(EvalSet.project_id == project_id).count()
            
            # Get total runs in period
            total_runs = db.session.query(EvalResult).join(EvalSet).filter(
                EvalSet.project_id == project_id,
                EvalResult.run_timestamp >= cutoff_date
            ).count()
            
            # Get average pass rate
            avg_pass_rate_result = db.session.query(func.avg(EvalResult.pass_rate)).join(EvalSet).filter(
                EvalSet.project_id == project_id,
                EvalResult.run_timestamp >= cutoff_date
            ).scalar()
            
            avg_pass_rate = float(avg_pass_rate_result) if avg_pass_rate_result else 0.0
            
            # Get total cases evaluated
            total_cases_result = db.session.query(func.sum(EvalResult.total_cases)).join(EvalSet).filter(
                EvalSet.project_id == project_id,
                EvalResult.run_timestamp >= cutoff_date
            ).scalar()
            
            total_cases = int(total_cases_result) if total_cases_result else 0
            
            return {
                'total_eval_sets': total_eval_sets,
                'total_runs': total_runs,
                'average_pass_rate': avg_pass_rate,
                'total_cases_evaluated': total_cases,
                'period_days': (datetime.utcnow() - cutoff_date).days
            }
            
        except Exception as e:
            logger.error(f"Error getting summary statistics: {str(e)}")
            return {
                'total_eval_sets': 0,
                'total_runs': 0,
                'average_pass_rate': 0.0,
                'total_cases_evaluated': 0,
                'period_days': 0
            }