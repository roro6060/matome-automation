import requests
from bs4 import BeautifulSoup
from utils.http import generate_header
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

URL_POOLS = {}

class Scraper(object):
    def __init__(self, use_selenium=True, use_fake_useragent=False):
        self.use_fake_useragent = use_fake_useragent
        self.use_selenium = use_selenium
        self.url = None
        self.set_settings()

    def set_settings(self):
        self.header = generate_header(fake_useragent=self.use_fake_useragent)
        if self.use_selenium:
            self.driver = None
            self.driver_option = None

    def __call__(self, url, **kwds):
        if url in URL_POOLS:
            return URL_POOLS[url]
        self.get_soup(url)
        item = self.scrape(**kwds)
        URL_POOLS[url] = item
        return item

    def __del__(self):
        if self.driver is not None:
            self.driver.close()

    def save_as_html(self, name='./data/test.html', prettify=False, smooth=False):
        with open(name, mode='w', encoding='utf-8') as fw:
            if prettify:
                if smooth:
                    self.soup.smooth()
                fw.write(self.soup.prettify())
            else:
                fw.write(str(self.soup))

    def load_from_html(self, path):
        with open(path, mode='r', encoding='utf-8') as fr:
            self.soup = BeautifulSoup(fr, 'html.parser')

    def scrape(self, **kwds):
        raise NotImplementedError

    def get_soup(self, url):
        if self.use_selenium:
            self.set_driver()
            try:
                self.driver.implicitly_wait(5)
                self.driver.get(url)
                element = WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.ID, '#thread'))
                )
            except TimeoutException as e:
                error = e
            finally:
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        else:
            response = requests.get(url, self.header)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
        self.soup = soup
        return self.soup

    def set_driver(self):
        if self.driver is None:
            # self.driver = webdriver.Firefox()
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument("--log-level=OFF")
            self.driver = webdriver.Chrome(options=options)

