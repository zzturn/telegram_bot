import requests

from logger.logger_config import setup_logger

logger = setup_logger('wayback')


def snapshot_with_wayback_api(url: str):
    """使用wayback机制进行快照

    Args:
        url (str): 目标网页
    """
    wayback_api_url = 'https://web.archive.org/save/'
    response = requests.get(wayback_api_url + url)
    logger.info(f"wayback response: {response.status_code}")
    if response.status_code == 200:
        return {'url': response.url, 'text': response.text}
    else:
        raise Exception(response.text)


if __name__ == '__main__':
    snapshot_with_wayback_api('https://blog.csdn.net/qq_30934923/article/details/119803947')
