from browser_handler import BrowserHandler
from job_scraper import IndeedScraper
import json
import logging
from datetime import datetime
import os
import time

class IndeedAgent:
    def __init__(self, config_path='../config/config.json'):
        self._setup_logging()
        self.config = self._load_config(config_path)
        self.browser_handler = BrowserHandler(config_path)
        self.scraper = IndeedScraper(self.browser_handler)
        self.applied_jobs = self._load_applied_jobs()
        
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('job_agent.log'),
                logging.StreamHandler()
            ]
        )
        
    def _load_config(self, config_path):
        config_path = os.path.join(os.path.dirname(__file__), config_path)
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def _load_applied_jobs(self):
        if os.path.exists('applied_jobs.json'):
            with open('applied_jobs.json', 'r') as f:
                return json.load(f)
        return []
    
    def _save_applied_jobs(self):
        with open('applied_jobs.json', 'w') as f:
            json.dump(self.applied_jobs, f)
    
    def _filter_job(self, job):
        title_lower = job['title'].lower()
        description_lower = job['description'].lower()
        
        # Check required keywords in title or description
        has_required_skill = False
        for keyword in self.config['auto_apply']['required_keywords']:
            if keyword.lower() in title_lower or keyword.lower() in description_lower:
                has_required_skill = True
                break
        
        if not has_required_skill:
            return False
            
        # Check excluded keywords
        if any(keyword.lower() in title_lower for keyword in self.config['auto_apply']['exclude_keywords']):
            return False
            
        # Check if company is blacklisted
        if job['company'] in self.config['auto_apply']['blacklist_companies']:
            return False
            
        # Check if already applied
        if job['link'] in [applied_job['link'] for applied_job in self.applied_jobs]:
            return False
            
        return True
    
    def run(self):
        try:
            logging.info("Starting job search...")
            
            # First try to login
            if not self.scraper.login():
                logging.error("Failed to login to Indeed. Please check your credentials.")
                return
            
            total_applications = 0
            max_applications = self.config['auto_apply']['max_applications_per_day']
            
            # Search for each keyword and location combination
            for keyword in self.config['job_search']['keywords']:
                for location in self.config['job_search']['locations']:
                    if total_applications >= max_applications:
                        logging.info("Reached maximum applications for today")
                        break
                        
                    logging.info(f"Searching for {keyword} jobs in {location}")
                    jobs = self.scraper.search_jobs(keyword, location)
                    
                    filtered_jobs = [job for job in jobs if self._filter_job(job)]
                    logging.info(f"Found {len(filtered_jobs)} matching jobs for {keyword} in {location}")
                    
                    for job in filtered_jobs:
                        if total_applications >= max_applications:
                            break
                            
                        try:
                            logging.info(f"Attempting to apply: {job['title']} at {job['company']}")
                            if self.scraper.apply_to_job(job['link']):
                                job['applied_date'] = datetime.now().isoformat()
                                self.applied_jobs.append(job)
                                total_applications += 1
                                logging.info(f"Successfully applied to job at {job['company']}")
                                self._save_applied_jobs()  # Save after each successful application
                                time.sleep(5)  # Wait between applications
                            else:
                                logging.warning(f"Could not apply to job at {job['company']}")
                                
                        except Exception as e:
                            logging.error(f"Error applying to job: {str(e)}")
                            continue
                    
                    time.sleep(3)  # Wait between searches
            
            # Save all jobs to CSV for reference
            csv_file = self.scraper.save_jobs_to_csv()
            logging.info(f"Applied to {total_applications} jobs. Job data saved to {csv_file}")
            
        except Exception as e:
            logging.error(f"Error in job application process: {str(e)}")
        finally:
            self.browser_handler.close()

if __name__ == "__main__":
    agent = IndeedAgent()
    agent.run()