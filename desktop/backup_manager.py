import json
from pathlib import Path
import subprocess
import time

import requests

import shutil

from desktop.paths import get_application_root


class BackupManagerError(Exception):
    pass


class BackupManager:
    def __init__(self) -> None:
        self.project_root = get_application_root()

        self.scripts_directory = (
            self.project_root / "scripts"
        )

        self.backups_directory = (
            self.project_root / "backups"
        )

        self.backups_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def list_backups(self) -> list[dict]:
        backups: list[dict] = []

        for directory in self.backups_directory.iterdir():
            if not directory.is_dir():
                continue

            manifest_path = (
                directory / "backup-info.json"
            )
            dump_path = (
                directory / "recipe_book.dump"
            )
            hashes_path = (
                directory / "checksums.json"
            )

            if not manifest_path.is_file():
                continue

            try:
                manifest = json.loads(
                    manifest_path.read_text(
                        encoding="utf-8-sig"
                    )
                )
            except (OSError, json.JSONDecodeError):
                continue

            manifest["directory"] = str(directory)
            manifest["folder_name"] = directory.name

            manifest["valid"] = (
                dump_path.is_file()
                and hashes_path.is_file()
            )

            backups.append(manifest)

        return sorted(
            backups,
            key=lambda item: item.get(
                "created_at",
                "",
            ),
            reverse=True,
        )

    def create_backup(
        self,
        backup_type: str = "manual",
        label: str = "",
    ) -> None:
        if backup_type not in {
            "initial",
            "manual",
            "before_restore",
        }:
            raise BackupManagerError(
                "Неизвестный тип резервной копии"
            )

        script = (
            self.scripts_directory / "backup.ps1"
        )

        self.run_powershell(
            script,
            [
                "-Type",
                backup_type,
                "-Label",
                label,
            ],
            timeout=600,
        )

    def restore_backup(
        self,
        backup_directory: str,
    ) -> None:
        directory = Path(
            backup_directory
        ).resolve()

        backups_root = (
            self.backups_directory.resolve()
        )

        # Разрешаем восстановление только из backups.
        if directory.parent != backups_root:
            raise BackupManagerError(
                "Выбран недопустимый каталог бэкапа"
            )

        if not (
            directory / "recipe_book.dump"
        ).is_file():
            raise BackupManagerError(
                "В бэкапе отсутствует recipe_book.dump"
            )

        script = (
            self.scripts_directory / "restore.ps1"
        )

        self.run_powershell(
            script,
            [
                "-BackupDirectory",
                str(directory),
                "-Force",
            ],
            timeout=900,
        )

        self.wait_for_api()

    def run_powershell(
        self,
        script: Path,
        arguments: list[str],
        timeout: int,
    ) -> None:
        if not script.is_file():
            raise BackupManagerError(
                f"Скрипт не найден: {script}"
            )

        command = [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            *arguments,
        ]

        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except subprocess.TimeoutExpired as error:
            raise BackupManagerError(
                "Операция выполнялась слишком долго"
            ) from error
        except OSError as error:
            raise BackupManagerError(
                "Не удалось запустить PowerShell"
            ) from error

        if result.returncode != 0:
            message = (
                result.stderr.strip()
                or result.stdout.strip()
                or "Неизвестная ошибка PowerShell"
            )

            raise BackupManagerError(message)

    @staticmethod
    def wait_for_api() -> None:
        for _ in range(30):
            try:
                response = requests.get(
                    "http://localhost:8000/health/database",
                    timeout=2,
                )

                if response.ok:
                    return
            except requests.RequestException:
                pass

            time.sleep(2)

        raise BackupManagerError(
            "База восстановлена, но API не запустился"
        )
    
    def delete_backup(
        self,
        backup_directory: str,
    ) -> None:
        directory = Path(
            backup_directory
        ).resolve()

        backups_root = (
            self.backups_directory.resolve()
        )

        # Разрешаем удалять только непосредственные
        # дочерние каталоги папки backups.
        if directory.parent != backups_root:
            raise BackupManagerError(
                "Недопустимый каталог резервной копии"
            )

        if not directory.is_dir():
            raise BackupManagerError(
                "Резервная копия не найдена"
            )

        manifest_path = (
            directory / "backup-info.json"
        )

        manifest: dict = {}

        if manifest_path.is_file():
            try:
                manifest = json.loads(
                    manifest_path.read_text(
                        encoding="utf-8-sig"
                    )
                )
            except (
                OSError,
                json.JSONDecodeError,
            ) as error:
                raise BackupManagerError(
                    "Не удалось прочитать описание бэкапа"
                ) from error

        is_initial = (
            directory.name.lower() == "initial"
            or manifest.get("type") == "initial"
            or manifest.get("protected") is True
        )

        if is_initial:
            raise BackupManagerError(
                "Стартовый бэкап удалить нельзя"
            )

        try:
            shutil.rmtree(directory)
        except OSError as error:
            raise BackupManagerError(
                "Не удалось удалить резервную копию"
            ) from error    