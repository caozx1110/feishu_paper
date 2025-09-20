"""
飞书配置管理类

统一管理飞书应用的配置信息，包括认证、连接参数等。
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class FeishuConfig:
    """飞书配置类"""

    # 基础配置
    app_id: str
    app_secret: str

    # 令牌配置
    user_access_token: Optional[str] = None
    tenant_access_token: Optional[str] = None

    # 多维表格配置
    app_token: str = ""  # 多维表格应用令牌

    # API配置
    base_url: str = "https://open.feishu.cn/open-apis"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

    # 内部状态
    _token_expire_time: Optional[datetime] = field(default=None, init=False)
    _cached_token: Optional[str] = field(default=None, init=False)

    def __post_init__(self):
        """初始化后处理"""
        if not self.app_id or not self.app_secret:
            raise ValueError("app_id 和 app_secret 不能为空")

    @property
    def access_token(self) -> Optional[str]:
        """获取当前有效的访问令牌"""
        # 优先使用用户令牌
        if self.user_access_token and self.user_access_token != "xxxx":
            return self.user_access_token

        # 使用应用令牌（需要检查过期时间）
        if self.tenant_access_token and self.tenant_access_token != "xxxx":
            return self.tenant_access_token

        # 使用缓存的令牌
        if self._cached_token and self._is_token_valid():
            return self._cached_token

        return None

    @property
    def token_type(self) -> str:
        """获取当前使用的令牌类型"""
        if self.user_access_token and self.user_access_token != "xxxx":
            return "user"
        elif self.tenant_access_token and self.tenant_access_token != "xxxx":
            return "tenant"
        elif self._cached_token and self._is_token_valid():
            return "tenant"
        else:
            return "none"

    def _is_token_valid(self) -> bool:
        """检查缓存的令牌是否仍然有效"""
        if not self._token_expire_time:
            return False

        # 提前5分钟认为令牌过期，避免边界情况
        return datetime.now() < (self._token_expire_time - timedelta(minutes=5))

    def update_cached_token(self, token: str, expire_seconds: int) -> None:
        """更新缓存的令牌信息"""
        self._cached_token = token
        self._token_expire_time = datetime.now() + timedelta(seconds=expire_seconds)
        logger.debug(f"已更新缓存令牌，过期时间: {self._token_expire_time}")

    def clear_cached_token(self) -> None:
        """清除缓存的令牌"""
        self._cached_token = None
        self._token_expire_time = None

    def validate(self) -> bool:
        """验证配置的有效性"""
        if not self.app_id or not self.app_secret:
            logger.error("app_id 或 app_secret 为空")
            return False

        if not self.access_token:
            logger.warning("没有有效的访问令牌")

        return True

    @classmethod
    def from_env(cls, prefix: str = "FEISHU") -> "FeishuConfig":
        """从环境变量创建配置"""
        return cls(
            app_id=os.getenv(f"{prefix}_APP_ID", ""),
            app_secret=os.getenv(f"{prefix}_APP_SECRET", ""),
            user_access_token=os.getenv(f"{prefix}_USER_ACCESS_TOKEN"),
            tenant_access_token=os.getenv(f"{prefix}_TENANT_ACCESS_TOKEN"),
            app_token=os.getenv(f"{prefix}_BITABLE_APP_TOKEN", ""),
        )

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "FeishuConfig":
        """从字典创建配置"""
        return cls(
            app_id=config_dict.get("app_id", ""),
            app_secret=config_dict.get("app_secret", ""),
            user_access_token=config_dict.get("user_access_token"),
            tenant_access_token=config_dict.get("tenant_access_token"),
            app_token=config_dict.get("app_token", ""),
            base_url=config_dict.get("base_url", "https://open.feishu.cn/open-apis"),
            timeout=config_dict.get("timeout", 30),
            max_retries=config_dict.get("max_retries", 3),
            retry_delay=config_dict.get("retry_delay", 1.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
            "user_access_token": self.user_access_token,
            "tenant_access_token": self.tenant_access_token,
            "app_token": self.app_token,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
        }


class FeishuAPIError(Exception):
    """飞书API异常类"""

    def __init__(self, message: str, code: int = None, response: dict = None):
        self.message = message
        self.code = code
        self.response = response
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.code:
            return f"FeishuAPIError(code={self.code}): {self.message}"
        return f"FeishuAPIError: {self.message}"


# 字段类型常量
class FieldType:
    """飞书多维表格字段类型"""

    TEXT = 1  # 单行文本
    NUMBER = 2  # 数字
    SINGLE_SELECT = 3  # 单选
    MULTI_SELECT = 4  # 多选
    DATE = 5  # 日期
    CHECKBOX = 7  # 复选框
    PERSON = 11  # 人员
    PHONE = 13  # 电话号码
    URL = 15  # 超链接
    ATTACHMENT = 17  # 附件
    LOOKUP = 18  # 单向关联
    FORMULA = 20  # 公式
    DUPLEX_LINK = 21  # 双向关联
    LOCATION = 22  # 地理位置
    GROUP = 23  # 群组
    CREATED_TIME = 1001  # 创建时间
    MODIFIED_TIME = 1002  # 最后更新时间
    CREATED_BY = 1003  # 创建人
    MODIFIED_BY = 1004  # 修改人
    AUTO_NUMBER = 1005  # 自动编号


# 字段类型中文映射
FIELD_TYPE_NAMES = {
    FieldType.TEXT: "单行文本",
    FieldType.NUMBER: "数字",
    FieldType.SINGLE_SELECT: "单选",
    FieldType.MULTI_SELECT: "多选",
    FieldType.DATE: "日期",
    FieldType.CHECKBOX: "复选框",
    FieldType.PERSON: "人员",
    FieldType.PHONE: "电话号码",
    FieldType.URL: "超链接",
    FieldType.ATTACHMENT: "附件",
    FieldType.LOOKUP: "单向关联",
    FieldType.FORMULA: "公式",
    FieldType.DUPLEX_LINK: "双向关联",
    FieldType.LOCATION: "地理位置",
    FieldType.GROUP: "群组",
    FieldType.CREATED_TIME: "创建时间",
    FieldType.MODIFIED_TIME: "最后更新时间",
    FieldType.CREATED_BY: "创建人",
    FieldType.MODIFIED_BY: "修改人",
    FieldType.AUTO_NUMBER: "自动编号",
}
