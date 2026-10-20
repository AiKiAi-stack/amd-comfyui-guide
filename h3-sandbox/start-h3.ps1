param([switch]$Cpu, [switch]$GpuVae, [double]$ReserveVram = 2.0)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Join-Path $root 'ComfyUI'
$trial = Join-Path (Split-Path -Parent $root) 'trials/2026-10-19-h3'
foreach ($dir in @('input','output','temp','user')) {
    New-Item -ItemType Directory -Force -Path (Join-Path $trial $dir) | Out-Null
}
$env:PYTHONDONTWRITEBYTECODE = '1'
$h3Args = @(
    (Join-Path $repo 'main.py'),
    '--listen', '127.0.0.1', '--port', '8189', '--disable-auto-launch',
    '--input-directory', (Join-Path $trial 'input'),
    '--output-directory', (Join-Path $trial 'output'),
    '--temp-directory', (Join-Path $trial 'temp'),
    '--user-directory', (Join-Path $trial 'user'),
    '--disable-assets', '--disable-async-offload'
)
if ($Cpu -or -not $GpuVae) { $h3Args += '--cpu-vae' }
if ($Cpu) { $h3Args += '--cpu' } else {
    $h3Args += @('--lowvram', '--reserve-vram', $ReserveVram.ToString([Globalization.CultureInfo]::InvariantCulture))
}
Push-Location $repo
try {
    & 'D:/AI/barely-comfy/.venv/Scripts/python.exe' @h3Args *>&1 |
        Tee-Object -FilePath (Join-Path $trial 'server-8189.log')
    if ($LASTEXITCODE -ne 0) { throw "H3 ComfyUI exited with code $LASTEXITCODE" }
} finally {
    Pop-Location
}
