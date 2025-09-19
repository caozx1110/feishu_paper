# ArXiv 论文同步系统 Makefile

.PHONY: help build run stop logs clean test setup

# 默认目标
help:
	@echo "ArXiv 论文同步系统 - 可用命令:"
	@echo ""
	@echo "  setup     - 初始化环境（复制 .env 模板）"
	@echo "  build     - 构建 Docker 镜像"
	@echo "  run       - 启动服务（使用 docker-compose）"
	@echo "  stop      - 停止服务"
	@echo "  restart   - 重启服务"
	@echo "  logs      - 查看日志"
	@echo "  shell     - 进入容器 shell"
	@echo "  test      - 运行测试"
	@echo "  sync      - 手动执行同步"
	@echo "  clean     - 清理容器和镜像"
	@echo "  backup    - 备份数据"
	@echo "  status    - 查看服务状态"
	@echo ""

# 初始化环境
setup:
	@echo "🔧 初始化环境..."
	@if [ ! -f .env ]; then \
		cp .env.template .env; \
		echo "✅ 已创建 .env 文件，请编辑其中的配置"; \
	else \
		echo "ℹ️  .env 文件已存在"; \
	fi
	@mkdir -p logs backup downloads
	@echo "✅ 目录创建完成"

# 构建镜像
build:
	@echo "🔨 构建 Docker 镜像..."
	docker-compose build --no-cache

# 启动服务
run: setup
	@echo "🚀 启动服务..."
	docker-compose up -d

# 停止服务
stop:
	@echo "⏹️  停止服务..."
	docker-compose down

# 重启服务
restart: stop run

# 查看日志
logs:
	@echo "📋 查看日志..."
	docker-compose logs -f

# 进入容器 shell
shell:
	@echo "🔧 进入容器..."
	docker-compose exec arxiv-sync bash

# 运行测试
test:
	@echo "🧪 运行测试..."
	docker-compose run --rm arxiv-sync python scripts/health_check.py

# 手动执行同步
sync:
	@echo "🔄 手动执行同步..."
	docker-compose exec arxiv-sync python arxiv_hydra.py --config-name=all

# 模拟同步（dry-run）
dry-run:
	@echo "🔍 模拟同步..."
	docker-compose exec arxiv-sync python scripts/scheduled_sync.py --dry-run

# 清理容器和镜像
clean:
	@echo "🧹 清理资源..."
	docker-compose down --rmi all --volumes --remove-orphans
	docker system prune -f

# 备份数据
backup:
	@echo "💾 备份数据..."
	@mkdir -p backups
	tar -czf backups/arxiv-sync-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz \
		logs backup downloads .env
	@echo "✅ 备份完成: backups/arxiv-sync-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz"

# 查看服务状态
status:
	@echo "📊 服务状态:"
	@echo ""
	@echo "容器状态:"
	@docker-compose ps
	@echo ""
	@echo "健康检查:"
	@docker-compose exec arxiv-sync python scripts/health_check.py 2>/dev/null || echo "❌ 健康检查失败"
	@echo ""
	@echo "最近的同步日志:"
	@tail -n 10 logs/scheduled_sync.log 2>/dev/null || echo "📝 暂无同步日志"

# 查看配置
config:
	@echo "📋 当前配置:"
	docker-compose config

# 更新系统
update:
	@echo "🔄 更新系统..."
	git pull
	docker-compose build --no-cache
	docker-compose up -d

# 安装开发依赖
dev-setup:
	@echo "🔧 安装开发依赖..."
	pip install -r requirements.txt

# 本地测试
local-test:
	@echo "🧪 本地测试..."
	python scripts/health_check.py
	python scripts/scheduled_sync.py --dry-run

# 查看 cron 日志
cron-logs:
	@echo "⏰ Cron 日志:"
	docker-compose exec arxiv-sync tail -f logs/cron.log
