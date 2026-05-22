#!/usr/bin/env python3
"""Feishu tenant_access_token helpers."""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from ..terminal import error, info, key_values, panel, print, success


def get_tenant_access_token(app_id: str = None, app_secret: str = None, base_url: str = None, timeout: int = 30) -> dict:
    """获取应用访问令牌 (tenant_access_token)

    Args:
        app_id: 飞书应用ID，如果不提供则从环境变量读取
        app_secret: 飞书应用密钥，如果不提供则从环境变量读取

    Returns:
        包含token信息的字典
    """
    # 从环境变量获取配置
    load_dotenv()

    if not app_id:
        app_id = os.getenv('FEISHU_APP_ID')
    if not app_secret:
        app_secret = os.getenv('FEISHU_APP_SECRET')

    if not app_id or not app_secret:
        raise ValueError("需要提供FEISHU_APP_ID和FEISHU_APP_SECRET")

    # 请求参数
    payload = {"app_id": app_id, "app_secret": app_secret}

    base_url = (base_url or os.getenv('FEISHU_BASE_URL') or "https://open.feishu.cn/open-apis").rstrip("/")
    url = f"{base_url}/auth/v3/tenant_access_token/internal"

    try:
        response = requests.post(
            url, json=payload, headers={'Content-Type': 'application/json; charset=utf-8'}, timeout=timeout
        )

        result = response.json()

        if result.get('code') == 0:
            return {
                'success': True,
                'tenant_access_token': result.get('tenant_access_token'),
                'expire': result.get('expire'),
                'message': f"成功获取tenant_access_token，有效期: {result.get('expire')}秒",
            }
        else:
            return {
                'success': False,
                'error': result.get('msg', 'Unknown error'),
                'code': result.get('code'),
                'message': f"获取tenant_access_token失败: {result.get('msg', 'Unknown error')}",
            }

    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': str(e), 'message': f"网络请求失败: {str(e)}"}


def update_env_file(tenant_access_token: str, env_file: str = '.env') -> bool:
    """更新.env文件中的tenant_access_token

    Args:
        tenant_access_token: 新的访问令牌
        env_file: 环境变量文件路径

    Returns:
        是否成功更新
    """
    try:
        env_path = Path(env_file).expanduser()
        env_path.parent.mkdir(parents=True, exist_ok=True)

        # 读取现有的.env文件
        if env_path.exists():
            with env_path.open('r', encoding='utf-8') as f:
                lines = f.readlines()
        else:
            lines = []

        # 查找并更新FEISHU_TENANT_ACCESS_TOKEN行
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith('FEISHU_TENANT_ACCESS_TOKEN='):
                lines[i] = f'FEISHU_TENANT_ACCESS_TOKEN={tenant_access_token}\n'
                updated = True
                break

        # 如果没有找到，添加新行
        if not updated:
            lines.append(f'FEISHU_TENANT_ACCESS_TOKEN={tenant_access_token}\n')

        # 写回文件
        with env_path.open('w', encoding='utf-8') as f:
            f.writelines(lines)

        env_path.chmod(0o600)
        return True

    except Exception as e:
        error(f"更新.env文件失败: {e}")
        return False


def mask_token(token: str, *, prefix: int = 12, suffix: int = 8) -> str:
    """Return a display-safe token preview."""
    if len(token) <= prefix + suffix:
        return "*" * len(token)
    return f"{token[:prefix]}...{token[-suffix:]}"


def main(
    *,
    save: bool = False,
    env_file: str = ".env",
    print_token: bool = False,
    app_id: str | None = None,
    app_secret: str | None = None,
    base_url: str | None = None,
    timeout: int = 30,
) -> bool:
    """Fetch and optionally persist a tenant access token."""
    panel("Feishu Token", "飞书应用访问令牌获取工具", style="cyan")

    load_dotenv()
    app_id = app_id or os.getenv('FEISHU_APP_ID')
    app_secret = app_secret or os.getenv('FEISHU_APP_SECRET')

    if not app_id or not app_secret:
        error("请先设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        return False

    print(f"📱 使用应用ID: {app_id}")
    print("🔄 正在获取应用访问令牌...")

    result = get_tenant_access_token(app_id=app_id, app_secret=app_secret, base_url=base_url, timeout=timeout)

    if result['success']:
        token = result['tenant_access_token']
        expire = result['expire']

        success(result['message'])
        key_values(
            "Token",
            {
                "preview": mask_token(token),
                "expires": f"{expire} 秒（约 {expire//3600:.1f} 小时）",
            },
            style="green",
        )

        if print_token:
            print(f"FEISHU_TENANT_ACCESS_TOKEN={token}")

        if save:
            if update_env_file(token, env_file):
                success(f"已将 tenant_access_token 保存到 {env_file}")
            else:
                return False
        elif not print_token:
            info("未写入 .env；如需保存请使用 autopaper get-token --save")
        return True

    error(result['message'])
    if 'code' in result:
        print(f"错误代码: {result['code']}")
    return False


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
