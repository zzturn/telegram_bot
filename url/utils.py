import base64
import json
import re

import requests
import zhipuai as zhipuai
import openai

from config.config import configInstance
from logger.logger_config import setup_logger

logger = setup_logger('utils')


class GitHubRepo:
    def __init__(self, token, repo, base_url="https://api.github.com", branch="master"):
        self.token = token
        self.repo = repo
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.url = f'{base_url}/repos/{self.repo}'
        self.branch = branch

    def make_github_request(self, method, endpoint, data=None, params=None, is_json=True):
        url = f"{self.url}{endpoint}"
        headers = self.headers
        if is_json and data:
            data = json.dumps(data)
        response = requests.request(method, url, headers=headers, data=data, params=params)
        if response.ok:
            return response.json()
        else:
            response.raise_for_status()

    def get_branch_info(self):
        return self.make_github_request('GET', f'/branches/{self.branch}')

    def get_contents(self, path):
        try:
            file_info = self.make_github_request('GET', f'/contents/{path}?ref={self.branch}')
            content = base64.b64decode(file_info["content"]).decode("utf-8")
            return content
        except requests.HTTPError:
            return None

    def create_or_update_file(self, path, content, message):
        branch_info = self.get_branch_info()
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        data = {
            "message": message,
            "content": encoded_content,
            "branch": self.branch
        }
        try:
            file_info = self.make_github_request('GET', f'/contents/{path}?ref={self.branch}')
            if 'sha' in file_info:
                data['sha'] = file_info['sha']  # 文件存在，添加sha进行更新
        except requests.HTTPError as e:
            if e.response.status_code != 404:
                raise  # 如果不是404错误，重新抛出异常

        response = self.make_github_request('PUT', f'/contents/{path}', data)
        return response

    def delete_file(self, path, message):
        branch_info = self.get_branch_info()
        file_info = self.make_github_request('GET', f'/contents/{path}?ref={self.branch}')
        data = {
            "message": message,
            "sha": file_info["sha"],
            "branch": self.branch
        }
        if 'commit' in branch_info:
            data['branch'] = branch_info['commit']['sha']
        response = self.make_github_request('DELETE', f'/contents/{path}', data)
        return response

    def add_files_to_repo(self, files):
        """
        添加多个文件到GitHub仓库的一个commit中。
        :param files: 一个字典，包含文件路径和内容。
        """
        try:
            # 1. 获取最新的commit SHA
            commit_data = self.make_github_request('GET', f'/git/ref/heads/{self.branch}')
            commit_sha = commit_data['object']['sha']

            # 2. 获取最新commit的树的SHA
            commit = self.make_github_request('GET', f'/git/commits/{commit_sha}')
            tree_sha = commit['tree']['sha']

            # 3. 为新的文件创建blob
            blobs = []
            for file_path, content in files.items():
                blob_data = self.make_github_request('POST', '/git/blobs', {'content': content, 'encoding': 'utf-8'})
                blobs.append({'path': file_path, 'mode': '100644', 'type': 'blob', 'sha': blob_data['sha']})

            # 4. 创建一个新的树
            new_tree = self.make_github_request('POST', '/git/trees', {'base_tree': tree_sha, 'tree': blobs})

            # 5. 创建一个新的commit
            new_commit = self.make_github_request('POST', '/git/commits', {
                'parents': [commit_sha],
                'tree': new_tree['sha'],
                'message': 'Add multiple files'
            })

            # 6. 更新引用
            self.make_github_request('PATCH', f'/git/refs/heads/{self.branch}', {'sha': new_commit['sha']})

            print('Files added successfully.')

        except Exception as e:
            msg = f'An error occurred when add files to repo params: {files}, error: {e}'
            logger.error(msg)
            raise Exception(msg)


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


def summarize_content_by_zhipuai(prompt: str, api_key: str, model_name="chatglm_turbo", **kwargs):
    zhipuai.api_key = api_key
    response = zhipuai.model_api.invoke(model=model_name,
                                        prompt=[{"role": "user", "content": prompt}],
                                        temperature=0.95,
                                        top_p=0.7,
                                        return_type="text",
                                        **kwargs)
    return response


def summarize_content(prompt: str, model_name="gpt-4-1106-preview", **kwargs):
    client = openai.OpenAI(api_key=configInstance.openai_key, base_url=configInstance.openai_api_base)
    res = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": prompt}])
    return res


def test_add_files_to_repo():
    # 要添加的文件，以字典形式，键为文件路径，值为文件内容
    files_to_add = {
        'path/to/your/fisdffdsle1.txt': 'Contesdf nt of file1',
        'path/to/your/fil45e2.txt': 'Cont345ent of filefdgfdg2',
    }

    # 调用方法添加文件
    github_repo.add_files_to_repo(files_to_add)


def test_create_or_update_file():
    github_repo.create_or_update_file('te23sdfxt', 'te234st', 't6st')

def test_summarize_content_by_openai():
    prompt = "what is ojbk in Chinese"
    res = summarize_content_by_openai(prompt)
    print(res)

if __name__ == '__main__':
    test_summarize_content_by_openai()
    test_create_or_update_file()
    test_add_files_to_repo()

