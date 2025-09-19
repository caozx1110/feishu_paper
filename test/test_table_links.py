#!/usr/bin/env python3
"""
测试群聊通知中的表格链接功能
"""

import os
import sys
from dotenv import load_dotenv

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_table_link_generation():
    """测试表格链接生成功能"""
    print("🔗 测试表格链接生成功能...")
    
    try:
        from feishu_chat_notification import FeishuChatNotifier, ChatNotificationConfig
        from feishu_bitable_connector import FeishuBitableConfig
        
        # 创建配置
        config = FeishuBitableConfig(
            app_id=os.getenv('FEISHU_APP_ID', ''),
            app_secret=os.getenv('FEISHU_APP_SECRET', ''),
            tenant_access_token=os.getenv('FEISHU_TENANT_ACCESS_TOKEN'),
            user_access_token=os.getenv('FEISHU_USER_ACCESS_TOKEN'),
            app_token=os.getenv('FEISHU_BITABLE_APP_TOKEN', '')
        )
        
        chat_config = ChatNotificationConfig(enabled=True)
        notifier = FeishuChatNotifier(config, chat_config)
        
        # 测试通过表格名称生成链接
        print("   📊 测试通过表格名称生成链接...")
        table_link1 = notifier.generate_table_link(table_name="移动操作论文表")
        if table_link1:
            print(f"   ✅ 成功生成链接: {table_link1}")
        else:
            print("   ⚠️ 未能生成链接（可能表格不存在）")
        
        # 测试直接使用table_id生成链接
        print("   🆔 测试直接使用table_id生成链接...")
        test_table_id = "tblRpDN8cd9Ihl97"  # 移动操作论文表的ID
        table_link2 = notifier.generate_table_link(table_id=test_table_id)
        if table_link2:
            print(f"   ✅ 成功生成链接: {table_link2}")
        else:
            print("   ❌ 链接生成失败")
        
        return table_link1 or table_link2
        
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False

def test_notification_with_links():
    """测试包含表格链接的通知消息"""
    print("\n📢 测试包含表格链接的通知消息...")
    
    try:
        from feishu_chat_notification import FeishuChatNotifier, ChatNotificationConfig
        from feishu_bitable_connector import FeishuBitableConfig
        
        config = FeishuBitableConfig(
            app_id=os.getenv('FEISHU_APP_ID', ''),
            app_secret=os.getenv('FEISHU_APP_SECRET', ''),
            tenant_access_token=os.getenv('FEISHU_TENANT_ACCESS_TOKEN'),
            user_access_token=os.getenv('FEISHU_USER_ACCESS_TOKEN'),
            app_token=os.getenv('FEISHU_BITABLE_APP_TOKEN', '')
        )
        
        chat_config = ChatNotificationConfig(enabled=True, min_papers_threshold=1)
        notifier = FeishuChatNotifier(config, chat_config)
        
        # 准备测试数据
        test_stats = {
            "移动操作": {
                "new_count": 2,
                "total_count": 12,
                "table_name": "移动操作论文表"
            }
        }
        
        test_papers = {
            "移动操作": [{
                "title": "M4Diffuser: Multi-View Diffusion Policy with Manipulability-Aware Control",
                "authors_str": "Ju Dong, Lei Zhang, Liding Zhang",
                "relevance_score": 407.64,
                "arxiv_id": "2509.14980",
                "paper_url": "http://arxiv.org/abs/2509.14980v1",
                "summary": "Mobile manipulation requires coordinated control of mobile base and robotic arm..."
            }]
        }
        
        # 生成表格链接
        test_table_links = {}
        table_link = notifier.generate_table_link(table_name="移动操作论文表")
        if table_link:
            test_table_links["移动操作"] = table_link
            print(f"   🔗 表格链接: {table_link}")
        
        # 测试富文本消息
        print("   📝 测试富文本消息格式...")
        rich_message = notifier.create_paper_update_message(test_stats, test_papers, test_table_links)
        print("   ✅ 富文本消息创建成功")
        
        # 检查消息中是否包含链接
        message_content = rich_message.get('content', {})
        elements = message_content.get('elements', [])
        has_link = False
        for element in elements:
            text_content = element.get('text', {}).get('content', '')
            if '查看完整表格' in text_content and 'feishu.cn' in text_content:
                has_link = True
                print(f"   ✅ 发现表格链接: {text_content}")
                break
        
        if not has_link and test_table_links:
            print("   ⚠️ 富文本消息中未找到表格链接")
        
        # 测试简单文本消息
        print("   📄 测试简单文本消息格式...")
        simple_message = notifier.create_simple_text_message(test_stats, test_papers, test_table_links)
        simple_text = simple_message.get('content', {}).get('text', '')
        
        if test_table_links and test_table_links.get('移动操作') in simple_text:
            print("   ✅ 简单文本消息包含表格链接")
        elif test_table_links:
            print("   ⚠️ 简单文本消息中未找到表格链接")
        
        print("   📤 尝试发送测试通知...")
        # 注意：这里会实际发送消息到群聊
        success = notifier.notify_paper_updates(test_stats, test_papers, test_table_links)
        
        if success:
            print("   ✅ 通知发送成功，请检查群聊中的表格链接")
        else:
            print("   ⚠️ 通知发送失败或跳过")
        
        return success
        
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback
        print(f"   🔍 详细错误: {traceback.format_exc()}")
        return False

def show_table_link_info():
    """显示表格链接相关信息"""
    print("\n📋 表格链接功能说明:")
    print("=" * 40)
    print("✅ 新增功能:")
    print("   - 群聊通知中自动包含多维表格链接")
    print("   - 支持富文本消息中的链接按钮")
    print("   - 支持纯文本消息中的链接地址")
    print("   - 自动根据表格名称查找表格ID")
    
    print("\n🔗 链接格式:")
    app_token = os.getenv('FEISHU_BITABLE_APP_TOKEN', 'YOUR_APP_TOKEN')
    print(f"   https://feishu.cn/base/{app_token}?table=TABLE_ID&view=vew")
    
    print("\n📱 用户体验:")
    print("   - 点击链接直接跳转到对应的多维表格")
    print("   - 可以查看完整的论文数据和排序视图")
    print("   - 支持在线编辑和协作")

def main():
    """主函数"""
    print("🔗 飞书群聊通知表格链接功能测试")
    print("=" * 50)
    
    load_dotenv()
    
    # 检查基础配置
    required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_BITABLE_APP_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 缺少必要配置: {', '.join(missing_vars)}")
        return
    
    has_token = bool(os.getenv('FEISHU_TENANT_ACCESS_TOKEN')) or bool(os.getenv('FEISHU_USER_ACCESS_TOKEN'))
    if not has_token:
        print("❌ 缺少访问令牌")
        return
    
    # 运行测试
    print("🚀 开始测试...")
    
    # 1. 测试链接生成
    link_success = test_table_link_generation()
    
    if link_success:
        # 2. 测试完整通知功能
        notification_success = test_notification_with_links()
        
        # 3. 显示功能说明
        show_table_link_info()
        
        if notification_success:
            print("\n🎉 所有测试通过！表格链接功能正常工作")
        else:
            print("\n⚠️ 链接生成正常，但通知发送失败")
            print("💡 可能原因:")
            print("   - 缺少群聊发送权限")
            print("   - 机器人未加入群聊")
    else:
        print("\n❌ 表格链接生成失败")
        print("💡 请检查:")
        print("   - FEISHU_BITABLE_APP_TOKEN 是否正确")
        print("   - 多维表格是否存在")
        print("   - 访问权限是否充足")

if __name__ == "__main__":
    main()
