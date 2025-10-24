"""
PRD Editor API - Editor.js Integration with Intelligent AI Conversation
Provides REST endpoints specifically for the intelligent PRD editor
"""

import json
import logging
import os
import uuid
import base64
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app, send_file, Response
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ValidationError, root_validator, validator
import io

# Handle both relative and absolute imports
try:
    from ..models import db, PRD, MissionControlProject, UploadSession, FeedItem, Stage, ProductBrief
    from ..services.ai_service import get_ai_service
    from ..services.ai_broker import get_ai_broker
    from ..services.context_aware_ai import get_context_aware_ai
    from ..services.event_bus import get_event_bus
    from ..services.export_service import get_export_service
    from ..core.events import Event, EventType
except ImportError:
    from models import db, PRD, MissionControlProject, UploadSession, FeedItem, Stage, ProductBrief
    from services.ai_service import get_ai_service
    from services.ai_broker import get_ai_broker
    from services.context_aware_ai import get_context_aware_ai
    from services.event_bus import get_event_bus
    from services.export_service import get_export_service
    from core.events import Event, EventType

logger = logging.getLogger(__name__)

# Pydantic models for structured AI responses
class ConversationResponse(BaseModel):
    """Structured response model for AI conversation"""
    question: str = Field(description="The intelligent follow-up question")
    suggestions: List[str] = Field(description="3-5 clickable suggestion options for quick responses")

prd_editor_bp = Blueprint('prd_editor', __name__, url_prefix='/api/prd-editor')


@prd_editor_bp.route('/prds/<prd_id>', methods=['GET'])
def get_prd(prd_id):
    """Get PRD content by ID in Editor.js format"""
    try:
        # Get version parameter if provided
        version = request.args.get('version')
        
        # Try to find the PRD by ID - handle both PRD primary key and session ID
        prd = None
        
        # First try to find by PRD primary key (UUID)
        try:
            prd_uuid = uuid.UUID(prd_id)
            prd = PRD.query.filter_by(id=prd_uuid).first()
        except (ValueError, TypeError):
            # Not a valid UUID, continue to session lookup
            pass
        
        # If not found by primary key, try by session ID (draft_id)
        if not prd:
            if version:
                prd = PRD.get_by_version(prd_id, version)
            else:
                prd = PRD.get_latest_for_session(prd_id)
        

        
        if not prd:
            return jsonify({
                'success': False,
                'error': 'PRD not found and could not create sample'
            }), 404
        
        # Convert markdown content to Editor.js format
        if prd.md_uri:
            editorjs_content = convert_markdown_to_editorjs(prd.md_uri)
        else:
            # Create empty Editor.js structure
            editorjs_content = {
                "time": int(datetime.now().timestamp() * 1000),
                "blocks": [
                    {
                        "id": str(uuid.uuid4()),
                        "type": "header",
                        "data": {"text": "Product Requirements Document", "level": 1}
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "paragraph",
                        "data": {"text": "Start writing your PRD here..."}
                    }
                ],
                "version": "2.28.2"
            }
        
        # Also provide block-document (v1) derived from best available source
        def _derive_blocks_v1() -> List[Dict[str, Any]]:
            # 1) If JSON summary already contains a block document, use it (PRIORITY: AI-generated content)
            try:
                js = prd.get_summary() or {}
                bd = js.get('block_document')
                if (
                    isinstance(bd, dict)
                    and isinstance(bd.get('blocks'), list)
                    and len(bd['blocks']) > 1  # ignore malformed single-paragraph blobs
                ):
                    logger.info(f"Loading PRD {prd.id}: Found {len(bd['blocks'])} persisted blocks from AI generation")
                    return bd['blocks']
                else:
                    logger.info(f"Loading PRD {prd.id}: No valid block document in summary, trying other sources")
            except Exception as e:
                logger.warning(f"Loading PRD {prd.id}: Error reading block document from summary: {e}")
                pass

            # 2) If md_uri looks like JSON, expand directly
            try:
                content = prd.md_uri or ''
                s = _strip_fences_and_normalize(content)
                # Try direct
                if (s.strip().startswith('{') and s.strip().endswith('}')) or (s.strip().startswith('[') and s.strip().endswith(']')):
                    out = _json_to_blocks_v1(s)
                    if out and len(out) > 1:
                        return out
                # Try slicing between first { and last }
                i1 = s.find('{')
                i2 = s.rfind('}')
                if i1 != -1 and i2 > i1:
                    out = _json_to_blocks_v1(s[i1:i2+1])
                    if out and len(out) > 1:
                        return out
            except Exception:
                pass

            # 3) Fallback to Editor.js bridge
            try:
                return editorjs_to_blocks_v1(editorjs_content)
            except Exception as conv_err:
                logger.warning(f"Failed to derive blocks v1 via editorjs: {conv_err}")
                return []

        blocks_v1 = _derive_blocks_v1()

        return jsonify({
            'success': True,
            'data': {
                'id': str(prd.id),
                'title': f'PRD v{prd.version}',
                'editorjs_content': editorjs_content,
                'blocks': blocks_v1,
                'version': prd.version,
                'status': prd.status,
                'created_at': prd.created_at.isoformat() if prd.created_at else None,
                'updated_at': prd.created_at.isoformat() if prd.created_at else None
            }
        })
        
    except Exception as e:
        logger.error(f"Error loading PRD {prd_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to load PRD: {str(e)}'
        }), 500


@prd_editor_bp.route('/prds/<prd_id>', methods=['PUT'])
def update_prd(prd_id):
    """Update PRD content from Editor.js format"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON'
            }), 400
        
        # Find the PRD
        prd = PRD.get_latest_for_session(prd_id)
        if not prd:
            return jsonify({
                'success': False,
                'error': 'PRD not found'
            }), 404
        
        # Extract Editor.js content
        editorjs_content = data.get('content')
        if not editorjs_content:
            return jsonify({
                'success': False,
                'error': 'Content is required'
            }), 400
        
        # Convert Editor.js content back to markdown
        markdown_content = convert_editorjs_to_markdown(editorjs_content)
        
        # Update the PRD
        prd.update_content(md_content=markdown_content)
        
        return jsonify({
            'success': True,
            'data': {
                'id': str(prd.id),
                'message': 'PRD updated successfully'
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating PRD {prd_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to update PRD: {str(e)}'
        }), 500


@prd_editor_bp.route('/save-blocks/<session_id>', methods=['POST'])
def save_prd_blocks(session_id):
    """Save PRD blocks from AI generation/modification with persistence"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON'
            }), 400
        
        blocks = data.get('blocks', [])
        metadata = data.get('metadata', {})
        
        if not blocks:
            return jsonify({
                'success': False,
                'error': 'Blocks are required'
            }), 400
        
        logger.info(f"Saving {len(blocks)} PRD blocks for session {session_id}")
        
        # Find existing PRD or create new one
        prd = PRD.get_latest_for_session(session_id)
        
        # Convert blocks to JSON for storage
        block_document = {
            'blocks': blocks,
            'version': '1.0',
            'source': metadata.get('source', 'ai_generation'),
            'lastModified': metadata.get('lastModified', datetime.now().isoformat()),
            'blockCount': len(blocks)
        }
        
        # Convert blocks to markdown for backward compatibility
        markdown_content = blocks_to_markdown(blocks)
        
        if prd:
            # Update existing PRD
            logger.info(f"Updating existing PRD {prd.id} for session {session_id}")
            
            # Update summary with block document
            summary = prd.get_summary() or {}
            summary.update({
                'block_document': block_document,
                'title': metadata.get('title', extract_title_from_blocks(blocks)),
                'lastModified': metadata.get('lastModified', datetime.now().isoformat()),
                'source': metadata.get('source', 'ai_generation')
            })
            
            prd.update_summary(summary)
            prd.update_content(md_content=markdown_content)
            
            return jsonify({
                'success': True,
                'data': {
                    'prdId': str(prd.id),
                    'sessionId': session_id,
                    'blocksCount': len(blocks),
                    'message': 'PRD blocks saved successfully'
                }
            })
        else:
            # Create new PRD
            logger.info(f"Creating new PRD for session {session_id}")
            
            # Create PRD with block document  
            title = metadata.get('title', extract_title_from_blocks(blocks))
            
            # Use session_id as both project_id and draft_id for simplicity
            new_prd = PRD.create_draft(
                project_id=session_id,
                draft_id=session_id,
                md_content=markdown_content,
                json_summary={
                    'block_document': block_document,
                    'title': title,
                    'lastModified': metadata.get('lastModified', datetime.now().isoformat()),
                    'source': metadata.get('source', 'ai_generation')
                }
            )
            
            db.session.add(new_prd)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'data': {
                    'prdId': str(new_prd.id),
                    'sessionId': session_id,
                    'blocksCount': len(blocks),
                    'message': 'New PRD created and saved successfully'
                }
            })
            
    except Exception as e:
        logger.error(f"Error saving PRD blocks for session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to save PRD blocks: {str(e)}'
        }), 500


def blocks_to_markdown(blocks):
    """Convert block format to markdown for backward compatibility"""
    markdown_lines = []
    
    for block in blocks:
        block_type = block.get('type', 'paragraph')
        content = block.get('content', {})
        
        if block_type == 'header':
            level = content.get('level', 1)
            text = content.get('text', '')
            markdown_lines.append('#' * level + ' ' + text)
            markdown_lines.append('')
        elif block_type == 'paragraph':
            text = content.get('text', '')
            if text.strip():
                markdown_lines.append(text)
                markdown_lines.append('')
        elif block_type == 'mermaid':
            code = content.get('code', '')
            caption = content.get('caption', '')
            markdown_lines.append('```mermaid')
            markdown_lines.append(code)
            markdown_lines.append('```')
            if caption:
                markdown_lines.append(f'*{caption}*')
            markdown_lines.append('')
        elif block_type == 'list':
            items = content.get('items', [])
            for item in items:
                markdown_lines.append(f'- {item}')
            markdown_lines.append('')
    
    return '\n'.join(markdown_lines)


def extract_title_from_blocks(blocks):
    """Extract title from the first header block"""
    for block in blocks:
        if block.get('type') == 'header' and block.get('content', {}).get('level') == 1:
            return block.get('content', {}).get('text', 'Product Requirements Document')
    return 'Product Requirements Document'


@prd_editor_bp.route('/simple-conversation', methods=['POST'])
def simple_conversation():
    """LLM-driven intelligent conversation like the user's example"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
            
        message = data.get('message', '').strip()
        conversation_state = data.get('conversation_state', {})
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Build conversation history for LLM context
        conversation_history = conversation_state.get('history', [])
        
        # Add user's message to history
        conversation_history.append({
            'role': 'user',
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
                    # Create intelligent prompt for LLM with Pydantic schema
        schema = ConversationResponse.model_json_schema()
        
        if len(conversation_history) == 1:
            # First message - start the drilling conversation
            conversation_prompt = f"""USER WANTS TO BUILD: "{message}"

Create an intelligent follow-up question and 4 suggestion options.

RESPOND WITH ONLY THIS JSON FORMAT:
{{
  "question": "Your intelligent follow-up question here",
  "suggestions": [
    "Suggestion option 1",
    "Suggestion option 2", 
    "Suggestion option 3",
    "Suggestion option 4"
  ]
}}

NO OTHER TEXT. ONLY JSON."""
        else:
            # Build context from conversation history
            history_context = ""
            for i, entry in enumerate(conversation_history[:-1]):
                if entry['role'] == 'user':
                    history_context += f"User: {entry['message']}\n"
                elif entry['role'] == 'assistant':
                    history_context += f"Agent: {entry['message']}\n"
            
            conversation_prompt = f"""CONVERSATION:
{history_context}

USER JUST SAID: "{message}"

Ask the NEXT intelligent follow-up question based on their answer.

RESPOND WITH ONLY THIS JSON FORMAT:
{{
  "question": "Your next intelligent question here",
  "suggestions": [
    "Quick response 1",
    "Quick response 2", 
    "Quick response 3",
    "Quick response 4"
  ]
}}

NO OTHER TEXT. ONLY JSON."""

        # Use AI service to generate intelligent question
        ai_service = get_ai_service()
        if not ai_service:
            return jsonify({
                'success': False,
                'error': 'AI service not available'
            }), 503

        try:
            # Use response prefilling to force JSON output
            prefilled_prompt = f"""{conversation_prompt}

I'll respond with exactly this JSON structure:
{{
  "question": "My intelligent follow-up question here",
  "suggestions": [
    "Quick response option 1",
    "Quick response option 2", 
    "Quick response option 3",
    "Quick response option 4"
  ]
}}

Here's my response:
{{"""
            
            # Call AI service with prefilled response start
            ai_response = ai_service.execute_model_garden_task(
                instruction=prefilled_prompt,
                model='claude-sonnet-3-5',
                role='po'
            )
            
            if not ai_response or not ai_response.get('output'):
                raise Exception('AI conversation failed')
            
            ai_output = ai_response['output'].strip()
            
            # Complete the JSON by adding the opening brace back
            if not ai_output.startswith('{'):
                ai_output = '{' + ai_output
            
            # Parse and validate JSON response using Pydantic
            try:
                ai_json = json.loads(ai_output)
                validated_response = ConversationResponse(**ai_json)
                ai_question = validated_response.question
                suggestions = validated_response.suggestions
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.error(f"Raw AI output: {ai_output}")
                raise Exception(f'AI response format invalid: {e}')
            
            # Add AI's question to history
            conversation_history.append({
                'role': 'assistant',
                'message': ai_question,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Update conversation state
            conversation_state['history'] = conversation_history
            conversation_state['stage'] = 'gathering'
            
            # Determine if we should show "Generate Initial Specs" button
            show_generate_button = len(conversation_history) >= 6  # After 3 Q&A pairs
            
            return jsonify({
                'success': True,
                'data': {
                    'message': ai_question,
                    'stage': 'gathering',
                    'next_action': 'continue_conversation',
                    'conversation_state': conversation_state,
                    'suggestions': suggestions,
                    'show_generate_button': show_generate_button,
                    'ai_metadata': {
                        'model_used': ai_response.get('model_used', 'claude-opus-4'),
                        'provider': 'model_garden'
                    }
                }
            })
            
        except Exception as ai_error:
            logger.error(f"AI conversation failed: {ai_error}")
            return jsonify({
                'success': False,
                'error': f'AI conversation failed: {str(ai_error)}'
            }), 503
        
    except Exception as e:
        current_app.logger.error(f"Simple conversation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Conversation processing failed: {str(e)}'
        }), 500


@prd_editor_bp.route('/generate-comprehensive-prd', methods=['POST'])
def generate_comprehensive_prd():
    """Generate comprehensive PRD from conversation history using enhanced orchestrator"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON'
            }), 400
        
        conversation_state = data.get('conversation_state', {})
        conversation_history = conversation_state.get('history', [])
        
        if not conversation_history:
            return jsonify({
                'success': False,
                'error': 'Conversation history is required'
            }), 400
        
        # Build comprehensive context from conversation
        user_responses = []
        for entry in conversation_history:
            if entry['role'] == 'user':
                user_responses.append(entry['message'])
        
        conversation_context = "\n".join([f"User Response {i+1}: {response}" for i, response in enumerate(user_responses)])
        
        # Check if this is modify mode
        mode = data.get('mode', 'create')
        current_content = data.get('current_content')
        
        # Use the new PRD Generation Orchestrator
        try:
            from ..services.nautex_inspired_generator import generate_reliable_prd
            from ..services.ai_service import get_ai_service
        except ImportError:
            # Handle import issues when running from script context
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from services.nautex_inspired_generator import generate_reliable_prd
            from services.ai_service import get_ai_service
            
        ai_service = get_ai_service()
        if not ai_service:
            logger.warning("AI service not available, falling back to original method")
            require_blocks = bool(data.get('require_blocks', True))
            if require_blocks:
                return jsonify({'success': False, 'error': 'AI service not available'}), 503
            return _generate_prd_fallback(conversation_context, mode, current_content)
            
        # Prepare project context
        project_context = {
            'project_id': data.get('project_id', 'conversation-project'),
            'mode': mode,
            'has_current_content': bool(current_content)
        }
            
        if mode == 'modify' and current_content:
            current_text = ""
            if current_content and current_content.get('blocks'):
                for block in current_content['blocks']:
                    if block.get('type') == 'paragraph':
                        current_text += block.get('data', {}).get('text', '') + "\n"
                    elif block.get('type') == 'header':
                        current_text += block.get('data', {}).get('text', '') + "\n"
            
            project_context['current_content'] = current_text[:3000]  # Limit context size
        
        # Generate with reliable Nautex-inspired method
        result = generate_reliable_prd(
            conversation_context=conversation_context,
            ai_service=ai_service,
            project_context=project_context
        )
            
        if result['success']:
            # Nautex-inspired generator already returns properly formatted blocks
            blocks_v1 = result.get('blocks', [])
                
            # Create empty Editor.js structure for backward compatibility
            editorjs_content = {
                "time": int(datetime.now().timestamp() * 1000),
                "blocks": [],  # Empty since we're using blocks_v1 format
                "version": "2.28.2"
            }
            
            # Enforce strict validation requiring blocks by default (task 4.2)
            require_blocks = bool(data.get('require_blocks', True))
            if require_blocks and not blocks_v1:
                return jsonify({
                    'success': False,
                    'error': 'Reliable generator did not produce blocks',
                    'details': {'hint': 'Nautex-inspired generator should always produce BlockDocument v1 format'}
                }), 422

            return jsonify({
                'success': True,
                'data': {
                    'prd_content': 'Generated via Nautex-inspired reliable method',
                    'editorjs_content': editorjs_content,
                    'blocks': blocks_v1,  # Already in proper BlockDocument v1 format
                    'structured_data': result.get('structured_data'),  # Full structured PRD data
                    'prd_id': None,  # Will be assigned when saved
                    'session_id': str(uuid.uuid4()),
                    'generation_metadata': result.get('metadata', {})
                }
            })
        else:
            # Reliable generator failed, fall back to original method
            logger.warning(f"Nautex-inspired generator failed: {result.get('error')}, falling back to original method")
            require_blocks = bool(data.get('require_blocks', True))
            if require_blocks:
                return jsonify({'success': False, 'error': f'Reliable generation failed: {result.get("error")}'}), 503
            return _generate_prd_fallback(conversation_context, mode, current_content)
                
    except ImportError as e:
        logger.warning(f"Could not import nautex_inspired_generator: {e}, using fallback")
        return _generate_prd_fallback(conversation_context, mode, current_content)
    except Exception as e:
        logger.error(f"Error in comprehensive PRD generation: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to process PRD generation request'
        }), 500


def _generate_prd_fallback(conversation_context: str, mode: str = 'create', current_content=None):
    """Fallback PRD generation using original method"""
    try:
        # Load comprehensive PRD template
        template_path = 'templates/comprehensive_prd_template.md'
        try:
            with open(template_path, 'r') as f:
                prd_template = f.read()
        except FileNotFoundError:
            # Fallback template if file not found
            prd_template = """# Project

## Product Specification

### Introduction & Vision
[Comprehensive project overview and vision]

### Target Audience & User Personas
[Detailed user personas with characteristics and goals]

### User Stories / Use Cases
[Specific user scenarios and workflows]

### Functional Requirements
[Detailed system requirements]

### Non-Functional Requirements
[Performance, security, scalability requirements]

### Success Metrics
[KPIs and measurement criteria]

## Technical Specification

### System Overview
[Technical architecture overview]

### High-Level Architecture
[System design and components]

#### Components Diagram
```mermaid
flowchart TD
    A[Component A] --> B[Component B]
    B --> C[Component C]
```

### Data Architecture and Models
[Data models and relationships]

#### Entity Relationship Diagram (ERD)
```mermaid
erDiagram
    USERS ||--o{ PROJECTS : owns
    PROJECTS ||--o{ DOCUMENTS : contains
```

### Implementation Plan
[Phased development approach]"""

        # Create comprehensive PRD generation prompt
        contract_header = (
            "Respond ONLY with a JSON object matching 'BlockDocument v1' schema. "
            "Schema: { meta?: { title?: string, version?: 'v1' }, blocks: Block[] } where Block ∈ { "
            "header{level:1..6,text}, paragraph{text}, bullet-list{items[]}, numbered-list{items[]}, "
            "code{language?,code}, mermaid-diagram{code,diagramType?}, table{header?,rows[][]}, hr{content:null} }. "
            "No prose, no markdown fences, no comments. Use ASCII quotes only."
        )

        if mode == 'modify' and current_content:
            prd_generation_prompt = f"""{contract_header}\n\nMODIFY MODE: Enhance and improve this existing PRD based on the conversation.

CURRENT PRD CONTENT:
{current_content[:3000]}

CONVERSATION CONTEXT:
{conversation_context}

TASK: Generate an ENHANCED version of the PRD that:
1. Keeps all existing good content
2. Adds the improvements discussed in the conversation
3. Makes it as comprehensive and detailed as possible
4. Includes Mermaid diagrams for technical sections
5. Adds missing sections that were discussed

Generate the complete enhanced PRD with all improvements:"""
        else:
            prd_generation_prompt = f"""{contract_header}\n\nBased on this comprehensive conversation about a project, generate an EXTREMELY DETAILED Product Requirements Document (PRD) and Technical Requirements Document (TRD).

CONVERSATION CONTEXT:
{conversation_context}

Generate a comprehensive PRD with the following structure:

## Product Specification
- Introduction & Vision (3-4 detailed paragraphs)
- Target Audience & User Personas (4-5 detailed personas)
- User Stories / Use Cases (15-20 detailed stories)
- Functional Requirements (5-7 major sections)
- Non-Functional Requirements (Performance, Security, etc.)
- Success Metrics (5-6 specific KPIs)

## Technical Specification
- System Overview (technical architecture)
- High-Level Architecture (detailed description)
- Components Diagram (Mermaid flowchart)
- Data Architecture and Models
- Entity Relationship Diagram (Mermaid ERD)
- Class Diagram (Mermaid class diagram)

## Implementation Plan
- Phased development approach with specific tasks

REQUIREMENTS:
1. Generate extremely detailed and comprehensive content
2. Include all Mermaid diagrams with proper syntax
3. Use specific technical details
4. Generate the COMPLETE document

Generate the complete, comprehensive PRD now:"""

        # Use AI service to generate comprehensive PRD
        ai_service = get_ai_service()
        if not ai_service:
            return jsonify({
                'success': False,
                'error': 'AI service not available'
            }), 503

        try:
            ai_response = ai_service.execute_model_garden_task(
                instruction=prd_generation_prompt,
                model='claude-sonnet-3.5',
                role='po'
            )
            
            if not ai_response or not ai_response.get('output'):
                raise Exception('PRD generation failed')
            
            prd_content = ai_response['output']
            
            # Prefer BlockDocument v1 if model followed the contract
            blocks_v1 = []
            try:
                blocks_v1 = validate_block_document_v1(prd_content).get('blocks', [])
            except Exception:
                blocks_v1 = []

            # Convert markdown to Editor.js format if not a block document
            editorjs_content = convert_markdown_to_editorjs(prd_content)
            
            return jsonify({
                'success': True,
                'data': {
                    'prd_content': prd_content,
                    'editorjs_content': editorjs_content,
                    'blocks': blocks_v1,
                    'generation_metadata': {
                        'model_used': ai_response.get('model_used', 'claude-opus-4'),
                        'provider': 'model_garden',
                        'generated_at': datetime.now(timezone.utc).isoformat(),
                        'template_used': 'comprehensive_prd_template',
                        'mode': mode,
                        'fallback': True
                    }
                }
            })
            
        except Exception as ai_error:
            logger.error(f"Fallback PRD generation failed: {ai_error}")
            return jsonify({
                'success': False,
                'error': f'PRD generation failed: {str(ai_error)}'
            }), 503
            
    except Exception as e:
        logger.error(f"Error in fallback PRD generation: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to process PRD generation request'
        }), 500


@prd_editor_bp.route('/modify-conversation', methods=['POST'])
def modify_conversation():
    """Handle conversation for modifying existing PRD"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
            
        message = data.get('message', '').strip()
        conversation_state = data.get('conversation_state', {})
        current_prd_id = data.get('current_prd_id')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get current PRD content for context
        current_prd_content = ""
        if current_prd_id:
            try:
                prd = PRD.get_latest_for_session(current_prd_id)
                if prd and prd.md_uri:
                    current_prd_content = prd.md_uri[:2000]  # Limit context size
            except Exception as e:
                logger.warning(f"Could not load PRD content: {e}")
        
        # Build conversation history
        conversation_history = conversation_state.get('history', [])
        conversation_history.append({
            'role': 'user',
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Create modification-specific prompt
        modification_prompt = f"""You are helping a user improve their existing PRD. 

CURRENT PRD CONTENT (first 2000 chars):
{current_prd_content}

USER REQUEST: "{message}"

CONVERSATION HISTORY:
{chr(10).join([f"{entry['role']}: {entry['message']}" for entry in conversation_history[-5:]])}

Provide a helpful response that:
1. Acknowledges their request
2. Asks a follow-up question to better understand what they want to improve
3. Provides 3-4 specific suggestion options

RESPOND WITH ONLY THIS JSON FORMAT:
{{
  "message": "Your helpful response here",
  "suggestions": [
    "Specific suggestion 1",
    "Specific suggestion 2", 
    "Specific suggestion 3",
    "Specific suggestion 4"
  ]
}}

NO OTHER TEXT. ONLY JSON."""

        # Use AI service
        ai_service = get_ai_service()
        if not ai_service:
            return jsonify({
                'success': False,
                'error': 'AI service not available'
            }), 503

        try:
            ai_response = ai_service.execute_model_garden_task(
                instruction=modification_prompt,
                model='claude-sonnet-3.5',
                role='po'
            )
            
            if not ai_response or not ai_response.get('output'):
                raise Exception('AI conversation failed')
            
            ai_output = ai_response['output'].strip()
            
            # Parse JSON response
            try:
                if not ai_output.startswith('{'):
                    ai_output = '{' + ai_output
                ai_json = json.loads(ai_output)
                ai_message = ai_json.get('message', 'How can I help you improve your PRD?')
                suggestions = ai_json.get('suggestions', [])
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse AI response: {e}")
                ai_message = "How can I help you improve your PRD?"
                suggestions = [
                    'Add more detailed user personas',
                    'Improve technical specifications',
                    'Add implementation timeline',
                    'Enhance success metrics'
                ]
            
            # Add AI response to history
            conversation_history.append({
                'role': 'assistant',
                'message': ai_message,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Update conversation state
            conversation_state['history'] = conversation_history
            conversation_state['stage'] = 'modifying'
            
            return jsonify({
                'success': True,
                'data': {
                    'message': ai_message,
                    'suggestions': suggestions,
                    'conversation_state': conversation_state,
                    'modifications': []
                }
            })
            
        except Exception as ai_error:
            logger.error(f"AI modify conversation failed: {ai_error}")
            return jsonify({
                'success': False,
                'error': f'AI conversation failed: {str(ai_error)}'
            }), 503
        
    except Exception as e:
        logger.error(f"Modify conversation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Conversation processing failed: {str(e)}'
        }), 500


@prd_editor_bp.route('/analyze-current-prd', methods=['POST'])
def analyze_current_prd():
    """Analyze current PRD content and suggest improvements"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
            
        content = data.get('content', {})
        prd_id = data.get('prd_id')
        
        # Extract text content from Editor.js blocks
        text_content = ""
        
        # Handle both old format (content.blocks) and new format (content is array)
        blocks = []
        if isinstance(content, list):
            # New format: content is directly an array of blocks
            blocks = content
        elif isinstance(content, dict) and content.get('blocks'):
            # Old format: content.blocks contains the array
            blocks = content.get('blocks', [])
        elif data.get('blocks'):
            # Alternative format: blocks are directly in data
            blocks = data.get('blocks', [])
        
        for block in blocks:
            if isinstance(block, dict):
                block_type = block.get('type')
                if block_type == 'paragraph':
                    # Handle both Editor.js format and custom format
                    text = block.get('data', {}).get('text') or block.get('content', {}).get('text', '')
                    text_content += text + "\n"
                elif block_type == 'header':
                    # Handle both Editor.js format and custom format  
                    text = block.get('data', {}).get('text') or block.get('content', {}).get('text', '')
                    text_content += text + "\n"
        
        # Create analysis prompt
        analysis_prompt = f"""Analyze this PRD content and suggest specific improvements:

CURRENT PRD CONTENT:
{text_content[:3000]}

Provide analysis and suggestions in this JSON format:
{{
  "message": "Brief analysis of the current PRD and what could be improved",
  "suggestions": [
    "Specific improvement suggestion 1",
    "Specific improvement suggestion 2",
    "Specific improvement suggestion 3",
    "Specific improvement suggestion 4"
  ]
}}

Focus on missing sections, areas that need more detail, or structural improvements."""

        # Use real AI analysis - no more mock mode

        # Use AI service
        ai_service = get_ai_service()
        if not ai_service:
            return jsonify({
                'success': False,
                'error': 'AI service not available'
            }), 503

        try:
            ai_response = ai_service.execute_model_garden_task(
                instruction=analysis_prompt,
                model='claude-sonnet-3.5',  # Use faster model instead of claude-opus-4
                role='po'
            )
            
            if not ai_response or not ai_response.get('output'):
                raise Exception('PRD analysis failed')
            
            ai_output = ai_response['output'].strip()
            
            # Parse JSON response
            try:
                if not ai_output.startswith('{'):
                    ai_output = '{' + ai_output
                ai_json = json.loads(ai_output)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'message': ai_json.get('message', 'I can help you improve your PRD.'),
                        'suggestions': ai_json.get('suggestions', [
                            'Add more detailed user personas',
                            'Improve technical specifications',
                            'Add implementation timeline',
                            'Enhance success metrics'
                        ])
                    }
                })
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse AI analysis: {e}")
                return jsonify({
                    'success': True,
                    'data': {
                        'message': 'I can help you improve your PRD. What specific aspect would you like to enhance?',
                        'suggestions': [
                            'Add more detailed user personas',
                            'Improve technical specifications',
                            'Add implementation timeline',
                            'Enhance success metrics'
                        ]
                    }
                })
            
        except Exception as ai_error:
            logger.error(f"PRD analysis failed: {ai_error}")
            return jsonify({
                'success': False,
                'error': f'PRD analysis failed: {str(ai_error)}'
            }), 503
            
    except Exception as e:
        logger.error(f"Error in PRD analysis: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to analyze PRD'
        }), 500


@prd_editor_bp.route('/generate-additional-section', methods=['POST'])
def generate_additional_section():
    """Generate additional sections like UI/UX, Implementation Plan, etc."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
            
        section_type = data.get('section_type')
        conversation_state = data.get('conversation_state', {})
        current_prd_id = data.get('current_prd_id')
        
        if not section_type:
            return jsonify({'error': 'Section type is required'}), 400
        
        # Define section templates
        section_templates = {
            'ui_ux': """## User Interface / User Experience Requirements

### Design Principles
[AI will generate design principles and guidelines]

### User Interface Specifications
[AI will generate detailed UI specifications]

### User Experience Flow
[AI will generate user journey and experience flow]

### Accessibility Requirements
[AI will generate accessibility and usability requirements]

### Design System
[AI will generate design system specifications]

### Responsive Design
[AI will generate responsive design requirements]""",

            'implementation': """## Implementation Plan

### Development Phases
[AI will generate detailed development phases]

### Phase 1: Foundation
[AI will generate phase 1 details with tasks and timeline]

### Phase 2: Core Features
[AI will generate phase 2 details with tasks and timeline]

### Phase 3: Advanced Features
[AI will generate phase 3 details with tasks and timeline]

### Resource Requirements
[AI will generate team and resource requirements]

### Timeline and Milestones
[AI will generate detailed timeline with milestones]

### Risk Management
[AI will generate implementation risks and mitigation strategies]""",

            'api_specs': """## API Specifications

### REST API Design
[AI will generate REST API design principles]

### Authentication & Authorization
[AI will generate auth specifications]

### API Endpoints
[AI will generate detailed API endpoint specifications]

### Data Models
[AI will generate API data models and schemas]

### Error Handling
[AI will generate error handling specifications]

### Rate Limiting & Security
[AI will generate security and rate limiting specs]""",

            'testing': """## Testing Strategy

### Testing Approach
[AI will generate comprehensive testing approach]

### Unit Testing
[AI will generate unit testing specifications]

### Integration Testing
[AI will generate integration testing requirements]

### End-to-End Testing
[AI will generate E2E testing specifications]

### Performance Testing
[AI will generate performance testing requirements]

### Security Testing
[AI will generate security testing specifications]

### Quality Assurance
[AI will generate QA processes and standards]"""
        }
        
        template = section_templates.get(section_type, "## Additional Section\n[AI will generate relevant content]")
        
        # Build context from conversation
        conversation_context = ""
        if conversation_state.get('history'):
            user_responses = [entry['message'] for entry in conversation_state['history'] if entry['role'] == 'user']
            conversation_context = "\n".join([f"User Response {i+1}: {response}" for i, response in enumerate(user_responses)])
        
        # Create section generation prompt
        section_names = {
            'ui_ux': 'UI/UX Requirements',
            'implementation': 'Implementation Plan',
            'api_specs': 'API Specifications', 
            'testing': 'Testing Strategy'
        }
        
        section_name = section_names.get(section_type, 'Additional Section')
        
        generation_prompt = f"""Based on the project conversation, generate a comprehensive {section_name} section.

CONVERSATION CONTEXT:
{conversation_context}

SECTION TEMPLATE:
{template}

Generate a detailed {section_name} section that:
1. Is specific to the project discussed in the conversation
2. Follows the template structure
3. Includes relevant technical details
4. Uses professional formatting
5. Includes code examples or diagrams where appropriate

Format as clean markdown. Be comprehensive and detailed."""

        # Use AI service
        ai_service = get_ai_service()
        if not ai_service:
            return jsonify({
                'success': False,
                'error': 'AI service not available'
            }), 503

        try:
            ai_response = ai_service.execute_model_garden_task(
                instruction=generation_prompt,
                model='claude-sonnet-3.5',
                role='po'
            )
            
            if not ai_response or not ai_response.get('output'):
                raise Exception('Section generation failed')
            
            section_content = ai_response['output']
            
            # Convert markdown to Editor.js blocks
            editorjs_content = convert_markdown_to_editorjs(section_content)
            editorjs_blocks = editorjs_content.get('blocks', [])
            
            return jsonify({
                'success': True,
                'data': {
                    'content': section_content,
                    'editorjs_blocks': editorjs_blocks,
                    'section_type': section_type,
                    'section_name': section_name
                }
            })
            
        except Exception as ai_error:
            logger.error(f"Section generation failed: {ai_error}")
            return jsonify({
                'success': False,
                'error': f'Section generation failed: {str(ai_error)}'
            }), 503
            
    except Exception as e:
        logger.error(f"Error generating additional section: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate additional section'
        }), 500





def _extract_prd_from_nested_json(nested_json: Dict[str, Any]) -> str:
    """Extract and format PRD content from nested JSON structure"""
    try:
        markdown_content = ""
        
        if isinstance(nested_json, dict) and 'Project' in nested_json:
            project = nested_json['Project']
            
            # Product Specification
            if 'Product Specification' in project:
                prod_spec = project['Product Specification']
                markdown_content += "# Product Specification\n\n"
                
                if 'Introduction & Vision' in prod_spec:
                    markdown_content += "## Introduction & Vision\n\n"
                    markdown_content += str(prod_spec['Introduction & Vision']) + "\n\n"
                
                if 'Target Audience & User Personas' in prod_spec:
                    markdown_content += "## Target Audience & User Personas\n\n"
                    personas_data = prod_spec['Target Audience & User Personas']
                    if isinstance(personas_data, dict) and 'Personas' in personas_data:
                        personas = personas_data['Personas']
                        if isinstance(personas, list):
                            for persona in personas:
                                if isinstance(persona, dict):
                                    name = persona.get('name', 'Unnamed Persona')
                                    description = persona.get('description', '')
                                    goals = persona.get('goals', [])
                                    
                                    markdown_content += f"### {name}\n\n"
                                    if description:
                                        markdown_content += f"{description}\n\n"
                                    if goals and isinstance(goals, list):
                                        markdown_content += "**Goals:**\n"
                                        for goal in goals:
                                            markdown_content += f"- {goal}\n"
                                        markdown_content += "\n"
                
                if 'User Stories / Use Cases' in prod_spec:
                    stories = prod_spec['User Stories / Use Cases']
                    if isinstance(stories, list):
                        markdown_content += "## User Stories / Use Cases\n\n"
                        for story in stories:
                            markdown_content += f"- {story}\n"
                        markdown_content += "\n"
            
            # Technical Specification
            if 'Technical Specification' in project:
                tech_spec = project['Technical Specification']
                markdown_content += "# Technical Specification\n\n"
                
                if 'System Overview' in tech_spec:
                    markdown_content += "## System Overview\n\n"
                    markdown_content += str(tech_spec['System Overview']) + "\n\n"
                
                if 'High-Level Architecture' in tech_spec:
                    arch = tech_spec['High-Level Architecture']
                    markdown_content += "## High-Level Architecture\n\n"
                    
                    if isinstance(arch, dict) and 'Components Diagram' in arch:
                        diagram = arch['Components Diagram']
                        if isinstance(diagram, str) and 'mermaid' in diagram.lower():
                            markdown_content += "### Components Diagram\n\n"
                            markdown_content += diagram + "\n\n"
        
        return markdown_content.strip()
    except Exception as e:
        logger.error(f"Error extracting PRD from nested JSON: {e}")
        return ""


def _construct_prd_from_summary(json_data: Dict[str, Any]) -> str:
    """Construct a basic PRD from summary fields"""
    try:
        markdown_content = "# Product Requirements Document\n\n"
        
        if 'problem' in json_data and isinstance(json_data['problem'], dict):
            problem = json_data['problem']
            if 'text' in problem:
                markdown_content += "## Problem Statement\n\n"
                markdown_content += str(problem['text']) + "\n\n"
        
        if 'audience' in json_data and isinstance(json_data['audience'], dict):
            audience = json_data['audience']
            if 'text' in audience:
                markdown_content += "## Target Audience\n\n"
                markdown_content += str(audience['text']) + "\n\n"
        
        if 'goals' in json_data and isinstance(json_data['goals'], dict):
            goals = json_data['goals']
            if 'items' in goals and isinstance(goals['items'], list):
                markdown_content += "## Goals & Objectives\n\n"
                for goal in goals['items']:
                    markdown_content += f"- {goal}\n"
                markdown_content += "\n"
        
        if 'risks' in json_data and isinstance(json_data['risks'], dict):
            risks = json_data['risks']
            if 'items' in risks and isinstance(risks['items'], list):
                markdown_content += "## Risks & Considerations\n\n"
                for risk in risks['items']:
                    markdown_content += f"- {risk}\n"
                markdown_content += "\n"
        
        if 'competitive_scan' in json_data and isinstance(json_data['competitive_scan'], dict):
            competitive = json_data['competitive_scan']
            if 'items' in competitive and isinstance(competitive['items'], list):
                markdown_content += "## Competitive Analysis\n\n"
                for item in competitive['items']:
                    markdown_content += f"- {item}\n"
                markdown_content += "\n"
        
        if 'open_questions' in json_data and isinstance(json_data['open_questions'], dict):
            questions = json_data['open_questions']
            if 'items' in questions and isinstance(questions['items'], list):
                markdown_content += "## Open Questions\n\n"
                for question in questions['items']:
                    markdown_content += f"- {question}\n"
                markdown_content += "\n"
        
        return markdown_content.strip()
    except Exception as e:
        logger.error(f"Error constructing PRD from summary: {e}")
        return ""


def convert_markdown_to_editorjs(markdown_content: str) -> Dict[str, Any]:
    """Convert markdown content to Editor.js format with Mermaid and code block support"""
    if not markdown_content:
        return {"time": int(datetime.now().timestamp() * 1000), "blocks": [], "version": "2.28.2"}
    
    # Clean the content first - remove any HTML entities that might have been introduced
    import html
    markdown_content = html.unescape(markdown_content)
    
    # Check if the content is JSON-formatted PRD data (only if it's clearly JSON)
    content_stripped = markdown_content.strip()
    if content_stripped.startswith('{') and content_stripped.endswith('}'):
        try:
            json_data = json.loads(markdown_content)
            
            # Try different extraction strategies
            extracted_content = None
            
            if 'full_prd' in json_data:
                full_prd = json_data['full_prd']
                if isinstance(full_prd, str):
                    # Handle nested JSON in full_prd
                    if full_prd.strip().startswith('{'):
                        try:
                            nested_json = json.loads(full_prd)
                            extracted_content = _extract_prd_from_nested_json(nested_json)
                        except:
                            extracted_content = full_prd
                    else:
                        extracted_content = full_prd
                elif isinstance(full_prd, dict):
                    extracted_content = _extract_prd_from_nested_json(full_prd)
            
            # Fallback: try to construct PRD from summary fields
            if not extracted_content and any(key in json_data for key in ['problem', 'audience', 'goals']):
                extracted_content = _construct_prd_from_summary(json_data)
            
            if extracted_content:
                markdown_content = extracted_content
                # Convert escaped newlines to actual newlines
                markdown_content = markdown_content.replace('\\n', '\n').replace('\\"', '"')
                logger.info(f"Successfully extracted PRD content ({len(markdown_content)} chars) from JSON wrapper")
            else:
                logger.warning("Could not extract meaningful PRD content from JSON structure")
                
        except (json.JSONDecodeError, KeyError) as e:
            # If it starts with { but isn't valid JSON, it's probably markdown with code blocks
            # Don't try to parse as JSON, just treat as regular markdown
            logger.debug(f"Content starts with {{ but isn't valid JSON, treating as markdown: {e}")
            pass
    
    # If content still looks like malformed JSON, try to detect and fix common issues
    if content_stripped.startswith('{"full_prd":') and not content_stripped.endswith('}'):
        logger.warning("Detected potentially truncated JSON, attempting to extract markdown content")
        try:
            # Try to extract the full_prd content even from malformed JSON
            start_marker = '"full_prd": "'
            start_pos = markdown_content.find(start_marker)
            if start_pos != -1:
                start_pos += len(start_marker)
                # Look for the end of the string value
                remaining = markdown_content[start_pos:]
                
                # Find the end of the full_prd string value
                end_pos = -1
                quote_count = 0
                for i, char in enumerate(remaining):
                    if char == '"' and (i == 0 or remaining[i-1] != '\\'):
                        quote_count += 1
                        if quote_count == 1:  # Found the closing quote
                            end_pos = i
                            break
                
                if end_pos > 0:
                    extracted_content = remaining[:end_pos]
                    # Unescape JSON string
                    extracted_content = extracted_content.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
                    if len(extracted_content) > 50:
                        markdown_content = extracted_content
                        logger.info(f"Successfully extracted {len(markdown_content)} chars from malformed JSON")
        except Exception as extract_error:
            logger.warning(f"Could not extract from malformed JSON: {extract_error}")
            # Keep original content as fallback
    
    blocks = []
    lines = markdown_content.split('\n')
    current_list_items = []
    current_list_style = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Finish any pending list
        if current_list_items and not (line.startswith('- ') or line.startswith('* ') or line.startswith(tuple(f'{j}. ' for j in range(1, 10)))):
            # Ensure all list items are properly decoded
            decoded_items = [html.unescape(item) for item in current_list_items]
            blocks.append({
                "id": str(uuid.uuid4()),
                "type": "list",
                "data": {
                    "style": current_list_style,
                    "items": decoded_items
                }
            })
            current_list_items = []
            current_list_style = None
        
        # Code blocks (including Mermaid)
        if line.startswith('```'):
            code_type = line[3:].strip()
            code_lines = []
            i += 1
            
            # Collect code content
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            
            code_content = '\n'.join(code_lines)
            
            # Create Mermaid block for mermaid code
            if code_type == 'mermaid':
                blocks.append({
                    "id": str(uuid.uuid4()),
                    "type": "mermaid",
                    "data": {"code": code_content}
                })
            else:
                # Regular code block
                blocks.append({
                    "id": str(uuid.uuid4()),
                    "type": "raw",
                    "data": {
                        "html": f'<pre><code class="language-{code_type}">{code_content}</code></pre>'
                    }
                })
        
        # Headers
        elif line.startswith('# '):
            blocks.append({
                "id": str(uuid.uuid4()),
                "type": "header",
                "data": {"text": html.unescape(line[2:].strip()), "level": 1}
            })
        elif line.startswith('## '):
            blocks.append({
                "id": str(uuid.uuid4()),
                "type": "header", 
                "data": {"text": html.unescape(line[3:].strip()), "level": 2}
            })
        elif line.startswith('### '):
            blocks.append({
                "id": str(uuid.uuid4()),
                "type": "header",
                "data": {"text": html.unescape(line[4:].strip()), "level": 3}
            })
        elif line.startswith('#### '):
            blocks.append({
                "id": str(uuid.uuid4()),
                "type": "header",
                "data": {"text": html.unescape(line[5:].strip()), "level": 4}
            })
        elif line.startswith('##### '):
            blocks.append({
                "id": str(uuid.uuid4()),
                "type": "header",
                "data": {"text": html.unescape(line[6:].strip()), "level": 5}
            })
        
        # Unordered lists
        elif line.startswith('- ') or line.startswith('* '):
            if current_list_style != 'unordered':
                current_list_style = 'unordered'
            current_list_items.append(html.unescape(line[2:].strip()))
        
        # Ordered lists
        elif any(line.startswith(f'{j}. ') for j in range(1, 10)):
            if current_list_style != 'ordered':
                current_list_style = 'ordered'
            for j in range(1, 10):
                if line.startswith(f'{j}. '):
                    current_list_items.append(html.unescape(line[len(f'{j}. '):].strip()))
                    break
        
        # Bold text sections (treat as subheaders)
        elif line.startswith('**') and line.endswith('**') and len(line) > 4:
            blocks.append({
                "id": str(uuid.uuid4()),
                "type": "header",
                "data": {"text": html.unescape(line[2:-2].strip()), "level": 4}
            })
        
        # Paragraphs
        else:
            # Collect multi-line paragraphs
            paragraph_lines = [line]
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if (not next_line or 
                    next_line.startswith('#') or 
                    next_line.startswith('```') or
                    next_line.startswith('- ') or 
                    next_line.startswith('* ') or
                    any(next_line.startswith(f'{k}. ') for k in range(1, 10)) or
                    (next_line.startswith('**') and next_line.endswith('**'))):
                    break
                paragraph_lines.append(next_line)
                j += 1
            
            # Join paragraph lines and create block
            paragraph_text = ' '.join(paragraph_lines).strip()
            if paragraph_text:
                blocks.append({
                    "id": str(uuid.uuid4()),
                    "type": "paragraph",
                    "data": {"text": html.unescape(paragraph_text)}
                })
            i = j - 1
        
        i += 1
    
    # Add any remaining list items
    if current_list_items:
        # Ensure all list items are properly decoded
        decoded_items = [html.unescape(item) for item in current_list_items]
        blocks.append({
            "id": str(uuid.uuid4()),
            "type": "list",
            "data": {
                "style": current_list_style,
                "items": decoded_items
            }
        })
    
    return {
        "time": int(datetime.now().timestamp() * 1000),
        "blocks": blocks,
        "version": "2.28.2"
    }


def convert_editorjs_to_markdown(editorjs_content: Dict[str, Any]) -> str:
    """Convert Editor.js content back to markdown format"""
    if not editorjs_content or not editorjs_content.get('blocks'):
        return ""
    
    markdown_lines = []
    
    for block in editorjs_content['blocks']:
        block_type = block.get('type', '')
        block_data = block.get('data', {})
        
        if block_type == 'header':
            level = block_data.get('level', 1)
            text = block_data.get('text', '')
            markdown_lines.append('#' * level + ' ' + text)
            markdown_lines.append('')
            
        elif block_type == 'paragraph':
            text = block_data.get('text', '')
            markdown_lines.append(text)
            markdown_lines.append('')
            
        elif block_type == 'list':
            style = block_data.get('style', 'unordered')
            items = block_data.get('items', [])
            
            for i, item in enumerate(items):
                if style == 'ordered':
                    markdown_lines.append(f"{i+1}. {item}")
                else:
                    markdown_lines.append(f"- {item}")
            markdown_lines.append('')
            
        elif block_type == 'quote':
            text = block_data.get('text', '')
            markdown_lines.append(f"> {text}")
            markdown_lines.append('')
            
        elif block_type == 'code':
            code = block_data.get('code', '')
            markdown_lines.append('```')
            markdown_lines.append(code)
            markdown_lines.append('```')
            markdown_lines.append('')
            
        elif block_type == 'table':
            # Handle table conversion
            content = block_data.get('content', [])
            if content:
                # Header row
                if len(content) > 0:
                    header = '| ' + ' | '.join(content[0]) + ' |'
                    separator = '| ' + ' | '.join(['---'] * len(content[0])) + ' |'
                    markdown_lines.append(header)
                    markdown_lines.append(separator)
                    
                    # Data rows
                    for row in content[1:]:
                        row_text = '| ' + ' | '.join(row) + ' |'
                        markdown_lines.append(row_text)
                    markdown_lines.append('')
    
    return '\n'.join(markdown_lines)


# ---------------- BlockDocument v1 helpers (server-side) ----------------

def _bd_generate_id() -> str:
    return str(uuid.uuid4())

def _json_to_blocks_v1(value: Union[str, Dict[str, Any], List[Any]], level: int = 1, key: Optional[str] = None, out: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    if out is None:
        out = []

    def header(lvl: int, text: str):
        out.append({
            'id': _bd_generate_id(),
            'type': 'header',
            'content': { 'level': max(1, min(6, lvl)), 'text': str(text) }
        })

    def paragraph(text: str):
        out.append({ 'id': _bd_generate_id(), 'type': 'paragraph', 'content': { 'text': str(text) } })

    if key is not None:
        header(level, key)

    # Try to coerce stringified JSON first
    if isinstance(value, str):
        s = value.strip()
        if (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']')):
            try:
                value = json.loads(s)
            except Exception:
                paragraph(value)
                return out
        else:
            paragraph(value)
            return out

    if isinstance(value, list):
        if all(not isinstance(v, (dict, list)) for v in value):
            out.append({ 'id': _bd_generate_id(), 'type': 'bullet-list', 'content': { 'items': [str(v) for v in value] } })
        else:
            # List of objects → summarize
            items = []
            for v in value:
                if isinstance(v, dict):
                    flat = ', '.join(f"{k}: {str(vv)}" for k, vv in list(v.items())[:4])
                    items.append(flat)
                else:
                    items.append(str(v))
            out.append({ 'id': _bd_generate_id(), 'type': 'bullet-list', 'content': { 'items': items } })
        return out

    if isinstance(value, dict):
        for k, v in value.items():
            _json_to_blocks_v1(v, min(6, level + 1), str(k), out)
        return out

    # primitive
    paragraph(str(value))
    return out


def editorjs_to_blocks_v1(editorjs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Server-side bridge: Editor.js → BlockDocument v1.
    Expands a single JSON blob paragraph when detected.
    """
    blocks: List[Dict[str, Any]] = []
    if not editorjs or not isinstance(editorjs, dict) or not isinstance(editorjs.get('blocks'), list):
        return blocks

    # If entire doc is JSON in first paragraph, expand and return
    try:
        first = editorjs['blocks'][0] if editorjs['blocks'] else None
        txt = first.get('data', {}).get('text') if isinstance(first, dict) else None
        if isinstance(txt, str) and (txt.strip().startswith('{') or txt.strip().startswith('[')):
            expanded = _json_to_blocks_v1(txt)
            if len(expanded) > 0:
                return expanded
    except Exception:
        pass

    for b in editorjs['blocks']:
        t = b.get('type')
        d = b.get('data', {})
        if t == 'header':
            blocks.append({
                'id': _bd_generate_id(),
                'type': 'header',
                'content': { 'level': int(d.get('level', 1)), 'text': d.get('text', '') }
            })
        elif t == 'paragraph':
            txt = d.get('text', '')
            if isinstance(txt, str) and (txt.strip().startswith('{') or txt.strip().startswith('[')):
                try:
                    blocks.extend(_json_to_blocks_v1(txt))
                    continue
                except Exception:
                    pass
            blocks.append({ 'id': _bd_generate_id(), 'type': 'paragraph', 'content': { 'text': txt } })
        elif t == 'list':
            style = d.get('style', 'unordered')
            items = d.get('items', []) or []
            blocks.append({ 'id': _bd_generate_id(), 'type': 'numbered-list' if style == 'ordered' else 'bullet-list', 'content': { 'items': [str(x) for x in items] } })
        elif t == 'delimiter':
            blocks.append({ 'id': _bd_generate_id(), 'type': 'hr', 'content': None })
        elif t == 'code':
            blocks.append({ 'id': _bd_generate_id(), 'type': 'code', 'content': { 'language': d.get('language'), 'code': d.get('code', '') } })
        elif t == 'mermaid':
            blocks.append({ 'id': _bd_generate_id(), 'type': 'mermaid-diagram', 'content': { 'code': d.get('code', '') } })
        elif t == 'table':
            content = d.get('content', []) or []
            header = content[0] if content and isinstance(content[0], list) else None
            rows = content[1:] if content and isinstance(content[0], list) else content
            blocks.append({ 'id': _bd_generate_id(), 'type': 'table', 'content': { 'header': header, 'rows': rows } })
        else:
            # Fallback as paragraph if textual
            txt = d.get('text')
            if isinstance(txt, str) and txt:
                blocks.append({ 'id': _bd_generate_id(), 'type': 'paragraph', 'content': { 'text': txt }, 'meta': { 'errors': [f'unmapped type {t}'] } })
    return blocks


@prd_editor_bp.route('/export', methods=['POST'])
def export_document():
    """Export PRD document in multiple formats (PDF, Word, Markdown, HTML)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON'
            }), 400
        
        # Extract export parameters
        content = data.get('content')
        format_type = data.get('format', 'pdf').lower()
        options = data.get('options', {})
        
        if not content:
            return jsonify({
                'success': False,
                'error': 'Document content is required'
            }), 400
        
        # Validate format
        supported_formats = ['pdf', 'docx', 'markdown', 'html']
        if format_type not in supported_formats:
            return jsonify({
                'success': False,
                'error': f'Unsupported format. Supported formats: {", ".join(supported_formats)}'
            }), 400
        
        # Get export service and perform export
        export_service = get_export_service()
        
        try:
            export_result = export_service.export_document(content, format_type, options)
            
            if not export_result.get('success'):
                return jsonify({
                    'success': False,
                    'error': 'Export failed'
                }), 500
            
            # Return file as download
            file_content = export_result['content']
            filename = export_result['filename']
            mime_type = export_result['mime_type']
            
            # Create response with file content
            response = Response(
                file_content,
                mimetype=mime_type,
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Length': str(len(file_content))
                }
            )
            
            return response
            
        except Exception as export_error:
            logger.error(f"Export processing failed: {export_error}")
            return jsonify({
                'success': False,
                'error': f'Export processing failed: {str(export_error)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Export endpoint error: {e}")
        return jsonify({
            'success': False,
            'error': 'Export request processing failed'
        }), 500


@prd_editor_bp.route('/export/formats', methods=['GET'])
def get_export_formats():
    """Get available export formats and their capabilities"""
    try:
        export_service = get_export_service()
        
        # Check which formats are available based on installed dependencies
        formats = {
            'pdf': {
                'name': 'PDF',
                'description': 'Portable Document Format with preserved formatting',
                'mime_type': 'application/pdf',
                'extension': 'pdf',
                'features': ['diagrams', 'tables', 'formatting', 'print_ready'],
                'available': True  # Will be checked by export service
            },
            'docx': {
                'name': 'Word Document',
                'description': 'Microsoft Word document with native table support',
                'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'extension': 'docx',
                'features': ['tables', 'formatting', 'editable'],
                'available': True  # Will be checked by export service
            },
            'markdown': {
                'name': 'Markdown',
                'description': 'Plain text format with markup syntax',
                'mime_type': 'text/markdown',
                'extension': 'md',
                'features': ['diagrams', 'tables', 'version_control_friendly'],
                'available': True
            },
            'html': {
                'name': 'HTML',
                'description': 'Web page with interactive features',
                'mime_type': 'text/html',
                'extension': 'html',
                'features': ['interactive', 'diagrams', 'styling', 'web_ready'],
                'available': True
            }
        }
        
        return jsonify({
            'success': True,
            'formats': formats
        })
        
    except Exception as e:
        logger.error(f"Error getting export formats: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get export formats'
        }), 500


@prd_editor_bp.route('/export/options', methods=['GET'])
def get_export_options():
    """Get available export customization options"""
    try:
        options = {
            'pdf': {
                'page_size': {
                    'type': 'select',
                    'options': ['A4', 'Letter', 'Legal'],
                    'default': 'A4',
                    'description': 'Page size for PDF output'
                },
                'include_toc': {
                    'type': 'boolean',
                    'default': True,
                    'description': 'Include table of contents'
                },
                'include_metadata': {
                    'type': 'boolean',
                    'default': True,
                    'description': 'Include document metadata'
                },
                'font_size': {
                    'type': 'select',
                    'options': ['10pt', '11pt', '12pt', '14pt'],
                    'default': '11pt',
                    'description': 'Base font size'
                }
            },
            'docx': {
                'include_toc': {
                    'type': 'boolean',
                    'default': True,
                    'description': 'Include table of contents'
                },
                'include_metadata': {
                    'type': 'boolean',
                    'default': True,
                    'description': 'Include document metadata'
                },
                'template': {
                    'type': 'select',
                    'options': ['default', 'professional', 'minimal'],
                    'default': 'default',
                    'description': 'Document template style'
                }
            },
            'markdown': {
                'include_metadata': {
                    'type': 'boolean',
                    'default': True,
                    'description': 'Include YAML frontmatter'
                },
                'diagram_format': {
                    'type': 'select',
                    'options': ['mermaid', 'plantuml', 'inline'],
                    'default': 'mermaid',
                    'description': 'Diagram embedding format'
                }
            },
            'html': {
                'include_css': {
                    'type': 'boolean',
                    'default': True,
                    'description': 'Include embedded CSS styling'
                },
                'interactive_diagrams': {
                    'type': 'boolean',
                    'default': True,
                    'description': 'Enable interactive Mermaid diagrams'
                },
                'theme': {
                    'type': 'select',
                    'options': ['default', 'dark', 'minimal'],
                    'default': 'default',
                    'description': 'Visual theme'
                }
            }
        }
        
        return jsonify({
            'success': True,
            'options': options
        })
        
    except Exception as e:
        logger.error(f"Error getting export options: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get export options'
        }), 500


@prd_editor_bp.route('/export/queue', methods=['POST'])
def queue_export():
    """Queue export for large documents (async processing)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON'
            }), 400
        
        # Extract parameters
        content = data.get('content')
        format_type = data.get('format', 'pdf').lower()
        options = data.get('options', {})
        callback_url = data.get('callback_url')
        
        if not content:
            return jsonify({
                'success': False,
                'error': 'Document content is required'
            }), 400
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # For now, we'll process synchronously but return job structure
        # In production, this would use a task queue like Celery
        try:
            export_service = get_export_service()
            export_result = export_service.export_document(content, format_type, options)
            
            if export_result.get('success'):
                # Store result temporarily (in production, use Redis or database)
                # For now, encode as base64 for JSON response
                file_content_b64 = base64.b64encode(export_result['content']).decode('utf-8')
                
                return jsonify({
                    'success': True,
                    'job_id': job_id,
                    'status': 'completed',
                    'result': {
                        'filename': export_result['filename'],
                        'mime_type': export_result['mime_type'],
                        'size': export_result['size'],
                        'content_base64': file_content_b64
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'job_id': job_id,
                    'status': 'failed',
                    'error': 'Export processing failed'
                })
                
        except Exception as export_error:
            logger.error(f"Queued export failed: {export_error}")
            return jsonify({
                'success': False,
                'job_id': job_id,
                'status': 'failed',
                'error': str(export_error)
            })
            
    except Exception as e:
        logger.error(f"Export queue error: {e}")
        return jsonify({
            'success': False,
            'error': 'Export queue processing failed'
        }), 500


@prd_editor_bp.route('/export/queue/<job_id>', methods=['GET'])
def get_export_status(job_id):
    """Get status of queued export job"""
    try:
        # In production, this would check job status from queue/database
        # For now, return a mock response
        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': 'completed',  # or 'pending', 'processing', 'failed'
            'progress': 100,
            'message': 'Export completed successfully'
        })
        
    except Exception as e:
        logger.error(f"Export status check error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to check export status'
        }), 500


# Block editing and persistence endpoints (Task 5)

@prd_editor_bp.route('/blocks/<block_id>', methods=['PUT'])
def update_block(block_id):
    """Update a specific block's content"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON'
            }), 400
        
        content = data.get('content')
        if not content:
            return jsonify({
                'success': False,
                'error': 'Content is required'
            }), 400
        
        # For MVP, we'll store the updated content in session storage
        # In production, this would update the database
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'Session ID is required'
            }), 400
        
        # Update the block content and return success
        # This would typically update the PRD in the database
        return jsonify({
            'success': True,
            'data': {
                'block_id': block_id,
                'content': content,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating block {block_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to update block: {str(e)}'
        }), 500


@prd_editor_bp.route('/blocks', methods=['POST'])
def create_block():
    """Create a new block"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON'
            }), 400
        
        block_type = data.get('type')
        content = data.get('content')
        session_id = data.get('session_id')
        position = data.get('position', 0)
        
        if not all([block_type, content, session_id]):
            return jsonify({
                'success': False,
                'error': 'Type, content, and session_id are required'
            }), 400
        
        # Generate new block ID
        new_block_id = str(uuid.uuid4())
        
        # For MVP, return the new block structure
        # In production, this would insert into database
        new_block = {
            'id': new_block_id,
            'type': block_type,
            'content': content,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': new_block
        })
        
    except Exception as e:
        logger.error(f"Error creating block: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to create block: {str(e)}'
        }), 500


@prd_editor_bp.route('/blocks/<block_id>', methods=['DELETE'])
def delete_block(block_id):
    """Delete a specific block"""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'Session ID is required'
            }), 400
        
        # For MVP, just return success
        # In production, this would delete from database
        return jsonify({
            'success': True,
            'data': {
                'block_id': block_id,
                'deleted_at': datetime.now(timezone.utc).isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error deleting block {block_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to delete block: {str(e)}'
        }), 500


# Error handlers
@prd_editor_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Resource not found'
    }), 404


@prd_editor_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500
# ---------------- BlockDocument v1 schema (Pydantic) ----------------

class ParagraphContent(BaseModel):
    text: str

class HeaderContent(BaseModel):
    level: int
    text: str

    @validator('level')
    def level_range(cls, v):
        if v < 1 or v > 6:
            raise ValueError('level must be 1..6')
        return v

class ListContent(BaseModel):
    items: List[str]

class CodeContent(BaseModel):
    language: Optional[str] = None
    code: str

class MermaidContent(BaseModel):
    code: str
    diagramType: Optional[str] = None

class TableContent(BaseModel):
    header: Optional[List[str]] = None
    rows: List[List[str]]

BlockContent = Union[ParagraphContent, HeaderContent, ListContent, CodeContent, MermaidContent, TableContent, None]

class Block(BaseModel):
    id: Optional[str] = None
    type: str
    content: BlockContent
    meta: Optional[Dict[str, Any]] = None

    @validator('type')
    def type_allowed(cls, v):
        allowed = {
            'paragraph', 'header', 'bullet-list', 'numbered-list', 'code', 'mermaid-diagram', 'table', 'hr'
        }
        if v not in allowed:
            raise ValueError(f'Unknown type {v}')
        return v

    @root_validator(skip_on_failure=True)
    def content_matches_type(cls, values):
        t = values.get('type')
        c = values.get('content')
        if t == 'paragraph' and not isinstance(c, ParagraphContent):
            raise ValueError('paragraph.content must be { text }')
        if t == 'header' and not isinstance(c, HeaderContent):
            raise ValueError('header.content must be { level, text }')
        if t in ('bullet-list', 'numbered-list') and not isinstance(c, ListContent):
            raise ValueError('list.content must be { items }')
        if t == 'code' and not isinstance(c, CodeContent):
            raise ValueError('code.content must be { code, language? }')
        if t == 'mermaid-diagram' and not isinstance(c, MermaidContent):
            raise ValueError('mermaid.content must be { code, diagramType? }')
        if t == 'table' and not isinstance(c, TableContent):
            raise ValueError('table.content must be { header?, rows }')
        if t == 'hr' and c is not None:
            raise ValueError('hr.content must be null')
        return values

class BlockDocument(BaseModel):
    meta: Optional[Dict[str, Any]] = None
    blocks: List[Block]

def _strip_fences_and_normalize(text: str) -> str:
    if text is None:
        return ''
    s = text.strip()
    # Normalize smart quotes
    s = s.replace('\u201C', '"').replace('\u201D', '"').replace('\u201E', '"').replace('\u201F', '"').replace('\u2033', '"')
    s = s.replace('\u2018', "'").replace('\u2019', "'").replace('\u201A', "'").replace('\u201B', "'").replace('\u2032', "'")
    # Extract fenced json if present
    if '```' in s:
        try:
            start = s.index('```')
            end = s.rindex('```')
            inner = s[start+3:end]
            # Remove optional 'json' language tag
            if inner.lstrip().lower().startswith('json'):
                inner = inner.split('\n', 1)[1] if '\n' in inner else ''
            return inner.strip()
        except Exception:
            return s
    return s

def validate_block_document_v1(payload: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Validate and normalize a BlockDocument v1. Raises ValidationError on failure."""
    if isinstance(payload, str):
        payload = _strip_fences_and_normalize(payload)
        obj = json.loads(payload)
    else:
        obj = payload
    # Pydantic will coerce nested content into the right models
    doc = BlockDocument.parse_obj(obj)
    return doc.dict()
