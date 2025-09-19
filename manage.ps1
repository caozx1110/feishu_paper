# ArXiv Paper Sync Management Script for Windows
param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "ArXiv Paper Sync System - Available Commands:" -ForegroundColor Green
    Write-Host ""
    Write-Host "  .\manage.ps1 setup      - Initialize environment" -ForegroundColor Yellow
    Write-Host "  .\manage.ps1 run        - Start Docker services" -ForegroundColor Yellow
    Write-Host "  .\manage.ps1 stop       - Stop Docker services" -ForegroundColor Yellow
    Write-Host "  .\manage.ps1 logs       - View logs" -ForegroundColor Yellow
    Write-Host "  .\manage.ps1 sync       - Execute manual sync" -ForegroundColor Yellow
    Write-Host "  .\manage.ps1 dry-run    - Simulate sync" -ForegroundColor Yellow
    Write-Host "  .\manage.ps1 test       - Run local tests" -ForegroundColor Yellow
    Write-Host "  .\manage.ps1 status     - Show service status" -ForegroundColor Yellow
    Write-Host "  .\manage.ps1 backup     - Backup data" -ForegroundColor Yellow
    Write-Host ""
}

function Initialize-Environment {
    Write-Host "Initializing environment..." -ForegroundColor Blue
    
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.template" ".env"
        Write-Host "Created .env file, please edit the configuration" -ForegroundColor Green
    } else {
        Write-Host ".env file already exists" -ForegroundColor Yellow
    }
    
    @("logs", "backup", "downloads") | ForEach-Object {
        if (-not (Test-Path $_)) {
            New-Item -ItemType Directory -Path $_ -Force | Out-Null
        }
    }
    Write-Host "Directories created successfully" -ForegroundColor Green
}

function Start-Service {
    Write-Host "Starting Docker services..." -ForegroundColor Blue
    Initialize-Environment
    docker-compose up -d
}

function Stop-Service {
    Write-Host "Stopping Docker services..." -ForegroundColor Blue
    docker-compose down
}

function Show-Logs {
    Write-Host "Viewing logs..." -ForegroundColor Blue
    docker-compose logs -f
}

function Execute-Sync {
    Write-Host "Executing manual sync..." -ForegroundColor Blue
    python scripts/simple_sync.py
}

function Execute-DryRun {
    Write-Host "Simulating sync..." -ForegroundColor Blue
    python scripts/scheduled_sync.py --dry-run
}

function Run-LocalTest {
    Write-Host "Running local tests..." -ForegroundColor Blue
    python scripts/health_check.py
    python scripts/scheduled_sync.py --dry-run
}

function Show-Status {
    Write-Host "Service Status:" -ForegroundColor Blue
    Write-Host ""
    Write-Host "Docker containers:" -ForegroundColor Yellow
    docker-compose ps
    Write-Host ""
    if (Test-Path "logs/scheduled_sync.log") {
        Write-Host "Recent sync logs:" -ForegroundColor Yellow
        Get-Content "logs/scheduled_sync.log" -Tail 5
    } else {
        Write-Host "No sync logs found" -ForegroundColor Gray
    }
}

function Backup-Data {
    Write-Host "Backing up data..." -ForegroundColor Blue
    $BackupDir = "backups"
    if (-not (Test-Path $BackupDir)) {
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    }
    
    $BackupFile = "$BackupDir/arxiv-sync-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss').zip"
    Compress-Archive -Path "logs", "backup", "downloads", ".env" -DestinationPath $BackupFile -Force
    Write-Host "Backup completed: $BackupFile" -ForegroundColor Green
}

# Main execution
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "setup" { Initialize-Environment }
    "run" { Start-Service }
    "stop" { Stop-Service }
    "logs" { Show-Logs }
    "sync" { Execute-Sync }
    "dry-run" { Execute-DryRun }
    "test" { Run-LocalTest }
    "status" { Show-Status }
    "backup" { Backup-Data }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Show-Help
    }
}
