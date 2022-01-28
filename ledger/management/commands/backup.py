from typing import Any, Optional
from django.core.management import BaseCommand, call_command
from django.utils.timezone import now
from pathlib import Path
from django.conf import settings
import sys
from django.db.migrations.recorder import MigrationRecorder
from django.db import connection


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        recorder = MigrationRecorder(connection)
        recorded_migrations = recorder.applied_migrations()
        last_applied_migration = max([
            str(migration)
            for app, migration in recorded_migrations
            if app == 'ledger'
        ])

        backups = settings.BASE_DIR / 'backups'
        backups.mkdir(exist_ok=True)
        file_name = last_applied_migration[:4] + '_' + now().isoformat() + '.json'
        file = backups / file_name

        call_command('dumpdata', 'ledger', indent=2, output=str(file))