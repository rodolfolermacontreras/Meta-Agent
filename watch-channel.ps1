# watch-channel.ps1
# Watches teamates.md for changes and alerts you when the DEV agent posts.
# Run this in a PowerShell window and leave it open while you work.
#
# Usage:
#   cd C:\Training\Microsoft\Copilot\multi-agent
#   .\watch-channel.ps1

$watchFile  = "$PSScriptRoot\teamates.md"
$checkEvery = 300   # seconds (5 minutes)
$lastHash   = ""

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Meta-Agent Communication Watcher" -ForegroundColor Cyan
Write-Host "  Watching: teamates.md" -ForegroundColor Cyan
Write-Host "  Interval: every $checkEvery seconds" -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

function Get-FileHash-Quick($path) {
    (Get-FileHash $path -Algorithm MD5).Hash
}

# Seed initial hash
if (Test-Path $watchFile) {
    $lastHash = Get-FileHash-Quick $watchFile
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Started. Baseline captured." -ForegroundColor Gray
} else {
    Write-Host "[ERROR] File not found: $watchFile" -ForegroundColor Red
    exit 1
}

while ($true) {
    Start-Sleep -Seconds $checkEvery

    if (Test-Path $watchFile) {
        $currentHash = Get-FileHash-Quick $watchFile

        if ($currentHash -ne $lastHash) {
            $lastHash = $currentHash

            # Get last 20 lines to show what changed
            $tail = Get-Content $watchFile -Tail 20

            Write-Host ""
            Write-Host "==========================================" -ForegroundColor Yellow
            Write-Host "  NEW MESSAGE in teamates.md!" -ForegroundColor Yellow
            Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Yellow
            Write-Host "==========================================" -ForegroundColor Yellow
            Write-Host ($tail -join "`n") -ForegroundColor White
            Write-Host "==========================================" -ForegroundColor Yellow
            Write-Host ""

            # Windows toast notification (works on Win10/11)
            try {
                $notify = New-Object -ComObject WScript.Shell
                $notify.Popup("New message in teamates.md — check your terminal!", 10, "Meta-Agent Update", 64) | Out-Null
            } catch {
                # Silently skip if COM not available
            }

            Write-Host "[ACTION] Go to Claude Code and ask: 'Check teamates.md for new messages and respond'" -ForegroundColor Green
            Write-Host ""
        } else {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] No changes." -ForegroundColor DarkGray
        }
    }
}
