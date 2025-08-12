"""
Domain Pack Schema Definitions

Pydantic schemas for domain pack configuration and validation
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime

class PackMetadata(BaseModel):
    """Pack metadata configuration"""
    name: str = Field(..., description="Human-readable pack name")
    version: str = Field(..., description="Semantic version (e.g., 1.0.0)")
    owner_team: str = Field(..., description="Team responsible for the pack")
    description: Optional[str] = Field(None, description="Pack description")
    extends: Optional[str] = Field(None, description="Parent pack to inherit from")

class PackDefaults(BaseModel):
    """Default configuration values"""
    sla: Optional[Dict[str, int]] = Field(None, description="SLA timeouts in milliseconds")
    review: Optional[Dict[str, Any]] = Field(None, description="Review configuration")

class FailureMode(BaseModel):
    """Failure mode definition"""
    code: str = Field(..., description="Unique failure mode code")
    label: str = Field(..., description="Human-readable label")
    group: str = Field(..., description="Category group")
    color: str = Field(..., description="Display color (hex)")
    description: Optional[str] = Field(None, description="Detailed description")

class MetricConfig(BaseModel):
    """Metric configuration"""
    key: str = Field(..., description="Unique metric key")
    label: str = Field(..., description="Display label")
    description: str = Field(..., description="Metric description")
    type: Literal["north_star", "supporting"] = Field(..., description="Metric type")
    compute: str = Field(..., description="Computation method")
    target: Optional[float] = Field(None, description="Target value")
    unit: Optional[str] = Field(None, description="Unit of measurement")

class PolicyRule(BaseModel):
    """Policy rule definition"""
    id: str = Field(..., description="Unique rule ID")
    description: str = Field(..., description="Rule description")
    applies_when: Dict[str, Any] = Field(..., description="Conditions when rule applies")
    expect: Dict[str, Any] = Field(..., description="Expected outcomes")

class DomainKnowledge(BaseModel):
    """Domain knowledge item"""
    title: str = Field(..., description="Knowledge title")
    content: str = Field(..., description="Knowledge content")
    rule_yaml: Optional[str] = Field(None, description="Associated YAML rule")
    scope_filters: Dict[str, Any] = Field(default_factory=dict, description="Scope filters")
    source_link: Optional[str] = Field(None, description="Source reference")
    author: str = Field(default="", description="Author name")
    tags: List[str] = Field(default_factory=list, description="Tags")

class DomainPackData(BaseModel):
    """Domain pack data structure"""
    defaults: Optional[PackDefaults] = None
    ontology: Optional[List[FailureMode]] = None
    metrics: Optional[List[MetricConfig]] = None
    rules: Optional[List[PolicyRule]] = None
    knowledge: Optional[List[DomainKnowledge]] = None

class DomainPackSchema(BaseModel):
    """Complete domain pack schema"""
    id: str
    project_id: str
    name: str
    version: str
    owner_team: str
    description: Optional[str] = None
    extends: Optional[str] = None
    status: Literal["active", "draft", "deprecated"] = "active"
    created_at: str
    updated_at: str
    pack_data: DomainPackData

    @validator('version')
    def validate_version(cls, v):
        """Validate semantic version format"""
        parts = v.split('.')
        if len(parts) != 3:
            raise ValueError('Version must be in semantic format (x.y.z)')
        
        for part in parts:
            try:
                int(part)
            except ValueError:
                raise ValueError('Version parts must be integers')
        
        return v

    @validator('pack_data')
    def validate_pack_data(cls, v):
        """Validate pack data consistency"""
        if v.ontology:
            codes = set()
            for failure_mode in v.ontology:
                if failure_mode.code in codes:
                    raise ValueError(f'Duplicate failure mode code: {failure_mode.code}')
                codes.add(failure_mode.code)
        
        if v.metrics:
            keys = set()
            for metric in v.metrics:
                if metric.key in keys:
                    raise ValueError(f'Duplicate metric key: {metric.key}')
                keys.add(metric.key)
        
        if v.rules:
            ids = set()
            for rule in v.rules:
                if rule.id in ids:
                    raise ValueError(f'Duplicate rule ID: {rule.id}')
                ids.add(rule.id)
        
        return v

class PackVersionSchema(BaseModel):
    """Pack version information"""
    version: str
    deployed_at: str
    status: Literal["active", "deprecated", "rollback"]
    factory_pr: Optional[str] = None

class PackValidationResult(BaseModel):
    """Pack validation result"""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class PackDeploymentRequest(BaseModel):
    """Pack deployment request"""
    version: Optional[str] = None
    force: bool = False

class PackRollbackRequest(BaseModel):
    """Pack rollback request"""
    version: str
    reason: Optional[str] = None

# Legacy aliases for backward compatibility
PackConfig = PackMetadata
MetricsConfig = List[MetricConfig]

# Validation functions
def validate_pack_config(config: Dict[str, Any]) -> PackMetadata:
    """Validate pack configuration"""
    return PackMetadata(**config.get('pack', {}))

def validate_ontology(ontology: List[Dict[str, Any]]) -> List[FailureMode]:
    """Validate ontology configuration"""
    return [FailureMode(**item) for item in ontology]

def validate_metrics(metrics: Dict[str, Any]) -> List[MetricConfig]:
    """Validate metrics configuration"""
    all_metrics = []
    
    # Add north star metrics
    for metric in metrics.get('north_star', []):
        all_metrics.append(MetricConfig(**metric, type='north_star'))
    
    # Add supporting metrics
    for metric in metrics.get('supporting', []):
        all_metrics.append(MetricConfig(**metric, type='supporting'))
    
    return all_metrics