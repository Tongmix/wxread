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
    try:
        # 添加随机延迟，避免请求过于频繁
        time.sleep(random.uniform(1.5, 3.5))
        response = requests.post(RENEW_URL, headers=headers, cookies=cookies,
                                data=json.dumps(COOKIE_DATA, separators=(',', ':')))
        
        if response.status_code != 200:
            logging.warning(f"刷新密钥请求失败，状态码: {response.status_code}")
            return None
            
        for cookie in response.headers.get('Set-Cookie', '').split(';'):
            if "wr_skey" in cookie:
                return cookie.split('=')[-1][:8]
        
        logging.warning("响应中未找到wr_skey")
        return None
    except Exception as e:
        logging.error(f"刷新密钥时发生错误: {str(e)}")
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
    page_id = hashlib.md5(str(time.time() + random.random()).encode()).hexdigest()[:20]
    data['ps'] = f"b1d32a307a4c3259g{page_id[:6]}"
    data['pc'] = f"080327b07a4c3259g{page_id[6:12]}"
    
    # 更新章节位置（如果需要）
    if new_progress > 90 and data['ci'] < 100:
        data['ci'] += 1
    
    # 随机更新sm参数（模拟不同的阅读内容）
    reading_contents = [
        "[插图]第三部广播纪元7年，程心艾AA说",
        "三体舰队即将抵达，人类文明面临最大危机",
        "面壁者计划失败后，人类开始寻找新的出路",
        "黑暗森林法则揭示了宇宙文明的生存法则",
        "智子监控下，人类科技发展受到极大限制"
    ]
    data['sm'] = random.choice(reading_contents)
    
    logging.info(f"📖 模拟翻页，阅读进度更新为: {new_progress}%")
    return new_progress


# 添加指数退避重试机制
def exponential_backoff(attempt):
    """指数退避算法，随着尝试次数增加等待时间"""
    wait_time = min(30, (2 ** attempt)) + random.uniform(0, 1)
    return wait_time


index = 1
current_progress = data['pr']  # 初始阅读进度
retry_count = 0
max_retries = 5

while index <= READ_NUM:
    try:
        # 添加随机延迟，使请求看起来更自然
        time.sleep(random.uniform(0.5, 1.5))
        
        data['ct'] = int(time.time())
        data['ts'] = int(time.time() * 1000)
        data['rn'] = random.randint(0, 1000)
        data['sg'] = hashlib.sha256(f"{data['ts']}{data['rn']}{KEY}".encode()).hexdigest()
        data['s'] = cal_hash(encode_data(data))

        logging.info(f"⏱️ 尝试第 {index} 次阅读...")
        
        # 随机化User-Agent，避免被识别为机器人
        if random.random() < 0.3:  # 30%的概率更换User-Agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
            ]
            headers['user-agent'] = random.choice(user_agents)
        
        response = requests.post(READ_URL, headers=headers, cookies=cookies, data=json.dumps(data, separators=(',', ':')))
        
        # 检查HTTP状态码
        if response.status_code != 200:
            logging.warning(f"HTTP请求失败，状态码: {response.status_code}")
            wait_time = exponential_backoff(retry_count)
            logging.info(f"等待 {wait_time:.2f} 秒后重试...")
            time.sleep(wait_time)
            retry_count += 1
            continue
            
        resData = response.json()

        if 'succ' in resData:
            index += 1
            retry_count = 0  # 重置重试计数
            
            # 随机决定是否翻页
            if random.random() < 0.7:  # 70%的概率翻页
                current_progress = simulate_page_turn(current_progress)
            
            # 随机等待时间（25-60秒），更接近真实阅读
            wait_time = random.randint(25, 60)
            logging.info(f"✅ 阅读成功，等待 {wait_time} 秒后继续...")
            time.sleep(wait_time)
            logging.info(f"📊 阅读进度：{(index - 1) * 0.5} 分钟")

        else:
            logging.warning("❌ cookie 已过期，尝试刷新...")
            # 在重试前等待一段时间
            time.sleep(random.uniform(2, 5))
            new_skey = get_wr_skey()
            if new_skey:
                cookies['wr_skey'] = new_skey
                logging.info(f"✅ 密钥刷新成功，新密钥：{new_skey}")
                logging.info(f"🔄 重新本次阅读。")
                # 刷新成功后额外等待，避免立即请求
                time.sleep(random.uniform(3, 7))
            else:
                retry_count += 1
                if retry_count >= max_retries:
                    ERROR_CODE = f"❌ 尝试 {max_retries} 次后仍无法获取新密钥，终止运行。"
                    logging.error(ERROR_CODE)
                    push(ERROR_CODE, PUSH_METHOD)
                    raise Exception(ERROR_CODE)
                
                wait_time = exponential_backoff(retry_count)
                logging.warning(f"⚠️ 无法获取新密钥，第 {retry_count} 次重试，等待 {wait_time:.2f} 秒...")
                time.sleep(wait_time)
    except requests.exceptions.RequestException as e:
        logging.error(f"网络请求错误: {str(e)}")
        retry_count += 1
        if retry_count >= max_retries:
            ERROR_CODE = f"❌ 网络请求失败 {max_retries} 次，终止运行。"
            logging.error(ERROR_CODE)
            push(ERROR_CODE, PUSH_METHOD)
            raise Exception(ERROR_CODE)
        
        wait_time = exponential_backoff(retry_count)
        logging.warning(f"⚠️ 网络错误，第 {retry_count} 次重试，等待 {wait_time:.2f} 秒...")
        time.sleep(wait_time)
    
    data.pop('s', None)  # 安全移除's'键

logging.info("🎉 阅读脚本已完成！")

if PUSH_METHOD not in (None, ''):
    logging.info("⏱️ 开始推送...")
    push(f"🎉 微信读书自动阅读完成！\n⏱️ 阅读时长：{(index - 1) * 0.5}分钟。\n📖 最终阅读进度：{current_progress}%", PUSH_METHOD)
