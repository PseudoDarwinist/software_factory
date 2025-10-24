"""
Template Loader - Loads and manages PRD templates
Handles loading of comprehensive PRD templates with validation and caching
"""

import logging
import os
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class TemplateLoader:
    """
    Loads and manages PRD templates from the templates directory
    
    Provides template loading, validation, and caching functionality
    for the PRD generation system.
    """
    
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)
        self._template_cache = {}
        self._last_loaded = {}
        
        # Ensure templates directory exists
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory {templates_dir} does not exist")
    
    def load_comprehensive_template(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load the comprehensive PRD template
        
        Args:
            force_reload: Force reload from disk even if cached
            
        Returns:
            Dict containing template structure and content
        """
        template_path = self.templates_dir / "comprehensive_prd_template.md"
        cache_key = "comprehensive_prd_template"
        
        # Check cache first
        if not force_reload and cache_key in self._template_cache:
            # Check if file has been modified
            if template_path.exists():
                file_mtime = template_path.stat().st_mtime
                cached_mtime = self._last_loaded.get(cache_key, 0)
                
                if file_mtime <= cached_mtime:
                    logger.debug("Using cached comprehensive PRD template")
                    return self._template_cache[cache_key]
        
        # Load template from file
        try:
            if not template_path.exists():
                logger.warning(f"Template file {template_path} not found, using default template")
                return self._get_default_template()
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Parse template structure
            parsed_template = self._parse_template(template_content)
            
            # Validate template
            if not self._validate_template(parsed_template):
                logger.warning("Template validation failed, using default template")
                return self._get_default_template()
            
            # Cache the template
            self._template_cache[cache_key] = parsed_template
            self._last_loaded[cache_key] = template_path.stat().st_mtime
            
            logger.info(f"Loaded comprehensive PRD template from {template_path}")
            return parsed_template
            
        except Exception as e:
            logger.error(f"Failed to load template from {template_path}: {e}")
            return self._get_default_template()
    
    def _parse_template(self, content: str) -> Dict[str, Any]:
        """
        Parse template content into structured format
        
        Args:
            content: Raw template content
            
        Returns:
            Parsed template structure
        """
        template = {
            'version': '1.0',
            'content': content,
            'sections': [],
            'placeholders': [],
            'mermaid_diagrams': [],
            'metadata': {
                'parsed_at': datetime.now().isoformat(),
                'total_sections': 0,
                'total_placeholders': 0,
                'total_diagrams': 0
            }
        }
        
        try:
            # Extract sections (headers)
            sections = self._extract_sections(content)
            template['sections'] = sections
            template['metadata']['total_sections'] = len(sections)
            
            # Extract placeholders
            placeholders = self._extract_placeholders(content)
            template['placeholders'] = placeholders
            template['metadata']['total_placeholders'] = len(placeholders)
            
            # Extract Mermaid diagram locations
            diagrams = self._extract_mermaid_locations(content)
            template['mermaid_diagrams'] = diagrams
            template['metadata']['total_diagrams'] = len(diagrams)
            
            logger.debug(f"Parsed template: {len(sections)} sections, {len(placeholders)} placeholders, {len(diagrams)} diagrams")
            
        except Exception as e:
            logger.error(f"Error parsing template: {e}")
        
        return template
    
    def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """Extract section headers from template content"""
        sections = []
        
        # Find all markdown headers
        header_pattern = r'^(#{1,6})\s+(.+)$'
        
        for match in re.finditer(header_pattern, content, re.MULTILINE):
            level = len(match.group(1))
            title = match.group(2).strip()
            
            sections.append({
                'level': level,
                'title': title,
                'position': match.start(),
                'type': self._classify_section(title)
            })
        
        return sections
    
    def _classify_section(self, title: str) -> str:
        """Classify section type based on title"""
        title_lower = title.lower()
        
        if any(keyword in title_lower for keyword in ['introduction', 'vision', 'overview']):
            return 'introduction'
        elif any(keyword in title_lower for keyword in ['audience', 'persona', 'user']):
            return 'audience'
        elif any(keyword in title_lower for keyword in ['stories', 'use case', 'scenario']):
            return 'user_stories'
        elif any(keyword in title_lower for keyword in ['functional', 'requirement']):
            return 'functional_requirements'
        elif any(keyword in title_lower for keyword in ['technical', 'architecture', 'system']):
            return 'technical_spec'
        elif any(keyword in title_lower for keyword in ['implementation', 'plan', 'phase']):
            return 'implementation'
        elif any(keyword in title_lower for keyword in ['diagram', 'erd', 'class']):
            return 'diagram'
        else:
            return 'general'
    
    def _extract_placeholders(self, content: str) -> List[Dict[str, Any]]:
        """Extract AI generation placeholders from template"""
        placeholders = []
        
        # Find placeholders in square brackets
        placeholder_pattern = r'\[([^\]]+)\]'
        
        for match in re.finditer(placeholder_pattern, content):
            placeholder_text = match.group(1)
            
            # Skip markdown links and other non-placeholder brackets
            if not placeholder_text.startswith('AI will') and 'generate' not in placeholder_text.lower():
                continue
            
            placeholders.append({
                'text': placeholder_text,
                'position': match.start(),
                'type': self._classify_placeholder(placeholder_text)
            })
        
        return placeholders
    
    def _classify_placeholder(self, text: str) -> str:
        """Classify placeholder type based on content"""
        text_lower = text.lower()
        
        if 'diagram' in text_lower or 'mermaid' in text_lower:
            return 'diagram'
        elif 'code' in text_lower or 'example' in text_lower:
            return 'code'
        elif 'requirement' in text_lower:
            return 'requirements'
        elif 'persona' in text_lower or 'user' in text_lower:
            return 'user_content'
        elif 'technical' in text_lower or 'architecture' in text_lower:
            return 'technical'
        else:
            return 'content'
    
    def _extract_mermaid_locations(self, content: str) -> List[Dict[str, Any]]:
        """Extract Mermaid diagram code block locations"""
        diagrams = []
        
        # Find Mermaid code blocks
        mermaid_pattern = r'```mermaid\s*\n(.*?)\n```'
        
        for match in re.finditer(mermaid_pattern, content, re.DOTALL):
            diagram_content = match.group(1).strip()
            
            diagrams.append({
                'content': diagram_content,
                'position': match.start(),
                'type': self._classify_mermaid_diagram(diagram_content)
            })
        
        return diagrams
    
    def _classify_mermaid_diagram(self, content: str) -> str:
        """Classify Mermaid diagram type based on content"""
        content_lower = content.lower()
        
        if 'flowchart' in content_lower or 'graph' in content_lower:
            return 'flowchart'
        elif 'erdiagram' in content_lower or 'er' in content_lower:
            return 'erd'
        elif 'classdiagram' in content_lower or 'class' in content_lower:
            return 'class'
        elif 'sequencediagram' in content_lower or 'sequence' in content_lower:
            return 'sequence'
        else:
            return 'unknown'
    
    def _validate_template(self, template: Dict[str, Any]) -> bool:
        """
        Validate template structure and content
        
        Args:
            template: Parsed template to validate
            
        Returns:
            True if template is valid, False otherwise
        """
        try:
            # Check required fields
            required_fields = ['content', 'sections', 'placeholders', 'metadata']
            for field in required_fields:
                if field not in template:
                    logger.error(f"Template missing required field: {field}")
                    return False
            
            # Check minimum sections
            sections = template['sections']
            if len(sections) < 5:
                logger.warning(f"Template has only {len(sections)} sections, expected at least 5")
            
            # Check for key section types
            section_types = {section['type'] for section in sections}
            required_types = {'introduction', 'technical_spec', 'implementation'}
            
            missing_types = required_types - section_types
            if missing_types:
                logger.warning(f"Template missing section types: {missing_types}")
            
            # Check content length
            if len(template['content']) < 1000:
                logger.warning("Template content seems too short")
            
            logger.debug("Template validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Template validation error: {e}")
            return False
    
    def _get_default_template(self) -> Dict[str, Any]:
        """
        Get default template when file loading fails
        
        Returns:
            Default template structure
        """
        default_content = """# Comprehensive PRD Template

## Product Specification

### Introduction & Vision
[AI will generate comprehensive introduction and vision statement]

### Target Audience & User Personas
[AI will generate detailed user personas with characteristics, goals, and motivations]

### User Stories / Use Cases
[AI will generate specific user stories and use cases]

### Functional Requirements
[AI will generate detailed functional requirements organized by feature areas]

### Non-Functional Requirements
#### Performance
[AI will generate performance requirements with specific metrics]

#### Reliability
[AI will generate reliability and availability requirements]

#### Security
[AI will generate security requirements and compliance needs]

#### Usability
[AI will generate usability and accessibility requirements]

### Success Metrics
[AI will generate KPIs and success measurements]

## Technical Specification

### System Overview
[AI will generate comprehensive technical architecture overview]

### High-Level Architecture
[AI will generate system architecture description]

#### Components Diagram
```mermaid
[AI will generate appropriate Mermaid diagram]
```

### Data Architecture and Models
[AI will generate data model descriptions]

#### Entity Relationship Diagram (ERD)
```mermaid
[AI will generate ERD diagram]
```

### Component Blueprint & Class Diagram
[AI will generate component architecture details]

#### Class Diagram
```mermaid
[AI will generate class diagram]
```

## Implementation Plan
[AI will generate phased implementation approach]

### Phase 1: Foundation
[AI will generate detailed phase descriptions with tasks and deliverables]

### Phase 2: Core Development
[AI will continue with subsequent phases]
"""
        
        return self._parse_template(default_content)
    
    def get_template_info(self) -> Dict[str, Any]:
        """Get information about available templates"""
        info = {
            'templates_dir': str(self.templates_dir),
            'available_templates': [],
            'cached_templates': list(self._template_cache.keys())
        }
        
        if self.templates_dir.exists():
            for template_file in self.templates_dir.glob("*.md"):
                info['available_templates'].append({
                    'name': template_file.stem,
                    'path': str(template_file),
                    'size': template_file.stat().st_size,
                    'modified': datetime.fromtimestamp(template_file.stat().st_mtime).isoformat()
                })
        
        return info
    
    def clear_cache(self):
        """Clear template cache"""
        self._template_cache.clear()
        self._last_loaded.clear()
        logger.info("Template cache cleared")
    
    def reload_template(self, template_name: str = "comprehensive_prd_template") -> Dict[str, Any]:
        """
        Force reload a specific template
        
        Args:
            template_name: Name of template to reload
            
        Returns:
            Reloaded template
        """
        if template_name == "comprehensive_prd_template":
            return self.load_comprehensive_template(force_reload=True)
        else:
            logger.warning(f"Unknown template: {template_name}")
            return {}


# Global template loader instance
_template_loader: Optional[TemplateLoader] = None


def get_template_loader() -> TemplateLoader:
    """Get the global template loader instance"""
    global _template_loader
    
    if _template_loader is None:
        _template_loader = TemplateLoader()
    
    return _template_loader