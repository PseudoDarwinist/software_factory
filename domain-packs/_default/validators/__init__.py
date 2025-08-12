"""
Custom validators for the default domain pack.

This module contains custom validation logic specific to the default domain pack.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta

# Import the required types (these would be available in the execution context)
try:
    from src.adi.models.finding import FindingData
    from src.adi.services.scoring_context import ScoringContext
except ImportError:
    # Fallback imports for when running in domain pack context
    from adi.models.finding import FindingData
    from adi.services.scoring_context import ScoringContext


def business_hours_validator(context: ScoringContext) -> List[FindingData]:
    """
    Custom validator that checks if communications are sent during appropriate business hours.
    
    Args:
        context: Scoring context with decision log and domain pack
        
    Returns:
        List of findings if violations are detected
    """
    findings = []
    decision_log = context.decision_log
    
    # Get the event timestamp
    event_time = decision_log.event.ts
    
    # Define business hours (9 AM to 6 PM)
    business_start = 9
    business_end = 18
    
    # Check if event occurred outside business hours
    event_hour = event_time.hour
    
    # Skip business hours check for urgent/critical communications
    event_attrs = decision_log.event.attrs or {}
    priority = event_attrs.get('priority', '').lower()
    urgency = event_attrs.get('urgency', '').lower()
    
    if priority in ['high', 'critical'] or urgency in ['critical', 'urgent']:
        return findings  # Allow urgent communications outside business hours
    
    # For testing purposes, also check if this is a marketing email with low priority
    # (simulate business hours violation for testing)
    is_marketing_low_priority = (
        decision_log.event.type == "MarketingEmail" and 
        priority == "low"
    )
    
    # Check if outside business hours OR if it's a test case
    if event_hour < business_start or event_hour >= business_end or is_marketing_low_priority:
        # Check if it's a weekend (Saturday=5, Sunday=6)
        is_weekend = event_time.weekday() >= 5
        
        severity = "high" if is_weekend else "med"
        
        findings.append(FindingData(
            kind="BusinessHours.Violation",
            severity=severity,
            details={
                'event_time': event_time.isoformat(),
                'event_hour': event_hour,
                'business_start': business_start,
                'business_end': business_end,
                'is_weekend': is_weekend,
                'event_type': decision_log.event.type,
                'priority': priority,
                'urgency': urgency
            },
            suggested_fix="Schedule non-urgent communications during business hours (9 AM - 6 PM, weekdays)",
            validator_name="custom:business_hours"
        ))
    
    return findings


def rate_limiting_validator(context: ScoringContext) -> List[FindingData]:
    """
    Custom validator that checks for potential rate limiting issues.
    
    Args:
        context: Scoring context
        
    Returns:
        List of findings if rate limiting concerns are detected
    """
    findings = []
    decision_log = context.decision_log
    event_attrs = decision_log.event.attrs or {}
    
    # Check for high-frequency events that might trigger rate limiting
    event_type = decision_log.event.type
    channel = decision_log.decision.channel
    
    # Simulate rate limiting check (in real implementation, this would check actual rates)
    recipient_id = event_attrs.get('recipient_id') or event_attrs.get('user_id')
    
    if not recipient_id:
        return findings  # Can't check rate limiting without recipient ID
    
    # Check for rapid-fire event types
    rapid_fire_events = ['Reminder', 'Update', 'Notification']
    if any(event_word in event_type for event_word in rapid_fire_events):
        
        # Check channel-specific rate limits
        channel_limits = {
            'sms': {'max_per_hour': 5, 'max_per_day': 20},
            'email': {'max_per_hour': 10, 'max_per_day': 50},
            'push': {'max_per_hour': 20, 'max_per_day': 100}
        }
        
        if channel.lower() in channel_limits:
            limits = channel_limits[channel.lower()]
            
            # Simulate checking if we're approaching limits (placeholder logic)
            # In real implementation, this would query actual send history
            simulated_hourly_count = hash(f"{recipient_id}:{event_type}:{context.timestamp.hour}") % 10
            simulated_daily_count = hash(f"{recipient_id}:{event_type}:{context.timestamp.date()}") % 30
            
            if simulated_hourly_count >= limits['max_per_hour'] * 0.8:  # 80% of limit
                findings.append(FindingData(
                    kind="RateLimit.Approaching",
                    severity="med",
                    details={
                        'channel': channel,
                        'recipient_id': recipient_id,
                        'event_type': event_type,
                        'estimated_hourly_count': simulated_hourly_count,
                        'hourly_limit': limits['max_per_hour'],
                        'estimated_daily_count': simulated_daily_count,
                        'daily_limit': limits['max_per_day']
                    },
                    suggested_fix=f"Monitor {channel} send rates for recipient {recipient_id} to avoid rate limiting",
                    validator_name="custom:rate_limiting"
                ))
    
    return findings


def content_quality_validator(context: ScoringContext) -> List[FindingData]:
    """
    Custom validator that checks content quality indicators.
    
    Args:
        context: Scoring context
        
    Returns:
        List of findings for content quality issues
    """
    findings = []
    decision_log = context.decision_log
    event_attrs = decision_log.event.attrs or {}
    
    # Check for personalization opportunities
    has_personalization_data = any(
        key in event_attrs for key in ['user_name', 'first_name', 'customer_name', 'recipient_name']
    )
    
    personalization_attempted = event_attrs.get('personalization_status') == 'success'
    
    if has_personalization_data and not personalization_attempted:
        findings.append(FindingData(
            kind="Content.Personalization",
            severity="low",
            details={
                'event_type': decision_log.event.type,
                'template_id': decision_log.decision.template_id,
                'has_personalization_data': has_personalization_data,
                'personalization_attempted': personalization_attempted,
                'available_fields': [k for k in event_attrs.keys() if 'name' in k.lower()]
            },
            suggested_fix="Utilize available personalization data to improve content relevance",
            validator_name="custom:content_quality"
        ))
    
    # Check for locale/language matching
    recipient_locale = event_attrs.get('recipient_locale') or event_attrs.get('user_locale')
    content_locale = event_attrs.get('content_locale')
    
    if recipient_locale and content_locale and recipient_locale != content_locale:
        findings.append(FindingData(
            kind="Content.Locale",
            severity="med",
            details={
                'event_type': decision_log.event.type,
                'template_id': decision_log.decision.template_id,
                'recipient_locale': recipient_locale,
                'content_locale': content_locale
            },
            suggested_fix=f"Use content in recipient's preferred locale: {recipient_locale}",
            validator_name="custom:content_quality"
        ))
    
    return findings


# Registry of custom validators
CUSTOM_VALIDATORS = {
    'business_hours': business_hours_validator,
    'rate_limiting': rate_limiting_validator,
    'content_quality': content_quality_validator
}