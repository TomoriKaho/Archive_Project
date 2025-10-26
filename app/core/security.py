from __future__ import annotations  # 启用未来注解特性以便在类型注释中引用后定义的类型

import logging  # 提供日志记录功能用于输出安全相关的提示
import os  # 读取环境变量以获得密钥和配置
from dotenv import load_dotenv, find_dotenv  # 用于加载环境变量
from datetime import datetime, timedelta, timezone  # 处理token过期时间所需的时间工具
from typing import Any, Dict  # 声明函数入参和返回值的类型提示

from jose import JWTError, jwt  # 引入JWT库以实现令牌的编码与解码
from passlib.context import CryptContext  # 使用Passlib统一管理密码哈希算法

logger = logging.getLogger(__name__)  # 获取当前模块的日志记录器
load_dotenv(find_dotenv())  # 加载环境变量文件中的配置
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")  # 配置密码哈希上下文，选择Argon2算法并自动管理版本

JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me")  # 从环境变量读取JWT密钥，默认值仅用于开发提示应尽快替换

if JWT_SECRET_KEY == "change-me":  # 检查是否仍使用默认密钥
    logger.warning("JWT_SECRET_KEY 使用默认值，正式环境务必修改以防止令牌被伪造")  # 给出日志警示确保部署后调整

JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")  # 读取JWT签名算法，默认使用HS256对称加密
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))  # 读取访问令牌有效期并保持60分钟默认值


def hash_password(password: str) -> str:  # 定义密码哈希函数
    """对用户输入的明文密码进行哈希处理。"""  # 文档字符串说明函数用途
    hashed = pwd_context.hash(password)  # 使用Argon2算法对明文进行哈希，避免直接存储明文密码
    return hashed  # 返回哈希结果供数据库保存，实现“哈希 vs 明文”的安全隔离


def verify_password(plain_password: str, hashed_password: str) -> bool:  # 定义密码校验函数
    """校验用户输入的明文密码与数据库中存储的哈希值是否匹配。"""  # 解释函数职责
    result = pwd_context.verify(plain_password, hashed_password)  # Passlib会使用Argon2算法比较明文和哈希，避免泄露真实密码
    return result  # 返回布尔结果，调用方据此判断登录是否成功


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:  # 定义JWT生成函数
    """基于给定的数据生成带有效期的JWT访问令牌。"""  # 注释函数作用
    to_encode = data.copy()  # 复制数据避免调用方的字典被篡改
    expire_delta = expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  # 计算令牌的过期时间，优先使用外部传入的时长
    expire_time = datetime.now(timezone.utc) + expire_delta  # 以UTC时间为基准计算具体过期时刻
    to_encode.update({"exp": expire_time})  # 将过期时间写入JWT标准声明exp中用于校验
    token = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)  # 使用指定算法和密钥生成签名后的令牌
    return token  # 返回可供客户端使用的JWT字符串


def decode_access_token(token: str) -> Dict[str, Any]:  # 定义JWT解析函数
    """解析JWT令牌并返回其中的载荷数据，失败时抛出ValueError。"""  # 描述函数行为
    try:  # 捕获可能的解析异常
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])  # 使用相同密钥解码并验证签名
        return payload  # 解析成功后返回payload供上层业务使用
    except JWTError as exc:  # 捕获所有JWT异常
        raise ValueError("invalid token") from exc  # 统一转化为ValueError便于调用方处理认证失败
