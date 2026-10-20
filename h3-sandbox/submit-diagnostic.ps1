param([string]$Server = 'http://127.0.0.1:8189', [switch]$NativeVae)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$trial = Join-Path (Split-Path -Parent $root) 'trials/2026-10-19-h3'
$graph = Get-Content -LiteralPath (Join-Path $trial 'ref2va-5frame-api.json') -Raw | ConvertFrom-Json
if ($NativeVae) { $graph.'4'.inputs.vae_name = 'minimax_h3_video_vae_fp16.safetensors' }
$body = @{ prompt = $graph; client_id = 'h3-ref2va-diagnostic' } | ConvertTo-Json -Depth 30 -Compress
$result = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType 'application/json' -Body $body
$receipt = if ($NativeVae) { 'submitted-native-vae.json' } else { 'submitted.json' }
$result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $trial $receipt) -Encoding utf8
$result | ConvertTo-Json -Depth 10
