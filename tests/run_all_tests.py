#!/usr/bin/env python3
"""
简化版统一测试运行脚本

运行项目中的所有测试文件，包括：
1. autopaper包的单元测试
2. 集成测试
3. 遗留功能测试
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime


def get_project_root():
    """获取项目根目录"""
    return Path(__file__).parent.parent


def discover_test_files():
    """发现所有测试文件"""
    test_files = {"autopaper_unit_tests": [], "integration_tests": [], "legacy_tests": [], "other_tests": []}

    tests_dir = Path(__file__).parent

    # autopaper单元测试
    autopaper_tests_dir = tests_dir.parent / "autopaper" / "tests"
    if autopaper_tests_dir.exists():
        for test_file in autopaper_tests_dir.glob("test_*.py"):
            test_files["autopaper_unit_tests"].append(test_file)

    # 集成测试
    integration_dir = tests_dir / "integration"
    if integration_dir.exists():
        for test_file in integration_dir.glob("test_*.py"):
            test_files["integration_tests"].append(test_file)

    # 遗留测试
    legacy_dir = tests_dir / "legacy"
    if legacy_dir.exists():
        for test_file in legacy_dir.glob("test_*.py"):
            test_files["legacy_tests"].append(test_file)

    # 其他测试文件
    for test_file in tests_dir.glob("test_*.py"):
        test_files["other_tests"].append(test_file)

    return test_files


def run_python_test(test_file_path, category):
    """运行单个Python测试文件"""
    print(f"\n{'='*60}")
    print(f"🧪 运行{category}: {test_file_path.name}")
    print(f"{'='*60}")

    try:
        # 切换到项目根目录运行测试
        project_root = get_project_root()

        # 运行测试文件
        result = subprocess.run(
            [sys.executable, str(test_file_path)],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300,  # 5分钟超时
        )

        print(result.stdout)
        if result.stderr:
            print("⚠️  警告/错误信息:")
            print(result.stderr)

        if result.returncode == 0:
            print(f"✅ {test_file_path.name} - 通过")
            return True
        else:
            print(f"❌ {test_file_path.name} - 失败 (退出码: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ {test_file_path.name} - 超时")
        return False
    except Exception as e:
        print(f"💥 {test_file_path.name} - 异常: {e}")
        return False


def run_category_tests(test_files, category_name, category_description):
    """运行某个类别的测试"""
    if not test_files:
        print(f"\n📝 {category_description}: 没有找到测试文件")
        return True, 0, 0

    print(f"\n🎯 开始运行{category_description}")
    print(f"共找到 {len(test_files)} 个测试文件")

    passed = 0
    total = len(test_files)

    for test_file in test_files:
        if run_python_test(test_file, category_description):
            passed += 1

    print(f"\n📊 {category_description}结果: {passed}/{total} 通过")
    return passed == total, passed, total


def generate_test_report(results):
    """生成测试报告"""
    print(f"\n{'='*80}")
    print("📋 测试报告")
    print(f"{'='*80}")
    print(f"🕒 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    total_passed = 0
    total_count = 0
    all_success = True

    for category, (success, passed, count) in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} {category}: {passed}/{count}")
        total_passed += passed
        total_count += count
        if not success:
            all_success = False

    print(f"\n📊 总体结果: {total_passed}/{total_count} 通过")

    if all_success:
        print("🎉 所有测试都通过了！")
    else:
        print("⚠️  存在测试失败，请检查具体问题")

    return all_success


def main():
    """主函数"""
    print("🚀 feishu_paper项目 - 统一测试运行器")
    print("=" * 80)

    # 发现测试文件
    test_files = discover_test_files()

    print("📋 测试文件概览:")
    for category, files in test_files.items():
        if files:
            print(f"  {category}: {len(files)} 个文件")
            for f in files:
                print(f"    - {f.name}")
        else:
            print(f"  {category}: 无测试文件")

    # 运行测试
    results = {}

    # 1. autopaper单元测试
    success, passed, total = run_category_tests(
        test_files["autopaper_unit_tests"], "autopaper_unit", "autopaper单元测试"
    )
    results["autopaper单元测试"] = (success, passed, total)

    # 2. 集成测试
    success, passed, total = run_category_tests(test_files["integration_tests"], "integration", "集成测试")
    results["集成测试"] = (success, passed, total)

    # 3. 遗留测试
    success, passed, total = run_category_tests(test_files["legacy_tests"], "legacy", "遗留功能测试")
    results["遗留功能测试"] = (success, passed, total)

    # 4. 其他测试
    success, passed, total = run_category_tests(test_files["other_tests"], "other", "其他测试")
    results["其他测试"] = (success, passed, total)

    # 生成报告
    all_success = generate_test_report(results)

    # 额外说明
    print("\n💡 测试说明:")
    print("  - autopaper单元测试: autopaper包的核心功能测试")
    print("  - 集成测试: 使用真实环境变量的完整功能测试")
    print("  - 遗留功能测试: 项目早期的基础功能测试")
    print("  - 其他测试: 项目根目录的其他测试文件")

    print("\n🔧 测试环境要求:")
    print("  - 需要.env文件配置飞书API凭据")
    print("  - 集成测试需要真实的网络连接")
    print("  - 某些测试可能因为API限制而失败")

    return 0 if all_success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
