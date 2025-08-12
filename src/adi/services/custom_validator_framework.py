"""
Custom Validator Framework

Provides safe execution environment for custom validators with timeout and error handling.
"""

import logging
import time
import traceback
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from contextlib import contextmanager

from ..models.finding import FindingData
from .scoring_context import ScoringContext

logger = logging.getLogger(__name__)


@dataclass
class ValidatorResult:
    """Result of custom validator execution."""
    validator_name: str
    success: bool
    findings: List[FindingData]
    execution_time_ms: float
    error: Optional[str] = None
    timeout: bool = False


class CustomValidatorError(Exception):
    """Raised when custom validator execution fails."""
    pass


class CustomValidatorFramework:
    """
    Framework for safely executing custom validators with timeout and error handling.
    """
    
    def __init__(self, default_timeout_seconds: int = 30, max_workers: int = 4):
        self.default_timeout_seconds = default_timeout_seconds
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Validator registry for debugging and monitoring
        self.validator_registry: Dict[str, Dict[str, Any]] = {}
    
    def register_validator(
        self, 
        name: str, 
        validator_func: Callable, 
        timeout_seconds: Optional[int] = None,
        description: str = "",
        version: str = "1.0.0"
    ) -> None:
        """
        Register a custom validator for execution.
        
        Args:
            name: Validator name
            validator_func: Validator function
            timeout_seconds: Custom timeout (uses default if None)
            description: Validator description
            version: Validator version
        """
        self.validator_registry[name] = {
            'function': validator_func,
            'timeout_seconds': timeout_seconds or self.default_timeout_seconds,
            'description': description,
            'version': version,
            'registered_at': time.time(),
            'execution_count': 0,
            'success_count': 0,
            'error_count': 0,
            'timeout_count': 0,
            'total_execution_time_ms': 0.0
        }
        
        logger.info(f"Registered custom validator: {name} (timeout: {timeout_seconds or self.default_timeout_seconds}s)")
    
    def execute_validator(
        self, 
        validator_name: str, 
        context: ScoringContext,
        timeout_seconds: Optional[int] = None
    ) -> ValidatorResult:
        """
        Execute a single custom validator safely.
        
        Args:
            validator_name: Name of validator to execute
            context: Scoring context
            timeout_seconds: Override timeout
            
        Returns:
            ValidatorResult with execution details
        """
        if validator_name not in self.validator_registry:
            return ValidatorResult(
                validator_name=validator_name,
                success=False,
                findings=[],
                execution_time_ms=0.0,
                error=f"Validator '{validator_name}' not registered"
            )
        
        validator_info = self.validator_registry[validator_name]
        validator_func = validator_info['function']
        timeout = timeout_seconds or validator_info['timeout_seconds']
        
        # Update execution stats
        validator_info['execution_count'] += 1
        
        start_time = time.time()
        
        try:
            # Execute validator with timeout
            future = self.executor.submit(self._safe_validator_execution, validator_func, context)
            findings = future.result(timeout=timeout)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Update success stats
            validator_info['success_count'] += 1
            validator_info['total_execution_time_ms'] += execution_time_ms
            
            # Ensure findings have correct validator name
            for finding in findings:
                if finding.validator_name == "unknown":
                    finding.validator_name = f"custom:{validator_name}"
            
            logger.debug(f"Custom validator {validator_name} executed successfully in {execution_time_ms:.2f}ms")
            
            return ValidatorResult(
                validator_name=validator_name,
                success=True,
                findings=findings,
                execution_time_ms=execution_time_ms
            )
            
        except FutureTimeoutError:
            execution_time_ms = (time.time() - start_time) * 1000
            validator_info['timeout_count'] += 1
            validator_info['total_execution_time_ms'] += execution_time_ms
            
            error_msg = f"Validator '{validator_name}' timed out after {timeout}s"
            logger.warning(error_msg)
            
            return ValidatorResult(
                validator_name=validator_name,
                success=False,
                findings=[],
                execution_time_ms=execution_time_ms,
                error=error_msg,
                timeout=True
            )
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            validator_info['error_count'] += 1
            validator_info['total_execution_time_ms'] += execution_time_ms
            
            error_msg = f"Validator '{validator_name}' failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return ValidatorResult(
                validator_name=validator_name,
                success=False,
                findings=[],
                execution_time_ms=execution_time_ms,
                error=error_msg
            )
    
    def execute_all_validators(
        self, 
        context: ScoringContext,
        parallel: bool = True
    ) -> List[ValidatorResult]:
        """
        Execute all registered validators.
        
        Args:
            context: Scoring context
            parallel: Execute validators in parallel
            
        Returns:
            List of validator results
        """
        if not self.validator_registry:
            return []
        
        if parallel:
            return self._execute_validators_parallel(context)
        else:
            return self._execute_validators_sequential(context)
    
    def _execute_validators_parallel(self, context: ScoringContext) -> List[ValidatorResult]:
        """Execute validators in parallel."""
        futures = {}
        
        for validator_name in self.validator_registry.keys():
            future = self.executor.submit(self.execute_validator, validator_name, context)
            futures[future] = validator_name
        
        results = []
        for future in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                validator_name = futures[future]
                logger.error(f"Failed to get result for validator {validator_name}: {str(e)}")
                results.append(ValidatorResult(
                    validator_name=validator_name,
                    success=False,
                    findings=[],
                    execution_time_ms=0.0,
                    error=str(e)
                ))
        
        return results
    
    def _execute_validators_sequential(self, context: ScoringContext) -> List[ValidatorResult]:
        """Execute validators sequentially."""
        results = []
        
        for validator_name in self.validator_registry.keys():
            result = self.execute_validator(validator_name, context)
            results.append(result)
        
        return results
    
    def _safe_validator_execution(
        self, 
        validator_func: Callable, 
        context: ScoringContext
    ) -> List[FindingData]:
        """
        Safely execute a validator function with error handling.
        
        Args:
            validator_func: The validator function to execute
            context: Scoring context
            
        Returns:
            List of findings
        """
        try:
            # Create a safe execution environment
            with self._safe_execution_context():
                # Call the validator function
                result = validator_func(context)
                
                # Validate the result
                if result is None:
                    return []
                
                if isinstance(result, list):
                    # Validate each finding
                    validated_findings = []
                    for item in result:
                        # Check if it's a FindingData instance (handle both import paths)
                        if hasattr(item, 'kind') and hasattr(item, 'severity') and hasattr(item, 'details'):
                            validated_findings.append(item)
                        else:
                            logger.warning(f"Invalid finding type returned by validator: {type(item)}")
                    return validated_findings
                
                elif hasattr(result, 'kind') and hasattr(result, 'severity') and hasattr(result, 'details'):
                    return [result]
                
                else:
                    logger.warning(f"Invalid result type returned by validator: {type(result)}")
                    return []
                    
        except Exception as e:
            logger.error(f"Custom validator execution failed: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise CustomValidatorError(f"Validator execution failed: {str(e)}") from e
    
    @contextmanager
    def _safe_execution_context(self):
        """Context manager for safe validator execution."""
        # Could add resource limits, sandboxing, etc. here
        try:
            yield
        except KeyboardInterrupt:
            raise CustomValidatorError("Validator execution interrupted")
        except MemoryError:
            raise CustomValidatorError("Validator exceeded memory limits")
        except Exception as e:
            raise CustomValidatorError(f"Validator execution error: {str(e)}") from e
    
    def get_validator_stats(self, validator_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get execution statistics for validators.
        
        Args:
            validator_name: Specific validator name (all if None)
            
        Returns:
            Statistics dictionary
        """
        if validator_name:
            if validator_name not in self.validator_registry:
                return {}
            
            info = self.validator_registry[validator_name]
            avg_execution_time = (
                info['total_execution_time_ms'] / info['execution_count'] 
                if info['execution_count'] > 0 else 0.0
            )
            
            return {
                'validator_name': validator_name,
                'description': info['description'],
                'version': info['version'],
                'execution_count': info['execution_count'],
                'success_count': info['success_count'],
                'error_count': info['error_count'],
                'timeout_count': info['timeout_count'],
                'success_rate': info['success_count'] / info['execution_count'] if info['execution_count'] > 0 else 0.0,
                'avg_execution_time_ms': avg_execution_time,
                'total_execution_time_ms': info['total_execution_time_ms']
            }
        
        else:
            # Return stats for all validators
            stats = {
                'total_validators': len(self.validator_registry),
                'validators': {}
            }
            
            for name in self.validator_registry.keys():
                stats['validators'][name] = self.get_validator_stats(name)
            
            return stats
    
    def test_validator(
        self, 
        validator_name: str, 
        test_context: ScoringContext,
        debug: bool = True
    ) -> Dict[str, Any]:
        """
        Test a validator with debugging information.
        
        Args:
            validator_name: Validator to test
            test_context: Test context
            debug: Include debug information
            
        Returns:
            Test results with debugging info
        """
        if validator_name not in self.validator_registry:
            return {
                'success': False,
                'error': f"Validator '{validator_name}' not registered"
            }
        
        logger.info(f"Testing custom validator: {validator_name}")
        
        # Execute the validator
        result = self.execute_validator(validator_name, test_context)
        
        test_result = {
            'validator_name': validator_name,
            'success': result.success,
            'execution_time_ms': result.execution_time_ms,
            'findings_count': len(result.findings),
            'findings': [f.to_dict() if hasattr(f, 'to_dict') else str(f) for f in result.findings]
        }
        
        if not result.success:
            test_result['error'] = result.error
            test_result['timeout'] = result.timeout
        
        if debug:
            test_result['debug'] = {
                'context_project_id': test_context.project_id,
                'context_case_id': test_context.case_id,
                'event_type': test_context.decision_log.event.type,
                'decision_action': test_context.decision_log.decision.action,
                'validator_stats': self.get_validator_stats(validator_name)
            }
        
        return test_result
    
    def cleanup(self):
        """Clean up resources."""
        self.executor.shutdown(wait=True)
        logger.info("Custom validator framework cleaned up")


# Global custom validator framework instance
_custom_validator_framework: Optional[CustomValidatorFramework] = None


def get_custom_validator_framework(
    default_timeout_seconds: int = 30,
    max_workers: int = 4
) -> CustomValidatorFramework:
    """Get the global custom validator framework instance."""
    global _custom_validator_framework
    
    if _custom_validator_framework is None:
        _custom_validator_framework = CustomValidatorFramework(
            default_timeout_seconds=default_timeout_seconds,
            max_workers=max_workers
        )
    
    return _custom_validator_framework