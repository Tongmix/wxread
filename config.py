# config.py - 配置文件
# 包含脚本运行所需的所有配置参数，包括阅读次数、推送方式和认证信息

import os
import re

"""
可修改区域
默认使用本地值，如果本地值不存在则从环境变量中获取值
"""

# 阅读次数设置 - 每次计为30秒，默认120次相当于60分钟
# 可通过环境变量READ_NUM覆盖
READ_NUM = int(os.getenv('READ_NUM') or 120)

# 推送通知方式 - 支持pushplus、wxpusher、telegram三种方式
# 留空表示不推送通知
PUSH_METHOD = "" or os.getenv('PUSH_METHOD')

# PushPlus推送服务配置 - 当PUSH_METHOD为"pushplus"时使用
# 需要在 https://www.pushplus.plus 获取token
PUSHPLUS_TOKEN = "" or os.getenv("PUSHPLUS_TOKEN")

# Telegram推送服务配置 - 当PUSH_METHOD为"telegram"时使用
# 需要创建Telegram机器人并获取token和聊天ID
TELEGRAM_BOT_TOKEN = "" or os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "" or os.getenv("TELEGRAM_CHAT_ID")

# WxPusher推送服务配置 - 当PUSH_METHOD为"wxpusher"时使用
# 需要在 https://wxpusher.zjiecode.com 获取SPT
WXPUSHER_SPT = "" or os.getenv("WXPUSHER_SPT")

# 从环境变量获取curl命令字符串 - 用于提取headers和cookies
# 在GitHub Actions中使用，本地部署时可忽略
curl_str = os.getenv('WXREAD_CURL_BASH')

# 默认cookies配置 - 本地或Docker部署时需要替换为自己的cookies
# 这些是示例值，实际使用时需要替换
cookies = {
    'RK': 'xzsh0fMOVJ',
    'ptcz': '626491ceda7231fb30fe8ec33d45412f8c7ff2c43debfe9f9b751367454ba191',
    'pac_uid': '0_e63870bcecc18',
    'iip': '0',
    '_qimei_uuid42': '191150d120510054c6141a3309bda049b26a822f6d',
    'wr_avatar': 'https%3A%2F%2Fthirdwx.qlogo.cn%2Fmmopen%2Fvi_32%2FPiajxSqBRaEIbibQ84hicAvZ2gZXpCCc41wxM1ZnSe0yUB9VxPSpeG1DZtkacPZYnxE0N2O67czsS1bwPmkDPVbQjCfkSYWrdQ2Ru1w7JmSW1TnPQNzsQiaBbQ%2F132',
    'wr_gender': '0',
}

# 默认headers配置 - 本地或Docker部署时需要替换为自己的headers
# 这些是示例值，实际使用时需要替换
headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,ko;q=0.5',
    'baggage': 'sentry-environment=production,sentry-release=dev-1730698697208,sentry-public_key=ed67ed71f7804a038e898ba54bd66e44,sentry-trace_id=1ff5a0725f8841088b42f97109c45862',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
}


"""
建议保留区域 - 默认读三体，其它书籍自行测试时间是否增加
这部分包含请求数据的默认值，修改可能影响阅读记录
"""
# 请求数据 - 包含书籍信息、阅读位置等参数
data = {
    "appId": "wb182564874663h776775553",  # 应用ID
    "b": "612327107189997b612511d",       # 书籍ID
    "c": "1c3321802231c383cd30bb3",       # 内容ID
    "ci": 35,                             # 章节索引
    "co": 419,                            # 内容位置
    "sm": "5.9　移位和循环指令TIA博途软件移位",  # 当前阅读内容摘要
    "pr": 99,                             # 页码或段落索引
    "rt": 14,                             # 阅读时长或进度
    "ts": 1742110495206,                  # 时间戳(毫秒)
    "rn": 604,                            # 随机数
    "sg": "7fd6df8f2262dcb802731aa432ac230f3c099bf8cb2abbd03a3d3e234c4a2722",  # 安全签名
    "ct": 1742110495,                     # 时间戳(秒)
    "ps": "272326e07a623fe7g018361",      # 用户标识符
    "pc": "6bd322007a623fe8g01005f",      # 设备标识符
}


def convert(curl_command):
    """从curl命令中提取headers和cookies
    
    Args:
        curl_command (str): curl命令字符串
        
    Returns:
        tuple: (headers字典, cookies字典)
        
    支持两种方式的cookie提取:
    1. -H 'Cookie: xxx' 形式
    2. -b 'xxx' 形式
    """
    # 提取 headers
    headers_temp = {}
    for match in re.findall(r"-H '([^:]+): ([^']+)'", curl_command):
        headers_temp[match[0]] = match[1]

    # 提取 cookies
    cookies = {}
    
    # 从 -H 'Cookie: xxx' 提取
    cookie_header = next((v for k, v in headers_temp.items() 
                         if k.lower() == 'cookie'), '')
    
    # 从 -b 'xxx' 提取
    cookie_b = re.search(r"-b '([^']+)'", curl_command)
    cookie_string = cookie_b.group(1) if cookie_b else cookie_header
    
    # 解析 cookie 字符串
    if cookie_string:
        for cookie in cookie_string.split('; '):
            if '=' in cookie:
                key, value = cookie.split('=', 1)
                cookies[key.strip()] = value.strip()
    
    # 移除 headers 中的 Cookie/cookie
    headers = {k: v for k, v in headers_temp.items() 
              if k.lower() != 'cookie'}

    return headers, cookies

# 如果环境变量中有curl命令，则使用它提取headers和cookies
# 否则使用上面定义的默认值
headers, cookies = convert(curl_str) if curl_str else (headers, cookies)
