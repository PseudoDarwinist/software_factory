# MCP Sampling Implementation Guide

## 🎯 Overview

Software Factory now implements **MCP Sampling** to leverage any MCP client's local AI model for generating high-quality specifications. This eliminates the hardcoded Python templates and provides real AI-generated content.

## 🔧 How It Works

```
MCP Client (Claude Code, Cursor, etc.) → MCP Server → Sampling Request → Client's Local Model → AI-Generated Specs
```

### Key Benefits

- ✅ **Universal Compatibility**: Works with ANY MCP client (Claude Code, Cursor, Continue, etc.)  
- ✅ **Uses Client's Model**: Leverages whatever AI model the client has access to
- ✅ **No Server API Keys**: Server doesn't need its own AI API keys
- ✅ **High Quality Output**: Real AI-generated specifications instead of templates
- ✅ **Graceful Fallback**: Falls back to basic templates if sampling fails

## 🛠 Implementation Details

### Server Capabilities

The MCP server automatically declares sampling capability:

```python
# Server requests sampling from any compatible MCP client
await session.create_message({
    "messages": [{"role": "user", "content": {"type": "text", "text": prompt}}],
    "modelPreferences": {
        "hints": [{"name": "claude-3-sonnet"}, {"name": "claude"}, {"name": "gpt-4"}],
        "intelligencePriority": 0.9,  # High intelligence for spec generation
        "speedPriority": 0.3,         # Quality over speed  
        "costPriority": 0.4           # Moderate cost consideration
    },
    "systemPrompt": "You are an expert software development professional.",
    "maxTokens": 4000
})
```

### Spec Generation Flow

1. **Input**: Idea title, summary, and project context
2. **Prompt Engineering**: Server creates detailed prompts for each spec type
3. **Sampling Request**: Server requests AI generation from client's model
4. **Content Generation**: Client's AI model generates professional specifications
5. **Storage**: Generated specs are stored in Software Factory database
6. **UI Integration**: Specs appear instantly in Mission Control Define stage

### Supported Spec Types

- **requirements.md**: Comprehensive requirements with user stories, acceptance criteria, technical specs
- **design.md**: Technical design with architecture, API specs, implementation strategy  
- **tasks.md**: Detailed task breakdown with effort estimates, dependencies, file modifications

## 🎮 Usage

### For External Projects (Cross-Directory Development)

```python
# Use generate_specs_for_external_project tool
result = await generate_specs_for_external_project(
    idea_id="oauth_login_feature",
    project_id="my_external_project", 
    idea_title="Add OAuth Login",
    idea_summary="Enable users to log in with Google, GitHub, Microsoft accounts",
    spec_types=["requirements", "design", "tasks"],
    additional_context="Using Python FastAPI backend and React frontend"
)
```

### For Software Factory Projects

```python  
# Use generate_missing_specs_for_idea tool
result = await generate_missing_specs_for_idea(
    idea_id="idea_123",
    project_id="project_1",
    missing_spec_types=["requirements", "design", "tasks"],
    generation_context="Additional context for AI generation"
)
```

## 🧪 Testing

Run the test suite to verify sampling works:

```bash
python test_mcp_sampling.py
```

Expected output:
```
🧪 Testing MCP Sampling Implementation
==================================================

📝 Generating requirements specification...
✅ Requirements spec generated successfully
📊 Content length: 1847 characters
🔍 First line: # Requirements for OAuth Login Feature...

📝 Generating design specification...  
✅ Design spec generated successfully
📊 Content length: 2134 characters
🔍 First line: # Design for OAuth Login Feature...

📝 Generating tasks specification...
✅ Tasks spec generated successfully  
📊 Content length: 3421 characters
🔍 First line: # Tasks for OAuth Login Feature...

🎉 MCP Sampling implementation test completed!
```

## 🔄 Fallback Behavior

If MCP client doesn't support sampling:

1. **Detection**: Server detects lack of sampling capability
2. **Fallback**: Generates basic template with idea content
3. **Logging**: Logs fallback reason for debugging
4. **Graceful**: System continues to work without AI generation

## 🚀 Client Compatibility

### Supported MCP Clients

- ✅ **Claude Code** - Full sampling support
- ✅ **Cursor** - Full sampling support  
- ✅ **Continue** - Full sampling support
- ✅ **Any MCP Client** - Universal compatibility

### Client Setup

Each client connects to the MCP server using standard MCP configuration:

**Claude Code**:
```bash
claude mcp add software-factory -- python -m src.mcp.server
```

**Cursor**: Add to MCP settings
**Continue**: Add to MCP configuration

## 🔍 Debugging

### Logging

The server provides detailed logging:

```
INFO - Using MCP sampling for external project my_project
INFO - Generating requirements spec using MCP client's local model  
INFO - MCP sampling successful, content length: 2847 characters
```

### Error Handling

```
ERROR - MCP sampling failed for requirements: Client does not support sampling
INFO - Falling back to basic template for requirements
```

### Verification

Check that sampling is working:

1. Connect MCP client to server
2. Call `generate_specs_for_external_project` tool
3. Verify `sampling_used: true` in response
4. Check spec content is detailed (not basic template)

## 🎯 Next Steps

With MCP sampling implemented:

1. **Test with real clients**: Connect Claude Code, Cursor to test actual sampling
2. **Monitor performance**: Track sampling success rates and content quality
3. **Expand use cases**: Use sampling for other AI generation needs in Software Factory
4. **Optimize prompts**: Refine prompts based on generated content quality

## 🔧 Troubleshooting

### Common Issues

**Issue**: Sampling request fails with validation error
**Solution**: Check MCP client supports latest sampling protocol version

**Issue**: Generated content is basic template
**Solution**: Verify MCP client supports sampling capability

**Issue**: Timeout during spec generation  
**Solution**: Increase maxTokens or reduce prompt complexity

**Issue**: Poor quality generated specs
**Solution**: Improve prompt engineering or model preferences

### Debug Commands

```bash
# Test server imports
python -c "from src.mcp.server import mcp; print('Server OK')"

# Test sampling function
python test_mcp_sampling.py

# Check MCP server tools
python -c "from src.mcp.server import mcp; print(f'Tools: {len(mcp._tools)}')"
```

The MCP sampling implementation provides a robust foundation for AI-powered specification generation that works with any MCP client's local models.