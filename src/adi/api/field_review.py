"""
ADI Field Review API endpoints

Provides REST API endpoints for the Field Review interface:
- Decision case management
- Failure mode tagging
- Domain knowledge management
- Evaluation execution
- Work idea creation

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 12.1
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import uuid
import json

# Create blueprint
adi_bp = Blueprint('adi', __name__, url_prefix='/api/adi')

# Mock data for development - replace with actual database queries
MOCK_DECISION_CASES = [
    {
        'id': 'case-001',
        'timestamp': '2024-01-15T10:30:00Z',
        'domain': 'data-privacy',
        'decision': 'Approve data processing request for marketing analytics',
        'reasoning': 'User provided explicit consent for marketing purposes. Data is anonymized and retention period is within policy limits.',
        'confidence': 0.85,
        'isCorrect': True,
        'failureModes': [],
        'rawData': {
            'id': 'log-001',
            'timestamp': '2024-01-15T10:30:00Z',
            'request': {
                'user_id': 'user-123',
                'data_type': 'behavioral',
                'purpose': 'marketing_analytics',
                'consent_status': 'explicit'
            },
            'response': {
                'decision': 'approved',
                'reasoning': 'Consent verified, data anonymized',
                'conditions': ['30_day_retention', 'anonymization_required']
            },
            'context': {
                'user_consent_date': '2024-01-10T09:00:00Z',
                'data_sensitivity': 'medium',
                'regulatory_framework': 'GDPR'
            },
            'metadata': {
                'model': 'privacy-decision-v2.1',
                'version': '2.1.0',
                'latency': 245,
                'tokens': 1250
            }
        },
        'similarCases': ['case-002', 'case-005'],
        'workItems': []
    },
    {
        'id': 'case-002',
        'timestamp': '2024-01-15T11:45:00Z',
        'domain': 'data-privacy',
        'decision': 'Reject data sharing request with third-party vendor',
        'reasoning': 'Third-party vendor does not meet our data protection standards. No adequate safeguards in place.',
        'confidence': 0.92,
        'isCorrect': False,
        'failureModes': [
            {
                'id': 'fm-001',
                'name': 'Insufficient Context Analysis',
                'category': 'reasoning',
                'description': 'Failed to consider vendor certification updates',
                'severity': 'medium'
            }
        ],
        'rawData': {
            'id': 'log-002',
            'timestamp': '2024-01-15T11:45:00Z',
            'request': {
                'vendor_id': 'vendor-456',
                'data_type': 'customer_profiles',
                'purpose': 'service_enhancement',
                'contract_type': 'data_processing'
            },
            'response': {
                'decision': 'rejected',
                'reasoning': 'Vendor compliance insufficient',
                'risk_factors': ['no_certification', 'unclear_retention']
            },
            'context': {
                'vendor_certification': 'pending_renewal',
                'data_sensitivity': 'high',
                'business_impact': 'medium'
            },
            'metadata': {
                'model': 'privacy-decision-v2.1',
                'version': '2.1.0',
                'latency': 312,
                'tokens': 1580
            }
        },
        'similarCases': ['case-001', 'case-003'],
        'workItems': ['work-001']
    }
]

MOCK_FAILURE_MODES = [
    {
        'id': 'fm-001',
        'name': 'Insufficient Context Analysis',
        'category': 'reasoning',
        'description': 'AI failed to consider all relevant context factors',
        'severity': 'medium',
        'frequency': 15
    },
    {
        'id': 'fm-002',
        'name': 'Outdated Policy Reference',
        'category': 'knowledge',
        'description': 'Decision based on outdated policy information',
        'severity': 'high',
        'frequency': 8
    },
    {
        'id': 'fm-003',
        'name': 'Overconfident Assessment',
        'category': 'confidence',
        'description': 'Confidence score higher than warranted by evidence',
        'severity': 'low',
        'frequency': 23
    },
    {
        'id': 'fm-004',
        'name': 'Missing Risk Evaluation',
        'category': 'risk',
        'description': 'Failed to properly assess associated risks',
        'severity': 'critical',
        'frequency': 5
    }
]

MOCK_POLICY_RULES = [
    {
        'id': 'policy-001',
        'name': 'GDPR Consent Verification',
        'domain': 'data-privacy',
        'condition': 'data_type == "personal" AND purpose == "marketing"',
        'action': 'require_explicit_consent',
        'priority': 1,
        'active': True
    },
    {
        'id': 'policy-002',
        'name': 'Data Retention Limits',
        'domain': 'data-privacy',
        'condition': 'data_sensitivity == "high"',
        'action': 'apply_30_day_retention',
        'priority': 2,
        'active': True
    }
]

MOCK_EVAL_SETS = [
    {
        'id': 'eval-001',
        'name': 'Privacy Decision Accuracy',
        'domain': 'data-privacy',
        'description': 'Comprehensive evaluation of privacy-related decisions',
        'testCases': 150,
        'lastRun': '2024-01-14T15:30:00Z',
        'status': 'ready'
    },
    {
        'id': 'eval-002',
        'name': 'Consent Compliance Check',
        'domain': 'data-privacy',
        'description': 'Validates consent handling and compliance',
        'testCases': 75,
        'lastRun': '2024-01-13T09:15:00Z',
        'status': 'completed'
    }
]

@adi_bp.route('/cases', methods=['GET'])
def get_decision_cases():
    """Get decision cases for review"""
    domain = request.args.get('domain')
    limit = int(request.args.get('limit', 50))
    
    cases = MOCK_DECISION_CASES
    if domain:
        cases = [case for case in cases if case['domain'] == domain]
    
    return jsonify(cases[:limit])

@adi_bp.route('/cases/<case_id>', methods=['GET'])
def get_decision_case(case_id):
    """Get specific decision case"""
    case = next((case for case in MOCK_DECISION_CASES if case['id'] == case_id), None)
    if not case:
        return jsonify({'error': 'Case not found'}), 404
    return jsonify(case)

@adi_bp.route('/cases/<case_id>/correctness', methods=['PUT'])
def update_case_correctness(case_id):
    """Update case correctness assessment"""
    data = request.get_json()
    is_correct = data.get('isCorrect')
    
    # In real implementation, update database
    for case in MOCK_DECISION_CASES:
        if case['id'] == case_id:
            case['isCorrect'] = is_correct
            break
    
    return jsonify({'success': True})

@adi_bp.route('/failure-modes', methods=['GET'])
def get_failure_modes():
    """Get available failure modes"""
    domain = request.args.get('domain')
    modes = MOCK_FAILURE_MODES
    
    if domain:
        # In real implementation, filter by domain
        pass
    
    return jsonify(modes)

@adi_bp.route('/cases/<case_id>/failure-modes', methods=['POST'])
def tag_failure_mode(case_id):
    """Tag a case with a failure mode"""
    data = request.get_json()
    failure_mode = data.get('failureMode')
    
    # In real implementation, store in database
    for case in MOCK_DECISION_CASES:
        if case['id'] == case_id:
            if 'failureModes' not in case:
                case['failureModes'] = []
            case['failureModes'].append(failure_mode)
            break
    
    return jsonify({'success': True})

@adi_bp.route('/knowledge', methods=['POST'])
def add_domain_knowledge():
    """Add domain knowledge"""
    data = request.get_json()
    
    # In real implementation, validate and store in database
    knowledge = {
        'id': str(uuid.uuid4()),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        **data
    }
    
    return jsonify(knowledge)

@adi_bp.route('/knowledge', methods=['GET'])
def get_domain_knowledge():
    """Get domain knowledge"""
    domain = request.args.get('domain')
    
    # In real implementation, query database
    knowledge = [
        {
            'id': 'knowledge-001',
            'domain': domain or 'data-privacy',
            'type': 'policy',
            'content': 'GDPR requires explicit consent for marketing data processing',
            'format': 'text',
            'tags': ['gdpr', 'consent', 'marketing'],
            'timestamp': '2024-01-10T12:00:00Z'
        }
    ]
    
    return jsonify(knowledge)

@adi_bp.route('/rescore', methods=['POST'])
def rescore_similar_cases():
    """Trigger re-scoring of similar cases"""
    data = request.get_json()
    domain = data.get('domain')
    
    # In real implementation, trigger background job
    return jsonify({'success': True, 'message': f'Re-scoring initiated for domain: {domain}'})

@adi_bp.route('/policies', methods=['GET'])
def get_policy_rules():
    """Get policy rules for domain"""
    domain = request.args.get('domain')
    
    rules = [rule for rule in MOCK_POLICY_RULES if rule['domain'] == domain]
    return jsonify(rules)

@adi_bp.route('/cases/<case_id>/similar', methods=['GET'])
def get_similar_cases(case_id):
    """Get similar cases"""
    # Mock similar cases
    similar = [
        {
            'id': 'case-003',
            'similarity': 0.87,
            'decision': 'Approve data processing with conditions',
            'outcome': 'correct',
            'timestamp': '2024-01-12T14:20:00Z'
        },
        {
            'id': 'case-004',
            'similarity': 0.73,
            'decision': 'Reject data sharing request',
            'outcome': 'incorrect',
            'timestamp': '2024-01-11T16:45:00Z'
        }
    ]
    
    return jsonify(similar)

@adi_bp.route('/eval-sets', methods=['GET'])
def get_eval_sets():
    """Get evaluation sets"""
    domain = request.args.get('domain')
    
    eval_sets = MOCK_EVAL_SETS
    if domain:
        eval_sets = [es for es in eval_sets if es['domain'] == domain]
    
    return jsonify(eval_sets)

@adi_bp.route('/eval-sets/<eval_set_id>/execute', methods=['POST'])
def execute_eval_set(eval_set_id):
    """Execute evaluation set"""
    execution_id = str(uuid.uuid4())
    
    # In real implementation, start background evaluation job
    return jsonify({'executionId': execution_id})

@adi_bp.route('/eval-sets/<eval_set_id>/results', methods=['GET'])
def get_eval_results(eval_set_id):
    """Get evaluation results"""
    # Mock results
    results = [
        {
            'id': 'result-001',
            'evalSetId': eval_set_id,
            'timestamp': '2024-01-14T15:30:00Z',
            'accuracy': 0.87,
            'precision': 0.89,
            'recall': 0.85,
            'f1Score': 0.87,
            'details': {
                'passed': 131,
                'failed': 19,
                'total': 150,
                'failures': [
                    {
                        'testCase': 'Privacy consent validation',
                        'expected': 'require_explicit_consent',
                        'actual': 'allow_implied_consent',
                        'reason': 'Failed to detect marketing purpose'
                    }
                ]
            }
        }
    ]
    
    return jsonify(results)

@adi_bp.route('/eval-executions/<execution_id>', methods=['GET'])
def get_eval_execution(execution_id):
    """Get evaluation execution status/result"""
    # Mock execution result
    result = {
        'id': execution_id,
        'evalSetId': 'eval-001',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'accuracy': 0.91,
        'precision': 0.88,
        'recall': 0.94,
        'f1Score': 0.91,
        'details': {
            'passed': 137,
            'failed': 13,
            'total': 150,
            'failures': []
        }
    }
    
    return jsonify(result)

@adi_bp.route('/work-ideas', methods=['POST'])
def create_work_idea():
    """Create work idea for Think stage"""
    data = request.get_json()
    insight = data.get('insight')
    context = data.get('context')
    
    # In real implementation, integrate with Think stage
    work_idea = {
        'id': str(uuid.uuid4()),
        'title': f"Improve {context.get('domain', 'system')} decision accuracy",
        'description': insight,
        'priority': context.get('priority', 'medium'),
        'status': 'draft',
        'sourceCase': context.get('sourceCase'),
        'insights': context.get('insights', []),
        'createdAt': datetime.utcnow().isoformat() + 'Z'
    }
    
    return jsonify(work_idea)

@adi_bp.route('/work-ideas', methods=['GET'])
def get_work_ideas():
    """Get work ideas"""
    source_case = request.args.get('sourceCase')
    
    # Mock work ideas
    ideas = [
        {
            'id': 'work-001',
            'title': 'Improve privacy decision context analysis',
            'description': 'Enhance AI model to better analyze vendor certification status',
            'priority': 'high',
            'status': 'ready',
            'sourceCase': source_case or 'case-002',
            'insights': ['Vendor certification updates not considered', 'Need real-time compliance checking'],
            'createdAt': '2024-01-15T12:00:00Z'
        }
    ]
    
    return jsonify(ideas)

@adi_bp.route('/metrics', methods=['GET'])
def get_domain_metrics():
    """Get domain metrics and analytics"""
    domain = request.args.get('domain')
    
    # Mock metrics
    metrics = {
        'totalCases': 247,
        'correctnessRate': 0.83,
        'commonFailureModes': [
            {
                'mode': 'Insufficient Context Analysis',
                'frequency': 15,
                'trend': 'decreasing'
            },
            {
                'mode': 'Outdated Policy Reference',
                'frequency': 8,
                'trend': 'stable'
            },
            {
                'mode': 'Overconfident Assessment',
                'frequency': 23,
                'trend': 'increasing'
            }
        ],
        'confidenceDistribution': [
            {'range': '0.9-1.0', 'count': 89},
            {'range': '0.8-0.9', 'count': 76},
            {'range': '0.7-0.8', 'count': 45},
            {'range': '0.6-0.7', 'count': 23},
            {'range': '0.0-0.6', 'count': 14}
        ]
    }
    
    return jsonify(metrics)