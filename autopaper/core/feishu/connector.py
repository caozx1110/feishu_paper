"""
飞书API连接器

统一的飞书API客户端，提供基础的HTTP请求功能和认证管理。
"""

import json
import time
import logging
import requests
from typing import Dict, Any, Optional
from .config import FeishuConfig, FeishuAPIError

logger = logging.getLogger(__name__)


class FeishuConnector:
    """飞书API连接器 - 提供基础的API调用功能"""

    def __init__(self, config: FeishuConfig):
        """
        初始化连接器

        Args:
            config: 飞书配置对象
        """
        self.config = config
        self.session = requests.Session()
        self._setup_session()

        logger.info(f"🔑 初始化飞书连接器，使用 {config.token_type}_access_token")

    def _setup_session(self) -> None:
        """设置请求会话"""
        self.session.headers.update(
            {"Content-Type": "application/json; charset=utf-8", "Authorization": f"Bearer {self.config.access_token}"}
        )
        self.session.timeout = self.config.timeout

    def _refresh_session_auth(self) -> None:
        """刷新会话认证头"""
        if self.config.access_token:
            self.session.headers["Authorization"] = f"Bearer {self.config.access_token}"

    def get_tenant_access_token(self) -> Optional[str]:
        """获取应用访问令牌 (tenant_access_token)

        Returns:
            应用访问令牌字符串
        """
        if not self.config.app_id or not self.config.app_secret:
            raise FeishuAPIError("app_id 和 app_secret 不能为空")

        payload = {"app_id": self.config.app_id, "app_secret": self.config.app_secret}

        endpoint = "auth/v3/tenant_access_token/internal"

        # 使用临时会话获取token，避免认证循环
        temp_session = requests.Session()
        temp_session.headers.update({"Content-Type": "application/json; charset=utf-8"})

        try:
            url = f"{self.config.base_url}/{endpoint}"
            response = temp_session.post(url, json=payload, timeout=self.config.timeout)
            result = response.json()

            if result.get("code") == 0:
                token = result.get("tenant_access_token")
                expire = result.get("expire", 7200)  # 默认2小时

                # 更新配置中的缓存令牌
                self.config.update_cached_token(token, expire)

                # 刷新当前会话的认证
                self._refresh_session_auth()

                logger.info(f"✅ 成功获取tenant_access_token，有效期: {expire}秒")
                return token
            else:
                error_msg = result.get("msg", "Unknown error")
                raise FeishuAPIError(f"获取tenant_access_token失败: {error_msg}", result.get("code"), result)

        except requests.exceptions.RequestException as e:
            raise FeishuAPIError(f"网络请求失败: {str(e)}")

    def refresh_token_if_needed(self) -> bool:
        """如果需要则刷新令牌

        Returns:
            是否成功刷新了令牌
        """
        if self.config.token_type == "tenant" and not self.config._is_token_valid():
            try:
                self.get_tenant_access_token()
                return True
            except FeishuAPIError as e:
                logger.error(f"刷新令牌失败: {e}")
                return False
        return False

    def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送API请求

        Args:
            method: HTTP方法
            endpoint: API端点 (不应该以/开头)
            **kwargs: 请求参数

        Returns:
            API响应数据

        Raises:
            FeishuAPIError: API调用失败
        """
        # 确保endpoint不以/开头，避免双斜杠
        endpoint = endpoint.lstrip("/")
        url = f"{self.config.base_url}/{endpoint}"

        for attempt in range(self.config.max_retries):
            try:
                # 刷新认证（如果需要）
                if attempt > 0:
                    self.refresh_token_if_needed()
                    self._refresh_session_auth()

                response = self.session.request(method, url, **kwargs)

                # 检查HTTP状态码
                if response.status_code == 401:
                    # 认证失败，尝试刷新令牌
                    if self.refresh_token_if_needed():
                        continue
                    else:
                        raise FeishuAPIError("认证失败，请检查令牌", 401)

                response.raise_for_status()

                # 解析响应
                try:
                    result = response.json()
                except json.JSONDecodeError:
                    raise FeishuAPIError(f"响应解析失败: {response.text}")

                # 检查业务状态码
                if result.get("code") != 0:
                    error_msg = result.get("msg", "Unknown error")
                    raise FeishuAPIError(f"API调用失败: {error_msg}", result.get("code"), result)

                return result.get("data", result)

            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise FeishuAPIError(f"网络请求失败: {str(e)}")

                logger.warning(
                    f"请求失败，{self.config.retry_delay}秒后重试 (尝试 {attempt + 1}/{self.config.max_retries}): {e}"
                )
                time.sleep(self.config.retry_delay)

        raise FeishuAPIError("请求重试次数已用尽")

    def test_connection(self) -> bool:
        """测试连接是否正常

        Returns:
            连接是否成功
        """
        try:
            # 获取应用信息来测试连接
            endpoint = "application/v6/applications"
            self.make_request("GET", endpoint)
            return True
        except FeishuAPIError as e:
            logger.error(f"连接测试失败: {e}")
            return False
