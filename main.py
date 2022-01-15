from AI.summarizer import Summarizer
from models.settings.genshin_settings import Genshin_settings
import logging
import sys
streamHandler = logging.StreamHandler(sys.stdout)
fileHandler = logging.FileHandler('./logs/summarize.log', encoding='utf-8')
logging.basicConfig(
    handlers=[streamHandler, fileHandler],
    level=logging.INFO,
    format='%(asctime)s:[%(levelname)s] %(message)s'
)


if __name__ == '__main__':
    # wordpress 情報を追加
    wordpress_url = ''
    wordpress_user = ''
    wordpress_password = ''

    target_datas = {}
    target_datas['wordpress_url'] = wordpress_url
    target_datas['wordpress_user'] = wordpress_user
    target_datas['wordpress_password'] = wordpress_password

    settings = Genshin_settings(**target_datas)
    # Trueの場合htmlとして記事を保存しwordpressに投稿されない
    settings.save_outputs = True

    smr = Summarizer(settings)
    smr()
