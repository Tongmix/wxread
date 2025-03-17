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

# 保存初始数据，用于重置
INITIAL_DATA = data.copy()
INITIAL_COOKIES = cookies.copy()


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
        
        # 修改请求头，模拟不同的浏览器行为
        temp_headers = headers.copy()
        temp_headers['user-agent'] = random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ])
        
        # 添加随机参数，避免缓存
        renewal_data = COOKIE_DATA.copy()
        renewal_data["_t"] = int(time.time() * 1000)
        renewal_data["_r"] = random.randint(1000, 9999)
        
        logging.info("尝试刷新密钥...")
        response = requests.post(RENEW_URL, headers=temp_headers, cookies=cookies,
                                data=json.dumps(renewal_data, separators=(',', ':')))
        
        if response.status_code != 200:
            logging.warning(f"刷新密钥请求失败，状态码: {response.status_code}")
            return None
        
        # 提取所有cookie
        new_cookies = {}
        for cookie in response.headers.get('Set-Cookie', '').split(','):
            for item in cookie.split(';'):
                if '=' in item and not item.strip().startswith(' '):
                    key, value = item.strip().split('=', 1)
                    new_cookies[key] = value
        
        logging.info("已获取新cookie")
        
        # 更新所有相关cookie
        if new_cookies:
            for key, value in new_cookies.items():
                if key in cookies:
                    cookies[key] = value
            
            # 特别检查wr_skey
            if 'wr_skey' in new_cookies:
                logging.info("成功获取wr_skey")
                return new_cookies['wr_skey']
        
        # 尝试从响应体中获取信息
        try:
            resp_data = response.json()
            if 'errcode' in resp_data:
                logging.warning(f"密钥刷新失败，错误码: {resp_data.get('errcode')}")
        except:
            logging.warning("无法解析响应内容为JSON")
        
        logging.warning("响应中未找到有效的wr_skey")
        return None
    except Exception as e:
        logging.error(f"刷新密钥时发生错误: {str(e)}")
        return None


def reset_session():
    """完全重置会话，创建新的请求会话"""
    try:
        logging.info("尝试完全重置会话...")
        
        # 创建新的会话对象
        session = requests.Session()
        
        # 设置随机User-Agent
        session.headers.update({
            'user-agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
            ]),
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'content-type': 'application/json;charset=UTF-8',
            'origin': 'https://weread.qq.com',
            'referer': 'https://weread.qq.com/'
        })
        
        # 设置现有的cookies
        for key, value in cookies.items():
            session.cookies.set(key, value)
        
        # 尝试访问主页，获取新的cookies
        try:
            home_resp = session.get('https://weread.qq.com/', timeout=10)
            logging.info(f"主页访问状态码: {home_resp.status_code}")
        except Exception as e:
            logging.warning(f"访问主页时出错: {str(e)}")
        
        # 尝试刷新密钥
        renewal_data = COOKIE_DATA.copy()
        renewal_data["_t"] = int(time.time() * 1000)
        
        renew_resp = session.post(RENEW_URL, 
                                 json=renewal_data,
                                 timeout=10)
        
        logging.info(f"会话重置响应状态码: {renew_resp.status_code}")
        
        # 更新cookies
        new_cookies = dict(session.cookies)
        logging.info("已获取新会话cookies")
        
        # 更新全局cookies
        for key, value in new_cookies.items():
            cookies[key] = value
        
        return True
    except Exception as e:
        logging.error(f"重置会话时发生错误: {str(e)}")
        return False


def reset_to_initial_state():
    """重置数据到初始状态"""
    global data
    logging.info("重置数据到初始状态")
    
    # 保留当前时间戳和随机数
    current_time = int(time.time())
    current_time_ms = int(time.time() * 1000)
    random_num = random.randint(0, 1000)
    
    # 重置数据
    data = INITIAL_DATA.copy()
    
    # 更新时间戳和随机数
    data['ct'] = current_time
    data['ts'] = current_time_ms
    data['rn'] = random_num
    
    return data


def exponential_backoff(attempt):
    """指数退避算法，随着尝试次数增加等待时间"""
    wait_time = min(30, (2 ** attempt)) + random.uniform(0, 1)
    return wait_time


def refresh_cookies():
    """刷新所有cookie并确保会话有效"""
    logging.info("🔄 开始刷新会话...")
    
    # 先尝试刷新密钥（更简单的方法）
    logging.info("尝试刷新密钥...")
    new_skey = get_wr_skey()
    if new_skey:
        cookies['wr_skey'] = new_skey
        logging.info("✅ 密钥刷新成功")
        time.sleep(random.uniform(2, 4))
        return True
    
    # 如果刷新密钥失败，再尝试重置会话（更复杂的方法）
    logging.info("密钥刷新失败，尝试重置会话...")
    if reset_session():
        logging.info("✅ 会话重置成功")
        time.sleep(random.uniform(2, 4))
        return True
    
    logging.warning("❌ 无法刷新会话或密钥")
    return False


def check_cookie_valid():
    """检查当前cookie是否有效"""
    logging.info("🔍 检查当前cookie是否有效...")
    
    try:
        # 构建一个简单的请求来验证cookie
        temp_data = {
            "appId": data["appId"],
            "b": data["b"],
            "ct": int(time.time()),
            "ts": int(time.time() * 1000),
            "rn": random.randint(0, 1000)
        }
        
        # 计算签名
        temp_data['sg'] = hashlib.sha256(f"{temp_data['ts']}{temp_data['rn']}{KEY}".encode()).hexdigest()
        temp_data['s'] = cal_hash(encode_data(temp_data))
        
        # 使用随机User-Agent
        temp_headers = headers.copy()
        temp_headers['user-agent'] = random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ])
        
        # 发送请求
        response = requests.post(READ_URL, headers=temp_headers, cookies=cookies, 
                               data=json.dumps(temp_data, separators=(',', ':')),
                               timeout=10)
        
        # 检查响应
        if response.status_code == 200:
            resp_data = response.json()
            if 'succ' in resp_data:
                logging.info("✅ 当前cookie有效，无需刷新")
                return True
            else:
                logging.info("❌ 当前cookie已失效")
                return False
        else:
            logging.warning(f"❌ 验证cookie请求失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"验证cookie时发生错误: {str(e)}")
        return False


# 主循环
index = 1
retry_count = 0
max_retries = 5
consecutive_failures = 0
max_consecutive_failures = 3

# 脚本开始
logging.info("🚀 开始执行阅读脚本...")

# 先检查cookie是否有效，只有在无效时才刷新
if check_cookie_valid():
    logging.info("🔑 当前cookie有效，直接开始阅读")
    cookie_refresh_success = True
else:
    logging.info("🔑 当前cookie已失效，尝试刷新...")
    
    # 尝试刷新cookie，如果失败则重试
    cookie_refresh_success = False
    for i in range(3):  # 最多尝试3次
        if refresh_cookies():
            cookie_refresh_success = True
            logging.info("✅ Cookie刷新成功，准备开始阅读")
            break
        else:
            logging.warning(f"⚠️ 第{i+1}次Cookie刷新失败，等待后重试...")
            time.sleep(exponential_backoff(i))
            
            # 第二次尝试前，先重置到初始状态
            if i == 1:
                logging.info("尝试重置数据到初始状态后再刷新...")
                reset_to_initial_state()
                # 重置cookies
                for key, value in INITIAL_COOKIES.items():
                    cookies[key] = value

if not cookie_refresh_success:
    ERROR_CODE = "❌ 无法刷新Cookie，请检查配置或稍后再试"
    logging.error(ERROR_CODE)
    push(ERROR_CODE, PUSH_METHOD)
    raise Exception(ERROR_CODE)

# 等待一段时间再开始阅读
time.sleep(random.uniform(3, 6))

while index <= READ_NUM:
    try:
        # 添加随机延迟，使请求看起来更自然
        time.sleep(random.uniform(0.5, 1.5))
        
        # 更新时间戳和随机数
        data['ct'] = int(time.time())
        data['ts'] = int(time.time() * 1000)
        data['rn'] = random.randint(0, 1000)
        
        # 计算签名
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
            consecutive_failures += 1
            continue
            
        resData = response.json()

        if 'succ' in resData:
            index += 1
            retry_count = 0  # 重置重试计数
            consecutive_failures = 0  # 重置连续失败计数
            
            # 随机等待时间（25-45秒），模拟阅读
            wait_time = random.randint(25, 45)
            logging.info(f"✅ 阅读成功，等待 {wait_time} 秒后继续...")
            time.sleep(wait_time)
            logging.info(f"📊 阅读进度：{(index - 1) * 0.5} 分钟")
            
            # 每隔一定次数主动刷新cookie，避免过期
            if index % 8 == 0:
                logging.info("🔄 定期刷新cookie...")
                refresh_cookies()
                time.sleep(random.uniform(2, 5))

        else:
            logging.warning("❌ cookie 已过期")
            consecutive_failures += 1
            
            # 如果连续失败次数过多，重置到初始状态
            if consecutive_failures >= max_consecutive_failures:
                logging.warning(f"⚠️ 连续失败 {consecutive_failures} 次，尝试重置到初始状态")
                reset_to_initial_state()
                consecutive_failures = 0
            
            # 在重试前等待一段时间
            time.sleep(random.uniform(2, 5))
            
            # 刷新cookie
            if refresh_cookies():
                logging.info("✅ Cookie刷新成功，继续阅读")
                time.sleep(random.uniform(3, 7))
                continue
            else:
                retry_count += 1
                if retry_count >= max_retries:
                    ERROR_CODE = f"❌ 尝试 {max_retries} 次后仍无法获取新密钥，终止运行。"
                    logging.error(ERROR_CODE)
                    push(ERROR_CODE, PUSH_METHOD)
                    raise Exception(ERROR_CODE)
                
                wait_time = exponential_backoff(retry_count)
                logging.warning(f"⚠️ 无法刷新Cookie，第 {retry_count} 次重试，等待 {wait_time:.2f} 秒...")
                time.sleep(wait_time)
    except requests.exceptions.RequestException as e:
        logging.error(f"网络请求错误: {str(e)}")
        retry_count += 1
        consecutive_failures += 1
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
    push(f"🎉 微信读书自动阅读完成！\n⏱️ 阅读时长：{(index - 1) * 0.5}分钟。", PUSH_METHOD)
