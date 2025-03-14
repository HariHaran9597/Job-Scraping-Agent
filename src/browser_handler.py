from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
import json
import os

class BrowserHandler:
    def __init__(self, config_path='../config/config.json'):
        self.config = self._load_config(config_path)
        chromedriver_autoinstaller.install()  # This will install the correct chromedriver version
        self.driver = self._setup_driver()
        
    def _load_config(self, config_path):
        config_path = os.path.join(os.path.dirname(__file__), config_path)
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def _setup_driver(self):
        chrome_options = Options()
        if self.config.get('browser_settings', {}).get('headless', False):
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--start-maximized')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(self.config.get('browser_settings', {}).get('timeout', 20))
        return driver
    
    def wait_for_element(self, by, value, timeout=None):
        if timeout is None:
            timeout = self.config.get('browser_settings', {}).get('timeout', 20)
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    
    def close(self):
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()