import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from telegram.helpers import escape_markdown

from config.config import configInstance
from handlers.constants import error_title, operation_title
from logger.logger_config import setup_logger
from url.snapshot_with_selenium import get_text_by_selenium, get_url_info_by_selenium
from url.snapshot_with_wayback import snapshot_with_wayback_api
from url.utils import summarize_content, github_repo

retry_times = configInstance.ai_retry_times

logger = setup_logger('url')


async def summarize_url_text(update: Update, context: CallbackContext) -> None:
    url = context.args[0]
    if not is_url(url):
        msg = f'{error_title}Please input a valid url.'
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return
    url_content_text = None

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    logger.info(f"Begin to summarize {url}")
    try:
        url_content_text = get_text_by_selenium(url)
    except Exception as e:
        logger.error(f"😿 文章->{url} selenium 抓取失败! Error: {str(e)}")
        await update.message.reply_text(f'{operation_title}{url} 摘要生成失败!\n\nSave snapshot failed, error: {e}')
    if url_content_text is None or url_content_text == '':
        msg = f'{operation_title}Selenium failed to get the content of the url.'
        logger.error(f"😿 文章->{url} selenium 抓取失败! 返回结果为 None 或 空字符串")
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    prompt = configInstance.ai_prompt + "\n" + url_content_text
    for i in range(retry_times):
        try:
            response = summarize_content(prompt=prompt, api_key=configInstance.zhipuai_key)
            if response['code'] == 200:
                logger.info(f"🐱 文章->{url} 摘要第生成成功! Cost: {response['data']['usage']}")
                msg = f"{operation_title}{url} 摘要生成成功！\n\n{response['data']['choices'][0]['content']}"
                await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
                return
            else:
                logger.error(f"😿 文章->{url} 摘要第 {i + 1} 次返回错误! Error: {response['msg']}")
                continue
        except Exception as e:
            logger.error(f"😿 文章->{url} 摘要第 {i + 1} 次生成失败! Error: {str(e)}")
            continue
    msg = f'{operation_title}{url}摘要生成失败，请稍后再试。'
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def save_url(update: Update, context: CallbackContext) -> None:
    url = context.args[0]
    if not is_url(url):
        msg = f'{error_title}Please input a valid url.'
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return
    url_html = None
    title = None

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    logger.info(f"Begin to upload {url} to Github.")
    try:
        url_html, title = get_url_info_by_selenium(url)
        path = configInstance.github_file_path.format_map({'title': title})
        github_repo.create_or_update_file(path, url_html, f"Add {path}")
        github_content_url = f"https://github.com/{configInstance.github_username}/{configInstance.github_repo}/blob/master/{path}"
        pages_url = f"https://{configInstance.github_username}.github.io/{configInstance.github_repo}/{path}"
        selenium_msg = f"Github: {github_content_url}\nPages: {pages_url}"
    except Exception as e:
        selenium_msg = f"Save snapshot failed, error: {str(e)}"

    try:
        wayback_msg = snapshot_with_wayback_api(url)
    except Exception as e:
        wayback_msg = f"Save snapshot failed, error: {str(e)}"

    res_msg = f"{operation_title}{url} 备份结果：\n\n*wayback*: {escape_markdown(wayback_msg)}\n\n*selenium*: {escape_markdown(selenium_msg)}"
    await update.message.reply_text(res_msg, parse_mode=ParseMode.MARKDOWN)


def is_url(url):
    return re.match(r'^https?:/{2}\w.+$', url)
