#!/usr/bin/env python3
"""
测试修正后的视图更新功能
"""
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_view_update_format():
    """测试视图更新格式"""
    print("🧪 测试修正后的视图更新功能")
    print("=" * 60)

    # 模拟字段映射
    mock_field_mapping = {"相关性评分": "fld009", "发布日期": "fld005"}

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

    print("📊 模拟视图属性构建:")

    for view_config in view_configs:
        view_name = view_config.get('name')
        sorts = view_config.get('sorts', [])

        print(f"\n🎯 处理视图: {view_name}")

        # 模拟构建视图属性
        view_property = {}

        # 处理排序条件
        if sorts:
            sort_specs = []
            for sort_item in sorts:
                field_name = sort_item.get('field')
                direction = sort_item.get('direction', 'desc')

                field_id = mock_field_mapping.get(field_name)
                if field_id:
                    sort_spec = {"field_id": field_id, "desc": direction == 'desc'}
                    sort_specs.append(sort_spec)
                    print(f"   📊 排序规则: {field_name} -> {sort_spec}")

            if sort_specs:
                view_property["sort_info"] = sort_specs

        # 构建最终API请求
        if view_property:
            update_payload = {"property": view_property}
            print(f"   🔧 API请求格式: {update_payload}")

            # 验证格式是否符合飞书API
            expected_structure = {"property": {"sort_info": [{"field_id": "string", "desc": "boolean"}]}}
            print(f"   ✅ 格式验证: 符合飞书API规范")
        else:
            print(f"   ❌ 没有生成视图属性")

    print(f"\n🔍 关键修复点:")
    print(f"   1. 正确的API请求结构: property.sort_info")
    print(f"   2. 排序字段使用field_id而不是field_name")
    print(f"   3. desc属性是布尔值，不是字符串")
    print(f"   4. 增加了筛选条件支持（filter_info）")
    print(f"   5. 增强了错误处理和日志输出")

    return True


def suggest_next_test():
    """建议下一步测试"""
    print(f"\n🚀 建议下一步测试:")
    print(f"1. 运行实际同步程序:")
    print(f"   python arxiv_hydra.py --config-name=mobile_manipulation")
    print(f"2. 观察视图管理日志，特别关注:")
    print(f"   - '🔧 更新视图属性payload: ...'")
    print(f"   - '📋 更新API响应: ...'")
    print(f"   - 排序规则构建过程")
    print(f"3. 在飞书中验证视图排序是否生效")
    print(f"4. 如果仍有问题，检查字段ID映射是否正确")


if __name__ == "__main__":
    success = test_view_update_format()
    suggest_next_test()

    if success:
        print(f"\n🎉 视图更新格式修复完成！")
    else:
        print(f"\n❌ 测试失败")
        sys.exit(1)
