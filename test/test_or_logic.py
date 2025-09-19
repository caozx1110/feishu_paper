#!/usr/bin/env python3
"""
测试OR逻辑功能
"""
import sys
import os

# 添加父目录到路径，以便导入主模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arxiv_core import PaperRanker


def test_or_logic():
    """测试OR逻辑功能"""
    print("🧪 测试必须关键词的OR逻辑功能")
    print("=" * 60)

    # 创建搜索器实例
    ranker = PaperRanker()

    # 模拟配置 - 使用OR逻辑组合
    required_keywords_config = {
        'enabled': True,
        'fuzzy_match': True,
        'similarity_threshold': 0.8,
        'keywords': [
            'mobile OR locomotion',  # 必须包含mobile或locomotion其中之一
            'manipulation',  # 必须包含manipulation
        ],
    }

    # 测试用例
    test_cases = [
        {
            'title': 'Mobile Manipulation for Service Robots',
            'abstract': 'This paper presents a mobile manipulation system for service robots.',
            'expected_pass': True,
            'reason': '包含mobile和manipulation，满足两个条件',
        },
        {
            'title': 'Locomotion-based Manipulation System',
            'abstract': 'We develop a locomotion-based manipulation system for dynamic environments.',
            'expected_pass': True,
            'reason': '包含locomotion和manipulation，满足两个条件',
        },
        {
            'title': 'Mobile Robot Navigation',
            'abstract': 'This work focuses on mobile robot navigation algorithms.',
            'expected_pass': False,
            'reason': '只包含mobile，缺少manipulation，应该被过滤',
        },
        {
            'title': 'Robot Manipulation Tasks',
            'abstract': 'We study various robot manipulation tasks in laboratory settings.',
            'expected_pass': False,
            'reason': '只包含manipulation，缺少mobile/locomotion，应该被过滤',
        },
        {
            'title': 'Deep Learning in Computer Vision',
            'abstract': 'We propose a new deep learning architecture for computer vision tasks.',
            'expected_pass': False,
            'reason': '不包含任何必须关键词，应该被过滤',
        },
        {
            'title': 'Locomotion and Grasping Coordination',
            'abstract': 'This research explores coordination between locomotion and manipulation tasks.',
            'expected_pass': True,
            'reason': '包含locomotion和manipulation，满足两个条件',
        },
    ]

    # 执行测试
    all_passed = True
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 测试用例 {i}: {test_case['title']}")
        print(f"摘要: {test_case['abstract']}")
        print(f"期望结果: {'✅ 通过' if test_case['expected_pass'] else '❌ 被过滤'}")
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
        print(f"匹配到的关键词: {matched_keywords}")

        # 验证结果
        if matched == test_case['expected_pass']:
            print(f"测试结果: ✅ 正确")
        else:
            print(f"测试结果: ❌ 错误")
            all_passed = False

    print("\n" + "=" * 60)
    print("🎯 OR逻辑说明:")
    print("- 配置: ['mobile OR locomotion', 'manipulation']")
    print("- 必须满足: (mobile或locomotion) 且 manipulation")
    print("- 支持模糊匹配和词形变化")
    print("- 返回具体匹配到的关键词")

    print(f"\n🎉 总体测试结果: {'✅ 全部通过' if all_passed else '❌ 有失败用例'}")


def test_complex_or_logic():
    """测试更复杂的OR逻辑"""
    print("\n\n🔬 测试复杂OR逻辑组合")
    print("=" * 60)

    ranker = PaperRanker()

    # 更复杂的配置
    complex_config = {
        'enabled': True,
        'fuzzy_match': True,
        'similarity_threshold': 0.8,
        'keywords': [
            'humanoid OR robot OR robotic',  # 三选一
            'imitation OR demonstration OR learning',  # 三选一
        ],
    }

    test_cases = [
        {
            'title': 'Humanoid Imitation Learning',
            'abstract': 'This paper presents humanoid imitation learning methods.',
            'expected_pass': True,
        },
        {
            'title': 'Robot Demonstration Learning',
            'abstract': 'We develop robot demonstration learning algorithms.',
            'expected_pass': True,
        },
        {
            'title': 'Robotic Learning Systems',
            'abstract': 'This work focuses on robotic learning systems.',
            'expected_pass': True,
        },
        {
            'title': 'Computer Vision Methods',
            'abstract': 'We propose new computer vision methods.',
            'expected_pass': False,
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 复杂测试 {i}: {test_case['title']}")

        mock_paper = {
            'title': test_case['title'],
            'summary': test_case['abstract'],
            'categories': [],
            'authors_str': '',
        }

        matched, matched_keywords = ranker.check_required_keywords(mock_paper, complex_config)

        print(f"结果: {'✅ 通过' if matched else '❌ 被过滤'}")
        print(f"匹配: {matched_keywords}")

        success = matched == test_case['expected_pass']
        print(f"验证: {'✅' if success else '❌'}")


if __name__ == "__main__":
    test_or_logic()
    test_complex_or_logic()
