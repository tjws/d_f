param(
  [string]$ComposeFile = "compose.yml",
  [switch]$Prune
)

# 供 Windows Task Scheduler 调用：使用 PostgreSQL 容器自带工具，避免后端镜像安装数据库客户端。
$backupDirectory = Join-Path (Get-Location) "backend/backups"
New-Item -ItemType Directory -Force -Path $backupDirectory | Out-Null
$stamp = Get-Date -Format "yyyyMMddTHHmmssZ"
$filename = "k12_sales_$stamp.dump"
$containerPath = "/tmp/$filename"
$localPath = Join-Path $backupDirectory $filename

$postgresUser = "k12_app"
$postgresDatabase = "k12_sales"
if (Test-Path "infra/local.env") {
  foreach ($line in Get-Content "infra/local.env") {
    if ($line -match '^POSTGRES_USER=(.*)$') { $postgresUser = $Matches[1].Trim() }
    if ($line -match '^POSTGRES_DB=(.*)$') { $postgresDatabase = $Matches[1].Trim() }
  }
}

docker compose --env-file infra/local.env -f $ComposeFile exec -T postgres pg_dump -U $postgresUser -d $postgresDatabase --format=custom --no-owner --file $containerPath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose --env-file infra/local.env -f $ComposeFile cp "postgres:$containerPath" $localPath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose --env-file infra/local.env -f $ComposeFile exec -T postgres pg_restore --list --file - $containerPath | Out-Null
$verifyExit = $LASTEXITCODE
docker compose --env-file infra/local.env -f $ComposeFile exec -T postgres rm -f $containerPath | Out-Null
if ($verifyExit -ne 0) { exit $verifyExit }

if ($Prune) {
  $pruneEnabled = $false
  if (Test-Path "infra/local.env") {
    $pruneEnabled = (Get-Content "infra/local.env" | Select-String '^BACKUP_PRUNE_ENABLED=1$') -ne $null
  }
  if (-not $pruneEnabled) { Write-Error "清理旧备份需要 infra/local.env 中 BACKUP_PRUNE_ENABLED=1"; exit 2 }
  $cutoff = (Get-Date).AddDays(-30)
  Get-ChildItem -LiteralPath $backupDirectory -Filter "*.dump" -File |
    Where-Object { $_.LastWriteTime -lt $cutoff -and $_.FullName -ne $localPath } |
    Remove-Item -Force
}
Write-Output "backup_job_verified=$localPath"
