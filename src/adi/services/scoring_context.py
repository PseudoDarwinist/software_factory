"""
Scoring Context

Shared context data structure for scoring pipeline and validators.
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any

from ..schemas.decision_log import DecisionLog
from .domain_pack_loader import DomainPack


@dataclass
class ScoringContext:
    """Context information for scoring a decision log."""
    project_id: str
    case_id: str
    decision_log: DecisionLog
    domain_pack: DomainPack
    timestamp: datetime
    relevant_knowledge: List[Dict[str, Any]] = field(default_factory=list)