# PowerShell OpenAI CLI Runbook (Arabic)

## Scope
هذا المستند يحفظ خطوات تشغيل أداة `ai` في PowerShell مع إدارة مفاتيح API بشكل تدريجي.

## 1) إنشاء مفتاح API
1. تسجيل الدخول إلى منصة OpenAI.
2. الانتقال إلى **API Keys**.
3. إنشاء مفتاح جديد ونسخه مباشرة.

## 2) سكربت `Invoke-ChatGPT.ps1`
```powershell
param (
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Prompt,
    [string]$Model = "gpt-4.1-mini",
    [int]$MaxTokens = 1000
)

$OutputEncoding = [System.Text.Encoding]::UTF8

$apiKey = $env:OPENAI_API_KEY
if (-not $apiKey) {
    Write-Error "OPENAI_API_KEY environment variable not set."
    exit 1
}

$headers = @{
    "Authorization" = "Bearer $apiKey"
    "Content-Type"  = "application/json"
}

$body = @{
    model = $Model
    messages = @(
        @{ role = "system"; content = "You are a helpful AI assistant that responds in clear, concise Arabic or English as appropriate." }
        @{ role = "user"; content = $Prompt }
    )
    max_completion_tokens = $MaxTokens
} | ConvertTo-Json -Depth 10

$response = Invoke-RestMethod -Uri "https://api.openai.com/v1/chat/completions" -Method Post -Headers $headers -Body $body -ContentType "application/json"
$response.choices[0].message.content
```

## 3) إدارة المفتاح عبر Environment Variables
```powershell
$env:OPENAI_API_KEY = "sk-..."  # Session فقط
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-...', 'User')
```

## 4) إضافة الأمر `ai` إلى Profile
```powershell
$functionPath = "$env:USERPROFILE\Documents\PowerShell\Functions"
New-Item -ItemType Directory -Path $functionPath -Force
```

## 5) مستوى أعلى للأمان
- يمكن استخدام Windows Credential Manager أو SecretManagement module بدل النص الصريح في الملفات.
- يمنع حفظ المفتاح داخل repository أو في سكربتات متتبعة عبر Git.

## Verification Notes
- CHANGED BUT NOT VERIFIED: هذا المستند توثيقي فقط ولا يتضمن اختبارًا تشغيليًا داخل بيئة Windows PowerShell.
