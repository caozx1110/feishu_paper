#!/usr/bin/env python3
"""
简单的飞书功能测试脚本

直接运行基本的功能测试验证。
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, "/home/ubuntu/ws/feishu_paper")


def test_imports():
    """测试所有模块导入"""
    print("📦 测试模块导入...")

    try:
        from autopaper.core.feishu.config import FeishuConfig, FeishuAPIError, FieldType

        print("✅ 配置模块导入成功")
    except ImportError as e:
        print(f"❌ 配置模块导入失败: {e}")
        return False

    try:
        from autopaper.core.feishu.connector import FeishuConnector

        print("✅ 连接器模块导入成功")
    except ImportError as e:
        print(f"❌ 连接器模块导入失败: {e}")
        return False

    try:
        from autopaper.core.feishu.bitable import BitableManager

        print("✅ 多维表格模块导入成功")
    except ImportError as e:
        print(f"❌ 多维表格模块导入失败: {e}")
        return False

    try:
        from autopaper.core.feishu.notification import ChatNotifier, ChatNotificationConfig

        print("✅ 通知模块导入成功")
    except ImportError as e:
        print(f"❌ 通知模块导入失败: {e}")
        return False

    try:
        from autopaper.core.feishu.sync import SyncManager

        print("✅ 同步管理器模块导入成功")
    except ImportError as e:
        print(f"❌ 同步管理器模块导入失败: {e}")
        return False

    return True


def test_config_creation():
    """测试配置创建"""
    print("\n⚙️  测试配置创建...")

    try:
        from autopaper.core.feishu.config import FeishuConfig

        # 测试基本配置
        config = FeishuConfig(app_id="test_app_id", app_secret="test_app_secret")
        print(f"✅ 基本配置创建成功: {config.app_id}")

        # 测试完整配置
        full_config = FeishuConfig(
            app_id="test_app_id",
            app_secret="test_app_secret",
            user_access_token="test_user_token",
            app_token="test_app_token",
        )
        print(f"✅ 完整配置创建成功: {full_config.app_token}")

        return True
    except Exception as e:
        print(f"❌ 配置创建失败: {e}")
        return False


def test_manager_creation():
    """测试管理器创建"""
    print("\n🔧 测试管理器创建...")

    try:
        from autopaper.core.feishu.config import FeishuConfig
        from autopaper.core.feishu.sync import SyncManager

        config = FeishuConfig(
            app_id="test_app_id",
            app_secret="test_app_secret",
            user_access_token="test_user_token",
            app_token="test_app_token",
        )

        # 创建同步管理器
        sync_manager = SyncManager(config)
        print("✅ 同步管理器创建成功")

        # 验证组件
        if hasattr(sync_manager, "bitable_manager"):
            print("✅ 多维表格管理器初始化成功")
        else:
            print("❌ 多维表格管理器初始化失败")
            return False

        if hasattr(sync_manager, "chat_notifier"):
            print("✅ 聊天通知器初始化成功")
        else:
            print("❌ 聊天通知器初始化失败")
            return False

        return True
    except Exception as e:
        print(f"❌ 管理器创建失败: {e}")
        return False


def test_data_formatting():
    """测试数据格式化"""
    print("\n📊 测试数据格式化...")

    try:
        from autopaper.core.feishu.config import FeishuConfig
        from autopaper.core.feishu.bitable import BitableManager

        config = FeishuConfig(app_id="test_app_id", app_secret="test_app_secret")

        bitable = BitableManager(config)

        # 测试论文数据格式化
        from datetime import datetime

        paper_data = {
            "标题": "测试论文标题",
            "作者": ["作者1", "作者2"],
            "摘要": "这是一个测试论文的摘要",
            "发布日期": datetime(2024, 1, 1),
            "ArXiv ID": "2401.00001",
            "相关性评分": 95.5,
        }

        formatted_data = bitable.format_paper_data(paper_data)
        print(f"✅ 论文数据格式化成功: {len(formatted_data)} 个字段")

        # 验证必要字段
        required_fields = ["标题", "作者", "摘要", "发布日期", "ArXiv ID", "相关性评分"]
        for field in required_fields:
            if field in formatted_data:
                print(f"  ✓ {field}: {formatted_data[field]}")
            else:
                print(f"  ✗ 缺少字段: {field}")
                return False

        return True
    except Exception as e:
        print(f"❌ 数据格式化失败: {e}")
        return False


def test_message_creation():
    """测试消息创建"""
    print("\n💬 测试消息创建...")

    try:
        from autopaper.core.feishu.config import FeishuConfig
        from autopaper.core.feishu.notification import ChatNotifier

        config = FeishuConfig(app_id="test_app_id", app_secret="test_app_secret", app_token="test_app_token")

        notifier = ChatNotifier(config)

        # 测试简单文本消息
        update_stats = {"机器学习": {"new_count": 3, "total_count": 15, "table_name": "机器学习论文表"}}

        recommended_papers = {"机器学习": [{"title": "测试论文", "authors_str": "测试作者", "relevance_score": 90.0}]}

        message = notifier.create_simple_text_message(update_stats, recommended_papers)
        print("✅ 简单文本消息创建成功")
        print(f"  消息类型: {message['msg_type']}")
        print(f"  包含内容: {'ArXiv论文更新通知' in message['content']['text']}")

        # 测试富文本消息
        table_links = {"机器学习": "https://test.link"}
        rich_message = notifier.create_paper_update_message(update_stats, recommended_papers, table_links)
        print("✅ 富文本消息创建成功")
        print(f"  消息类型: {rich_message['msg_type']}")

        return True
    except Exception as e:
        print(f"❌ 消息创建失败: {e}")
        return False


def run_basic_tests():
    """运行基本功能测试"""
    print("🚀 开始autopaper飞书功能基本测试")
    print("=" * 50)

    tests = [
        ("模块导入", test_imports),
        ("配置创建", test_config_creation),
        ("管理器创建", test_manager_creation),
        ("数据格式化", test_data_formatting),
        ("消息创建", test_message_creation),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {test_name} 测试通过")
            else:
                print(f"\n❌ {test_name} 测试失败")
        except Exception as e:
            print(f"\n❌ {test_name} 测试出错: {e}")

    print("\n" + "=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)
    print(f"总测试数: {total}")
    print(f"通过测试: {passed}")
    print(f"失败测试: {total - passed}")
    print(f"通过率: {(passed / total * 100):.1f}%")

    if passed == total:
        print("\n🎉 所有基本功能测试通过！autopaper包重构成功！")
        return True
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查相关功能。")
        return False


if __name__ == "__main__":
    success = run_basic_tests()
    sys.exit(0 if success else 1)
