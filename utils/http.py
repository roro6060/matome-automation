from fake_useragent import UserAgent
from requests.models import HTTPError


def generate_header(fake_useragent=False):
    user_agent = ''
    header = {
        'User-Agent': user_agent
    }
    if fake_useragent:
        user_agent = UserAgent()
        header['User-Agent'] = user_agent.chrome

    return header



