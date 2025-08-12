"""Tests for PRD model operations and versioning."""

import pytest
import uuid
import json
from datetime import datetime
from src.models import db, PRD, extract_prd_summary


class TestPRDModel:
    """Test PRD model operations."""
    
    def test_create_draft(self, app):
        """Test creating a new PRD draft."""
        
        with app.app_context():
            project_id = str(uuid.uuid4())
            draft_id = str(uuid.uuid4())
            md_content = "# PRD\n\nThis is a test PRD."
            json_summary = {
                'problem': {'text': 'Test problem', 'sources': ['S1']},
                'audience': {'text': 'Test audience', 'sources': ['S1']}
            }
            sources = ['file1.pdf', 'file2.pdf']
            
            prd = PRD.create_draft(
                project_id=project_id,
                draft_id=draft_id,
                md_content=md_content,
                json_summary=json_summary,
                sources=sources,
                created_by='test_user'
            )
            
            assert prd.id is not None
            assert str(prd.project_id) == project_id
            assert str(prd.draft_id) == draft_id
            assert prd.version == 'v0'
            assert prd.md_uri == md_content
            assert prd.get_summary() == json_summary
            assert prd.sources == sources
            assert prd.created_by == 'test_user'
            assert prd.status == 'draft'
            assert prd.created_at is not None
    
    def test_freeze_version(self, app):
        """Test freezing a PRD version."""
        
        with app.app_context():
            # Create initial draft
            project_id = str(uuid.uuid4())
            draft_id = str(uuid.uuid4())
            
            draft_prd = PRD.create_draft(
                project_id=project_id,
                draft_id=draft_id,
                md_content="# Draft PRD",
                json_summary={'problem': {'text': 'Draft problem', 'sources': []}},
                created_by='test_user'
            )
            
            # Freeze the draft
            frozen_prd = draft_prd.freeze_version(created_by='freeze_user')
            
            assert frozen_prd.id != draft_prd.id
            assert frozen_prd.project_id == draft_prd.project_id
            assert frozen_prd.draft_id == draft_prd.draft_id
            assert frozen_prd.version == 'v1'
            assert frozen_prd.status == 'frozen'
            assert frozen_prd.created_by == 'freeze_user'
            assert frozen_prd.md_uri == draft_prd.md_uri
            assert frozen_prd.get_summary() == draft_prd.get_summary()
    
    def test_freeze_already_frozen_raises_error(self, app):
        """Test that freezing an already frozen PRD raises an error."""
        
        with app.app_context():
            project_id = str(uuid.uuid4())
            draft_id = str(uuid.uuid4())
            
            # Create and freeze a PRD
            draft_prd = PRD.create_draft(project_id=project_id, draft_id=draft_id)
            frozen_prd = draft_prd.freeze_version()
            
            # Try to freeze the frozen version
            with pytest.raises(ValueError, match="is already frozen"):
                frozen_prd.freeze_version()
    
    def test_update_content_draft(self, app):
        """Test updating content of a draft PRD."""
        
        with app.app_context():
            project_id = str(uuid.uuid4())
            draft_id = str(uuid.uuid4())
            
            prd = PRD.create_draft(
                project_id=project_id,
                draft_id=draft_id,
                md_content="# Original",
                json_summary={'problem': {'text': 'Original problem', 'sources': []}}
            )
            
            # Update content
            new_summary = {'problem': {'text': 'Updated problem', 'sources': ['S1']}}
            prd.update_content(
                md_content="# Updated PRD",
                json_summary=new_summary,
                sources=['updated_file.pdf']
            )
            
            assert prd.md_uri == "# Updated PRD"
            assert prd.get_summary() == new_summary
            assert prd.sources == ['updated_file.pdf']
    
    def test_update_frozen_content_raises_error(self, app):
        """Test that updating frozen PRD content raises an error."""
        
        with app.app_context():
            project_id = str(uuid.uuid4())
            draft_id = str(uuid.uuid4())
            
            # Create and freeze a PRD
            draft_prd = PRD.create_draft(project_id=project_id, draft_id=draft_id)
            frozen_prd = draft_prd.freeze_version()
            
            # Try to update frozen content
            with pytest.raises(ValueError, match="Cannot update frozen PRD"):
                frozen_prd.update_content(md_content="# Should fail")
    
    def test_get_latest_for_session(self, app):
        """Test getting the latest PRD for a session."""
        
        with app.app_context():
            project_id = str(uuid.uuid4())
            draft_id = str(uuid.uuid4())
            
            # Create multiple versions
            draft_prd = PRD.create_draft(project_id=project_id, draft_id=draft_id)
            frozen_v1 = draft_prd.freeze_version()
            
            # Update draft and freeze again
            draft_prd.update_content(md_content="# Updated")
            frozen_v2 = draft_prd.freeze_version()
            
            # Get latest should return v2
            latest = PRD.get_latest_for_session(draft_id)
            assert latest.id == frozen_v2.id
            assert latest.version == 'v2'
    
    def test_get_by_version(self, app):
        """Test getting specific PRD version."""
        
        with app.app_context():
            project_id = str(uuid.uuid4())
            draft_id = str(uuid.uuid4())
            
            # Create versions
            draft_prd = PRD.create_draft(project_id=project_id, draft_id=draft_id)
            frozen_v1 = draft_prd.freeze_version()
            
            # Get specific versions
            v0 = PRD.get_by_version(draft_id, 'v0')
            v1 = PRD.get_by_version(draft_id, 'v1')
            v2 = PRD.get_by_version(draft_id, 'v2')
            
            assert v0.id == draft_prd.id
            assert v1.id == frozen_v1.id
            assert v2 is None
    
    def test_get_all_versions(self, app):
        """Test getting all PRD versions for a session."""
        
        with app.app_context():
            project_id = str(uuid.uuid4())
            draft_id = str(uuid.uuid4())
            
            # Create multiple versions
            draft_prd = PRD.create_draft(project_id=project_id, draft_id=draft_id)
            frozen_v1 = draft_prd.freeze_version()
            draft_prd.update_content(md_content="# Updated")
            frozen_v2 = draft_prd.freeze_version()
            
            # Get all versions
            versions = PRD.get_all_versions(draft_id)
            
            assert len(versions) == 3
            assert versions[0].version == 'v0'
            assert versions[1].version == 'v1'
            assert versions[2].version == 'v2'
    
    def test_to_dict(self, app):
        """Test converting PRD to dictionary."""
        
        with app.app_context():
            project_id = str(uuid.uuid4())
            draft_id = str(uuid.uuid4())
            json_summary = {'problem': {'text': 'Test problem', 'sources': ['S1']}}
            
            prd = PRD.create_draft(
                project_id=project_id,
                draft_id=draft_id,
                md_content="# Test PRD",
                json_summary=json_summary,
                sources=['file1.pdf'],
                created_by='test_user'
            )
            
            result = prd.to_dict()
            
            assert result['id'] == str(prd.id)
            assert result['project_id'] == project_id
            assert result['draft_id'] == draft_id
            assert result['version'] == 'v0'
            assert result['md_uri'] == "# Test PRD"
            assert result['json_summary'] == json_summary
            assert result['sources'] == ['file1.pdf']
            assert result['created_by'] == 'test_user'
            assert result['status'] == 'draft'
            assert 'created_at' in result


class TestExtractPRDSummary:
    """Test PRD summary extraction logic."""
    
    def test_extract_basic_sections(self):
        """Test extracting basic PRD sections from AI response."""
        
        ai_response = """
        # Product Requirements Document
        
        ## Problem Statement
        - Users struggle with complex workflows
        - Current tools are inefficient
        
        ## Target Audience
        - Software developers and product managers
        
        ## Goals and Objectives
        - Streamline user workflows
        - Improve tool efficiency
        - Reduce learning curve
        
        ## Risks and Concerns
        - Technical complexity may be high
        
        ## Competitive Analysis
        - Competitor A has similar features
        - Competitor B lacks integration
        
        ## Open Questions
        - How will users migrate existing data?
        - What is the expected timeline?
        - Should we support mobile platforms?
        """
        
        sources = ['file1.pdf', 'file2.pdf', 'file3.pdf']
        result = extract_prd_summary(ai_response, sources)
        
        # Check structure
        assert 'problem' in result
        assert 'audience' in result
        assert 'goals' in result
        assert 'risks' in result
        assert 'competitive_scan' in result
        assert 'open_questions' in result
        
        # Check content extraction
        assert 'Users struggle with complex workflows' in result['problem']['text']
        assert 'Software developers and product managers' in result['audience']['text']
        assert len(result['goals']['items']) == 3
        assert len(result['risks']['items']) == 1
        assert len(result['competitive_scan']['items']) == 2
        assert len(result['open_questions']['items']) == 3
    
    def test_extract_empty_response(self):
        """Test extracting from empty AI response."""
        
        result = extract_prd_summary("", [])
        
        # Should return default structure
        assert result['problem']['text'] == ''
        assert result['audience']['text'] == ''
        assert result['goals']['items'] == []
        assert result['risks']['items'] == []
        assert result['competitive_scan']['items'] == []
        assert result['open_questions']['items'] == []
    
    def test_extract_with_source_attribution(self):
        """Test that sources are properly attributed to sections."""
        
        ai_response = """
        ## Problem Statement
        - Main problem here
        
        ## Goals and Objectives
        - Goal 1
        - Goal 2
        - Goal 3
        """
        
        sources = ['S1', 'S2']
        result = extract_prd_summary(ai_response, sources)
        
        # Check source attribution
        assert result['problem']['sources'] == ['S1']
        assert len(result['goals']['sources']) == 3
        # Sources should be distributed across items
        assert 'S1' in result['goals']['sources']
        assert 'S2' in result['goals']['sources']
    
    def test_extract_no_sources(self):
        """Test extraction without source files."""
        
        ai_response = """
        ## Problem Statement
        - Test problem
        
        ## Goals and Objectives
        - Test goal
        """
        
        result = extract_prd_summary(ai_response, None)
        
        assert result['problem']['sources'] == []
        assert result['goals']['sources'] == []