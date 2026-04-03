Param(
    [string]$Start = "20220101",
    [string]$End = (Get-Date -Format "yyyyMMdd"),
    [string]$Db = "data\\tushare\\db\\quant_data.db",
    [double]$Sleep = 0.2,
    [int]$BatchSize = 500,
    [string]$Python = "python"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projRoot = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $projRoot

$fetch = "scripts\fetch_history_batch.py"
$coverage = "scripts\check_coverage.py"
$log = "BATCH_INGEST_DOCUMENTATION.md"

New-Item -ItemType Directory -Force -Path "data\\tushare\\db" | Out-Null
New-Item -ItemType Directory -Force -Path "data\\tushare\\reports" | Out-Null
New-Item -ItemType Directory -Force -Path "data\\tushare\\state" | Out-Null

Write-Host "=== 批量落数开始 (ALL) ==="
& $Python $fetch --universe all --start $Start --end $End --db $Db --sleep $Sleep --batch-size $BatchSize
if ($LASTEXITCODE -ne 0) {
    Write-Host "落数进程返回非0，检查日志后可再次运行以续传（已启用断点记录）" -ForegroundColor Yellow
}

Write-Host "=== 生成覆盖率报告 (DB) ==="
$stamp = Get-Date -Format "yyyyMMdd_HHmm"
$report = "data\\tushare\\reports\\coverage_db_${Start}_${End}_$stamp.csv"
& $Python $coverage --universe db --start $Start --end $End --db $Db --output $report
if ($LASTEXITCODE -eq 0) {
    Write-Host "报告已生成: $report"
    Write-Host "Markdown 概览: $($report.Replace('.csv','.md'))"
    $now = Get-Date -Format "yyyy-MM-dd HH:mm"
    "`n### $now" | Out-File -FilePath $log -Append -Encoding UTF8
    "- 执行方式：run_batches.ps1" | Out-File -FilePath $log -Append -Encoding UTF8
    "- 参数：universe=all, start=$Start, end=$End, db=$Db, sleep=$Sleep, batch_size=$BatchSize" | Out-File -FilePath $log -Append -Encoding UTF8
    "- 报告：$report" | Out-File -FilePath $log -Append -Encoding UTF8
} else {
    Write-Host "覆盖率报告生成失败，请检查参数与数据库" -ForegroundColor Yellow
}

Write-Host "=== 完成 ==="

