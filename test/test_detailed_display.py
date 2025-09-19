#!/usr/bin/env python3
"""
测试具体匹配关键词显示功能
"""
import sys
import os

# 添加父目录到路径，以便导入主模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arxiv_core import PaperRanker


def test_detailed_keyword_display():
    """测试具体匹配关键词的显示功能"""
    print("🧪 测试具体匹配关键词显示功能")
    print("=" * 60)

    # 创建搜索器实例
    ranker = PaperRanker()

    # 模拟配置 - 复杂OR逻辑
    required_keywords_config = {
        'enabled': True,
        'fuzzy_match': True,
        'similarity_threshold': 0.8,
        'keywords': [
            'mobile OR locomotion OR walking',  # 三选一或多选
            'manipulation OR grasping',  # 二选一或多选
        ],
    }

    # 测试用例
    test_cases = [
        {
            'title': 'Mobile Manipulation for Service Robots',
            'abstract': 'This paper presents a mobile manipulation system.',
            'expected_keywords': ['mobile', 'manipulation'],
            'reason': '匹配mobile和manipulation',
        },
        {
            'title': 'Locomotion-based Grasping System',
            'abstract': 'We develop a locomotion-based grasping system.',
            'expected_keywords': ['locomotion', 'grasping'],
            'reason': '匹配locomotion和grasping',
        },
        {
            'title': 'Walking Robot with Manipulation Capabilities',
            'abstract': 'This robot can walk and perform manipulation tasks.',
            'expected_keywords': ['walking', 'manipulation'],
            'reason': '匹配walking和manipulation',
        },
        {
            'title': 'Mobile Walking Robot Grasping Objects',
            'abstract': 'A mobile walking robot that can grasp objects.',
            'expected_keywords': ['mobile', 'walking', 'grasping'],
            'reason': '匹配mobile、walking和grasping（多个匹配）',
        },
        {
            'title': 'Autonomous Navigation System',
            'abstract': 'This paper focuses on autonomous navigation algorithms.',
            'expected_keywords': [],
            'reason': '缺少manipulation相关关键词，应该被过滤',
        },
    ]

    # 执行测试
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 测试用例 {i}: {test_case['title']}")
        print(f"摘要: {test_case['abstract']}")
        print(f"期望匹配关键词: {test_case['expected_keywords']}")
        print(f"原因: {test_case['reason']}")

        # 创建模拟论文字典
        mock_paper = {
            'title': test_case['title'],
            'summary': test_case['abstract'],
            'categories': [],
            'authors_str': '',
        }

        # 检查必须关键词
        matched, matched_keywords = ranker.check_required_keywords(mock_paper, required_keywords_config)

        print(f"实际结果: {'✅ 通过' if matched else '❌ 被过滤'}")
        print(f"实际匹配关键词: {matched_keywords}")

        # 验证结果
        if test_case['expected_keywords']:
            expected_pass = True
            # 检查是否包含期望的关键词
            expected_set = set(test_case['expected_keywords'])
            actual_set = set(matched_keywords)
            success = matched and expected_set.issubset(actual_set)
        else:
            expected_pass = False
            success = not matched

        print(f"测试结果: {'✅ 正确' if success else '❌ 错误'}")

    print("\n" + "=" * 60)
    print("🎯 新显示逻辑说明:")
    print("- 配置: ['mobile OR locomotion OR walking', 'manipulation OR grasping']")
    print("- 显示: 具体匹配到的关键词，如 ['mobile', 'manipulation']")
    print("- 多匹配: 如果OR组合中多个都匹配，全部显示")
    print("- 例如: 论文包含mobile、walking、grasping，显示所有三个")


def test_single_keyword_display():
    """测试单个关键词的显示"""
    print("\n\n🔬 测试单个关键词显示")
    print("=" * 60)

    ranker = PaperRanker()

    # 单个关键词配置
    single_config = {
        'enabled': True,
        'fuzzy_match': True,
        'similarity_threshold': 0.8,
        'keywords': [
            'humanoid',  # 单个关键词
            'imitation',  # 单个关键词
        ],
    }

    mock_paper = {
        'title': 'Humanoid Robot Imitation Learning',
        'summary': 'This paper presents humanoid robot imitation methods.',
        'categories': [],
        'authors_str': '',
    }

    matched, matched_keywords = ranker.check_required_keywords(mock_paper, single_config)

    print(f"论文: Humanoid Robot Imitation Learning")
    print(f"配置: ['humanoid', 'imitation']")
    print(f"结果: {'✅ 通过' if matched else '❌ 被过滤'}")
    print(f"显示关键词: {matched_keywords}")
    print(f"说明: 单个关键词直接显示关键词本身")


if __name__ == "__main__":
    test_detailed_keyword_display()
    test_single_keyword_display()
