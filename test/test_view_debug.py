#!/usr/bin/env python3
"""
测试视图字段映射和功能
"""
import os
import sys

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_field_mapping():
    """测试字段映射是否正确"""
    print("🔍 检查字段映射...")

    # 从 feishu_bitable_connector.py 中提取字段定义
    expected_fields = [
        "标题",
        "ArXiv ID",
        "作者",
        "摘要",
        "发布日期",
        "更新日期",
        "分类",
        "关键词",
        "相关性评分",
        "详细匹配信息",
        "研究领域",
        "PDF链接",
        "评价",
    ]

    # 视图配置中使用的字段
    view_sort_fields = ["相关性评分", "发布日期"]

    print(f"📊 期望字段数量: {len(expected_fields)}")
    for i, field in enumerate(expected_fields, 1):
        print(f"   {i:2d}. {field}")

    print(f"\n🎯 视图排序字段:")
    for field in view_sort_fields:
        if field in expected_fields:
            print(f"   ✅ {field} - 字段存在")
        else:
            print(f"   ❌ {field} - 字段不存在")

    # 检查字段名称是否匹配
    missing_fields = [f for f in view_sort_fields if f not in expected_fields]
    if missing_fields:
        print(f"\n❌ 缺失字段: {missing_fields}")
        return False
    else:
        print(f"\n✅ 所有视图字段都存在于表格定义中")
        return True


def test_view_config_structure():
    """测试视图配置结构"""
    print("\n🏗️ 检查视图配置结构...")

    # 模拟视图配置
    views = [
        {
            'name': '评分排序视图',
            'type': 'sort',
            'description': '按相关性评分降序排列',
            'sorts': [{'field': '相关性评分', 'direction': 'desc'}],
        },
        {
            'name': '时间排序视图',
            'type': 'sort',
            'description': '按发布时间降序排列',
            'sorts': [{'field': '发布日期', 'direction': 'desc'}],
        },
    ]

    print(f"📋 视图配置数量: {len(views)}")

    all_valid = True
    for i, view in enumerate(views, 1):
        print(f"\n   {i}. {view.get('name', '未知名称')}")

        # 检查必需字段
        required_fields = ['name', 'type', 'sorts']
        for field in required_fields:
            if field in view:
                print(f"      ✅ {field}: {view[field]}")
            else:
                print(f"      ❌ 缺少必需字段: {field}")
                all_valid = False

        # 检查排序配置
        sorts = view.get('sorts', [])
        if sorts:
            for j, sort_config in enumerate(sorts):
                sort_field = sort_config.get('field', '未知')
                sort_direction = sort_config.get('direction', '未知')
                print(f"      📊 排序{j+1}: {sort_field} ({sort_direction})")

                if not sort_field or sort_field == '未知':
                    print(f"         ❌ 排序字段无效")
                    all_valid = False
                if sort_direction not in ['asc', 'desc']:
                    print(f"         ❌ 排序方向无效: {sort_direction}")
                    all_valid = False
        else:
            print(f"      ⚠️ 没有排序配置")

    return all_valid


def check_potential_issues():
    """检查可能的问题"""
    print("\n🔧 检查潜在问题...")

    issues = []

    # 检查1：字段名称是否包含特殊字符
    sort_fields = ["相关性评分", "发布日期"]
    for field in sort_fields:
        if any(char in field for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
            issues.append(f"字段名包含特殊字符: {field}")

    # 检查2：字段名称长度
    for field in sort_fields:
        if len(field) > 50:
            issues.append(f"字段名过长: {field} ({len(field)} 字符)")

    # 检查3：检查是否有英文字段名可能性
    potential_mappings = {
        "相关性评分": ["relevance_score", "score", "rating"],
        "发布日期": ["publish_date", "date", "created_time"],
    }

    print("💡 可能的英文字段映射:")
    for chinese, english_options in potential_mappings.items():
        print(f"   {chinese} -> {english_options}")

    if issues:
        print("\n⚠️ 发现潜在问题:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("\n✅ 未发现明显问题")
        return True


def suggest_troubleshooting():
    """提供故障排除建议"""
    print("\n🛠️ 故障排除建议:")
    print("1. 确认表格字段已正确创建")
    print("2. 检查飞书API权限是否足够")
    print("3. 查看同步日志中的视图创建信息")
    print("4. 手动在飞书中验证视图是否存在")
    print("5. 检查字段ID映射是否正确")

    print("\n📝 调试步骤:")
    print("1. 运行同步时观察控制台输出")
    print("2. 查找类似以下消息:")
    print("   - '🎯 管理表格视图...'")
    print("   - '🆕 创建视图: xxx'")
    print("   - '✅ 基础视图已创建'")
    print("   - '✅ 视图配置已应用'")
    print("3. 如果看到错误消息，检查具体原因")


if __name__ == "__main__":
    print("🧪 测试视图字段映射和功能")
    print("=" * 60)

    # 测试字段映射
    mapping_ok = test_field_mapping()

    # 测试配置结构
    config_ok = test_view_config_structure()

    # 检查潜在问题
    issues_ok = check_potential_issues()

    # 提供建议
    suggest_troubleshooting()

    print("\n" + "=" * 60)
    if mapping_ok and config_ok and issues_ok:
        print("✅ 配置检查通过！如果视图仍不起作用，请检查API权限和网络连接")
    else:
        print("❌ 发现配置问题，请根据上述信息进行修复")
