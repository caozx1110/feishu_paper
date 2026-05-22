#!/usr/bin/env python3
"""
飞书访问令牌获取工具
用于获取tenant_access_token（应用访问令牌）
"""

import os
import requests
from dotenv import load_dotenv

from ..terminal import panel, print


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
        # 读取现有的.env文件
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
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
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return True

    except Exception as e:
        print(f"更新.env文件失败: {e}")
        return False


def main():
    """主函数 - 获取并保存tenant_access_token"""
    panel("Feishu Token", "飞书应用访问令牌获取工具", style="cyan")

    # 检查环境变量
    load_dotenv()
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')

    if not app_id or not app_secret:
        print("❌ 请先在.env文件中设置FEISHU_APP_ID和FEISHU_APP_SECRET")
        print("   参考.env.example文件进行配置")
        return

    print(f"📱 使用应用ID: {app_id}")
    print("🔄 正在获取应用访问令牌...")

    # 获取token
    result = get_tenant_access_token()

    if result['success']:
        token = result['tenant_access_token']
        expire = result['expire']

        print(f"✅ {result['message']}")
        print(f"🔐 Token: {token[:20]}...{token[-10:]}")

        # 询问是否保存到.env文件
        save_choice = input("\n是否将token保存到.env文件？(y/n): ").lower().strip()

        if save_choice in ['y', 'yes', '是']:
            if update_env_file(token):
                print("✅ 已将tenant_access_token保存到.env文件")
                print("🚀 现在可以运行 autopaper health 或 autopaper sync 来检查和同步")
            else:
                print("❌ 保存到.env文件失败")
        else:
            print("ℹ️ 请手动将以下token添加到.env文件：")
            print(f"FEISHU_TENANT_ACCESS_TOKEN={token}")

        print(f"\n⏰ 注意：此token有效期为{expire}秒（约{expire//3600:.1f}小时）")
        print("   过期后需要重新获取")

    else:
        print(f"❌ {result['message']}")
        if 'code' in result:
            print(f"   错误代码: {result['code']}")
        print("   请检查应用ID和密钥是否正确")


if __name__ == "__main__":
    main()
