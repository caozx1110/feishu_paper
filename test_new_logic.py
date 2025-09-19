#!/usr/bin/env python3
"""
测试修改后的必须关键词逻辑
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from arxiv_core import PaperRanker


def test_new_required_keywords_logic():
    """测试新的必须关键词逻辑（所有关键词都必须匹配）"""
    print("🧪 测试新的必须关键词逻辑")
    print("=" * 50)

    # 创建搜索器实例
    ranker = PaperRanker()

    # 模拟配置 - 所有关键词都必须匹配
    required_keywords_config = {
        'enabled': True,
        'fuzzy_match': True,
        'similarity_threshold': 0.8,
        'keywords': [
            'humanoid',  # 必须包含
            'imitation',  # 必须包含
        ],
    }

    # 测试用例
    test_cases = [
        {
            'title': 'Humanoid Robot Imitation Learning',
            'abstract': 'This paper presents a humanoid robot system that learns through imitation.',
            'expected_pass': True,
            'reason': '包含humanoid和imitation，应该通过',
        },
        {
            'title': 'Humanoid Robot Walking',
            'abstract': 'This work focuses on humanoid robot walking algorithms.',
            'expected_pass': False,
            'reason': '只包含humanoid，缺少imitation，应该被过滤',
        },
        {
            'title': 'Imitation Learning for Manipulation',
            'abstract': 'We develop imitation learning methods for robot manipulation tasks.',
            'expected_pass': False,
            'reason': '只包含imitation，缺少humanoid，应该被过滤',
        },
        {
            'title': 'Deep Learning in Computer Vision',
            'abstract': 'We propose a new deep learning architecture for computer vision tasks.',
            'expected_pass': False,
            'reason': '不包含任何必须关键词，应该被过滤',
        },
        {
            'title': 'Humanoid Imitation of Human Movements',
            'abstract': 'This research explores how humanoid robots can imitate complex human movements.',
            'expected_pass': True,
            'reason': '包含humanoid和imitation（变体），应该通过',
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

    print("\n" + "=" * 50)
    print("🎯 新逻辑说明:")
    print("- 所有配置的关键词都必须匹配（AND逻辑）")
    print("- 支持模糊匹配和词形变化")
    print("- 返回的匹配关键词是配置中的原始关键词")
    print("- 不显示具体匹配到的词汇或模糊匹配标记")

    print(f"\n🎉 总体测试结果: {'✅ 全部通过' if all_passed else '❌ 有失败用例'}")


if __name__ == "__main__":
    test_new_required_keywords_logic()
