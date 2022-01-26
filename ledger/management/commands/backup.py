from typing import Any, Optional
from django.core.management import BaseCommand, call_command
from django.utils.timezone import now
from pathlib import Path
from django.conf import settings


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        backups = settings.BASE_DIR / 'backups'
        backups.mkdir(exist_ok=True)
        file_name = now().isoformat() + '.json'
        file = backups / file_name
        call_command('dumpdata', 'ledger', indent=2, output=str(file))