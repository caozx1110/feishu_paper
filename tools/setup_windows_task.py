#!/usr/bin/env python3
"""
Windows 定时任务设置脚本

帮助用户在 Windows 上设置定时任务，自动执行 ArXiv 论文同步
"""

import os
import sys
import subprocess
from pathlib import Path


def get_script_path():
    """获取脚本路径"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # 检查可用的脚本
    simple_sync = project_root / "scripts" / "simple_sync.py"
    scheduled_sync = project_root / "scripts" / "scheduled_sync.py"
    batch_script = project_root / "scripts" / "start_sync.bat"

    if batch_script.exists():
        return str(batch_script)
    elif simple_sync.exists():
        return f'python "{simple_sync}"'
    elif scheduled_sync.exists():
        return f'python "{scheduled_sync}"'
    else:
        raise FileNotFoundError("未找到可执行的同步脚本")


def create_task_xml(task_name, script_path, schedule_time="02:00"):
    """创建 Windows 定时任务 XML 配置"""
    xml_content = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>2023-12-01T00:00:00</Date>
    <Author>ArXiv Paper Sync</Author>
    <Description>自动同步 ArXiv 论文到飞书</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2023-12-01T{schedule_time}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{script_path.split()[0] if script_path.startswith('python') else script_path}</Command>
      <Arguments>{' '.join(script_path.split()[1:]) if script_path.startswith('python') else ''}</Arguments>
      <WorkingDirectory>{Path(__file__).parent.parent}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
    return xml_content


def setup_windows_task():
    """设置 Windows 定时任务"""
    print("🔧 Windows 定时任务设置")
    print("=" * 50)

    # 检查是否为 Windows
    if os.name != 'nt':
        print("❌ 此脚本仅适用于 Windows 系统")
        return False

    try:
        # 获取脚本路径
        script_path = get_script_path()
        print(f"📄 检测到同步脚本: {script_path}")

        # 询问用户配置
        task_name = input("📝 请输入任务名称 (默认: ArXivPaperSync): ").strip()
        if not task_name:
            task_name = "ArXivPaperSync"

        schedule_time = input("⏰ 请输入执行时间 (格式: HH:MM, 默认: 02:00): ").strip()
        if not schedule_time:
            schedule_time = "02:00"

        # 验证时间格式
        try:
            hour, minute = schedule_time.split(':')
            hour = int(hour)
            minute = int(minute)
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                raise ValueError
        except ValueError:
            print("❌ 时间格式无效，使用默认时间 02:00")
            schedule_time = "02:00"

        # 创建 XML 配置
        xml_content = create_task_xml(task_name, script_path, schedule_time)

        # 保存 XML 文件
        xml_file = Path(f"{task_name}.xml")
        with open(xml_file, 'w', encoding='utf-16') as f:
            f.write(xml_content)

        print(f"📄 已创建任务配置文件: {xml_file}")

        # 创建定时任务
        cmd = f'schtasks /create /xml "{xml_file}" /tn "{task_name}"'
        print(f"🔧 创建定时任务: {cmd}")

        if input("❓ 是否立即创建定时任务? (y/N): ").lower() == 'y':
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ 定时任务创建成功!")
                print(f"📅 任务将在每天 {schedule_time} 执行")

                # 显示如何管理任务的提示
                print("\n📋 管理定时任务:")
                print(f"  查看任务: schtasks /query /tn \"{task_name}\"")
                print(f"  运行任务: schtasks /run /tn \"{task_name}\"")
                print(f"  停用任务: schtasks /change /tn \"{task_name}\" /disable")
                print(f"  启用任务: schtasks /change /tn \"{task_name}\" /enable")
                print(f"  删除任务: schtasks /delete /tn \"{task_name}\" /f")

            else:
                print(f"❌ 定时任务创建失败: {result.stderr}")
                return False
        else:
            print("ℹ️ 可以稍后手动执行以下命令创建任务:")
            print(f"  {cmd}")

        # 清理 XML 文件
        if xml_file.exists():
            xml_file.unlink()

        return True

    except Exception as e:
        print(f"❌ 设置过程中发生错误: {e}")
        return False


def main():
    """主函数"""
    print("ArXiv 论文同步系统 - 定时任务设置工具")
    print("=" * 60)

    if not setup_windows_task():
        print("\n❌ 定时任务设置失败")
        sys.exit(1)

    print("\n✅ 设置完成!")
    print("\n💡 提示:")
    print("  - 确保计算机在定时执行时处于开启状态")
    print("  - 检查 .env 文件中的飞书配置是否正确")
    print("  - 可以在任务计划程序中查看和管理任务")


if __name__ == "__main__":
    main()
