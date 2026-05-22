"""Feishu authentication and low-level request handling."""

from __future__ import annotations

import time
from typing import Any, Dict

import requests

from .config import FeishuBitableConfig
from .errors import FeishuBitableAPIError


class FeishuAuthMixin:
    def _create_config_from_env(self) -> FeishuBitableConfig:
        """从环境变量创建配置"""
        import os
        from dotenv import load_dotenv

        load_dotenv()

        return FeishuBitableConfig(
            app_id=os.getenv('FEISHU_APP_ID', ''),
            app_secret=os.getenv('FEISHU_APP_SECRET', ''),
            user_access_token=os.getenv('FEISHU_USER_ACCESS_TOKEN'),
            tenant_access_token=os.getenv('FEISHU_TENANT_ACCESS_TOKEN'),
            app_token=os.getenv('FEISHU_BITABLE_APP_TOKEN', ''),
        )

    def get_tenant_access_token(self) -> str:
        """获取应用访问令牌 (tenant_access_token)

        Returns:
            应用访问令牌字符串
        """
        if not self.config.app_id or not self.config.app_secret:
            raise FeishuBitableAPIError("获取tenant_access_token需要app_id和app_secret")

        payload = {"app_id": self.config.app_id, "app_secret": self.config.app_secret}

        endpoint = "auth/v3/tenant_access_token/internal"

        # 临时创建一个不带认证的session来获取token
        temp_session = requests.Session()
        temp_session.headers.update({'Content-Type': 'application/json; charset=utf-8'})

        try:
            url = f"{self.config.base_url}/{endpoint}"
            response = temp_session.post(url, json=payload, timeout=self.config.timeout)
            result = response.json()

            if result.get('code') == 0:
                tenant_access_token = result.get('tenant_access_token')
                expires_in = result.get('expire')

                print(f"✅ 成功获取tenant_access_token，有效期: {expires_in}秒")
                return tenant_access_token
            else:
                raise FeishuBitableAPIError(
                    f"获取tenant_access_token失败: {result.get('msg', 'Unknown error')}", result.get('code'), result
                )

        except requests.exceptions.RequestException as e:
            raise FeishuBitableAPIError(f"获取tenant_access_token网络请求失败: {str(e)}")

    def refresh_token_if_needed(self) -> bool:
        """如果使用tenant_access_token且需要刷新，则自动刷新

        Returns:
            是否成功刷新了token
        """
        if self.config.token_type == "tenant" and self.config.app_id and self.config.app_secret:
            try:
                new_token = self.get_tenant_access_token()
                self.config.tenant_access_token = new_token

                # 更新session header
                self.session.headers.update({'Authorization': f'Bearer {new_token}'})

                return True
            except Exception as e:
                print(f"⚠️ token刷新失败: {e}")
                return False
        return False

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送API请求"""
        url = f"{self.config.base_url}/{endpoint}"

        for attempt in range(self.config.max_retries):
            try:
                response = self.session.request(method, url, timeout=self.config.timeout, **kwargs)

                result = response.json()

                if result.get('code') == 0:
                    return result.get('data', {})
                elif result.get('code') == 99991663:  # token过期
                    print("🔄 检测到token过期，尝试刷新...")
                    if self.refresh_token_if_needed():
                        print("✅ token刷新成功，重试请求...")
                        continue  # 重试请求
                    else:
                        raise FeishuBitableAPIError(
                            f"Token已过期且刷新失败: {result.get('msg', 'Unknown error')}", result.get('code'), result
                        )
                else:
                    raise FeishuBitableAPIError(
                        f"API请求失败: {result.get('msg', 'Unknown error')}", result.get('code'), result
                    )

            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise FeishuBitableAPIError(f"网络请求失败: {str(e)}")
                time.sleep(self.config.retry_delay)
