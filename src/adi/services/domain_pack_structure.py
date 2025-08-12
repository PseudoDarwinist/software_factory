"""
Domain Pack file system structure management.

Provides functions to create and manage Domain Pack directory structures.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from ..schemas.domain_pack import PackConfig, MetricsConfig, FailureMode


def create_domain_pack_structure(
    pack_id: str, 
    domain_packs_root: str = "domain-packs"
) -> Path:
    """
    Create the complete directory structure for a new domain pack.
    
    Args:
        pack_id: The domain pack identifier (directory name)
        domain_packs_root: Root directory for domain packs
        
    Returns:
        Path to the created pack directory
    """
    pack_path = Path(domain_packs_root) / pack_id
    pack_path.mkdir(parents=True, exist_ok=True)
    
    # Create required subdirectories
    subdirs = [
        'policy',      # rules.yaml, knowledge.md
        'validators',  # __init__.py, custom.py
        'evals',       # evaluation blueprints
        'mappings'     # template mappings and other lookups
    ]
    
    for subdir in subdirs:
        (pack_path / subdir).mkdir(exist_ok=True)
    
    # Create __init__.py in validators directory
    validators_init = pack_path / 'validators' / '__init__.py'
    if not validators_init.exists():
        validators_init.write_text('''"""
Custom validators for this domain pack.

Register custom validation functions here.
"""

from .custom import *

# Register custom validators
CUSTOM_VALIDATORS = {
    # Add custom validator registrations here
    # 'validator_name': validator_function,
}
''')
    
    # Create placeholder custom.py in validators directory
    custom_validators = pack_path / 'validators' / 'custom.py'
    if not custom_validators.exists():
        custom_validators.write_text('''"""
Custom validation functions for this domain pack.

Implement domain-specific validation logic here.
"""

from typing import Dict, List, Any
from ...models.decision_log import DecisionLog


def example_custom_validator(log: DecisionLog) -> List[Dict[str, Any]]:
    """
    Example custom validator function.
    
    Args:
        log: Decision log to validate
        
    Returns:
        List of findings (empty if no issues found)
    """
    findings = []
    
    # Example validation logic
    # if some_condition:
    #     findings.append({
    #         'kind': 'Custom.Example',
    #         'severity': 'medium',
    #         'details': {'message': 'Custom validation failed'},
    #         'suggested_fix': 'Fix the custom issue'
    #     })
    
    return findings
''')
    
    return pack_path


def create_default_pack_config(
    pack_name: str,
    pack_version: str = "1.0.0",
    owner_team: str = "platform",
    description: str = "Default domain pack"
) -> Dict[str, Any]:
    """
    Create a default pack.yaml configuration.
    
    Args:
        pack_name: Human-readable pack name
        pack_version: Semantic version
        owner_team: Team responsible for the pack
        description: Pack description
        
    Returns:
        Dict representing pack.yaml structure
    """
    return {
        'pack': {
            'name': pack_name,
            'version': pack_version,
            'owner_team': owner_team,
            'description': description
        },
        'defaults': {
            'sla': {
                'Event.Default': 600000  # 10 minutes
            },
            'review': {
                'insight_thresholds': {
                    'cluster_min': 5,
                    'window_minutes': 60
                },
                'auto_tag_confidence': 0.85
            }
        }
    }


def create_default_ontology() -> List[Dict[str, Any]]:
    """
    Create a default ontology.json with common failure modes.
    
    Returns:
        List of failure mode definitions
    """
    return [
        {
            'code': 'Time.SLA',
            'label': 'Late or missed send',
            'group': 'Time',
            'color': '#ef4444',
            'description': 'Communication sent outside SLA timeframe'
        },
        {
            'code': 'Template.Selection',
            'label': 'Wrong template selected',
            'group': 'Template',
            'color': '#3b82f6',
            'description': 'Incorrect template chosen for event type'
        },
        {
            'code': 'Policy.Misapplied',
            'label': 'Policy misapplied',
            'group': 'Policy',
            'color': '#22c55e',
            'description': 'Business rule or regulation incorrectly applied'
        },
        {
            'code': 'Delivery.Failed',
            'label': 'Delivery failed',
            'group': 'Delivery',
            'color': '#a855f7',
            'description': 'Message failed to deliver to recipient'
        },
        {
            'code': 'Audience.Wrong',
            'label': 'Wrong recipient audience',
            'group': 'Audience',
            'color': '#f59e0b',
            'description': 'Message sent to wrong or partial audience'
        }
    ]


def create_default_metrics() -> Dict[str, Any]:
    """
    Create a default metrics.yaml configuration.
    
    Returns:
        Dict representing metrics.yaml structure
    """
    return {
        'north_star': [
            {
                'key': 'OnTimeRate',
                'label': 'On-time communications',
                'description': 'Percentage of messages sent within SLA',
                'compute': 'builtin:ontime_rate',
                'target': 0.95
            }
        ],
        'supporting': [
            {
                'key': 'P95Latency',
                'label': 'P95 send latency (ms)',
                'description': '95th percentile response time',
                'compute': 'builtin:p95_latency',
                'target': 3000
            },
            {
                'key': 'TemplateAccuracy',
                'label': 'Template selection accuracy',
                'description': 'Percentage of correct template choices',
                'compute': 'builtin:template_accuracy',
                'target': 0.98
            },
            {
                'key': 'DeliverySuccessRate',
                'label': 'Delivery success rate',
                'description': 'Percentage of messages successfully delivered',
                'compute': 'builtin:delivery_success_rate',
                'target': 0.99
            }
        ]
    }


def create_complete_domain_pack(
    pack_id: str,
    pack_name: str,
    pack_version: str = "1.0.0",
    owner_team: str = "platform",
    description: str = "New domain pack",
    domain_packs_root: str = "domain-packs"
) -> Path:
    """
    Create a complete domain pack with default configuration files.
    
    Args:
        pack_id: The domain pack identifier (directory name)
        pack_name: Human-readable pack name
        pack_version: Semantic version
        owner_team: Team responsible for the pack
        description: Pack description
        domain_packs_root: Root directory for domain packs
        
    Returns:
        Path to the created pack directory
    """
    # Create directory structure
    pack_path = create_domain_pack_structure(pack_id, domain_packs_root)
    
    # Create pack.yaml
    pack_config = create_default_pack_config(pack_name, pack_version, owner_team, description)
    with open(pack_path / 'pack.yaml', 'w') as f:
        yaml.dump(pack_config, f, default_flow_style=False, sort_keys=False)
    
    # Create ontology.json
    ontology = create_default_ontology()
    with open(pack_path / 'ontology.json', 'w') as f:
        json.dump(ontology, f, indent=2)
    
    # Create metrics.yaml
    metrics = create_default_metrics()
    with open(pack_path / 'metrics.yaml', 'w') as f:
        yaml.dump(metrics, f, default_flow_style=False, sort_keys=False)
    
    # Create policy/rules.yaml
    rules_config = {
        'rules': [
            {
                'id': 'example.rule',
                'description': 'Example rule - replace with domain-specific rules',
                'applies_when': {
                    'event.type': 'ExampleEvent'
                },
                'expect': {
                    'status': 'OK'
                }
            }
        ]
    }
    with open(pack_path / 'policy' / 'rules.yaml', 'w') as f:
        yaml.dump(rules_config, f, default_flow_style=False, sort_keys=False)
    
    # Create policy/knowledge.md
    knowledge_content = f"""# {pack_name} Domain Knowledge

## Overview

This file contains free-form domain knowledge for the {pack_name} domain pack.

## Business Rules

Add domain-specific business rules and context here.

## Common Failure Patterns

Document common failure patterns and their causes.

## Troubleshooting Guide

Provide guidance for resolving common issues.

## References

- Link to relevant documentation
- Link to business process descriptions
- Link to regulatory requirements
"""
    with open(pack_path / 'policy' / 'knowledge.md', 'w') as f:
        f.write(knowledge_content)
    
    # Create example eval blueprint
    eval_config = {
        'id': 'example_eval',
        'tag': 'Time.SLA',
        'select': {
            'event_type': 'ExampleEvent',
            'window_hours': 24,
            'min_cases': 10
        },
        'verify': {
            'expect_status': 'OK',
            'min_pass_rate': 0.95
        },
        'min_pass_rate': 0.95
    }
    with open(pack_path / 'evals' / 'example.yaml', 'w') as f:
        yaml.dump(eval_config, f, default_flow_style=False, sort_keys=False)
    
    # Create example template mapping
    template_mapping = {
        'event_templates': {
            'ExampleEvent': {
                'default': 'EXAMPLE-01',
                'by_channel': {
                    'SMS': 'EXAMPLE-SMS-01',
                    'Email': 'EXAMPLE-EMAIL-01'
                }
            }
        }
    }
    with open(pack_path / 'mappings' / 'templates.yaml', 'w') as f:
        yaml.dump(template_mapping, f, default_flow_style=False, sort_keys=False)
    
    return pack_path


def get_domain_pack_file_structure() -> Dict[str, str]:
    """
    Get the expected file structure for a domain pack.
    
    Returns:
        Dict mapping file paths to descriptions
    """
    return {
        'pack.yaml': 'Pack metadata and configuration defaults',
        'ontology.json': 'Failure mode definitions with codes, labels, and colors',
        'metrics.yaml': 'North-star and supporting metrics configuration',
        'policy/rules.yaml': 'Structured business rules in YAML format',
        'policy/knowledge.md': 'Free-form domain knowledge in Markdown',
        'validators/__init__.py': 'Custom validator registration',
        'validators/custom.py': 'Custom validation function implementations',
        'evals/': 'Directory containing evaluation blueprint files',
        'mappings/': 'Directory containing lookup tables and mappings'
    }