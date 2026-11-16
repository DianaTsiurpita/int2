# Run from the project directory in Windows PowerShell 5.1+.
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path '.\secrets' | Out-Null
function New-RandomSecret([int]$bytes) {
    $buffer = New-Object byte[] $bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return [Convert]::ToBase64String($buffer)
}
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
foreach ($item in @(@('db_password',24), @('jwt_secret_key',48))) {
    $path = Join-Path (Get-Location).Path ('secrets\' + $item[0])
    if (-not (Test-Path $path)) {
        [System.IO.File]::WriteAllText($path, (New-RandomSecret ([int]$item[1])), $utf8NoBom)
        Write-Host ('Created secrets/' + $item[0])
    } else {
        Write-Host ('Already exists: secrets/' + $item[0])
    }
    # Limit Windows NTFS permissions to the current user and SYSTEM.
    $user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    & icacls $path /inheritance:r /grant:r "${user}:(R,W)" 'SYSTEM:(F)' | Out-Null
}
Write-Host 'Secrets generated; values were not printed.'
