from django.core.management.base import BaseCommand
from core.tracking.workflow import reminders
class Command(BaseCommand):
    help='Genera avisos internos idempotentes; requiere calendario institucional confirmado.'
    def handle(self,*args,**options):self.stdout.write(f'Avisos internos nuevos: {reminders()}')
