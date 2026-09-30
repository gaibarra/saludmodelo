from django.core.management.base import BaseCommand
from core.documents import enqueue_legacy,process_one
class Command(BaseCommand):
    help='Extrae hasta 10 documentos con procesos limitados y análisis binario aislado; no envía datos ni acepta evidencia.'
    def handle(self,*args,**options):
        enqueue_legacy()
        processed=0
        for _ in range(10):
            if not process_one():break
            processed+=1
        self.stdout.write(f'Trabajos procesados: {processed}')
