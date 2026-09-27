[CmdletBinding()]
param(
    [string]$Query = "",
    [Alias("Environment")]
    [string[]]$Provider = @(),
    [string[]]$Roots = @(),
    [int]$Top = 20,
    [switch]$Compact,
    [switch]$Brief,
    [switch]$Full,
    [switch]$Raw,
    [switch]$IncludeDisabled,
    [switch]$ListProviders
)

$ErrorActionPreference = "Stop"

function Get-ConfiguredProviderRoots {
    $builtins = @(
        @{ Provider = "Claude";   DefaultPath = Join-Path $HOME ".claude\skills";          EnvVar = "CLAUDE_SKILLS_PATH";   Direct = $true },
        @{ Provider = "OpenCode"; DefaultPath = Join-Path $HOME ".config\opencode\skills"; EnvVar = "OPENCODE_SKILLS_PATH"; Direct = $true },
        @{ Provider = "Codex";    DefaultPath = Join-Path $HOME ".codex\skills";           EnvVar = "CODEX_SKILLS_PATH";    Direct = $false },
        @{ Provider = "Cursor";   DefaultPath = Join-Path $HOME ".cursor\skills";          EnvVar = "CURSOR_SKILLS_PATH";   Direct = $true },
        @{ Provider = "Gemini";   DefaultPath = Join-Path $HOME ".gemini\skills";          EnvVar = "GEMINI_SKILLS_PATH";   Direct = $true },
        @{ Provider = "Windsurf"; DefaultPath = Join-Path $HOME ".windsurf\skills";        EnvVar = "WINDSURF_SKILLS_PATH"; Direct = $true }
    )

    foreach ($root in $builtins) {
        $path = $root.DefaultPath
        $envValue = [Environment]::GetEnvironmentVariable($root.EnvVar, "Process")
        if (-not [string]::IsNullOrWhiteSpace($envValue)) {
            $path = $envValue
        }

        [pscustomobject]@{
            Provider = $root.Provider
            Path     = $path
            Direct   = $root.Direct
        }
    }
}

function Read-SkillMetadata {
    param(
        [string]$SkillFile
    )

    if (-not (Test-Path -LiteralPath $SkillFile -PathType Leaf)) {
        return $null
    }

    $lines = @(Get-Content -LiteralPath $SkillFile -TotalCount 120 -Encoding UTF8)
    if ($lines.Count -eq 0) {
        return $null
    }

    $frontmatter = @()
    if ($lines[0].Trim() -eq "---") {
        for ($i = 1; $i -lt $lines.Count; $i++) {
            if ($lines[$i].Trim() -eq "---") {
                break
            }
            $frontmatter += $lines[$i]
        }
    }

    function Get-FrontmatterValue {
        param(
            [string[]]$Frontmatter,
            [string]$Key
        )

        foreach ($line in $Frontmatter) {
            $pattern = '^\s*' + [regex]::Escape($Key) + '\s*:\s*(.*)\s*$'
            if ($line -match $pattern) {
                return $matches[1].Trim().Trim('"').Trim("'")
            }
        }

        return ""
    }

    return [pscustomobject]@{
        Name        = Get-FrontmatterValue -Frontmatter $frontmatter -Key "name"
        Description = Get-FrontmatterValue -Frontmatter $frontmatter -Key "description"
        Disabled    = Get-FrontmatterValue -Frontmatter $frontmatter -Key "disable-model-invocation"
    }
}

$configuredRoots = @(Get-ConfiguredProviderRoots)
$activeProviders = @($Provider)
$configuredRoots = @(
    $configuredRoots | ForEach-Object {
        $_.Direct = ($activeProviders.Count -eq 0 -or $activeProviders -contains $_.Provider)
        $_
    }
)

$customRoots = @()
foreach ($rawRoot in $Roots) {
    if ($rawRoot -match '^([^=]+)=(.*)$') {
        $customProvider = $matches[1].Trim()
        $customPath = $matches[2].Trim()
    }
    else {
        $customPath = $rawRoot.Trim()
        $customProvider = Split-Path -Leaf $customPath
    }

    if ([string]::IsNullOrWhiteSpace($customProvider)) {
        $customProvider = "Custom"
    }

    $customRoots += [pscustomobject]@{
        Provider = $customProvider
        Path     = $customPath
        Direct   = $true
    }
}

if ($ListProviders) {
    @($configuredRoots + $customRoots) | ConvertTo-Json -Depth 4
    exit
}

$selectedRoots = @()
if ($Provider.Count -gt 0) {
    $selectedRoots = @($configuredRoots | Where-Object { $Provider -contains $_.Provider })
}
else {
    $selectedRoots = @($configuredRoots)
}

$selectedRoots = @($selectedRoots) + @($customRoots)

$entries = New-Object System.Collections.Generic.List[object]
$rootReports = New-Object System.Collections.Generic.List[object]

foreach ($root in $selectedRoots) {
    $rootCount = 0

    if (-not (Test-Path -LiteralPath $root.Path -PathType Container)) {
        $rootReports.Add([pscustomobject]@{
            Provider = $root.Provider
            Path     = $root.Path
            Exists   = $false
            Count    = 0
        })
        continue
    }

    foreach ($dir in Get-ChildItem -LiteralPath $root.Path -Directory -Force) {
        $skillFile = Join-Path $dir.FullName "SKILL.md"
        $metadata = Read-SkillMetadata -SkillFile $skillFile
        if ($null -eq $metadata) {
            continue
        }

        $name = if ([string]::IsNullOrWhiteSpace($metadata.Name)) { $dir.Name } else { $metadata.Name }
        $disabled = $metadata.Disabled -match '^\s*(true|1)\s*$'

        if ($disabled -and -not $IncludeDisabled) {
            continue
        }

        $haystack = @($name, $metadata.Description, $dir.Name, $dir.FullName) -join " "
        if ($Query -and $haystack -notmatch [regex]::Escape($Query)) {
            continue
        }

        $rootCount++
        $entries.Add([pscustomobject]@{
            Provider     = $root.Provider
            Availability = if ($root.Direct) { "direct" } else { "sync-first" }
            Folder       = $dir.Name
            Name         = $name
            Description  = $metadata.Description
            Disabled     = $disabled
            Path         = $dir.FullName
            SkillMd      = $skillFile
        })
    }

    $rootReports.Add([pscustomobject]@{
        Provider = $root.Provider
        Path     = $root.Path
        Exists   = $true
        Count    = $rootCount
    })
}

if ($Raw) {
    @($entries | Sort-Object Name, Provider) | ConvertTo-Json -Depth 5
    exit
}

$groups = @(
    $entries | Group-Object -Property Folder | ForEach-Object {
        $groupItems = @($_.Group | Sort-Object Provider)
        $first = $groupItems | Select-Object -First 1
        $providers = @($groupItems | ForEach-Object { $_.Provider } | Sort-Object -Unique)
        $directProviders = @(
            $groupItems | Where-Object { $_.Availability -eq "direct" } | ForEach-Object { $_.Provider }
        )
        $paths = @{}
        foreach ($item in $groupItems) {
            $paths[$item.Provider] = $item.SkillMd
        }

        [pscustomobject]@{
            Name         = $first.Name
            Folder       = $_.Name
            Description  = $first.Description
            Disabled     = $first.Disabled
            Availability = if ($directProviders.Count -gt 0) { "direct" } else { "sync-first" }
            Providers    = $providers
            Paths        = $paths
        }
    }
)

$groups = @($groups | Sort-Object Name)

$uniqueGroups = @($groups)
$directGroups = @($groups | Where-Object { $_.Availability -eq "direct" })
$syncFirstGroups = @($groups | Where-Object { $_.Availability -eq "sync-first" })

if ($Top -gt 0 -and $groups.Count -gt $Top) {
    $groups = @($groups | Select-Object -First $Top)
}

if ($Brief -or (-not $Full -and -not $Compact)) {
    $briefOutput = @($groups | ForEach-Object {
        [pscustomobject]@{
            Name         = $_.Name
            Availability = $_.Availability
            Providers    = ($_.Providers -join ", ")
        }
    })
    if ($briefOutput.Count -eq 0) { "[]" } else { $briefOutput | ConvertTo-Json -Depth 5 }
    exit
}

if ($Compact) {
    $compactOutput = @($groups | ForEach-Object {
        $description = [string]$_.Description
        if ($description.Length -gt 140) {
            $description = $description.Substring(0, 140) + "..."
        }
        [pscustomobject]@{
            Name         = $_.Name
            Availability = $_.Availability
            Providers    = ($_.Providers -join ", ")
            Description  = $description
        }
    })
    if ($compactOutput.Count -eq 0) { "[]" } else { $compactOutput | ConvertTo-Json -Depth 5 }
    exit
}

$providerCounts = @{}
foreach ($entry in $entries) {
    $key = $entry.Provider
    if ($providerCounts.ContainsKey($key)) {
        $providerCounts[$key] = [int]$providerCounts[$key] + 1
    }
    else {
        $providerCounts[$key] = 1
    }
}

[pscustomobject]@{
    generated_at = (Get-Date).ToString("s")
    query        = $Query
    providers    = if ($Provider.Count -gt 0) { $Provider } else { @($selectedRoots | ForEach-Object { $_.Provider }) }
    top          = if ($Top -gt 0) { $Top } else { $null }
    scan_roots   = $rootReports
    counts       = [pscustomobject]@{
        total_entries     = $entries.Count
        unique_skills     = $uniqueGroups.Count
        direct_skills     = $directGroups.Count
        sync_first_skills = $syncFirstGroups.Count
        providers         = $providerCounts
    }
    skills       = $groups
} | ConvertTo-Json -Depth 6
