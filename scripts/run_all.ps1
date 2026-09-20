$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$wslRepo = '/mnt/' + $repo.Substring(0,1).ToLower() + $repo.Substring(2).Replace('\','/')
wsl -d Ubuntu-22.04 -- bash "$wslRepo/scripts/run_all.sh"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
