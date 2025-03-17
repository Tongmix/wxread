# main.py - 主程序文件
# 实现微信读书自动阅读的核心逻辑，包括请求构造、签名计算和自动刷新认证

import re
import json
import time
import random
import logging
import hashlib
import requests
import urllib.parse
from push import push  # 导入推送通知模块
from config import data, headers, cookies, READ_NUM, PUSH_METHOD  # 导入配置

# 配置日志记录
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)-8s - %(message)s')

# 常量定义
KEY = "3c5c8717f3daf09iop3423zafeqoi"  # 签名计算的密钥
COOKIE_DATA = {"rq": "%2Fweb%2Fbook%2Fread"}  # 刷新cookie时的请求数据
READ_URL = "https://weread.qq.com/web/book/read"  # 阅读接口URL
RENEW_URL = "https://weread.qq.com/web/login/renewal"  # 刷新认证接口URL


def encode_data(data):
    """将数据编码为URL参数格式
    
    Args:
        data (dict): 需要编码的数据字典
        
    Returns:
        str: 编码后的字符串，格式为"key1=value1&key2=value2..."，按键名排序
    """
    return '&'.join(f"{k}={urllib.parse.quote(str(data[k]), safe='')}" for k in sorted(data.keys()))


def cal_hash(input_string):
    """计算哈希值 - 模拟微信读书的哈希算法
    
    Args:
        input_string (str): 输入字符串
        
    Returns:
        str: 计算得到的哈希值
        
    注: 这是从微信读书JS代码中逆向得到的哈希算法
    """
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
    """刷新微信读书的认证密钥
    
    当cookie过期时，尝试获取新的wr_skey
    
    Returns:
        str: 新的wr_skey值，如果获取失败则返回None
    """
    response = requests.post(RENEW_URL, headers=headers, cookies=cookies,
                             data=json.dumps(COOKIE_DATA, separators=(',', ':')))
    for cookie in response.headers.get('Set-Cookie', '').split(';'):
        if "wr_skey" in cookie:
            return cookie.split('=')[-1][:8]
    return None


# 主循环 - 执行自动阅读
index = 1
while index <= READ_NUM:
    # 更新请求数据中的时间戳和随机数
    data['ct'] = int(time.time())  # 当前时间戳(秒)
    data['ts'] = int(time.time() * 1000)  # 当前时间戳(毫秒)
    data['rn'] = random.randint(0, 1000)  # 随机数
    
    # 计算安全签名
    data['sg'] = hashlib.sha256(f"{data['ts']}{data['rn']}{KEY}".encode()).hexdigest()
    
    # 计算请求数据的哈希值
    data['s'] = cal_hash(encode_data(data))

    # 发送阅读请求
    logging.info(f"⏱️ 尝试第 {index} 次阅读...")
    response = requests.post(READ_URL, headers=headers, cookies=cookies, data=json.dumps(data, separators=(',', ':')))
    resData = response.json()

    if 'succ' in resData:
        # 阅读成功，增加计数并等待30秒
        index += 1
        time.sleep(30)  # 每次阅读间隔30秒
        logging.info(f"✅ 阅读成功，阅读进度：{(index - 1) * 0.5} 分钟")

    else:
        # 阅读失败，可能是cookie过期，尝试刷新
        logging.warning("❌ cookie 已过期，尝试刷新...")
        new_skey = get_wr_skey()
        if new_skey:
            # 刷新成功，更新cookie
            cookies['wr_skey'] = new_skey
            logging.info(f"✅ 密钥刷新成功，新密钥：{new_skey}")
            logging.info(f"🔄 重新本次阅读。")
        else:
            # 刷新失败，终止程序
            ERROR_CODE = "❌ 无法获取新密钥或者WXREAD_CURL_BASH配置有误，终止运行。"
            logging.error(ERROR_CODE)
            push(ERROR_CODE, PUSH_METHOD)  # 发送错误通知
            raise Exception(ERROR_CODE)
    
    # 移除签名字段，准备下一次请求
    data.pop('s')

# 阅读完成
logging.info("🎉 阅读脚本已完成！")

# 如果配置了推送方式，发送完成通知
if PUSH_METHOD not in (None, ''):
    logging.info("⏱️ 开始推送...")
    push(f"🎉 微信读书自动阅读完成！\n⏱️ 阅读时长：{(index - 1) * 0.5}分钟。", PUSH_METHOD)
