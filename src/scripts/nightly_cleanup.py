#!/usr/bin/env python3
"""
Nightly cleanup script for monitoring data retention.

This script should be run as a cron job to perform:
- Down-sampling of metrics older than 7 days
- Purging of data older than 30 days
- Database optimization

Usage:
    python src/scripts/nightly_cleanup.py

Cron job example (run at 2 AM daily):
    0 2 * * * cd /path/to/software_factory && python src/scripts/nightly_cleanup.py >> /var/log/cleanup.log 2>&1
"""

import os
import sys
import logging
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.app import create_app
from src.services.data_retention_service import data_retention_service


def setup_logging():
    """Setup logging for the cleanup script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('cleanup.log', mode='a')
        ]
    )
    return logging.getLogger(__name__)


def main():
    """Main cleanup function."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Starting nightly data retention cleanup")
    logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)
    
    try:
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            # Get retention stats before cleanup
            logger.info("Getting retention statistics before cleanup...")
            stats_before = data_retention_service.get_retention_stats()
            logger.info(f"Stats before cleanup: {stats_before}")
            
            # Run the cleanup
            logger.info("Running nightly cleanup...")
            cleanup_results = data_retention_service.run_nightly_cleanup()
            
            # Log results
            if cleanup_results.get('success', False):
                logger.info("Cleanup completed successfully!")
                logger.info(f"Metrics down-sampled: {cleanup_results.get('metrics_downsampled', 0)}")
                logger.info(f"Metrics purged: {cleanup_results.get('metrics_purged', 0)}")
                logger.info(f"Alerts purged: {cleanup_results.get('alerts_purged', 0)}")
                logger.info(f"System health records purged: {cleanup_results.get('system_health_purged', 0)}")
                logger.info(f"Integration status records purged: {cleanup_results.get('integration_status_purged', 0)}")
            else:
                logger.error("Cleanup failed!")
                for error in cleanup_results.get('errors', []):
                    logger.error(f"Error: {error}")
            
            # Get retention stats after cleanup
            logger.info("Getting retention statistics after cleanup...")
            stats_after = data_retention_service.get_retention_stats()
            logger.info(f"Stats after cleanup: {stats_after}")
            
            # Calculate space saved
            if 'tables' in stats_before and 'tables' in stats_after:
                total_before = sum(table['total_records'] for table in stats_before['tables'].values())
                total_after = sum(table['total_records'] for table in stats_after['tables'].values())
                records_removed = total_before - total_after
                logger.info(f"Total records removed: {records_removed}")
    
    except Exception as e:
        logger.error(f"Fatal error during cleanup: {str(e)}", exc_info=True)
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Nightly cleanup completed")
    logger.info(f"End timestamp: {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()