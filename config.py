# config.py - 配置文件
# 包含脚本运行所需的所有配置参数，包括阅读次数、推送方式和认证信息

import os
import re
import random

"""
可修改区域
默认使用本地值如果不存在从环境变量中获取值
"""

# 阅读时间 默认60分钟
READ_TIME = int(os.getenv('READ_TIME') or 60)
# 单次阅读时间的波动范围(秒)，默认在20-40秒之间波动
READ_MIN_INTERVAL = int(os.getenv('READ_MIN_INTERVAL') or 20)
READ_MAX_INTERVAL = int(os.getenv('READ_MAX_INTERVAL') or 40)

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
    'RK': 'oxEY1bTnXf',
    'ptcz': '53e3b35a9486dd63c4d06430b05aa169402117fc407dc5cc9329b41e59f62e2b',
    'pac_uid': '0_e63870bcecc18',
    'iip': '0',
    '_qimei_uuid42': '183070d3135100ee797b08bc922054dc3062834291',
    'wr_avatar': 'https%3A%2F%2Fthirdwx.qlogo.cn%2Fmmopen%2Fvi_32%2FeEOpSbFh2Mb1bUxMW9Y3FRPfXwWvOLaNlsjWIkcKeeNg6vlVS5kOVuhNKGQ1M8zaggLqMPmpE5qIUdqEXlQgYg%2F132',
    'wr_gender': '0',
}

# 默认headers配置 - 本地或Docker部署时需要替换为自己的headers
# 这些是示例值，实际使用时需要替换
headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,ko;q=0.5',
    'baggage': 'sentry-environment=production,sentry-release=dev-1738835404736,sentry-public_key=ed67ed71f7804a038e898ba54bd66e44,sentry-trace_id=6d183eca3c3c4e04bfbd5dab522765b9',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
}


"""
建议保留区域 - 默认读三体，其它书籍自行测试时间是否增加
这部分包含请求数据的默认值，修改可能影响阅读记录
"""

def get_data():
    """
    根据30%的几率返回备用的请求数据，从多个备用数据中随机选择一组，
    否则返回默认数据
    :return: 请求数据字典
    """
    default_data = {
    'appId': 'wb182564874663h776775553',
    'b': 'a57325c05c8ed3a57224187',
    'c': 'c9f326d018c9f0f895fb5e4',
    'ci': 8,
    'co': 338,
    'sm': '第6章储蓄资本朱元璋的第一桶金朱元璋又来',
    'pr': 0,
    'rt': 26,
    'ts': 1742300288310,
    'rn': 233,
    'sg': 'e4ec08574928fd62a4acb099a9f27bc548eff34e6e08c46869d80394b7690ab5',
    'ct': 1742300288,
    'ps': '98f32cb07a628a09g018409',
    'pc': 'eee324f07a628a0ag011bd9',
    }
    alternate_data_list = [
        {
    "appId": "wb182564874663h152492176",
    "b": "ce032b305a9bc1ce0b0dd2a",
    "c": "7cb321502467cbbc409e62d",
    "ci": 70,
    "co": 0,
    "sm": "[插图]第三部广播纪元7年，程心艾AA说",
    "pr": 74,
    "rt": 30,
    "ts": 1727660516749,
    "rn": 31,
    "sg": "991118cc229871a5442993ecb08b5d2844d7f001dbad9a9bc7b2ecf73dc8db7e",
    "ct": 1727660516,
    "ps": "b1d32a307a4c3259g016b67",
    "pc": "080327b07a4c3259g018787",
        },
        # 可以添加更多备用数据组
    ]
        # 以30%的几率返回备用数据中的随机一组
    if random.random() < 0.1:
        return random.choice(alternate_data_list)
    return default_data
    
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

"""
生成随机阅读时间序列的函数
"""
def generate_reading_intervals(total_minutes, min_seconds=20, max_seconds=40):
    """
    根据总阅读时间生成随机的阅读时间序列
    
    Args:
        total_minutes (int): 总阅读时间(分钟)
        min_seconds (int): 最小阅读间隔(秒)
        max_seconds (int): 最大阅读间隔(秒)
        
    Returns:
        list: 阅读时间间隔列表(秒)
    """
    
    if total_minutes <= 0:
        return [30] * 120  # 如果时间无效，返回默认值
        
    total_seconds = total_minutes * 60
    intervals = []
    
    # 生成随机间隔，直到总时间接近目标时间
    current_total = 0
    while current_total < total_seconds:
        # 如果剩余时间不足最小间隔，就用剩余时间作为最后一个间隔
        remaining = total_seconds - current_total
        if remaining < min_seconds:
            if remaining > 5:  # 如果剩余时间太少但还有意义，添加最后一个间隔
                intervals.append(remaining)
            break
            
        # 生成随机间隔，但确保不会超过总时间
        interval = min(random.randint(min_seconds, max_seconds), remaining)
        intervals.append(interval)
        current_total += interval
    
    return intervals

# 根据总时间生成阅读间隔序列
reading_intervals = generate_reading_intervals(
    READ_TIME, 
    READ_MIN_INTERVAL, 
    READ_MAX_INTERVAL
)

# 如果没有生成有效的间隔序列，添加一个默认间隔
if not reading_intervals:
    logging.warning("警告：未能生成有效的阅读间隔序列，使用默认值")
    reading_intervals = [30] * 120  # 默认120次，每次30秒
