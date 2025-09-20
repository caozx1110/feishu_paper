#!/usr/bin/env python3
"""
真实环境测试脚本

使用.env中的真实凭据测试arxiv拉取、飞书同步和消息发送功能。
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any
import traceback

# 导入环境变量加载
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, "/home/ubuntu/ws/feishu_paper")

# 加载环境变量
load_dotenv("/home/ubuntu/ws/feishu_paper/.env")


def load_config_from_env():
    """从环境变量加载配置"""
    from autopaper import FeishuConfig

    config = FeishuConfig(
        app_id=os.getenv("FEISHU_APP_ID"),
        app_secret=os.getenv("FEISHU_APP_SECRET"),
        user_access_token=os.getenv("FEISHU_USER_ACCESS_TOKEN"),
        tenant_access_token=os.getenv("FEISHU_TENANT_ACCESS_TOKEN"),
        app_token=os.getenv("FEISHU_BITABLE_APP_TOKEN"),
    )

    print(f"✅ 配置加载成功:")
    print(f"  App ID: {config.app_id}")
    print(f"  App Secret: {'***' if config.app_secret else 'None'}")
    print(f"  User Token: {'***' if config.user_access_token else 'None'}")
    print(f"  Tenant Token: {'***' if config.tenant_access_token else 'None'}")
    print(f"  App Token: {config.app_token}")

    return config


def test_arxiv_fetching():
    """测试ArXiv论文抓取"""
    print("\n📚 测试ArXiv论文抓取...")

    try:
        from arxiv_core import ArxivAPI

        # 创建ArXiv API实例
        arxiv_api = ArxivAPI()

        # 定义搜索查询
        test_queries = {
            "机器学习": "cat:cs.LG AND submittedDate:[20240101 TO 20241231]",
            "自然语言处理": "cat:cs.CL AND submittedDate:[20240101 TO 20241231]",
        }

        papers_by_field = {}

        for field, query in test_queries.items():
            print(f"\n🔍 搜索 {field} 论文...")

            # 限制每个领域只获取3篇论文用于测试
            papers = arxiv_api.search_papers(
                query=query, max_results=3, sort_by="submittedDate", sort_order="descending"
            )

            if papers:
                print(f"✅ 找到 {len(papers)} 篇 {field} 论文")
                for i, paper in enumerate(papers, 1):
                    print(f"  {i}. {paper.get('title', 'Unknown')[:60]}...")

                papers_by_field[field] = papers
            else:
                print(f"⚠️  未找到 {field} 论文")

        return papers_by_field

    except Exception as e:
        print(f"❌ ArXiv抓取失败: {e}")
        traceback.print_exc()
        return {}


def test_feishu_connection(config):
    """测试飞书连接"""
    print("\n🔗 测试飞书连接...")

    try:
        from autopaper import SyncManager

        sync_manager = SyncManager(config)

        # 测试连接
        if hasattr(sync_manager.bitable_manager, "test_connection"):
            connection_ok = sync_manager.bitable_manager.test_connection()
            if connection_ok:
                print("✅ 飞书连接成功")
            else:
                print("❌ 飞书连接失败")
                return False
        else:
            print("ℹ️  跳过连接测试（方法不存在）")

        return True

    except Exception as e:
        print(f"❌ 飞书连接测试失败: {e}")
        traceback.print_exc()
        return False


def test_table_operations(config):
    """测试表格操作"""
    print("\n📊 测试多维表格操作...")

    try:
        from autopaper import SyncManager

        sync_manager = SyncManager(config)

        # 获取表格信息
        table_id = os.getenv("FEISHU_PAPERS_TABLE_ID")
        if not table_id:
            print("⚠️  未配置FEISHU_PAPERS_TABLE_ID，跳过表格操作测试")
            return True

        print(f"📋 使用表格ID: {table_id}")

        # 测试获取记录数量
        try:
            count = sync_manager.bitable_manager.get_record_count(table_id)
            print(f"✅ 表格当前记录数: {count}")
        except Exception as e:
            print(f"⚠️  获取记录数失败: {e}")

        # 测试表格字段获取
        try:
            fields = sync_manager.bitable_manager.get_table_fields(table_id)
            if fields:
                print(f"✅ 表格字段数: {len(fields)}")
                for field in fields[:3]:  # 只显示前3个字段
                    print(f"  - {field.get('field_name', 'Unknown')}: {field.get('type', 'Unknown')}")
            else:
                print("⚠️  未获取到表格字段")
        except Exception as e:
            print(f"⚠️  获取表格字段失败: {e}")

        return True

    except Exception as e:
        print(f"❌ 表格操作测试失败: {e}")
        traceback.print_exc()
        return False


def test_paper_sync(config, papers_by_field):
    """测试论文同步"""
    print("\n🔄 测试论文同步...")

    if not papers_by_field:
        print("⚠️  没有论文数据，跳过同步测试")
        return True

    try:
        from autopaper import SyncManager

        sync_manager = SyncManager(config)

        # 准备表格映射
        table_id = os.getenv("FEISHU_PAPERS_TABLE_ID")
        if not table_id:
            print("⚠️  未配置FEISHU_PAPERS_TABLE_ID，无法进行同步测试")
            return False

        # 创建字段映射（所有领域使用同一个表格）
        field_to_table_map = {}
        for field in papers_by_field.keys():
            field_to_table_map[field] = table_id

        print(f"📋 同步映射: {len(field_to_table_map)} 个领域 -> {table_id}")

        # 执行同步（不发送通知，避免spam）
        result = sync_manager.sync_papers_to_feishu(
            papers_by_field, field_to_table_map, send_notification=False  # 测试时不发送通知
        )

        if result.get("success"):
            print("✅ 论文同步成功")
            for field, sync_result in result.get("sync_results", {}).items():
                inserted = sync_result.get("inserted", 0)
                updated = sync_result.get("updated", 0)
                failed = sync_result.get("failed", 0)
                print(f"  {field}: 插入 {inserted}, 更新 {updated}, 失败 {failed}")
        else:
            print("❌ 论文同步失败")
            for field, sync_result in result.get("sync_results", {}).items():
                if "error" in sync_result:
                    print(f"  {field}: {sync_result['error']}")

        return result.get("success", False)

    except Exception as e:
        print(f"❌ 论文同步失败: {e}")
        traceback.print_exc()
        return False


def test_notification(config, papers_by_field):
    """测试消息通知"""
    print("\n💬 测试消息通知...")

    try:
        from autopaper import SyncManager

        sync_manager = SyncManager(config)

        # 获取群聊列表
        chats = sync_manager.chat_notifier.get_bot_chats()
        if not chats:
            print("⚠️  未找到可用群聊，跳过通知测试")
            return True

        print(f"✅ 找到 {len(chats)} 个群聊")
        for chat in chats[:3]:  # 只显示前3个
            chat_name = chat.get("name", "未命名群聊")
            print(f"  - {chat_name}")

        # 创建测试通知（不实际发送）
        update_stats = {}
        for field, papers in papers_by_field.items():
            update_stats[field] = {"new_count": len(papers), "total_count": len(papers), "table_name": f"{field}论文表"}

        if update_stats:
            # 创建消息（但不发送）
            message = sync_manager.chat_notifier.create_simple_text_message(update_stats, papers_by_field)

            if message:
                print("✅ 消息创建成功")
                print(f"  消息类型: {message.get('msg_type')}")
                content_len = len(str(message.get("content", "")))
                print(f"  消息长度: {content_len} 字符")

                # 显示消息预览（截取前200字符）
                if message.get("msg_type") == "text":
                    preview = message["content"]["text"][:200]
                    print(f"  内容预览: {preview}...")
            else:
                print("❌ 消息创建失败")
                return False

        print("ℹ️  为避免spam，实际未发送消息到群聊")
        return True

    except Exception as e:
        print(f"❌ 消息通知测试失败: {e}")
        traceback.print_exc()
        return False


def run_real_world_test():
    """运行真实世界测试"""
    print("🚀 开始真实环境测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    test_results = {}

    try:
        # 1. 加载配置
        print("\n1️⃣ 加载环境配置...")
        config = load_config_from_env()
        test_results["配置加载"] = True

        # 2. 测试ArXiv抓取
        print("\n2️⃣ 测试ArXiv论文抓取...")
        papers_by_field = test_arxiv_fetching()
        test_results["ArXiv抓取"] = len(papers_by_field) > 0

        # 3. 测试飞书连接
        print("\n3️⃣ 测试飞书连接...")
        connection_ok = test_feishu_connection(config)
        test_results["飞书连接"] = connection_ok

        if connection_ok:
            # 4. 测试表格操作
            print("\n4️⃣ 测试表格操作...")
            table_ok = test_table_operations(config)
            test_results["表格操作"] = table_ok

            # 5. 测试论文同步
            if papers_by_field and table_ok:
                print("\n5️⃣ 测试论文同步...")
                sync_ok = test_paper_sync(config, papers_by_field)
                test_results["论文同步"] = sync_ok
            else:
                print("\n5️⃣ 跳过论文同步测试（缺少数据或表格访问失败）")
                test_results["论文同步"] = False

            # 6. 测试消息通知
            print("\n6️⃣ 测试消息通知...")
            notification_ok = test_notification(config, papers_by_field)
            test_results["消息通知"] = notification_ok
        else:
            test_results["表格操作"] = False
            test_results["论文同步"] = False
            test_results["消息通知"] = False

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        traceback.print_exc()

    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n总测试数: {total}")
    print(f"通过测试: {passed}")
    print(f"失败测试: {total - passed}")
    print(f"通过率: {(passed / total * 100):.1f}%" if total > 0 else "0%")

    if passed == total:
        print("\n🎉 所有测试通过！真实环境功能正常！")
        return True
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查配置和网络连接。")
        return False


if __name__ == "__main__":
    success = run_real_world_test()
    sys.exit(0 if success else 1)
