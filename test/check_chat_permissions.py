#!/usr/bin/env python3
"""
飞书权限检查和申请助手
帮助用户检查和申请群聊通知所需的权限
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv


def check_environment_variables():
    """检查环境变量配置"""
    print("🔍 检查环境变量配置...")

    required_vars = {
        'FEISHU_APP_ID': '飞书应用ID',
        'FEISHU_APP_SECRET': '飞书应用密钥',
        'FEISHU_BITABLE_APP_TOKEN': '多维表格App Token',
    }

    token_vars = {'FEISHU_USER_ACCESS_TOKEN': '用户访问令牌', 'FEISHU_TENANT_ACCESS_TOKEN': '应用访问令牌'}

    missing_vars = []
    valid_vars = []

    # 检查必需变量
    for var, desc in required_vars.items():
        value = os.getenv(var, '')
        if not value or 'xxxx' in value:
            missing_vars.append(f"{var} ({desc})")
        else:
            valid_vars.append(f"✅ {desc}")

    # 检查访问令牌
    has_valid_token = False
    for var, desc in token_vars.items():
        value = os.getenv(var, '')
        if value and 'xxxx' not in value and len(value) > 20:
            valid_vars.append(f"✅ {desc}")
            has_valid_token = True

    if not has_valid_token:
        missing_vars.append("有效的访问令牌 (USER_ACCESS_TOKEN 或 TENANT_ACCESS_TOKEN)")

    # 显示结果
    if valid_vars:
        print("✅ 已配置的环境变量:")
        for var in valid_vars:
            print(f"   {var}")

    if missing_vars:
        print("❌ 缺失的环境变量:")
        for var in missing_vars:
            print(f"   {var}")
        return False

    print("✅ 所有必需的环境变量都已正确配置")
    return True


def check_api_permissions():
    """检查API权限"""
    print("\n🔐 检查API权限...")

    try:
        from feishu_bitable_connector import FeishuBitableConfig, FeishuBitableConnector

        config = FeishuBitableConfig(
            app_id=os.getenv('FEISHU_APP_ID', ''),
            app_secret=os.getenv('FEISHU_APP_SECRET', ''),
            tenant_access_token=os.getenv('FEISHU_TENANT_ACCESS_TOKEN'),
            user_access_token=os.getenv('FEISHU_USER_ACCESS_TOKEN'),
            app_token=os.getenv('FEISHU_BITABLE_APP_TOKEN', ''),
        )

        connector = FeishuBitableConnector(config)

        # 测试基础权限（多维表格）
        print("   📊 测试多维表格权限...")
        try:
            tables = connector.list_tables()
            print(f"   ✅ 多维表格访问正常，发现 {len(tables)} 个表格")
        except Exception as e:
            print(f"   ❌ 多维表格访问失败: {e}")
            return False

        # 测试群聊权限
        print("   💬 测试群聊权限...")
        try:
            from feishu_chat_notification import FeishuChatNotifier, ChatNotificationConfig

            chat_config = ChatNotificationConfig(enabled=True)
            notifier = FeishuChatNotifier(config, chat_config)

            chats = notifier.get_bot_chats()
            print(f"   ✅ 群聊访问正常，发现 {len(chats)} 个群聊")

            if len(chats) == 0:
                print("   ⚠️ 机器人尚未加入任何群聊")
                print("   💡 请将机器人添加到需要接收通知的群聊中")

            return True

        except Exception as e:
            error_msg = str(e)
            if "Access denied" in error_msg and ("im:chat" in error_msg or "im:message" in error_msg):
                print("   ❌ 群聊/消息权限不足")
                print("   📋 需要申请的权限:")
                print("      - im:chat:readonly (获取群聊信息)")
                print("      - im:message:send 或 im:message:send_as_bot (发送消息)")
                print("      - im:message (消息管理权限)")

                # 从错误消息中提取权限申请链接
                if "点击链接申请" in error_msg:
                    import re

                    url_match = re.search(r'https://[^\s]+', error_msg)
                    if url_match:
                        print(f"   🔗 快速申请链接: {url_match.group()}")

                return False
            else:
                print(f"   ❌ 群聊测试失败: {e}")
                return False

    except Exception as e:
        print(f"   ❌ 权限检查失败: {e}")
        return False


def generate_permission_application_url():
    """生成权限申请URL"""
    app_id = os.getenv('FEISHU_APP_ID', '')
    if not app_id:
        return None

    required_scopes = ['im:chat:readonly', 'im:message:send_as_bot', 'im:message:send']

    scope_string = ','.join(required_scopes)
    url = f"https://open.feishu.cn/app/{app_id}/auth?q={scope_string}&op_from=openapi&token_type=tenant"

    return url


def show_permission_guide():
    """显示权限申请指南"""
    print("\n📋 权限申请指南:")
    print("=" * 50)

    print("1. 登录飞书开放平台:")
    print("   https://open.feishu.cn/")

    print("\n2. 进入您的应用管理页面")

    print("\n3. 点击 '权限管理' 或 'Permissions'")

    print("\n4. 申请以下权限:")
    print("   ✅ im:chat:readonly - 获取群聊信息")
    print("   ✅ im:message:send_as_bot - 以机器人身份发送消息")
    print("   ✅ im:message:send - 发送消息权限")

    print("\n5. 填写权限申请理由:")
    print("   '用于ArXiv论文更新自动通知，向群聊发送论文推荐信息'")

    print("\n6. 等待审核通过（通常1-3个工作日）")

    print("\n7. 权限通过后，重新获取访问令牌:")
    print("   python get_token.py")

    # 生成快速申请链接
    url = generate_permission_application_url()
    if url:
        print(f"\n🔗 快速申请链接:")
        print(f"   {url}")
        print("   (点击链接可直接跳转到权限申请页面)")


def test_notification_functionality():
    """测试通知功能"""
    print("\n🧪 测试通知功能...")

    try:
        from feishu_chat_notification import FeishuChatNotifier, ChatNotificationConfig
        from feishu_bitable_connector import FeishuBitableConfig

        config = FeishuBitableConfig(
            app_id=os.getenv('FEISHU_APP_ID', ''),
            app_secret=os.getenv('FEISHU_APP_SECRET', ''),
            tenant_access_token=os.getenv('FEISHU_TENANT_ACCESS_TOKEN'),
            user_access_token=os.getenv('FEISHU_USER_ACCESS_TOKEN'),
        )

        chat_config = ChatNotificationConfig(enabled=True, min_papers_threshold=1, max_recommended_papers=1)

        notifier = FeishuChatNotifier(config, chat_config)

        # 模拟测试数据
        test_stats = {"移动操作": {"new_count": 1, "total_count": 10, "table_name": "移动操作论文表"}}

        test_papers = {
            "移动操作": [
                {
                    "title": "Advanced Mobile Manipulation for Autonomous Robots",
                    "authors_str": "张三, 李四, 王五",
                    "relevance_score": 95.5,
                    "arxiv_id": "2409.test123",
                    "paper_url": "http://arxiv.org/abs/2409.test123",
                    "summary": "这是一篇关于移动操作机器人的测试论文摘要...",
                }
            ]
        }

        print("   📤 发送测试通知...")
        success = notifier.notify_paper_updates(test_stats, test_papers)

        if success:
            print("   ✅ 通知功能测试成功！")
            print("   📱 请检查相关群聊是否收到测试消息")
            return True
        else:
            print("   ❌ 通知功能测试失败")
            return False

    except Exception as e:
        print(f"   ❌ 测试过程出错: {e}")
        return False


def show_setup_summary():
    """显示设置摘要"""
    print("\n📋 群聊通知功能设置摘要:")
    print("=" * 50)

    print("✅ 功能特性:")
    print("   - 自动发送论文更新通知到所有群聊")
    print("   - 包含统计信息和推荐论文")
    print("   - 支持富文本和纯文本消息格式")
    print("   - 可配置通知阈值和推荐数量")

    print("\n🔧 配置文件:")
    print("   conf/default.yaml - chat_notification 部分")

    print("\n📚 使用方法:")
    print("   python arxiv_hydra.py --config-name=your_config")
    print("   (有新论文时会自动发送群聊通知)")

    print("\n📖 详细文档:")
    print("   CHAT_NOTIFICATION_GUIDE.md")


def main():
    """主函数"""
    print("🤖 飞书群聊通知权限检查助手")
    print("=" * 50)
    print(f"🕒 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    load_dotenv()

    # 1. 检查环境变量
    env_ok = check_environment_variables()

    if not env_ok:
        print("\n💡 请先运行 setup_feishu.py 配置基础环境变量")
        return

    # 2. 检查API权限
    permissions_ok = check_api_permissions()

    if not permissions_ok:
        print("\n📋 需要申请群聊相关权限")
        show_permission_guide()
        return

    # 3. 测试通知功能
    print("\n🎯 权限检查通过，测试实际功能...")
    notification_ok = test_notification_functionality()

    # 4. 显示设置摘要
    show_setup_summary()

    if notification_ok:
        print("\n🎉 群聊通知功能已完全配置并可正常使用！")
    else:
        print("\n⚠️ 群聊通知功能配置完成，但测试发送失败")
        print("💡 可能的原因:")
        print("   - 机器人尚未加入任何群聊")
        print("   - 群聊中机器人没有发言权限")
        print("   - 网络连接问题")


if __name__ == "__main__":
    main()
