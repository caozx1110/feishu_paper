#!/usr/bin/env python3
"""
飞书多维表格初始化脚本
使用此脚本为arxiv_hydra项目创建所需的多维表格结构
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from feishu_bitable_connector import FeishuBitableConnector
from dotenv import load_dotenv


def setup_feishu_tables():
    """初始化飞书多维表格"""
    # 加载环境变量
    load_dotenv()

    # 检查必要的环境变量
    required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_BITABLE_APP_TOKEN']

    # 检查访问令牌（二选一）
    has_user_token = bool(os.getenv('FEISHU_USER_ACCESS_TOKEN')) and 'xxxx' not in os.getenv(
        'FEISHU_USER_ACCESS_TOKEN', ''
    )
    has_tenant_token = bool(os.getenv('FEISHU_TENANT_ACCESS_TOKEN')) and 'xxxx' not in os.getenv(
        'FEISHU_TENANT_ACCESS_TOKEN', ''
    )

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print("❌ 以下环境变量未设置：")
        for var in missing_vars:
            print(f"   {var}")
        print("\n请参考 .env.example 文件设置这些环境变量")
        return False

    # 如果没有有效的访问令牌，但有app_id和app_secret，可以尝试自动获取
    if not has_user_token and not has_tenant_token:
        print("⚠️ 未检测到有效的访问令牌")
        print("🔄 将尝试使用应用凭证自动获取tenant_access_token...")

    try:
        # 初始化连接器
        print("🔗 初始化飞书Bitable连接器...")

        # 如果没有有效的访问令牌，尝试自动获取tenant_access_token
        if not has_user_token and not has_tenant_token:
            print("🔄 未检测到有效的访问令牌，尝试自动获取tenant_access_token...")
            from get_token import get_tenant_access_token

            token_result = get_tenant_access_token()
            if token_result['success']:
                print(f"✅ 成功获取tenant_access_token")
                # 临时设置环境变量
                os.environ['FEISHU_TENANT_ACCESS_TOKEN'] = token_result['tenant_access_token']
                has_tenant_token = True
            else:
                print(f"❌ 获取tenant_access_token失败: {token_result['message']}")
                return False

        connector = FeishuBitableConnector()

        if connector.config.token_type == "tenant":
            print("🔑 使用应用访问令牌模式（推荐）")
        elif connector.config.token_type == "user":
            print("🔑 使用用户访问令牌模式")
        else:
            print("⚠️ 令牌类型未知")

        # 创建论文主表
        print("📋 创建论文主表...")
        papers_table_result = connector.create_papers_table()
        papers_table_id = papers_table_result.get('table_id')
        if papers_table_id:
            print(f"✅ 论文主表创建成功，Table ID: {papers_table_id}")
        else:
            print(f"❌ 论文主表创建失败: {papers_table_result}")
            return False

        # 创建关系表
        print("\n🔗 创建领域关系表...")
        relations_table_result = connector.create_relations_table()
        relations_table_id = relations_table_result.get('table_id')
        if relations_table_id:
            print(f"✅ 领域关系表创建成功，Table ID: {relations_table_id}")
        else:
            print(f"❌ 领域关系表创建失败: {relations_table_result}")
            return False

        print("\n🎉 飞书多维表格初始化完成！")
        print("\n📝 环境变量设置摘要：")
        print("请将以下内容添加到你的 .env 文件：")
        print(f"FEISHU_PAPERS_TABLE_ID={papers_table_id}")
        print(f"FEISHU_RELATIONS_TABLE_ID={relations_table_id}")

        print("\n🚀 现在你可以运行 arxiv_hydra.py 来同步论文到飞书了！")

        return True

    except Exception as e:
        print(f"❌ 初始化过程中出现错误: {str(e)}")
        return False


def show_help():
    """显示帮助信息"""
    print("飞书多维表格初始化脚本")
    print("=" * 50)
    print()
    print("使用方法：")
    print("1. 首先设置必要的环境变量（参考 .env.example）")
    print("2. 运行此脚本：python setup_feishu.py")
    print()
    print("必要的环境变量：")
    print("- FEISHU_APP_ID: 飞书应用ID")
    print("- FEISHU_APP_SECRET: 飞书应用密钥")
    print("- FEISHU_USER_ACCESS_TOKEN: 用户访问令牌 (可选)")
    print("- FEISHU_TENANT_ACCESS_TOKEN: 应用访问令牌 (可选，与用户令牌二选一)")
    print("- FEISHU_BITABLE_APP_TOKEN: 多维表格app token")
    print()
    print("访问令牌说明：")
    print("- user_access_token: 需要用户授权，适用于用户操作")
    print("- tenant_access_token: 应用身份调用，适用于自动化操作")
    print("- 两种令牌二选一即可，推荐使用tenant_access_token进行自动化操作")
    print()
    print("脚本功能：")
    print("- 自动创建论文主表（包含标题、作者、摘要等字段）")
    print("- 自动创建领域关系表（用于管理论文分类）")
    print("- 输出表格ID用于后续配置")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
    else:
        setup_feishu_tables()
