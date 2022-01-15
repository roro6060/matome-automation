import os
import re
import random

from jinja2.tests import test_true
from models.thread_2chsc import HARD
from scraping.scraper_2chsc import Scraper_2chsc_thlist, Scraper_2chsc_thread, Scraper_2chsc_thread
from AI.context_vector import Context_Vectorizer
from AI.keyphrase import Keyphrase_extractor
from wordpress.page_template import Page_Template
from wordpress.wordpress_ctrl import WordPressCtrl, WordPressError
from models.ng_word import Ng_Word_Ctrl
import pickle
import time
import requests

import googletrans
import logging
import unicodedata2

logger = logging.getLogger(__name__)


class Summarizer(object):
    def __init__(self, summarize_settings) -> None:
        self.settings = summarize_settings
        self._feed_log_data = None
        self._vectorizer = None
        self._k_class_model = None
        self._page_tempale = None
        self._wordpress_ctrl = None
        self._tags = None
        self._categories = None
        self._medias = None
        self._ng_word_ctrl = None
        self._keyphrase_extr = None
        self._google_translator = None
        self.save_thd = False
        self.feed_log_filename = 'feeds.log'
        self.feed_line_th = 1000
        self.sleep_time = 10
        self.set_scraper()

    def set_scraper(self):
        self.thread_list_scraper = Scraper_2chsc_thlist()
        self.thread_scraper = Scraper_2chsc_thread()

    def __call__(self, url_ids=None, *args, **kwds):
        new_feeds = self.get_new_feeds(url_ids)
        self.sleep()
        logger.info(f'Obtained {len(new_feeds)} new feeds')

        for feed in new_feeds:
            feed_datas = self.summarize_feed(feed)

            for idx, f_data in enumerate(feed_datas):
                if self.settings.save_outputs:
                    self.save_page(f_data, feed, idx)
                else:
                    ng_flg, f_data = self.check_ng_for_upload(f_data)
                    if not ng_flg:
                        self.upload_page(f_data)
            self.save_log(feed)
            logger.info(f"Posted {len(feed_datas)} page from {feed['title']}")
            self.sleep()

        if self.settings.post_notification_url is not None and new_feeds:
            self.post_notification(
                self.settings.post_notification_url, f'{len(new_feeds)} feeds were posted from {self.settings.thread_titel_format}')

    def check_feeds(self):
        thd_list_ins = self.thread_list_scraper(
            url=self.settings.thread_list_url)
        target_feeds = [
            f for f in thd_list_ins.datas if self.settings.is_target_thread_title(f['title'])]
        return target_feeds

    def check_ng_for_upload(self, feed_dat):
        result_flg = False
        t_ng, feed_dat['title'] = self.check_ng_word(
            feed_dat['title'], ng_type='title')
        p_ng, feed_dat['page'] = self.check_ng_word(
            feed_dat['page'], ng_type='page')
        
        feed_dat['keyphrase'] = [
            k for k in feed_dat['keyphrase'] if not self.check_ng_word(k, ng_type='keyphrase')[0]
        ]

        if (not self.settings.use_ng_title and t_ng) or (not self.settings.use_ng_content and p_ng):
            result_flg = True
        return result_flg, feed_dat

    def is_new_feed(self, feed):
        log_datas = self.load_log_file()
        if feed['title'] in log_datas:
            return False
        return True

    def get_new_feeds(self, url_ids=None):
        target_feeds = self.check_feeds()
        new_target_feeds = [f for f in target_feeds if f['line_num']
                            > self.feed_line_th and self.is_new_feed(f)]
        if url_ids is not None:
            for url_id in url_ids:
                for target_f in target_feeds:
                    if url_id == target_f['url_id']:
                        flg = False
                        for nf in new_target_feeds:
                            if url_id == new_target_feeds['url_id']:
                                flg = True
                                break
                        if not flg:
                            new_target_feeds.append(target_f)
        return new_target_feeds

    def load_log_file(self, force=False):
        if self._feed_log_data is None or force:
            path = self.settings.get_logs_dir()
            log_file = os.path.join(path, self.feed_log_filename)
            log_data = []
            if not os.path.exists(log_file):
                with open(log_file, 'wt', encoding='utf-8') as f:
                    f.write('start')
            with open(log_file, 'rt', encoding='utf-8') as f:
                for l in f.readlines()[::-1]:
                    log_data.append(l.strip())
            self._feed_log_data = log_data
            logger.debug(f'loaded thread log file from {log_file}')
        return self._feed_log_data

    def summarize_feed(self, feed):
        feed_url = self.settings.get_thread_url(feed['url_id'])
        thd = self.thread_scraper(url=feed_url)

        if self.save_thd:
            self.thread_scraper.save_as_html(name=f'./data/{thd.title.replace("/", "_")}.html')

        thd.soft_target_range = self.settings.thd_soft_range
        thd.soft_min_score_th = self.settings.thd_soft_score_th
        vzer = self.load_vectorizer()
        thd.vectorize(vzer)
        kclass = self.load_k_class_model()
        thd.set_k_class(kclass)
        thd.set_ban_k_class(soft_bans=self.settings.soft_bans,
                            hard_bans=self.settings.hard_bans)
        parent_ng_word_ctrl = self.load_ng_word_ctrl(ng_type='parent')
        thd.set_soft_parent(ng_word_ctrl=parent_ng_word_ctrl)
        soft_topics = thd.soft_topics(sort_by_r=self.settings.sort_by_redirect)

        target_s_topics = [t for t in soft_topics if len(
            t) >= self.settings.topic_th]

        page_titles = [self.get_page_title(t) for t in target_s_topics]

        excerpts = [self.get_excerpt(t) for t in target_s_topics]

        keyphrases = [self.make_keryphrase(t) for t in target_s_topics]

        topic_params_list = [
            self.settings.make_template_params(url=feed_url, title=p_title, topic=topic) for p_title, topic in zip(page_titles, target_s_topics)]
        renderer = self.load_template()
        pages = [renderer.render(p) for p in topic_params_list]

        featured_media_ids = [
            self.get_featured_media(t) for t in target_s_topics]

        feed_datas = [
            self.feed_to_dict(t, p, k, e, f) for t, p, k, e, f in zip(page_titles, pages, keyphrases, excerpts, featured_media_ids)
        ]

        return feed_datas

    def get_page_title(self, topic):
        # for l in topic[0].text.splitlines():
        #     if l.strip() != '':
        #         return l.strip()
        #     else:
        #         continue
        return f'{self.settings.title_prefix}{topic[0].get_text_as_title()}{self.settings.title_suffix}'

    def get_excerpt(self, topic):
        if len(topic) == 0:
            return None
        if len(topic) == 1:
            return f"{topic[0].idx}: {topic[0].beautified_text(' ')}"
        else:
            redirect_flg =False
            for p in topic[1].parent:
                if p['idx'] == topic[0].idx and p['type'] == HARD:
                    redirect_flg = True
                    break
            if redirect_flg:
                return f"{topic[0].idx}: {topic[0].beautified_text(' ')} {topic[1].idx}: >>{topic[0].idx} {topic[1].beautified_text(' ')}"
            else:
                return f"{topic[0].idx}: {topic[0].beautified_text(' ')} {topic[1].idx}: {topic[1].beautified_text(' ')}"

    def make_keryphrase(self, topic):
        extr = self.load_keyphrase_extr()
        text = self.get_text_only_from_topic(topic)
        n_best = extr(text, keyphrase_num=self.settings.candidate_keyphrase_num)
        keyphrase_list = []
        for nb in n_best:
            if nb[1] >= self.settings.keyphrase_th:
                keyphrase_list.append(nb[0])

        return keyphrase_list[:self.settings.max_keyphrase_num]

    def get_featured_media(self, topic):
        if self.settings.candidate_media_metas is None:
            return self.settings.wordpress_default_featured_media_id

        sub_candidate_list = self.settings.candidate_media_metas['sub']
        main_candidate_list = self.settings.candidate_media_metas['main']

        media_data = self.select_candidate_media(sub_candidate_list, topic)
        if media_data is None:
            media_data = random.choice(main_candidate_list)

        return self.create_new_media(media_data)

    def select_candidate_media(self, media_metas, topic, use_count=False):
        selected = None
        texts = []
        for t in topic[:3]:
            texts.append(t.beautified_text())
        texts = '\n'.join(texts)

        word_idx = len(texts)
        for meta in media_metas:
            temp_idx = len(texts)
            for word in meta['words']:
                temp = texts.find(word)
                if temp != -1 and temp_idx > temp:
                    temp_idx = temp
            if word_idx > temp_idx:
                word_idx = temp_idx
                selected = meta

        if selected is not None:
            return selected

        all_texts = []
        for t in topic:
            all_texts.append(t.beautified_text())
        all_texts = '\n'.join(all_texts)

        count_t = 0
        for meta in media_metas:
            count_w = 0
            for word in meta['words']:
                temp = all_texts.count(word)
                if count_w < temp:
                    count_w = temp
            if count_t < count_w:
                count_t = count_w
                selected = meta

        return selected

    def get_text_only_from_topic(self, topic):
        texts = []
        for line in topic:
            l_text = line.beautified_text(keyword='\n')
            if l_text != '':
                texts.append(l_text)
        return '\n'.join(texts)

    def load_vectorizer(self, force=False):
        if self._vectorizer is None or force:
            self._vectorizer = Context_Vectorizer(
                model_name=self.settings.vectrize_model_name)
            logger.debug(
                f'loaded vetorizer from {self.settings.vectrize_model_name}')
        return self._vectorizer

    def load_k_class_model(self, force=False):
        if self._k_class_model is None or force:
            self._k_class_model = pickle.load(
                open(self.settings.k_class_model_path, 'rb'))
            logger.debug(
                f'loaded claster model from {self.settings.k_class_model_path}')
        return self._k_class_model

    def load_template(self, force=False):
        if self._page_tempale is None or force:
            self._page_tempale = Page_Template(
                self.settings.template_file_path)
            logger.debug(
                f'loaded html template from {self.settings.template_file_path}')
        return self._page_tempale

    def load_wordpress_ctrl(self, force=False):
        if self._wordpress_ctrl is None or force:
            self._wordpress_ctrl = WordPressCtrl(
                url=self.settings.wordpress_url,
                user=self.settings.wordpress_user,
                password=self.settings.wordpress_password,
            )
        return self._wordpress_ctrl

    def save_page(self, feed_data, feed, idx):
        path = self.settings.get_logs_dir()
        title = feed['title']
        title = re.sub(r'[\\|/|:|?|.|"|<|>|\|]', '-', title)
        page_file = os.path.join(path, f'{title}_{idx}.html')
        with open(page_file, mode='w', encoding='utf-8') as f:
            f.write(f"<h1>{feed_data['title']}</h1>")
            f.write('\n')
            f.write(f"{feed_data['page']}")
            f.write('\n')
            f.write('<p>Keywords: ')
            for k in feed_data['keyphrase']:
                f.write(k)
                f.write(', ')
            f.write('</p>')
            f.write('\n')
        logger.info(f'saved generated page at {page_file}')

    def upload_page(self, feed_data):
        wp_ctrl = self.load_wordpress_ctrl()
        category_ids = [
            wp_ctrl.convert_stug_to_id(c, self.load_categories()) for c in self.settings.wordpress_categorie_slugs]
        category_ids = [c for c in category_ids if c is not None]
        tag_ids = [
            wp_ctrl.convert_stug_to_id(c, self.load_tags()) for c in self.settings.wordpress_tag_slugs]
        tag_ids = [c for c in tag_ids if c is not None]

        tag_ids.extend([self.create_new_tag(k)
                       for k in feed_data['keyphrase']])

        try:
            wp_ctrl.add_post(
                title=feed_data['title'],
                content=feed_data['page'],
                status=self.settings.wordpress_default_page_status,
                excerpt=feed_data['excerpt'],
                featured_media_id=feed_data['featured_media'],
                categorie_ids=category_ids,
                tag_ids=tag_ids,
            )
            logger.info(f"uploaded html page with {feed_data['title'][:20]}")
        except WordPressError as e:
            logger.error(f"failed uploading html page with {feed_data['title'][:20]} error:{str(e)}")
            self.save_page(feed_data, feed_data, feed_data['featured_media'])

    def save_log(self, feed):
        log_datas = self.load_log_file()
        path = self.settings.get_logs_dir()
        title = feed['title']
        log_file = os.path.join(path, self.feed_log_filename)
        with open(log_file, mode='a', encoding='utf-8') as f:
            log_datas.insert(0, title)
            f.write(f'\n{title}')
        logger.debug(f'saved thread log file')

    def sleep(self):
        time.sleep(self.sleep_time)

    def load_tags(self, force=False):
        if self._tags is None or force:
            wp_ctrl = self.load_wordpress_ctrl()
            self._tags = wp_ctrl.get_tags()
        return self._tags

    def add_tags(self, tag_data):
        if self._tags is not None:
            self._tags.append(tag_data)

    def add_medias(self, media_data):
        if self._medias is not None:
            self._medias.append(media_data)

    def load_categories(self, force=False):
        if self._categories is None or force:
            wp_ctrl = self.load_wordpress_ctrl()
            self._categories = wp_ctrl.get_categories()
        return self._categories

    def load_medias(self, force=False):
        if self._medias is None or force:
            wp_ctrl = self.load_wordpress_ctrl()
            self._medias = wp_ctrl.get_medias()
        return self._medias

    def load_ng_word_ctrl(self, ng_type, force=False,):
        if (self._ng_word_ctrl is None or ng_type not in self._ng_word_ctrl) or force:
            if self._ng_word_ctrl is None:
                self._ng_word_ctrl = {}
            self._ng_word_ctrl[ng_type] = Ng_Word_Ctrl(
                self.settings.ng_word_file_path[ng_type])
        return self._ng_word_ctrl[ng_type]

    def load_keyphrase_extr(self, force=False):
        if self._keyphrase_extr is None or force:
            self._keyphrase_extr = Keyphrase_extractor()
        return self._keyphrase_extr

    def load_google_translator(self, force=False):
        if self._google_translator is None or force:
            self._google_translator = googletrans.Translator()
        return self._google_translator

    def check_ng_word(self, text, ng_type='page'):
        ng_ctrl = self.load_ng_word_ctrl(ng_type=ng_type)
        if not ng_ctrl.has_ng_word(text):
            return False, text
        else:
            text = ng_ctrl.replace(text)
            return True, text

    def create_new_tag(self, name):
        tag_list = self.load_tags()
        for data in tag_list:
            if data['name'] == name:
                return data['id']

        if self.is_japanese(name):
            slug = self.translate_to_en(name)
        else:
            slug = name

        slug = slug.lower()
        slug_count = 0
        for data in tag_list:
            if data['slug'] == slug:
                slug_count += 1

        if slug_count > 0:
            slug = f'{slug}-{slug_count}'

        wp_ctrl = self.load_wordpress_ctrl()
        while True:
            try:
                data = wp_ctrl.post_tag(name, slug)
                break
            except WordPressError as e:
                slug_count += 1
                slug = f'{slug}-{slug_count}'
        self.add_tags(data)

        return data['id']

    def create_new_media(self, media_meta):
        if self.settings.wordpress_url is None or self.settings.wordpress_url == '':
            return media_meta['slug']
        media_list = self.load_medias()
        for data in media_list:
            if data['slug'] == media_meta['slug']:
                return data['id']

        wp_ctrl = self.load_wordpress_ctrl()
        data = wp_ctrl.upload_media(
            media_meta['path'],
            slug=media_meta['slug'],
            title=media_meta['title'],
            alt_text=media_meta['alt_text'],
            caption=media_meta['caption'],
            description=media_meta['description'],
        )
        self.add_medias(data)

        return data['id']

    def translate_to_en(self, text):
        tlr = self.load_google_translator()
        transed = tlr.translate(text, src='ja', dest='en').text
        return transed.replace(' ', '-').replace('　', '-').replace('.', '-').replace('!', '-').strip()

    @staticmethod
    def feed_to_dict(title, page, keyphrase, excerpt=None, featured_media=None):
        data = {
            'title': title,
            'page': page,
            'keyphrase': keyphrase,
            'excerpt': excerpt,
            'featured_media': featured_media,
        }
        return data

    @staticmethod
    def is_japanese(string):
        for ch in string:
            name = unicodedata2.name(ch)
            if "CJK UNIFIED" in name \
                    or "HIRAGANA" in name \
                    or "KATAKANA" in name:
                return True
        return False

    @staticmethod
    def post_notification(url, txt):
        datas = {
            'value1': txt
        }
        response = requests.post(url, data=datas)
        return response