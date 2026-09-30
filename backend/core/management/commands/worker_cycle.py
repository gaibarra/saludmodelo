import io
from django.core.management import call_command
from django.core.management.base import BaseCommand,CommandError
from django.utils import timezone
from core.monitoring import private_directory,lock,read_json,write_json

class Command(BaseCommand):
    help='Ejecuta el ciclo existente con señal local de inicio/resultado y exclusión mutua propia.'
    def add_arguments(self,parser):parser.add_argument('--state-dir',required=True)
    def handle(self,*args,**options):
        try:
            directory=private_directory(options['state_dir'])
            with lock(directory,'worker.lock'):
                try:last=read_json(directory/'worker.json').get('last_success')
                except FileNotFoundError:last=None
                state={'state':'running','updated_at':timezone.now().isoformat(),'last_success':last}
                write_json(directory/'worker.json',state)
                try:
                    for name in ['tracking_reminders','worker','extract_evidence','process_ai','scheduled_reports']:
                        call_command(name,stdout=io.StringIO(),stderr=io.StringIO())
                except Exception:
                    write_json(directory/'worker.json',{**state,'state':'failed','updated_at':timezone.now().isoformat()})
                    raise CommandError('Ciclo fallido; consulte colas y diagnóstico privado. No se registran datos sensibles en la señal.')
                now=timezone.now().isoformat()
                write_json(directory/'worker.json',{'state':'ok','updated_at':now,'last_success':now})
        except (OSError,ValueError,TypeError):
            raise CommandError('No se pudo iniciar o registrar el ciclo; estado inválido o ejecución concurrente.')
        self.stdout.write('Ciclo finalizado; señal privada actualizada.')
