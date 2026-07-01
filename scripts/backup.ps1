param(
    [ValidateSet(
        "initial",
        "manual",
        "before_restore"
    )]
    [string]$Type = "manual",

    [string]$Label = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$DatabaseService = "db"
$DatabaseName = "recipe_book"
$DatabaseUser = "recipe_user"

# Корень проекта: папка recipe-book.
$ProjectRoot = (
    Resolve-Path (
        Join-Path $PSScriptRoot ".."
    )
).Path

$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

$BackupFolderName = if ($Type -eq "initial") {
    "initial"
}
else {
    "${Timestamp}_${Type}"
}

# Общая папка всех бэкапов.
$BackupsRoot = Join-Path `
    $ProjectRoot `
    "backups"

# Папка конкретного бэкапа.
$BackupDirectory = Join-Path `
    $BackupsRoot `
    $BackupFolderName

if (
    $Type -eq "initial" `
    -and `
    (Test-Path -LiteralPath $BackupDirectory)
) {
    throw (
        "Стартовый бэкап уже существует. " +
        "Он не будет перезаписан."
    )
}

$DatabaseBackup = Join-Path `
    $BackupDirectory `
    "recipe_book.dump"

$MediaBackup = Join-Path `
    $BackupDirectory `
    "media.zip"

$ManifestPath = Join-Path `
    $BackupDirectory `
    "backup-info.json"

$HashesPath = Join-Path `
    $BackupDirectory `
    "checksums.json"

$ContainerDump = (
    "/tmp/recipe_book_$Timestamp.dump"
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
            Write-Host "PostgreSQL готов."
            return
        }

        Start-Sleep -Seconds 2
    }

    throw "PostgreSQL не запустился."
}

Push-Location $ProjectRoot

try {
    Write-Host "Проверка Docker Desktop..."

    & docker info 2>&1 | Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw (
            "Docker Desktop не запущен " +
            "или Docker Engine недоступен."
        )
    }

    New-Item `
        -ItemType Directory `
        -Path $BackupDirectory `
        -Force |
        Out-Null

    Invoke-Docker -Arguments @(
        "compose",
        "up",
        "-d",
        $DatabaseService
    )

    Wait-For-PostgreSQL

    Write-Host "Создание дампа PostgreSQL..."

    try {
        Invoke-Docker -Arguments @(
            "compose",
            "exec",
            "-T",
            $DatabaseService,
            "pg_dump",
            "-U",
            $DatabaseUser,
            "-d",
            $DatabaseName,
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--file=$ContainerDump"
        )

        # Проверяем, что архив читается pg_restore.
        & docker compose exec -T `
            $DatabaseService `
            pg_restore `
            --list `
            $ContainerDump |
            Out-Null

        if ($LASTEXITCODE -ne 0) {
            throw "Созданный дамп PostgreSQL повреждён."
        }

        Invoke-Docker -Arguments @(
            "compose",
            "cp",
            "${DatabaseService}:${ContainerDump}",
            $DatabaseBackup
        )
    }
    finally {
        & docker compose exec -T `
            $DatabaseService `
            rm -f $ContainerDump 2>&1 |
            Out-Null
    }

    $MediaDirectory = Join-Path `
        $ProjectRoot `
        "media"

    $MediaIncluded = $false

    # Получаем пути всех фотографий из базы.
    $ImagePaths = @(
        & docker compose exec -T `
            $DatabaseService `
            psql `
            -U $DatabaseUser `
            -d $DatabaseName `
            -tAc (
                "SELECT image_path FROM recipes " +
                "WHERE image_path IS NOT NULL " +
                "AND image_path <> '';"
            )
    )

    if ($LASTEXITCODE -ne 0) {
        throw "Не удалось проверить фотографии в базе."
    }

    # Проверяем наличие каждого файла на диске.
    foreach ($ImagePath in $ImagePaths) {
        $ImagePath = $ImagePath.Trim()

        if (-not $ImagePath) {
            continue
        }

        # /media/recipes/photo.jpg превращается
        # в media\recipes\photo.jpg
        $RelativePath = (
            $ImagePath.TrimStart("/") -replace "/", "\"
        )

        $HostImagePath = Join-Path `
            $ProjectRoot `
            $RelativePath

        if (
            -not (
                Test-Path `
                    -LiteralPath $HostImagePath `
                    -PathType Leaf
            )
        ) {
            throw (
                "Резервная копия отменена. " +
                "Фотография не найдена: " +
                $HostImagePath
            )
        }
    }

    # Архивируем всю папку media.
    if (Test-Path -LiteralPath $MediaDirectory) {
        $MediaItems = @(
            Get-ChildItem `
                -LiteralPath $MediaDirectory `
                -Force
        )

        if ($MediaItems.Count -gt 0) {
            Write-Host "Архивирование фотографий..."

            Compress-Archive `
                -Path (
                    Join-Path $MediaDirectory "*"
                ) `
                -DestinationPath $MediaBackup `
                -CompressionLevel Optimal `
                -Force

            $MediaIncluded = $true
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
        throw "Не удалось получить количество рецептов."
    }

    $Manifest = [ordered]@{
        created_at = (
            Get-Date
        ).ToString("yyyy-MM-ddTHH:mm:ssK")

        type = $Type
        label = $Label
        protected = ($Type -eq "initial")

        database = $DatabaseName
        database_user = $DatabaseUser
        recipe_count = [int]$RecipeCount
        media_included = $MediaIncluded
        format = "PostgreSQL custom dump"
    }

    $Manifest |
        ConvertTo-Json |
        Set-Content `
            -LiteralPath $ManifestPath `
            -Encoding UTF8

    $Checksums = [ordered]@{
        database_dump_sha256 = (
            Get-FileHash `
                -LiteralPath $DatabaseBackup `
                -Algorithm SHA256
        ).Hash

        media_sha256 = if ($MediaIncluded) {
            (
                Get-FileHash `
                    -LiteralPath $MediaBackup `
                    -Algorithm SHA256
            ).Hash
        }
        else {
            $null
        }
    }

    $Checksums |
        ConvertTo-Json |
        Set-Content `
            -LiteralPath $HashesPath `
            -Encoding UTF8

    Write-Host ""
    Write-Host "Резервная копия создана:"
    Write-Host $BackupDirectory
    Write-Host "Рецептов в копии: $RecipeCount"
}
finally {
    Pop-Location
}