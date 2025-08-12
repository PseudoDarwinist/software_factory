# Default Domain Pack Knowledge

## Overview

This is the default domain pack that serves as a fallback for any application domain that doesn't have its own specific domain pack. It contains universal failure modes and metrics that apply across different industries and use cases.

## Universal Business Rules

### Timing and SLA Management
- All communications should be sent within defined SLA timeframes
- High-priority messages (alerts) should be processed faster than low-priority ones
- Different channels may have different SLA expectations (SMS faster than email)

### Content and Template Management
- Templates should be selected based on event type and channel
- Content should be personalized when possible
- Locale and language should match recipient preferences

### Delivery and Audience Management
- Messages should only be sent to eligible recipients
- Duplicate messages within a time window should be suppressed
- Blocklisted recipients should be excluded from sends
- Consent requirements must be respected

### Compliance and Policy
- All applicable business rules and regulations must be followed
- Consent must be valid and current
- Data privacy requirements must be respected

## Common Failure Patterns

### Timing Issues
- **Late sends**: Messages sent after SLA deadline
- **Time window violations**: Messages sent outside allowed time windows

### Content Issues
- **Wrong templates**: Incorrect template selected for event/channel combination
- **Personalization failures**: Unable to personalize content with recipient data
- **Locale mismatches**: Content language doesn't match recipient preferences

### Delivery Issues
- **Blocked recipients**: Messages to blocklisted contacts
- **Invalid contacts**: Messages to invalid email/phone numbers
- **Duplicate sends**: Same message sent multiple times to same recipient

### Compliance Issues
- **Missing consent**: Messages sent without valid consent
- **Policy violations**: Business rules not followed correctly
- **Data issues**: Required data missing or invalid

## Troubleshooting Guide

### High Latency
1. Check system load and processing queues
2. Verify template rendering performance
3. Review personalization data lookup times
4. Check external service dependencies

### Low Delivery Success Rate
1. Review blocklist management
2. Validate contact data quality
3. Check consent coverage
4. Monitor external delivery service status

### Template Selection Issues
1. Verify event-to-template mapping configuration
2. Check template availability for all channels
3. Review template selection logic
4. Validate template content and formatting

### Compliance Violations
1. Review consent collection and validation processes
2. Audit business rule implementation
3. Check data privacy controls
4. Validate regulatory requirement compliance

## Metrics Interpretation

### North Star Metrics
- **OnTimeRate**: Primary indicator of system performance - should be >95%

### Supporting Metrics
- **P95Latency**: Response time indicator - should be <3 seconds
- **TemplateAccuracy**: Content quality indicator - should be >98%
- **DeliverySuccessRate**: Delivery reliability - should be >99%
- **ConsentCoverage**: Compliance indicator - should be >99%

## References

- This is a generic fallback pack - create domain-specific packs for better performance
- Domain-specific packs should inherit from these universal patterns where applicable
- Regular review and updates needed as new failure patterns emerge