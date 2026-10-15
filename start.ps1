# start.ps1 - Launcher for PowerShell
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

Set-Location -LiteralPath $PSScriptRoot
& "$PSScriptRoot\setup.ps1" @ScriptArgs
