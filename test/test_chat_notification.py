#!/usr/bin/env python3
"""
测试飞书群聊通知功能
"""

import os
import sys
from dotenv import load_dotenv

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_chat_notification():
    """测试群聊通知功能"""
    load_dotenv()

    try:
        from feishu_chat_notification import FeishuChatNotifier, ChatNotificationConfig
        from feishu_bitable_connector import FeishuBitableConfig

        print("🧪 开始测试飞书群聊通知功能...")

        # 创建配置
        config = FeishuBitableConfig(
            app_id=os.getenv('FEISHU_APP_ID', ''),
            app_secret=os.getenv('FEISHU_APP_SECRET', ''),
            tenant_access_token=os.getenv('FEISHU_TENANT_ACCESS_TOKEN'),
            user_access_token=os.getenv('FEISHU_USER_ACCESS_TOKEN'),
        )

        chat_config = ChatNotificationConfig(enabled=True, min_papers_threshold=1, max_recommended_papers=1)

        # 创建通知器
        notifier = FeishuChatNotifier(config, chat_config)

        # 测试获取群聊列表
        print("\n📋 测试获取群聊列表...")
        chats = notifier.get_bot_chats()

        if not chats:
            print("❌ 没有找到机器人参与的群聊")
            print("💡 请确保：")
            print("   1. 机器人已添加到至少一个群聊中")
            print("   2. 机器人有发送消息的权限")
            print("   3. access_token有效且权限充足")
            return False

        # 测试发送通知消息
        print(f"\n📤 测试发送通知消息到 {len(chats)} 个群聊...")

        # 模拟更新数据
        test_stats = {"移动操作": {"new_count": 3, "total_count": 15, "table_name": "移动操作论文表"}}

        test_papers = {
            "移动操作": [
                {
                    "title": "M4Diffuser: Multi-View Diffusion Policy with Manipulability-Aware Control for Robust Mobile Manipulation",
                    "authors_str": "Ju Dong, Lei Zhang, Liding Zhang, Yao Ling, Yu Fu",
                    "relevance_score": 407.64,
                    "arxiv_id": "2509.14980",
                    "paper_url": "http://arxiv.org/abs/2509.14980v1",
                    "summary": "Mobile manipulation requires the coordinated control of a mobile base and a robotic arm while simultaneously perceiving both global scene context and fine-grained object details...",
                }
            ]
        }

        # 发送测试通知
        success = notifier.notify_paper_updates(test_stats, test_papers)

        if success:
            print("✅ 群聊通知功能测试成功！")
            print("📝 请检查相关群聊是否收到了测试消息")
            return True
        else:
            print("❌ 群聊通知功能测试失败")
            return False

    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("💡 请确保所有依赖模块都已正确安装")
        return False

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback

        print(f"🔍 详细错误信息：")
        traceback.print_exc()
        return False


def test_chat_configuration():
    """测试聊天配置加载"""
    print("\n🔧 测试配置加载...")

    try:
        import hydra
        from omegaconf import DictConfig, OmegaConfig

        # 简单的配置测试
        test_config = {
            'feishu': {
                'api': {'app_id': 'test_app_id', 'app_secret': 'test_app_secret', 'tenant_access_token': 'test_token'},
                'chat_notification': {'enabled': True, 'min_papers_threshold': 2, 'max_recommended_papers': 1},
            }
        }

        from feishu_chat_notification import create_chat_notifier_from_config

        # 这应该不会出错（虽然token是假的）
        try:
            notifier = create_chat_notifier_from_config(test_config)
            print("✅ 配置加载测试成功")
            return True
        except Exception as e:
            if "有效的访问令牌" in str(e):
                print("✅ 配置验证正常工作（检测到无效token）")
                return True
            else:
                raise e

    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False


if __name__ == "__main__":
    print("🚀 飞书群聊通知功能测试")
    print("=" * 50)

    # 检查环境变量
    required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET']
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ 缺少必要的环境变量: {', '.join(missing_vars)}")
        print("💡 请先运行 setup_feishu.py 配置飞书应用信息")
        sys.exit(1)

    # 检查访问令牌
    has_user_token = bool(os.getenv('FEISHU_USER_ACCESS_TOKEN')) and 'xxxx' not in os.getenv(
        'FEISHU_USER_ACCESS_TOKEN', ''
    )
    has_tenant_token = bool(os.getenv('FEISHU_TENANT_ACCESS_TOKEN')) and 'xxxx' not in os.getenv(
        'FEISHU_TENANT_ACCESS_TOKEN', ''
    )

    if not has_user_token and not has_tenant_token:
        print("❌ 没有有效的访问令牌")
        print("💡 请确保设置了 FEISHU_USER_ACCESS_TOKEN 或 FEISHU_TENANT_ACCESS_TOKEN")
        sys.exit(1)

    # 运行测试
    config_success = test_chat_configuration()

    if config_success:
        notification_success = test_chat_notification()

        if notification_success:
            print("\n🎉 所有测试通过！群聊通知功能可正常使用")
        else:
            print("\n⚠️ 通知功能测试失败，请检查配置和权限")
    else:
        print("\n❌ 配置测试失败")
