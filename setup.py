from setuptools import setup, find_packages
import os

# 读取README文件
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as fh:
        long_description = fh.read()
else:
    long_description = "自动化论文管理和同步工具"

# 读取requirements文件
requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
if os.path.exists(requirements_path):
    with open(requirements_path, "r", encoding="utf-8") as fh:
        requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
else:
    # 默认依赖
    requirements = [
        "requests>=2.25.0",
        "arxiv>=1.4.0",
        "python-dotenv>=0.19.0",
        "dataclasses-json>=0.5.0",
    ]

setup(
    name="autopaper",
    version="0.1.0",
    author="feishu_paper",
    author_email="admin@example.com",
    description="自动化论文管理和同步工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/caozx1110/feishu_paper",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
        ],
        "docs": [
            "sphinx>=3.0",
            "sphinx-rtd-theme>=0.5",
        ],
    },
    entry_points={
        "console_scripts": [
            "autopaper=autopaper.cli.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "autopaper": [
            "config/*.yaml",
            "templates/*.txt",
        ],
    },
)
