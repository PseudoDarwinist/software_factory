"""
PRD Generation Configuration - Configuration management for PRD generation pipeline
Defines stages, dependencies, and generation parameters
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class GenerationStage(Enum):
    """PRD generation stages"""
    PRODUCT_SPEC = "product_spec"
    TECHNICAL_SPEC = "technical_spec"
    DIAGRAMS = "diagrams"
    IMPLEMENTATION_PLAN = "implementation_plan"


class ModelPreference(Enum):
    """Model preferences for different generation tasks"""
    FAST = "fast"           # Prefer fast models (Gemini Flash)
    QUALITY = "quality"     # Prefer high-quality models (Claude Opus)
    BALANCED = "balanced"   # Balance speed and quality (Claude Sonnet)
    COST_EFFECTIVE = "cost_effective"  # Prefer cost-effective models


@dataclass
class StageConfig:
    """Configuration for a single generation stage"""
    stage: GenerationStage
    enabled: bool = True
    max_tokens: int = 4000
    timeout_seconds: float = 300.0
    retry_attempts: int = 3
    model_preference: ModelPreference = ModelPreference.BALANCED
    preferred_models: List[str] = field(default_factory=list)
    excluded_models: List[str] = field(default_factory=list)
    dependencies: List[GenerationStage] = field(default_factory=list)
    fallback_enabled: bool = True
    quality_threshold: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationConfig:
    """Complete configuration for PRD generation pipeline"""
    # Stage configurations
    stages: Dict[GenerationStage, StageConfig] = field(default_factory=dict)
    
    # Global settings
    max_concurrent_stages: int = 2
    global_timeout_seconds: float = 1800.0  # 30 minutes
    fallback_enabled: bool = True
    quality_validation_enabled: bool = True
    
    # Template settings
    template_name: str = "comprehensive_prd_template"
    template_validation_enabled: bool = True
    
    # Output settings
    include_metadata: bool = True
    include_generation_comments: bool = True
    output_format: str = "markdown"  # markdown, json, hybrid
    
    # Error handling
    continue_on_stage_failure: bool = True
    max_stage_failures: int = 2
    
    # Performance settings
    enable_caching: bool = True
    cache_duration_hours: int = 24
    
    # Monitoring
    enable_metrics: bool = True
    log_level: str = "INFO"
    
    def __post_init__(self):
        """Initialize default stage configurations if not provided"""
        if not self.stages:
            self.stages = self._get_default_stage_configs()
    
    def _get_default_stage_configs(self) -> Dict[GenerationStage, StageConfig]:
        """Get default configurations for all stages"""
        return {
            GenerationStage.PRODUCT_SPEC: StageConfig(
                stage=GenerationStage.PRODUCT_SPEC,
                enabled=True,
                max_tokens=4000,
                timeout_seconds=300.0,
                retry_attempts=3,
                model_preference=ModelPreference.QUALITY,
                preferred_models=["claude-opus-4", "claude-sonnet-3.5"],
                dependencies=[],
                fallback_enabled=True,
                metadata={
                    "description": "Generate product specification sections",
                    "priority": "high",
                    "estimated_duration": "2-3 minutes"
                }
            ),
            GenerationStage.TECHNICAL_SPEC: StageConfig(
                stage=GenerationStage.TECHNICAL_SPEC,
                enabled=True,
                max_tokens=4000,
                timeout_seconds=300.0,
                retry_attempts=3,
                model_preference=ModelPreference.QUALITY,
                preferred_models=["claude-opus-4", "claude-sonnet-3.5"],
                dependencies=[GenerationStage.PRODUCT_SPEC],
                fallback_enabled=True,
                metadata={
                    "description": "Generate technical specification sections",
                    "priority": "high",
                    "estimated_duration": "2-3 minutes"
                }
            ),
            GenerationStage.DIAGRAMS: StageConfig(
                stage=GenerationStage.DIAGRAMS,
                enabled=True,
                max_tokens=3000,
                timeout_seconds=240.0,
                retry_attempts=3,
                model_preference=ModelPreference.BALANCED,
                preferred_models=["claude-sonnet-3.5", "gpt-4o"],
                dependencies=[GenerationStage.TECHNICAL_SPEC],
                fallback_enabled=True,
                metadata={
                    "description": "Generate Mermaid diagrams for technical sections",
                    "priority": "medium",
                    "estimated_duration": "1-2 minutes"
                }
            ),
            GenerationStage.IMPLEMENTATION_PLAN: StageConfig(
                stage=GenerationStage.IMPLEMENTATION_PLAN,
                enabled=True,
                max_tokens=4000,
                timeout_seconds=300.0,
                retry_attempts=3,
                model_preference=ModelPreference.BALANCED,
                preferred_models=["claude-sonnet-3.5", "gpt-4o"],
                dependencies=[GenerationStage.TECHNICAL_SPEC, GenerationStage.DIAGRAMS],
                fallback_enabled=True,
                metadata={
                    "description": "Generate implementation plan and file structure",
                    "priority": "medium",
                    "estimated_duration": "2-3 minutes"
                }
            )
        }


class ConfigManager:
    """Manages PRD generation configuration loading and validation"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "prd_generation.json"
        self._config_cache: Optional[GenerationConfig] = None
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
    
    def load_config(self, force_reload: bool = False) -> GenerationConfig:
        """
        Load configuration from file or return default
        
        Args:
            force_reload: Force reload from disk even if cached
            
        Returns:
            GenerationConfig instance
        """
        if not force_reload and self._config_cache is not None:
            return self._config_cache
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                config = self._deserialize_config(config_data)
                self._validate_config(config)
                
                self._config_cache = config
                logger.info(f"Loaded PRD generation config from {self.config_file}")
                return config
            else:
                logger.info("No config file found, using default configuration")
                config = GenerationConfig()
                self._save_default_config(config)
                self._config_cache = config
                return config
                
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using default")
            config = GenerationConfig()
            self._config_cache = config
            return config
    
    def save_config(self, config: GenerationConfig) -> bool:
        """
        Save configuration to file
        
        Args:
            config: Configuration to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            config_data = self._serialize_config(config)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self._config_cache = config
            logger.info(f"Saved PRD generation config to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def _serialize_config(self, config: GenerationConfig) -> Dict[str, Any]:
        """Serialize configuration to JSON-compatible dict"""
        config_dict = asdict(config)
        
        # Convert enums to strings
        stages_dict = {}
        for stage, stage_config in config.stages.items():
            stage_dict = asdict(stage_config)
            stage_dict['stage'] = stage.value
            stage_dict['model_preference'] = stage_config.model_preference.value
            stage_dict['dependencies'] = [dep.value for dep in stage_config.dependencies]
            stages_dict[stage.value] = stage_dict
        
        config_dict['stages'] = stages_dict
        return config_dict
    
    def _deserialize_config(self, config_data: Dict[str, Any]) -> GenerationConfig:
        """Deserialize configuration from JSON dict"""
        # Extract stages
        stages = {}
        if 'stages' in config_data:
            for stage_name, stage_data in config_data['stages'].items():
                try:
                    stage_enum = GenerationStage(stage_name)
                    
                    # Convert string values back to enums
                    stage_data['stage'] = stage_enum
                    stage_data['model_preference'] = ModelPreference(stage_data.get('model_preference', 'balanced'))
                    stage_data['dependencies'] = [
                        GenerationStage(dep) for dep in stage_data.get('dependencies', [])
                    ]
                    
                    stages[stage_enum] = StageConfig(**stage_data)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid stage config for {stage_name}: {e}")
        
        # Remove stages from config_data to avoid duplicate
        config_data_copy = config_data.copy()
        config_data_copy.pop('stages', None)
        
        # Create config with stages
        config = GenerationConfig(**config_data_copy)
        config.stages = stages
        
        return config
    
    def _validate_config(self, config: GenerationConfig) -> bool:
        """
        Validate configuration
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required stages
            required_stages = {GenerationStage.PRODUCT_SPEC, GenerationStage.TECHNICAL_SPEC}
            available_stages = set(config.stages.keys())
            
            missing_stages = required_stages - available_stages
            if missing_stages:
                logger.warning(f"Missing required stages: {[s.value for s in missing_stages]}")
            
            # Validate stage dependencies
            for stage, stage_config in config.stages.items():
                for dependency in stage_config.dependencies:
                    if dependency not in config.stages:
                        logger.error(f"Stage {stage.value} depends on missing stage {dependency.value}")
                        return False
            
            # Check for circular dependencies
            if self._has_circular_dependencies(config.stages):
                logger.error("Circular dependencies detected in stage configuration")
                return False
            
            # Validate timeouts and limits
            if config.global_timeout_seconds <= 0:
                logger.error("Global timeout must be positive")
                return False
            
            for stage_config in config.stages.values():
                if stage_config.timeout_seconds <= 0:
                    logger.error(f"Stage {stage_config.stage.value} timeout must be positive")
                    return False
                
                if stage_config.max_tokens <= 0:
                    logger.error(f"Stage {stage_config.stage.value} max_tokens must be positive")
                    return False
            
            logger.debug("Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False
    
    def _has_circular_dependencies(self, stages: Dict[GenerationStage, StageConfig]) -> bool:
        """Check for circular dependencies in stage configuration"""
        def visit(stage: GenerationStage, visited: set, rec_stack: set) -> bool:
            visited.add(stage)
            rec_stack.add(stage)
            
            stage_config = stages.get(stage)
            if stage_config:
                for dependency in stage_config.dependencies:
                    if dependency not in visited:
                        if visit(dependency, visited, rec_stack):
                            return True
                    elif dependency in rec_stack:
                        return True
            
            rec_stack.remove(stage)
            return False
        
        visited = set()
        for stage in stages:
            if stage not in visited:
                if visit(stage, visited, set()):
                    return True
        
        return False
    
    def _save_default_config(self, config: GenerationConfig):
        """Save default configuration to file"""
        try:
            self.save_config(config)
            logger.info("Saved default PRD generation configuration")
        except Exception as e:
            logger.warning(f"Could not save default config: {e}")
    
    def get_stage_config(self, stage: GenerationStage) -> Optional[StageConfig]:
        """Get configuration for a specific stage"""
        config = self.load_config()
        return config.stages.get(stage)
    
    def update_stage_config(self, stage: GenerationStage, updates: Dict[str, Any]) -> bool:
        """
        Update configuration for a specific stage
        
        Args:
            stage: Stage to update
            updates: Dictionary of updates to apply
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            config = self.load_config()
            
            if stage not in config.stages:
                logger.error(f"Stage {stage.value} not found in configuration")
                return False
            
            stage_config = config.stages[stage]
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(stage_config, key):
                    setattr(stage_config, key, value)
                else:
                    logger.warning(f"Unknown stage config field: {key}")
            
            return self.save_config(config)
            
        except Exception as e:
            logger.error(f"Failed to update stage config: {e}")
            return False
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get information about current configuration"""
        config = self.load_config()
        
        return {
            'config_file': str(self.config_file),
            'config_exists': self.config_file.exists(),
            'total_stages': len(config.stages),
            'enabled_stages': len([s for s in config.stages.values() if s.enabled]),
            'global_timeout': config.global_timeout_seconds,
            'fallback_enabled': config.fallback_enabled,
            'template_name': config.template_name,
            'stages': {
                stage.value: {
                    'enabled': stage_config.enabled,
                    'dependencies': [dep.value for dep in stage_config.dependencies],
                    'model_preference': stage_config.model_preference.value,
                    'timeout': stage_config.timeout_seconds
                }
                for stage, stage_config in config.stages.items()
            }
        }


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager()
    
    return _config_manager


def get_generation_config() -> GenerationConfig:
    """Get the current generation configuration"""
    return get_config_manager().load_config()


def update_generation_config(updates: Dict[str, Any]) -> bool:
    """
    Update generation configuration
    
    Args:
        updates: Dictionary of configuration updates
        
    Returns:
        True if updated successfully, False otherwise
    """
    try:
        config_manager = get_config_manager()
        config = config_manager.load_config()
        
        # Apply updates to config
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                logger.warning(f"Unknown config field: {key}")
        
        return config_manager.save_config(config)
        
    except Exception as e:
        logger.error(f"Failed to update generation config: {e}")
        return False