"""Feishu Bitable view management, filters, sorting, and grouping."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class FeishuViewMixin:
    def list_views(self, table_id: str) -> List[Dict[str, Any]]:
        """获取数据表中的所有视图"""
        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/views"
        result = self._make_request('GET', endpoint)
        return result.get('items', [])

    def create_view(self, table_id: str, view_config: Dict[str, Any]) -> Dict[str, Any]:
        """创建新视图并配置筛选排序条件

        Args:
            table_id: 表格ID
            view_config: 视图配置

        Returns:
            创建的视图信息
        """
        view_name = view_config.get('name', '新视图')

        # 第一步：创建基础视图
        payload = {"view_name": view_name, "view_type": "grid"}

        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/views"
        result = self._make_request('POST', endpoint, json=payload)

        if not result or not result.get('view', {}).get('view_id'):
            raise Exception(f"创建视图失败: {result}")

        view_id = result['view']['view_id']
        print(f"   ✅ 基础视图已创建: {view_name}")

        # 第二步：通过更新视图API配置筛选和排序
        success = self._configure_view_properties(table_id, view_id, view_config)
        if success:
            print("   ✅ 视图配置已应用")
        else:
            print("   ⚠️ 视图配置应用失败，但视图已创建")

        return result

    def _configure_view_properties(self, table_id: str, view_id: str, view_config: Dict[str, Any]) -> bool:
        """配置视图的排序和分组属性（不包括筛选，因为API限制）"""
        try:
            # 获取字段映射
            field_mapping = self._get_field_mapping(table_id)
            print(f"     🔍 字段映射获取结果: {len(field_mapping)} 个字段")
            for field_name, field_id in field_mapping.items():
                print(f"       - {field_name}: {field_id}")

            # 构建视图属性
            view_property = {}

            # 处理排序条件
            sorts = view_config.get('sorts', [])
            if sorts:
                print(f"     📊 处理排序条件: {len(sorts)} 个")
                sort_info = self._build_sort_info(sorts, field_mapping)
                if sort_info:
                    view_property["sort_info"] = sort_info
                    print(f"     ✅ 排序信息构建成功: {sort_info}")
                else:
                    print("     ❌ 排序信息构建失败")

            # 处理分组条件
            group_by = view_config.get('group_by')
            if group_by:
                group_info = self._build_group_info(group_by, field_mapping)
                if group_info:
                    view_property["group_info"] = group_info
                    print(f"     ✅ 分组信息构建成功: {group_info}")

            # 处理筛选条件
            filters = view_config.get('filters', [])
            if filters:
                print(f"     🔍 处理筛选条件: {len(filters)} 个")
                filter_info = self._build_filter_info(filters, field_mapping)
                if filter_info:
                    view_property["filter_info"] = filter_info
                    print(f"     ✅ 筛选信息构建成功: {filter_info}")

            # 如果有属性需要设置，则更新视图
            if view_property:
                # 按照飞书API格式构建请求
                update_payload = {"property": view_property}
                print(f"     🔧 更新视图属性payload: {update_payload}")

                endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/views/{view_id}"
                result = self._make_request('PATCH', endpoint, json=update_payload)
                print(f"     📋 更新API响应: {result}")
                return True
            else:
                print("     ⚠️ 没有视图属性需要更新")
                return True

        except Exception as e:
            print(f"   ❌ 配置视图属性失败: {e}")
            import traceback

            print(f"   🔍 详细错误: {traceback.format_exc()}")
            return False

    def _build_view_property(self, table_id: str, view_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """构建视图属性配置"""
        property_config = {}

        # 获取字段映射
        field_mapping = self._get_field_mapping(table_id)

        # 构建筛选条件
        filters = view_config.get('filters', [])
        if filters:
            conditions = []
            for filter_item in filters:
                condition = self._build_filter_condition_v2(filter_item, field_mapping)
                if condition:
                    conditions.append(condition)

            if conditions:
                property_config["filter_info"] = {"conjunction": "and", "conditions": conditions}

        # 构建排序条件
        sorts = view_config.get('sorts', [])
        if sorts:
            sort_infos = []
            for sort_item in sorts:
                field_name = sort_item.get('field')
                field_id = field_mapping.get(field_name, field_name)
                sort_info = {"field_id": field_id, "desc": sort_item.get('direction', 'desc') == 'desc'}
                sort_infos.append(sort_info)

            property_config["sort_info"] = sort_infos

        # 构建分组条件
        group_by = view_config.get('group_by')
        if group_by:
            field_id = field_mapping.get(group_by, group_by)
            property_config["group_info"] = [{"field_id": field_id, "desc": False}]

        return property_config if property_config else None

    def _build_filter_condition_v2(
        self, filter_item: Dict[str, Any], field_mapping: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """构建视图筛选条件（V2版本用于视图属性）"""
        field = filter_item.get('field')
        operator = filter_item.get('operator')
        value = filter_item.get('value')

        if not field or not operator:
            return None

        # 获取字段ID
        field_id = field_mapping.get(field, field)

        # 操作符映射（视图属性可能使用不同的操作符）
        operator_map = {
            'gte': 'isGreaterThanOrEqualTo',
            'lte': 'isLessThanOrEqualTo',
            'gt': 'isGreaterThan',
            'lt': 'isLessThan',
            'eq': 'is',
            'contains': 'contains',
            'not_contains': 'doesNotContain',
        }

        # 特殊处理日期相关操作符
        if operator == 'gte_days_ago':
            from datetime import datetime, timedelta

            days_ago = datetime.now() - timedelta(days=int(value))
            value = int(days_ago.timestamp() * 1000)
            operator = 'gte'

        feishu_operator = operator_map.get(operator, 'is')

        return {
            "field_id": field_id,
            "operator": feishu_operator,
            "value": [str(value)] if not isinstance(value, list) else [str(v) for v in value],
        }

    def delete_view(self, table_id: str, view_id: str) -> bool:
        """删除视图

        Args:
            table_id: 表格ID
            view_id: 视图ID

        Returns:
            是否删除成功
        """
        try:
            endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/views/{view_id}"
            self._make_request('DELETE', endpoint)
            return True
        except Exception as e:
            print(f"⚠️ 删除视图失败: {e}")
            return False

    def _build_filter_condition(
        self, filter_item: Dict[str, Any], field_mapping: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """构建筛选条件"""
        field = filter_item.get('field')
        operator = filter_item.get('operator')
        value = filter_item.get('value')

        if not field or not operator:
            return None

        # 获取字段ID
        field_id = field_mapping.get(field, field)

        # 操作符映射
        operator_map = {
            'gte': 'isGreaterThanOrEqualTo',
            'lte': 'isLessThanOrEqualTo',
            'gt': 'isGreaterThan',
            'lt': 'isLessThan',
            'eq': 'is',
            'contains': 'contains',
            'not_contains': 'doesNotContain',
        }

        # 特殊处理日期相关操作符
        if operator == 'gte_days_ago':
            # 计算N天前的时间戳
            from datetime import datetime, timedelta

            days_ago = datetime.now() - timedelta(days=int(value))
            value = int(days_ago.timestamp() * 1000)
            operator = 'gte'

        feishu_operator = operator_map.get(operator, 'is')

        return {
            "field_name": field_id,
            "operator": feishu_operator,
            "value": [str(value)] if not isinstance(value, list) else [str(v) for v in value],
        }

    def manage_table_views(
        self, table_id: str, view_configs: List[Dict[str, Any]], auto_cleanup: bool = True
    ) -> Dict[str, Any]:
        """管理表格视图

        Args:
            table_id: 表格ID
            view_configs: 视图配置列表
            auto_cleanup: 是否自动清理多余视图

        Returns:
            管理结果统计
        """
        result = {'created': 0, 'deleted': 0, 'existing': 0, 'errors': []}

        try:
            # 获取现有视图
            existing_views = self.list_views(table_id)
            existing_view_names = {view.get('view_name'): view.get('view_id') for view in existing_views}

            # 需要创建的视图名称
            target_view_names = {config.get('name') for config in view_configs}

            # 创建缺失的视图
            for view_config in view_configs:
                view_name = view_config.get('name')
                if view_name not in existing_view_names:
                    try:
                        print(f"🆕 创建视图: {view_name}")
                        self.create_view(table_id, view_config)
                        result['created'] += 1
                    except Exception as e:
                        error_msg = f"创建视图 '{view_name}' 失败: {e}"
                        print(f"❌ {error_msg}")
                        result['errors'].append(error_msg)
                else:
                    result['existing'] += 1

            # 删除多余的视图（如果启用自动清理）
            if auto_cleanup:
                for view_name, view_id in existing_view_names.items():
                    # 跳过默认视图
                    if view_name in ['表格视图', 'Grid View', '默认视图']:
                        continue

                    if view_name not in target_view_names:
                        try:
                            print(f"🗑️ 删除多余视图: {view_name}")
                            if self.delete_view(table_id, view_id):
                                result['deleted'] += 1
                        except Exception as e:
                            error_msg = f"删除视图 '{view_name}' 失败: {e}"
                            print(f"❌ {error_msg}")
                            result['errors'].append(error_msg)

            return result

        except Exception as e:
            error_msg = f"视图管理失败: {e}"
            print(f"❌ {error_msg}")
            result['errors'].append(error_msg)
            return result

    def _build_filter_info(self, filters: List[Dict], field_mapping: Dict[str, str]) -> Optional[Dict]:
        """构建筛选信息"""
        conditions = []

        for filter_item in filters:
            field_name = filter_item.get('field')
            operator = filter_item.get('operator')
            value = filter_item.get('value')

            if not field_name or not operator:
                continue

            # 获取字段ID
            field_id = field_mapping.get(field_name)
            if not field_id:
                print(f"     ⚠️ 字段 '{field_name}' 未找到")
                continue

            # 转换操作符
            feishu_operator = self._convert_operator(operator)

            # 处理特殊操作符
            if operator == 'gte_days_ago':
                from datetime import datetime, timedelta

                days_ago = datetime.now() - timedelta(days=int(value))
                value = int(days_ago.timestamp() * 1000)
                feishu_operator = 'isGreaterThanOrEqualTo'

            # 构建条件
            condition = {
                "field_id": field_id,
                "operator": feishu_operator,
                "value": [str(value)] if not isinstance(value, list) else [str(v) for v in value],
            }
            conditions.append(condition)

        if conditions:
            return {"conjunction": "and", "conditions": conditions}

        return None

    def _build_sort_info(self, sorts: List[Dict], field_mapping: Dict[str, str]) -> Optional[List[Dict]]:
        """构建排序信息"""
        sort_specs = []

        for sort_item in sorts:
            field_name = sort_item.get('field')
            direction = sort_item.get('direction', 'desc')

            print(f"       📊 处理排序字段: {field_name} ({direction})")

            if not field_name:
                print("       ❌ 字段名为空")
                continue

            field_id = field_mapping.get(field_name)
            if not field_id:
                print(f"       ❌ 排序字段 '{field_name}' 未找到")
                print(f"       🔍 可用字段: {list(field_mapping.keys())}")
                continue

            sort_spec = {"field_id": field_id, "desc": direction == 'desc'}
            sort_specs.append(sort_spec)
            print(f"       ✅ 排序规则添加: {sort_spec}")

        print(f"     📊 最终排序规则: {sort_specs}")
        return sort_specs if sort_specs else None

    def _build_group_info(self, group_by: str, field_mapping: Dict[str, str]) -> Optional[List[Dict]]:
        """构建分组信息"""
        field_id = field_mapping.get(group_by)
        if not field_id:
            print(f"     ⚠️ 分组字段 '{group_by}' 未找到")
            return None

        return [{"field_id": field_id, "desc": False}]

    def _convert_operator(self, operator: str) -> str:
        """转换操作符为飞书API格式"""
        operator_map = {
            'gte': 'isGreaterThanOrEqualTo',
            'lte': 'isLessThanOrEqualTo',
            'gt': 'isGreaterThan',
            'lt': 'isLessThan',
            'eq': 'is',
            'contains': 'contains',
            'not_contains': 'doesNotContain',
            'is_empty': 'isEmpty',
            'is_not_empty': 'isNotEmpty',
        }
        return operator_map.get(operator, 'is')
