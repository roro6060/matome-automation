import urllib.parse as urlparse
import re
import os
import oembed


class Summarize_Settings(object):
    def __init__(self,
                 thread_list_url,
                 thread_base_url,
                 thread_titel_format,
                 logs_dir,
                 thd_soft_range,
                 thd_soft_score_th,
                 vectrize_model_name,
                 k_class_model_path,
                 soft_bans,
                 hard_bans,
                 topic_th,
                 template_file_path,
                 wordpress_url,
                 wordpress_user,
                 wordpress_password,
                 wordpress_categorie_slugs,
                 wordpress_tag_slugs,
                 save_outputs=False,
                 base_logs_dir='./logs',
                 wordpress_default_page_status='draft',
                 wordpress_default_featured_media_id=None,
                 candidate_media_metas=None,
                 ng_word_file_title_path=None,
                 ng_word_file_page_path=None,
                 ng_word_file_parent_path=None,
                 ng_word_file_keyphrase_path=None,
                 use_ng_title=False,
                 use_ng_content=False,
                 max_keyphrase_num=5,
                 candidate_keyphrase_num=10,
                 post_notification_url=None,
                 keyphrase_th=0.0,
                 sort_by_redirect=True,
                 title_prefix='',
                 title_suffix='',
                 ):
        self.thread_list_url = thread_list_url
        self.thread_base_url = thread_base_url
        self.thread_titel_format = thread_titel_format
        self.thread_titel_rep = re.compile(self.thread_titel_format)
        self.logs_dir = logs_dir
        self.base_logs_dir = base_logs_dir

        self.thd_soft_range = thd_soft_range
        self.thd_soft_score_th = thd_soft_score_th

        self.vectrize_model_name = vectrize_model_name
        self.k_class_model_path = k_class_model_path

        self.soft_bans = soft_bans
        self.hard_bans = hard_bans

        self.topic_th = topic_th

        self.template_file_path = template_file_path

        self.save_outputs = save_outputs

        self.wordpress_url = wordpress_url
        self.wordpress_user = wordpress_user
        self.wordpress_password = wordpress_password
        self.wordpress_categorie_slugs = wordpress_categorie_slugs
        self.wordpress_tag_slugs = wordpress_tag_slugs
        self.wordpress_default_page_status = wordpress_default_page_status
        self.wordpress_default_featured_media_id = wordpress_default_featured_media_id

        self.ng_word_file_path = {
            'title': ng_word_file_title_path,
            'page': ng_word_file_page_path,
            'parent': ng_word_file_parent_path,
            'keyphrase': ng_word_file_keyphrase_path,
        }
        self.use_ng_title = use_ng_title
        self.use_ng_content = use_ng_content
        self.sort_by_redirect = sort_by_redirect

        self.max_keyphrase_num = max_keyphrase_num
        self.candidate_keyphrase_num = candidate_keyphrase_num
        self.keyphrase_th = keyphrase_th

        self.candidate_media_metas = candidate_media_metas

        self.post_notification_url = post_notification_url

        self.title_prefix = title_prefix
        self.title_suffix = title_suffix

        self.set_transform_rules()

    def set_transform_rules(self):
        self.transform_rules = [{
            'name': 'redirect',
            'reps': re.compile('>>\d[\d,]*'),
            'func': lambda x: f'<span>{x}</span>',
            'footer': False,
            'if':[],
        }, {
            'name': 'imgur',
            'reps': re.compile("https?://i?\.?imgur.com[\w!\?/\+\-_~=;\.,\*&@#\$%\(\)'\[\]]+"),
            # 'func': lambda x: f'<a href="{x}" target="_blank" rel="noopener nofollow"><img src="{x}" alt="image" loading="lazy" style="min-height:480px"' + 'onload="this.style={minHeight:''auto''}"></a><br>' + f'<small><a href="{x}" target="_blank" rel="noopener nofollow">引用元:{x}</a></small>',
            'func': lambda x: f'<img src="{x}" alt="image" loading="lazy" style="min-height:480px">',
            'footer': False,
            'if':[],
        }, {
            'name': 'imgur_no_https',
            'reps': re.compile("^i?\.?imgur\.com[\w!\?/\+\-_~=;\.,\*&@#\$%\(\)'\[\]]+"),
            'func': lambda x: f'<img src="https://{x}" alt="image" loading="lazy" style="min-height:480px">',
            'footer': False,
            'if':[],
        }, {
            'name': 'youtube',
            'reps': re.compile("https?://(www\.youtube|youtu\.be)[\w!\?/\+\-_~=;\.,\*&@#\$%\(\)'\[\]]+"),
            'func': lambda x: '',
            'footer': True,
            'footer_func': lambda x: self.return_url(x),
            'if':[],
        }, {
            'name': 'twitter',
            'reps': re.compile("https?://(twitter\.com|t\.co)[\w!\?/\+\-_~=;\.,\*&@#\$%\(\)'\[\]]+"),
            'func': lambda x: '',
            'footer': True,
            'footer_func': lambda x: self.return_url(x),
            'if':[],
        }, {
            'name': 'url',
            'reps': re.compile("(?!https?://(i?\.?imgur\.com|www\.youtube|youtu\.be|twitter\.com|t\.co).*)https?://[\w!\?/\+\-_~=;\.,\*&@#\$%\(\)'\[\]]+"),
            'func': lambda x: f'<a href="{x}" target="_blank" rel="noopener nofollow">{x}</a>',
            'footer': False,
            'if':['imgur', 'imgur_no_https', 'youtube', 'twitter'],
        }, {
            'name': 'unicode_s',
            'reps': re.compile(r"\\u[0-9][0-9][0-9][0-9]"),
            'func': lambda x: f' ',
            'footer': False,
            'if':['imgur', 'imgur_no_https', 'youtube', 'twitter', 'url'],
        }, ]

    def get_thread_url(self, thread_page_id):
        return urlparse.urljoin(self.thread_base_url, thread_page_id)

    def is_target_thread_title(self, title_txt):
        result = self.thread_titel_rep.match(title_txt.strip())
        return result is not None

    def get_logs_dir(self):
        path = os.path.join(self.base_logs_dir, self.logs_dir)
        if os.path.isdir(path):
            return path
        else:
            os.mkdir(path)
            return path

    def make_template_params(self, url, title, topic):
        params = {
            'url': url,
            'title': f'{self.title_prefix}{title}{self.title_suffix}',
            'items': [
                {
                    'idx': line.idx,
                    'name': line.name,
                    'time': line.time.strftime('%Y/%m/%d(%a) %H:%M:%S.%f')[:-4],
                    'id': line.id,
                    'text': line.joined_text('<br>')
                } for line in topic
            ]
        }
        params = self.html_format(params)
        return params

    def html_format(self, params):
        for item in params["items"]:
            item["idx"] = f'<span>{item["idx"]}: </span>'
            item[
                "name"] = f'<span>{item["name"]} : </span>'
            item["time"] = f'<span>{item["time"]} </span>'
            item["id"] = f'<span>{item["id"]}</span>'
            item["text"], item["footer"] = self.text_html_format(item["text"])

        return params

    def text_html_format(self, text):
        lines = text.split('<br>')
        new_texts = []
        footer_divs = []
        for l in lines:
            t, fds = self.text_transforms(l)
            if t is not None:
                new_texts.append(t)
            footer_divs.extend(fds)
        return '<br>'.join(new_texts), footer_divs

    def text_transforms(self, line_text):
        footer_divs = []
        transformed_func = []
        if line_text == '':
            return line_text, footer_divs
        for transform in self.transform_rules:
            reps = transform['reps']
            transform_func = transform['func']
            esc_flg = False
            for esc in transform['if']:
                if esc in transformed_func:
                    esc_flg = True
                    break
            if esc_flg:
                continue

            finditer = reps.finditer(line_text.strip())
            new_line_texts = []
            last_position = 0
            for matched in finditer:
                find_start = matched.start()
                new_line_texts.append(line_text[last_position:find_start])
                last_position = matched.end()
                if transform['footer']:
                    footer_divs.append(transform['footer_func'](
                        line_text[find_start:last_position]))
                new_line_texts.append(transform_func(
                    line_text[find_start:last_position]))
            if new_line_texts:
                new_line_texts.append(line_text[last_position:])
                line_text = ''.join(new_line_texts)
                transformed_func.append(transform['name'])

        if line_text == '':
            return None, footer_divs

        return line_text, footer_divs

    def youtube_div(self, url):
        return url
        # consumer = oembed.OEmbedConsumer()
        # endpoint = oembed.OEmbedEndpoint(
        #     'https://www.youtube.com/oembed', ['https://*.youtube.com/*', 'https://youtu.be/*'])
        # consumer.addEndpoint(endpoint)
        # response = consumer.embed(url)
        # url_embed = re.search(
        #     'src="https://[\w!\?/\+\-_~=;\.,\*&@#\$%\(\)''\[\]]+"', response["html"]).group()
        # text = f'<figure class="wp-block-embed is-type-video is-provider-youtube wp-block-embed-youtube wp-embed-aspect-16-9 wp-has-aspect-ratio"><div class="wp-block-embed__wrapper"><div class="youtube"><iframe title="{response["title"]}" {url_embed} frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div></div></figure>'
        # return text

    def twitter_div(self, url):
        consumer = oembed.OEmbedConsumer()
        endpoint = oembed.OEmbedEndpoint(
            'https://publish.twitter.com/oembed', ['https://twitter.com/*'])
        consumer.addEndpoint(endpoint)
        response = consumer.embed(url)
        text = f'<div>{response["html"]}</div>'
        return text

    def return_url(self, url):
        return url
