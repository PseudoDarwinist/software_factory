"""
Evaluation Runner

Service for executing evaluation sets with builtin and custom checks.
"""

import logging
import uuid
import asyncio
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from adi.models.evaluation import EvalSet, EvalResult
from adi.models.decision_log import DecisionLog
from adi.models.insight import Insight
from src.models.base import db
from adi.services.domain_pack_loader import DomainPack
from adi.services.scoring_pipeline import ScoringPipeline
from adi.services.custom_validator_framework import CustomValidatorFramework

logger = logging.getLogger(__name__)


@dataclass
class EvalCaseResult:
    """Result for a single evaluation case."""
    case_id: str
    passed: bool
    checks: Dict[str, bool]  # check_name -> passed
    errors: List[str]
    execution_time_ms: int
    details: Dict[str, Any]


@dataclass
class EvalExecutionResult:
    """Result of evaluation execution."""
    run_id: str
    eval_set_id: str
    pass_rate: float
    total_cases: int
    passed_cases: int
    failed_cases: List[str]
    case_results: List[EvalCaseResult]
    execution_time_ms: int
    pack_version: str
    errors: List[str]


class EvalRunner:
    """Service for executing evaluation sets with parallel processing."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.custom_validator = CustomValidatorFramework()
        
        # Builtin check functions
        self.builtin_checks = {
            'sla': self._check_sla,
            'template': self._check_template,
            'policy': self._check_policy,
            'delivery': self._check_delivery,
            'content': self._check_content
        }
    
    def run_eval_set(self, eval_set_id: str) -> EvalExecutionResult:
        """
        Execute an evaluation set with parallel processing.
        
        Args:
            eval_set_id: Evaluation set ID
            
        Returns:
            EvalExecutionResult with detailed results
        """
        start_time = datetime.utcnow()
        run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        try:
            # Load evaluation set
            eval_set = EvalSet.query.get(eval_set_id)
            if not eval_set:
                raise ValueError(f"Evaluation set {eval_set_id} not found")
            
            # Load domain pack
            domain_pack = DomainPack(eval_set.project_id)
            pack_version = domain_pack.pack_config.pack.version
            
            # Get selected cases
            selected_cases = eval_set.blueprint.get('selected_cases', [])
            if not selected_cases:
                raise ValueError("No cases selected for evaluation")
            
            # Load decision logs for selected cases
            decision_logs = self._load_decision_logs(eval_set.project_id, selected_cases)
            
            # Execute evaluation with parallel processing
            case_results = self._execute_parallel_evaluation(
                eval_set, decision_logs, domain_pack
            )
            
            # Calculate results
            total_cases = len(case_results)
            passed_cases = sum(1 for result in case_results if result.passed)
            failed_cases = [result.case_id for result in case_results if not result.passed]
            pass_rate = passed_cases / total_cases if total_cases > 0 else 0.0
            
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Create execution result
            execution_result = EvalExecutionResult(
                run_id=run_id,
                eval_set_id=eval_set_id,
                pass_rate=pass_rate,
                total_cases=total_cases,
                passed_cases=passed_cases,
                failed_cases=failed_cases,
                case_results=case_results,
                execution_time_ms=execution_time,
                pack_version=pack_version,
                errors=[]
            )
            
            # Store result in database
            self._store_eval_result(execution_result)
            
            logger.info(f"Completed evaluation {run_id}: {pass_rate:.2%} pass rate ({passed_cases}/{total_cases})")
            
            return execution_result
            
        except Exception as e:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"Error executing evaluation {eval_set_id}: {str(e)}")
            
            return EvalExecutionResult(
                run_id=run_id,
                eval_set_id=eval_set_id,
                pass_rate=0.0,
                total_cases=0,
                passed_cases=0,
                failed_cases=[],
                case_results=[],
                execution_time_ms=execution_time,
                pack_version="unknown",
                errors=[str(e)]
            )
    
    def schedule_eval_run(self, eval_set_id: str, schedule_time: datetime) -> str:
        """
        Schedule an evaluation run for future execution.
        
        Args:
            eval_set_id: Evaluation set ID
            schedule_time: When to run the evaluation
            
        Returns:
            Scheduled run ID
        """
        # This would integrate with a job scheduler like Celery or APScheduler
        # For now, we'll just log the scheduling request
        run_id = f"scheduled_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        logger.info(f"Scheduled evaluation {eval_set_id} for {schedule_time.isoformat()} with run_id {run_id}")
        
        # TODO: Integrate with background job system
        # scheduler.add_job(
        #     func=self.run_eval_set,
        #     args=[eval_set_id],
        #     trigger='date',
        #     run_date=schedule_time,
        #     id=run_id
        # )
        
        return run_id
    
    def _execute_parallel_evaluation(
        self, 
        eval_set: EvalSet, 
        decision_logs: List[DecisionLog], 
        domain_pack: Any
    ) -> List[EvalCaseResult]:
        """
        Execute evaluation cases in parallel.
        
        Args:
            eval_set: Evaluation set configuration
            decision_logs: Decision logs to evaluate
            domain_pack: Domain pack for validation
            
        Returns:
            List of case results
        """
        case_results = []
        verify_criteria = eval_set.blueprint.get('verify', {})
        
        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all cases for execution
            future_to_case = {
                executor.submit(
                    self._evaluate_single_case, 
                    log, 
                    verify_criteria, 
                    domain_pack
                ): log.case_id 
                for log in decision_logs
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_case):
                case_id = future_to_case[future]
                try:
                    result = future.result(timeout=30)  # 30 second timeout per case
                    case_results.append(result)
                except Exception as e:
                    logger.error(f"Error evaluating case {case_id}: {str(e)}")
                    # Create failed result
                    case_results.append(EvalCaseResult(
                        case_id=case_id,
                        passed=False,
                        checks={},
                        errors=[str(e)],
                        execution_time_ms=0,
                        details={}
                    ))
        
        return case_results
    
    def _evaluate_single_case(
        self, 
        decision_log: DecisionLog, 
        verify_criteria: Dict[str, Any], 
        domain_pack: Any
    ) -> EvalCaseResult:
        """
        Evaluate a single case against verification criteria.
        
        Args:
            decision_log: Decision log to evaluate
            verify_criteria: Verification criteria from blueprint
            domain_pack: Domain pack for validation
            
        Returns:
            EvalCaseResult for the case
        """
        start_time = datetime.utcnow()
        case_id = decision_log.case_id
        checks = {}
        errors = []
        details = {}
        
        try:
            # Run builtin checks
            check_types = verify_criteria.get('check_types', [])
            for check_type in check_types:
                if check_type in self.builtin_checks:
                    try:
                        passed, check_details = self.builtin_checks[check_type](
                            decision_log, domain_pack
                        )
                        checks[check_type] = passed
                        details[check_type] = check_details
                    except Exception as e:
                        checks[check_type] = False
                        errors.append(f"Error in {check_type} check: {str(e)}")
                else:
                    errors.append(f"Unknown check type: {check_type}")
            
            # Run custom validators
            custom_validators = verify_criteria.get('custom_validators', [])
            for validator_name in custom_validators:
                try:
                    passed, validator_details = self._run_custom_validator(
                        validator_name, decision_log, domain_pack
                    )
                    checks[f"custom_{validator_name}"] = passed
                    details[f"custom_{validator_name}"] = validator_details
                except Exception as e:
                    checks[f"custom_{validator_name}"] = False
                    errors.append(f"Error in custom validator {validator_name}: {str(e)}")
            
            # Check expected outcomes
            expected_outcomes = verify_criteria.get('expected_outcomes', {})
            if expected_outcomes:
                outcome_passed, outcome_details = self._check_expected_outcomes(
                    decision_log, expected_outcomes
                )
                checks['expected_outcomes'] = outcome_passed
                details['expected_outcomes'] = outcome_details
            
            # Determine overall pass/fail
            passed = all(checks.values()) and len(errors) == 0
            
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return EvalCaseResult(
                case_id=case_id,
                passed=passed,
                checks=checks,
                errors=errors,
                execution_time_ms=execution_time,
                details=details
            )
            
        except Exception as e:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"Error evaluating case {case_id}: {str(e)}")
            
            return EvalCaseResult(
                case_id=case_id,
                passed=False,
                checks=checks,
                errors=[str(e)],
                execution_time_ms=execution_time,
                details=details
            )
    
    def _check_sla(self, decision_log: DecisionLog, domain_pack: Any) -> Tuple[bool, Dict[str, Any]]:
        """Check SLA compliance for a decision log."""
        try:
            event_type = decision_log.event_data.get('type', 'Event.Default')
            latency_ms = decision_log.decision_data.get('latency_ms', 0)
            
            # Get SLA threshold from domain pack
            threshold_ms = domain_pack.get_sla_for_event(event_type)
            
            passed = latency_ms <= threshold_ms
            
            details = {
                'event_type': event_type,
                'latency_ms': latency_ms,
                'threshold_ms': threshold_ms,
                'within_sla': passed
            }
            
            return passed, details
            
        except Exception as e:
            return False, {'error': str(e)}
    
    def _check_template(self, decision_log: DecisionLog, domain_pack: Any) -> Tuple[bool, Dict[str, Any]]:
        """Check template selection correctness."""
        try:
            event_type = decision_log.event_data.get('type')
            template_id = decision_log.decision_data.get('template_id')
            
            # Get template mappings from domain pack
            mappings = domain_pack.get_mappings()
            template_mappings = mappings.get('templates', {})
            expected_templates = template_mappings.get(event_type, [])
            
            if not expected_templates:
                # No specific mapping, consider it passed
                passed = True
                details = {
                    'event_type': event_type,
                    'template_id': template_id,
                    'expected_templates': [],
                    'has_mapping': False
                }
            else:
                passed = template_id in expected_templates
                details = {
                    'event_type': event_type,
                    'template_id': template_id,
                    'expected_templates': expected_templates,
                    'has_mapping': True,
                    'correct_selection': passed
                }
            
            return passed, details
            
        except Exception as e:
            return False, {'error': str(e)}
    
    def _check_policy(self, decision_log: DecisionLog, domain_pack: Any) -> Tuple[bool, Dict[str, Any]]:
        """Check policy compliance."""
        try:
            # Get applicable rules from domain pack
            rules = domain_pack.get_rules_for_event(decision_log.event_data.get('type', ''))
            
            passed_rules = []
            failed_rules = []
            
            for rule in rules:
                rule_passed = self._evaluate_rule(decision_log, rule)
                if rule_passed:
                    passed_rules.append(rule.get('id', 'unknown'))
                else:
                    failed_rules.append(rule.get('id', 'unknown'))
            
            passed = len(failed_rules) == 0
            
            details = {
                'total_rules': len(rules),
                'passed_rules': passed_rules,
                'failed_rules': failed_rules,
                'all_passed': passed
            }
            
            return passed, details
            
        except Exception as e:
            return False, {'error': str(e)}
    
    def _check_delivery(self, decision_log: DecisionLog, domain_pack: Any) -> Tuple[bool, Dict[str, Any]]:
        """Check delivery status and success."""
        try:
            status = decision_log.decision_data.get('status', 'UNKNOWN')
            
            # Consider OK status as passed
            passed = status == 'OK'
            
            details = {
                'status': status,
                'delivered_successfully': passed
            }
            
            return passed, details
            
        except Exception as e:
            return False, {'error': str(e)}
    
    def _check_content(self, decision_log: DecisionLog, domain_pack: Any) -> Tuple[bool, Dict[str, Any]]:
        """Check content quality and appropriateness."""
        try:
            # This would involve more sophisticated content analysis
            # For now, we'll do basic checks
            
            template_id = decision_log.decision_data.get('template_id')
            event_type = decision_log.event_data.get('type')
            
            # Basic content validation
            has_template = bool(template_id)
            has_event_type = bool(event_type)
            
            passed = has_template and has_event_type
            
            details = {
                'has_template': has_template,
                'has_event_type': has_event_type,
                'template_id': template_id,
                'event_type': event_type
            }
            
            return passed, details
            
        except Exception as e:
            return False, {'error': str(e)}
    
    def _run_custom_validator(
        self, 
        validator_name: str, 
        decision_log: DecisionLog, 
        domain_pack: Any
    ) -> Tuple[bool, Dict[str, Any]]:
        """Run a custom validator from the domain pack."""
        try:
            validator_func = domain_pack.get_validator(validator_name)
            if not validator_func:
                raise ValueError(f"Custom validator {validator_name} not found")
            
            # Execute custom validator with timeout
            result = self.custom_validator.execute_validator(
                validator_func, 
                decision_log.to_dict(), 
                timeout_seconds=10
            )
            
            passed = result.get('passed', False)
            details = result.get('details', {})
            
            return passed, details
            
        except Exception as e:
            return False, {'error': str(e)}
    
    def _check_expected_outcomes(
        self, 
        decision_log: DecisionLog, 
        expected_outcomes: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if decision log matches expected outcomes."""
        try:
            checks = {}
            
            for key, expected_value in expected_outcomes.items():
                if key.startswith('decision.'):
                    actual_value = decision_log.decision_data.get(key[9:])  # Remove 'decision.' prefix
                elif key.startswith('event.'):
                    actual_value = decision_log.event_data.get(key[6:])  # Remove 'event.' prefix
                else:
                    # Direct key lookup in decision data
                    actual_value = decision_log.decision_data.get(key)
                
                checks[key] = actual_value == expected_value
            
            passed = all(checks.values())
            
            details = {
                'expected': expected_outcomes,
                'checks': checks,
                'all_matched': passed
            }
            
            return passed, details
            
        except Exception as e:
            return False, {'error': str(e)}
    
    def _evaluate_rule(self, decision_log: DecisionLog, rule: Dict[str, Any]) -> bool:
        """Evaluate a single rule against a decision log."""
        try:
            # Check if rule applies
            applies_when = rule.get('applies_when', {})
            if not self._check_conditions(decision_log, applies_when):
                return True  # Rule doesn't apply, so it passes
            
            # Check expected outcomes
            expect = rule.get('expect', {})
            return self._check_conditions(decision_log, expect)
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.get('id', 'unknown')}: {str(e)}")
            return False
    
    def _check_conditions(self, decision_log: DecisionLog, conditions: Dict[str, Any]) -> bool:
        """Check if conditions are met by the decision log."""
        try:
            for key, expected in conditions.items():
                if key.startswith('event.'):
                    actual = decision_log.event_data.get(key[6:])
                elif key.startswith('decision.'):
                    actual = decision_log.decision_data.get(key[9:])
                else:
                    # Try both event and decision data
                    actual = (decision_log.event_data.get(key) or 
                             decision_log.decision_data.get(key))
                
                if not self._compare_values(actual, expected):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking conditions: {str(e)}")
            return False
    
    def _compare_values(self, actual: Any, expected: Any) -> bool:
        """Compare actual and expected values with support for operators."""
        if isinstance(expected, str):
            if expected.startswith('>='):
                return float(actual) >= float(expected[2:].strip())
            elif expected.startswith('<='):
                return float(actual) <= float(expected[2:].strip())
            elif expected.startswith('>'):
                return float(actual) > float(expected[1:].strip())
            elif expected.startswith('<'):
                return float(actual) < float(expected[1:].strip())
            elif expected.startswith('!='):
                return actual != expected[2:].strip()
        
        return actual == expected
    
    def _load_decision_logs(self, project_id: str, case_ids: List[str]) -> List[DecisionLog]:
        """Load decision logs for the specified case IDs."""
        try:
            return DecisionLog.query.filter(
                DecisionLog.project_id == project_id,
                DecisionLog.case_id.in_(case_ids)
            ).all()
            
        except Exception as e:
            logger.error(f"Error loading decision logs: {str(e)}")
            return []
    
    def _store_eval_result(self, execution_result: EvalExecutionResult) -> None:
        """Store evaluation result in database."""
        try:
            eval_result = EvalResult(
                eval_set_id=execution_result.eval_set_id,
                run_id=execution_result.run_id,
                pass_rate=execution_result.pass_rate,
                total_cases=execution_result.total_cases,
                passed_cases=execution_result.passed_cases,
                failed_cases=execution_result.failed_cases,
                pack_version=execution_result.pack_version
            )
            
            db.session.add(eval_result)
            db.session.commit()
            
            logger.info(f"Stored eval result {execution_result.run_id}")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing eval result: {str(e)}")
            raise