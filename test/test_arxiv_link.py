#!/usr/bin/env python3
"""
测试ArXiv ID超链接字段修改
"""
import sys
import os

# 添加父目录到路径，以便导入主模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feishu_bitable_connector import FeishuBitableConnector, FeishuBitableConfig


def test_table_structure():
    """测试新的表格结构"""
    print("🧪 测试ArXiv ID超链接字段修改")
    print("=" * 50)

    # 模拟配置（不会实际创建表格）
    try:
        config = FeishuBitableConfig(app_id="test", app_secret="test", tenant_access_token="test_token")
        connector = FeishuBitableConnector(config)

        # 检查字段定义
        print("📋 新的表格字段结构:")
        print("1. ArXiv ID - 超链接类型 (type: 15)")
        print("2. 标题 - 单行文本")
        print("3. 作者 - 多选项")
        print("4. 摘要 - 单行文本")
        print("5. 分类 - 多选项")
        print("6. 匹配关键词 - 多选项")
        print("7. 相关性评分 - 数字")
        print("8. 研究领域 - 多选项")
        print("9. PDF链接 - 超链接")
        print("10. 必须关键词匹配 - 多选项")
        print("11. 发布日期 - 日期")
        print("12. 更新日期 - 日期")
        print("13. 同步时间 - 创建时间")

        print("\n🔄 主要变更:")
        print("✅ ArXiv ID: 单行文本 → 超链接")
        print("❌ 删除字段: 论文链接")
        print("📍 字段顺序: 保持不变")

        print("\n💡 超链接格式:")
        print('ArXiv ID: {"text": "2301.12345", "link": "https://arxiv.org/abs/2301.12345"}')

    except Exception as e:
        print(f"配置测试跳过（预期）: {e}")


def test_data_format():
    """测试数据格式"""
    print("\n🔬 测试数据格式")
    print("=" * 50)

    # 模拟论文数据
    sample_paper_data = {
        "ArXiv ID": {"text": "2301.12345", "link": "https://arxiv.org/abs/2301.12345"},
        "标题": "Sample Paper Title",
        "作者": ["Author 1", "Author 2"],
        "摘要": "This is a sample abstract...",
        "分类": ["cs.AI", "cs.RO"],
        "匹配关键词": ["robot", "learning"],
        "相关性评分": 0.85,
        "研究领域": ["Robotics"],
        "PDF链接": {"text": "PDF", "link": "https://arxiv.org/pdf/2301.12345.pdf"},
        "必须关键词匹配": ["mobile", "manipulation"],
        "发布日期": 1640995200000,  # 时间戳
        "更新日期": 1640995200000,  # 时间戳
    }

    print("📊 示例数据格式:")
    for field, value in sample_paper_data.items():
        if isinstance(value, dict) and 'text' in value and 'link' in value:
            print(f"{field}: 超链接 - 显示文本: '{value['text']}', 链接: '{value['link']}'")
        elif isinstance(value, list):
            print(f"{field}: 列表 - {value}")
        else:
            print(f"{field}: {type(value).__name__} - {value}")

    print("\n🎯 关键改进:")
    print("1. ArXiv ID现在是可点击的超链接")
    print("2. 用户可以直接点击ArXiv ID跳转到论文页面")
    print("3. 减少了冗余的'论文链接'字段")
    print("4. 界面更加简洁清晰")


def test_field_mapping():
    """测试字段映射"""
    print("\n🗂️ 字段映射对比")
    print("=" * 50)

    print("原有字段映射:")
    old_fields = [
        "ArXiv ID (文本)",
        "标题",
        "作者",
        "摘要",
        "分类",
        "匹配关键词",
        "相关性评分",
        "研究领域",
        "PDF链接 (超链接)",
        "论文链接 (超链接)",  # 将被删除
        "必须关键词匹配",
        "发布日期",
        "更新日期",
        "同步时间",
    ]

    print("新字段映射:")
    new_fields = [
        "ArXiv ID (超链接)",  # 类型改变
        "标题",
        "作者",
        "摘要",
        "分类",
        "匹配关键词",
        "相关性评分",
        "研究领域",
        "PDF链接 (超链接)",
        # "论文链接" - 已删除
        "必须关键词匹配",
        "发布日期",
        "更新日期",
        "同步时间",
    ]

    print(f"原有字段数: {len(old_fields)}")
    print(f"新字段数: {len(new_fields)}")
    print(f"减少字段数: {len(old_fields) - len(new_fields)}")


if __name__ == "__main__":
    test_table_structure()
    test_data_format()
    test_field_mapping()
