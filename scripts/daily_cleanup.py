#!/usr/bin/env python3
"""
Daily cleanup script for Decision Logs.

This script can be run as a cron job to automatically clean up expired decision logs.

Usage:
    python scripts/daily_cleanup.py [--max-age-days 60] [--dry-run]

Cron example (run daily at 2 AM):
    0 2 * * * /usr/bin/python3 /path/to/scripts/daily_cleanup.py
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from adi.services.cleanup_service import schedule_daily_cleanup, cleanup_now


def setup_logging():
    """Set up logging for the cleanup script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/var/log/adi_cleanup.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def main():
    """Main cleanup script."""
    parser = argparse.ArgumentParser(description='Daily cleanup for ADI Decision Logs')
    parser.add_argument('--max-age-days', type=int, default=60,
                       help='Maximum age of logs to keep in days (default: 60)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Perform a dry run without actually deleting logs')
    parser.add_argument('--background', action='store_true',
                       help='Run as background job instead of synchronous cleanup')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for cleanup operations (default: 1000)')
    
    args = parser.parse_args()
    
    logger = setup_logging()
    logger.info(f"Starting daily cleanup script (max_age_days={args.max_age_days}, dry_run={args.dry_run})")
    
    try:
        if args.background:
            # Schedule as background job
            job_id = schedule_daily_cleanup(max_age_days=args.max_age_days)
            logger.info(f"Scheduled cleanup job {job_id}")
            print(f"Cleanup job scheduled with ID: {job_id}")
        else:
            # Run synchronously
            result = cleanup_now(max_age_days=args.max_age_days, dry_run=args.dry_run)
            
            if result['success']:
                logger.info(f"Cleanup completed successfully: {result['total_deleted']} logs {'would be ' if args.dry_run else ''}deleted")
                print(f"✓ Cleanup completed: {result['total_deleted']} logs {'would be ' if args.dry_run else ''}deleted")
                print(f"  Duration: {result['duration_seconds']:.2f} seconds")
                print(f"  Batches processed: {result['batches_processed']}")
            else:
                logger.error(f"Cleanup failed: {result['error']}")
                print(f"✗ Cleanup failed: {result['error']}")
                return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Cleanup script failed: {str(e)}")
        print(f"✗ Cleanup script failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())