"""Scheduled task runner for the reports scraper.

This module handles periodic execution of the scraper using APScheduler.
"""

import logging
import sys
from typing import Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_INTERVAL_WEEKS = 1

def job_listener(event):
    """Log job execution events.
    
    Args:
        event: APScheduler job event
    """
    if event.exception:
        logger.error(f"Job {event.job_id} crashed: {event.exception}")
    else:
        logger.info(f"Job {event.job_id} executed successfully")

def run_scraper() -> bool:
    """Execute the scraper directly by importing and calling the scraper module.
    
    Returns:
        True if scraper completed successfully, False otherwise
    """
    logger.info("Starting scheduled scraper execution")
    
    try:
        # Import scraper module and call directly
        from scraper import run_scraper_for_users
        success = run_scraper_for_users(verbose=False)
        
        if success:
            logger.info("Scraper completed successfully")
            return True
        else:
            logger.error("Scraper failed - no users processed successfully")
            return False
            
    except ImportError as e:
        logger.error(f"Failed to import scraper module: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error running scraper: {e}")
        return False

def main() -> None:
    """Main scheduler function."""
    logger.info("Starting scheduler application")
    
    try:
        scheduler = BlockingScheduler()
        
        # Add job event listener
        scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        # Schedule the scraper to run weekly
        scheduler.add_job(
            run_scraper, 
            'interval', 
            weeks=DEFAULT_INTERVAL_WEEKS,
            id='weekly_scraper',
            name='Weekly Report Scraper',
            replace_existing=True
        )
        
        logger.info(f"Scheduler configured to run scraper every {DEFAULT_INTERVAL_WEEKS} week(s)")
        logger.info("Running scraper once now for initial execution...")
        
        # Run scraper immediately for testing
        initial_success = run_scraper()
        if not initial_success:
            logger.warning("Initial scraper run failed, but scheduler will continue")
        
        logger.info("Scheduler starting... Press Ctrl+C to stop")
        scheduler.start()
        
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        sys.exit(1)
    finally:
        logger.info("Scheduler shutdown complete")

if __name__ == '__main__':
    main() 
