#!/usr/bin/env python3
"""
Test script to verify Domain Pack structure creation functionality.
"""

import sys
import os
import shutil
sys.path.append('src')

from adi.services.domain_pack_structure import (
    create_domain_pack_structure,
    create_complete_domain_pack,
    get_domain_pack_file_structure
)
from adi.services.domain_pack_validator import DomainPackValidator

def main():
    print("Testing Domain Pack Structure Creation...")
    print("=" * 50)
    
    # Test creating a basic structure
    test_pack_id = "test-pack"
    test_root = "test-domain-packs"
    
    # Clean up any existing test directory
    if os.path.exists(test_root):
        shutil.rmtree(test_root)
    
    print(f"Creating basic structure for pack: {test_pack_id}")
    pack_path = create_domain_pack_structure(test_pack_id, test_root)
    print(f"✓ Created pack directory: {pack_path}")
    
    # List created directories
    for item in pack_path.iterdir():
        if item.is_dir():
            print(f"  📁 {item.name}/")
        else:
            print(f"  📄 {item.name}")
    
    print()
    
    # Test creating a complete domain pack
    complete_pack_id = "complete-test-pack"
    print(f"Creating complete domain pack: {complete_pack_id}")
    complete_pack_path = create_complete_domain_pack(
        pack_id=complete_pack_id,
        pack_name="Complete Test Pack",
        pack_version="1.0.0",
        owner_team="test-team",
        description="A complete test domain pack with all files",
        domain_packs_root=test_root
    )
    print(f"✓ Created complete pack: {complete_pack_path}")
    
    # List all created files recursively
    def list_files(path, indent=0):
        items = sorted(path.iterdir())
        for item in items:
            prefix = "  " * indent
            if item.is_dir():
                print(f"{prefix}📁 {item.name}/")
                list_files(item, indent + 1)
            else:
                print(f"{prefix}📄 {item.name}")
    
    list_files(complete_pack_path)
    print()
    
    # Test validation of the created pack
    print("Validating created domain pack...")
    validator = DomainPackValidator(test_root)
    
    try:
        result = validator.validate_complete_pack(complete_pack_id)
        print("✓ Validation passed!")
        print(f"  Pack name: {result['pack_config'].pack.name}")
        print(f"  Pack version: {result['pack_config'].pack.version}")
        print(f"  Failure modes: {len(result['ontology'])}")
        print(f"  North-star metrics: {len(result['metrics'].north_star)}")
        print(f"  Supporting metrics: {len(result['metrics'].supporting)}")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
    
    print()
    
    # Show expected file structure
    print("Expected Domain Pack File Structure:")
    print("-" * 40)
    structure = get_domain_pack_file_structure()
    for file_path, description in structure.items():
        print(f"  {file_path:<25} - {description}")
    
    # Clean up test directories
    print(f"\nCleaning up test directory: {test_root}")
    shutil.rmtree(test_root)
    print("✓ Cleanup complete")

if __name__ == "__main__":
    main()