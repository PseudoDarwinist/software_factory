# Nautex-Inspired PRD Generation Integration Guide

## Problem Solved

Your current PRD generation is inconsistent because:
1. **Over-complex prompts** (764 lines in ProductSpecGenerator) confuse the LLM
2. **No schema enforcement** - LLM can output anything
3. **Complex multi-stage pipeline** accumulates errors
4. **Inconsistent parsing** - trying to handle markdown, JSON, malformed JSON

## Solution: Nautex-Inspired Approach

Based on Nautex.ai analysis, this implements:
1. **Strict JSON schema** with Pydantic validation
2. **Short, focused prompts** with clear requirements  
3. **Retry logic** until valid output is achieved
4. **Consistent block conversion** every time

## Quick Integration

### Step 1: Register the New Blueprint

Add to your main Flask app (`src/app.py`):

```python
# Add this import
from api.reliable_prd_generator import reliable_prd_bp

# Register the blueprint
app.register_blueprint(reliable_prd_bp)
```

### Step 2: Test the New Generator

```bash
# Test the reliable generator
curl -X POST http://localhost:8000/api/reliable-prd/test \
  -H "Content-Type: application/json"
```

### Step 3: Replace Your Current Generation

In your existing `prd_editor.py`, update the `generate_comprehensive_prd()` function:

```python
@prd_editor_bp.route('/generate-comprehensive-prd', methods=['POST'])
def generate_comprehensive_prd():
    """Generate comprehensive PRD using reliable method"""
    try:
        data = request.get_json()
        conversation_state = data.get('conversation_state', {})
        
        # NEW: Use reliable generation
        from ..services.nautex_inspired_generator import generate_reliable_prd
        from ..services.ai_service import get_ai_service
        
        ai_service = get_ai_service()
        if not ai_service:
            return jsonify({'success': False, 'error': 'AI service not available'}), 503
        
        # Build conversation context
        conversation_history = conversation_state.get('history', [])
        user_responses = [entry['message'] for entry in conversation_history if entry['role'] == 'user']
        conversation_context = "\n".join([f"User Response {i+1}: {response}" for i, response in enumerate(user_responses)])
        
        # Generate with reliable method
        result = generate_reliable_prd(
            conversation_context=conversation_context,
            ai_service=ai_service
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': {
                    'prd_content': 'Generated via reliable method',
                    'blocks': result['blocks'],
                    'generation_metadata': result['metadata']
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 422
            
    except Exception as e:
        logger.error(f"Reliable PRD generation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
```

## Testing Strategy

### 1. Test Basic Generation

```bash
curl -X POST http://localhost:8000/api/reliable-prd/generate \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_state": {
      "history": [
        {"role": "user", "message": "I want to build a task management app"},
        {"role": "user", "message": "It should help teams collaborate"},
        {"role": "user", "message": "Users need to create and assign tasks"},
        {"role": "user", "message": "Real-time updates are important"}
      ]
    }
  }'
```

### 2. Validate Structure

```bash
# Test schema validation
curl -X POST http://localhost:8000/api/reliable-prd/validate \
  -H "Content-Type: application/json" \
  -d '{"prd_data": {...your_generated_prd...}}'
```

### 3. Compare Methods

```bash
# Compare old vs new approach
curl -X POST http://localhost:8000/api/reliable-prd/compare \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_context": "User wants to build a project management tool"
  }'
```

## Key Benefits

### ✅ **Consistent Structure Every Time**
- Pydantic schema ensures exact format
- No more raw JSON displayed in UI
- Always generates proper blocks for React editor

### ✅ **Shorter Generation Time**  
- Single focused request vs 4-stage pipeline
- No accumulation of errors
- Faster user feedback

### ✅ **Better Quality**
- Focused prompts produce better content
- Schema validation catches incomplete responses
- Retry logic ensures completeness

### ✅ **Easy Debugging**
- Clear error messages
- Validation endpoint for testing
- Compare endpoint for quality assessment

## Schema Overview

The new generator produces this structured format:

```json
{
  "introduction": "Project overview...",
  "user_personas": [
    {
      "name": "Product Manager",
      "role": "Team Lead", 
      "goals": ["Goal 1", "Goal 2"],
      "pain_points": ["Pain 1", "Pain 2"],
      "demographics": "30-45, tech companies"
    }
  ],
  "user_stories": [
    {
      "as_a": "Product Manager",
      "i_want": "create tasks",
      "so_that": "team stays organized", 
      "priority": "P0"
    }
  ],
  "diagrams": [
    {
      "title": "System Architecture",
      "type": "flowchart",
      "code": "flowchart TD\n    A[Frontend] --> B[Backend]"
    }
  ]
}
```

## Migration Strategy

1. **Week 1**: Test new generator alongside existing system
2. **Week 2**: Update frontend to handle new block format  
3. **Week 3**: Switch production traffic to new generator
4. **Week 4**: Remove old generation code

## Troubleshooting

### Common Issues:

**1. "Schema validation failed"**
- Check the `/validate` endpoint to see specific errors
- Increase retry attempts in generator config

**2. "No structured data generated"**
- Verify conversation context has enough detail
- Check AI service connection

**3. "Blocks not rendering"**  
- Ensure frontend expects BlockDocument v1 format
- Check block IDs are properly generated

### Debug Commands:

```bash
# Test AI service connection
curl http://localhost:8000/api/reliable-prd/test

# Validate specific PRD data
curl -X POST http://localhost:8000/api/reliable-prd/validate -d '{"prd_data": {...}}'

# Compare generation quality
curl -X POST http://localhost:8000/api/reliable-prd/compare -d '{"conversation_context": "test"}'
```

## Next Steps

1. **Immediate**: Test the new reliable generator
2. **This Week**: Integrate into your existing PRD editor API
3. **Next Week**: Update frontend to expect consistent format
4. **Following Week**: Remove old inconsistent generation code

This approach will give you **Nautex.ai-level consistency** while working with your existing React editor and block system.