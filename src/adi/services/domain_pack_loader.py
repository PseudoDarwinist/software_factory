"""
Domain Pack loader with caching and fallback capabilities.

Provides the DomainPack class that loads domain-specific configuration
with Redis caching and automatic fallback to _default pack.
"""

import os
import yaml
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
import redis
import logging

from ..schemas.domain_pack import (
    PackConfig, 
    MetricsConfig, 
    FailureMode,
    validate_pack_config,
    validate_ontology,
    validate_metrics
)
from .domain_pack_validator import DomainPackValidator, DomainPackValidationError

logger = logging.getLogger(__name__)


class DomainPackLoadError(Exception):
    """Raised when Domain Pack loading fails."""
    pass


class DomainPack:
    """
    Domain Pack loader with lazy loading, caching, and fallback support.
    
    Loads domain-specific configuration from the file system with Redis caching
    for performance and automatic fallback to _default pack when project-specific
    pack is missing or invalid.
    """
    
    def __init__(
        self, 
        project_id: str,
        domain_packs_root: str = "domain-packs",
        redis_client: Optional[redis.Redis] = None,
        cache_ttl: int = 3600  # 1 hour
    ):
        self.project_id = project_id
        self.domain_packs_root = Path(domain_packs_root)
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl
        
        # Lazy-loaded components
        self._pack_config: Optional[PackConfig] = None
        self._ontology: Optional[List[FailureMode]] = None
        self._metrics: Optional[MetricsConfig] = None
        self._rules: Optional[Dict[str, Any]] = None
        self._knowledge: Optional[str] = None
        self._validators: Optional[Dict[str, Callable]] = None
        self._evals: Optional[Dict[str, Any]] = None
        self._mappings: Optional[Dict[str, Any]] = None
        
        # Pack resolution info
        self._resolved_pack_id: Optional[str] = None
        self._used_fallback: bool = False
        self._load_timestamp: Optional[datetime] = None
        
        self.validator = DomainPackValidator(str(self.domain_packs_root))
    
    @property
    def pack_id(self) -> str:
        """Get the resolved pack ID (may be _default if fallback was used)."""
        if self._resolved_pack_id is None:
            self._resolve_pack_id()
        return self._resolved_pack_id
    
    @property
    def used_fallback(self) -> bool:
        """Check if fallback to _default pack was used."""
        if self._resolved_pack_id is None:
            self._resolve_pack_id()
        return self._used_fallback
    
    def _resolve_pack_id(self) -> None:
        """Resolve which pack to use (project-specific or _default fallback)."""
        project_pack_path = self.domain_packs_root / self.project_id
        default_pack_path = self.domain_packs_root / "_default"
        
        # Try project-specific pack first
        if project_pack_path.exists():
            try:
                # Quick validation check
                self.validator.validate_pack_structure(self.project_id)
                self._resolved_pack_id = self.project_id
                self._used_fallback = False
                logger.info(f"Using project-specific pack for {self.project_id}")
                return
            except DomainPackValidationError as e:
                logger.warning(f"Project pack {self.project_id} invalid, falling back to _default: {e}")
        
        # Fall back to _default pack
        if default_pack_path.exists():
            try:
                self.validator.validate_pack_structure("_default")
                self._resolved_pack_id = "_default"
                self._used_fallback = True
                logger.info(f"Using _default pack for {self.project_id}")
                return
            except DomainPackValidationError as e:
                logger.error(f"Default pack is invalid: {e}")
                raise DomainPackLoadError(f"Both project pack and _default pack are invalid")
        
        # No valid pack found
        raise DomainPackLoadError(f"No valid domain pack found for project {self.project_id}")
    
    def _get_cache_key(self, component: str) -> str:
        """Generate Redis cache key for a pack component."""
        return f"adi:pack:{self.pack_id}:{component}:v1"
    
    def _get_from_cache(self, component: str) -> Optional[Any]:
        """Get component data from Redis cache."""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._get_cache_key(component)
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                if component in ['pack_config', 'ontology', 'metrics']:
                    return json.loads(cached_data)
                else:
                    return cached_data.decode('utf-8')
        except Exception as e:
            logger.warning(f"Cache read failed for {component}: {e}")
        
        return None
    
    def _set_cache(self, component: str, data: Any) -> None:
        """Store component data in Redis cache."""
        if not self.redis_client:
            return
        
        try:
            cache_key = self._get_cache_key(component)
            if component in ['pack_config', 'ontology', 'metrics']:
                cached_data = json.dumps(data, default=str)
            else:
                cached_data = str(data)
            
            self.redis_client.setex(cache_key, self.cache_ttl, cached_data)
        except Exception as e:
            logger.warning(f"Cache write failed for {component}: {e}")
    
    def _load_file_with_cache(self, filename: str, component: str) -> Any:
        """Load file with caching support."""
        # Try cache first
        cached_data = self._get_from_cache(component)
        if cached_data:
            logger.debug(f"Cache hit for {component}")
            return cached_data
        
        # Load from file system
        pack_path = self.domain_packs_root / self.pack_id
        file_path = pack_path / filename
        
        if not file_path.exists():
            raise DomainPackLoadError(f"Required file not found: {filename}")
        
        try:
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                try:
                    with open(file_path, 'r') as f:
                        data = yaml.safe_load(f)
                except yaml.constructor.ConstructorError as e:
                    # Handle YAML files with custom tags by loading as unsafe
                    logger.warning(f"YAML constructor error in {filename}, trying unsafe load: {e}")
                    with open(file_path, 'r') as f:
                        yaml_content = f.read()
                        # Replace problematic operators with quoted strings
                        yaml_content = yaml_content.replace('op: !=', 'op: "!="')
                        yaml_content = yaml_content.replace('op: ==', 'op: "=="')
                        yaml_content = yaml_content.replace('op: <=', 'op: "<="')
                        yaml_content = yaml_content.replace('op: >=', 'op: ">="')
                        yaml_content = yaml_content.replace('op: <', 'op: "<"')
                        yaml_content = yaml_content.replace('op: >', 'op: ">"')
                        data = yaml.safe_load(yaml_content)
            elif filename.endswith('.json'):
                with open(file_path, 'r') as f:
                    data = json.load(f)
            elif filename.endswith('.md'):
                with open(file_path, 'r') as f:
                    data = f.read()
            else:
                with open(file_path, 'r') as f:
                    data = f.read()
            
            # Cache the loaded data
            self._set_cache(component, data)
            logger.debug(f"Loaded and cached {component}")
            return data
            
        except Exception as e:
            raise DomainPackLoadError(f"Failed to load {filename}: {str(e)}")
    
    @property
    def pack_config(self) -> PackConfig:
        """Get pack configuration (lazy loaded)."""
        if self._pack_config is None:
            data = self._load_file_with_cache('pack.yaml', 'pack_config')
            self._pack_config = validate_pack_config(data)
        return self._pack_config
    
    @property
    def ontology(self) -> List[FailureMode]:
        """Get failure mode ontology (lazy loaded)."""
        if self._ontology is None:
            data = self._load_file_with_cache('ontology.json', 'ontology')
            self._ontology = validate_ontology(data)
        return self._ontology
    
    @property
    def metrics(self) -> MetricsConfig:
        """Get metrics configuration (lazy loaded)."""
        if self._metrics is None:
            data = self._load_file_with_cache('metrics.yaml', 'metrics')
            self._metrics = validate_metrics(data)
        return self._metrics
    
    @property
    def rules(self) -> Dict[str, Any]:
        """Get business rules (lazy loaded)."""
        if self._rules is None:
            try:
                self._rules = self._load_file_with_cache('policy/rules.yaml', 'rules')
            except DomainPackLoadError:
                logger.warning(f"No rules.yaml found for pack {self.pack_id}, using empty rules")
                self._rules = {'rules': []}
        return self._rules
    
    @property
    def knowledge(self) -> str:
        """Get domain knowledge (lazy loaded)."""
        if self._knowledge is None:
            try:
                self._knowledge = self._load_file_with_cache('policy/knowledge.md', 'knowledge')
            except DomainPackLoadError:
                logger.warning(f"No knowledge.md found for pack {self.pack_id}, using empty knowledge")
                self._knowledge = ""
        return self._knowledge
    
    def get_validator(self, name: str) -> Optional[Callable]:
        """
        Get a custom validator function by name.
        
        Args:
            name: Validator function name
            
        Returns:
            Validator function or None if not found
        """
        if self._validators is None:
            self._load_validators()
        
        return self._validators.get(name)
    
    def get_all_validators(self) -> Dict[str, Callable]:
        """Get all available custom validators."""
        if self._validators is None:
            self._load_validators()
        return self._validators.copy()
    
    def _load_validators(self) -> None:
        """Load custom validators from validators directory."""
        self._validators = {}
        
        validators_path = self.domain_packs_root / self.pack_id / 'validators'
        if not validators_path.exists():
            return
        
        # Try to import custom validators
        try:
            import sys
            import importlib.util
            
            # Load the validators module
            init_file = validators_path / '__init__.py'
            if init_file.exists():
                spec = importlib.util.spec_from_file_location(
                    f"domain_pack_{self.pack_id}_validators", 
                    init_file
                )
                if spec and spec.loader:
                    validators_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(validators_module)
                    
                    # Get registered validators
                    if hasattr(validators_module, 'CUSTOM_VALIDATORS'):
                        self._validators = validators_module.CUSTOM_VALIDATORS
                        logger.info(f"Loaded {len(self._validators)} custom validators for {self.pack_id}")
        
        except Exception as e:
            logger.warning(f"Failed to load custom validators for {self.pack_id}: {e}")
            self._validators = {}
    
    def get_metric_config(self, metric_key: str) -> Optional[Union[Dict[str, Any], Any]]:
        """
        Get configuration for a specific metric.
        
        Args:
            metric_key: The metric key to look up
            
        Returns:
            Metric configuration or None if not found
        """
        metrics = self.metrics
        
        # Check north-star metrics
        for metric in metrics.north_star:
            if metric.key == metric_key:
                return metric
        
        # Check supporting metrics
        for metric in metrics.supporting:
            if metric.key == metric_key:
                return metric
        
        return None
    
    def get_failure_modes(self) -> List[FailureMode]:
        """Get all failure modes from ontology."""
        return self.ontology
    
    def get_failure_mode_by_code(self, code: str) -> Optional[FailureMode]:
        """
        Get a specific failure mode by its code.
        
        Args:
            code: Failure mode code (e.g., 'Time.SLA')
            
        Returns:
            FailureMode or None if not found
        """
        for failure_mode in self.ontology:
            if failure_mode.code == code:
                return failure_mode
        return None
    
    def get_rules_for_event(self, event_type: str) -> List[Dict[str, Any]]:
        """
        Get business rules that apply to a specific event type.
        
        Args:
            event_type: The event type to filter rules for
            
        Returns:
            List of applicable rules
        """
        applicable_rules = []
        rules = self.rules.get('rules', [])
        
        for rule in rules:
            applies_when = rule.get('applies_when', {})
            if applies_when.get('event.type') == event_type:
                applicable_rules.append(rule)
        
        return applicable_rules
    
    def get_sla_for_event(self, event_type: str, **context) -> int:
        """
        Get SLA timeout for an event type with context-aware overrides.
        
        Args:
            event_type: The event type
            **context: Additional context (channel, market, airport, etc.)
            
        Returns:
            SLA timeout in milliseconds
        """
        pack_config = self.pack_config
        defaults = pack_config.defaults
        
        # Start with default SLA
        # Try to get specific event type SLA, fallback to default
        base_sla = getattr(defaults.sla, event_type, None)
        if base_sla is None:
            # Try with underscores instead of dots
            event_type_underscore = event_type.replace('.', '_')
            base_sla = getattr(defaults.sla, event_type_underscore, None)
        if base_sla is None:
            # Use the default SLA
            base_sla = defaults.sla.Event_Default
        
        # Apply overrides if available
        if defaults.sla_overrides:
            overrides = defaults.sla_overrides
            
            # Check channel-specific overrides
            if 'channel' in context and overrides.by_channel:
                channel_overrides = overrides.by_channel.get(context['channel'], {})
                if event_type in channel_overrides:
                    return channel_overrides[event_type]
            
            # Check market-specific overrides
            if 'market' in context and overrides.by_market:
                market_overrides = overrides.by_market.get(context['market'], {})
                if event_type in market_overrides:
                    return market_overrides[event_type]
            
            # Check airport-specific overrides
            if 'airport' in context and overrides.by_airport:
                airport_overrides = overrides.by_airport.get(context['airport'], {})
                if event_type in airport_overrides:
                    return airport_overrides[event_type]
            
            # Check delay window overrides
            if 'delay_minutes' in context and overrides.by_delay_window_minutes:
                delay_minutes = context['delay_minutes']
                for window_key, sla_value in overrides.by_delay_window_minutes.items():
                    if self._matches_delay_window(delay_minutes, window_key):
                        return sla_value
        
        return base_sla
    
    def _matches_delay_window(self, delay_minutes: int, window_key: str) -> bool:
        """Check if delay minutes matches a window pattern like 'Delay:120-240'."""
        if not window_key.startswith('Delay:'):
            return False
        
        window_spec = window_key[6:]  # Remove 'Delay:' prefix
        
        if '-' in window_spec:
            parts = window_spec.split('-')
            if len(parts) == 2:
                min_delay = int(parts[0])
                max_delay = int(parts[1]) if parts[1] != '*' else float('inf')
                return min_delay <= delay_minutes <= max_delay
        
        return False
    
    def get_eval_blueprints(self) -> Dict[str, Any]:
        """Get evaluation blueprints (lazy loaded)."""
        if self._evals is None:
            self._load_evals()
        return self._evals
    
    def _load_evals(self) -> None:
        """Load evaluation blueprints from evals directory."""
        self._evals = {}
        
        evals_path = self.domain_packs_root / self.pack_id / 'evals'
        if not evals_path.exists():
            return
        
        for eval_file in evals_path.glob('*.yaml'):
            try:
                with open(eval_file, 'r') as f:
                    eval_data = yaml.safe_load(f)
                self._evals[eval_file.stem] = eval_data
            except Exception as e:
                logger.warning(f"Failed to load eval blueprint {eval_file}: {e}")
    
    def get_mappings(self) -> Dict[str, Any]:
        """Get template mappings and other lookup tables (lazy loaded)."""
        if self._mappings is None:
            self._load_mappings()
        return self._mappings
    
    def _load_mappings(self) -> None:
        """Load mappings from mappings directory."""
        self._mappings = {}
        
        mappings_path = self.domain_packs_root / self.pack_id / 'mappings'
        if not mappings_path.exists():
            return
        
        for mapping_file in mappings_path.glob('*.yaml'):
            try:
                with open(mapping_file, 'r') as f:
                    mapping_data = yaml.safe_load(f)
                self._mappings[mapping_file.stem] = mapping_data
            except Exception as e:
                logger.warning(f"Failed to load mapping {mapping_file}: {e}")
        
        for mapping_file in mappings_path.glob('*.json'):
            try:
                with open(mapping_file, 'r') as f:
                    mapping_data = json.load(f)
                self._mappings[mapping_file.stem] = mapping_data
            except Exception as e:
                logger.warning(f"Failed to load mapping {mapping_file}: {e}")
    
    def reload(self) -> None:
        """Force reload of all pack components, bypassing cache."""
        logger.info(f"Reloading domain pack for {self.project_id}")
        
        # Clear cached components
        self._pack_config = None
        self._ontology = None
        self._metrics = None
        self._rules = None
        self._knowledge = None
        self._validators = None
        self._evals = None
        self._mappings = None
        
        # Clear resolution state
        self._resolved_pack_id = None
        self._used_fallback = False
        self._load_timestamp = None
        
        # Clear Redis cache if available
        if self.redis_client:
            try:
                pattern = f"adi:pack:{self.project_id}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                
                # Also clear _default cache if we might fall back to it
                default_pattern = f"adi:pack:_default:*"
                default_keys = self.redis_client.keys(default_pattern)
                if default_keys:
                    self.redis_client.delete(*default_keys)
                    
            except Exception as e:
                logger.warning(f"Failed to clear cache: {e}")
    
    def get_pack_info(self) -> Dict[str, Any]:
        """Get information about the loaded pack."""
        return {
            'project_id': self.project_id,
            'resolved_pack_id': self.pack_id,
            'used_fallback': self.used_fallback,
            'pack_name': self.pack_config.pack.name,
            'pack_version': self.pack_config.pack.version,
            'owner_team': self.pack_config.pack.owner_team,
            'load_timestamp': self._load_timestamp or datetime.now(),
            'failure_modes_count': len(self.ontology),
            'north_star_metrics_count': len(self.metrics.north_star),
            'supporting_metrics_count': len(self.metrics.supporting),
            'rules_count': len(self.rules.get('rules', [])),
            'has_knowledge': bool(self.knowledge.strip()),
            'custom_validators_count': len(self.get_all_validators())
        }


class DomainPackManager:
    """
    Manages multiple Domain Packs with versioning and rollback capabilities.
    """
    
    def __init__(
        self,
        domain_packs_root: str = "domain-packs",
        redis_client: Optional[redis.Redis] = None
    ):
        self.domain_packs_root = Path(domain_packs_root)
        self.redis_client = redis_client
        self._loaded_packs: Dict[str, DomainPack] = {}
        self.validator = DomainPackValidator(str(self.domain_packs_root))
    
    def get_pack(self, project_id: str) -> DomainPack:
        """
        Get a Domain Pack for a project (cached).
        
        Args:
            project_id: The project identifier
            
        Returns:
            DomainPack instance
        """
        if project_id not in self._loaded_packs:
            self._loaded_packs[project_id] = DomainPack(
                project_id=project_id,
                domain_packs_root=str(self.domain_packs_root),
                redis_client=self.redis_client
            )
        
        return self._loaded_packs[project_id]
    
    def reload_pack(self, project_id: str) -> DomainPack:
        """
        Force reload a Domain Pack.
        
        Args:
            project_id: The project identifier
            
        Returns:
            Reloaded DomainPack instance
        """
        if project_id in self._loaded_packs:
            self._loaded_packs[project_id].reload()
        else:
            self._loaded_packs[project_id] = DomainPack(
                project_id=project_id,
                domain_packs_root=str(self.domain_packs_root),
                redis_client=self.redis_client
            )
        
        return self._loaded_packs[project_id]
    
    def list_available_packs(self) -> List[str]:
        """List all available domain packs."""
        return self.validator.list_available_packs()
    
    def validate_pack(self, pack_id: str) -> Dict[str, Any]:
        """Validate a specific domain pack."""
        return self.validator.validate_complete_pack(pack_id)
    
    def create_pack_version_snapshot(self, project_id: str) -> str:
        """
        Create a versioned snapshot of a domain pack.
        
        Args:
            project_id: The project identifier
            
        Returns:
            Version identifier for the snapshot
        """
        pack = self.get_pack(project_id)
        version_id = f"{pack.pack_config.pack.version}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Create snapshot directory
        snapshot_path = self.domain_packs_root / f"{pack.pack_id}-{version_id}"
        
        # Copy current pack to snapshot
        import shutil
        current_pack_path = self.domain_packs_root / pack.pack_id
        shutil.copytree(current_pack_path, snapshot_path)
        
        logger.info(f"Created pack snapshot: {snapshot_path}")
        return version_id
    
    def rollback_pack(self, project_id: str, version_id: str) -> None:
        """
        Rollback a domain pack to a previous version.
        
        Args:
            project_id: The project identifier
            version_id: The version to rollback to
        """
        pack = self.get_pack(project_id)
        snapshot_path = self.domain_packs_root / f"{pack.pack_id}-{version_id}"
        
        if not snapshot_path.exists():
            raise DomainPackLoadError(f"Version snapshot not found: {version_id}")
        
        # Backup current version first
        current_backup_id = self.create_pack_version_snapshot(project_id)
        logger.info(f"Created backup before rollback: {current_backup_id}")
        
        # Replace current pack with snapshot
        import shutil
        current_pack_path = self.domain_packs_root / pack.pack_id
        shutil.rmtree(current_pack_path)
        shutil.copytree(snapshot_path, current_pack_path)
        
        # Force reload the pack
        self.reload_pack(project_id)
        
        logger.info(f"Rolled back {project_id} to version {version_id}")


# Global domain pack manager instance
_domain_pack_manager: Optional[DomainPackManager] = None


def get_domain_pack_manager(
    domain_packs_root: str = "domain-packs",
    redis_client: Optional[redis.Redis] = None
) -> DomainPackManager:
    """Get the global domain pack manager instance."""
    global _domain_pack_manager
    
    if _domain_pack_manager is None:
        _domain_pack_manager = DomainPackManager(domain_packs_root, redis_client)
    
    return _domain_pack_manager


def get_domain_pack(project_id: str) -> DomainPack:
    """
    Convenience function to get a Domain Pack for a project.
    
    Args:
        project_id: The project identifier
        
    Returns:
        DomainPack instance
    """
    manager = get_domain_pack_manager()
    return manager.get_pack(project_id)