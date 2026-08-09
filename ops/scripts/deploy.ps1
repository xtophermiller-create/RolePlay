[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SshHost,
    [Parameter(Mandatory = $true)][string]$SshUser,
    [Parameter(Mandatory = $true)][string]$SiteRoot,
    [Parameter(Mandatory = $true)][string]$PublicBaseUrl,
    [Parameter(Mandatory = $true)][string]$PassengerRestartFile,
    [ValidateRange(1, 65535)][int]$SshPort = 22,
    [string]$IdentityFile,
    [string]$RemotePython = "python3.14",
    [string]$LocalPython = "python",
    [switch]$SkipFrontendBuild
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-ExternalCommand {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "'$Command' failed with exit code $LASTEXITCODE."
    }
}

if ($SshHost -notmatch '^[A-Za-z0-9.-]+$') {
    throw "SshHost must be a hostname or IP address without URL syntax."
}
if ($SshUser -notmatch '^[A-Za-z0-9._-]+$') {
    throw "SshUser contains unsupported characters."
}
if ($SiteRoot -notmatch '^/[A-Za-z0-9._/-]+$' -or $SiteRoot.Contains("..")) {
    throw "SiteRoot must be an absolute Linux path without spaces or '..'."
}
if ($PassengerRestartFile -notmatch '^/[A-Za-z0-9._/-]+$' -or
    $PassengerRestartFile.Contains("..")) {
    throw "PassengerRestartFile must be an absolute Linux path without spaces or '..'."
}
if ($RemotePython -notmatch '^[A-Za-z0-9._/-]+$') {
    throw "RemotePython must be a command or absolute path without spaces."
}
$publicUri = $null
if (-not [Uri]::TryCreate($PublicBaseUrl, [UriKind]::Absolute, [ref]$publicUri) -or
    $publicUri.Scheme -ne "https" -or -not $publicUri.Host -or
    $publicUri.AbsolutePath -ne "/" -or $publicUri.Query -or $publicUri.Fragment -or
    $publicUri.UserInfo) {
    throw "PublicBaseUrl must be an HTTPS origin without path/query, for example https://example.ru."
}
$PublicBaseUrl = $PublicBaseUrl.TrimEnd("/")

Assert-ExternalCommand "scp"
Assert-ExternalCommand "ssh"
Assert-ExternalCommand $LocalPython
if (-not $SkipFrontendBuild) {
    Assert-ExternalCommand "npm"
}
if ($IdentityFile -and -not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) {
    throw "Identity file does not exist: $IdentityFile"
}

# ops/scripts → repo root
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$opsScripts = Join-Path $root "ops\scripts"
$releaseId = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ") +
    "-" + [Guid]::NewGuid().ToString("N").Substring(0, 8)
$work = Join-Path ([System.IO.Path]::GetTempPath()) "roleplay-trainer-$releaseId"
$stage = Join-Path $work "artifact"
$archive = Join-Path $work "$releaseId.zip"

Push-Location $root
try {
    New-Item -ItemType Directory -Path $stage -Force | Out-Null

    if (-not $SkipFrontendBuild) {
        Invoke-Checked "npm" @("ci", "--ignore-scripts")
        Invoke-Checked "npm" @("run", "build")
    }

    $previousPycachePrefix = $env:PYTHONPYCACHEPREFIX
    $env:PYTHONPYCACHEPREFIX = Join-Path $work "pycache"
    try {
        Invoke-Checked $LocalPython @(
            "-m", "compileall", "-q",
            (Join-Path $root "app"),
            (Join-Path $root "web"),
            $opsScripts,
            (Join-Path $root "passenger_wsgi.py")
        )
    } finally {
        $env:PYTHONPYCACHEPREFIX = $previousPycachePrefix
    }

    $requirements = Get-Content -LiteralPath (Join-Path $root "requirements-production.txt")
    $unpinned = $requirements | Where-Object {
        $_ -and -not $_.TrimStart().StartsWith("#") -and $_ -notmatch '^[A-Za-z0-9_.-]+==[^=]+$'
    }
    if ($unpinned) {
        throw "requirements-production.txt contains unpinned or invalid entries: $($unpinned -join ', ')"
    }

    $directories = @("app", "web", "migrations")
    $files = @(
        "passenger_wsgi.py",
        "requirements-production.txt",
        "package.json",
        "package-lock.json"
    )
    foreach ($directory in $directories) {
        Copy-Item -Path (Join-Path $root $directory) -Destination $stage -Recurse `
            -Exclude "__pycache__", "*.pyc", "*.pyo"
    }
    # На сервере оставляем привычный путь scripts/ (cron/docs), источник — ops/scripts.
    New-Item -ItemType Directory -Path (Join-Path $stage "scripts") | Out-Null
    $runtimeScripts = @(
        "backup.py",
        "cron_backup.sh",
        "import_sqlite_to_mysql.py",
        "restore.py",
        "release_check.py"
    )
    foreach ($script in $runtimeScripts) {
        Copy-Item -LiteralPath (Join-Path $opsScripts $script) `
            -Destination (Join-Path $stage "scripts")
    }
    foreach ($file in $files) {
        Copy-Item -LiteralPath (Join-Path $root $file) -Destination $stage
    }

    Get-ChildItem -LiteralPath $stage -Recurse -Directory -Force |
        Where-Object { $_.Name -eq "__pycache__" } |
        Remove-Item -Recurse -Force
    $forbidden = Get-ChildItem -LiteralPath $stage -Recurse -Force | Where-Object {
        $_.Name -eq ".env" -or
        ($_.PSIsContainer -and $_.Name -in @("storage", "backups")) -or
        (-not $_.PSIsContainer -and $_.Extension -in @(".db", ".sqlite", ".sqlite3"))
    }
    if ($forbidden) {
        throw "Safety check failed: forbidden env/storage/database content entered the artifact."
    }

    # Compress-Archive stores Windows backslashes in ZIP entry names. GNU unzip
    # on REG.RU treats those as malformed paths, so build a portable archive.
    $zipScript = @'
import pathlib
import sys
import zipfile

stage = pathlib.Path(sys.argv[1])
archive = pathlib.Path(sys.argv[2])
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as output:
    for path in sorted(stage.rglob('*')):
        if path.is_file():
            output.write(path, path.relative_to(stage).as_posix())
'@
    Invoke-Checked $LocalPython @("-c", $zipScript, $stage, $archive)
    $sha256 = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()

    $sshArgs = @("-p", "$SshPort")
    $scpArgs = @("-P", "$SshPort")
    if ($IdentityFile) {
        $sshArgs += @("-i", $IdentityFile)
        $scpArgs += @("-i", $IdentityFile)
    }
    $target = "$SshUser@$SshHost"
    $incoming = "$SiteRoot/incoming"

    Invoke-Checked "ssh" ($sshArgs + @($target, "mkdir -p '$incoming' && chmod 700 '$incoming'"))
    Invoke-Checked "scp" ($scpArgs + @(
        $archive,
        (Join-Path $opsScripts "deploy_remote.sh"),
        "${target}:$incoming/"
    ))

    $remoteCommand = "sed -i 's/\r$//' '$incoming/deploy_remote.sh' && " +
        "bash '$incoming/deploy_remote.sh' '$SiteRoot' '$releaseId' " +
        "'$incoming/$releaseId.zip' '$sha256' '$RemotePython' '$PublicBaseUrl' " +
        "'$PassengerRestartFile'"
    Invoke-Checked "ssh" ($sshArgs + @($target, $remoteCommand))
    Write-Host "Deployment completed: $releaseId"
} finally {
    if (Test-Path -LiteralPath $work) {
        Remove-Item -LiteralPath $work -Recurse -Force
    }
    Pop-Location
}
