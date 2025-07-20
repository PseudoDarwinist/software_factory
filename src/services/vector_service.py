"""
Vector Database Service for Semantic Search and AI Context
Handles document chunking, embedding generation, and semantic search operations
"""

import os
import re
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import tiktoken
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from flask import current_app

logger = logging.getLogger(__name__)


class VectorService:
    """Service for managing vector embeddings and semantic search"""
    
    def __init__(self, db=None):
        self.db = db
        self.model = None
        self.tokenizer = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize embedding model and tokenizer"""
        try:
            # Use sentence-transformers for embeddings (384 dimensions)
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Use tiktoken for token counting
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
            logger.info("Vector service models initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector service models: {e}")
            raise
    
    def chunk_document(self, content: str, document_id: str, document_type: str, 
                      chunk_size: int = 512, overlap: int = 50) -> List[Dict[str, Any]]:
        """
        Chunk a document into smaller pieces for embedding
        
        Args:
            content: The document content to chunk
            document_id: Unique identifier for the document
            document_type: Type of document (code_file, conversation, etc.)
            chunk_size: Maximum tokens per chunk
            overlap: Number of tokens to overlap between chunks
            
        Returns:
            List of chunk dictionaries with metadata
        """
        try:
            if not content or not content.strip():
                return []
            
            # Clean and normalize content
            content = self._clean_content(content)
            
            # Tokenize the content
            tokens = self.tokenizer.encode(content)
            
            if len(tokens) <= chunk_size:
                # Document is small enough to be a single chunk
                return [{
                    'document_id': document_id,
                    'document_type': document_type,
                    'chunk_index': 0,
                    'content': content,
                    'token_count': len(tokens),
                    'metadata': {
                        'total_chunks': 1,
                        'chunk_method': 'single',
                        'original_length': len(content)
                    }
                }]
            
            chunks = []
            chunk_index = 0
            start_token = 0
            
            while start_token < len(tokens):
                # Calculate end token for this chunk
                end_token = min(start_token + chunk_size, len(tokens))
                
                # Extract chunk tokens and decode back to text
                chunk_tokens = tokens[start_token:end_token]
                chunk_content = self.tokenizer.decode(chunk_tokens)
                
                # Try to break at sentence boundaries for better coherence
                if end_token < len(tokens) and chunk_size > 100:
                    chunk_content = self._break_at_sentence_boundary(chunk_content)
                
                chunks.append({
                    'document_id': document_id,
                    'document_type': document_type,
                    'chunk_index': chunk_index,
                    'content': chunk_content.strip(),
                    'token_count': len(chunk_tokens),
                    'metadata': {
                        'start_token': start_token,
                        'end_token': end_token,
                        'total_tokens': len(tokens),
                        'chunk_method': 'token_based',
                        'original_length': len(content)
                    }
                })
                
                chunk_index += 1
                start_token = end_token - overlap
                
                # Prevent infinite loop
                if start_token >= end_token:
                    break
            
            # Add total chunks metadata to all chunks
            for chunk in chunks:
                chunk['metadata']['total_chunks'] = len(chunks)
            
            logger.info(f"Document {document_id} chunked into {len(chunks)} pieces")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to chunk document {document_id}: {e}")
            return []
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize document content"""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove control characters but keep newlines
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        return content.strip()
    
    def _break_at_sentence_boundary(self, content: str) -> str:
        """Try to break content at a sentence boundary"""
        # Look for sentence endings in the last 100 characters
        last_part = content[-100:]
        sentence_endings = ['. ', '.\n', '! ', '!\n', '? ', '?\n']
        
        best_break = -1
        for ending in sentence_endings:
            pos = last_part.rfind(ending)
            if pos > best_break:
                best_break = pos
        
        if best_break > 0:
            # Break at sentence boundary
            break_point = len(content) - len(last_part) + best_break + len(ending.strip())
            return content[:break_point]
        
        return content
    
    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for document chunks
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            List of chunks with embeddings added
        """
        try:
            if not chunks:
                return []
            
            # Extract content for embedding
            contents = [chunk['content'] for chunk in chunks]
            
            # Generate embeddings in batch for efficiency
            embeddings = self.model.encode(contents, convert_to_numpy=True)
            
            # Add embeddings to chunks
            for i, chunk in enumerate(chunks):
                chunk['embedding'] = embeddings[i].tolist()
            
            logger.info(f"Generated embeddings for {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return chunks
    
    def store_document_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """
        Store document chunks with embeddings in the database
        
        Args:
            chunks: List of chunk dictionaries with embeddings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not chunks:
                return True
            
            # Remove existing chunks for this document
            document_id = chunks[0]['document_id']
            document_type = chunks[0]['document_type']
            
            delete_query = text("""
                DELETE FROM document_chunks 
                WHERE document_id = :document_id AND document_type = :document_type
            """)
            
            self.db.session.execute(delete_query, {
                'document_id': document_id,
                'document_type': document_type
            })
            
            # Insert new chunks
            insert_query = text("""
                INSERT INTO document_chunks 
                (document_id, document_type, chunk_index, content, embedding, metadata, token_count)
                VALUES (:document_id, :document_type, :chunk_index, :content, :embedding, :metadata, :token_count)
            """)
            
            for chunk in chunks:
                # Convert embedding to appropriate format
                # Try pgvector format first, fall back to JSON if pgvector not available
                try:
                    embedding_str = '[' + ','.join(map(str, chunk['embedding'])) + ']'
                except:
                    # Fallback to JSON format
                    import json
                    embedding_str = json.dumps(chunk['embedding'])
                
                # Convert metadata to JSON string
                import json
                metadata_json = json.dumps(chunk['metadata']) if chunk['metadata'] else '{}'
                
                self.db.session.execute(insert_query, {
                    'document_id': chunk['document_id'],
                    'document_type': chunk['document_type'],
                    'chunk_index': chunk['chunk_index'],
                    'content': chunk['content'],
                    'embedding': embedding_str,
                    'metadata': metadata_json,
                    'token_count': chunk['token_count']
                })
            
            self.db.session.commit()
            logger.info(f"Stored {len(chunks)} chunks for document {document_id}")
            return True
            
        except Exception as e:
            try:
                self.db.session.rollback()
            except:
                pass
            logger.error(f"Failed to store document chunks: {e}")
            return False
    
    def process_document(self, content: str, document_id: str, document_type: str) -> bool:
        """
        Complete pipeline: chunk document, generate embeddings, and store
        
        Args:
            content: Document content
            document_id: Unique document identifier
            document_type: Type of document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Chunk the document
            chunks = self.chunk_document(content, document_id, document_type)
            
            if not chunks:
                logger.warning(f"No chunks generated for document {document_id}")
                return True
            
            # Generate embeddings
            chunks_with_embeddings = self.generate_embeddings(chunks)
            
            # Store in database
            return self.store_document_chunks(chunks_with_embeddings)
            
        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}")
            return False
    
    def semantic_search(self, query: str, document_types: Optional[List[str]] = None,
                       limit: int = 10, similarity_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Perform semantic search across document chunks
        
        Args:
            query: Search query
            document_types: Optional list of document types to filter
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of matching chunks with similarity scores
        """
        try:
            # Check if pgvector functions are available
            try:
                # Test if semantic_search function exists
                test_query = text("SELECT 1 FROM pg_proc WHERE proname = 'semantic_search'")
                result = self.db.session.execute(test_query)
                has_semantic_search = result.scalar() is not None
            except:
                has_semantic_search = False
            
            if not has_semantic_search:
                logger.info("pgvector functions not available, using fallback text search")
                return self._fallback_text_search(query, document_types, limit)
            
            # Generate embedding for query
            query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
            
            # Try pgvector-based search
            try:
                embedding_str = '[' + ','.join(map(str, query_embedding.tolist())) + ']'
                
                # Execute semantic search
                search_query = text("""
                    SELECT * FROM semantic_search(
                        :query_embedding::vector,
                        :document_types,
                        :limit,
                        :similarity_threshold
                    )
                """)
                
                result = self.db.session.execute(search_query, {
                    'query_embedding': embedding_str,
                    'document_types': document_types,
                    'limit': limit,
                    'similarity_threshold': similarity_threshold
                })
                
            except Exception as pgvector_error:
                logger.warning(f"pgvector search failed, falling back to basic search: {pgvector_error}")
                # Rollback the failed transaction
                self.db.session.rollback()
                # Fallback to basic text search when pgvector is not available
                return self._fallback_text_search(query, document_types, limit)
            
            results = []
            for row in result:
                results.append({
                    'document_id': row.document_id,
                    'document_type': row.document_type,
                    'chunk_index': row.chunk_index,
                    'content': row.content,
                    'similarity_score': float(row.similarity_score),
                    'metadata': row.metadata,
                    'token_count': row.token_count
                })
            
            logger.info(f"Semantic search returned {len(results)} results for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def hybrid_search(self, query: str, document_types: Optional[List[str]] = None,
                     limit: int = 10, semantic_weight: float = 0.7, 
                     keyword_weight: float = 0.3) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword search
        
        Args:
            query: Search query
            document_types: Optional list of document types to filter
            limit: Maximum number of results
            semantic_weight: Weight for semantic similarity
            keyword_weight: Weight for keyword matching
            
        Returns:
            List of matching chunks with combined scores
        """
        try:
            # Generate embedding for query
            query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
            embedding_str = '[' + ','.join(map(str, query_embedding.tolist())) + ']'
            
            # Execute hybrid search
            search_query = text("""
                SELECT * FROM hybrid_search(
                    :query_embedding::vector,
                    :keywords,
                    :document_types,
                    :limit,
                    :semantic_weight,
                    :keyword_weight
                )
            """)
            
            result = self.db.session.execute(search_query, {
                'query_embedding': embedding_str,
                'keywords': query,
                'document_types': document_types,
                'limit': limit,
                'semantic_weight': semantic_weight,
                'keyword_weight': keyword_weight
            })
            
            results = []
            for row in result:
                results.append({
                    'document_id': row.document_id,
                    'document_type': row.document_type,
                    'chunk_index': row.chunk_index,
                    'content': row.content,
                    'combined_score': float(row.combined_score),
                    'semantic_score': float(row.semantic_score),
                    'keyword_score': float(row.keyword_score),
                    'metadata': row.metadata
                })
            
            logger.info(f"Hybrid search returned {len(results)} results for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []
    
    def find_related_context(self, document_id: str, document_type: str, 
                           limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find contextually related documents based on semantic similarity
        
        Args:
            document_id: Source document ID
            document_type: Source document type
            limit: Maximum number of related documents
            
        Returns:
            List of related document chunks
        """
        try:
            search_query = text("""
                SELECT * FROM find_related_context(
                    :document_id,
                    :document_type,
                    :limit
                )
            """)
            
            result = self.db.session.execute(search_query, {
                'document_id': document_id,
                'document_type': document_type,
                'limit': limit
            })
            
            results = []
            for row in result:
                results.append({
                    'document_id': row.related_document_id,
                    'document_type': row.related_document_type,
                    'chunk_index': row.chunk_index,
                    'content': row.content,
                    'similarity_score': float(row.similarity_score),
                    'metadata': row.metadata
                })
            
            logger.info(f"Found {len(results)} related documents for {document_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to find related context: {e}")
            return []
    
    def search_similar_documents(self, query: str, project_id: Optional[str] = None, 
                               limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar documents (simplified interface for agents).
        
        Args:
            query: Search query
            project_id: Optional project filter
            limit: Maximum number of results
            
        Returns:
            List of similar document chunks
        """
        try:
            # Filter by project if specified
            document_types = None
            if project_id:
                # This would need to be implemented based on how project filtering works
                pass
            
            results = self.semantic_search(
                query=query,
                document_types=document_types,
                limit=limit,
                similarity_threshold=0.3
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search similar documents: {e}")
            return []
    
    def _fallback_text_search(self, query: str, document_types: Optional[List[str]] = None,
                             limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fallback text search when pgvector is not available
        Uses simple ILIKE search instead of vector similarity
        """
        try:
            # Build a simple text search query using ILIKE
            base_query = """
                SELECT 
                    document_id,
                    document_type,
                    chunk_index,
                    content,
                    CASE 
                        WHEN LOWER(content) LIKE LOWER(:query_exact) THEN 1.0
                        WHEN LOWER(content) LIKE LOWER(:query_partial) THEN 0.8
                        ELSE 0.5
                    END as similarity_score,
                    metadata,
                    token_count
                FROM document_chunks
                WHERE LOWER(content) LIKE LOWER(:query_partial)
            """
            
            if document_types:
                base_query += " AND document_type = ANY(:document_types)"
            
            base_query += " ORDER BY similarity_score DESC, LENGTH(content) ASC LIMIT :limit"
            
            search_query = text(base_query)
            
            # Create search patterns - be more flexible with word matching
            query_words = [word.strip() for word in query.lower().split() if len(word.strip()) > 2]
            
            # Create multiple search patterns for better matching
            if len(query_words) >= 2:
                # Try to match any combination of words
                query_partial = '%' + '%'.join(query_words[:3]) + '%'  # Use first 3 words
                query_exact = '%' + ' '.join(query_words[:2]) + '%'    # Use first 2 words as phrase
            else:
                query_partial = '%' + query.lower() + '%'
                query_exact = '%' + query.lower() + '%'
            
            params = {
                'query_exact': query_exact,
                'query_partial': query_partial,
                'limit': limit
            }
            
            if document_types:
                params['document_types'] = document_types
            
            result = self.db.session.execute(search_query, params)
            
            results = []
            for row in result:
                # Parse metadata JSON if it exists
                metadata = {}
                try:
                    if row.metadata:
                        import json
                        metadata = json.loads(row.metadata) if isinstance(row.metadata, str) else row.metadata
                except:
                    metadata = {}
                
                results.append({
                    'document_id': row.document_id,
                    'document_type': row.document_type,
                    'chunk_index': row.chunk_index,
                    'content': row.content,
                    'similarity_score': float(row.similarity_score),
                    'metadata': metadata,
                    'token_count': row.token_count
                })
            
            logger.info(f"Fallback text search returned {len(results)} results for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Fallback text search failed: {e}")
            # Rollback any failed transaction
            try:
                self.db.session.rollback()
            except:
                pass
            return []
    
    def get_ai_context(self, query: str, max_tokens: int = 2000, 
                      document_types: Optional[List[str]] = None) -> str:
        """
        Get relevant context for AI model calls based on semantic search
        
        Args:
            query: The query or prompt for context
            max_tokens: Maximum tokens to include in context
            document_types: Optional document types to search
            
        Returns:
            Formatted context string for AI models
        """
        try:
            # Perform semantic search to find relevant chunks
            results = self.semantic_search(
                query=query,
                document_types=document_types,
                limit=20,  # Get more results to select best ones
                similarity_threshold=0.2
            )
            
            if not results:
                return ""
            
            # Build context string within token limit
            context_parts = []
            current_tokens = 0
            
            for result in results:
                chunk_tokens = result['token_count']
                
                # Check if adding this chunk would exceed limit
                if current_tokens + chunk_tokens > max_tokens:
                    break
                
                # Format chunk with metadata
                chunk_context = f"[{result['document_type']}:{result['document_id']}]\n{result['content']}\n"
                context_parts.append(chunk_context)
                current_tokens += chunk_tokens
            
            context = "\n---\n".join(context_parts)
            
            if context:
                context = f"Relevant Context:\n{context}\n---\n"
            
            logger.info(f"Generated AI context with {current_tokens} tokens from {len(context_parts)} chunks")
            return context
            
        except Exception as e:
            logger.error(f"Failed to get AI context: {e}")
            return ""
    
    def process_code_repository(self, repo_path: str, project_id: str) -> bool:
        """
        Process all code files in a repository for semantic search
        
        Args:
            repo_path: Path to the repository
            project_id: Project identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            processed_files = 0
            
            # Define code file extensions to process
            code_extensions = {
                '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
                '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
                '.html', '.css', '.scss', '.less', '.sql', '.md', '.txt', '.json',
                '.yaml', '.yml', '.xml', '.sh', '.bash', '.dockerfile'
            }
            
            for root, dirs, files in os.walk(repo_path):
                # Skip common directories that don't contain useful code
                dirs[:] = [d for d in dirs if not d.startswith('.') and 
                          d not in {'node_modules', '__pycache__', 'venv', 'env', 'dist', 'build'}]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1].lower()
                    
                    if file_ext in code_extensions:
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            
                            if content.strip():
                                # Create document ID from relative path
                                rel_path = os.path.relpath(file_path, repo_path)
                                document_id = f"{project_id}:{rel_path}"
                                
                                # Process the file
                                if self.process_document(content, document_id, 'code_file'):
                                    processed_files += 1
                                
                        except Exception as e:
                            logger.warning(f"Failed to process file {file_path}: {e}")
                            continue
            
            logger.info(f"Processed {processed_files} code files for project {project_id}")
            return processed_files > 0
            
        except Exception as e:
            logger.error(f"Failed to process code repository: {e}")
            return False
    
    def get_document_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored documents and embeddings"""
        try:
            stats_query = text("""
                SELECT 
                    document_type,
                    COUNT(*) as chunk_count,
                    COUNT(DISTINCT document_id) as document_count,
                    AVG(token_count) as avg_tokens_per_chunk,
                    SUM(token_count) as total_tokens
                FROM document_chunks
                GROUP BY document_type
                ORDER BY chunk_count DESC
            """)
            
            result = self.db.session.execute(stats_query)
            
            stats = {
                'by_type': [],
                'total_chunks': 0,
                'total_documents': 0,
                'total_tokens': 0
            }
            
            for row in result:
                type_stats = {
                    'document_type': row.document_type,
                    'chunk_count': row.chunk_count,
                    'document_count': row.document_count,
                    'avg_tokens_per_chunk': float(row.avg_tokens_per_chunk or 0),
                    'total_tokens': row.total_tokens or 0
                }
                stats['by_type'].append(type_stats)
                stats['total_chunks'] += row.chunk_count
                stats['total_tokens'] += row.total_tokens or 0
            
            # Get unique document count across all types
            total_docs_query = text("SELECT COUNT(DISTINCT document_id) FROM document_chunks")
            result = self.db.session.execute(total_docs_query)
            stats['total_documents'] = result.scalar()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get document statistics: {e}")
            return {}


# Global instance
vector_service = None


def init_vector_service(db):
    """Initialize the global vector service instance"""
    global vector_service
    try:
        vector_service = VectorService(db)
        logger.info("Vector service initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize vector service: {e}")
        return False


def get_vector_service():
    """Get the global vector service instance"""
    return vector_service