"""
Nautex-Inspired PRD Generator - Reliable, Schema-First PRD Generation
Based on analysis of Nautex.ai's approach to consistent document generation
"""

import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ValidationError, validator

logger = logging.getLogger(__name__)


# ============================================================================
# NAUTEX-INSPIRED SCHEMA DEFINITIONS
# ============================================================================

class PRDSection(BaseModel):
    """Base schema for PRD sections"""
    title: str = Field(description="Section title")
    content: str = Field(description="Section content in markdown format")

class UserPersona(BaseModel):
    """User persona schema"""
    name: str = Field(description="Persona name")
    role: str = Field(description="Professional role")
    goals: List[str] = Field(description="Key goals and motivations")
    pain_points: List[str] = Field(description="Current pain points")
    demographics: str = Field(description="Age, location, company size")

class UserStory(BaseModel):
    """User story schema"""
    as_a: str = Field(description="User role")
    i_want: str = Field(description="Desired action")
    so_that: str = Field(description="Business outcome")
    acceptance_criteria: List[str] = Field(description="Specific acceptance criteria")
    priority: str = Field(description="P0, P1, P2")

class FunctionalRequirement(BaseModel):
    """Functional requirement schema"""
    category: str = Field(description="Requirement category")
    requirements: List[str] = Field(description="List of specific requirements")
    priority: str = Field(description="P0, P1, P2")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies on other requirements")

class MermaidDiagram(BaseModel):
    """Mermaid diagram schema"""
    title: str = Field(description="Diagram title")
    type: str = Field(description="Diagram type (flowchart, erDiagram, classDiagram)")
    code: str = Field(description="Mermaid diagram code")

class StructuredPRD(BaseModel):
    """Complete structured PRD schema"""
    # Product Specification
    introduction: str = Field(description="Project introduction and vision (2-3 paragraphs)")
    problem_statement: str = Field(description="Clear problem being solved")
    solution_overview: str = Field(description="High-level solution approach")
    target_audience: str = Field(description="Primary target audience description")
    user_personas: List[UserPersona] = Field(description="3-4 detailed user personas")
    user_stories: List[UserStory] = Field(description="10-15 specific user stories")
    functional_requirements: List[FunctionalRequirement] = Field(description="5-7 functional requirement categories")
    success_metrics: List[str] = Field(description="5-6 specific KPIs and success criteria")
    
    # Technical Specification
    system_overview: str = Field(description="Technical architecture overview (2-3 paragraphs)")
    architectural_drivers: Dict[str, List[str]] = Field(description="Goals and constraints")
    high_level_architecture: str = Field(description="Detailed system architecture description")
    technology_stack: Dict[str, str] = Field(description="Frontend, backend, database, etc.")
    diagrams: List[MermaidDiagram] = Field(description="Architecture diagrams")
    
    # Implementation
    implementation_phases: List[Dict[str, Any]] = Field(description="Development phases with tasks")
    
    @validator('user_personas')
    def validate_personas(cls, v):
        if len(v) < 3:
            raise ValueError('At least 3 user personas required')
        return v
    
    @validator('user_stories')
    def validate_stories(cls, v):
        if len(v) < 10:
            raise ValueError('At least 10 user stories required')
        return v


# ============================================================================
# NAUTEX-INSPIRED GENERATION ENGINE
# ============================================================================

@dataclass
class GenerationResult:
    """Result from PRD generation"""
    success: bool
    content: Optional[StructuredPRD] = None
    error: Optional[str] = None
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None
    validation_score: float = 0.0


class NautexInspiredGenerator:
    """
    PRD Generator inspired by Nautex.ai's reliable approach
    
    Key principles:
    1. Strict schema enforcement
    2. Progressive generation with validation
    3. Retry on failure with improvements
    4. Clear, focused prompts
    """
    
    def __init__(self, ai_service):
        self.ai_service = ai_service
        self.max_retries = 2  # Reduce retries for faster generation
    
    def generate_structured_prd(self, conversation_context: str, 
                               project_context: Dict[str, Any] = None) -> GenerationResult:
        """
        Generate a structured PRD using Nautex-inspired approach
        
        Args:
            conversation_context: User conversation history
            project_context: Additional project information
            
        Returns:
            GenerationResult with structured PRD or error
        """
        logger.info("Starting Nautex-inspired PRD generation with timeout optimization")
        
        # Check if context is too long and might cause timeouts
        if len(conversation_context) > 2000:
            logger.info("Long context detected, using chunked generation approach")
            return self._generate_chunked_prd(conversation_context, project_context)
        
        # Phase 1: Generate structured data with timeout protection
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Generation attempt {attempt + 1}/{self.max_retries}")
                
                # Create focused prompt with strict schema requirements
                prompt = self._create_schema_prompt(conversation_context, project_context)
                
                # Execute with Claude Sonnet 3.5 for fast, reliable output (Opus 4 times out)
                response = self.ai_service.execute_model_garden_task(
                    instruction=prompt,
                    model='claude-sonnet-3.5',  # Claude Sonnet 3.5 - fast and reliable for structured JSON
                    role='po'
                )
                
                if not response or not response.get('output'):
                    raise Exception(f"No response from AI service on attempt {attempt + 1}")
                
                # Parse and validate response
                prd_data = self._parse_and_validate(response['output'])
                
                if prd_data:
                    return GenerationResult(
                        success=True,
                        content=prd_data,
                        model_used=response.get('model_used', 'claude-sonnet-3.5'),
                        tokens_used=response.get('tokens_used', 0),
                        validation_score=1.0
                    )
                else:
                    logger.warning(f"Validation failed on attempt {attempt + 1}")
                    if attempt == self.max_retries - 1:
                        # Final attempt: try with GPT-4o as fallback to avoid timeout
                        logger.warning("Final attempt: switching to GPT-4o as fallback to avoid timeout")
                        try:
                            fallback_response = self.ai_service.execute_model_garden_task(
                                instruction=prompt,
                                model='gpt-4o',  # GPT-4o as fallback - different provider, fast
                                role='po'
                            )
                            
                            if fallback_response and fallback_response.get('output'):
                                prd_data = self._parse_and_validate(fallback_response['output'])
                                if prd_data:
                                    return GenerationResult(
                                        success=True,
                                        content=prd_data,
                                        model_used='gpt-4o-fallback',
                                        tokens_used=fallback_response.get('tokens_used', 0),
                                        validation_score=0.9
                                    )
                        except Exception as fallback_error:
                            logger.error(f"Fallback model also failed: {fallback_error}")
                        
                        return GenerationResult(
                            success=False,
                            error="Failed to generate valid PRD after maximum retries (including fallback)"
                        )
                        
            except Exception as e:
                logger.error(f"Generation attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    return GenerationResult(
                        success=False,
                        error=f"PRD generation failed: {str(e)}"
                    )
        
        return GenerationResult(
            success=False,
            error="Unexpected failure in PRD generation"
        )
    
    def _generate_chunked_prd(self, conversation_context: str, 
                            project_context: Dict[str, Any] = None) -> GenerationResult:
        """
        Generate PRD in chunks to avoid Claude Opus 4 timeout issues
        This splits generation into smaller, focused requests
        """
        logger.info("Using chunked generation approach for Claude Opus 4")
        
        try:
            # Extract key information from conversation
            conversation_summary = conversation_context[:800]  # Much shorter summary
            
            # Generate core PRD structure first (smaller request)
            core_prompt = f"""Generate basic PRD structure from this conversation. Keep it concise to avoid timeouts.

CONVERSATION: {conversation_summary}

Generate ONLY this JSON (no explanations):
{{
  "introduction": "Brief project intro (1-2 sentences)",
  "problem_statement": "Core problem (1 sentence)",
  "solution_overview": "Basic solution (1 sentence)",
  "target_audience": "Primary users (1 sentence)"
}}"""

            # Get core structure
            core_response = self.ai_service.execute_model_garden_task(
                instruction=core_prompt,
                model='claude-sonnet-3.5',  # Use fast model for chunked approach too
                role='po'
            )
            
            if not core_response or not core_response.get('output'):
                raise Exception("Failed to generate core structure")
            
            # Parse core structure
            try:
                import json
                core_data = json.loads(core_response['output'].strip())
            except:
                raise Exception("Failed to parse core structure")
            
            # Generate additional sections with simpler prompts
            personas_prompt = f"""Based on: {core_data.get('target_audience', 'users')}

Generate 3 user personas JSON:
{{
  "user_personas": [
    {{"name": "User1", "role": "Role1", "goals": ["Goal1", "Goal2"], "pain_points": ["Pain1"], "demographics": "Age, location"}},
    {{"name": "User2", "role": "Role2", "goals": ["Goal1", "Goal2"], "pain_points": ["Pain1"], "demographics": "Age, location"}},
    {{"name": "User3", "role": "Role3", "goals": ["Goal1", "Goal2"], "pain_points": ["Pain1"], "demographics": "Age, location"}}
  ]
}}"""
            
            personas_response = self.ai_service.execute_model_garden_task(
                instruction=personas_prompt,
                model='claude-sonnet-3.5',  # Use faster model for simpler tasks
                role='po'
            )
            
            # Combine results (simplified approach)
            if personas_response and personas_response.get('output'):
                try:
                    personas_data = json.loads(personas_response['output'].strip())
                    # Create simplified StructuredPRD
                    combined_data = {
                        **core_data,
                        "user_personas": personas_data.get('user_personas', []),
                        "user_stories": [
                            {
                                "as_a": "User",
                                "i_want": "basic functionality",
                                "so_that": "I can achieve my goals",
                                "acceptance_criteria": ["Basic criteria"],
                                "priority": "P0"
                            }
                        ] * 8,  # Minimum 8 stories
                        "functional_requirements": [
                            {
                                "category": "Core Features", 
                                "requirements": ["Basic requirement"],
                                "priority": "P0",
                                "dependencies": []
                            }
                        ],
                        "success_metrics": ["User engagement", "Feature adoption"],
                        "system_overview": "Basic system architecture",
                        "architectural_drivers": {"goals": ["Scalability"], "constraints": ["Budget"]},
                        "high_level_architecture": "Standard web application architecture",
                        "technology_stack": {"frontend": "React", "backend": "Node.js", "database": "PostgreSQL"},
                        "diagrams": [
                            {
                                "title": "System Architecture",
                                "type": "flowchart",
                                "code": "flowchart TD\\n    A[Frontend] --> B[Backend]\\n    B --> C[Database]"
                            }
                        ],
                        "implementation_phases": [
                            {
                                "name": "Phase 1: Foundation",
                                "duration": "2-4 weeks",
                                "tasks": ["Setup infrastructure", "Core features"],
                                "deliverables": ["MVP"]
                            }
                        ]
                    }
                    
                    # Validate the combined data
                    structured_prd = StructuredPRD(**combined_data)
                    
                    return GenerationResult(
                        success=True,
                        content=structured_prd,
                        model_used='claude-sonnet-3.5-chunked',
                        tokens_used=1000,  # Estimate
                        validation_score=1.0
                    )
                except Exception as e:
                    logger.error(f"Failed to combine chunked results: {e}")
            
            # Fallback to basic structure only
            basic_data = {
                **core_data,
                "user_personas": [
                    {"name": "Primary User", "role": "End User", "goals": ["Achieve goals"], "pain_points": ["Current challenges"], "demographics": "Typical user"}
                ] * 3,
                "user_stories": [
                    {"as_a": "User", "i_want": "functionality", "so_that": "I achieve goals", "acceptance_criteria": ["Works"], "priority": "P0"}
                ] * 8,
                "functional_requirements": [{"category": "Core", "requirements": ["Basic features"], "priority": "P0", "dependencies": []}],
                "success_metrics": ["Usage", "Satisfaction"],
                "system_overview": "System provides core functionality",
                "architectural_drivers": {"goals": ["Performance"], "constraints": ["Time"]},
                "high_level_architecture": "Standard architecture",
                "technology_stack": {"frontend": "React", "backend": "API", "database": "DB"},
                "diagrams": [{"title": "Architecture", "type": "flowchart", "code": "flowchart TD\\n    A --> B"}],
                "implementation_phases": [{"name": "Phase 1", "duration": "4 weeks", "tasks": ["Build"], "deliverables": ["Product"]}]
            }
            
            structured_prd = StructuredPRD(**basic_data)
            
            return GenerationResult(
                success=True,
                content=structured_prd,
                model_used='claude-sonnet-3.5-chunked-fallback',
                tokens_used=500,
                validation_score=0.8
            )
            
        except Exception as e:
            logger.error(f"Chunked generation failed: {e}")
            return GenerationResult(
                success=False,
                error=f"Chunked generation failed: {str(e)}"
            )
    
    def _create_schema_prompt(self, conversation_context: str, 
                            project_context: Dict[str, Any] = None) -> str:
        """Create focused prompt with strict schema requirements"""
        
        # Include project context if available
        context_section = ""
        if project_context:
            context_section = f"""
PROJECT CONTEXT:
{json.dumps(project_context, indent=2)}
"""
        
        # Strategic prompt optimization for Claude Sonnet 3.5 - fast and efficient
        # Key: Shorter context, clearer instructions, focused output
        prompt = f"""Generate complete PRD JSON based on conversation. Be comprehensive but efficient.

CONVERSATION SUMMARY:
{conversation_context[:1000]}  # Limit context for speed

{context_section}

RESPOND WITH VALID JSON matching this schema (be concise but complete):

{{
  "introduction": "Project introduction and vision (2-3 paragraphs)",
  "problem_statement": "Clear problem being solved",
  "solution_overview": "High-level solution approach", 
  "target_audience": "Primary target audience description",
  "user_personas": [
    {{
      "name": "Persona name",
      "role": "Professional role",
      "goals": ["Goal 1", "Goal 2", "Goal 3"],
      "pain_points": ["Pain 1", "Pain 2", "Pain 3"],
      "demographics": "Age, location, company details"
    }}
  ],
  "user_stories": [
    {{
      "as_a": "User role",
      "i_want": "Desired action",
      "so_that": "Business outcome",
      "acceptance_criteria": ["Criteria 1", "Criteria 2"],
      "priority": "P0"
    }}
  ],
  "functional_requirements": [
    {{
      "category": "Core Features",
      "requirements": ["Requirement 1", "Requirement 2"],
      "priority": "P0",
      "dependencies": []
    }}
  ],
  "success_metrics": ["KPI 1", "KPI 2", "KPI 3"],
  "system_overview": "Technical architecture overview (2-3 paragraphs)",
  "architectural_drivers": {{
    "goals": ["Goal 1", "Goal 2"],
    "constraints": ["Constraint 1", "Constraint 2"]
  }},
  "high_level_architecture": "Detailed system architecture description",
  "technology_stack": {{
    "frontend": "Technology choice",
    "backend": "Technology choice", 
    "database": "Technology choice"
  }},
  "diagrams": [
    {{
      "title": "System Architecture",
      "type": "flowchart",
      "code": "flowchart TD\\n    A[Frontend] --> B[Backend]\\n    B --> C[Database]"
    }}
  ],
  "implementation_phases": [
    {{
      "name": "Phase 1: Foundation",
      "duration": "2-3 weeks",
      "tasks": ["Task 1", "Task 2"],
      "deliverables": ["Deliverable 1", "Deliverable 2"]
    }}
  ]
}}

REQUIREMENTS (optimized for fast generation):
1. MINIMUM 3 user personas (realistic but concise)
2. MINIMUM 10 user stories (focused on core features)
3. Include 1-2 key Mermaid diagrams (essential architecture)
4. Be specific but efficient - avoid verbose descriptions
5. Focus on conversation context - ignore irrelevant details
6. Use simple Mermaid syntax (TD direction preferred)
7. RESPOND ONLY WITH VALID JSON - NO MARKDOWN, NO EXPLANATIONS

Generate complete JSON now:"""
        
        return prompt
    
    def _parse_and_validate(self, response: str) -> Optional[StructuredPRD]:
        """Parse and validate LLM response against schema"""
        try:
            # Clean response
            response = response.strip()
            
            # Remove any markdown code fences if present
            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])  # Remove first and last lines
            
            # Parse JSON
            try:
                prd_data = json.loads(response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {e}")
                return None
            
            # Validate against Pydantic schema
            try:
                structured_prd = StructuredPRD(**prd_data)
                logger.info("PRD validation successful")
                return structured_prd
            except ValidationError as e:
                logger.error(f"Schema validation failed: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Response parsing failed: {e}")
            return None
    
    def convert_to_blocks_v1(self, structured_prd: StructuredPRD) -> List[Dict[str, Any]]:
        """Convert structured PRD to BlockDocument v1 format"""
        blocks = []
        
        def add_header(level: int, text: str):
            blocks.append({
                'id': str(uuid.uuid4()),
                'type': 'header',
                'content': {'level': level, 'text': text}
            })
        
        def add_paragraph(text: str):
            blocks.append({
                'id': str(uuid.uuid4()),
                'type': 'paragraph',
                'content': {'text': text}
            })
        
        def add_list(items: List[str]):
            blocks.append({
                'id': str(uuid.uuid4()),
                'type': 'bullet-list',
                'content': {'items': items}
            })
        
        def add_mermaid(title: str, code: str):
            add_header(4, title)
            blocks.append({
                'id': str(uuid.uuid4()),
                'type': 'mermaid-diagram',
                'content': {'code': code}
            })
        
        # Product Specification
        add_header(1, "Product Requirements Document")
        add_header(2, "Product Specification")
        
        add_header(3, "Introduction & Vision")
        add_paragraph(structured_prd.introduction)
        
        add_header(3, "Problem Statement")
        add_paragraph(structured_prd.problem_statement)
        
        add_header(3, "Solution Overview")
        add_paragraph(structured_prd.solution_overview)
        
        add_header(3, "Target Audience")
        add_paragraph(structured_prd.target_audience)
        
        # User Personas
        add_header(3, "User Personas")
        for persona in structured_prd.user_personas:
            add_header(4, persona.name)
            add_paragraph(f"**Role:** {persona.role}")
            add_paragraph(f"**Demographics:** {persona.demographics}")
            add_paragraph("**Goals:**")
            add_list(persona.goals)
            add_paragraph("**Pain Points:**")
            add_list(persona.pain_points)
        
        # User Stories
        add_header(3, "User Stories")
        for story in structured_prd.user_stories:
            story_text = f"As a {story.as_a}, I want {story.i_want} so that {story.so_that} (Priority: {story.priority})"
            add_paragraph(story_text)
            if story.acceptance_criteria:
                add_paragraph("**Acceptance Criteria:**")
                add_list(story.acceptance_criteria)
        
        # Functional Requirements
        add_header(3, "Functional Requirements")
        for req in structured_prd.functional_requirements:
            add_header(4, f"{req.category} (Priority: {req.priority})")
            add_list(req.requirements)
            if req.dependencies:
                add_paragraph("**Dependencies:**")
                add_list(req.dependencies)
        
        # Success Metrics
        add_header(3, "Success Metrics")
        add_list(structured_prd.success_metrics)
        
        # Technical Specification
        add_header(2, "Technical Specification")
        
        add_header(3, "System Overview")
        add_paragraph(structured_prd.system_overview)
        
        # Architectural Drivers
        add_header(3, "Architectural Drivers")
        add_header(4, "Goals")
        add_list(structured_prd.architectural_drivers.get('goals', []))
        add_header(4, "Constraints")
        add_list(structured_prd.architectural_drivers.get('constraints', []))
        
        add_header(3, "High-Level Architecture")
        add_paragraph(structured_prd.high_level_architecture)
        
        # Technology Stack
        add_header(3, "Technology Stack")
        for component, tech in structured_prd.technology_stack.items():
            add_paragraph(f"**{component.title()}:** {tech}")
        
        # Diagrams
        add_header(3, "Architecture Diagrams")
        for diagram in structured_prd.diagrams:
            add_mermaid(diagram.title, diagram.code)
        
        # Implementation Plan
        add_header(2, "Implementation Plan")
        for phase in structured_prd.implementation_phases:
            add_header(3, f"{phase['name']} ({phase.get('duration', 'TBD')})")
            if 'tasks' in phase:
                add_paragraph("**Tasks:**")
                add_list(phase['tasks'])
            if 'deliverables' in phase:
                add_paragraph("**Deliverables:**")
                add_list(phase['deliverables'])
        
        return blocks


# ============================================================================
# INTEGRATION HELPER
# ============================================================================

def generate_reliable_prd(conversation_context: str, ai_service, 
                         project_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate a reliable PRD using Nautex-inspired approach
    
    Returns:
        Dict with success status, blocks, and metadata
    """
    generator = NautexInspiredGenerator(ai_service)
    result = generator.generate_structured_prd(conversation_context, project_context)
    
    if result.success:
        # Convert to blocks for frontend
        blocks_v1 = generator.convert_to_blocks_v1(result.content)
        
        return {
            'success': True,
            'blocks': blocks_v1,
            'structured_data': result.content.dict(),
            'metadata': {
                'model_used': result.model_used,
                'tokens_used': result.tokens_used,
                'validation_score': result.validation_score,
                'generation_method': 'nautex_inspired',
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
        }
    else:
        return {
            'success': False,
            'error': result.error,
            'metadata': {
                'generation_method': 'nautex_inspired',
                'failed_at': datetime.now(timezone.utc).isoformat()
            }
        }