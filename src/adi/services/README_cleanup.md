# Decision Log Cleanup System

The Decision Log Cleanup System provides automatic cleanup of expired decision logs to manage storage and comply with data retention policies.

## Overview

Decision logs are temporary storage for production application decisions and are automatically cleaned up after a configurable retention period (default: 60 days).

## Components

### 1. Cleanup Service (`cleanup_service.py`)

The main service that handles:
- Cleanup statistics and analysis
- Batch deletion of expired logs
- Background job scheduling
- Safety checks and error handling

### 2. API Endpoints

Available at `/api/adi/ingest/cleanup/`:

- `GET /stats` - Get cleanup statistics
- `POST /schedule` - Schedule a background cleanup job
- `POST /run` - Run cleanup immediately (synchronous)
- `GET /jobs` - Get recent cleanup job results

All cleanup endpoints require admin authentication.

### 3. Background Jobs

Cleanup operations can run as background jobs using the existing job system:
- Non-blocking execution
- Progress tracking
- Error handling and recovery
- Job history and monitoring

## Usage

### Manual Cleanup

```python
from src.adi.services.cleanup_service import cleanup_now

# Dry run to see what would be deleted
result = cleanup_now(max_age_days=60, dry_run=True)
print(f"Would delete {result['total_deleted']} logs")

# Actual cleanup
result = cleanup_now(max_age_days=60, dry_run=False)
print(f"Deleted {result['total_deleted']} logs")
```

### Scheduled Cleanup

```python
from src.adi.services.cleanup_service import schedule_daily_cleanup

# Schedule cleanup job
job_id = schedule_daily_cleanup(max_age_days=60)
print(f"Cleanup job scheduled: {job_id}")
```

### API Usage

```bash
# Get cleanup statistics
curl -H "Authorization: Bearer admin-token-12345" \
     "http://localhost:5000/api/adi/ingest/cleanup/stats?max_age_days=60"

# Schedule cleanup job
curl -X POST \
     -H "Authorization: Bearer admin-token-12345" \
     -H "Content-Type: application/json" \
     -d '{"max_age_days": 60, "batch_size": 1000}' \
     "http://localhost:5000/api/adi/ingest/cleanup/schedule"

# Run cleanup immediately
curl -X POST \
     -H "Authorization: Bearer admin-token-12345" \
     -H "Content-Type: application/json" \
     -d '{"max_age_days": 60, "dry_run": false}' \
     "http://localhost:5000/api/adi/ingest/cleanup/run"
```

## Automated Cleanup

### Daily Cron Job

Use the provided script for automated daily cleanup:

```bash
# Add to crontab (run daily at 2 AM)
0 2 * * * /usr/bin/python3 /path/to/scripts/daily_cleanup.py --max-age-days 60

# Dry run first to test
python scripts/daily_cleanup.py --max-age-days 60 --dry-run

# Background job mode
python scripts/daily_cleanup.py --max-age-days 60 --background
```

### Application Startup

Initialize cleanup service in your application:

```python
from src.adi.services.cleanup_service import get_cleanup_service

# Initialize service (registers background job handler)
cleanup_service = get_cleanup_service()

# Optional: Schedule initial cleanup
job_id = cleanup_service.schedule_cleanup_job(max_age_days=60)
```

## Configuration

### Retention Policy

- **Default retention**: 60 days
- **Minimum retention**: 1 day
- **Maximum retention**: 365 days

### Batch Processing

- **Default batch size**: 1000 logs
- **Minimum batch size**: 100 logs
- **Maximum batch size**: 10,000 logs

### Safety Limits

- **Maximum batches per run**: 100 (prevents runaway deletion)
- **Dry run batch limit**: 10 (for testing)

## Monitoring

### Cleanup Statistics

```python
service = get_cleanup_service()
stats = service.get_cleanup_stats(max_age_days=60)

print(f"Total logs: {stats['total_logs']}")
print(f"Expired logs: {stats['total_expired']}")
print(f"Expired by project: {stats['expired_by_project']}")
```

### Job History

```python
service = get_cleanup_service()
jobs = service.get_recent_cleanup_jobs(limit=10)

for job in jobs:
    print(f"Job {job['id']}: {job['status']} - {job['created_at']}")
```

### Health Monitoring

The cleanup service status is included in the health check endpoint:

```bash
curl http://localhost:5000/api/adi/ingest/health
```

## Error Handling

The cleanup system includes comprehensive error handling:

1. **Database errors**: Automatic rollback and error logging
2. **Batch failures**: Continue with next batch, log errors
3. **Safety limits**: Prevent runaway deletion
4. **Job failures**: Proper error reporting and status tracking

## Security

- **Admin authentication**: All cleanup endpoints require admin tokens
- **Audit logging**: All cleanup operations are logged
- **Data sanitization**: PII is removed from logs before cleanup
- **Dry run mode**: Test cleanup operations safely

## Testing

Run the test suite to verify cleanup functionality:

```bash
python test_cleanup_service.py
```

The test suite covers:
- Cleanup statistics
- Dry run operations
- Actual cleanup
- Background job scheduling
- Error handling

## Troubleshooting

### Common Issues

1. **Permission errors**: Ensure admin token is valid
2. **Database locks**: Use smaller batch sizes
3. **Memory issues**: Reduce batch size for large datasets
4. **Job failures**: Check background job logs

### Debug Mode

Enable debug logging for detailed cleanup information:

```python
import logging
logging.getLogger('src.adi.services.cleanup_service').setLevel(logging.DEBUG)
```

### Manual Recovery

If cleanup jobs fail, you can run manual cleanup:

```python
from src.adi.services.cleanup_service import cleanup_now

# Force cleanup with small batches
result = cleanup_now(max_age_days=60, batch_size=100)
```