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

def simulate_page_turn(data):
    """模拟翻页
    Args:
        data: 请求数据字典
    """
    # 随机翻页次数(2-4次)，减少翻页频率
    page_turns = random.randint(2, 4)
    current_page = data.get('pf', 1)  # 获取当前页码，默认从第1页开始
    
    for i in range(page_turns):
        try:
            # 随机翻页间隔(15-25秒)，降低请求频率
            time.sleep(random.uniform(15, 25))
            current_page += 1
            # 更新请求数据中的页码
            data['pf'] = current_page
            data['pc'] = current_page - 1  # 上一页的页码
            
            # 重新生成时间戳和签名
            data['ct'] = int(time.time())
            data['ts'] = int(time.time() * 1000)
            data['rn'] = random.randint(0, 1000)
            data['sg'] = hashlib.sha256(f"{data['ts']}{data['rn']}{KEY}".encode()).hexdigest()
            data['s'] = cal_hash(encode_data(data))
            
            # 发送翻页请求
            response = requests.post(READ_URL, headers=headers, cookies=cookies, 
                                   data=json.dumps(data, separators=(',', ':')))
            result = response.json()
            
            if 'succ' not in result:
                # 尝试刷新Cookie
                logging.warning("⚠️ 翻页请求失败，尝试刷新Cookie...")
                new_skey = get_wr_skey()
                if new_skey:
                    cookies['wr_skey'] = new_skey
                    logging.info(f"✅ 密钥刷新成功，新密钥：{new_skey}")
                    # 重试当前页面
                    response = requests.post(READ_URL, headers=headers, cookies=cookies, 
                                          data=json.dumps(data, separators=(',', ':')))
                    if 'succ' not in response.json():
                        logging.warning("❌ 重试失败，停止翻页...")
                        return
                else:
                    logging.warning("❌ Cookie刷新失败，停止翻页...")
                    return
            
            logging.info(f"📖 第 {i+1}/{page_turns} 次翻页，当前页码：{current_page}")
            # 随机增加2-5秒的停顿，模拟阅读内容
            time.sleep(random.uniform(2, 5))
            
        except Exception as e:
            logging.error(f"❌ 翻页过程出错: {str(e)}")
            return

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


index = 1
while index <= READ_NUM:
    try:
        data['ct'] = int(time.time())
        data['ts'] = int(time.time() * 1000)
        data['rn'] = random.randint(0, 1000)
        data['sg'] = hashlib.sha256(f"{data['ts']}{data['rn']}{KEY}".encode()).hexdigest()
        data['s'] = cal_hash(encode_data(data))
        
        # 初始化页码参数
        if 'pf' not in data:
            data['pf'] = 1  # 当前页码
            data['pc'] = 0  # 上一页页码

        logging.info(f"⏱️ 尝试第 {index} 次阅读...")
        response = requests.post(READ_URL, headers=headers, cookies=cookies, data=json.dumps(data, separators=(',', ':')))
        resData = response.json()

        if 'succ' in resData:
            index += 1
            logging.info("📚 开始模拟阅读行为...")
            simulate_page_turn(data)
            # 每次阅读后增加随机等待时间(45-75秒)
            wait_time = random.uniform(45, 75)
            logging.info(f"⏳ 等待 {wait_time:.1f} 秒后继续下一次阅读...")
            time.sleep(wait_time)
            logging.info(f"✅ 阅读成功，阅读进度：{(index - 1) * 1} 分钟")
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
                
    except Exception as e:
        logging.error(f"❌ 阅读过程出错: {str(e)}")
        time.sleep(30)  # 出错后等待30秒再继续
        continue
        
    data.pop('s')

logging.info("🎉 阅读脚本已完成！")

if PUSH_METHOD not in (None, ''):
    logging.info("⏱️ 开始推送...")
    push(f"🎉 微信读书自动阅读完成！\n⏱️ 阅读时长：{(index - 1) * 1}分钟。", PUSH_METHOD)
