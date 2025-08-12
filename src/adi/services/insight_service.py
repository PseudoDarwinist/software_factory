"""
Insight Service

Handles clustering of findings into insights and insight management.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass

from ..models.finding import Finding, FindingData
from ..models.insight import Insight
from .domain_pack_loader import get_domain_pack
from .event_bus import ADIEventBus, ADIEvents
from .knowledge_service import KnowledgeService

try:
    from ...models.base import db
except ImportError:
    try:
        from src.models.base import db
    except ImportError:
        from models.base import db

logger = logging.getLogger(__name__)


@dataclass
class EvidenceData:
    """Evidence data for an insight."""
    case_ids: List[str]
    sample_count: int
    total_affected: int
    first_seen: datetime
    last_seen: datetime
    sample_details: List[Dict[str, Any]]


class InsightGenerationError(Exception):
    """Raised when insight generation fails."""
    pass


class InsightService:
    """
    Service for clustering findings into insights and managing insight lifecycle.
    """
    
    def __init__(self, event_bus: Optional[ADIEventBus] = None):
        self.event_bus = event_bus
        self.knowledge_service = KnowledgeService()
    
    def cluster_findings_into_insights(
        self, 
        project_id: str, 
        window_minutes: int = 60,
        min_cluster_size: int = 5
    ) -> List[Insight]:
        """
        Cluster recent findings into insights.
        
        Args:
            project_id: Project to cluster findings for
            window_minutes: Time window to look for findings
            min_cluster_size: Minimum findings needed to create insight
            
        Returns:
            List of newly created insights
        """
        try:
            # Get domain pack for configuration
            domain_pack = get_domain_pack(project_id)
            pack_config = domain_pack.pack_config
            
            # Use pack-specific thresholds if available
            if hasattr(pack_config.defaults, 'review') and pack_config.defaults.review:
                review_config = pack_config.defaults.review
                if hasattr(review_config, 'insight_thresholds'):
                    thresholds = review_config.insight_thresholds
                    window_minutes = getattr(thresholds, 'window_minutes', window_minutes)
                    min_cluster_size = getattr(thresholds, 'cluster_min', min_cluster_size)
            
            logger.info(f"Clustering findings for project {project_id} with window={window_minutes}min, min_size={min_cluster_size}")
            
            # Get recent findings within the time window
            cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
            recent_findings = Finding.query.filter(
                Finding.project_id == project_id,
                Finding.created_at >= cutoff_time
            ).all()
            
            if not recent_findings:
                logger.info(f"No recent findings found for project {project_id}")
                return []
            
            # Group findings by signature for clustering
            signature_groups = defaultdict(list)
            for finding in recent_findings:
                signature_groups[finding.signature].append(finding)
            
            # Enhanced clustering: also consider temporal and contextual similarity
            enhanced_clusters = self._enhance_clustering(signature_groups, recent_findings)
            
            # Create insights from clusters that meet minimum size
            new_insights = []
            for signature, findings in enhanced_clusters.items():
                if len(findings) >= min_cluster_size:
                    # Check if insight already exists for this signature
                    existing_insight = Insight.query.filter(
                        Insight.project_id == project_id,
                        Insight.signature == signature,
                        Insight.status.in_(['open', 'converted'])
                    ).first()
                    
                    if existing_insight:
                        # Update existing insight with new evidence
                        self._update_insight_evidence(existing_insight, findings)
                        logger.info(f"Updated existing insight {existing_insight.id} with {len(findings)} findings")
                    else:
                        # Create new insight
                        insight = self._create_insight_from_findings(project_id, signature, findings, domain_pack)
                        new_insights.append(insight)
                        logger.info(f"Created new insight {insight.id} from {len(findings)} findings")
            
            # Commit all changes
            db.session.commit()
            
            # Emit events for new insights
            if self.event_bus:
                for insight in new_insights:
                    self.event_bus.emit(ADIEvents.INSIGHT_GENERATED, {
                        'project_id': project_id,
                        'insight_id': str(insight.id),
                        'kind': insight.kind,
                        'severity': insight.severity,
                        'evidence_count': insight.evidence.get('total_affected', 0),
                        'timestamp': insight.created_at.isoformat()
                    })
            
            # Enhance insights with relevant knowledge
            for insight in new_insights:
                self._enhance_insight_with_knowledge(insight)
            
            logger.info(f"Generated {len(new_insights)} new insights for project {project_id}")
            return new_insights
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Insight clustering failed for project {project_id}: {str(e)}")
            raise InsightGenerationError(f"Failed to cluster findings into insights: {str(e)}") from e
    
    def _enhance_insight_with_knowledge(self, insight: Insight) -> None:
        """
        Enhance an insight with relevant knowledge from the knowledge base.
        
        Args:
            insight: The insight to enhance with knowledge
        """
        try:
            # Create a search query from the insight
            search_query = f"{insight.kind} {insight.title}"
            if insight.description:
                search_query += f" {insight.description}"
            
            # Get relevant knowledge
            knowledge_items = self.knowledge_service.search_knowledge(
                insight.project_id, 
                search_query, 
                limit=3
            )
            
            if knowledge_items:
                # Add knowledge to insight metadata
                knowledge_data = []
                for item in knowledge_items:
                    knowledge_data.append({
                        'id': item.id,
                        'title': item.title,
                        'content': item.content[:200] + '...' if len(item.content) > 200 else item.content,
                        'author': item.author,
                        'similarity_score': item.similarity_score
                    })
                
                # Update insight metadata with knowledge
                if not insight.metadata:
                    insight.metadata = {}
                insight.metadata['related_knowledge'] = knowledge_data
                
                logger.debug(f"Enhanced insight {insight.id} with {len(knowledge_items)} knowledge items")
            
        except Exception as e:
            logger.warning(f"Failed to enhance insight {insight.id} with knowledge: {str(e)}")
            # Don't fail the insight creation if knowledge enhancement fails
    
    def _create_insight_from_findings(
        self, 
        project_id: str, 
        signature: str, 
        findings: List[Finding],
        domain_pack
    ) -> Insight:
        """Create a new insight from a cluster of findings."""
        
        # Analyze findings to extract common patterns
        first_finding = findings[0]
        kind = first_finding.kind
        
        # Determine overall severity using weighted approach
        severity_order = {'low': 1, 'med': 2, 'high': 3}
        severity_counts = Counter(f.severity for f in findings)
        
        # Calculate weighted severity score
        total_findings = len(findings)
        severity_score = sum(severity_order[sev] * count for sev, count in severity_counts.items()) / total_findings
        
        # Determine final severity based on score and thresholds
        if severity_score >= 2.5 or severity_counts.get('high', 0) >= total_findings * 0.5:
            max_severity = 'high'
        elif severity_score >= 1.5 or severity_counts.get('med', 0) >= total_findings * 0.3:
            max_severity = 'med'  
        else:
            max_severity = 'low'
        
        # Override for critical patterns
        if total_findings >= 10 and kind in ['Time.SLA', 'Delivery.Failed', 'Policy.Misapplied']:
            max_severity = 'high'
        
        # Generate title and summary
        title = self._generate_insight_title(kind, findings)
        summary = self._generate_insight_summary(kind, findings, domain_pack)
        
        # Build evidence data
        evidence = self._build_evidence_data(findings)
        
        # Calculate metrics
        metrics = self._calculate_insight_metrics(findings, domain_pack)
        
        # Create insight
        insight = Insight(
            project_id=project_id,
            kind=kind,
            title=title,
            summary=summary,
            severity=max_severity,
            evidence=evidence,
            metrics=metrics,
            signature=signature,
            status='open'
        )
        
        db.session.add(insight)
        return insight
    
    def _enhance_clustering(
        self, 
        signature_groups: Dict[str, List[Finding]], 
        all_findings: List[Finding]
    ) -> Dict[str, List[Finding]]:
        """
        Enhance clustering by considering temporal and contextual similarity.
        
        Args:
            signature_groups: Initial signature-based groups
            all_findings: All findings to consider
            
        Returns:
            Enhanced clustering groups
        """
        enhanced_clusters = {}
        
        for signature, findings in signature_groups.items():
            # Start with the signature-based cluster
            enhanced_clusters[signature] = findings
            
            # Look for similar findings in other clusters that might belong here
            for other_signature, other_findings in signature_groups.items():
                if other_signature == signature:
                    continue
                
                # Check if clusters should be merged based on similarity
                if self._should_merge_clusters(findings, other_findings):
                    # Merge the clusters
                    enhanced_clusters[signature].extend(other_findings)
                    # Mark the other cluster for removal
                    if other_signature in enhanced_clusters:
                        del enhanced_clusters[other_signature]
        
        return enhanced_clusters
    
    def _should_merge_clusters(self, cluster1: List[Finding], cluster2: List[Finding]) -> bool:
        """
        Determine if two clusters should be merged based on similarity.
        
        Args:
            cluster1: First cluster of findings
            cluster2: Second cluster of findings
            
        Returns:
            True if clusters should be merged
        """
        if not cluster1 or not cluster2:
            return False
        
        # Get representative findings from each cluster
        rep1 = cluster1[0]
        rep2 = cluster2[0]
        
        # Don't merge different kinds
        if rep1.kind != rep2.kind:
            return False
        
        # Check temporal proximity (within 30 minutes)
        time_diff = abs((rep1.created_at - rep2.created_at).total_seconds())
        if time_diff > 1800:  # 30 minutes
            return False
        
        # Check contextual similarity
        details1 = rep1.details or {}
        details2 = rep2.details or {}
        
        # For SLA violations, check if same event type
        if rep1.kind == "Time.SLA":
            return details1.get('event_type') == details2.get('event_type')
        
        # For template issues, check if same event type and channel
        if rep1.kind == "Template.Select":
            return (details1.get('event_type') == details2.get('event_type') and
                   details1.get('channel') == details2.get('channel'))
        
        # For delivery issues, check if same channel
        if rep1.kind.startswith("Delivery."):
            return details1.get('channel') == details2.get('channel')
        
        # Default: don't merge unless very similar
        return False
    
    def _update_insight_evidence(self, insight: Insight, new_findings: List[Finding]) -> None:
        """Update an existing insight with new evidence."""
        
        # Get existing evidence
        existing_evidence = insight.evidence or {}
        existing_case_ids = set(existing_evidence.get('case_ids', []))
        
        # Add new case IDs
        new_case_ids = [f.case_id for f in new_findings]
        all_case_ids = list(existing_case_ids.union(set(new_case_ids)))
        
        # Update evidence
        evidence = self._build_evidence_data(new_findings)
        evidence['case_ids'] = all_case_ids
        evidence['total_affected'] = len(all_case_ids)
        
        # Keep first_seen from existing evidence if available
        if 'first_seen' in existing_evidence:
            existing_first_seen = datetime.fromisoformat(existing_evidence['first_seen'])
            new_first_seen = datetime.fromisoformat(evidence['first_seen'])
            evidence['first_seen'] = min(existing_first_seen, new_first_seen).isoformat()
        
        insight.evidence = evidence
        insight.updated_at = datetime.utcnow()
        
        # Update severity if new findings are more severe
        severity_order = {'low': 1, 'med': 2, 'high': 3}
        max_new_severity = max(new_findings, key=lambda f: severity_order.get(f.severity, 0)).severity
        if severity_order.get(max_new_severity, 0) > severity_order.get(insight.severity, 0):
            insight.severity = max_new_severity
    
    def _generate_insight_title(self, kind: str, findings: List[Finding]) -> str:
        """Generate a descriptive title for the insight."""
        
        count = len(findings)
        
        if kind == "Time.SLA":
            return f"SLA violations detected in {count} cases"
        elif kind == "Template.Select":
            return f"Template selection issues in {count} cases"
        elif kind == "Policy.Misapplied":
            return f"Policy compliance issues in {count} cases"
        elif kind == "Delivery.Failed":
            return f"Delivery failures in {count} cases"
        elif kind == "Delivery.Skipped":
            return f"Skipped deliveries in {count} cases"
        else:
            return f"{kind} issues detected in {count} cases"
    
    def _generate_insight_summary(self, kind: str, findings: List[Finding], domain_pack) -> str:
        """Generate a detailed summary for the insight."""
        
        count = len(findings)
        
        # Analyze common patterns in findings
        event_types = Counter(f.details.get('event_type') for f in findings if f.details.get('event_type'))
        templates = Counter(f.details.get('actual_template') for f in findings if f.details.get('actual_template'))
        
        summary_parts = []
        
        if kind == "Time.SLA":
            avg_overage = sum(f.details.get('overage_ms', 0) for f in findings) / count
            summary_parts.append(f"Average SLA overage: {avg_overage:.0f}ms")
            
            if event_types:
                top_event = event_types.most_common(1)[0]
                summary_parts.append(f"Most affected event type: {top_event[0]} ({top_event[1]} cases)")
        
        elif kind == "Template.Select":
            if templates:
                top_template = templates.most_common(1)[0]
                summary_parts.append(f"Most common incorrect template: {top_template[0]} ({top_template[1]} cases)")
            
            if event_types:
                top_event = event_types.most_common(1)[0]
                summary_parts.append(f"Most affected event type: {top_event[0]} ({top_event[1]} cases)")
        
        elif kind == "Policy.Misapplied":
            rule_ids = Counter(f.details.get('rule_id') for f in findings if f.details.get('rule_id'))
            if rule_ids:
                top_rule = rule_ids.most_common(1)[0]
                summary_parts.append(f"Most violated rule: {top_rule[0]} ({top_rule[1]} cases)")
        
        # Add suggested fix from domain knowledge
        suggested_fix = self._generate_suggested_fix(kind, findings, domain_pack)
        if suggested_fix:
            summary_parts.append(f"Suggested action: {suggested_fix}")
        
        return " | ".join(summary_parts) if summary_parts else f"Multiple {kind} issues detected across {count} cases"
    
    def _build_evidence_data(self, findings: List[Finding]) -> Dict[str, Any]:
        """Build evidence data structure from findings."""
        
        case_ids = [f.case_id for f in findings]
        timestamps = [f.created_at for f in findings]
        
        # Sample details (limit to avoid huge payloads)
        sample_details = []
        for finding in findings[:10]:  # Limit to 10 samples
            sample_details.append({
                'case_id': finding.case_id,
                'details': finding.details,
                'timestamp': finding.created_at.isoformat()
            })
        
        return {
            'case_ids': case_ids,
            'sample_count': len(sample_details),
            'total_affected': len(case_ids),
            'first_seen': min(timestamps).isoformat(),
            'last_seen': max(timestamps).isoformat(),
            'sample_details': sample_details
        }
    
    def _calculate_insight_metrics(self, findings: List[Finding], domain_pack) -> Dict[str, Any]:
        """Calculate metrics for the insight."""
        
        metrics = {
            'finding_count': len(findings),
            'unique_cases': len(set(f.case_id for f in findings)),
            'severity_distribution': Counter(f.severity for f in findings),
            'validator_distribution': Counter(f.validator_name for f in findings)
        }
        
        # Add kind-specific metrics
        kind = findings[0].kind
        
        if kind == "Time.SLA":
            overages = [f.details.get('overage_ms', 0) for f in findings if f.details.get('overage_ms')]
            if overages:
                metrics.update({
                    'avg_overage_ms': sum(overages) / len(overages),
                    'max_overage_ms': max(overages),
                    'min_overage_ms': min(overages)
                })
        
        elif kind == "Template.Select":
            event_types = [f.details.get('event_type') for f in findings if f.details.get('event_type')]
            metrics['affected_event_types'] = len(set(event_types))
        
        return metrics
    
    def _generate_suggested_fix(self, kind: str, findings: List[Finding], domain_pack) -> Optional[str]:
        """Generate a suggested fix based on domain knowledge and patterns."""
        
        # Try to get suggested fix from domain knowledge
        knowledge = domain_pack.knowledge
        
        # Look for relevant knowledge based on kind
        if kind in knowledge:
            # Extract relevant section (simplified - could be more sophisticated)
            lines = knowledge.split('\n')
            for i, line in enumerate(lines):
                if kind.lower() in line.lower():
                    # Return next few lines as suggested fix
                    fix_lines = lines[i+1:i+4]
                    return ' '.join(line.strip() for line in fix_lines if line.strip())
        
        # Enhanced pattern-based suggestions with context
        if kind == "Time.SLA":
            # Analyze SLA violations for more specific suggestions
            avg_overage = sum(f.details.get('overage_ms', 0) for f in findings) / len(findings)
            if avg_overage > 600000:  # > 10 minutes
                return "Critical SLA violations detected. Immediate infrastructure scaling and process optimization required"
            elif avg_overage > 300000:  # > 5 minutes
                return "Significant SLA violations. Review processing pipeline for performance bottlenecks"
            else:
                return "Minor SLA violations. Consider optimizing specific event processing workflows"
                
        elif kind == "Template.Select":
            # Analyze template issues
            event_types = set(f.details.get('event_type') for f in findings if f.details.get('event_type'))
            if len(event_types) == 1:
                event_type = list(event_types)[0]
                return f"Template mapping issue specific to {event_type} events. Update template selection rules"
            else:
                return "Widespread template selection issues. Review and update template mapping configuration"
                
        elif kind == "Policy.Misapplied":
            # Analyze policy violations
            rule_ids = set(f.details.get('rule_id') for f in findings if f.details.get('rule_id'))
            if len(rule_ids) == 1:
                rule_id = list(rule_ids)[0]
                return f"Specific policy rule violation: {rule_id}. Review rule implementation and validation"
            else:
                return "Multiple policy violations detected. Comprehensive review of business rules needed"
                
        elif kind.startswith("Delivery."):
            # Analyze delivery issues
            channels = set(f.details.get('channel') for f in findings if f.details.get('channel'))
            if len(channels) == 1:
                channel = list(channels)[0]
                return f"Delivery issues specific to {channel} channel. Investigate {channel} infrastructure"
            else:
                return "Multi-channel delivery issues. Review overall delivery infrastructure and retry mechanisms"
                
        elif kind.startswith("Audience."):
            return "Audience targeting issues detected. Review eligibility criteria and consent management"
            
        elif kind.startswith("BusinessHours."):
            return "Business hours violations detected. Review scheduling logic and urgency classification"
            
        elif kind.startswith("RateLimit."):
            return "Rate limiting concerns detected. Review send frequency and implement throttling"
            
        elif kind.startswith("Content."):
            return "Content quality issues detected. Review personalization and localization processes"
        
        return f"Review and investigate {kind} issues across affected cases"
    
    def get_insights_for_review(
        self, 
        project_id: str, 
        status: str = 'open',
        limit: int = 50
    ) -> List[Insight]:
        """Get insights ready for domain expert review."""
        
        query = Insight.query.filter(
            Insight.project_id == project_id,
            Insight.status == status
        ).order_by(
            Insight.severity.desc(),  # High severity first
            Insight.created_at.desc()  # Most recent first
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def update_insight_status(
        self, 
        insight_id: str, 
        status: str, 
        notes: Optional[str] = None
    ) -> Insight:
        """Update insight status (e.g., when converted to work item)."""
        
        insight = Insight.query.get(insight_id)
        if not insight:
            raise InsightGenerationError(f"Insight not found: {insight_id}")
        
        insight.status = status
        insight.updated_at = datetime.utcnow()
        
        if notes:
            # Add notes to evidence
            if 'notes' not in insight.evidence:
                insight.evidence['notes'] = []
            insight.evidence['notes'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'note': notes
            })
        
        db.session.commit()
        
        # Emit status change event
        if self.event_bus:
            self.event_bus.emit(ADIEvents.INSIGHT_STATUS_CHANGED, {
                'insight_id': insight_id,
                'old_status': 'open',  # Could track this better
                'new_status': status,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return insight


# Global insight service instance
_insight_service: Optional[InsightService] = None


def get_insight_service(event_bus: Optional[ADIEventBus] = None) -> InsightService:
    """Get the global insight service instance."""
    global _insight_service
    
    if _insight_service is None:
        _insight_service = InsightService(event_bus)
    
    return _insight_service