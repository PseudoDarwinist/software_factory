"""
ADI Pack Configuration API

Handles domain pack configuration, versioning, and deployment
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import json
import os
import yaml
from typing import Dict, Any, List, Optional

from ..services.domain_pack_loader import DomainPack
from ..schemas.domain_pack import DomainPackSchema, PackVersionSchema

pack_config_bp = Blueprint('pack_config', __name__)

@pack_config_bp.route('/packs/<project_id>', methods=['GET'])
def get_domain_pack(project_id: str):
    """Get domain pack configuration for a project"""
    try:
        pack = DomainPack(project_id)
        
        # Convert to API response format
        pack_data = {
            'id': f"pack_{project_id}",
            'project_id': project_id,
            'name': pack.pack_config.get('pack', {}).get('name', f'Pack for {project_id}'),
            'version': pack.pack_config.get('pack', {}).get('version', '1.0.0'),
            'owner_team': pack.pack_config.get('pack', {}).get('owner_team', 'unknown'),
            'description': pack.pack_config.get('pack', {}).get('description', ''),
            'extends': pack.pack_config.get('pack', {}).get('extends'),
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'pack_data': {
                'defaults': pack.pack_config.get('defaults', {}),
                'ontology': pack.ontology,
                'metrics': pack.metrics,
                'rules': pack.rules,
                'knowledge': pack.knowledge
            }
        }
        
        return jsonify(pack_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading domain pack for {project_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@pack_config_bp.route('/packs/<project_id>', methods=['PUT'])
def update_domain_pack(project_id: str):
    """Update domain pack configuration"""
    try:
        data = request.get_json()
        
        # Get the pack directory
        pack_dir = os.path.join('domain-packs', project_id)
        os.makedirs(pack_dir, exist_ok=True)
        
        # Update pack.yaml if metadata changed
        if any(key in data for key in ['name', 'version', 'owner_team', 'description', 'extends']):
            pack_yaml_path = os.path.join(pack_dir, 'pack.yaml')
            
            # Load existing or create new pack.yaml
            if os.path.exists(pack_yaml_path):
                with open(pack_yaml_path, 'r') as f:
                    pack_config = yaml.safe_load(f) or {}
            else:
                pack_config = {'pack': {}, 'defaults': {}}
            
            # Update pack metadata
            pack_section = pack_config.setdefault('pack', {})
            if 'name' in data:
                pack_section['name'] = data['name']
            if 'version' in data:
                pack_section['version'] = data['version']
            if 'owner_team' in data:
                pack_section['owner_team'] = data['owner_team']
            if 'description' in data:
                pack_section['description'] = data['description']
            if 'extends' in data:
                pack_section['extends'] = data['extends']
            
            # Write updated pack.yaml
            with open(pack_yaml_path, 'w') as f:
                yaml.dump(pack_config, f, default_flow_style=False)
        
        # Update other pack components if provided
        if 'pack_data' in data:
            pack_data = data['pack_data']
            
            # Update ontology.json
            if 'ontology' in pack_data:
                ontology_path = os.path.join(pack_dir, 'ontology.json')
                with open(ontology_path, 'w') as f:
                    json.dump(pack_data['ontology'], f, indent=2)
            
            # Update metrics.yaml
            if 'metrics' in pack_data:
                metrics_path = os.path.join(pack_dir, 'metrics.yaml')
                with open(metrics_path, 'w') as f:
                    yaml.dump(pack_data['metrics'], f, default_flow_style=False)
            
            # Update rules
            if 'rules' in pack_data:
                policy_dir = os.path.join(pack_dir, 'policy')
                os.makedirs(policy_dir, exist_ok=True)
                rules_path = os.path.join(policy_dir, 'rules.yaml')
                with open(rules_path, 'w') as f:
                    yaml.dump({'rules': pack_data['rules']}, f, default_flow_style=False)
            
            # Update knowledge
            if 'knowledge' in pack_data:
                policy_dir = os.path.join(pack_dir, 'policy')
                os.makedirs(policy_dir, exist_ok=True)
                knowledge_path = os.path.join(policy_dir, 'knowledge.md')
                
                # Convert knowledge items to markdown
                knowledge_content = "# Domain Knowledge\n\n"
                for item in pack_data['knowledge']:
                    knowledge_content += f"## {item.get('title', 'Untitled')}\n\n"
                    knowledge_content += f"{item.get('content', '')}\n\n"
                    if item.get('rule_yaml'):
                        knowledge_content += f"```yaml\n{item['rule_yaml']}\n```\n\n"
                
                with open(knowledge_path, 'w') as f:
                    f.write(knowledge_content)
        
        # Return updated pack
        return get_domain_pack(project_id)
        
    except Exception as e:
        current_app.logger.error(f"Error updating domain pack for {project_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@pack_config_bp.route('/packs/<project_id>/deploy', methods=['POST'])
def deploy_domain_pack(project_id: str):
    """Deploy domain pack to production"""
    try:
        data = request.get_json() or {}
        version = data.get('version')
        
        # For now, deployment is just marking the pack as active
        # In a full implementation, this would:
        # 1. Validate the pack configuration
        # 2. Create a snapshot in the database
        # 3. Update the active version
        # 4. Trigger cache refresh
        
        current_app.logger.info(f"Deploying domain pack for {project_id}, version: {version}")
        
        return jsonify({
            'status': 'deployed',
            'project_id': project_id,
            'version': version,
            'deployed_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error deploying domain pack for {project_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@pack_config_bp.route('/packs/<project_id>/versions', methods=['GET'])
def get_pack_versions(project_id: str):
    """Get version history for a domain pack"""
    try:
        # For now, return mock version data
        # In a full implementation, this would query the database
        versions = [
            {
                'version': '1.0.0',
                'deployed_at': datetime.utcnow().isoformat(),
                'status': 'active'
            }
        ]
        
        return jsonify(versions)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching versions for {project_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@pack_config_bp.route('/packs/<project_id>/rollback', methods=['POST'])
def rollback_domain_pack(project_id: str):
    """Rollback domain pack to a previous version"""
    try:
        data = request.get_json()
        version = data.get('version')
        
        if not version:
            return jsonify({'error': 'Version is required'}), 400
        
        # For now, just log the rollback request
        # In a full implementation, this would:
        # 1. Validate the version exists
        # 2. Restore the pack configuration from snapshot
        # 3. Update the active version
        # 4. Trigger cache refresh
        
        current_app.logger.info(f"Rolling back domain pack for {project_id} to version: {version}")
        
        return jsonify({
            'status': 'rolled_back',
            'project_id': project_id,
            'version': version,
            'rolled_back_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error rolling back domain pack for {project_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@pack_config_bp.route('/packs/<project_id>/validate', methods=['POST'])
def validate_domain_pack(project_id: str):
    """Validate domain pack configuration"""
    try:
        data = request.get_json()
        
        # Basic validation
        errors = []
        warnings = []
        
        # Validate pack metadata
        if 'name' in data and not data['name'].strip():
            errors.append("Pack name cannot be empty")
        
        if 'version' in data and not data['version'].strip():
            errors.append("Pack version cannot be empty")
        
        # Validate ontology
        if 'pack_data' in data and 'ontology' in data['pack_data']:
            ontology = data['pack_data']['ontology']
            if not isinstance(ontology, list):
                errors.append("Ontology must be a list of failure modes")
            else:
                codes = set()
                for item in ontology:
                    if not isinstance(item, dict):
                        errors.append("Each ontology item must be an object")
                        continue
                    
                    if 'code' not in item:
                        errors.append("Each ontology item must have a 'code' field")
                    elif item['code'] in codes:
                        errors.append(f"Duplicate ontology code: {item['code']}")
                    else:
                        codes.add(item['code'])
                    
                    if 'label' not in item:
                        errors.append(f"Ontology item {item.get('code', 'unknown')} must have a 'label' field")
        
        # Validate metrics
        if 'pack_data' in data and 'metrics' in data['pack_data']:
            metrics = data['pack_data']['metrics']
            if not isinstance(metrics, list):
                errors.append("Metrics must be a list")
            else:
                keys = set()
                for metric in metrics:
                    if not isinstance(metric, dict):
                        errors.append("Each metric must be an object")
                        continue
                    
                    if 'key' not in metric:
                        errors.append("Each metric must have a 'key' field")
                    elif metric['key'] in keys:
                        errors.append(f"Duplicate metric key: {metric['key']}")
                    else:
                        keys.add(metric['key'])
        
        return jsonify({
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        })
        
    except Exception as e:
        current_app.logger.error(f"Error validating domain pack for {project_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500