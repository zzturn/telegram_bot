import datetime
import re

import telegram.constants
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from telegram.helpers import escape_markdown

from config.config import configInstance
from handlers.constants import error_title, operation_title, COMMAND_SUMMARIZE, COMMAND_BACKUP
from logger.logger_config import setup_logger
from url.snapshot_with_selenium import get_text_by_selenium, get_url_info_by_selenium
from url.snapshot_with_wayback import snapshot_with_wayback_api
from url.utils import summarize_content, github_repo

retry_times = configInstance.ai_retry_times

logger = setup_logger('url')


async def summarize_url_text(update: Update, context: CallbackContext) -> None:
    if len(context.args) == 0:
        await update.message.reply_text(
            f"{error_title}{escape_markdown(f'Please input a url.eg: /{COMMAND_SUMMARIZE} https://www.google.com', 2)}",
            parse_mode=ParseMode.MARKDOWN_V2)
        return
    url = context.args[0]
    if not is_url(url):
        msg = f'{error_title}{escape_markdown("Please input a valid url.", 2)}'
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
        return
    url_content_text = None

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    logger.info(f"Begin to summarize {url}")
    try:
        url_content_text = get_text_by_selenium(url)
    except Exception as e:
        logger.error(f"😿 文章->{url} selenium 抓取失败! Error: {str(e)}")
        await update.message.reply_text(
            f'{operation_title}{escape_markdown(url, 2)} 摘要生成失败!\n\nSave snapshot failed, error: {escape_markdown(str(e), 2)}',
            parse_mode=ParseMode.MARKDOWN_V2)
    if url_content_text is None or url_content_text == '':
        msg = f'{operation_title}{escape_markdown("Selenium failed to get the content of the url.", 2)}'
        logger.error(f"😿 文章->{url} selenium 抓取失败! 返回结果为 None 或 空字符串")
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

    prompt = configInstance.ai_prompt + "\n" + url_content_text
    for i in range(retry_times):
        try:
            response = summarize_content(prompt=prompt, api_key=configInstance.zhipuai_key)
            if response['code'] == 200:
                logger.info(f"🐱 文章->{url} 摘要第生成成功! Cost: {response['data']['usage']}")
                msg = f"{operation_title}{escape_markdown(url, 2)} 摘要生成成功！\n\n{escape_markdown(response['data']['choices'][0]['content'], 2)}"
                await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
                return
            else:
                logger.error(f"😿 文章->{url} 摘要第 {i + 1} 次返回错误! Error: {response['msg']}")
                continue
        except Exception as e:
            logger.error(f"😿 文章->{url} 摘要第 {i + 1} 次生成失败! Error: {str(e)}")
            continue
    msg = f'{operation_title}{escape_markdown(url, 2)}摘要生成失败，请稍后再试。'
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def save_url(update: Update, context: CallbackContext) -> None:
    if len(context.args) == 0:
        await update.message.reply_text(
            f'{error_title}{escape_markdown("Please input a url.eg: /{COMMAND_BACKUP} https://www.google.com", 2)}',
            parse_mode=ParseMode.MARKDOWN_V2)
        return
    url = context.args[0]

    if not is_url(url):
        msg = f'{error_title}{escape_markdown("Please input a valid url.", 2)}'
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
        return

    # mobile to use mobile user agent(only selenium)
    # selenium to use selenium to get html
    # wayback to use wayback to get html
    # default to use selenium and wayback
    args = context.args[1:]
    mobile = True if 'mobile' in args else False
    use_selenium = True if 'selenium' in args else False
    use_wayback = True if 'wayback' in args else False
    if not use_wayback and not use_selenium:
        use_selenium = True
        use_wayback = True

    url_html = None
    title = None

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING)

    logger.info(f"Begin to upload {url} to Github.")
    sg_url = ''
    sp_url = ''
    wb_url = ''
    wg_url = ''
    wp_url = ''
    selenium_error = None
    wayback_error = None
    if use_selenium:
        try:
            url_html, title = get_url_info_by_selenium(url, mobile=mobile)
            path = f"{configInstance.github_file_prefix}/{title}.html"
            github_repo.create_or_update_file(path, url_html, f"Add {path}")
            sg_url = f"https://github.com/{configInstance.github_username}/{configInstance.github_repo}/blob/master/{path}"
            sp_url = f"https://{configInstance.github_username}.github.io/{configInstance.github_repo}/{path}"
        except Exception as e:
            selenium_error = str(e)

    if use_wayback:
        try:
            wayback_json = snapshot_with_wayback_api(url)
            wb_url = wayback_json['url']
            wayback_html = wayback_json['text']
            wayback_html = wayback_html.replace('href="//', 'href="https://')
            w_path = f"{configInstance.github_file_prefix}/wayback/{transfer_now_time()}.html"
            github_repo.create_or_update_file(w_path, wayback_html, f"Add {w_path}")
            wg_url = f"https://github.com/{configInstance.github_username}/{configInstance.github_repo}/blob/master/{w_path}"
            wp_url = f"https://{configInstance.github_username}.github.io/{configInstance.github_repo}/{w_path}"
        except Exception as e:
            wayback_error = str(e)

    res_msg = f"""
    {operation_title}{escape_markdown(url, 2)} 
    备份结果：
    *[{escape_markdown('selenium_github_url', 2)}]({escape_markdown(sg_url, 2)})*
    *[{escape_markdown('selenium_page_url', 2)}]({escape_markdown(sp_url, 2)})*
    *[{escape_markdown('wayback_url', 2)}]({escape_markdown(wb_url, 2)})*
    *[{escape_markdown('wayback_github_url', 2)}]({escape_markdown(wg_url, 2)})*
    *[{escape_markdown('wayback_page_url', 2)}]({escape_markdown(wp_url, 2)})*
    {escape_markdown(selenium_error, 2) if selenium_error else ''}
    {escape_markdown(wayback_error, 2) if wayback_error else ''}
    """
    await update.message.reply_text(res_msg, parse_mode=ParseMode.MARKDOWN_V2)


def is_url(url):
    return re.match(r'^https?:/{2}\w.+$', url)


def transfer_now_time():
    now = datetime.datetime.now()
    return now.strftime("%Y%m%d%H%M%S%f")[:-3]
