from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
import json

class LinkedInScraper:
    def __init__(self, browser_handler):
        self.browser = browser_handler
        self.driver = browser_handler.driver
        self.config = self.browser.config
        self.jobs_data = []
        self.logged_in = False
        
    def login(self):
        if self.logged_in:
            return True
            
        try:
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)
            
            # Enter email
            email_field = self.browser.wait_for_element(By.ID, "username")
            email_field.send_keys(self.config['credentials']['linkedin_email'])
            
            # Enter password
            password_field = self.browser.wait_for_element(By.ID, "password")
            password_field.send_keys(self.config['credentials']['linkedin_password'])
            password_field.send_keys(Keys.RETURN)
            
            # Wait for login to complete
            time.sleep(5)
            self.logged_in = True
            logging.info("Successfully logged into LinkedIn")
            return True
            
        except Exception as e:
            logging.error(f"Failed to login to LinkedIn: {str(e)}")
            return False
    
    def search_jobs(self, keyword, location):
        try:
            # Format the URL for LinkedIn job search
            keyword = keyword.replace(' ', '%20')
            location = location.replace(' ', '%20')
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={keyword}&location={location}&f_TPR=r604800&f_WT=2"
            
            self.driver.get(search_url)
            time.sleep(3)
            return self._extract_job_listings()
            
        except Exception as e:
            logging.error(f"Error searching jobs: {str(e)}")
            return []
    
    def _extract_job_listings(self):
        jobs = []
        try:
            # Scroll to load more jobs
            self._scroll_jobs_list()
            
            job_cards = self.driver.find_elements(By.CLASS_NAME, "jobs-search-results__list-item")
            
            for card in job_cards:
                try:
                    # Click the job card to load details
                    card.click()
                    time.sleep(1)
                    
                    # Extract job details
                    title = self.driver.find_element(By.CLASS_NAME, "jobs-unified-top-card__job-title").text
                    company = self.driver.find_element(By.CLASS_NAME, "jobs-unified-top-card__company-name").text
                    location = self.driver.find_element(By.CLASS_NAME, "jobs-unified-top-card__bullet").text
                    
                    # Get the apply button status
                    try:
                        apply_button = self.driver.find_element(By.CLASS_NAME, "jobs-apply-button")
                        easy_apply = "Easy Apply" in apply_button.text
                    except:
                        easy_apply = False
                    
                    job = {
                        'title': title,
                        'company': company,
                        'location': location,
                        'easy_apply': easy_apply,
                        'link': self.driver.current_url,
                        'source': 'LinkedIn'
                    }
                    
                    if easy_apply:
                        jobs.append(job)
                    
                except Exception as e:
                    logging.warning(f"Failed to parse job card: {str(e)}")
                    continue
            
            self.jobs_data.extend(jobs)
            logging.info(f"Found {len(jobs)} Easy Apply jobs")
            return jobs
            
        except Exception as e:
            logging.error(f"Error extracting job listings: {str(e)}")
            return []
    
    def _scroll_jobs_list(self):
        """Scroll through the jobs list to load more results"""
        jobs_list = self.driver.find_element(By.CLASS_NAME, "jobs-search-results-list")
        for _ in range(5):  # Scroll 5 times
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", jobs_list)
            time.sleep(1)
    
    def apply_to_job(self, job_url):
        try:
            if not self.logged_in:
                if not self.login():
                    return False
            
            self.driver.get(job_url)
            time.sleep(3)
            
            # Find and click the Easy Apply button
            try:
                # Updated selectors for the Easy Apply button
                button_selectors = [
                    "[data-control-name='jobdetails_topcard_inapply']",  # New LinkedIn selector
                    "button.jobs-apply-button",
                    "button[aria-label='Easy Apply']",
                    "button.jobs-apply-button--top-card",
                    "[aria-label*='Easy Apply']",
                    "[data-job-id]button.artdeco-button--primary"
                ]
                
                apply_button = None
                for selector in button_selectors:
                    try:
                        apply_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        if "Easy Apply" in apply_button.text or "Apply" in apply_button.text:
                            break
                    except:
                        continue
                
                if not apply_button:
                    logging.warning("Could not find Easy Apply button")
                    return False
                
                # Try to click the button, handling any overlay issues
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", apply_button)
                    time.sleep(1)
                    apply_button.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", apply_button)
                
                time.sleep(2)
                return self._handle_application_flow()
                
            except Exception as e:
                logging.warning(f"Error clicking apply button: {str(e)}")
                return False
                
        except Exception as e:
            logging.error(f"Error applying to job: {str(e)}")
            return False
    
    def _handle_application_flow(self):
        """Handle the multi-step application flow"""
        try:
            # Wait for the application modal
            modal_selectors = [
                ".jobs-easy-apply-modal",
                "div[data-test-modal-id='easy-apply-modal']",
                ".jobs-apply-form__container"
            ]
            
            modal = None
            for selector in modal_selectors:
                try:
                    modal = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if not modal:
                logging.warning("Application modal not found")
                return False
            
            # Handle each step of the application
            steps_completed = 0
            max_steps = 10  # Maximum number of steps to prevent infinite loops
            
            while steps_completed < max_steps:
                time.sleep(2)
                
                # Handle resume upload if needed
                try:
                    resume_upload = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                    resume_upload.send_keys(self.config['resume_path'])
                    time.sleep(2)
                except:
                    pass
                
                # Handle any dropdowns requiring selection
                try:
                    dropdowns = self.driver.find_elements(By.CSS_SELECTOR, "select.fb-dropdown__select")
                    for dropdown in dropdowns:
                        # Select the first non-empty option
                        options = dropdown.find_elements(By.TAG_NAME, "option")
                        for option in options[1:]:  # Skip the first option as it's usually empty
                            if option.text.strip():
                                option.click()
                                break
                except:
                    pass
                
                # Look for any radio buttons that need to be selected (usually Yes/No questions)
                try:
                    radio_buttons = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                    for radio in radio_buttons:
                        if radio.get_attribute("value").lower() in ["yes", "true", "1"]:
                            radio.click()
                except:
                    pass
                
                # Look for the next, review, or submit button
                buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                    "button.artdeco-button, button[aria-label*='Submit'], button[aria-label*='Next'], button[aria-label*='Review']"
                )
                
                next_button = None
                for button in buttons:
                    try:
                        text = button.text.lower()
                        if 'submit' in text:
                            button.click()
                            time.sleep(2)
                            logging.info("Application submitted successfully")
                            return True
                        elif any(action in text for action in ['next', 'review', 'continue']):
                            next_button = button
                    except:
                        continue
                
                if next_button:
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                        time.sleep(1)
                        next_button.click()
                        steps_completed += 1
                        continue
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", next_button)
                        steps_completed += 1
                        continue
                
                # If we can't find standard buttons, look for any primary action button
                try:
                    footer_buttons = self.driver.find_elements(
                        By.CSS_SELECTOR, 
                        "footer button.artdeco-button--primary, div[class*='footer'] button.artdeco-button--primary"
                    )
                    if footer_buttons:
                        footer_buttons[-1].click()
                        steps_completed += 1
                        time.sleep(2)
                        continue
                except:
                    pass
                
                # If we get here and haven't found any buttons to proceed
                logging.warning("Could not find next/submit button, application might be complete or stuck")
                return steps_completed > 0  # Return True if we completed at least one step
                
            logging.warning("Reached maximum number of application steps")
            return False
                
        except TimeoutException:
            logging.warning("Application modal not found or timed out")
            return False
        except Exception as e:
            logging.error(f"Error in application flow: {str(e)}")
            return False
    
    def save_jobs_to_csv(self, filename='linkedin_jobs.csv'):
        df = pd.DataFrame(self.jobs_data)
        df.to_csv(filename, index=False)
        return filename