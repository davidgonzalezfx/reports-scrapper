from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess

def run_scraper():
    subprocess.call(['python3', 'scraper.py'])

if __name__ == '__main__':
    scheduler = BlockingScheduler()
    scheduler.add_job(run_scraper, 'interval', weeks=1)
    print('Scheduler started. Scraper will run once a week.')
    print('Running scraper once now for testing...')
    run_scraper()
    scheduler.start() 
