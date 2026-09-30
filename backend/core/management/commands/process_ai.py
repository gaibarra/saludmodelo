from django.core.management.base import BaseCommand
from core.ai.workflow import process_one
class Command(BaseCommand):
    help='Procesa hasta diez solicitudes IA autorizadas; no habilita proveedores ni políticas.'
    def handle(self,*args,**options):
        for _ in range(10):
            if not process_one():break
