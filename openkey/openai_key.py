import copy
import email
import imaplib
import json
import os
import random
import re
import string
import time
from abc import ABC, abstractmethod

import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config.config import configInstance
from logger.logger_config import setup_logger
from db.redis_config import redis_conn

logger = setup_logger(__name__)


class Email(ABC):

    def __init__(self, email_item):
        self.email_item = email_item

    @abstractmethod
    def read_email_code(self):
        pass


class Gmail(Email):
    gmail_client_config = {
        "web": {
            "client_id": os.environ.get('GOOGLE_CLIENT_ID'),
            "client_secret": os.environ.get('GOOGLE_CLIENT_SECRET')
        }
    }
    logger.info(f"Gmail config initialized")

    def __init__(self, email_item):
        super().__init__(email_item)
        self.creds = None
        self.email = email_item['email']
        self.refresh_token = email_item['refresh_token']

    def get_creds(self):
        return Credentials.from_authorized_user_info(
            {
                "refresh_token": self.refresh_token,
                "client_id": self.gmail_client_config['web']['client_id'],
                "client_secret": self.gmail_client_config['web']['client_secret']
            }
        )

    def read_email_code(self, wait_time=30):
        try:
            self.creds = self.get_creds()
        except Exception as e:
            logger.error(f"获取 {self.email} 的凭证失败: {e}")
            raise Exception(f"获取 {self.email} 的凭证失败: {e}")
        service = build('gmail', 'v1', credentials=self.creds)
        code = ""
        # 最多等待 wait_time 秒
        current_iteration = 0

        while code == "" and current_iteration < wait_time:
            results = service.users().messages().list(userId='me',
                                                      q='is:unread in:inbox from:support@openkey.cloud',
                                                      labelIds=['INBOX']).execute()
            messages = results.get('messages', [])
            logger.debug(f"Get gmail emails: {messages}")
            if messages:
                msg = service.users().messages().get(userId='me', id=messages[0]['id']).execute()
                # 使用正则表达式匹配数字部分
                code = re.search(r'\d+', msg['snippet']).group()
                # 创建邮件的已读标记请求
                ids = [msg['id'] for msg in messages]
                mark_as_read_request = {
                    'ids': ids,
                    'removeLabelIds': ['UNREAD']
                }
                res = service.users().messages().batchModify(userId='me', body=mark_as_read_request).execute()
                logger.debug(res)
            time.sleep(1)
            current_iteration += 1
        if code == "":
            raise Exception(f"未找到 {self.email} 的未读邮件")
        return [{"code": code, "email": self.email}]


class ICloud(Email):
    icloud_client_config = {
        "imap_server": "imap.mail.me.com",
        "imap_port": 993,
        "username": os.environ.get('ICLOUD_USERNAME'),
        "password": os.environ.get('ICLOUD_PASSWORD')
    }
    logger.info(f"iCloud config initialized")

    def __init__(self, email_item):
        super().__init__(email_item)
        self.M = None
        self.email = email_item['email']

    def read_email_code(self):
        """
        读取所有邮件中的验证码
        :return: [{code, email}]
        """
        self.M = imaplib.IMAP4_SSL(self.icloud_client_config['imap_server'], self.icloud_client_config['imap_port'])
        self.M.login(self.icloud_client_config['username'], self.icloud_client_config['password'])
        try:
            self.open_inbox()
            email_ids = self.search_emails()
            if len(email_ids) == 0:
                raise Exception(f"未找到 {self.email} 主题为 水龙头 的未读邮件")
            code_and_email_list = self.fetch_emails(email_ids)
            return code_and_email_list
        except Exception as e:
            logger.error(e)
        finally:
            self.M.logout()

    def open_inbox(self):
        rv, data = self.M.select("INBOX")
        if rv == 'OK':
            return data
        else:
            raise Exception("Unable to open inbox")

    def search_emails(self):
        rv, data = self.M.uid('search', None, '(UNSEEN)')
        if rv == 'OK':
            return data[0].split() if data[0] else []
        else:
            raise Exception("Unable to search emails")

    def fetch_emails(self, email_ids):
        code_and_address = []
        for num in email_ids:
            rv, data = self.M.uid('fetch', num, '(BODY[])')
            if rv == 'OK':
                raw_email = data[0][1]
                email_message = email.message_from_bytes(raw_email)
                body = ""
                if email_message.is_multipart():
                    for payload in email_message.get_payload():
                        body = payload.get_payload(decode=True)
                else:
                    body = email_message.get_payload(decode=True)
                code_pattern = r"验证码(\d{4})"
                match = re.search(code_pattern, body.decode())
                if not match:
                    continue
                code = match.group(1)
                email_pattern = r"\b[a-zA-Z0-9_]+@icloud.com\b"
                to_mail = re.findall(email_pattern, email_message['To'])[0]
                code_and_address.append({'code': code, 'email': to_mail})

                # Mark the email as read
                self.M.uid('MOVE', num, '"Deleted Messages"')
        return code_and_address


headers = {
    'authority': 'faucet.openkey.cloud',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en,zh-CN;q=0.9,zh;q=0.8',
    'content-type': 'application/json',
    'origin': 'https://faucet.openkey.cloud',
    'referer': 'https://faucet.openkey.cloud/',
    'sec-ch-ua': '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
}
request_for_code_url = 'https://faucet.openkey.cloud/api/send_verification_code'

def generate_random_letters(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))

class OpenaiKey:
    email_items = configInstance.get_email_items()

    # 请求头信息

    def hack_openai_token(self, num_keys: int = 1) -> list:
        # 随机打乱email_items的顺序
        random.shuffle(self.email_items)

        keys = []
        email_addresses = []
        for email_item in self.email_items:
            if len(keys) >= num_keys:
                break
            if redis_conn.exists(email_item['email']):
                continue

            # 调用request_for_email_code方法
            code_res = self.request_for_email_code(email_item['email'])
            if code_res.status_code != 200 or code_res.json().get('status') != 1:
                logger.info(
                    f"Request for {email_item['email']} code failed,\
                    res: {code_res.text.encode().decode('unicode_escape')}")
                continue
            time.sleep(10)
            mail = None
            if email_item['email'].endswith('@gmail.com'):
                mail = Gmail(email_item)
            elif email_item['email'].endswith('@icloud.com'):
                mail = ICloud(email_item)
            else:
                continue

            code_list = mail.read_email_code()

            logger.debug(f"Get code list: {code_list}")

            if code_list is None:
                continue

            for ec in code_list:
                # 调用request_for_openai_key方法
                token = self.request_for_openai_key_and_set_cache(ec['email'], ec['code'])
                if token is not None:
                    keys.append(token)
                    email_addresses.append(ec['email'])

        logger.debug(f"Get {len(keys)} keys: {keys}, from {email_addresses}")
        return keys

    def hack_openai_token_via_plus_gmail(self, num_key: int = 1) -> list:
        random.shuffle(self.email_items)
        list = [x for x in self.email_items if x['email'].endswith('@gmail.com')]
        if len(list) == 0:
            return []
        email_item = list[0]
        keys = []
        count = 0
        while len(keys) < num_key and count < 2 * num_key:
            count += 1
            item = copy.copy(email_item)
            item['email'] = item['email'].replace('@gmail.com', f'+{generate_random_letters(5)}@gmail.com')
            code_res = self.request_for_email_code(item['email'])
            if code_res.status_code != 200 or code_res.json().get('status') != 1:
                logger.info(
                    f"Request for {item['email']} code failed,\
                    res: {code_res.text.encode().decode('unicode_escape')}")
                continue
            time.sleep(10)
            mail = Gmail(item)
            code_list = mail.read_email_code()
            if code_list is None:
                continue
            for ec in code_list:
                # 调用request_for_openai_key方法
                token = self.request_for_openai_key_and_set_cache(ec['email'], ec['code'])
                if token is not None:
                    keys.append(token)
                    logger.debug(f"Get {len(keys)} keys: {keys}, from {ec['email']}")
        return keys



    def request_for_email_code(self, email_address: str):
        # 请求数据
        data = f'{{"email": "{email_address}"}}'

        # 发送 POST 请求
        response = requests.post(request_for_code_url, headers=headers, data=data)
        logger.info(f"Request for {email_address} code, res: {response.text.encode().decode('unicode_escape')}")
        return response

    def read_code_and_request_key(self, email_address: str):
        if email_address.endswith('@gmail.com'):
            email_item = [x for x in configInstance.get_email_items() if x['email'] == email_address]
            if len(email_item) == 0:
                raise Exception(f"Unsupported email address: {email_address}")
            email_and_code_list = Gmail(email_item[0]).read_email_code()
        elif email_address.endswith('@icloud.com'):
            email_and_code_list = ICloud({'email': email_address}).read_email_code()
        else:
            raise Exception(f"Unsupported email address: {email_address}")

        if email_and_code_list is None or len(email_and_code_list) == 0:
            raise Exception(f"Read code from {email_address} failed")

        tokens = []
        for emaiL_and_code in email_and_code_list:
            try:
                token = self.request_for_openai_key_and_set_cache(emaiL_and_code['email'], emaiL_and_code['code'])
            except Exception as e:
                logger.error(f"Request for openai key failed, args: {emaiL_and_code}, error: {e}")
                continue
            if token is not None:
                tokens.append(token)
        return tokens

    def request_for_openai_key(self, email_address: str, code: str) -> str:
        # 请求数据
        data = f'{{"email": "{email_address}", "code": "{code}"}}'

        # 发送 POST 请求
        url = 'https://faucet.openkey.cloud/api/verify_code'
        response = requests.post(url, headers=headers, data=data)
        res_text = response.text
        print(res_text)
        return json.loads(res_text).get('token')

    def request_for_openai_key_and_set_cache(self, email_address: str, code: str) -> str:
        token = self.request_for_openai_key(email_address, code)
        if token is not None:
            redis_conn.sadd('all_openai_key', token)
            redis_conn.setex(email_address, token, 60 * 60 * 24)
        return token

def request_refresh_token():
    creds = None
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']
    google_config = {
        "web": {
            "client_id": configInstance.google_client_id,
            "client_secret": configInstance.google_client_secret,
            "project_id": "gmail-402307", "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost:8080/"]
        }
    }

    flow = InstalledAppFlow.from_client_config(google_config, SCOPES)
    creds = flow.run_local_server(port=8080, open_browser=False)
    print(creds.refresh_token)


def validate_openai_key(key: str) -> bool:
    url = 'https://openkey.cloud/v1/dashboard/billing/subscription'
    validate_headers = headers.copy()
    validate_headers['Authorization'] = f'Bearer {key}'
    logger.debug(f"Begin to validate openai key: {key}")
    response = requests.get(url, headers=validate_headers)
    res_data = response.json()
    logger.debug(f"Validate openai key: {key}, code: {response.status_code}, response: {res_data}")
    if response.status_code == 200:
        return True
    else:
        return False


def test_read_gmail():
    for email_item in configInstance.get_email_items():
        print(email_item)
        if email_item['email'].endswith('@gmail.com'):
            try:
                res = Gmail(email_item).read_email_code(2)
            except Exception as e:
                print(e)
                continue
            print(res)


def main():
    from dotenv import load_dotenv

    load_dotenv(dotenv_path='../.env')
    openai_key = OpenaiKey()
    # keys = openai_key.hack_openai_token(1)
    keys = openai_key.hack_openai_token_via_plus_gmail()
    print(keys)


if __name__ == '__main__':
    # item = [x for x in configInstance.get_email_items() if x['email'] == 'luoxin9712@gmail.com'][0]
    # r = Gmail(item).read_email_code()
    # r = ICloud({'email': 'item'}).read_email_code()
    # OpenaiKey().request_for_openai_key(r[0]['email'], r[0]['code'])
    # test_read_gmail()
    # request_refresh_token()
    main()
