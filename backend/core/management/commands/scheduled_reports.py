from django.core.management.base import BaseCommand,CommandError
from core.models import ReportSchedule
from core.report_schedules import run_schedule

class Command(BaseCommand):
    help='Genera borradores semanales autorizados, sin aprobación ni envío.'
    def handle(self,*args,**options):
        generated=0;failed=0
        for pk in ReportSchedule.objects.filter(enabled=True).values_list('pk',flat=True).iterator():
            try:
                result=run_schedule(pk)
                generated+=int(result=='generated')
                failed+=int(result=='authorization_required')
            except Exception:failed+=1
        if failed:raise CommandError(f'Programaciones sin completar: {failed}. Consulte su estado; no se imprimen contenidos.')
        self.stdout.write(f'Borradores semanales generados: {generated}')
