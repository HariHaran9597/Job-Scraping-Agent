from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
import json
from browser_handler import BrowserHandler

class IndeedScraper:
    def __init__(self, browser_handler):
        self.browser = browser_handler
        self.driver = browser_handler.driver
        self.jobs_data = []
        self.config = self.browser.config
        self.logged_in = False
        
    def login(self):
        if self.logged_in:
            return True
            
        try:
            self.driver.get("https://secure.indeed.com/auth")
            time.sleep(2)  # Wait for any redirects
            
            # Enter email
            email_field = self.browser.wait_for_element(By.ID, "ifl-InputFormField-3")
            email_field.send_keys(self.config['credentials']['indeed_email'])
            email_field.send_keys(Keys.RETURN)
            time.sleep(2)
            
            # Enter password
            password_field = self.browser.wait_for_element(By.ID, "ifl-InputFormField-7")
            password_field.send_keys(self.config['credentials']['indeed_password'])
            password_field.send_keys(Keys.RETURN)
            
            # Wait for login to complete
            time.sleep(5)
            self.logged_in = True
            logging.info("Successfully logged into Indeed")
            return True
            
        except Exception as e:
            logging.error(f"Failed to login to Indeed: {str(e)}")
            return False
    
    def search_jobs(self, keyword, location):
        try:
            search_url = f"https://www.indeed.com/jobs?q={keyword.replace(' ', '+')}&l={location.replace(' ', '+')}"
            if self.config['job_search'].get('job_type'):
                search_url += f"&jt={self.config['job_search']['job_type']}"
            if self.config['job_search'].get('posted_within'):
                search_url += "&fromage=14"  # Last 14 days
                
            self.driver.get(search_url)
            time.sleep(3)  # Wait for results to load
            return self._extract_job_listings()
            
        except Exception as e:
            logging.error(f"Error searching jobs: {str(e)}")
            return []
    
    def _extract_job_listings(self):
        jobs = []
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            job_cards = soup.find_all('div', class_='job_seen_beacon')
            
            for card in job_cards:
                try:
                    # Extract job details
                    title = card.find('h2', class_='jobTitle').text.strip()
                    company = card.find('span', class_='companyName').text.strip()
                    location = card.find('div', class_='companyLocation').text.strip()
                    
                    # Get job link
                    job_link = card.find('a', class_='jcs-JobTitle')
                    if job_link and 'href' in job_link.attrs:
                        link = 'https://www.indeed.com' + job_link['href']
                    else:
                        continue
                        
                    # Extract salary if available
                    salary_elem = card.find('div', class_='salary-snippet')
                    salary = salary_elem.text.strip() if salary_elem else "Not specified"
                    
                    # Extract job description snippet
                    description_elem = card.find('div', class_='job-snippet')
                    description = description_elem.text.strip() if description_elem else ""
                    
                    job = {
                        'title': title,
                        'company': company,
                        'location': location,
                        'salary': salary,
                        'description': description,
                        'link': link,
                        'source': 'Indeed'
                    }
                    
                    jobs.append(job)
                    
                except AttributeError as e:
                    logging.warning(f"Failed to parse job card: {str(e)}")
                    continue
                    
            self.jobs_data.extend(jobs)
            logging.info(f"Found {len(jobs)} jobs")
            return jobs
            
        except Exception as e:
            logging.error(f"Error extracting job listings: {str(e)}")
            return []
    
    def apply_to_job(self, job_url):
        try:
            if not self.logged_in:
                if not self.login():
                    return False
                    
            self.driver.get(job_url)
            time.sleep(3)
            
            # Look for the Apply button
            try:
                apply_button = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='jobsearch-IndeedApplyButton']"))
                )
                apply_button.click()
                
                # Switch to the application iframe if present
                time.sleep(3)
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    self.driver.switch_to.frame(iframes[0])
                
                # Fill application if needed
                self._fill_application_form()
                
                return True
                
            except TimeoutException:
                logging.warning(f"No quick apply button found for {job_url}")
                return False
                
        except Exception as e:
            logging.error(f"Error applying to job: {str(e)}")
            return False
            
    def _fill_application_form(self):
        try:
            # Upload resume if needed
            resume_upload = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            if resume_upload:
                resume_upload[0].send_keys(self.config['resume_path'])
                time.sleep(2)
            
            # Continue button - might need to click multiple times
            for _ in range(3):
                try:
                    continue_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                    )
                    continue_button.click()
                    time.sleep(2)
                except:
                    break
                    
        except Exception as e:
            logging.error(f"Error filling application form: {str(e)}")
            
    def save_jobs_to_csv(self, filename='jobs.csv'):
        df = pd.DataFrame(self.jobs_data)
        df.to_csv(filename, index=False)
        return filename