import os

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from telethon.sync import TelegramClient

app = FastAPI()

api_id = int(os.getenv('TELEGRAM_API_ID', ''))
api_hash = os.getenv('TELEGRAM_API_HASH', '')
phone = os.getenv('TELEGRAM_PHONE', '')
session_name = os.getenv('TELEGRAM_SESSION_NAME', 'self_backup')

# client = TelegramClient(session_name, api_id, api_hash)


header_token = os.getenv('TOKEN', None)


class Message(BaseModel):
    to: str
    message: str


def get_bearer_token(authorization: str = Header(None)):
    parts = []
    token = None
    if authorization is not None:
        parts = authorization.split()
        if len(parts) == 2 or parts[0].lower() == 'bearer':
            token = parts[1]

    return token


def verify_bearer_token(token: str = Depends(get_bearer_token)):
    # 在这个函数中，您可以验证Bearer令牌是否有效，以及用户是否已经授权。
    # 如果令牌有效并用户已经授权，可以返回用户信息或继续执行。
    # 否则，您可以引发HTTP异常来拒绝请求。
    if header_token is None or token == header_token:
        return True
    else:
        raise HTTPException(status_code=401, detail="Invalid authorization")


@app.post("/send_message")
async def send_message(message: Message, authorized: bool = Depends(verify_bearer_token)):
    try:
        async with TelegramClient(session_name, api_id, api_hash) as client:
            if not await client.is_user_authorized():
                await client.send_code_request(phone)
                await client.sign_in(phone, input('Enter the code: '))
            await client.send_message(message.to, message.message)
        return {'message': 'success'}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
