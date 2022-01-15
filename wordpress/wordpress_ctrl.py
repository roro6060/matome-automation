import json
import os
import base64
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder


class WordPressError(Exception):
    def __init__(self, ctrl, status_code, reason, message):
        super(WordPressError, self).__init__()
        self.ctrl = ctrl
        self.status_code = status_code
        self.reason = reason
        self.message = message

    def __str__(self):
        return (
            f"Status code is {self.status_code}:{self.reason}:{self.message}"
        )


class WordPressCtrl:
    def __init__(self, url, user, password, press_format='standard'):
        self.url = url
        auth_str = f"{user}:{password}"
        auth_base64_bytes = base64.b64encode(auth_str.encode(encoding='utf-8'))
        self.auth = auth_base64_bytes.decode(encoding='utf-8')
        self.press_format = press_format

    def check_response(self, res, success_code):
        try:
            json_object = json.loads(res.content)
        except ValueError as ex:
            raise WordPressError(self, res.status_code, res.reason, str(ex))
        if res.status_code != success_code:
            if type(json_object) is dict and 'message' in json_object:
                raise WordPressError(self, res.status_code,
                                     res.reason, json_object['message'])
            else:
                raise WordPressError(self, res.status_code,
                                     res.reason, res.text)
        return json_object

    def add_post(self, title, content, status='draft', excerpt=None, featured_media_id=None, categorie_ids=[], tag_ids=[]):
        headers = self.get_headers()
        headers["content-type"] = "application/json"
        data = {
            'title': title,
            'status': status,
            'content': content,
            'format': self.press_format,
            'categories': categorie_ids,
            'tags': tag_ids
        }
        if excerpt is not None:
            data['excerpt'] = excerpt
        if featured_media_id is not None:
            data['featured_media'] = featured_media_id
        res = requests.post(
            f'{self.url}/wp-json/wp/v2/posts', json=data, headers=headers)
        return self.check_response(res, 201)

    def get_headers(self):
        headers = {
            'Authorization': 'Basic ' + self.auth
        }

        return headers

    def update_post(self, id, title, content, excerpt=None, featured_media_id=None, categorie_ids=[], tag_ids=[]):
        headers = self.get_headers()
        data = {
            'title': title,
            'content': content,
            'format': self.press_format,
            'categories': categorie_ids,
            'tags': tag_ids
        }
        if excerpt is not None:
            data['excerpt'] = excerpt
        if featured_media_id is not None:
            data['featured_media'] = featured_media_id
        res = requests.post(
            f'{self.url}/wp-json/wp/v2/posts/{id}', json=data, headers=headers)
        return self.check_response(res, 200)

    def upload_media(self,
                     path,
                     slug=None,
                     title=None,
                     alt_text=None,
                     caption=None,
                     description=None,
                     status='publish'):
        file_name = os.path.basename(path)
        _, file_ext = os.path.splitext(file_name)
        content_type = 'image/jpeg'
        if file_ext == '.jpeg' or file_ext == '.jpg':
            content_type = 'image/jpeg'
        if file_ext == '.png':
            content_type = 'image/png'

        fields = {
            'file': (file_name,
                     open(path, 'rb'), content_type),
            'status': status,
        }
        if slug is not None:
            fields['slug'] = slug
        if title is not None:
            fields['title'] = title
        if alt_text is not None:
            fields['alt_text'] = alt_text
        if caption is not None:
            fields['caption'] = caption
        if description is not None:
            fields['description'] = description

        multipart_data = MultipartEncoder(fields=fields)
        headers = {
            'Authorization': 'Basic ' + self.auth,
            'Content-Type': multipart_data.content_type,
        }

        res = requests.post(
            f'{self.url}/wp-json/wp/v2/media', data=multipart_data, headers=headers)
        return self.check_response(res, 201)

    def get_tags(self):
        headers = self.get_headers()
        tag_list = []

        per_page = 100
        page: int = 1

        while True:
            res = requests.get(
                f'{self.url}/wp-json/wp/v2/tags/?context=embed&per_page={per_page}&page={page}', headers=headers)
            items = self.check_response(res, 200)
            if 0 == len(items):
                return tag_list
            tag_list.extend(items)
            if per_page > len(items):
                return tag_list
            page += 1

    def get_categories(self):
        headers = self.get_headers()
        category_list = []

        per_page = 100
        page: int = 1

        while True:
            res = requests.get(
                f'{self.url}/wp-json/wp/v2/categories/?context=embed&per_page={per_page}&page={page}', headers=headers)
            items = self.check_response(res, 200)
            if 0 == len(items):
                return category_list
            category_list.extend(items)
            if per_page > len(items):
                return category_list
            page += 1

    def get_medias(self):
        headers = self.get_headers()
        media_list = []

        per_page = 100
        page: int = 1

        while True:
            res = requests.get(
                f'{self.url}/wp-json/wp/v2/media/?context=embed&per_page={per_page}&page={page}', headers=headers)
            items = self.check_response(res, 200)
            if 0 == len(items):
                return media_list
            media_list.extend(items)
            if per_page > len(items):
                return media_list
            page += 1

    def post_tag(self, name, slug, description=None):
        headers = self.get_headers()
        data = {
            'name': name,
            'slug': slug,
        }
        if description is not None:
            data['description'] = description
        res = requests.post(
            f'{self.url}/wp-json/wp/v2/tags', json=data, headers=headers)
        return self.check_response(res, 201)

    @staticmethod
    def convert_stug_to_id(slug, datas):
        for data in datas:
            if data['slug'] == slug:
                return data['id']

        return None

    @staticmethod
    def exist_by_name(name, datas):
        for data in datas:
            if data['name'] == name:
                return True
        return False
