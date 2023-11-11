import json
import os
from dotenv import load_dotenv

import yaml

load_dotenv()


class Config:
    telegram_bot_token = None
    developer_chat_id = None
    icloud_username = None
    icloud_password = None
    google_client_id = None
    google_client_secret = None
    email_items = None
    redis_host = None
    redis_port = None

    def __init__(self):
        # telegram bot token
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        # telegram bot api base url
        self.telegram_bot_api_base = os.getenv("TELEGRAM_BOT_API_BASE", "https://api.telegram.org/bot")
        # telegram chat id
        self.developer_chat_id = int(os.getenv("DEVELOPER_CHAT_ID", ""))

        # icloud 主账号邮箱
        self.icloud_username = os.getenv("ICLOUD_USERNAME", "")
        # icloud 主账号密码（App 专用密码）
        self.icloud_password = os.getenv("ICLOUD_PASSWORD", "")

        # gmail 应用 client id
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        # gmail 应用n client secret
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

        self.email_items = []
        account_path = 'account.yml'
        if os.path.exists(account_path):
            # 邮箱地址 以及 refresh token(可选)
            with open(account_path, 'r') as f:
                self.email_items = yaml.safe_load(f)['accounts']

        # redis_conn 配置
        self.redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        self.redis_port = os.getenv("REDIS_PORT", 6379)

        # selenium 配置
        self.selenium_server = os.getenv("SELENIUM_SERVER", "http://127.0.0.1:4444/wd/hub")

        # ai 配置
        self.ai_prompt = os.getenv("PROMPT", "🤖")
        self.ai_retry_times = int(os.getenv("RETRY_TIMES", 3))

        # open ai 配置
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        # open ai api 地址，用于反向代理，eg: https://ghproxy.com/https://api.openai.com/v1
        self.openai_api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

        # 智谱 ai 配置
        self.zhipuai_key = os.getenv("ZHIPUAI_KEY", "")

        # GitHub 配置
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.github_username = os.getenv("GITHUB_USERNAME", "")
        self.github_repo = os.getenv("GITHUB_REPO", "")
        # 文件存放路径
        self.github_file_prefix = os.getenv("GITHUB_FILE_PREFIX", "docs").strip('/')
        # GitHub API 地址，用于反向代理，eg: https://ghproxy.com/https://api.github.com
        self.github_api_base = os.getenv("GITHUB_API_BASE", "https://api.github.com").rstrip('/')

        # Cloudflare 配置
        self.cf_api_key = os.getenv("CF_API_KEY", "")
        self.cf_account_id = os.getenv("CF_ACCOUNT_ID", "")
        self.cf_namespace_id = os.getenv("CF_NAMESPACE_ID", "")

    def get_email_items(self):
        return self.email_items


# 创建一个全局的配置实例
configInstance = Config()

if __name__ == "__main__":
    # 示例用法
    print("Telegram Bot Token:", configInstance.telegram_bot_token)
    print("Email Items:", configInstance.get_email_items())
