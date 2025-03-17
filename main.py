# main.py 主逻辑：包括字段拼接、模拟请求
import re
import json
import time
import random
import logging
import hashlib
import requests
import urllib.parse
from push import push
from config import data, headers, cookies, READ_NUM, PUSH_METHOD

# 配置日志格式
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)-8s - %(message)s')

# 加密盐及其它默认值
KEY = "3c5c8717f3daf09iop3423zafeqoi"
COOKIE_DATA = {"rq": "%2Fweb%2Fbook%2Fread"}
READ_URL = "https://weread.qq.com/web/book/read"
RENEW_URL = "https://weread.qq.com/web/login/renewal"


def encode_data(data):
    """数据编码"""
    return '&'.join(f"{k}={urllib.parse.quote(str(data[k]), safe='')}" for k in sorted(data.keys()))


def cal_hash(input_string):
    """计算哈希值"""
    _7032f5 = 0x15051505
    _cc1055 = _7032f5
    length = len(input_string)
    _19094e = length - 1

    while _19094e > 0:
        _7032f5 = 0x7fffffff & (_7032f5 ^ ord(input_string[_19094e]) << (length - _19094e) % 30)
        _cc1055 = 0x7fffffff & (_cc1055 ^ ord(input_string[_19094e - 1]) << _19094e % 30)
        _19094e -= 2

    return hex(_7032f5 + _cc1055)[2:].lower()


def get_wr_skey():
    """刷新cookie密钥"""
    response = requests.post(RENEW_URL, headers=headers, cookies=cookies,
                             data=json.dumps(COOKIE_DATA, separators=(',', ':')))
    for cookie in response.headers.get('Set-Cookie', '').split(';'):
        if "wr_skey" in cookie:
            return cookie.split('=')[-1][:8]
    return None


def simulate_page_turn(current_progress):
    """模拟翻页，更新阅读进度参数"""
    # 随机增加阅读进度（1-3个百分点）
    progress_increment = random.randint(1, 3)
    new_progress = min(current_progress + progress_increment, 100)
    
    # 更新data中的进度相关参数
    data['pr'] = new_progress
    
    # 更新页面位置参数（ps和pc通常是页面位置的标识）
    # 这里使用简单的随机字符串模拟新的页面位置
    page_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:20]
    data['ps'] = f"b1d32a307a4c3259g{page_id[:6]}"
    data['pc'] = f"080327b07a4c3259g{page_id[6:12]}"
    
    # 更新章节位置（如果需要）
    if new_progress > 90 and data['ci'] < 100:
        data['ci'] += 1
    
    logging.info(f"📖 模拟翻页，阅读进度更新为: {new_progress}%")
    return new_progress


index = 1
current_progress = data['pr']  # 初始阅读进度
while index <= READ_NUM:
    data['ct'] = int(time.time())
    data['ts'] = int(time.time() * 1000)
    data['rn'] = random.randint(0, 1000)
    data['sg'] = hashlib.sha256(f"{data['ts']}{data['rn']}{KEY}".encode()).hexdigest()
    data['s'] = cal_hash(encode_data(data))

    logging.info(f"⏱️ 尝试第 {index} 次阅读...")
    response = requests.post(READ_URL, headers=headers, cookies=cookies, data=json.dumps(data, separators=(',', ':')))
    resData = response.json()

    if 'succ' in resData:
        index += 1
        
        # 随机决定是否翻页
        if random.random() < 0.7:  # 70%的概率翻页
            current_progress = simulate_page_turn(current_progress)
        
        # 随机等待时间（20-40秒）
        wait_time = random.randint(20, 40)
        logging.info(f"✅ 阅读成功，等待 {wait_time} 秒后继续...")
        time.sleep(wait_time)
        logging.info(f"📊 阅读进度：{(index - 1) * 0.5} 分钟")

    else:
        logging.warning("❌ cookie 已过期，尝试刷新...")
        new_skey = get_wr_skey()
        if new_skey:
            cookies['wr_skey'] = new_skey
            logging.info(f"✅ 密钥刷新成功，新密钥：{new_skey}")
            logging.info(f"🔄 重新本次阅读。")
        else:
            ERROR_CODE = "❌ 无法获取新密钥或者WXREAD_CURL_BASH配置有误，终止运行。"
            logging.error(ERROR_CODE)
            push(ERROR_CODE, PUSH_METHOD)
            raise Exception(ERROR_CODE)
    data.pop('s')

logging.info("🎉 阅读脚本已完成！")

if PUSH_METHOD not in (None, ''):
    logging.info("⏱️ 开始推送...")
    push(f"🎉 微信读书自动阅读完成！\n⏱️ 阅读时长：{(index - 1) * 0.5}分钟。\n📖 最终阅读进度：{current_progress}%", PUSH_METHOD)
