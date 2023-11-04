import time
from typing import Tuple

import html2text
import requests
from bs4 import BeautifulSoup
from selenium import webdriver

from config.config import configInstance
from logger.logger_config import setup_logger

logger = setup_logger('snapshot')


def get_url_info_by_selenium(url: str):
    """发起GET请求，获取文本

    Args:
        url (str): 目标网页
    """
    # resp = send_get_request(url=url, params=params, timeout=timeout, **kwargs)
    html_content = None
    title = None
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Remote(
            command_executor=configInstance.selenium_server,
            options=options)

        # 访问网页
        driver.get(url)

        # 获取网页的高度
        height = driver.execute_script("return document.body.scrollHeight")

        # 从顶部开始，模拟浏览网页的过程
        for i in range(0, height, 200):
            # 使用JavaScript代码控制滚动条滚动
            driver.execute_script(f"window.scrollTo(0, {i});")
            # 暂停一段时间，模拟人类浏览网页的速度
            time.sleep(0.2)

        driver.implicitly_wait(5)

        # 获取网页源代码
        source = driver.page_source
        title = driver.title
    except Exception as e:
        msg = f"selenium 发生异常 {str(e)}"
        logger.warning(msg)
        raise Exception(msg) from e
    finally:
        if driver is not None:
            driver.quit()

    try:
        new_soup = BeautifulSoup(source, 'html.parser')

        # 下列处理其实都是针对微信公众号文章的，暂不清楚对其他网页是否有影响

        # 找到所有的<img>标签，将图片的src属性设置为data-src属性的值，并生成外链
        img_tags = new_soup.find_all('img')
        for img in img_tags:
            # 如果<img>标签有data-src属性
            if img.has_attr('data-src'):
                # 将src属性设置为data-src属性的值
                img['src'] = 'https://images.weserv.nl/?url=' + img['data-src']

        # 找到所有的<link>标签，如果href属性的值不是以https:开头，则添加https:前缀
        link_tags = new_soup.find_all('link')
        for link in link_tags:
            # 如果<link>标签有href属性
            if link.has_attr('href'):
                # 如果href属性的值不以https:开头
                if not link['href'].startswith('https:') and not link['href'].startswith('http:'):
                    # 在href属性的值前面添加https:
                    link['href'] = 'https:' + link['href']

        # 找到所有的<script>标签，删除这些标签
        script_tags = new_soup.find_all('script')
        for script in script_tags:
            # 删除<script>标签
            script.decompose()

        html_content = new_soup.prettify()
    except Exception as e:
        logger.warning(f"请求发生异常 {str(e)}")

    return html_content, title


def get_text_by_selenium(url) -> str:
    html, _ = get_url_info_by_selenium(url)
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text()


def get_markdown_by_selenium(url) -> str:
    html, _ = get_url_info_by_selenium(url)
    converter = html2text.HTML2Text()
    converter.hard_wrap = True
    return converter.handle(html)


def get_title_with_request(url):
    try:
        # 发起HTTP GET请求获取网页内容
        response = requests.get(url)

        # 检查响应状态码，确保请求成功
        if response.status_code == 200:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # 使用soup.title获取页面的标题标签内容
            title = soup.title.string

            return title
        else:
            logger.error(f"Failed to fetch content from URL. Status code: {response.status_code}")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

    return None


def get_title_with_selenium(url):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Remote(
        command_executor=configInstance.selenium_server,
        options=options)
    # 访问网页
    driver.get(url)
    driver.implicitly_wait(2)  # 等待10秒，你可以根据实际情况调整这个时间

    return driver.title




if __name__ == '__main__':
    url = 'https://mp.weixin.qq.com/s/HtQLt33NKRaNO3c9rIq80g'
    print(get_url_info_by_selenium(url))
