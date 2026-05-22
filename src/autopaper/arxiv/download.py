"""PDF download and local metadata/index generation."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import arxiv

from ..terminal import print


class ArxivDownloadMixin:
    def download_pdf(
        self, paper: Dict[str, Any], force_download: bool = False, create_metadata: bool = True
    ) -> Tuple[bool, str]:
        """
        下载论文PDF

        Args:
            paper: 论文信息字典
            force_download: 是否强制重新下载
            create_metadata: 是否创建元数据文件

        Returns:
            tuple: (是否成功, 文件路径或错误信息)
        """
        try:
            arxiv_id = paper.get("arxiv_id", "")
            if not arxiv_id:
                return False, "论文ID无效"

            # 生成文件名
            safe_title = self._sanitize_filename(paper.get("title", ""))[:100]
            pdf_filename = f"{arxiv_id}_{safe_title}.pdf"
            pdf_path = self.download_dir / pdf_filename

            # 检查是否已存在
            if pdf_path.exists() and not force_download:
                return True, str(pdf_path)

            print(f"📥 下载论文: {paper.get('title', '')[:50]}...")

            # 获取arxiv结果对象
            search = arxiv.Search(id_list=[arxiv_id])
            result = next(self.client.results(search), None)

            if not result:
                return False, "无法找到论文"

            # 下载PDF
            result.download_pdf(dirpath=str(self.download_dir), filename=pdf_filename)

            # 创建元数据文件
            if create_metadata:
                self._create_paper_metadata(paper, pdf_path.with_suffix(".md"))

            print(f"✅ 下载完成: {pdf_filename}")
            return True, str(pdf_path)

        except Exception as e:
            error_msg = f"下载失败: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def batch_download_pdfs(
        self, papers: List[Dict[str, Any]], max_downloads: int = 10, create_index: bool = True
    ) -> Dict[str, Any]:
        """
        批量下载PDF

        Args:
            papers: 论文列表
            max_downloads: 最大下载数量
            create_index: 是否创建索引文件

        Returns:
            下载统计信息
        """
        stats = {"total": len(papers), "downloaded": 0, "skipped": 0, "failed": 0, "failed_papers": []}

        download_count = 0
        downloaded_papers = []

        for paper in papers:
            if download_count >= max_downloads:
                break

            success, result = self.download_pdf(paper)
            if success:
                stats["downloaded"] += 1
                downloaded_papers.append({**paper, "pdf_path": result})
            else:
                if "已存在" in result:
                    stats["skipped"] += 1
                else:
                    stats["failed"] += 1
                    stats["failed_papers"].append({"title": paper.get("title", ""), "error": result})

            download_count += 1

        # 创建下载索引
        if create_index and downloaded_papers:
            self._create_download_index(downloaded_papers)

        return stats

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除不合法字符"""
        # 移除或替换不合法字符
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, "_", filename)
        # 移除多余空格和标点
        sanitized = re.sub(r"\s+", "_", sanitized)
        sanitized = re.sub(r"[^\w\-_.]", "", sanitized)
        return sanitized.strip("_")

    def _create_paper_metadata(self, paper: Dict[str, Any], md_path: Path) -> None:
        """创建论文元数据Markdown文件"""
        try:
            content = f"""# {paper.get('title', 'Unknown Title')}

## 基本信息
- **ArXiv ID**: {paper.get('arxiv_id', 'N/A')}
- **发布日期**: {paper.get('published_date', 'N/A')}
- **主分类**: {paper.get('primary_category', 'N/A')}
- **所有分类**: {paper.get('categories_str', 'N/A')}

## 作者
{paper.get('authors_str', 'Unknown Authors')}

## 摘要
{paper.get('summary', 'No summary available')}

## 链接
- **论文页面**: {paper.get('paper_url', 'N/A')}
- **PDF下载**: {paper.get('pdf_url', 'N/A')}

## 其他信息
- **期刊引用**: {paper.get('journal_ref', 'N/A')}
- **DOI**: {paper.get('doi', 'N/A')}
- **备注**: {paper.get('comment', 'N/A')}

---
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            print(f"创建元数据文件失败: {e}")

    def _create_download_index(self, papers: List[Dict[str, Any]]) -> None:
        """创建下载索引文件"""
        try:
            index_path = self.download_dir / "README.md"

            content = f"""# ArXiv 论文下载索引

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 总计论文数: {len(papers)}

## 论文列表

"""

            for i, paper in enumerate(papers, 1):
                arxiv_id = paper.get("arxiv_id", "N/A")
                title = paper.get("title", "Unknown Title")
                authors = paper.get("authors_str", "Unknown Authors")
                categories = paper.get("categories_str", "N/A")
                published = paper.get("published_date", "N/A")

                content += f"""### {i}. {title}

- **ArXiv ID**: {arxiv_id}
- **作者**: {authors}
- **分类**: {categories}
- **发布**: {published}
- **链接**: [{arxiv_id}]({paper.get('paper_url', '#')}) | [PDF]({paper.get('pdf_url', '#')})

---

"""

            with open(index_path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"📝 创建下载索引: {index_path}")

        except Exception as e:
            print(f"创建索引文件失败: {e}")
