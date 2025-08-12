"""
Domain Pack validation service.

Provides functions to validate Domain Pack files and directory structure.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from ..schemas.domain_pack import (
    validate_pack_config,
    validate_ontology, 
    validate_metrics,
    DomainPackSchema
)


class DomainPackValidationError(Exception):
    """Raised when Domain Pack validation fails."""
    pass


class DomainPackValidator:
    """Validates Domain Pack file structure and content."""
    
    REQUIRED_FILES = [
        'pack.yaml',
        'ontology.json', 
        'metrics.yaml'
    ]
    
    OPTIONAL_DIRECTORIES = [
        'policy',
        'validators',
        'evals',
        'mappings'
    ]
    
    def __init__(self, domain_packs_root: str = "domain-packs"):
        self.domain_packs_root = Path(domain_packs_root)
    
    def validate_pack_structure(self, pack_id: str) -> Dict[str, Any]:
        """
        Validate the file structure of a domain pack.
        
        Args:
            pack_id: The domain pack identifier (directory name)
            
        Returns:
            Dict with validation results and file inventory
            
        Raises:
            DomainPackValidationError: If pack structure is invalid
        """
        pack_path = self.domain_packs_root / pack_id
        
        if not pack_path.exists():
            raise DomainPackValidationError(f"Domain pack directory not found: {pack_path}")
        
        if not pack_path.is_dir():
            raise DomainPackValidationError(f"Domain pack path is not a directory: {pack_path}")
        
        # Check required files
        missing_files = []
        found_files = []
        
        for required_file in self.REQUIRED_FILES:
            file_path = pack_path / required_file
            if file_path.exists():
                found_files.append(required_file)
            else:
                missing_files.append(required_file)
        
        if missing_files:
            raise DomainPackValidationError(
                f"Missing required files in pack '{pack_id}': {missing_files}"
            )
        
        # Check optional directories
        found_directories = []
        for optional_dir in self.OPTIONAL_DIRECTORIES:
            dir_path = pack_path / optional_dir
            if dir_path.exists() and dir_path.is_dir():
                found_directories.append(optional_dir)
        
        return {
            'pack_id': pack_id,
            'pack_path': str(pack_path),
            'required_files': found_files,
            'optional_directories': found_directories,
            'valid_structure': True
        }
    
    def validate_pack_files(self, pack_id: str) -> Dict[str, Any]:
        """
        Validate the content of Domain Pack files.
        
        Args:
            pack_id: The domain pack identifier
            
        Returns:
            Dict with validation results and parsed data
            
        Raises:
            DomainPackValidationError: If file content is invalid
        """
        pack_path = self.domain_packs_root / pack_id
        
        # Load and validate pack.yaml
        pack_config_path = pack_path / 'pack.yaml'
        try:
            with open(pack_config_path, 'r') as f:
                pack_data = yaml.safe_load(f)
            pack_config = validate_pack_config(pack_data)
        except Exception as e:
            raise DomainPackValidationError(f"Invalid pack.yaml: {str(e)}")
        
        # Load and validate ontology.json
        ontology_path = pack_path / 'ontology.json'
        try:
            with open(ontology_path, 'r') as f:
                ontology_data = json.load(f)
            ontology = validate_ontology(ontology_data)
        except Exception as e:
            raise DomainPackValidationError(f"Invalid ontology.json: {str(e)}")
        
        # Load and validate metrics.yaml
        metrics_path = pack_path / 'metrics.yaml'
        try:
            with open(metrics_path, 'r') as f:
                metrics_data = yaml.safe_load(f)
            metrics = validate_metrics(metrics_data)
        except Exception as e:
            raise DomainPackValidationError(f"Invalid metrics.yaml: {str(e)}")
        
        # Create complete domain pack schema
        try:
            domain_pack = DomainPackSchema(
                pack_config=pack_config,
                ontology=ontology,
                metrics=metrics
            )
        except Exception as e:
            raise DomainPackValidationError(f"Domain pack validation failed: {str(e)}")
        
        return {
            'pack_id': pack_id,
            'pack_config': pack_config,
            'ontology': ontology,
            'metrics': metrics,
            'domain_pack': domain_pack,
            'valid_content': True
        }
    
    def validate_complete_pack(self, pack_id: str) -> Dict[str, Any]:
        """
        Perform complete validation of a domain pack (structure + content).
        
        Args:
            pack_id: The domain pack identifier
            
        Returns:
            Dict with complete validation results
        """
        # Validate structure first
        structure_result = self.validate_pack_structure(pack_id)
        
        # Then validate content
        content_result = self.validate_pack_files(pack_id)
        
        return {
            **structure_result,
            **content_result,
            'validation_complete': True
        }
    
    def list_available_packs(self) -> List[str]:
        """
        List all available domain packs.
        
        Returns:
            List of domain pack identifiers
        """
        if not self.domain_packs_root.exists():
            return []
        
        packs = []
        for item in self.domain_packs_root.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                packs.append(item.name)
        
        return sorted(packs)
    
    def validate_all_packs(self) -> Dict[str, Dict[str, Any]]:
        """
        Validate all available domain packs.
        
        Returns:
            Dict mapping pack_id to validation results
        """
        results = {}
        packs = self.list_available_packs()
        
        for pack_id in packs:
            try:
                results[pack_id] = self.validate_complete_pack(pack_id)
                results[pack_id]['validation_status'] = 'success'
            except DomainPackValidationError as e:
                results[pack_id] = {
                    'pack_id': pack_id,
                    'validation_status': 'error',
                    'error_message': str(e)
                }
        
        return results


def create_domain_pack_directory(pack_id: str, domain_packs_root: str = "domain-packs") -> Path:
    """
    Create the directory structure for a new domain pack.
    
    Args:
        pack_id: The domain pack identifier
        domain_packs_root: Root directory for domain packs
        
    Returns:
        Path to the created pack directory
    """
    pack_path = Path(domain_packs_root) / pack_id
    pack_path.mkdir(parents=True, exist_ok=True)
    
    # Create optional subdirectories
    for subdir in ['policy', 'validators', 'evals', 'mappings']:
        (pack_path / subdir).mkdir(exist_ok=True)
    
    return pack_path


def validate_domain_pack_files(pack_path: Path) -> Tuple[bool, List[str]]:
    """
    Quick validation of domain pack files in a directory.
    
    Args:
        pack_path: Path to domain pack directory
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check required files exist
    required_files = ['pack.yaml', 'ontology.json', 'metrics.yaml']
    for filename in required_files:
        file_path = pack_path / filename
        if not file_path.exists():
            errors.append(f"Missing required file: {filename}")
    
    if errors:
        return False, errors
    
    # Try to validate file contents
    validator = DomainPackValidator(str(pack_path.parent))
    try:
        validator.validate_pack_files(pack_path.name)
        return True, []
    except DomainPackValidationError as e:
        return False, [str(e)]