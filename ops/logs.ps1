[CmdletBinding()]
param(
    [ValidateSet("error", "access")]
    [string]$Type = "error",
    [ValidateRange(1, 2000)]
    [int]$Lines = 100,
    [switch]$Follow
)

$log = if ($Type -eq "error") {
    "/var/www/u3594164/data/logs/roleplay-trainer.online.error.log"
} else {
    "/var/www/u3594164/data/logs/roleplay-trainer.online.access.log"
}

$arguments = @(
    "-i", (Join-Path $HOME ".ssh\roleplaytrainer_ed25519"),
    "-o", "BatchMode=yes",
    "u3594164@37.140.192.114"
)
$remote = if ($Follow) {
    "tail -n $Lines -f '$log'"
} else {
    "tail -n $Lines '$log'"
}

& ssh @arguments $remote
if ($LASTEXITCODE -ne 0) {
    throw "Could not read the remote $Type log."
}
