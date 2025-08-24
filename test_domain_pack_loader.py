#!/usr/bin/env python3
"""
Test script to verify Domain Pack loader functionality.
"""

import sys
import os
import shutil
sys.path.append('src')

from adi.services.domain_pack_loader import (
    DomainPack, 
    DomainPackManager,
    get_domain_pack,
    DomainPackLoadError
)
from adi.services.domain_pack_structure import create_complete_domain_pack

def main():
    print("Testing Domain Pack Loader...")
    print("=" * 50)
    
    # Setup test environment
    test_root = "test-domain-packs"
    
    # Clean up any existing test directory
    if os.path.exists(test_root):
        shutil.rmtree(test_root)
    
    # Create a _default pack
    print("Creating _default domain pack...")
    create_complete_domain_pack(
        pack_id="_default",
        pack_name="Default Domain Pack",
        pack_version="1.0.0",
        owner_team="platform",
        description="Default fallback domain pack",
        domain_packs_root=test_root
    )
    print("✓ Created _default pack")
    
    # Create a project-specific pack
    print("Creating project-specific domain pack...")
    create_complete_domain_pack(
        pack_id="test-project",
        pack_name="Test Project Pack",
        pack_version="2.0.0",
        owner_team="test-team",
        description="Test project specific pack",
        domain_packs_root=test_root
    )
    print("✓ Created test-project pack")
    
    print()
    
    # Test 1: Load project-specific pack
    print("Test 1: Loading project-specific pack")
    print("-" * 40)
    
    try:
        pack = DomainPack("test-project", domain_packs_root=test_root)
        
        print(f"Pack ID: {pack.pack_id}")
        print(f"Used fallback: {pack.used_fallback}")
        print(f"Pack name: {pack.pack_config.pack.name}")
        print(f"Pack version: {pack.pack_config.pack.version}")
        print(f"Owner team: {pack.pack_config.pack.owner_team}")
        print(f"Failure modes: {len(pack.ontology)}")
        print(f"North-star metrics: {len(pack.metrics.north_star)}")
        print(f"Supporting metrics: {len(pack.metrics.supporting)}")
        
        # Test SLA lookup
        default_sla = pack.get_sla_for_event("ExampleEvent")
        print(f"Default SLA for ExampleEvent: {default_sla}ms")
        
        # Test failure mode lookup
        failure_mode = pack.get_failure_mode_by_code("Time.SLA")
        if failure_mode:
            print(f"Found failure mode: {failure_mode.label}")
        
        print("✓ Project-specific pack loaded successfully")
        
    except Exception as e:
        print(f"✗ Failed to load project-specific pack: {e}")
    
    print()
    
    # Test 2: Load non-existent project (should fallback to _default)
    print("Test 2: Loading non-existent project (fallback test)")
    print("-" * 40)
    
    try:
        pack = DomainPack("non-existent-project", domain_packs_root=test_root)
        
        print(f"Pack ID: {pack.pack_id}")
        print(f"Used fallback: {pack.used_fallback}")
        print(f"Pack name: {pack.pack_config.pack.name}")
        print(f"Pack version: {pack.pack_config.pack.version}")
        
        if pack.used_fallback:
            print("✓ Correctly fell back to _default pack")
        else:
            print("✗ Should have used fallback")
        
    except Exception as e:
        print(f"✗ Failed fallback test: {e}")
    
    print()
    
    # Test 3: Domain Pack Manager
    print("Test 3: Domain Pack Manager")
    print("-" * 40)
    
    try:
        manager = DomainPackManager(domain_packs_root=test_root)
        
        # List available packs
        available_packs = manager.list_available_packs()
        print(f"Available packs: {available_packs}")
        
        # Get pack through manager
        pack1 = manager.get_pack("test-project")
        pack2 = manager.get_pack("test-project")  # Should return cached instance
        
        print(f"Pack instances are same: {pack1 is pack2}")
        
        # Test pack info
        pack_info = pack1.get_pack_info()
        print("Pack info:")
        for key, value in pack_info.items():
            print(f"  {key}: {value}")
        
        print("✓ Domain Pack Manager working correctly")
        
    except Exception as e:
        print(f"✗ Domain Pack Manager test failed: {e}")
    
    print()
    
    # Test 4: Convenience function
    print("Test 4: Convenience function")
    print("-" * 40)
    
    try:
        # This should work without explicitly creating a manager
        pack = get_domain_pack("test-project")
        print(f"Got pack via convenience function: {pack.pack_config.pack.name}")
        print("✓ Convenience function working")
        
    except Exception as e:
        print(f"✗ Convenience function test failed: {e}")
    
    print()
    
    # Test 5: Lazy loading
    print("Test 5: Lazy loading test")
    print("-" * 40)
    
    try:
        pack = DomainPack("test-project", domain_packs_root=test_root)
        
        # Access different components to test lazy loading
        print("Accessing pack_config...")
        config = pack.pack_config
        print(f"  ✓ Pack name: {config.pack.name}")
        
        print("Accessing ontology...")
        ontology = pack.ontology
        print(f"  ✓ Failure modes: {len(ontology)}")
        
        print("Accessing metrics...")
        metrics = pack.metrics
        print(f"  ✓ Total metrics: {len(metrics.north_star) + len(metrics.supporting)}")
        
        print("Accessing rules...")
        rules = pack.rules
        print(f"  ✓ Rules: {len(rules.get('rules', []))}")
        
        print("Accessing knowledge...")
        knowledge = pack.knowledge
        print(f"  ✓ Knowledge length: {len(knowledge)} characters")
        
        print("✓ Lazy loading working correctly")
        
    except Exception as e:
        print(f"✗ Lazy loading test failed: {e}")
    
    # Clean up test directories
    print(f"\nCleaning up test directory: {test_root}")
    shutil.rmtree(test_root)
    print("✓ Cleanup complete")

if __name__ == "__main__":
    main()