#!/usr/bin/env python3
"""
Test script for work order generation service
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.services.work_order_generation_service import WorkOrderGenerationService
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_markdown_parsing():
    """Test parsing tasks from markdown content"""
    service = WorkOrderGenerationService()
    
    # Sample tasks.md content
    tasks_content = """# Implementation Plan

- [ ] 1. Setup React Frontend Infrastructure with Modern Tooling Stack
  - Create directory structure for models, services, repositories, and API components
  - Define interfaces that establish system boundaries
  - _Requirements: 1.1_

- [ ] 2. Implement Wine Post Creation API Endpoint with Photo Upload Support
  - Write TypeScript interfaces for all data models
  - Implement validation functions for data integrity
  - _Requirements: 2.1, 3.3, 1.2_

- [ ] 2.1 Create core data model interfaces and types
  - Write User class with validation methods
  - Create unit tests for User model validation
  - _Requirements: 1.2_

- [ ] 3. Build Wine Post Creation Form Component
  - Code Document class with relationship handling
  - Write unit tests for relationship management
  - _Requirements: 2.1, 3.3, 1.2_
"""
    
    parsed_tasks = service._parse_tasks_from_markdown(tasks_content)
    
    print(f"Parsed {len(parsed_tasks)} tasks:")
    for i, task in enumerate(parsed_tasks):
        print(f"\nTask {i+1}:")
        print(f"  Number: {task.get('task_number')}")
        print(f"  Title: {task.get('title')}")
        print(f"  Details: {len(task.get('details', []))} items")
        print(f"  Requirements: {task.get('requirements_refs')}")

def test_work_order_context():
    """Test work order context preparation"""
    service = WorkOrderGenerationService()
    
    # Mock data
    task_data = {
        'task_number': '2',
        'title': 'Implement Wine Post Creation API Endpoint with Photo Upload Support',
        'details': [
            'Write TypeScript interfaces for all data models',
            'Implement validation functions for data integrity',
            '_Requirements: 2.1, 3.3, 1.2_'
        ],
        'requirements_refs': ['2.1', '3.3', '1.2']
    }
    
    # Mock artifacts (would normally come from database)
    class MockArtifact:
        def __init__(self, content):
            self.content = content
    
    artifacts = {
        'requirements': MockArtifact("# Requirements\n\n## Requirement 2.1\nAPI endpoint requirements..."),
        'design': MockArtifact("# Design\n\n## API Design\nRESTful API design...")
    }
    
    # Mock project
    class MockProject:
        def __init__(self):
            self.name = "Wine Sharing Platform"
            self.repo_url = "https://github.com/example/wine-platform"
    
    project = MockProject()
    
    context = service._prepare_work_order_context(task_data, artifacts, project)
    
    print("Generated context:")
    print(context[:500] + "..." if len(context) > 500 else context)

def test_comprehensive_work_order_generation():
    """Test comprehensive work order generation (Step 1)"""
    service = WorkOrderGenerationService()
    
    # Mock data
    task_data = {
        'task_number': '2',
        'title': 'Implement Wine Post Creation API Endpoint with Photo Upload Support',
        'details': [
            'Write TypeScript interfaces for all data models',
            'Implement validation functions for data integrity',
            '_Requirements: 2.1, 3.3, 1.2_'
        ],
        'requirements_refs': ['2.1', '3.3', '1.2']
    }
    
    # Mock artifacts
    class MockArtifact:
        def __init__(self, content):
            self.content = content
    
    artifacts = {
        'requirements': MockArtifact("# Requirements\n\n## Requirement 2.1\nAPI endpoint requirements..."),
        'design': MockArtifact("# Design\n\n## API Design\nRESTful API design...")
    }
    
    # Mock project
    class MockProject:
        def __init__(self):
            self.name = "Wine Sharing Platform"
            self.repo_url = "https://github.com/example/wine-platform"
    
    project = MockProject()
    
    # Test comprehensive work order generation (will fallback to basic extraction since no AI)
    work_order = service._generate_basic_work_order(task_data, artifacts, project, "spec_123", "proj_456")
    
    print("Generated comprehensive work order:")
    if work_order:
        print(f"  Title: {work_order.title}")
        print(f"  Status: {work_order.status}")
        print(f"  Category: {work_order.category}")
        print(f"  Purpose: {work_order.purpose}")
        print(f"  Requirements: {len(work_order.requirements)} items")
        print(f"  Out of Scope: {len(work_order.out_of_scope or [])} items")
        print(f"  Blueprint Context: {'Present' if work_order.blueprint_context else 'None'}")
        print(f"  PRD Context: {'Present' if work_order.prd_context else 'None'}")
        print(f"  Implementation Plan: {'None' if not work_order.implementation_plan else 'Present'}")
    else:
        print("  Failed to generate work order")

def test_comprehensive_work_order_prompt():
    """Test comprehensive work order prompt generation"""
    service = WorkOrderGenerationService()
    
    task_data = {
        'task_number': '2',
        'title': 'Implement Wine Post Creation API Endpoint with Photo Upload Support',
        'description': 'Create a RESTful API endpoint for wine post creation',
        'details': ['API validation', 'Photo upload handling']
    }
    
    context = "=== PROJECT CONTEXT ===\nWine sharing platform with React frontend and Python backend"
    
    prompt = service._create_comprehensive_work_order_prompt(task_data, context)
    
    print("Generated comprehensive work order prompt:")
    print(prompt[:800] + "..." if len(prompt) > 800 else prompt)

def test_implementation_plan_prompt():
    """Test implementation plan prompt generation (Step 2)"""
    service = WorkOrderGenerationService()
    
    task_data = {
        'task_number': '2',
        'title': 'Implement Wine Post Creation API Endpoint with Photo Upload Support',
        'description': 'Create a RESTful API endpoint for wine post creation',
        'details': ['API validation', 'Photo upload handling']
    }
    
    context = "=== PROJECT CONTEXT ===\nWine sharing platform with React frontend and Python backend"
    
    prompt = service._create_implementation_plan_prompt(task_data, context)
    
    print("Generated implementation plan prompt:")
    print(prompt[:800] + "..." if len(prompt) > 800 else prompt)

if __name__ == "__main__":
    print("Testing Work Order Generation Service")
    print("=" * 50)
    
    print("\n1. Testing markdown parsing:")
    test_markdown_parsing()
    
    print("\n2. Testing context preparation:")
    test_work_order_context()
    
    print("\n3. Testing comprehensive work order generation:")
    test_comprehensive_work_order_generation()
    
    print("\n4. Testing comprehensive work order prompt generation:")
    test_comprehensive_work_order_prompt()
    
    print("\n5. Testing implementation plan prompt generation:")
    test_implementation_plan_prompt()
    
    print("\nAll tests completed!")