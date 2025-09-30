# PowerShell deployment script for Image Analysis Lambda function
# Usage: .\deploy.ps1 [-Environment production] [-AwsProfile default]

param(
    [string]$Environment = "production",
    [string]$AwsProfile = "default",
    [switch]$SkipTests,
    [switch]$PackageOnly
)

$ErrorActionPreference = "Stop"

# Configuration
$FunctionName = "image-analysis-tool"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackageName = "deployment-package.zip"

Write-Host "Deploying Image Analysis Lambda function..." -ForegroundColor Green
Write-Host "Environment: $Environment"
Write-Host "AWS Profile: $AwsProfile"
Write-Host "Function Directory: $ScriptDir"

try {
    # Clean up previous builds
    Write-Host "Cleaning up previous builds..." -ForegroundColor Yellow
    $packagePath = Join-Path $ScriptDir $PackageName
    if (Test-Path $packagePath) {
        Remove-Item $packagePath -Force
    }
    
    Get-ChildItem -Path $ScriptDir -Recurse -Name "__pycache__" -Directory | ForEach-Object {
        Remove-Item (Join-Path $ScriptDir $_) -Recurse -Force
    }
    
    Get-ChildItem -Path $ScriptDir -Recurse -Name "*.pyc" | ForEach-Object {
        Remove-Item (Join-Path $ScriptDir $_) -Force
    }

    # Install dependencies
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    $requirementsPath = Join-Path $ScriptDir "requirements.txt"
    if (Test-Path $requirementsPath) {
        & python -m pip install -r $requirementsPath -t $ScriptDir --upgrade
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install dependencies"
        }
    } else {
        Write-Host "No requirements.txt found, skipping dependency installation"
    }

    # Run tests unless skipped
    if (-not $SkipTests) {
        Write-Host "Running tests..." -ForegroundColor Yellow
        & python -m pytest $ScriptDir -v
        if ($LASTEXITCODE -ne 0) {
            throw "Tests failed. Use -SkipTests to deploy anyway."
        }
    }

    # Create deployment package
    Write-Host "Creating deployment package..." -ForegroundColor Yellow
    
    $excludePatterns = @(
        "*.git*",
        "*__pycache__*",
        "*.pyc",
        "*test_*",
        "*.zip",
        "deploy.py",
        "deploy.sh",
        "deploy.ps1",
        "lambda_config.json",
        "env_configs",
        "iam_policy.json",
        "trust_policy.json",
        "README.md",
        ".pytest_cache"
    )
    
    # Use PowerShell's Compress-Archive
    $filesToZip = Get-ChildItem -Path $ScriptDir -Recurse | Where-Object {
        $file = $_
        $shouldExclude = $false
        foreach ($pattern in $excludePatterns) {
            if ($file.Name -like $pattern -or $file.FullName -like "*$pattern*") {
                $shouldExclude = $true
                break
            }
        }
        -not $shouldExclude -and -not $file.PSIsContainer
    }
    
    $tempDir = Join-Path $env:TEMP "lambda-package-$(Get-Random)"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    
    foreach ($file in $filesToZip) {
        $relativePath = $file.FullName.Substring($ScriptDir.Length + 1)
        $destPath = Join-Path $tempDir $relativePath
        $destDir = Split-Path $destPath -Parent
        
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        
        Copy-Item $file.FullName $destPath
    }
    
    Compress-Archive -Path "$tempDir\*" -DestinationPath $packagePath -Force
    Remove-Item $tempDir -Recurse -Force

    # Validate package size
    $packageSize = (Get-Item $packagePath).Length
    $maxSize = 50 * 1024 * 1024  # 50MB
    
    if ($packageSize -gt $maxSize) {
        throw "Package size ($([math]::Round($packageSize / 1024 / 1024, 1))MB) exceeds 50MB limit"
    }
    
    Write-Host "Package size: $([math]::Round($packageSize / 1024 / 1024, 1))MB"

    if ($PackageOnly) {
        Write-Host "Package-only mode. Deployment package created successfully!" -ForegroundColor Green
        Write-Host "Package location: $packagePath"
        return
    }

    # Load environment configuration
    $envConfigPath = Join-Path $ScriptDir "env_configs\$Environment.json"
    if (-not (Test-Path $envConfigPath)) {
        throw "Environment configuration not found: $envConfigPath"
    }
    
    $envConfig = Get-Content $envConfigPath | ConvertFrom-Json
    Write-Host "Configuration loaded for $Environment environment"
    Write-Host "Memory: $($envConfig.MemorySize)MB, Timeout: $($envConfig.Timeout)s"

    # Deploy function
    Write-Host "Deploying Lambda function..." -ForegroundColor Yellow
    
    # Check if function exists
    $functionExists = $false
    try {
        aws lambda get-function --function-name $FunctionName --profile $AwsProfile | Out-Null
        $functionExists = $true
    } catch {
        $functionExists = $false
    }
    
    if ($functionExists) {
        Write-Host "Function exists, updating..."
        
        # Update function code
        aws lambda update-function-code --function-name $FunctionName --zip-file "fileb://$packagePath" --profile $AwsProfile
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to update function code"
        }
        
        # Update function configuration
        $envVarsJson = $envConfig.Environment.Variables | ConvertTo-Json -Compress
        aws lambda update-function-configuration --function-name $FunctionName --memory-size $envConfig.MemorySize --timeout $envConfig.Timeout --environment "Variables=$envVarsJson" --profile $AwsProfile
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to update function configuration"
        }
    } else {
        Write-Host "Function does not exist. Please create it manually or update the IAM role in lambda_config.json" -ForegroundColor Red
    }

    Write-Host "Deployment completed successfully!" -ForegroundColor Green
    Write-Host "Package location: $packagePath"

} catch {
    Write-Host "Deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}