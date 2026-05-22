"""Public Feishu Bitable connector facade."""

from __future__ import annotations

import requests

from ..terminal import debug, print, success, table
from .auth import FeishuAuthMixin
from .config import FeishuBitableConfig
from .errors import FeishuBitableAPIError
from .fields import FeishuFieldMixin
from .paper_mapping import FeishuPaperMappingMixin
from .records import FeishuRecordMixin
from .tables import FeishuTableMixin
from .views import FeishuViewMixin

__all__ = [
    "FeishuBitableAPIError",
    "FeishuBitableConfig",
    "FeishuBitableConnector",
    "test_bitable_connection",
]


class FeishuBitableConnector(
    FeishuAuthMixin,
    FeishuTableMixin,
    FeishuFieldMixin,
    FeishuRecordMixin,
    FeishuPaperMappingMixin,
    FeishuViewMixin,
):
    """飞书多维表格连接器"""

    def __init__(self, config: FeishuBitableConfig = None):
        """初始化飞书多维表格连接器"""
        if config is None:
            # 如果没有提供配置，尝试从环境变量创建
            config = self._create_config_from_env()

        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {'Content-Type': 'application/json; charset=utf-8', 'Authorization': f'Bearer {config.access_token}'}
        )

        debug(f"🔑 使用 {config.token_type}_access_token 进行API认证")



def test_bitable_connection(config: FeishuBitableConfig) -> bool:
    """测试多维表格连接"""
    try:
        connector = FeishuBitableConnector(config)
        tables = connector.list_tables()
        success("多维表格连接测试成功")
        table(
            "当前表格",
            ["表格名", "Table ID"],
            [(item.get('name', 'Unknown'), item.get('table_id', 'Unknown')) for item in tables],
        )
        return True

    except Exception as e:
        print(f"❌ 多维表格连接测试失败: {e}")
        return False
