"""
Pydantic schemas for Decision Log validation.

These schemas validate the structure and content of decision logs ingested from production applications:
- DecisionLog: Main decision log payload
- EventData: Event information and context
- DecisionData: AI decision details
- VersionData: System version information
"""

from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
import re
import hashlib


class EventData(BaseModel):
    """Event information and context data."""
    type: str = Field(description="Event type (e.g., FlightDelay, FlightCancellation)")
    ts: datetime = Field(description="Event timestamp")
    scope: str = Field(description="Event scope/context")
    attrs: Dict[str, Any] = Field(default_factory=dict, description="Domain-specific event attributes")
    
    @field_validator('type')
    @classmethod
    def validate_event_type(cls, v):
        if not v.strip():
            raise ValueError("Event type cannot be empty")
        # Event type should be alphanumeric with optional dots/underscores
        if not re.match(r'^[A-Za-z][A-Za-z0-9._]*$', v):
            raise ValueError("Event type must start with letter and contain only letters, numbers, dots, underscores")
        return v
    
    @field_validator('scope')
    @classmethod
    def validate_scope(cls, v):
        if not v.strip():
            raise ValueError("Event scope cannot be empty")
        return v
    
    @field_validator('attrs')
    @classmethod
    def validate_attrs_no_pii(cls, v):
        """Validate that attrs don't contain PII - only hashed IDs allowed."""
        if not isinstance(v, dict):
            return v
        
        # Check for potential PII patterns
        pii_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{3}-\d{3}-\d{4}\b',  # Phone
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card
        ]
        
        def check_value_for_pii(value, key_path=""):
            if isinstance(value, str):
                for pattern in pii_patterns:
                    if re.search(pattern, value):
                        raise ValueError(f"Potential PII detected in attrs{key_path}: {pattern}")
            elif isinstance(value, dict):
                for k, v in value.items():
                    check_value_for_pii(v, f"{key_path}.{k}")
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    check_value_for_pii(item, f"{key_path}[{i}]")
        
        check_value_for_pii(v)
        return v


class DecisionData(BaseModel):
    """AI decision details and outcomes."""
    action: str = Field(description="Action taken by the AI system")
    channel: str = Field(description="Communication channel used")
    template_id: str = Field(description="Template identifier used")
    status: Literal["OK", "FAILED", "SKIPPED"] = Field(description="Decision execution status")
    latency_ms: int = Field(ge=0, description="Decision latency in milliseconds")
    counts: Optional[Dict[str, int]] = Field(None, description="Optional count metrics")
    
    @field_validator('action', 'channel', 'template_id')
    @classmethod
    def validate_non_empty_strings(cls, v):
        if not v.strip():
            raise ValueError("Action, channel, and template_id cannot be empty")
        return v
    
    @field_validator('counts')
    @classmethod
    def validate_counts(cls, v):
        if v is not None:
            for key, value in v.items():
                if not isinstance(value, int) or value < 0:
                    raise ValueError(f"Count values must be non-negative integers, got {key}: {value}")
        return v


class VersionData(BaseModel):
    """System version information for tracking deployments."""
    app: str = Field(description="Application version")
    policy: str = Field(description="Policy/rules version")
    factory_pr: str = Field(description="Software Factory PR number")
    
    @field_validator('app', 'policy', 'factory_pr')
    @classmethod
    def validate_non_empty_strings(cls, v):
        if not v.strip():
            raise ValueError("Version fields cannot be empty")
        return v
    
    @field_validator('factory_pr')
    @classmethod
    def validate_factory_pr_format(cls, v):
        # Factory PR should be numeric or in format PR-123
        if not re.match(r'^(PR-?)?\d+$', v):
            raise ValueError("Factory PR must be numeric or in format 'PR-123'")
        return v


class DecisionLog(BaseModel):
    """Main decision log payload from production applications."""
    project_id: str = Field(description="Project identifier")
    case_id: str = Field(description="Unique case identifier (must be hashed)")
    event: EventData = Field(description="Event information")
    decision: DecisionData = Field(description="AI decision details")
    version: VersionData = Field(description="System version information")
    links: Optional[Dict[str, str]] = Field(None, description="Optional external links")
    hashes: Optional[Dict[str, List[str]]] = Field(None, description="Optional hash collections")
    
    # Schema version for backward compatibility
    schema_version: str = Field(default="1.0.0", description="Decision log schema version")
    
    @field_validator('project_id')
    @classmethod
    def validate_project_id(cls, v):
        if not v.strip():
            raise ValueError("Project ID cannot be empty")
        # Project ID should be alphanumeric with optional hyphens/underscores
        if not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError("Project ID must contain only letters, numbers, hyphens, underscores")
        return v
    
    @field_validator('case_id')
    @classmethod
    def validate_case_id_is_hashed(cls, v):
        if not v.strip():
            raise ValueError("Case ID cannot be empty")
        
        # Case ID should be a hash - check if it looks like a hash
        # Accept common hash formats: hex strings of various lengths
        if not re.match(r'^[a-fA-F0-9]{8,}$', v):
            raise ValueError("Case ID must be a hashed identifier (hex string, min 8 chars)")
        
        return v
    
    @field_validator('links')
    @classmethod
    def validate_links(cls, v):
        if v is not None:
            for key, url in v.items():
                if not isinstance(url, str) or not url.strip():
                    raise ValueError(f"Link values must be non-empty strings, got {key}: {url}")
                # Basic URL validation
                if not re.match(r'^https?://', url):
                    raise ValueError(f"Links must be valid HTTP/HTTPS URLs, got {key}: {url}")
        return v
    
    @field_validator('hashes')
    @classmethod
    def validate_hashes(cls, v):
        if v is not None:
            for key, hash_list in v.items():
                if not isinstance(hash_list, list):
                    raise ValueError(f"Hash values must be lists, got {key}: {type(hash_list)}")
                for hash_val in hash_list:
                    if not isinstance(hash_val, str) or not re.match(r'^[a-fA-F0-9]{8,}$', hash_val):
                        raise ValueError(f"Hash values must be hex strings (min 8 chars), got {key}: {hash_val}")
        return v
    
    @field_validator('schema_version')
    @classmethod
    def validate_schema_version(cls, v):
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError("Schema version must be in semantic version format (e.g., '1.0.0')")
        return v
    
    @model_validator(mode='after')
    def validate_consistency(self):
        """Cross-field validation for consistency."""
        # Ensure event timestamp is reasonable (not too far in future/past)
        from datetime import timedelta
        
        now = datetime.utcnow()
        event_time = self.event.ts
        
        # Remove timezone info if present for comparison
        if event_time.tzinfo is not None:
            event_time = event_time.replace(tzinfo=None)
        
        # Allow up to 1 hour in the future (for clock skew)
        future_limit = now + timedelta(hours=1)
        if event_time > future_limit:
            raise ValueError("Event timestamp cannot be more than 1 hour in the future")
        
        # Allow up to 30 days in the past
        past_limit = now - timedelta(days=30)
        if event_time < past_limit:
            raise ValueError("Event timestamp cannot be more than 30 days in the past")
        
        return self


# Schema versioning support
SUPPORTED_SCHEMA_VERSIONS = ["1.0.0"]

def validate_schema_version(version: str) -> bool:
    """Check if the schema version is supported."""
    return version in SUPPORTED_SCHEMA_VERSIONS


def get_current_schema_version() -> str:
    """Get the current schema version."""
    return "1.0.0"


# Validation helper functions
def validate_decision_log(log_data: Dict[str, Any]) -> DecisionLog:
    """Validate decision log payload."""
    try:
        return DecisionLog(**log_data)
    except Exception as e:
        raise ValueError(f"Invalid decision log: {str(e)}")


def hash_case_id(original_id: str) -> str:
    """Helper function to hash case IDs for PII protection."""
    return hashlib.sha256(original_id.encode()).hexdigest()


def is_valid_hash(value: str) -> bool:
    """Check if a value looks like a valid hash."""
    return bool(re.match(r'^[a-fA-F0-9]{8,}$', value))


# PII detection patterns for additional validation
PII_DETECTION_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'phone': r'\b\d{3}-\d{3}-\d{4}\b',
    'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
    'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
}


def detect_pii_in_text(text: str) -> List[str]:
    """Detect potential PII patterns in text."""
    detected = []
    for pii_type, pattern in PII_DETECTION_PATTERNS.items():
        if re.search(pattern, text):
            detected.append(pii_type)
    return detected


def sanitize_for_logging(data: Any, max_depth: int = 3) -> Any:
    """Sanitize data for safe logging by removing potential PII."""
    if max_depth <= 0:
        return "[TRUNCATED]"
    
    if isinstance(data, dict):
        return {k: sanitize_for_logging(v, max_depth - 1) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_logging(item, max_depth - 1) for item in data[:10]]  # Limit list size
    elif isinstance(data, str):
        # Replace potential PII with placeholders
        sanitized = data
        for pii_type, pattern in PII_DETECTION_PATTERNS.items():
            sanitized = re.sub(pattern, f'[{pii_type.upper()}_REDACTED]', sanitized)
        return sanitized
    else:
        return data