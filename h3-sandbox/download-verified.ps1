param(
    [ValidateSet('model','vae','clipproj','all')]
    [string]$Only = 'all'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$trial = Join-Path (Split-Path -Parent $root) 'trials/2026-10-19-h3'
$items = @(
    @{ key='model'; repo='molbal/MiniMax-H3-GGUF'; revision='b45874371c61c49bf04096602f5527aac71b360b'; source_path='minimax-h3-ref2va-Q4_0.gguf'; name='minimax-h3-ref2va-Q4_0.gguf'; subdir='diffusion_models'; size=11377542880L; sha256='737463c522b0f78ebe157df918c272935c2b61047ba7ae303008cfc84ba81644' },
    @{ key='vae'; repo='Comfy-Org/MiniMax-H3'; revision='e5eb578a89295337b8ff433a035929ce0279e0b6'; source_path='vae/minimax_h3_video_vae_int8_convrot.safetensors'; name='minimax_h3_video_vae_int8_convrot.safetensors'; subdir='vae'; size=2811065184L; sha256='52a2c8c73583c86e4f41cdcce3a6ad0ea562987bc0bf3d60a0cef5f5c8e60c0e' },
    @{ key='clipproj'; repo='NicoLab28/ClipProj-MiniMax-H3'; revision='2ebdbcdc27a29a9607efdb221a9afcb9a0cdd808'; source_path='mmh3-4b-ClipProj-v3.1.safetensors'; name='mmh3-4b-ClipProj-v3.1.safetensors'; subdir='clip_projections'; size=26256128L; sha256='0184e5c8d666a131962506d21949c2d8a8c6f33445b7b5e347e9a7e0a5baa819' }
)
New-Item -ItemType Directory -Force -Path $trial | Out-Null
foreach ($item in $items) {
    if ($Only -ne 'all' -and $Only -ne $item.key) { continue }
    $folder = Join-Path $root "ComfyUI/models/$($item.subdir)"
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
    $final = Join-Path $folder $item.name
    $part = "$final.part"
    $url = "https://huggingface.co/$($item.repo)/resolve/$($item.revision)/$($item.source_path)?download=true"
    if (-not (Test-Path -LiteralPath $final)) {
        if (-not (Test-Path -LiteralPath $part) -or (Get-Item -LiteralPath $part).Length -ne $item.size) {
            & curl.exe --location --fail --silent --show-error --retry 8 --retry-all-errors --retry-delay 5 --continue-at - --output $part $url
            if ($LASTEXITCODE -ne 0) { throw "Download failed for $($item.key), curl exit $LASTEXITCODE" }
        }
        if ((Get-Item -LiteralPath $part).Length -ne $item.size) { throw "Byte count mismatch for $($item.key)" }
        $hash = (Get-FileHash -LiteralPath $part -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($hash -ne $item.sha256) { throw "SHA-256 mismatch for $($item.key): $hash" }
        Move-Item -LiteralPath $part -Destination $final
    } else {
        if ((Get-Item -LiteralPath $final).Length -ne $item.size) { throw "Final byte count mismatch for $($item.key)" }
        $hash = (Get-FileHash -LiteralPath $final -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($hash -ne $item.sha256) { throw "Final SHA-256 mismatch for $($item.key): $hash" }
    }
    [pscustomobject]@{ key=$item.key; source=$url; repo=$item.repo; revision=$item.revision; path=$final; bytes=$item.size; sha256=$hash; verified_at=(Get-Date).ToString('o') } |
        ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $trial "$($item.key).verified.json") -Encoding utf8
    Write-Host "VERIFIED $($item.key) $($item.size) $hash"
}
