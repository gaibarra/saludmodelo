import json
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from core.monitoring import private_directory,collect,persist

class Command(BaseCommand):
    help='Observa únicamente recursos configurados del proyecto y registra alertas locales; no repara ni envía mensajes.'
    def add_arguments(self,parser):
        parser.add_argument('--state-dir',required=True,type=Path)
        parser.add_argument('--certificate',type=Path)
        parser.add_argument('--backup',type=Path)
        parser.add_argument('--restore-report',type=Path)
        parser.add_argument('--backend-url')
        parser.add_argument('--frontend-url')
    def handle(self,*args,**options):
        try:
            directory=private_directory(options['state_dir'])
            report=collect(directory,**{k:options[k] for k in ['certificate','backup','restore_report','backend_url','frontend_url']})
            report=persist(directory,report)
        except (OSError,ValueError,KeyError,TypeError):
            raise CommandError('No se pudo conservar el estado de monitoreo; revise el directorio privado y su integridad.',returncode=2)
        self.stdout.write(json.dumps(report,ensure_ascii=False))
        if report['exit_code']:
            raise CommandError('Requiere atención; consulte el informe privado de monitoreo.',returncode=report['exit_code'])
