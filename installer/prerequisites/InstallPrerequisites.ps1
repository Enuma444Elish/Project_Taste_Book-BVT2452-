param(
    [Parameter(Mandatory = $true)]
    [string]$DockerInstaller,

    [Parameter(Mandatory = $true)]
    [string]$WslInstaller,

    [Parameter(Mandatory = $true)]
    [string]$RestartMarker
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$LogDirectory = Join-Path $env:ProgramData "RecipeBook\logs"
$LogFile = Join-Path $LogDirectory "prerequisites-install.log"

New-Item `
    -ItemType Directory `
    -Path $LogDirectory `
    -Force | Out-Null

function Write-InstallLog {
    param([string]$Message)

    $Time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    Add-Content `
        -Path $LogFile `
        -Value "[$Time] $Message"
}

try {
    Write-InstallLog "Начало установки компонентов."

    $RestartRequired = $false

    $Features = @(
        "Microsoft-Windows-Subsystem-Linux",
        "VirtualMachinePlatform"
    )

    foreach ($Feature in $Features) {
        $FeatureInfo = Get-WindowsOptionalFeature `
            -Online `
            -FeatureName $Feature

        if ($FeatureInfo.State -ne "Enabled") {
            Write-InstallLog "Включение компонента: $Feature"

            Enable-WindowsOptionalFeature `
                -Online `
                -FeatureName $Feature `
                -All `
                -NoRestart | Out-Null

            $RestartRequired = $true
        }
    }

    if (-not (Test-Path $WslInstaller)) {
        throw "Не найден установщик WSL: $WslInstaller"
    }

    Write-InstallLog "Установка или обновление WSL."

    $WslArguments = "/i `"$WslInstaller`" /qn /norestart"

    $WslProcess = Start-Process `
        -FilePath "$env:SystemRoot\System32\msiexec.exe" `
        -ArgumentList $WslArguments `
        -WindowStyle Hidden `
        -Wait `
        -PassThru

    if ($WslProcess.ExitCode -eq 3010) {
        $RestartRequired = $true
    }
    elseif ($WslProcess.ExitCode -notin @(0, 1638)) {
        throw "Ошибка установки WSL. Код: $($WslProcess.ExitCode)"
    }

    $DockerDesktop = Join-Path `
        $env:ProgramFiles `
        "Docker\Docker\Docker Desktop.exe"

    if (-not (Test-Path $DockerDesktop)) {
        if (-not (Test-Path $DockerInstaller)) {
            throw "Не найден установщик Docker: $DockerInstaller"
        }

        Write-InstallLog "Тихая установка Docker Desktop."

        $DockerProcess = Start-Process `
            -FilePath $DockerInstaller `
            -ArgumentList @(
                "install",
                "--quiet",
                "--accept-license",
                "--backend=wsl-2",
                "--always-run-service"
            ) `
            -WindowStyle Hidden `
            -Wait `
            -PassThru

        if ($DockerProcess.ExitCode -eq 3010) {
            $RestartRequired = $true
        }
        elseif ($DockerProcess.ExitCode -ne 0) {
            throw "Ошибка установки Docker. Код: $($DockerProcess.ExitCode)"
        }
    }
    else {
        Write-InstallLog "Docker Desktop уже установлен."
    }

    if ($RestartRequired) {
        Set-Content `
            -Path $RestartMarker `
            -Value "Restart required"
    }
    elseif (Test-Path $RestartMarker) {
        Remove-Item `
            -LiteralPath $RestartMarker `
            -Force
    }

    Write-InstallLog "Компоненты успешно подготовлены."
    exit 0
}
catch {
    Write-InstallLog "ОШИБКА: $($_.Exception.Message)"
    exit 1
}