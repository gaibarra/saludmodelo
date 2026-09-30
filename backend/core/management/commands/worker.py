from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from core.models import OutboxEvent,Notification,Service
from core.access import scopes
from core.coverage import coverage_event_valid
class Command(BaseCommand):
    help='Drena el outbox interno de forma transaccional; ejecutar mediante temporizador.'
    def handle(self,*args,**options):
        while True:
            with transaction.atomic():
                candidate=OutboxEvent.objects.filter(delivered_at=None).order_by('id').values('id','task__service_id').first()
                if candidate is None:return
                Service.objects.select_for_update().get(pk=candidate['task__service_id'])
                event=OutboxEvent.objects.select_for_update(skip_locked=True).filter(pk=candidate['id'],delivered_at=None).first()
                if event is None:continue
                recipient=event.recipient or event.task.owner
                current=event.task_etag is None or (event.task.etag==event.task_etag and event.task.state not in ['accepted','cancelled','submitted'])
                if current and coverage_event_valid(event) and recipient.is_active and event.task.service_id in scopes(recipient):
                    Notification.objects.get_or_create(event=event,defaults={'recipient':recipient})
                event.delivered_at=timezone.now();event.save(update_fields=['delivered_at'])
