param(
    [Parameter(Mandatory = $true)]
    [string]$BackupDirectory,

    [switch]$Force
)

[Console]::OutputEncoding = (
    New-Object System.Text.UTF8Encoding($false)
)

$OutputEncoding = (
    New-Object System.Text.UTF8Encoding($false)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$DatabaseService = "db"
$ApiService = "api"
$DatabaseName = "recipe_book"
$DatabaseUser = "recipe_user"

$ProjectRoot = (
    Resolve-Path (
        Join-Path $PSScriptRoot ".."
    )
).Path

$ResolvedBackupDirectory = (
    Resolve-Path $BackupDirectory
).Path

$DatabaseBackup = Join-Path `
    $ResolvedBackupDirectory `
    "recipe_book.dump"

$MediaBackup = Join-Path `
    $ResolvedBackupDirectory `
    "media.zip"

$ManifestPath = Join-Path `
    $ResolvedBackupDirectory `
    "backup-info.json"

$HashesPath = Join-Path `
    $ResolvedBackupDirectory `
    "checksums.json"

$RestoreTimestamp = Get-Date `
    -Format "yyyy-MM-dd_HH-mm-ss"

$ContainerDump = (
    "/tmp/recipe_book_restore_$RestoreTimestamp.dump"
)

function Invoke-Docker {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments
    )

    & docker @Arguments

    if ($LASTEXITCODE -ne 0) {
        throw (
            "Команда Docker завершилась с ошибкой: " +
            "docker " +
            ($Arguments -join " ")
        )
    }
}

function Wait-For-PostgreSQL {
    Write-Host "Ожидание PostgreSQL..."

    for ($Attempt = 1; $Attempt -le 30; $Attempt++) {
        & docker compose exec -T `
            $DatabaseService `
            pg_isready `
            -U $DatabaseUser `
            -d $DatabaseName 2>&1 |
            Out-Null

        if ($LASTEXITCODE -eq 0) {
            return
        }

        Start-Sleep -Seconds 2
    }

    throw "PostgreSQL не запустился."
}

if (
    -not (
        Test-Path `
            -LiteralPath $DatabaseBackup `
            -PathType Leaf
    )
) {
    throw "Файл recipe_book.dump не найден."
}

if (
    -not (
        Test-Path `
            -LiteralPath $HashesPath `
            -PathType Leaf
    )
) {
    throw "Файл checksums.json не найден."
}

$ExpectedHashes = (
    Get-Content `
        -LiteralPath $HashesPath `
        -Raw
) | ConvertFrom-Json

$ActualDatabaseHash = (
    Get-FileHash `
        -LiteralPath $DatabaseBackup `
        -Algorithm SHA256
).Hash

if (
    $ActualDatabaseHash `
    -ne $ExpectedHashes.database_dump_sha256
) {
    throw (
        "Контрольная сумма дампа не совпадает. " +
        "Файл мог быть повреждён."
    )
}

if (
    Test-Path `
        -LiteralPath $MediaBackup `
        -PathType Leaf
) {
    $ActualMediaHash = (
        Get-FileHash `
            -LiteralPath $MediaBackup `
            -Algorithm SHA256
    ).Hash

    if (
        $ExpectedHashes.media_sha256 `
        -and `
        $ActualMediaHash `
        -ne $ExpectedHashes.media_sha256
    ) {
        throw (
            "Контрольная сумма media.zip " +
            "не совпадает."
        )
    }
}

if (
    Test-Path `
        -LiteralPath $ManifestPath `
        -PathType Leaf
) {
    Write-Host "Сведения о резервной копии:"

    Get-Content `
        -LiteralPath $ManifestPath `
        -Raw |
        Write-Host
}

Write-Host ""
Write-Host (
    "ВНИМАНИЕ: текущая база будет заменена " +
    "данными резервной копии."
)

if (-not $Force) {
    $Confirmation = Read-Host (
        "Введите ВОССТАНОВИТЬ для продолжения"
    )

    if ($Confirmation -ne "ВОССТАНОВИТЬ") {
        Write-Host "Восстановление отменено."
        exit 0
    }
}

Push-Location $ProjectRoot

try {
    & docker info 2>&1 | Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop не запущен."
    }

    Invoke-Docker -Arguments @(
        "compose",
        "up",
        "-d",
        $DatabaseService
    )

    Wait-For-PostgreSQL

    # API останавливается, чтобы во время восстановления
    # никто не изменял базу.
    Invoke-Docker -Arguments @(
        "compose",
        "stop",
        $ApiService
    )

    # Остановленного контейнера недостаточно:
    # Windows может продолжать удерживать папку media.
    Invoke-Docker -Arguments @(
        "compose",
        "rm",
        "-f",
        $ApiService
    )

    Start-Sleep -Seconds 2

    try {
        Invoke-Docker -Arguments @(
            "compose",
            "cp",
            $DatabaseBackup,
            "${DatabaseService}:${ContainerDump}"
        )

        # Проверка структуры архива перед восстановлением.
        & docker compose exec -T `
            $DatabaseService `
            pg_restore `
            --list `
            $ContainerDump |
            Out-Null

        if ($LASTEXITCODE -ne 0) {
            throw "Архив PostgreSQL повреждён."
        }

        Write-Host "Восстановление PostgreSQL..."

        Invoke-Docker -Arguments @(
            "compose",
            "exec",
            "-T",
            $DatabaseService,
            "pg_restore",
            "-U",
            $DatabaseUser,
            "-d",
            $DatabaseName,
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "--single-transaction",
            $ContainerDump
        )

        Write-Host "Восстановление фотографий..."

        $CurrentMedia = Join-Path `
            $ProjectRoot `
            "media"

        if (Test-Path -LiteralPath $CurrentMedia) {
            # Удаляем старое содержимое, но сохраняем папку media.
            Get-ChildItem `
                -LiteralPath $CurrentMedia `
                -Force |
            Remove-Item `
                -Recurse `
                -Force
        }
        else {
            New-Item `
                -ItemType Directory `
                -Path $CurrentMedia `
                -Force |
                Out-Null
        }

        if (
            Test-Path `
                -LiteralPath $MediaBackup `
                -PathType Leaf
        ) {
            Expand-Archive `
                -LiteralPath $MediaBackup `
                -DestinationPath $CurrentMedia `
                -Force
        }

        Write-Host "Применение миграций Alembic..."

        Invoke-Docker -Arguments @(
            "compose",
            "run",
            "--rm",
            $ApiService,
            "alembic",
            "upgrade",
            "head"
        )
    }
    finally {
        & docker compose exec -T `
            $DatabaseService `
            rm -f $ContainerDump 2>&1 |
            Out-Null

        $PreviousErrorActionPreference = (
            $ErrorActionPreference
        )

        $ErrorActionPreference = "Continue"

        & docker compose up -d $ApiService

        $DockerExitCode = $LASTEXITCODE

        $ErrorActionPreference = (
            $PreviousErrorActionPreference
        )

        if ($DockerExitCode -ne 0) {
            Write-Warning (
                "Не удалось автоматически запустить API. " +
                "Выполните: docker compose up -d api"
            )
        }
    }

    $RecipeCount = (
        & docker compose exec -T `
            $DatabaseService `
            psql `
            -U $DatabaseUser `
            -d $DatabaseName `
            -tAc "SELECT COUNT(*) FROM recipes;"
    ).Trim()

    if ($LASTEXITCODE -ne 0) {
        throw (
            "База восстановлена, но проверка " +
            "количества рецептов завершилась ошибкой."
        )
    }

    Write-Host ""
    Write-Host "Восстановление завершено."
    Write-Host "Количество рецептов: $RecipeCount"

}
finally {
    Pop-Location
}