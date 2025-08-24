#!/usr/bin/env python3
"""
Test script to validate the existing IRR domain pack with our new Pydantic schemas.
"""

import sys
import os
sys.path.append('src')

from adi.services.domain_pack_validator import DomainPackValidator, DomainPackValidationError

def main():
    print("Testing Domain Pack Validation...")
    print("=" * 50)
    
    validator = DomainPackValidator("domain-packs")
    
    # List available packs
    print("Available domain packs:")
    packs = validator.list_available_packs()
    for pack in packs:
        print(f"  - {pack}")
    print()
    
    if not packs:
        print("No domain packs found!")
        return
    
    # Test validation on each pack
    for pack_id in packs:
        print(f"Validating pack: {pack_id}")
        print("-" * 30)
        
        try:
            # Test structure validation
            structure_result = validator.validate_pack_structure(pack_id)
            print("✓ Structure validation passed")
            print(f"  Required files: {structure_result['required_files']}")
            print(f"  Optional directories: {structure_result['optional_directories']}")
            
            # Test content validation
            content_result = validator.validate_pack_files(pack_id)
            print("✓ Content validation passed")
            
            pack_config = content_result['pack_config']
            print(f"  Pack name: {pack_config.pack.name}")
            print(f"  Pack version: {pack_config.pack.version}")
            print(f"  Owner team: {pack_config.pack.owner_team}")
            
            ontology = content_result['ontology']
            print(f"  Failure modes: {len(ontology)}")
            
            metrics = content_result['metrics']
            print(f"  North-star metrics: {len(metrics.north_star)}")
            print(f"  Supporting metrics: {len(metrics.supporting)}")
            
            print("✓ Complete validation passed")
            
        except DomainPackValidationError as e:
            print(f"✗ Validation failed: {e}")
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
        
        print()

if __name__ == "__main__":
    main()