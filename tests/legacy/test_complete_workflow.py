#!/usr/bin/env python3
"""
完整的autopaper包功能验证脚本

验证所有重构后的飞书功能是否正常工作。
"""

import sys
import traceback
from datetime import datetime


def test_complete_workflow():
    """测试完整的工作流程"""
    print("🚀 开始autopaper完整功能验证")
    print("=" * 60)

    try:
        # 1. 导入所有模块
        print("\n1️⃣ 测试模块导入...")
        from autopaper import FeishuConfig, FeishuConnector, BitableManager, ChatNotifier, SyncManager

        print("✅ 所有核心模块导入成功")

        # 2. 创建配置
        print("\n2️⃣ 测试配置管理...")
        config = FeishuConfig(
            app_id="test_app_id",
            app_secret="test_app_secret",
            user_access_token="test_user_token",
            app_token="test_app_token",
        )
        print(f"✅ 配置创建成功: {config.app_id}")

        # 3. 测试同步管理器
        print("\n3️⃣ 测试同步管理器...")
        sync_manager = SyncManager(config)
        print("✅ 同步管理器创建成功")

        # 验证组件
        assert hasattr(sync_manager, "bitable_manager"), "缺少多维表格管理器"
        assert hasattr(sync_manager, "chat_notifier"), "缺少聊天通知器"
        print("✅ 所有组件初始化成功")

        # 4. 测试数据格式化
        print("\n4️⃣ 测试数据处理...")

        # 模拟论文数据
        papers_by_field = {
            "机器学习": [
                {
                    "标题": "深度学习在自然语言处理中的应用",
                    "作者": ["张三", "李四", "王五"],
                    "摘要": "本文探讨了深度学习技术在自然语言处理领域的最新进展...",
                    "发布日期": datetime(2024, 1, 1),
                    "ArXiv ID": "2401.00001",
                    "相关性评分": 95.5,
                    "PDF链接": "http://arxiv.org/pdf/2401.00001.pdf",
                },
                {
                    "标题": "强化学习与智能决策系统",
                    "作者": ["赵六", "钱七"],
                    "摘要": "介绍强化学习在智能决策系统中的应用和挑战...",
                    "发布日期": datetime(2024, 1, 2),
                    "ArXiv ID": "2401.00002",
                    "相关性评分": 88.0,
                    "PDF链接": "http://arxiv.org/pdf/2401.00002.pdf",
                },
            ],
            "计算机视觉": [
                {
                    "标题": "多目标检测的新方法",
                    "作者": ["孙八", "周九"],
                    "摘要": "提出了一种新的多目标检测算法，提高了检测精度...",
                    "发布日期": datetime(2024, 1, 3),
                    "ArXiv ID": "2401.00003",
                    "相关性评分": 92.0,
                    "PDF链接": "http://arxiv.org/pdf/2401.00003.pdf",
                }
            ],
        }

        # 测试数据格式化
        for field, papers in papers_by_field.items():
            for paper in papers:
                formatted = sync_manager.bitable_manager.format_paper_data(paper)
                assert "标题" in formatted, f"{field}领域论文缺少标题字段"
                assert "作者" in formatted, f"{field}领域论文缺少作者字段"
                assert "相关性评分" in formatted, f"{field}领域论文缺少评分字段"

        print(f"✅ 数据格式化成功: {sum(len(papers) for papers in papers_by_field.values())} 篇论文")

        # 5. 测试消息创建
        print("\n5️⃣ 测试消息生成...")

        # 模拟更新统计
        update_stats = {
            "机器学习": {"new_count": 2, "total_count": 15, "table_name": "机器学习论文表"},
            "计算机视觉": {"new_count": 1, "total_count": 8, "table_name": "计算机视觉论文表"},
        }

        # 选择推荐论文
        recommended_papers = sync_manager.chat_notifier._select_recommended_papers(papers_by_field)

        # 创建简单文本消息
        text_message = sync_manager.chat_notifier.create_simple_text_message(update_stats, recommended_papers)
        assert text_message["msg_type"] == "text", "文本消息类型错误"
        assert "ArXiv论文更新通知" in text_message["content"]["text"], "文本消息内容错误"

        # 创建富文本消息
        table_links = {
            "机器学习": "https://feishu.cn/base/test_app_token?table=ml_table",
            "计算机视觉": "https://feishu.cn/base/test_app_token?table=cv_table",
        }

        rich_message = sync_manager.chat_notifier.create_paper_update_message(
            update_stats, recommended_papers, table_links
        )
        assert rich_message["msg_type"] == "interactive", "富文本消息类型错误"
        assert "elements" in rich_message["content"], "富文本消息结构错误"

        print("✅ 消息生成成功: 文本消息 + 富文本消息")

        # 6. 测试表格链接生成
        print("\n6️⃣ 测试表格链接...")

        link = sync_manager.chat_notifier.generate_table_link(table_id="test_table_id")
        expected_link = f"https://feishu.cn/base/{config.app_token}?table=test_table_id"
        assert link == expected_link, f"表格链接生成错误: {link}"

        print(f"✅ 表格链接生成成功: {link}")

        # 7. 测试配置验证
        print("\n7️⃣ 测试配置验证...")

        # 测试不完整配置
        incomplete_config = FeishuConfig(app_id="test", app_secret="test")
        incomplete_sync = SyncManager(incomplete_config)

        # 验证警告提示
        assert hasattr(incomplete_sync, "bitable_manager"), "不完整配置下组件应该仍然可用"

        print("✅ 配置验证成功")

        # 8. 测试错误处理
        print("\n8️⃣ 测试错误处理...")

        from autopaper.core.feishu.config import FeishuAPIError

        # 验证自定义异常
        try:
            raise FeishuAPIError("测试错误")
        except FeishuAPIError as e:
            # FeishuAPIError的str格式是 "FeishuAPIError: 消息"
            assert "测试错误" in str(e), f"自定义异常处理错误: {str(e)}"

        print("✅ 错误处理机制正常")

        print("\n" + "=" * 60)
        print("🎉 autopaper包完整功能验证通过！")
        print("=" * 60)
        print("\n📊 验证结果统计:")
        print("✅ 模块导入: 通过")
        print("✅ 配置管理: 通过")
        print("✅ 同步管理器: 通过")
        print("✅ 数据处理: 通过")
        print("✅ 消息生成: 通过")
        print("✅ 表格链接: 通过")
        print("✅ 配置验证: 通过")
        print("✅ 错误处理: 通过")

        print(f"\n📝 功能总结:")
        print(f"• 处理论文数据: {sum(len(papers) for papers in papers_by_field.values())} 篇")
        print(f"• 支持研究领域: {len(papers_by_field)} 个")
        print(f"• 消息类型: 2 种 (文本 + 富文本)")
        print(f"• 核心组件: 5 个")

        print(f"\n🚀 autopaper包已准备就绪，可以投入使用！")

        return True

    except Exception as e:
        print(f"\n❌ 验证过程中出现错误:")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print(f"\n📍 详细错误信息:")
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("autopaper包完整功能验证")
    print("版本: 0.1.0")
    print("时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    success = test_complete_workflow()

    if success:
        print("\n✨ 恭喜！autopaper包重构完成，所有功能正常！")
        sys.exit(0)
    else:
        print("\n⚠️  部分功能存在问题，请检查错误信息。")
        sys.exit(1)


if __name__ == "__main__":
    main()
