"""
Capture Agent - Intelligent idea processing from Slack and external sources
Subscribes to slack.message.received events and publishes idea.captured events
"""

import logging
import uuid
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import BaseAgent, AgentConfig, EventProcessingResult, ProjectContext
from ..events.domain_events import SlackMessageReceivedEvent, IdeaCapturedEvent
from ..events.base import BaseEvent
from ..services.ai_broker import AIBroker, AIRequest, TaskType, Priority

logger = logging.getLogger(__name__)


class CaptureAgent(BaseAgent):
    """
    Capture Agent for intelligent idea processing from external sources
    
    Responsibilities:
    - Process incoming Slack messages
    - Extract entities using project system map
    - Categorize ideas by severity using AI analysis
    - Enrich ideas with vector search for similar historical items
    - Publish idea.captured events
    """
    
    def __init__(self, event_bus, ai_broker: Optional[AIBroker] = None):
        config = AgentConfig(
            agent_id="capture_agent",
            name="Capture Agent",
            description="Processes external inputs and captures ideas with intelligent analysis",
            event_types=["slack.message.received"],
            max_concurrent_events=3,
            retry_attempts=2,
            timeout_seconds=60.0
        )
        
        super().__init__(config, event_bus)
        self.ai_broker = ai_broker
        
        # Entity extraction patterns
        self.entity_patterns = {
            'bug': r'\b(?:bug|error|issue|problem|broken|fail|crash|exception)\b',
            'feature': r'\b(?:feature|enhancement|improvement|add|new|implement)\b',
            'performance': r'\b(?:slow|fast|performance|speed|optimize|lag|timeout)\b',
            'ui_ux': r'\b(?:ui|ux|interface|design|user|experience|usability)\b',
            'security': r'\b(?:security|auth|login|permission|access|vulnerability)\b',
            'integration': r'\b(?:api|integration|connect|sync|webhook|third.party)\b',
            'data': r'\b(?:data|database|query|storage|backup|migration)\b'
        }
        
        # Severity keywords for initial classification
        self.severity_keywords = {
            'critical': r'\b(?:critical|urgent|emergency|down|outage|broken|crash)\b',
            'high': r'\b(?:important|high|priority|asap|soon|major)\b',
            'medium': r'\b(?:medium|moderate|normal|standard)\b',
            'low': r'\b(?:low|minor|nice.to.have|someday|eventually)\b'
        }
    
    def process_event(self, event: BaseEvent) -> EventProcessingResult:
        """Process slack.message.received events and capture ideas"""
        start_time = datetime.utcnow()
        
        try:
            if not isinstance(event, SlackMessageReceivedEvent):
                return EventProcessingResult(
                    success=False,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=0.0,
                    error_message="Event is not a SlackMessageReceivedEvent"
                )
            
            logger.info(f"Processing Slack message from channel {event.channel_id} in project {event.project_id}")
            
            # Skip if message is too short or looks like noise
            if not self._is_valid_idea_message(event.content):
                logger.debug(f"Skipping message - not a valid idea: {event.content[:50]}...")
                return EventProcessingResult(
                    success=True,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    result_data={'action': 'skipped', 'reason': 'not_valid_idea'}
                )
            
            # Get project context for entity recognition
            project_context = self.get_project_context(event.project_id)
            
            # Extract entities using system map and pattern matching
            entities = self._extract_entities(event.content, project_context)
            
            # Perform initial severity classification
            initial_severity = self._classify_initial_severity(event.content)
            
            # Get vector context for similar historical items
            similar_items = []
            try:
                similar_items = self.get_vector_context(
                    query=event.content,
                    project_id=event.project_id,
                    limit=3
                )
            except Exception as e:
                logger.warning(f"Vector context retrieval failed: {e}")
                similar_items = []
            
            # Use AI for enhanced categorization and severity analysis
            ai_analysis = None
            if self.ai_broker:
                ai_analysis = self._perform_ai_analysis(
                    content=event.content,
                    entities=entities,
                    project_context=project_context,
                    similar_items=similar_items
                )
            
            # Determine final severity
            final_severity = self._determine_final_severity(
                initial_severity=initial_severity,
                ai_analysis=ai_analysis
            )
            
            # Create enriched tags
            tags = self._create_tags(entities, ai_analysis)
            
            # Generate idea ID
            idea_id = f"idea_{event.project_id}_{uuid.uuid4().hex[:8]}"
            
            # Create idea.captured event
            idea_captured_event = IdeaCapturedEvent(
                idea_id=idea_id,
                project_id=event.project_id,
                content=event.content,
                source=f"slack:{event.channel_id}",
                tags=tags,
                severity=final_severity,
                correlation_id=event.metadata.correlation_id,
                actor=event.author
            )
            
            # Add enrichment metadata to the event payload instead of metadata
            enrichment_data = {
                'original_message_id': event.aggregate_id,  # message_id is stored as aggregate_id
                'channel_id': event.channel_id,
                'author': event.author,
                'entities': entities,
                'similar_items_count': len(similar_items),
                'ai_analysis': ai_analysis,
                'processing_agent': self.config.agent_id
            }
            
            # Store enrichment data in the event's custom attributes
            for key, value in enrichment_data.items():
                setattr(idea_captured_event, key, value)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Captured idea {idea_captured_event.aggregate_id} with severity {final_severity} and {len(tags)} tags")
            
            return EventProcessingResult(
                success=True,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=processing_time,
                result_data={
                    'idea_id': idea_id,
                    'severity': final_severity,
                    'tags': tags,
                    'entities': entities,
                    'similar_items_count': len(similar_items)
                },
                generated_events=[idea_captured_event]
            )
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Failed to process Slack message: {e}")
            
            return EventProcessingResult(
                success=False,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=processing_time,
                error_message=str(e)
            )
    
    def _is_valid_idea_message(self, content: str) -> bool:
        """Check if a message contains a valid idea worth capturing"""
        if not content or len(content.strip()) < 10:
            return False
        
        # Skip common noise patterns
        noise_patterns = [
            r'^(ok|okay|yes|no|thanks|thank you|got it|sure)$',
            r'^(lol|haha|😂|👍|👎)$',
            r'^(good morning|good afternoon|hello|hi|hey)$',
            r'^\+1$',
            r'^(done|completed|finished)$'
        ]
        
        content_lower = content.lower().strip()
        for pattern in noise_patterns:
            if re.match(pattern, content_lower, re.IGNORECASE):
                return False
        
        # Look for idea indicators
        idea_indicators = [
            r'\b(?:should|could|would|might|maybe|perhaps|what if|how about)\b',
            r'\b(?:idea|suggestion|proposal|thought|consider)\b',
            r'\b(?:problem|issue|bug|error|improvement|feature)\b',
            r'\b(?:why don\'t we|we should|we could|let\'s)\b',
            r'[?!]',  # Questions and exclamations often contain ideas
        ]
        
        for pattern in idea_indicators:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        # If message is longer than 20 words, likely contains substance
        if len(content.split()) > 20:
            return True
        
        return False
    
    def _extract_entities(self, content: str, project_context: ProjectContext) -> List[str]:
        """Extract entities from message content using system map and patterns"""
        entities = []
        content_lower = content.lower()
        
        # Extract entities using predefined patterns
        for entity_type, pattern in self.entity_patterns.items():
            if re.search(pattern, content_lower, re.IGNORECASE):
                entities.append(entity_type)
        
        # Extract entities from project system map
        if project_context.system_map:
            system_map = project_context.system_map
            
            # Look for component names
            components = system_map.get('components', [])
            for component in components:
                if isinstance(component, dict):
                    name = component.get('name', '').lower()
                    if name and name in content_lower:
                        entities.append(f"component:{name}")
                elif isinstance(component, str):
                    if component.lower() in content_lower:
                        entities.append(f"component:{component.lower()}")
            
            # Look for technology mentions
            technologies = system_map.get('technologies', [])
            for tech in technologies:
                if isinstance(tech, str) and tech.lower() in content_lower:
                    entities.append(f"tech:{tech.lower()}")
        
        # Remove duplicates and return
        return list(set(entities))
    
    def _classify_initial_severity(self, content: str) -> str:
        """Perform initial severity classification using keyword patterns"""
        content_lower = content.lower()
        
        # Check for severity keywords in order of priority
        for severity, pattern in self.severity_keywords.items():
            if re.search(pattern, content_lower, re.IGNORECASE):
                return severity
        
        # Default classification based on content characteristics
        if any(word in content_lower for word in ['bug', 'error', 'broken', 'crash', 'fail']):
            return 'high'
        elif any(word in content_lower for word in ['feature', 'improvement', 'enhancement']):
            return 'medium'
        else:
            return 'low'
    
    def _perform_ai_analysis(self, content: str, entities: List[str], 
                           project_context: ProjectContext, similar_items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Use AI to analyze content for enhanced categorization and severity"""
        try:
            # Prepare context for AI analysis
            context_parts = [
                f"Message: {content}",
                f"Detected entities: {', '.join(entities) if entities else 'None'}",
            ]
            
            if project_context.system_map:
                context_parts.append(f"Project components: {', '.join([str(c) for c in project_context.system_map.get('components', [])])}")
            
            if similar_items:
                context_parts.append(f"Similar historical items found: {len(similar_items)}")
                for item in similar_items[:2]:  # Include top 2 similar items
                    context_parts.append(f"- {item.get('content', '')[:100]}...")
            
            analysis_prompt = f"""
Analyze this Slack message for idea capture in a software development context:

{chr(10).join(context_parts)}

Please provide:
1. Severity level (critical/high/medium/low) with reasoning
2. Category (bug/feature/performance/ui_ux/security/integration/data/other)
3. Key themes or topics (2-3 words each)
4. Urgency assessment (urgent/normal/low)
5. Confidence score (0.0-1.0) for your analysis

Respond in JSON format:
{{
    "severity": "medium",
    "severity_reasoning": "explanation",
    "category": "feature",
    "themes": ["user-experience", "mobile"],
    "urgency": "normal",
    "confidence": 0.8
}}
"""
            
            # Create AI request
            ai_request = AIRequest(
                request_id=f"capture_analysis_{uuid.uuid4().hex[:8]}",
                task_type=TaskType.ANALYSIS,
                instruction=analysis_prompt,
                priority=Priority.NORMAL,
                max_tokens=500,
                timeout_seconds=30.0,
                metadata={'agent': self.config.agent_id}
            )
            
            # Submit request synchronously with short timeout
            response = self.ai_broker.submit_request_sync(ai_request, timeout=30.0)
            
            if response.success:
                # Try to parse JSON response
                import json
                try:
                    analysis = json.loads(response.content)
                    logger.debug(f"AI analysis completed with confidence {analysis.get('confidence', 0.0)}")
                    return analysis
                except json.JSONDecodeError:
                    logger.warning("AI response was not valid JSON, using text analysis")
                    return {
                        'severity': 'medium',
                        'category': 'other',
                        'themes': [],
                        'urgency': 'normal',
                        'confidence': 0.5,
                        'raw_response': response.content
                    }
            else:
                logger.warning(f"AI analysis failed: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return None
    
    def _determine_final_severity(self, initial_severity: str, ai_analysis: Optional[Dict[str, Any]]) -> str:
        """Determine final severity combining initial classification and AI analysis"""
        if not ai_analysis:
            return initial_severity
        
        ai_severity = ai_analysis.get('severity', initial_severity)
        confidence = ai_analysis.get('confidence', 0.0)
        
        # If AI confidence is high, use AI severity
        if confidence >= 0.7:
            return ai_severity
        
        # If AI confidence is medium, blend with initial classification
        if confidence >= 0.4:
            severity_weights = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
            initial_weight = severity_weights.get(initial_severity, 2)
            ai_weight = severity_weights.get(ai_severity, 2)
            
            # Weighted average, leaning toward higher severity
            avg_weight = (initial_weight + ai_weight * confidence) / (1 + confidence)
            
            if avg_weight >= 3.5:
                return 'critical'
            elif avg_weight >= 2.5:
                return 'high'
            elif avg_weight >= 1.5:
                return 'medium'
            else:
                return 'low'
        
        # Low confidence, stick with initial classification
        return initial_severity
    
    def _create_tags(self, entities: List[str], ai_analysis: Optional[Dict[str, Any]]) -> List[str]:
        """Create comprehensive tags from entities and AI analysis"""
        tags = []
        
        # Add entity-based tags
        for entity in entities:
            if ':' in entity:
                # Structured entity like "component:auth"
                tags.append(entity)
            else:
                # Simple entity like "bug"
                tags.append(entity)
        
        # Add AI-derived tags
        if ai_analysis:
            category = ai_analysis.get('category')
            if category and category not in tags:
                tags.append(category)
            
            themes = ai_analysis.get('themes', [])
            for theme in themes:
                if theme and theme not in tags:
                    tags.append(theme)
            
            urgency = ai_analysis.get('urgency')
            if urgency and urgency != 'normal':
                tags.append(f"urgency:{urgency}")
        
        # Add source tag
        tags.append('source:slack')
        
        # Limit tags and clean up
        tags = [tag.strip().lower() for tag in tags if tag and tag.strip()]
        tags = list(set(tags))  # Remove duplicates
        
        return tags[:10]  # Limit to 10 tags


def create_capture_agent(event_bus, ai_broker: Optional[AIBroker] = None) -> CaptureAgent:
    """Factory function to create a Capture Agent"""
    return CaptureAgent(event_bus, ai_broker)