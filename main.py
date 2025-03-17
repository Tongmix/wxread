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
        
        # 打印完整的响应头，用于调试
        logging.info(f"密钥刷新响应头: {dict(response.headers)}")
        
        # 提取所有cookie
        new_cookies = {}
        for cookie in response.headers.get('Set-Cookie', '').split(','):
            for item in cookie.split(';'):
                if '=' in item and not item.strip().startswith(' '):
                    key, value = item.strip().split('=', 1)
                    new_cookies[key] = value
        
        logging.info(f"获取到的新cookie: {new_cookies}")
        
        # 更新所有相关cookie
        if new_cookies:
            for key, value in new_cookies.items():
                if key in cookies:
                    cookies[key] = value
                    logging.info(f"更新cookie: {key}={value}")
            
            # 特别检查wr_skey
            if 'wr_skey' in new_cookies:
                return new_cookies['wr_skey']
        
        # 尝试从响应体中获取信息
        try:
            resp_data = response.json()
            logging.info(f"密钥刷新响应内容: {resp_data}")
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
        logging.info(f"新会话cookies: {new_cookies}")
        
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
    
    # 先尝试重置会话
    if reset_session():
        logging.info("✅ 会话重置成功")
        time.sleep(random.uniform(2, 4))
        return True
    
    # 如果重置失败，尝试刷新密钥
    logging.info("会话重置失败，尝试刷新密钥...")
    new_skey = get_wr_skey()
    if new_skey:
        cookies['wr_skey'] = new_skey
        logging.info(f"✅ 密钥刷新成功，新密钥：{new_skey}")
        time.sleep(random.uniform(2, 4))
        return True
    
    logging.warning("❌ 无法刷新会话或密钥")
    return False


def simulate_page_turn(current_progress):
    """模拟翻页，更新阅读进度参数"""
    # 保存原始数据，以便在失败时回退
    original_data = data.copy()
    
    # 更自然的进度增量（0.5-1.5个百分点）
    progress_increment = random.uniform(0.5, 1.5)
    new_progress = min(round(current_progress + progress_increment, 1), 100)
    
    # 更新data中的进度相关参数
    data['pr'] = new_progress
    
    # 更新阅读时间参数 - 重要：每次翻页都需要更新时间戳
    data['ct'] = int(time.time())
    data['ts'] = int(time.time() * 1000)
    data['rn'] = random.randint(0, 1000)
    
    # 更新页面位置参数（ps和pc通常是页面位置的标识）
    # 使用更真实的页面ID生成方式
    base_id = "b1d32a307a4c3259g"
    page_num = int(new_progress * 100)  # 基于进度计算页码
    page_id = f"{base_id}{page_num:06d}"
    
    # 确保ps和pc值有细微差异但保持一定关联
    data['ps'] = f"{page_id[:15]}{random.randint(100, 999)}"
    data['pc'] = f"{page_id[:12]}{random.randint(1000, 9999)}"
    
    # 更新章节位置（如果需要）- 更自然的章节变化
    if new_progress > data.get('_last_chapter_change', 0) + 10:  # 每增加10%进度更新一次章节
        data['ci'] = min(data['ci'] + 1, 100)
        data['_last_chapter_change'] = new_progress
    
    # 更新阅读内容 - 基于进度选择不同的内容
    reading_contents = [
        "[插图]第三部广播纪元7年，程心艾AA说",
        "三体舰队即将抵达，人类文明面临最大危机",
        "面壁者计划失败后，人类开始寻找新的出路",
        "黑暗森林法则揭示了宇宙文明的生存法则",
        "智子监控下，人类科技发展受到极大限制"
    ]
    # 根据进度选择内容，使内容变化更连贯
    content_index = min(int(new_progress / 20), len(reading_contents) - 1)
    data['sm'] = reading_contents[content_index]
    
    # 更新阅读时长参数 - rt应该随着阅读进度增加
    # 假设每页阅读30秒
    data['rt'] = min(30 + int(new_progress / 5), 60)
    
    logging.info(f"📖 模拟翻页，阅读进度更新为: {new_progress}%")
    return new_progress, original_data


# 主循环
index = 1
current_progress = data['pr']  # 初始阅读进度
retry_count = 0
max_retries = 5
consecutive_failures = 0
max_consecutive_failures = 3
page_turn_count = 0  # 翻页计数
last_page_turn_index = 0  # 上次翻页的索引
original_data = None  # 用于存储翻页前的原始数据

# 在开始阅读前先刷新cookie
logging.info("🚀 开始执行阅读脚本...")
logging.info("🔑 在开始阅读前先刷新cookie")

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
        
        # 记录请求参数，便于调试
        if index % 5 == 0:  # 每5次记录一次请求参数
            logging.info(f"请求参数: {json.dumps({k: data[k] for k in data if not k.startswith('_')})}")
        
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
            
            # 检查是否刚刚翻页，如果是则立即刷新cookie
            if index - last_page_turn_index == 1 and page_turn_count > 0:
                logging.info("🔄 翻页后立即刷新cookie...")
                refresh_cookies()
                time.sleep(random.uniform(2, 4))
            
            # 更自然的翻页模式
            # 前几次阅读不翻页，让系统认为用户在阅读当前页面
            if index <= 5:
                logging.info("📚 初始阅读阶段，不翻页...")
                wait_time = random.randint(30, 45)  # 初始阅读时间稍长
            else:
                # 随机决定是否翻页，概率随着阅读次数增加而增加，但保持较低概率
                # 每10次阅读最多翻1-2页
                if page_turn_count < (index // 10) and random.random() < 0.15:  # 15%的概率翻页
                    # 在翻页前先等待一段时间，模拟阅读当前页面
                    pre_turn_wait = random.randint(20, 30)
                    logging.info(f"📖 阅读当前页面 {pre_turn_wait} 秒...")
                    time.sleep(pre_turn_wait)
                    
                    # 翻页
                    current_progress, original_data = simulate_page_turn(current_progress)
                    page_turn_count += 1
                    last_page_turn_index = index
                    
                    # 翻页后短暂等待，模拟页面加载时间
                    time.sleep(random.uniform(1.0, 2.5))
                    
                    # 翻页后立即刷新cookie
                    logging.info("🔄 翻页后立即刷新cookie...")
                    refresh_cookies()
                    time.sleep(random.uniform(2, 4))
                else:
                    logging.info("📚 继续阅读当前页面，不翻页")
                
                # 阅读等待时间
                wait_time = random.randint(25, 40)
            
            logging.info(f"✅ 阅读成功，等待 {wait_time} 秒后继续...")
            time.sleep(wait_time)
            logging.info(f"📊 阅读进度：{(index - 1) * 0.5} 分钟")
            
            # 每隔一定次数主动刷新cookie，避免过期
            if index % 8 == 0:
                logging.info("🔄 定期刷新cookie...")
                refresh_cookies()
                time.sleep(random.uniform(2, 5))

        else:
            logging.warning(f"❌ cookie 已过期，响应内容: {resData}")
            consecutive_failures += 1
            
            # 如果是在翻页后立即失效，尝试回退翻页
            if index - last_page_turn_index <= 1 and original_data:
                logging.warning("⚠️ 检测到翻页后立即失效，尝试回退翻页状态")
                # 回退到翻页前的状态
                data = original_data.copy()
                current_progress = data['pr']
                page_turn_count -= 1  # 减少翻页计数
                
                # 等待较长时间后重试
                time.sleep(random.uniform(10, 15))
                
                # 刷新cookie
                refresh_cookies()
                time.sleep(random.uniform(3, 7))
                continue
            
            # 如果连续失败次数过多，重置到初始状态
            if consecutive_failures >= max_consecutive_failures:
                logging.warning(f"⚠️ 连续失败 {consecutive_failures} 次，尝试重置到初始状态")
                reset_to_initial_state()
                current_progress = data['pr']  # 更新当前进度
                consecutive_failures = 0
                page_turn_count = 0  # 重置翻页计数
            
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
    push(f"🎉 微信读书自动阅读完成！\n⏱️ 阅读时长：{(index - 1) * 0.5}分钟。\n📖 最终阅读进度：{current_progress}%", PUSH_METHOD)
