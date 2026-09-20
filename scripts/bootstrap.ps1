$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$wslRepo = '/mnt/' + $repoPath.Substring(0,1).ToLower() + $repoPath.Substring(2).Replace('\','/')
wsl -d Ubuntu-22.04 -- bash "$wslRepo/scripts/bootstrap.sh"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
