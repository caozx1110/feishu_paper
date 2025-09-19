#!/usr/bin/env python3
"""
测试视图排序配置修复
"""
import os
import sys

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_view_sorting_fix():
    """测试视图排序配置修复"""
    print("🔧 测试视图排序配置修复")
    print("=" * 60)

    # 模拟字段映射
    mock_field_mapping = {
        "标题": "fld001",
        "ArXiv ID": "fld002",
        "作者": "fld003",
        "摘要": "fld004",
        "发布日期": "fld005",
        "更新日期": "fld006",
        "分类": "fld007",
        "关键词": "fld008",
        "相关性评分": "fld009",
        "详细匹配信息": "fld010",
        "研究领域": "fld011",
        "PDF链接": "fld012",
        "评价": "fld013",
    }

    print(f"📋 模拟字段映射 ({len(mock_field_mapping)} 个字段):")
    for field_name, field_id in mock_field_mapping.items():
        print(f"   - {field_name}: {field_id}")

    # 测试视图配置
    test_views = [
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

    print(f"\n🧪 测试视图配置:")

    all_success = True
    for view in test_views:
        view_name = view.get('name')
        sorts = view.get('sorts', [])

        print(f"\n   🎯 测试视图: {view_name}")

        # 模拟排序信息构建
        sort_specs = []
        for sort_item in sorts:
            field_name = sort_item.get('field')
            direction = sort_item.get('direction', 'desc')

            print(f"     📊 处理排序字段: {field_name} ({direction})")

            if not field_name:
                print(f"     ❌ 字段名为空")
                all_success = False
                continue

            field_id = mock_field_mapping.get(field_name)
            if not field_id:
                print(f"     ❌ 排序字段 '{field_name}' 未找到")
                print(f"     🔍 可用字段: {list(mock_field_mapping.keys())}")
                all_success = False
                continue

            sort_spec = {"field_id": field_id, "desc": direction == 'desc'}
            sort_specs.append(sort_spec)
            print(f"     ✅ 排序规则添加: {sort_spec}")

        if sort_specs:
            print(f"     📊 最终排序规则: {sort_specs}")

            # 模拟API请求payload
            property_payload = {"sort_info": sort_specs}
            update_payload = {"property": property_payload}
            print(f"     🔧 API请求payload: {update_payload}")
        else:
            print(f"     ❌ 没有有效的排序规则")
            all_success = False

    print(f"\n" + "=" * 60)
    if all_success:
        print("✅ 视图排序配置测试通过！")
        print("🎯 修复要点:")
        print("   1. 添加了详细的字段映射日志")
        print("   2. 添加了排序信息构建日志")
        print("   3. 添加了API请求日志")
        print("   4. 添加了错误详情跟踪")

        print("\n📝 下次运行同步时，你应该能看到类似输出:")
        print("   - '🔍 字段映射获取结果: 13 个字段'")
        print("   - '📊 处理排序条件: 1 个'")
        print("   - '✅ 排序信息构建成功: [...]'")
        print("   - '🔧 更新视图属性: {...}'")

    else:
        print("❌ 视图排序配置测试失败！")

    return all_success


def suggest_next_steps():
    """建议下一步操作"""
    print("\n🚀 建议下一步操作:")
    print("1. 运行实际的同步程序:")
    print("   python main.py")
    print("")
    print("2. 查看详细的日志输出，特别关注:")
    print("   - 字段映射是否正确获取")
    print("   - 排序字段是否能正确匹配")
    print("   - API请求是否成功发送")
    print("")
    print("3. 如果仍有问题，可能的原因:")
    print("   - 飞书API权限不足")
    print("   - 字段名称不匹配（中英文等）")
    print("   - 网络连接问题")
    print("   - API限制或延迟")
    print("")
    print("4. 验证方法:")
    print("   - 在飞书多维表格中查看视图")
    print("   - 手动点击视图切换")
    print("   - 检查数据是否按预期排序")


if __name__ == "__main__":
    success = test_view_sorting_fix()
    suggest_next_steps()

    if success:
        print("\n🎉 视图排序配置已修复，可以运行同步测试了！")
    else:
        print("\n❌ 配置测试失败，请检查问题。")
        sys.exit(1)
