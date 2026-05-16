#!/usr/bin/env powershell
<#
.SYNOPSIS
    Superpowers-ZH Git Submodule Deploy Tool
.DESCRIPTION
    Deploy 23 AI coding skills via Git Submodule to any project.
#>

param(
    [ValidateSet("Install", "Update", "Status")]
    [string]$Mode = "Install",
    [string]$TargetProject = (Get-Location).Path,
    [string]$RepoUrl = "https://github.com/xianweibo/superpowers-skills.git"
)

$ErrorActionPreference = "Stop"

$SubmoduleName = ".trae/superpowers-skills"
$SkillsLinkDir = ".trae/skills"
$StagingDir = ".trae/skills-staging"

$GeneralSkills = @(
    "brainstorming", "test-driven-development", "systematic-debugging",
    "requesting-code-review", "writing-plans", "executing-plans",
    "using-git-worktrees", "subagent-driven-development",
    "finishing-a-development-branch", "verification-before-completion",
    "dispatching-parallel-agents", "receiving-code-review",
    "chinese-code-review", "chinese-git-workflow",
    "chinese-documentation", "chinese-commit-conventions",
    "mcp-builder", "workflow-runner",
    "using-superpowers", "writing-skills",
    "team-workflow-session", "team-git-branch-policy",
    "team-code-review-standard"
)

function Write-Banner {
    param([string]$t)
    $line = "=" * 60
    Write-Host ""
    Write-Host $line -ForegroundColor Cyan
    Write-Host ("  " + $t) -ForegroundColor Cyan
    Write-Host $line -ForegroundColor Cyan
}

function Install-Submodule {
    Write-Banner "Submodule Install Mode"

    $projRoot = $TargetProject
    $subPath = Join-Path $projRoot $SubmoduleName

    Write-Host "[1/4] Adding Git Submodule..." -ForegroundColor Yellow

    Push-Location $projRoot
    try {
        if (Test-Path $SubmoduleName) {
            Write-Host "   Submodule already exists, skipping" -ForegroundColor DarkGray
        } else {
            git submodule add $RepoUrl $SubmoduleName
            Write-Host ("   OK: " + $RepoUrl + " -> " + $SubmoduleName) -ForegroundColor Green
        }
    } catch {
        Write-Host "   Remote unavailable, trying local source..." -ForegroundColor Yellow
        $localSource = Join-Path (Split-Path $PSScriptRoot) "superpowers-skills-source"
        if (Test-Path $localSource) {
            git submodule add $localSource $SubmoduleName
            Write-Host ("   OK: local source -> " + $SubmoduleName) -ForegroundColor Green
        } else {
            Write-Host "   ERROR: Source repo not found!" -ForegroundColor Red
            Pop-Location
            return
        }
    }
    Pop-Location

    Write-Host "[2/4] Extracting Skills to staging..." -ForegroundColor Yellow

    $srcSkills = Join-Path $subPath ".trae\skills"
    $staging = Join-Path $projRoot $StagingDir

    if (-not (Test-Path $srcSkills)) {
        $srcSkills = Join-Path $subPath "skills"
    }

    New-Item -ItemType Directory -Force -Path $staging | Out-Null

    $count = 0
    foreach ($s in $GeneralSkills) {
        $src = Join-Path $srcSkills $s
        $dst = Join-Path $staging $s
        if (Test-Path (Join-Path $src "SKILL.md")) {
            Copy-Item -Recurse -Force $src $dst
            $count++
        }
    }
    Write-Host ("   OK: extracted " + $count + " skills") -ForegroundColor Green

    Write-Host "[3/4] Creating symlink..." -ForegroundColor Yellow

    $linkPath = Join-Path $projRoot $SkillsLinkDir

    if (Test-Path $linkPath) {
        $item = Get-Item $linkPath
        if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            (Get-Item $linkPath).Delete()
        } else {
            Remove-Item -Recurse -Force $linkPath
        }
    }

    try {
        New-Item -ItemType Junction -Path $linkPath -TargetPath (Resolve-Path $staging) | Out-Null
        Write-Host ("   OK: symlink " + $SkillsLinkDir + " -> staging") -ForegroundColor Green
    } catch {
        Copy-Item -Recurse -Force $staging $linkPath
        Write-Host "   OK: copy mode (no symlink permission)" -ForegroundColor Yellow
    }

    Write-Host "[4/4] Configuring .gitignore..." -ForegroundColor Yellow

    $gi = Join-Path $projRoot ".gitignore"
    $rule1 = "# Superpowers-ZH (managed by Submodule)"
    $rule2 = $StagingDir + "/"
    $rule3 = $SkillsLinkDir + "/"

    if (Test-Path $gi) {
        $content = Get-Content $gi -Raw -ErrorAction SilentlyContinue
        if ($content -notmatch "skills-staging") {
            Add-Content -Path $gi -Value "`n$rule1`n$rule2`n$rule3"
        }
    } else {
        Set-Content -Path $gi -Value ($rule1 + "`n" + $rule2 + "`n" + $rule3)
    }
    Write-Host "   OK: .gitignore configured" -ForegroundColor Green

    Show-FinalStatus -ProjRoot $projRoot -Count $count
}

function Update-Submodule {
    Write-Banner "Updating Skills"
    Push-Location $TargetProject
    Write-Host "[1/2] Pulling latest skills..." -ForegroundColor Yellow
    Push-Location $SubmoduleName
    git pull origin master
    Pop-Location
    Pop-Location
    Write-Host "[2/2] Re-deploying..." -ForegroundColor Yellow
    if (Test-Path $StagingDir) { Remove-Item -Recurse -Force $StagingDir }
    Install-Submodule
}

function Show-Status {
    Write-Banner "Current Status"
    $sp = Join-Path $TargetProject $SubmoduleName
    if (Test-Path $sp) {
        Push-Location $sp
        $hash = git log --oneline -1
        Pop-Location
        Write-Host "Submodule: INSTALLED" -ForegroundColor Green
        Write-Host ("  Commit: " + $hash) -ForegroundColor White
    } else {
        Write-Host "Submodule: NOT INSTALLED" -ForegroundColor Red
    }
    $sd = Join-Path $TargetProject $SkillsLinkDir
    if (Test-Path $sd) {
        $c = (Get-ChildItem $sd -Directory).Count
        Write-Host ("Skills: " + $c + " ready") -ForegroundColor Green
    }
}

function Show-FinalStatus {
    param([string]$ProjRoot, [int]$Count)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host "  DEPLOY COMPLETE!" -ForegroundColor Magenta
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host ""
    Write-Host ("  Mode: Git Submodule") -ForegroundColor Cyan
    Write-Host ("  Skills: " + $Count + " / 23") -ForegroundColor Green
    Write-Host ""
    Write-Host "  Next steps:" -ForegroundColor Magenta
    Write-Host "    1. Restart Trae IDE" -ForegroundColor White
    Write-Host "    2. git add ." -ForegroundColor White
    Write-Host '    3. git commit -m "chore: add superpowers submodule"' -ForegroundColor White
    Write-Host "    4. git push" -ForegroundColor White
}

switch ($Mode) {
    "Install" { Install-Submodule }
    "Update"  { Update-Submodule }
    "Status"  { Show-Status }
}
