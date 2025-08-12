"""
Scoring Pipeline

Core infrastructure for analyzing decision logs using domain pack configuration
to generate findings and insights.
"""

import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from ..models.finding import FindingData
from ..models.insight import Insight
from ..schemas.decision_log import DecisionLog
from .domain_pack_loader import DomainPack, get_domain_pack
from .event_bus import ADIEventBus, ADIEvents
from .scoring_context import ScoringContext
from .custom_validator_framework import get_custom_validator_framework
from .knowledge_service import KnowledgeService
from .knowledge_analytics import knowledge_analytics

logger = logging.getLogger(__name__)





class ScoringPipelineError(Exception):
    """Raised when scoring pipeline encounters an error."""
    pass


class ScoringPipeline:
    """
    Core scoring pipeline that analyzes decision logs using domain pack configuration.
    
    The pipeline loads the appropriate domain pack and runs both builtin and custom
    validators to generate findings, which are then clustered into insights.
    """
    
    def __init__(self, event_bus: Optional[ADIEventBus] = None):
        self.event_bus = event_bus
        self.knowledge_service = KnowledgeService()
        self.builtin_validators = [
            self._sla_validator,
            self._template_validator,
            self._policy_validator,
            self._delivery_validator,
            self._audience_validator
        ]
        self.custom_validator_framework = get_custom_validator_framework()
    
    def score_decision(self, decision_log: DecisionLog) -> List[FindingData]:
        """
        Score a single decision log and return findings.
        
        Args:
            decision_log: The decision log to analyze
            
        Returns:
            List of findings from validation
            
        Raises:
            ScoringPipelineError: If scoring fails
        """
        try:
            # Load domain pack for the project
            domain_pack = get_domain_pack(decision_log.project_id)
            
            # Retrieve relevant knowledge for this decision
            relevant_knowledge = self._get_relevant_knowledge(decision_log)
            
            # Create scoring context with knowledge
            context = ScoringContext(
                project_id=decision_log.project_id,
                case_id=decision_log.case_id,
                decision_log=decision_log,
                domain_pack=domain_pack,
                timestamp=datetime.utcnow(),
                relevant_knowledge=relevant_knowledge
            )
            
            logger.info(f"Scoring decision {decision_log.case_id} for project {decision_log.project_id}")
            
            # Run all validators
            findings = []
            
            # Run builtin validators
            builtin_findings = self._run_builtin_validators(context)
            findings.extend(builtin_findings)
            
            # Run custom validators
            custom_findings = self._run_custom_validators(context)
            findings.extend(custom_findings)
            
            logger.info(f"Generated {len(findings)} findings for case {decision_log.case_id}")
            
            # Emit scoring completed event
            if self.event_bus:
                self.event_bus.emit(ADIEvents.DECISION_SCORED, {
                    'project_id': decision_log.project_id,
                    'case_id': decision_log.case_id,
                    'findings_count': len(findings),
                    'timestamp': context.timestamp.isoformat()
                })
            
            return findings
            
        except Exception as e:
            logger.error(f"Scoring failed for case {decision_log.case_id}: {str(e)}")
            raise ScoringPipelineError(f"Failed to score decision log: {str(e)}") from e
    
    def _get_relevant_knowledge(self, decision_log: DecisionLog) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge for the decision log case.
        
        Args:
            decision_log: The decision log to get knowledge for
            
        Returns:
            List of relevant knowledge items
        """
        try:
            # Convert decision log to case data format
            case_data = {
                'event': {
                    'type': decision_log.event.type,
                    'attrs': decision_log.event.attrs or {}
                },
                'decision': {
                    'action': decision_log.decision.action,
                    'template_id': decision_log.decision.template_id,
                    'status': decision_log.decision.status
                }
            }
            
            # Get relevant knowledge from knowledge service
            knowledge_items = self.knowledge_service.get_relevant_context(
                decision_log.project_id, 
                case_data
            )
            
            # Convert to dictionary format for context
            knowledge_data = []
            for item in knowledge_items:
                knowledge_data.append({
                    'id': item.id,
                    'title': item.title,
                    'content': item.content,
                    'author': item.author,
                    'tags': item.tags,
                    'similarity_score': item.similarity_score,
                    'created_at': item.created_at.isoformat() if item.created_at else None
                })
            
            # Log knowledge usage for analytics
            knowledge_analytics.log_knowledge_retrieval(
                decision_log.project_id,
                decision_log.case_id,
                knowledge_data,
                {
                    'event_type': decision_log.event.type,
                    'decision_action': decision_log.decision.action,
                    'template_id': decision_log.decision.template_id
                }
            )
            
            logger.info(f"Retrieved {len(knowledge_data)} relevant knowledge items for case {decision_log.case_id}")
            return knowledge_data
            
        except Exception as e:
            logger.warning(f"Failed to retrieve relevant knowledge for case {decision_log.case_id}: {str(e)}")
            return []
    
    def _run_builtin_validators(self, context: ScoringContext) -> List[FindingData]:
        """Run all builtin validators against the decision log."""
        findings = []
        
        for validator in self.builtin_validators:
            try:
                validator_findings = validator(context)
                if validator_findings:
                    findings.extend(validator_findings)
            except Exception as e:
                logger.warning(f"Builtin validator {validator.__name__} failed: {str(e)}")
                # Continue with other validators
        
        return findings
    
    def _run_custom_validators(self, context: ScoringContext) -> List[FindingData]:
        """Run custom validators from the domain pack using the safe execution framework."""
        findings = []
        
        # Load and register custom validators from domain pack
        self._load_domain_pack_validators(context.domain_pack)
        
        # Execute all registered custom validators
        validator_results = self.custom_validator_framework.execute_all_validators(context)
        
        for result in validator_results:
            if result.success:
                findings.extend(result.findings)
                logger.debug(f"Custom validator {result.validator_name} generated {len(result.findings)} findings")
            else:
                logger.warning(f"Custom validator {result.validator_name} failed: {result.error}")
                
                # Optionally create a finding about the validator failure
                if not result.timeout:  # Don't create findings for timeouts
                    findings.append(FindingData(
                        kind="Validator.Error",
                        severity="low",
                        details={
                            'validator_name': result.validator_name,
                            'error': result.error,
                            'execution_time_ms': result.execution_time_ms
                        },
                        suggested_fix=f"Fix custom validator {result.validator_name}: {result.error}",
                        validator_name="builtin:validator_monitor"
                    ))
        
        return findings
    
    def _load_domain_pack_validators(self, domain_pack: DomainPack) -> None:
        """Load and register custom validators from domain pack."""
        custom_validators = domain_pack.get_all_validators()
        
        for validator_name, validator_func in custom_validators.items():
            # Register validator with framework if not already registered
            if validator_name not in self.custom_validator_framework.validator_registry:
                self.custom_validator_framework.register_validator(
                    name=validator_name,
                    validator_func=validator_func,
                    description=f"Custom validator from domain pack {domain_pack.pack_id}",
                    version=domain_pack.pack_config.pack.version
                )
    
    def _sla_validator(self, context: ScoringContext) -> List[FindingData]:
        """
        Builtin SLA validator - checks if decision was made within SLA timeframe.
        """
        findings = []
        decision_log = context.decision_log
        domain_pack = context.domain_pack
        
        # Get SLA for this event type
        event_attrs = decision_log.event.attrs or {}
        sla_ms = domain_pack.get_sla_for_event(
            decision_log.event.type,
            channel=event_attrs.get('channel'),
            market=event_attrs.get('market'),
            airport=event_attrs.get('airport'),
            delay_minutes=event_attrs.get('delay_minutes')
        )
        
        # Check if decision latency exceeds SLA
        actual_latency = decision_log.decision.latency_ms
        if actual_latency > sla_ms:
            findings.append(FindingData(
                kind="Time.SLA",
                severity="high" if actual_latency > sla_ms * 2 else "med",
                details={
                    'expected_sla_ms': sla_ms,
                    'actual_latency_ms': actual_latency,
                    'overage_ms': actual_latency - sla_ms,
                    'overage_percent': ((actual_latency - sla_ms) / sla_ms) * 100,
                    'event_type': decision_log.event.type
                },
                suggested_fix=f"Optimize processing for {decision_log.event.type} events to meet {sla_ms}ms SLA",
                validator_name="builtin:sla"
            ))
        
        return findings
    
    def _template_validator(self, context: ScoringContext) -> List[FindingData]:
        """
        Builtin template validator - checks if correct template was selected.
        """
        findings = []
        decision_log = context.decision_log
        domain_pack = context.domain_pack
        
        # Get template mappings
        mappings = domain_pack.get_mappings()
        template_mappings = mappings.get('templates', {})
        
        if not template_mappings:
            return findings
        
        # Get event templates configuration
        event_templates = template_mappings.get('event_templates', {})
        
        # Map decision action to template category
        action = decision_log.decision.action
        template_category = self._map_action_to_template_category(action)
        
        if template_category and template_category in event_templates:
            template_config = event_templates[template_category]
            expected_template = self._get_expected_template(
                template_config, 
                decision_log.decision.channel,
                decision_log.event.attrs or {}
            )
            
            actual_template = decision_log.decision.template_id
            
            if expected_template and actual_template != expected_template:
                findings.append(FindingData(
                    kind="Template.Select",
                    severity="med",
                    details={
                        'action': action,
                        'template_category': template_category,
                        'channel': decision_log.decision.channel,
                        'expected_template': expected_template,
                        'actual_template': actual_template,
                        'template_mapping_source': 'domain_pack'
                    },
                    suggested_fix=f"Use template {expected_template} for {action} via {decision_log.decision.channel}",
                    validator_name="builtin:template"
                ))
        
        return findings
    
    def _map_action_to_template_category(self, action: str) -> Optional[str]:
        """Map decision action to template category."""
        action_lower = action.lower()
        
        if 'notification' in action_lower or 'notify' in action_lower:
            return 'Notification'
        elif 'alert' in action_lower:
            return 'Alert'
        elif 'update' in action_lower:
            return 'Update'
        elif 'remind' in action_lower:
            return 'Reminder'
        
        return None
    
    def _get_expected_template(self, template_config: Dict[str, Any], channel: str, event_attrs: Dict[str, Any]) -> Optional[str]:
        """Get expected template based on channel and context."""
        
        # Check channel-specific templates first
        if 'by_channel' in template_config and channel in template_config['by_channel']:
            return template_config['by_channel'][channel]
        
        # Check priority-based templates
        if 'by_priority' in template_config and 'priority' in event_attrs:
            priority = event_attrs['priority']
            if priority in template_config['by_priority']:
                return template_config['by_priority'][priority]
        
        # Check urgency-based templates
        if 'by_urgency' in template_config and 'urgency' in event_attrs:
            urgency = event_attrs['urgency']
            if urgency in template_config['by_urgency']:
                return template_config['by_urgency'][urgency]
        
        # Check frequency-based templates
        if 'by_frequency' in template_config and 'frequency' in event_attrs:
            frequency = event_attrs['frequency']
            if frequency in template_config['by_frequency']:
                return template_config['by_frequency'][frequency]
        
        # Fall back to default template
        return template_config.get('default')
    
    def _policy_validator(self, context: ScoringContext) -> List[FindingData]:
        """
        Builtin policy validator - checks business rules compliance.
        """
        findings = []
        decision_log = context.decision_log
        domain_pack = context.domain_pack
        
        # Get all rules (since most are universal with "*" event type)
        rules = domain_pack.rules.get('rules', [])
        
        for rule in rules:
            try:
                # Check if rule applies to this specific case
                if self._rule_applies(rule, decision_log):
                    # Validate expectations
                    violations = self._check_rule_expectations(rule, decision_log)
                    
                    if violations:
                        # Determine severity based on rule type
                        severity = self._get_rule_severity(rule.get('id', ''))
                        
                        findings.append(FindingData(
                            kind="Policy.Misapplied",
                            severity=severity,
                            details={
                                'rule_id': rule.get('id', 'unknown'),
                                'rule_description': rule.get('description', ''),
                                'violations': violations,
                                'event_type': decision_log.event.type
                            },
                            suggested_fix=f"Review rule compliance: {rule.get('description', 'Unknown rule')}",
                            validator_name="builtin:policy"
                        ))
                        
            except Exception as e:
                logger.warning(f"Policy rule validation failed for rule {rule.get('id', 'unknown')}: {str(e)}")
        
        return findings
    
    def _get_rule_severity(self, rule_id: str) -> str:
        """Determine severity based on rule type."""
        rule_id_lower = rule_id.lower()
        
        if any(keyword in rule_id_lower for keyword in ['consent', 'blocklist', 'eligibility']):
            return 'high'
        elif any(keyword in rule_id_lower for keyword in ['sla', 'duplicate', 'error']):
            return 'high'
        elif any(keyword in rule_id_lower for keyword in ['template', 'personalization', 'locale']):
            return 'med'
        else:
            return 'med'
    
    def _delivery_validator(self, context: ScoringContext) -> List[FindingData]:
        """
        Builtin delivery validator - checks if decision was successfully delivered.
        """
        findings = []
        decision_log = context.decision_log
        
        # Check decision status
        status = decision_log.decision.status
        
        if status == "FAILED":
            findings.append(FindingData(
                kind="Delivery.Failed",
                severity="high",
                details={
                    'status': status,
                    'channel': decision_log.decision.channel,
                    'template_id': decision_log.decision.template_id,
                    'event_type': decision_log.event.type,
                    'action': decision_log.decision.action
                },
                suggested_fix="Investigate delivery failure and retry mechanism",
                validator_name="builtin:delivery"
            ))
        elif status == "SKIPPED":
            findings.append(FindingData(
                kind="Delivery.Skipped",
                severity="med",
                details={
                    'status': status,
                    'channel': decision_log.decision.channel,
                    'template_id': decision_log.decision.template_id,
                    'event_type': decision_log.event.type,
                    'action': decision_log.decision.action
                },
                suggested_fix="Review why decision was skipped - may indicate missing business logic",
                validator_name="builtin:delivery"
            ))
        elif status == "RETRY":
            findings.append(FindingData(
                kind="Delivery.Retry",
                severity="med",
                details={
                    'status': status,
                    'channel': decision_log.decision.channel,
                    'template_id': decision_log.decision.template_id,
                    'event_type': decision_log.event.type,
                    'action': decision_log.decision.action
                },
                suggested_fix="Monitor retry patterns and investigate underlying delivery issues",
                validator_name="builtin:delivery"
            ))
        
        # Check for audience validation issues
        if hasattr(decision_log.decision, 'audience_validated') and not decision_log.decision.audience_validated:
            findings.append(FindingData(
                kind="Audience.Invalid",
                severity="high",
                details={
                    'channel': decision_log.decision.channel,
                    'template_id': decision_log.decision.template_id,
                    'event_type': decision_log.event.type,
                    'validation_failed': True
                },
                suggested_fix="Review audience validation logic and eligibility criteria",
                validator_name="builtin:delivery"
            ))
        
        return findings
    
    def _audience_validator(self, context: ScoringContext) -> List[FindingData]:
        """
        Builtin audience validator - checks audience targeting and eligibility.
        """
        findings = []
        decision_log = context.decision_log
        event_attrs = decision_log.event.attrs or {}
        
        # Check for missing recipient information
        if not event_attrs.get('recipient_id') and not event_attrs.get('user_id'):
            findings.append(FindingData(
                kind="Audience.Missing",
                severity="high",
                details={
                    'event_type': decision_log.event.type,
                    'missing_fields': ['recipient_id', 'user_id'],
                    'available_attrs': list(event_attrs.keys())
                },
                suggested_fix="Ensure recipient identification is included in event data",
                validator_name="builtin:audience"
            ))
        
        # Check for consent-related issues
        if event_attrs.get('consent_status') == 'invalid':
            findings.append(FindingData(
                kind="Audience.Consent",
                severity="high",
                details={
                    'event_type': decision_log.event.type,
                    'consent_status': event_attrs.get('consent_status'),
                    'consent_reason': event_attrs.get('consent_reason', 'unknown')
                },
                suggested_fix="Verify consent status before sending communications",
                validator_name="builtin:audience"
            ))
        
        # Check for blocklist issues
        if event_attrs.get('blocklist_status') == 'blocked':
            findings.append(FindingData(
                kind="Audience.Blocked",
                severity="high",
                details={
                    'event_type': decision_log.event.type,
                    'blocklist_status': event_attrs.get('blocklist_status'),
                    'block_reason': event_attrs.get('block_reason', 'unknown')
                },
                suggested_fix="Respect blocklist status and do not send to blocked recipients",
                validator_name="builtin:audience"
            ))
        
        # Check for eligibility issues
        if event_attrs.get('eligibility_status') == 'ineligible':
            findings.append(FindingData(
                kind="Audience.Ineligible",
                severity="med",
                details={
                    'event_type': decision_log.event.type,
                    'eligibility_status': event_attrs.get('eligibility_status'),
                    'eligibility_reason': event_attrs.get('eligibility_reason', 'unknown')
                },
                suggested_fix="Review eligibility criteria and targeting logic",
                validator_name="builtin:audience"
            ))
        
        return findings
    
    def _rule_applies(self, rule: Dict[str, Any], decision_log: DecisionLog) -> bool:
        """Check if a business rule applies to the given decision log."""
        applies_when = rule.get('applies_when', {})
        
        for condition_key, condition_value in applies_when.items():
            if not self._evaluate_condition(condition_key, condition_value, decision_log):
                return False
        
        return True
    
    def _evaluate_condition(self, condition_key: str, condition_value: Any, decision_log: DecisionLog) -> bool:
        """Evaluate a single rule condition."""
        try:
            # Handle dot notation for nested attributes
            if condition_key.startswith('event.'):
                attr_path = condition_key[6:]  # Remove 'event.' prefix
                actual_value = self._get_nested_value(decision_log.event, attr_path)
            elif condition_key.startswith('decision.'):
                attr_path = condition_key[9:]  # Remove 'decision.' prefix
                actual_value = self._get_nested_value(decision_log.decision, attr_path)
            else:
                # Direct attribute access
                actual_value = getattr(decision_log, condition_key, None)
            
            # Handle comparison operators in condition_value
            if isinstance(condition_value, str):
                if condition_value.startswith('>='):
                    return actual_value >= float(condition_value[2:].strip())
                elif condition_value.startswith('<='):
                    return actual_value <= float(condition_value[2:].strip())
                elif condition_value.startswith('>'):
                    return actual_value > float(condition_value[1:].strip())
                elif condition_value.startswith('<'):
                    return actual_value < float(condition_value[1:].strip())
            
            # Direct equality check
            return actual_value == condition_value
            
        except Exception as e:
            logger.warning(f"Condition evaluation failed for {condition_key}: {str(e)}")
            return False
    
    def _get_nested_value(self, obj: Any, attr_path: str) -> Any:
        """Get nested attribute value using dot notation."""
        parts = attr_path.split('.')
        current = obj
        
        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def _check_rule_expectations(self, rule: Dict[str, Any], decision_log: DecisionLog) -> List[str]:
        """Check if decision log meets rule expectations."""
        violations = []
        expect = rule.get('expect', {})
        
        for expectation_key, expectation_value in expect.items():
            if not self._check_expectation(expectation_key, expectation_value, decision_log):
                violations.append(f"{expectation_key}: expected {expectation_value}")
        
        return violations
    
    def _check_expectation(self, expectation_key: str, expectation_value: Any, decision_log: DecisionLog) -> bool:
        """Check a single rule expectation."""
        try:
            if expectation_key == 'actions_include':
                # Check if decision includes required actions
                decision_actions = decision_log.decision.action
                if isinstance(expectation_value, list):
                    return any(action in decision_actions for action in expectation_value)
                else:
                    return expectation_value in decision_actions
            
            elif expectation_key == 'template_id_in':
                # Check if template ID is in allowed list
                actual_template = decision_log.decision.template_id
                return actual_template in expectation_value
            
            elif expectation_key == 'not_template_id':
                # Check if template ID is NOT the forbidden one
                actual_template = decision_log.decision.template_id
                return actual_template != expectation_value
            
            else:
                # Generic attribute check
                actual_value = self._get_nested_value(decision_log, expectation_key)
                return actual_value == expectation_value
                
        except Exception as e:
            logger.warning(f"Expectation check failed for {expectation_key}: {str(e)}")
            return False
    
    def generate_signature(self, finding: FindingData, project_id: str) -> str:
        """
        Generate a signature for clustering similar findings.
        
        Args:
            finding: The finding to generate signature for
            project_id: Project identifier
            
        Returns:
            Signature string for clustering
        """
        # Create signature from kind, severity, and key details
        signature_parts = [
            project_id,
            finding.kind,
            finding.severity
        ]
        
        # Add relevant details for clustering
        if 'event_type' in finding.details:
            signature_parts.append(finding.details['event_type'])
        
        if 'template_id' in finding.details:
            signature_parts.append(finding.details['template_id'])
        
        if 'rule_id' in finding.details:
            signature_parts.append(finding.details['rule_id'])
        
        # Create hash of signature parts
        signature_string = '|'.join(str(part) for part in signature_parts)
        return hashlib.md5(signature_string.encode()).hexdigest()[:16]


# Global scoring pipeline instance
_scoring_pipeline: Optional[ScoringPipeline] = None


def get_scoring_pipeline(event_bus: Optional[ADIEventBus] = None) -> ScoringPipeline:
    """Get the global scoring pipeline instance."""
    global _scoring_pipeline
    
    if _scoring_pipeline is None:
        _scoring_pipeline = ScoringPipeline(event_bus)
    
    return _scoring_pipeline