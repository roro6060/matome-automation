from .scraper import Scraper
from models.thread_2chsc import Thread, Thread_list


class Scraper_2chsc_thread(Scraper):
    def __init__(self, use_selenium=True, use_fake_useragent=False):
        super().__init__(use_selenium=use_selenium, use_fake_useragent=use_fake_useragent)

    def scrape(self, **kwds):
        title_sp = self.soup.select_one('h1')
        thread_names_sp = self.soup.select('dt.net')
        thread_texts_sp = self.soup.select('dd.net')
        thd = Thread(title_sp, thread_names_sp, thread_texts_sp)

        return thd


class Scraper_2chsc_thlist(Scraper):
    def __init__(self, use_selenium=True, use_fake_useragent=False):
        super().__init__(use_selenium=use_selenium, use_fake_useragent=use_fake_useragent)

    def scrape(self, **kwds):
        title_sp = self.soup.select_one('title')
        thread_lsit_sp = self.soup.select('#trad a')
        thlist = Thread_list(title_sp, thread_lsit_sp)

        return thlist
