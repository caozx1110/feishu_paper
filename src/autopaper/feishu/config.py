"""Feishu Bitable configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class FeishuBitableConfig:
    """飞书多维表格配置类"""

    app_id: str
    app_secret: str
    user_access_token: Optional[str] = None  # 用户访问令牌
    tenant_access_token: Optional[str] = None  # 应用访问令牌
    app_token: str = ""  # 多维表格的app_token
    base_url: str = "https://open.feishu.cn/open-apis"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

    def __post_init__(self):
        """验证配置"""
        if not self.user_access_token and not self.tenant_access_token:
            raise ValueError("必须提供 user_access_token 或 tenant_access_token 之一")

        # 优先使用有效的token，而不是优先使用user_access_token
        # 如果user_access_token是占位符，则清空它
        if self.user_access_token and ('xxxx' in self.user_access_token or len(self.user_access_token) < 20):
            self.user_access_token = None

        # 如果tenant_access_token是占位符，则清空它
        if self.tenant_access_token and ('xxxx' in self.tenant_access_token or len(self.tenant_access_token) < 20):
            self.tenant_access_token = None

        # 重新检查是否有有效token
        if not self.user_access_token and not self.tenant_access_token:
            raise ValueError("未提供有效的访问令牌，请检查环境变量配置")

    @property
    def access_token(self) -> str:
        """获取当前使用的访问令牌"""
        return self.user_access_token or self.tenant_access_token

    @property
    def token_type(self) -> str:
        """获取令牌类型"""
        if self.user_access_token:
            return "user"
        elif self.tenant_access_token:
            return "tenant"
        else:
            return "unknown"

    @classmethod
    def from_hydra_config(cls, cfg) -> 'FeishuBitableConfig':
        """从Hydra配置创建飞书多维表格配置"""
        feishu_cfg = cfg.get('feishu', {})
        api_cfg = feishu_cfg.get('api', {})
        bitable_cfg = feishu_cfg.get('bitable', {})

        return cls(
            app_id=api_cfg.get('app_id', ''),
            app_secret=api_cfg.get('app_secret', ''),
            user_access_token=api_cfg.get('user_access_token') or None,
            tenant_access_token=api_cfg.get('tenant_access_token') or None,
            app_token=bitable_cfg.get('app_token', ''),
            base_url=api_cfg.get('base_url', 'https://open.feishu.cn/open-apis'),
            timeout=api_cfg.get('timeout', 30),
            max_retries=api_cfg.get('max_retries', 3),
            retry_delay=api_cfg.get('retry_delay', 1.0),
        )
