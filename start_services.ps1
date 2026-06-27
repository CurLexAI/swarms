# سكريبت تشغيل جميع الخدمات
Write-Host "=== تشغيل Bayyina Services ===" -ForegroundColor Cyan

# Ollama
Start-Process "ollama" "serve" -WindowStyle Hidden
Start-Sleep -Seconds 2

# Qdrant (عبر Docker)
docker start qdrant 2>$null
if ($?) {
    Write-Host "Qdrant جاهز: http://localhost:6333" -ForegroundColor Green
} else {
    Write-Host "Qdrant يحتاج تشغيل: docker run -d --name qdrant -p 6333:6333 qdrant/qdrant" -ForegroundColor Yellow
}

# التحقق
Start-Sleep -Seconds 3
$services = @(
    @{Name="Ollama";    URL="http://127.0.0.1:11434/api/tags"},
    @{Name="Qdrant";    URL="http://localhost:6333/healthz"}
)

foreach ($svc in $services) {
    try {
        $r = Invoke-WebRequest -Uri $svc.URL -UseBasicParsing -TimeoutSec 3
        Write-Host "✅ $($svc.Name): يعمل" -ForegroundColor Green
    } catch {
        Write-Host "❌ $($svc.Name): متوقف" -ForegroundColor Red
    }
}

Write-Host "`n=== النماذج المحلية المتاحة ===" -ForegroundColor Cyan
ollama list
