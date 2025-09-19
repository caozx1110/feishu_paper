#!/usr/bin/env python3
"""
模拟同步过程中的视图管理测试
"""
import os
import sys

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
from unittest.mock import Mock, patch


def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'conf', 'default.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def simulate_view_management():
    """模拟视图管理过程"""
    print("🎯 模拟飞书同步中的视图管理过程...")

    config = load_config()
    feishu_config = config.get('feishu', {})
    view_config = feishu_config.get('views', {})

    print(f"📋 视图管理配置:")
    print(f"   - 启用状态: {view_config.get('enabled', False)}")
    print(f"   - 自动清理: {view_config.get('auto_cleanup', False)}")

    if not view_config.get('enabled', False):
        print("❌ 视图管理未启用！这可能是问题所在")
        return False

    view_configs = view_config.get('create_views', [])
    auto_cleanup = view_config.get('auto_cleanup', True)

    print(f"📊 需要创建的视图: {len(view_configs)} 个")

    if not view_configs:
        print("❌ 没有配置任何视图！")
        return False

    # 模拟视图创建过程
    for i, view_config in enumerate(view_configs, 1):
        view_name = view_config.get('name', f'视图{i}')
        view_type = view_config.get('type', 'unknown')
        sorts = view_config.get('sorts', [])

        print(f"\n🆕 模拟创建视图: {view_name}")
        print(f"   - 类型: {view_type}")
        print(f"   - 排序规则: {len(sorts)} 个")

        for sort_config in sorts:
            field = sort_config.get('field', '未知字段')
            direction = sort_config.get('direction', 'asc')
            print(f"     📊 {field} ({direction})")

        # 检查字段名称
        for sort_config in sorts:
            field = sort_config.get('field')
            if field in ['相关性评分', '发布日期']:
                print(f"     ✅ 字段名称正确: {field}")
            else:
                print(f"     ⚠️ 未知字段: {field}")

        print(f"   ✅ 基础视图创建模拟完成")
        print(f"   ✅ 视图配置应用模拟完成")

    print(f"\n📊 模拟视图管理结果:")
    print(f"   - 创建: {len(view_configs)} 个")
    print(f"   - 已存在: 0 个")
    print(f"   - 删除: 0 个")
    print(f"   - 错误: 0 个")

    return True


def check_sync_configuration():
    """检查同步配置"""
    print("\n🔍 检查同步配置...")

    config = load_config()
    feishu_config = config.get('feishu', {})

    # 检查基本配置
    enabled = feishu_config.get('enabled', False)
    auto_sync = feishu_config.get('auto_sync', False)

    print(f"📋 飞书同步配置:")
    print(f"   - 启用状态: {enabled}")
    print(f"   - 自动同步: {auto_sync}")

    if not enabled:
        print("❌ 飞书同步未启用！")
        return False

    # 检查API配置
    api_config = feishu_config.get('api', {})
    app_id = api_config.get('app_id', '')
    app_secret = api_config.get('app_secret', '')

    print(f"   - App ID: {'已配置' if app_id else '未配置'}")
    print(f"   - App Secret: {'已配置' if app_secret else '未配置'}")

    # 检查表格配置
    bitable_config = feishu_config.get('bitable', {})
    app_token = bitable_config.get('app_token', '')

    print(f"   - App Token: {'已配置' if app_token else '未配置'}")

    return enabled


def suggest_debugging_steps():
    """提供调试步骤建议"""
    print("\n🛠️ 调试建议:")
    print("1. 运行实际同步命令并观察输出")
    print("2. 查找以下关键日志信息:")
    print("   - '🎯 管理表格视图...'")
    print("   - '🆕 创建视图: 评分排序视图'")
    print("   - '🆕 创建视图: 时间排序视图'")
    print("   - '✅ 基础视图已创建'")
    print("   - '✅ 视图配置已应用'")
    print("3. 如果没有看到这些信息，可能原因:")
    print("   - 视图管理未启用")
    print("   - API权限不足")
    print("   - 网络连接问题")
    print("   - 表格ID错误")
    print("4. 手动检查飞书多维表格是否有新视图")


def test_actual_sync_process():
    """测试实际同步过程会遇到的情况"""
    print("\n🧪 测试实际同步场景...")

    # 模拟sync_to_feishu.py中的逻辑
    config = load_config()
    feishu_cfg = config.get('feishu', {})

    # 模拟视图管理代码段
    view_config = feishu_cfg.get('views', {})
    if view_config.get('enabled', False):
        print("🎯 管理表格视图...")
        view_configs = view_config.get('create_views', [])
        auto_cleanup = view_config.get('auto_cleanup', True)

        if view_configs:
            print(f"📊 找到 {len(view_configs)} 个视图配置")

            # 模拟connector.manage_table_views调用
            result = {'created': len(view_configs), 'existing': 0, 'deleted': 0, 'errors': []}

            print(f"📊 视图管理结果:")
            print(f"   - 创建: {result['created']} 个")
            print(f"   - 已存在: {result['existing']} 个")
            print(f"   - 删除: {result['deleted']} 个")

            if result['errors']:
                print(f"   - 错误: {len(result['errors'])} 个")
                for error in result['errors']:
                    print(f"     • {error}")
        else:
            print("⚠️ 没有配置任何视图")
    else:
        print("⚠️ 视图管理未启用")


if __name__ == "__main__":
    print("🧪 模拟同步过程中的视图管理")
    print("=" * 60)

    # 检查同步配置
    sync_ok = check_sync_configuration()

    # 模拟视图管理
    view_ok = simulate_view_management()

    # 测试实际同步过程
    test_actual_sync_process()

    # 提供调试建议
    suggest_debugging_steps()

    print("\n" + "=" * 60)
    if sync_ok and view_ok:
        print("✅ 配置正常！如果视图仍不起作用，请按照调试建议操作")
    else:
        print("❌ 发现配置问题，请检查上述输出")
