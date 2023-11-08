# Telegram 文章备份与总结机器人


个人自用的 Telegram 机器人，主要功能是对文章进行备份和总结。不再需要手动复制和粘贴文章内容，只需向机器人发送文章链接，它就会为您完成备份和总结的工作。

## 功能特点

- **备份文章**: 使用 `/backup <url>` 命令，将指定 URL 中的文章内容备份到您的 GitHub 仓库和 Wayback Machine。这样就可以通过 GitHub 或者 Wayback 的 url 随时查看和检索保存的文章，防止原文丢失。
- **文章总结**: 使用 `/summarize <url>` 命令，机器人会调用 AI 技术，为您生成文章的简明摘要，使您能够迅速了解文章的要点，节省时间。
- **Telegram Http**: 使用 http 向 telegram 好友/群组/bot 发送消息