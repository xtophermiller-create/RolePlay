[CmdletBinding()]
param(
    [switch]$BuildFrontend
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$deploy = @{
    SshHost = "37.140.192.114"
    SshUser = "u3594164"
    SshPort = 22
    SiteRoot = "/var/www/u3594164/data/apps/roleplay-trainer"
    PublicBaseUrl = "https://roleplay-trainer.online"
    PassengerRestartFile = "/var/www/u3594164/data/www/roleplay-trainer.online/.restart-app"
    RemotePython = "/opt/python/python-3.14/bin/python3.14"
    LocalPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    IdentityFile = Join-Path $HOME ".ssh\roleplaytrainer_ed25519"
}

if ($BuildFrontend) {
    $nodeDirectory = Join-Path $env:ProgramFiles "nodejs"
    if (-not (Get-Command npm -ErrorAction SilentlyContinue) -and
        (Test-Path (Join-Path $nodeDirectory "npm.cmd"))) {
        $env:Path = "$nodeDirectory;$env:Path"
    }
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "Node.js/npm is required with -BuildFrontend."
    }
} else {
    $deploy["SkipFrontendBuild"] = $true
}

& (Join-Path $PSScriptRoot "scripts\deploy.ps1") @deploy
