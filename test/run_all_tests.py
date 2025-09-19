#!/usr/bin/env python3
"""
运行所有测试用例
"""
import sys
import os
import subprocess


def run_test(test_file):
    """运行单个测试文件"""
    print(f"\n{'='*60}")
    print(f"🧪 运行测试: {test_file}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            [sys.executable, test_file], capture_output=True, text=True, cwd=os.path.dirname(__file__)
        )

        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"❌ 测试失败: {test_file}")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
    except Exception as e:
        print(f"❌ 运行测试时出错: {e}")
        return False


def main():
    """运行所有测试"""
    print("🚀 运行所有测试用例")
    print("=" * 60)

    # 测试文件列表
    test_files = [
        'test_arxiv_link.py',
        'test_or_logic.py',
        'test_detailed_display.py',
        'test_views.py',
        'test_view_debug.py',
        'test_sync_simulation.py',
        'test_view_sorting_fix.py',
    ]

    passed = 0
    total = len(test_files)

    for test_file in test_files:
        if os.path.exists(test_file):
            if run_test(test_file):
                passed += 1
        else:
            print(f"⚠️ 测试文件不存在: {test_file}")

    print(f"\n{'='*60}")
    print(f"📊 测试结果汇总")
    print(f"{'='*60}")
    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total - passed}/{total}")

    if passed == total:
        print("🎉 所有测试都通过了！")
        return 0
    else:
        print("💥 有测试失败！")
        return 1


if __name__ == "__main__":
    sys.exit(main())
