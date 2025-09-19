#!/usr/bin/env python3
"""
飞书多维表格设置向导
帮助用户一步步完成多维表格的创建和配置
"""

import os
import webbrowser
from dotenv import load_dotenv


def setup_wizard():
    """设置向导主函数"""
    print("🧙‍♂️ 飞书多维表格设置向导")
    print("=" * 50)

    # 加载环境变量
    load_dotenv()

    # 检查基础配置
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')

    if not app_id or not app_secret:
        print("❌ 请先在.env文件中设置FEISHU_APP_ID和FEISHU_APP_SECRET")
        return False

    print(f"✅ 检测到飞书应用配置")
    print(f"   应用ID: {app_id}")

    # 检查访问令牌
    tenant_token = os.getenv('FEISHU_TENANT_ACCESS_TOKEN')
    if not tenant_token or 'xxxx' in tenant_token:
        print("\n🔄 获取访问令牌...")
        from get_token import get_tenant_access_token

        result = get_tenant_access_token()
        if result['success']:
            print("✅ 成功获取访问令牌")
            tenant_token = result['tenant_access_token']

            # 更新.env文件
            from get_token import update_env_file

            update_env_file(tenant_token)
        else:
            print(f"❌ 获取访问令牌失败: {result['message']}")
            return False
    else:
        print("✅ 检测到有效的访问令牌")

    # 检查多维表格配置
    bitable_token = os.getenv('FEISHU_BITABLE_APP_TOKEN')
    if not bitable_token or 'xxxx' in bitable_token:
        print("\n📋 需要创建多维表格")
        print("请按照以下步骤操作：")
        print()
        print("1. 🌐 打开飞书网页版")
        print("2. 📊 创建新的多维表格")
        print("3. 📝 从URL中复制app_token")
        print("4. ⚙️ 配置应用权限")
        print()

        # 询问是否自动打开飞书
        choice = input("是否自动打开飞书网页版？(y/n): ").lower().strip()
        if choice in ['y', 'yes', '是']:
            print("🌐 正在打开飞书...")
            webbrowser.open("https://feishu.cn/")

        print("\n" + "=" * 50)
        print("📋 创建多维表格的详细步骤：")
        print()
        print("1. 在飞书中点击「+」-> 「多维表格」")
        print("2. 创建一个新的多维表格，名称可以是「论文管理系统」")
        print("3. 创建后，查看浏览器地址栏的URL")
        print("4. URL格式为：https://xxx.feishu.cn/base/[app_token]")
        print("5. 复制其中的app_token（通常以 basc 开头）")
        print()
        print("⚠️ 重要：确保应用有多维表格的权限")
        print("   在飞书开放平台 -> 应用详情 -> 权限管理中")
        print("   开启「bitable:app」权限")
        print()

        app_token = input("请输入多维表格的app_token: ").strip()

        if not app_token or len(app_token) < 20:
            print("❌ app_token无效，请重新输入")
            return False

        # 更新.env文件
        try:
            # 读取现有的.env文件
            with open('.env', 'r', encoding='utf-8') as f:
                content = f.read()

            # 替换BITABLE_APP_TOKEN
            if 'FEISHU_BITABLE_APP_TOKEN=' in content:
                import re

                content = re.sub(r'FEISHU_BITABLE_APP_TOKEN=.*', f'FEISHU_BITABLE_APP_TOKEN={app_token}', content)
            else:
                content += f'\nFEISHU_BITABLE_APP_TOKEN={app_token}\n'

            # 写回文件
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(content)

            print("✅ 已更新.env文件中的BITABLE_APP_TOKEN")

        except Exception as e:
            print(f"❌ 更新.env文件失败: {e}")
            return False
    else:
        print("✅ 检测到多维表格配置")

    print("\n🎉 配置检查完成！")
    print("🚀 现在可以运行 setup_feishu.py 来创建数据表了")

    # 询问是否立即运行setup
    choice = input("\n是否立即运行setup_feishu.py创建数据表？(y/n): ").lower().strip()
    if choice in ['y', 'yes', '是']:
        print("\n" + "=" * 50)
        print("🔄 正在运行setup_feishu.py...")

        # 重新加载环境变量
        load_dotenv()

        try:
            from setup_feishu import setup_feishu_tables

            return setup_feishu_tables()
        except Exception as e:
            print(f"❌ 运行setup失败: {e}")
            return False

    return True


def show_help():
    """显示帮助信息"""
    print("飞书多维表格设置向导")
    print("=" * 30)
    print()
    print("此向导将帮助你完成以下配置：")
    print("1. ✅ 检查飞书应用配置")
    print("2. 🔑 获取访问令牌")
    print("3. 📋 创建多维表格")
    print("4. ⚙️ 配置权限")
    print("5. 🚀 创建数据表")
    print()
    print("使用方法：")
    print("python setup_wizard.py")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
    else:
        setup_wizard()
