"""Scheduled task runner for the reports scraper.

This module handles periodic execution of the scraper using APScheduler.
"""

import logging
import subprocess
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
SCRAPER_COMMAND = ['python3', 'scraper.py']
DEFAULT_INTERVAL_WEEKS = 1
SCRAPER_TIMEOUT = 3600  # 1 hour timeout

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
    """Execute the scraper subprocess with proper error handling.
    
    Returns:
        True if scraper completed successfully, False otherwise
    """
    logger.info("Starting scheduled scraper execution")
    
    try:
        result = subprocess.run(
            SCRAPER_COMMAND,
            capture_output=True,
            text=True,
            timeout=SCRAPER_TIMEOUT
        )
        
        if result.returncode == 0:
            logger.info("Scraper completed successfully")
            if result.stdout:
                logger.debug(f"Scraper output: {result.stdout}")
            return True
        else:
            logger.error(f"Scraper failed with return code {result.returncode}")
            if result.stderr:
                logger.error(f"Scraper stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"Scraper process timed out after {SCRAPER_TIMEOUT} seconds")
        return False
    except FileNotFoundError:
        logger.error("Scraper script not found. Please ensure scraper.py exists in the current directory")
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
