@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

title Запуск книги рецептов

set "APP_EXE=%~dp0RecipeBook.exe"

if not exist "%APP_EXE%" (
    echo.
    echo ОШИБКА: файл RecipeBook.exe не найден.
    echo Сначала соберите приложение через PyInstaller.
    echo.
    pause
    exit /b 1
)

where docker >nul 2>&1

if errorlevel 1 (
    echo.
    echo ОШИБКА: Docker Desktop не установлен.
    echo Установите Docker Desktop и повторите запуск.
    echo.
    pause
    exit /b 1
)

echo Проверка Docker Desktop...

docker info >nul 2>&1

if errorlevel 1 (
    echo Docker Desktop запускается...

    docker desktop start --timeout 120 >nul 2>&1

    if errorlevel 1 (
        if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
            start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
        ) else if exist "%LOCALAPPDATA%\Programs\Docker\Docker\Docker Desktop.exe" (
            start "" "%LOCALAPPDATA%\Programs\Docker\Docker\Docker Desktop.exe"
        )
    )
)

set /a ATTEMPT=0

:WAIT_DOCKER

docker info >nul 2>&1

if not errorlevel 1 goto DOCKER_READY

set /a ATTEMPT+=1

if %ATTEMPT% GEQ 60 goto DOCKER_ERROR

echo Ожидание Docker Engine...
timeout /t 2 /nobreak >nul

goto WAIT_DOCKER


:DOCKER_READY

echo Docker Desktop готов.
echo Запуск PostgreSQL и API...

docker compose up --build --wait --wait-timeout 180

if errorlevel 1 goto COMPOSE_ERROR

echo PostgreSQL и API готовы.
echo Запуск приложения...

start "" "%APP_EXE%"

exit /b 0


:DOCKER_ERROR

echo.
echo ОШИБКА: Docker Desktop не запустился.
echo Откройте Docker Desktop вручную и проверьте его состояние.
echo.
pause
exit /b 1


:COMPOSE_ERROR

echo.
echo ОШИБКА: не удалось запустить PostgreSQL или API.
echo.
echo Последние сообщения контейнеров:
docker compose logs --tail 30
echo.
pause
exit /b 1