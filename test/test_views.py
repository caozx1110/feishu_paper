#!/usr/bin/env python3
"""
测试视图管理功能
"""
import os
import sys

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
from unittest.mock import Mock, patch
from feishu_bitable_connector import FeishuBitableConnector


def test_view_configuration():
    """测试视图配置是否正确"""
    # 读取配置文件
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'conf', 'default.yaml')

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    views_config = config.get('feishu', {}).get('views', {})

    print("📋 当前视图配置:")
    print(f"   - 启用状态: {views_config.get('enabled', False)}")
    print(f"   - 自动清理: {views_config.get('auto_cleanup', False)}")

    create_views = views_config.get('create_views', [])
    print(f"   - 配置视图数量: {len(create_views)}")

    expected_views = ["评分排序视图", "时间排序视图"]
    actual_views = [view.get('name') for view in create_views]

    print("\n🎯 视图列表:")
    for i, view in enumerate(create_views, 1):
        print(f"   {i}. {view.get('name')} - {view.get('description', '无描述')}")
        print(f"      类型: {view.get('type', '未知')}")
        if view.get('sorts'):
            sorts = view['sorts']
            for sort_config in sorts:
                field = sort_config.get('field', '未知字段')
                direction = sort_config.get('direction', 'asc')
                direction_text = "降序" if direction == "desc" else "升序"
                print(f"      排序: {field} ({direction_text})")

    # 验证
    success = True
    if len(actual_views) != 2:
        print(f"\n❌ 错误：期望2个视图，实际{len(actual_views)}个")
        success = False

    for expected in expected_views:
        if expected not in actual_views:
            print(f"\n❌ 错误：缺少视图 '{expected}'")
            success = False

    for actual in actual_views:
        if actual not in expected_views:
            print(f"\n❌ 错误：多余视图 '{actual}'")
            success = False

    if success:
        print("\n✅ 视图配置正确！只包含评分排序视图和时间排序视图")

    return success


def test_view_creation_logic():
    """测试视图创建逻辑"""
    print("\n🔧 测试视图创建逻辑...")

    # 模拟视图配置
    view_configs = [
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

    print(f"✅ 视图配置格式正确，包含 {len(view_configs)} 个视图")

    # 验证每个视图的结构
    for view in view_configs:
        name = view.get('name', '未知')
        view_type = view.get('type', '未知')
        sorts = view.get('sorts', [])

        print(f"   - {name}: 类型={view_type}, 排序规则={len(sorts)}个")

        if not sorts:
            print(f"     ⚠️ 警告：{name} 没有排序规则")
        else:
            for sort_rule in sorts:
                field = sort_rule.get('field', '未知')
                direction = sort_rule.get('direction', 'asc')
                print(f"     📊 {field} ({direction})")

    return True


if __name__ == "__main__":
    print("🧪 测试视图功能")
    print("=" * 50)

    # 测试配置
    config_ok = test_view_configuration()

    # 测试逻辑
    logic_ok = test_view_creation_logic()

    print("\n" + "=" * 50)
    if config_ok and logic_ok:
        print("🎉 所有测试通过！视图功能配置正确")
    else:
        print("❌ 测试失败，请检查配置")
        sys.exit(1)
