import base64
import json
import re

import requests
import zhipuai as zhipuai

from config.config import configInstance
from logger.logger_config import setup_logger

logger = setup_logger('utils')

class GitHubRepo:
    BASE_URL = "{base_url}/repos/{repo}/contents/"

    def __init__(self, token, repo, base_url="https://api.github.com"):
        self.token = token
        self.repo = repo
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = base_url

    def get_contents(self, path):
        response = requests.get(self.BASE_URL.format(base_url=self.base_url, repo=self.repo) + path,
                                headers=self.headers)
        if response.status_code == 200:
            file_info = response.json()
            content = base64.b64decode(file_info["content"]).decode("utf-8")
            return content
        else:
            return None

    def create_or_update_file(self, path, content, message):
        # 检查文件是否存在
        file_info = requests.get(self.BASE_URL.format(base_url=self.base_url, repo=self.repo) + path,
                                 headers=self.headers)
        data = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8")
        }
        if file_info.status_code == 200:
            # 文件存在，执行更新
            file_info = file_info.json()
            sha = file_info["sha"]
            data['sha'] = sha
        response = requests.put(self.BASE_URL.format(base_url=self.base_url, repo=self.repo) + path,
                                headers=self.headers,
                                data=json.dumps(data))
        logger.info(response.status_code)

        if response.status_code != 200 and response.status_code != 201:
            raise Exception(f"Create or update file {path} failed, error: {response.text}")


    def update_file(self, path, content, message):
        file_info = requests.get(self.BASE_URL.format(base_url=self.base_url, repo=self.repo) + path,
                                 headers=self.headers).json()
        sha = file_info["sha"]

        data = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "sha": sha
        }
        response = requests.put(self.BASE_URL.format(base_url=self.base_url, repo=self.repo) + path,
                                headers=self.headers,
                                data=json.dumps(data))
        return response.status_code == 200

    def create_file(self, path, content, message):
        data = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8")
        }
        response = requests.put(self.BASE_URL.format(base_url=self.base_url, repo=self.repo) + path,
                                headers=self.headers,
                                data=json.dumps(data))
        return response.status_code == 201

    def delete_file(self, path, message):
        file_info = requests.get(self.BASE_URL.format(base_url=self.base_url, repo=self.repo) + path,
                                 headers=self.headers).json()
        sha = file_info["sha"]

        data = {
            "message": message,
            "sha": sha
        }
        response = requests.delete(self.BASE_URL.format(base_url=self.base_url, repo=self.repo) + path,
                                   headers=self.headers,
                                   data=json.dumps(data))
        return response.status_code == 200


github_repo = GitHubRepo(token=configInstance.github_token,
                         repo=f"{configInstance.github_username}/{configInstance.github_repo}",
                         base_url=configInstance.github_api_base)


def sanitize_string(input_str):
    illegal_re = r'[~^:*?[\]\\/|<>".%]'
    control_re = r'[\x00-\x1f\x7f]'
    reserved_re = r'^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?$'
    windows_re = r'^[. ]+'

    input_str = re.sub(illegal_re, '', input_str)
    input_str = re.sub(control_re, '', input_str)
    input_str = re.sub(reserved_re, '', input_str, flags=re.I)
    input_str = re.sub(windows_re, '', input_str)

    return input_str


def summarize_content(prompt: str, api_key: str, model_name="chatglm_turbo", **kwargs):
    zhipuai.api_key = api_key
    response = zhipuai.model_api.invoke(model=model_name,
                                        prompt=[{"role": "user", "content": prompt}],
                                        temperature=0.95,
                                        top_p=0.7,
                                        return_type="text",
                                        **kwargs)
    return response
