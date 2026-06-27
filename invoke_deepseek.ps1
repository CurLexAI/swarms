#Requires -Version 5.1
# DeepSeek API Client - Local Edition

param(
    [Parameter(Mandatory=$true)]
    [string]$Prompt,

    [ValidateSet("chat", "reasoner")]
    [string]$Model = "chat",

    [int]$MaxTokens = 4096,

    [double]$Temperature = 0.7
)

# === الإعدادات ===
$apiKey = $env:DEEPSEEK_API_KEY
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "خطأ: اضبط DEEPSEEK_API_KEY في البيئة قبل التشغيل." -ForegroundColor Red
    exit 1
}
$baseUrl = "https://api.deepseek.com/v1"

$modelMap = @{
    "chat"     = "deepseek-chat"
    "reasoner" = "deepseek-reasoner"
}

# === رأس الطلب ===
$headers = @{
    "Authorization" = "Bearer $apiKey"
    "Content-Type"  = "application/json"
}

# === جسم الطلب ===
$body = @{
    model       = $modelMap[$Model]
    messages    = @(@{ role = "user"; content = $Prompt })
    max_tokens  = $MaxTokens
    temperature = $Temperature
    stream      = $false
} | ConvertTo-Json -Depth 10 -Compress

Write-Host "DeepSeek ($Model)..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod `
        -Uri "$baseUrl/chat/completions" `
        -Method Post `
        -Headers $headers `
        -Body $body `
        -TimeoutSec 120

    Write-Host "
=== الإجابة ===" -ForegroundColor Green
    Write-Host $response.choices[0].message.content

    Write-Host "
=== الإحصائيات ===" -ForegroundColor Cyan
    Write-Host "Model:        $($response.model)" -ForegroundColor White
    Write-Host "Total tokens: $($response.usage.total_tokens)" -ForegroundColor White
    Write-Host "  Prompt:     $($response.usage.prompt_tokens)" -ForegroundColor White
    Write-Host "  Completion:  $($response.usage.completion_tokens)" -ForegroundColor White

    exit 0
} catch {
    Write-Host "
خطأ: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        Write-Host "Response: $($reader.ReadToEnd())" -ForegroundColor Red
    }
    exit 1
}
