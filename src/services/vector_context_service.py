"""
Vector Context Service for AI-powered context retrieval
Provides specialized methods for finding similar specs, code, and documentation
"""

import logging
from typing import List, Dict, Any, Optional
from .vector_service import get_vector_service

logger = logging.getLogger(__name__)


class VectorContextService:
    """Service for AI-powered context retrieval using vector similarity search"""
    
    def __init__(self):
        self.vector_service = get_vector_service()
        if not self.vector_service:
            raise RuntimeError("Vector service not initialized. Call init_vector_service() first.")
        
        # Check if we have pgvector support
        self.has_pgvector = self._check_pgvector_support()
    
    def find_similar_specs(self, query: str, project_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar specifications using vector similarity search
        
        Args:
            query: Search query (idea description, requirement text, etc.)
            project_id: Project identifier for filtering
            limit: Maximum number of results to return
            
        Returns:
            List of similar specification chunks with metadata
        """
        try:
            # Search for specification-related document types
            spec_types = ['requirements', 'design', 'tasks', 'specification', 'spec']
            
            results = self.vector_service.semantic_search(
                query=query,
                document_types=spec_types,
                limit=limit,
                similarity_threshold=0.3
            )
            
            # Filter by project if specified and enhance with spec-specific metadata
            filtered_results = []
            for result in results:
                # Check if document belongs to the specified project
                if project_id and not result['document_id'].startswith(f"{project_id}:"):
                    continue
                
                # Enhance with specification-specific metadata
                enhanced_result = {
                    **result,
                    'context_type': 'specification',
                    'relevance_reason': self._get_spec_relevance_reason(result, query)
                }
                filtered_results.append(enhanced_result)
            
            logger.info(f"Found {len(filtered_results)} similar specs for project {project_id}")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Failed to find similar specs: {e}")
            return []
    
    def find_similar_code(self, query: str, project_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find similar code using vector similarity search
        
        Args:
            query: Search query (function description, code pattern, etc.)
            project_id: Project identifier for filtering
            limit: Maximum number of results to return
            
        Returns:
            List of similar code chunks with metadata
        """
        try:
            # Search for code-related document types
            code_types = ['code_file', 'function', 'class', 'module']
            
            results = self.vector_service.semantic_search(
                query=query,
                document_types=code_types,
                limit=limit,
                similarity_threshold=0.25  # Lower threshold for code to catch more patterns
            )
            
            # Filter by project and enhance with code-specific metadata
            filtered_results = []
            for result in results:
                # Check if document belongs to the specified project
                if project_id and not result['document_id'].startswith(f"{project_id}:"):
                    continue
                
                # Enhance with code-specific metadata
                enhanced_result = {
                    **result,
                    'context_type': 'code',
                    'file_path': self._extract_file_path(result['document_id']),
                    'code_type': self._detect_code_type(result['content']),
                    'relevance_reason': self._get_code_relevance_reason(result, query)
                }
                filtered_results.append(enhanced_result)
            
            logger.info(f"Found {len(filtered_results)} similar code chunks for project {project_id}")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Failed to find similar code: {e}")
            return []
    
    def find_related_docs(self, query: str, project_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Find related documentation using vector similarity search
        
        Args:
            query: Search query (topic, concept, etc.)
            project_id: Project identifier for filtering
            limit: Maximum number of results to return
            
        Returns:
            List of related documentation chunks with metadata
        """
        try:
            # Search for documentation-related document types
            doc_types = ['documentation', 'readme', 'guide', 'manual', 'wiki', 'markdown']
            
            results = self.vector_service.semantic_search(
                query=query,
                document_types=doc_types,
                limit=limit,
                similarity_threshold=0.35  # Higher threshold for docs to ensure relevance
            )
            
            # Filter by project and enhance with documentation-specific metadata
            filtered_results = []
            for result in results:
                # Check if document belongs to the specified project
                if project_id and not result['document_id'].startswith(f"{project_id}:"):
                    continue
                
                # Enhance with documentation-specific metadata
                enhanced_result = {
                    **result,
                    'context_type': 'documentation',
                    'doc_type': self._detect_doc_type(result['document_id'], result['content']),
                    'relevance_reason': self._get_doc_relevance_reason(result, query)
                }
                filtered_results.append(enhanced_result)
            
            logger.info(f"Found {len(filtered_results)} related docs for project {project_id}")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Failed to find related docs: {e}")
            return []
    
    def embed_and_store(self, content: str, content_type: str, project_id: str, 
                       document_id: Optional[str] = None) -> bool:
        """
        Embed content and store it for future similarity search
        
        Args:
            content: Content to embed and store
            content_type: Type of content (spec, code, documentation, etc.)
            project_id: Project identifier
            document_id: Optional document identifier (auto-generated if not provided)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate document ID if not provided
            if not document_id:
                import hashlib
                import time
                content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
                timestamp = int(time.time())
                document_id = f"{project_id}:{content_type}:{timestamp}:{content_hash}"
            elif not document_id.startswith(f"{project_id}:"):
                document_id = f"{project_id}:{document_id}"
            
            # Process and store the document
            success = self.vector_service.process_document(
                content=content,
                document_id=document_id,
                document_type=content_type
            )
            
            if success:
                logger.info(f"Successfully embedded and stored document {document_id}")
            else:
                logger.error(f"Failed to embed and store document {document_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to embed and store content: {e}")
            return False
    
    def optimize_embeddings_for_project(self, project_id: str) -> bool:
        """
        Optimize embeddings for a specific project by re-chunking and re-embedding
        documents with better parameters
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from sqlalchemy import text
            
            # Get all documents for the project
            query = text("""
                SELECT DISTINCT document_id, document_type
                FROM document_chunks
                WHERE document_id LIKE :project_pattern
            """)
            
            result = self.vector_service.db.session.execute(query, {
                'project_pattern': f"{project_id}:%"
            })
            
            optimized_count = 0
            
            for row in result:
                # Get the original content (reconstruct from chunks)
                content_query = text("""
                    SELECT content
                    FROM document_chunks
                    WHERE document_id = :document_id AND document_type = :document_type
                    ORDER BY chunk_index
                """)
                
                content_result = self.vector_service.db.session.execute(content_query, {
                    'document_id': row.document_id,
                    'document_type': row.document_type
                })
                
                # Reconstruct content
                content_parts = [chunk_row.content for chunk_row in content_result]
                full_content = '\n'.join(content_parts)
                
                if full_content.strip():
                    # Re-process with optimized parameters
                    if self.vector_service.process_document(
                        content=full_content,
                        document_id=row.document_id,
                        document_type=row.document_type
                    ):
                        optimized_count += 1
            
            logger.info(f"Optimized {optimized_count} documents for project {project_id}")
            return optimized_count > 0
            
        except Exception as e:
            logger.error(f"Failed to optimize embeddings for project {project_id}: {e}")
            return False
    
    def embed_project_documentation(self, project_id: str, docs: List[Dict[str, str]]) -> bool:
        """
        Embed multiple project documentation files for context retrieval
        
        Args:
            project_id: Project identifier
            docs: List of documents with 'content', 'type', and 'id' keys
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success_count = 0
            
            for doc in docs:
                content = doc.get('content', '')
                doc_type = doc.get('type', 'documentation')
                doc_id = doc.get('id', f"doc_{len(docs)}")
                
                if content.strip():
                    if self.embed_and_store(content, doc_type, project_id, doc_id):
                        success_count += 1
            
            logger.info(f"Successfully embedded {success_count}/{len(docs)} documents for project {project_id}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to embed project documentation: {e}")
            return False
    
    def search_all_content(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search all content without project filtering (for testing)
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching chunks
        """
        try:
            results = self.vector_service.semantic_search(
                query=query,
                document_types=None,  # Search all types
                limit=limit,
                similarity_threshold=0.1  # Lower threshold for testing
            )
            
            logger.info(f"Found {len(results)} results across all content for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search all content: {e}")
            return []
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the vector context service
        
        Returns:
            Dictionary with service statistics
        """
        try:
            stats = self.vector_service.get_document_statistics()
            
            # Add vector context service specific stats
            stats['service_info'] = {
                'has_pgvector': self.has_pgvector,
                'embedding_model': 'all-MiniLM-L6-v2',
                'embedding_dimensions': 384,
                'search_method': 'pgvector' if self.has_pgvector else 'fallback_text'
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get service statistics: {e}")
            return {'error': str(e)}
    
    def get_project_context_summary(self, project_id: str) -> Dict[str, Any]:
        """
        Get a summary of available context for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dictionary with context statistics
        """
        try:
            from sqlalchemy import text
            
            # Query document statistics for the project
            stats_query = text("""
                SELECT 
                    document_type,
                    COUNT(*) as chunk_count,
                    COUNT(DISTINCT document_id) as document_count,
                    SUM(token_count) as total_tokens
                FROM document_chunks
                WHERE document_id LIKE :project_pattern
                GROUP BY document_type
                ORDER BY chunk_count DESC
            """)
            
            result = self.vector_service.db.session.execute(stats_query, {
                'project_pattern': f"{project_id}:%"
            })
            
            summary = {
                'project_id': project_id,
                'document_types': [],
                'total_chunks': 0,
                'total_documents': 0,
                'total_tokens': 0
            }
            
            for row in result:
                type_info = {
                    'type': row.document_type,
                    'chunks': row.chunk_count,
                    'documents': row.document_count,
                    'tokens': row.total_tokens or 0
                }
                summary['document_types'].append(type_info)
                summary['total_chunks'] += row.chunk_count
                summary['total_documents'] += row.document_count
                summary['total_tokens'] += row.total_tokens or 0
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get project context summary: {e}")
            return {'project_id': project_id, 'error': str(e)}
    
    def get_context_for_ai(self, query: str, project_id: str, max_tokens: int = 2000) -> str:
        """
        Get comprehensive context for AI model calls by combining specs, code, and docs
        
        Args:
            query: The query or prompt for context
            project_id: Project identifier for filtering
            max_tokens: Maximum tokens to include in context
            
        Returns:
            Formatted context string for AI models
        """
        try:
            # Allocate tokens across different context types
            spec_tokens = max_tokens // 3
            code_tokens = max_tokens // 3
            doc_tokens = max_tokens - spec_tokens - code_tokens
            
            context_parts = []
            
            # Get similar specifications
            similar_specs = self.find_similar_specs(query, project_id, limit=3)
            if similar_specs:
                spec_context = self._format_context_section(
                    "Similar Specifications", similar_specs, spec_tokens
                )
                if spec_context:
                    context_parts.append(spec_context)
            
            # Get similar code
            similar_code = self.find_similar_code(query, project_id, limit=5)
            if similar_code:
                code_context = self._format_context_section(
                    "Similar Code", similar_code, code_tokens
                )
                if code_context:
                    context_parts.append(code_context)
            
            # Get related documentation
            related_docs = self.find_related_docs(query, project_id, limit=2)
            if related_docs:
                doc_context = self._format_context_section(
                    "Related Documentation", related_docs, doc_tokens
                )
                if doc_context:
                    context_parts.append(doc_context)
            
            # Combine all context
            if context_parts:
                full_context = "\n\n".join(context_parts)
                logger.info(f"Generated comprehensive AI context with {len(context_parts)} sections")
                return full_context
            else:
                logger.info("No relevant context found for AI")
                return ""
            
        except Exception as e:
            logger.error(f"Failed to get context for AI: {e}")
            return ""
    
    def _extract_file_path(self, document_id: str) -> str:
        """Extract file path from document ID"""
        try:
            # Document ID format: project_id:file_path
            parts = document_id.split(':', 1)
            if len(parts) > 1:
                return parts[1]
            return document_id
        except:
            return document_id
    
    def _detect_code_type(self, content: str) -> str:
        """Detect the type of code based on content patterns"""
        content_lower = content.lower()
        
        if 'class ' in content_lower and 'def ' in content_lower:
            return 'class_definition'
        elif 'def ' in content_lower or 'function ' in content_lower:
            return 'function_definition'
        elif 'import ' in content_lower or 'from ' in content_lower:
            return 'module_imports'
        elif 'test' in content_lower and ('assert' in content_lower or 'expect' in content_lower):
            return 'test_code'
        elif any(keyword in content_lower for keyword in ['api', 'endpoint', 'route', '@app']):
            return 'api_code'
        else:
            return 'general_code'
    
    def _detect_doc_type(self, document_id: str, content: str) -> str:
        """Detect the type of documentation based on ID and content"""
        doc_id_lower = document_id.lower()
        content_lower = content.lower()
        
        if 'readme' in doc_id_lower:
            return 'readme'
        elif any(word in doc_id_lower for word in ['api', 'swagger', 'openapi']):
            return 'api_documentation'
        elif 'guide' in doc_id_lower or 'tutorial' in doc_id_lower:
            return 'guide'
        elif any(word in content_lower for word in ['installation', 'setup', 'getting started']):
            return 'setup_guide'
        elif any(word in content_lower for word in ['architecture', 'design', 'system']):
            return 'architecture_doc'
        else:
            return 'general_documentation'
    
    def _get_spec_relevance_reason(self, result: Dict[str, Any], query: str) -> str:
        """Generate a reason why this spec is relevant to the query"""
        doc_type = result.get('document_type', 'specification')
        similarity = result.get('similarity_score', 0)
        
        if similarity > 0.8:
            return f"Highly similar {doc_type} (similarity: {similarity:.2f})"
        elif similarity > 0.6:
            return f"Moderately similar {doc_type} (similarity: {similarity:.2f})"
        else:
            return f"Related {doc_type} (similarity: {similarity:.2f})"
    
    def _get_code_relevance_reason(self, result: Dict[str, Any], query: str) -> str:
        """Generate a reason why this code is relevant to the query"""
        code_type = self._detect_code_type(result['content'])
        similarity = result.get('similarity_score', 0)
        file_path = self._extract_file_path(result['document_id'])
        
        return f"{code_type} from {file_path} (similarity: {similarity:.2f})"
    
    def _get_doc_relevance_reason(self, result: Dict[str, Any], query: str) -> str:
        """Generate a reason why this documentation is relevant to the query"""
        doc_type = self._detect_doc_type(result['document_id'], result['content'])
        similarity = result.get('similarity_score', 0)
        
        return f"{doc_type} (similarity: {similarity:.2f})"
    
    def _check_pgvector_support(self) -> bool:
        """Check if pgvector extension is available"""
        try:
            from sqlalchemy import text
            from flask import current_app
            
            # Try to query a vector function to see if pgvector is available
            test_query = text("SELECT 1 WHERE EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            result = self.vector_service.db.session.execute(test_query)
            has_extension = result.scalar() is not None
            
            logger.info(f"pgvector support: {'available' if has_extension else 'not available'}")
            return has_extension
            
        except Exception as e:
            logger.warning(f"Could not check pgvector support: {e}")
            return False
    
    def _format_context_section(self, section_title: str, results: List[Dict[str, Any]], 
                               max_tokens: int) -> str:
        """Format a section of context results within token limits"""
        if not results:
            return ""
        
        section_parts = [f"=== {section_title} ==="]
        current_tokens = len(self.vector_service.tokenizer.encode(section_parts[0]))
        
        for result in results:
            # Format the result
            content = result['content']
            relevance = result.get('relevance_reason', 'Related content')
            
            result_text = f"\n[{relevance}]\n{content}\n"
            result_tokens = len(self.vector_service.tokenizer.encode(result_text))
            
            # Check if adding this result would exceed token limit
            if current_tokens + result_tokens > max_tokens:
                break
            
            section_parts.append(result_text)
            current_tokens += result_tokens
        
        return "".join(section_parts) if len(section_parts) > 1 else ""


# Global instance
vector_context_service = None


def init_vector_context_service():
    """Initialize the global vector context service instance"""
    global vector_context_service
    try:
        vector_context_service = VectorContextService()
        logger.info("Vector context service initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize vector context service: {e}")
        return False


def get_vector_context_service():
    """Get the global vector context service instance"""
    return vector_context_service