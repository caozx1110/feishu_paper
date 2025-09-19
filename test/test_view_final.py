#!/usr/bin/env python3
"""
简化视图功能验证和问题排查
"""
import os
import sys

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml


def main():
    """主函数：简化视图配置并验证"""
    print("🎯 视图功能简化和验证")
    print("=" * 50)

    # 1. 确认配置已简化
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'conf', 'default.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    views_config = config.get('feishu', {}).get('views', {})
    create_views = views_config.get('create_views', [])

    print(f"📋 当前视图配置:")
    print(f"   - 视图管理启用: {views_config.get('enabled', False)}")
    print(f"   - 自动清理: {views_config.get('auto_cleanup', False)}")
    print(f"   - 配置的视图数量: {len(create_views)}")

    expected_views = ["评分排序视图", "时间排序视图"]
    actual_views = [view.get('name') for view in create_views]

    print(f"\n🎯 视图列表:")
    for i, view in enumerate(create_views, 1):
        print(f"   {i}. {view.get('name')}")
        print(f"      描述: {view.get('description', '无')}")
        print(f"      类型: {view.get('type', '未知')}")
        sorts = view.get('sorts', [])
        for sort_config in sorts:
            field = sort_config.get('field', '未知')
            direction = sort_config.get('direction', 'asc')
            direction_text = "降序" if direction == "desc" else "升序"
            print(f"      排序: {field} ({direction_text})")

    # 2. 验证简化结果
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
        print(f"\n✅ 视图配置已正确简化！")
    else:
        print(f"\n❌ 视图配置有问题")
        return False

    # 3. 提供使用说明
    print(f"\n📝 使用说明:")
    print(f"   1. 运行 python main.py 进行论文同步")
    print(f"   2. 查看控制台输出中的视图管理信息")
    print(f"   3. 在飞书多维表格中检查是否有新视图")
    print(f"   4. 验证视图是否按预期排序")

    print(f"\n🔍 查看视图的方法:")
    print(f"   1. 打开飞书多维表格")
    print(f"   2. 在表格上方查找视图切换选项")
    print(f"   3. 应该能看到：")
    print(f"      - 表格视图（默认）")
    print(f"      - 评分排序视图")
    print(f"      - 时间排序视图")

    print(f"\n⚡ 可能的问题和解决方案:")
    print(f"   问题1: 视图创建但不生效")
    print(f"   解决: 刷新浏览器页面，或重新打开表格")
    print(f"   ")
    print(f"   问题2: 看不到视图创建的日志")
    print(f"   解决: 检查环境变量配置是否正确")
    print(f"   ")
    print(f"   问题3: 视图存在但排序不对")
    print(f"   解决: 确保表格中有数据，空表格看不出排序效果")
    print(f"   ")
    print(f"   ✅ 最新修复: 已添加详细日志输出")
    print(f"   现在运行同步时可以看到详细的视图配置过程")
    print(f"   包括字段映射、排序规则构建、API请求等信息")

    return True


if __name__ == "__main__":
    if main():
        print("\n🎉 视图配置验证完成！")
        print("现在可以运行同步程序测试视图功能了。")
    else:
        print("\n❌ 验证失败，请检查配置。")
        sys.exit(1)
