"""Retire an explicitly identified demonstration service without deleting history."""
import json
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from core.models import Service
from core.governance import record

class Command(BaseCommand):
    help='Archiva un servicio DEMO identificado explícitamente; simulación por defecto.'

    def add_arguments(self,parser):
        parser.add_argument('--service',type=int,required=True)
        parser.add_argument('--expected-name',required=True)
        parser.add_argument('--actor',required=True)
        parser.add_argument('--apply',action='store_true')

    @transaction.atomic
    def handle(self,*args,**options):
        service=Service.objects.select_for_update().select_related('site__campus').get(pk=options['service'])
        if service.name != options['expected_name'] or not service.name.endswith(' · DEMO'):
            raise CommandError('El ID y nombre deben identificar exactamente un servicio DEMO.')
        actor=get_user_model().objects.filter(username=options['actor'],is_active=True,is_superuser=True).first()
        if actor is None:raise CommandError('Requiere operador activo autorizado.')
        relations={r.get_accessor_name():r.related_model.objects.filter(**{r.field.name:service}).count() for r in Service._meta.related_objects}
        result={'service':service.pk,'name':service.name,'relations_preserved':relations,'apply':options['apply'],'already_archived':bool(service.archived_at)}
        if options['apply'] and not service.archived_at:
            service.archived_at=timezone.now()
            service.confirmed=False
            service.etag+=1
            service.save(update_fields=['archived_at','confirmed','etag'])
            record(actor,service.site.campus.institution_id,'service.archived',service.pk,'Retiro de servicio DEMO solicitado por el usuario; historial conservado, sin traslado a servicios reales.',service)
        self.stdout.write(json.dumps(result,ensure_ascii=False))
