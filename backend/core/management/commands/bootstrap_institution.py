from datetime import date
from getpass import getpass
from django.contrib.auth import get_user_model, password_validation
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Institution, InstitutionMember, InstitutionMandate, ImportBatch, CatalogAccess
from core.governance import record

class Command(BaseCommand):
    help = 'Registra un nombramiento inicial documentado; no asigna roles clínicos ni publica formularios.'
    def add_arguments(self, parser):
        group=parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--institution',type=int)
        group.add_argument('--institution-name')
        parser.add_argument('--director',required=True)
        parser.add_argument('--approver',required=True)
        parser.add_argument('--starts',type=date.fromisoformat,required=True)
        parser.add_argument('--ends',type=date.fromisoformat,required=True)
        parser.add_argument('--rationale',required=True)
        parser.add_argument('--catalog-batch',type=int)
    @transaction.atomic
    def handle(self,*args,**options):
        U=get_user_model()
        approver=U.objects.filter(username=options['approver'],is_active=True,is_superuser=True).first()
        if approver is None: raise CommandError('Se requiere un operador técnico autorizado existente.')
        if options['director']==options['approver']: raise CommandError('Director y aprobador deben ser personas distintas.')
        if options['starts']>options['ends'] or not options['rationale'].strip(): raise CommandError('Periodo o fundamento inválido.')
        director=U.objects.filter(username=options['director'],is_active=True).first()
        if director is None:
            director=U(username=options['director'])
            password=getpass('Contraseña inicial del nuevo director: ')
            if password!=getpass('Repita la contraseña: '): raise CommandError('Las contraseñas no coinciden.')
            password_validation.validate_password(password,user=director)
            director.set_password(password);director.save()
        if options['institution']:
            institution=Institution.objects.get(pk=options['institution'])
        else:
            if Institution.objects.filter(name=options['institution_name']).exists(): raise CommandError('La institución ya existe; indique --institution ID.')
            institution=Institution.objects.create(name=options['institution_name'])
        InstitutionMember.objects.get_or_create(institution=institution,user=director)
        mandate,created=InstitutionMandate.objects.get_or_create(institution=institution,user=director,starts=options['starts'],ends=options['ends'],defaults={'approved_by':approver,'rationale':options['rationale']})
        if created: record(approver,institution.pk,'institution.mandate_granted',mandate.pk,options['rationale'])
        if options['catalog_batch']:
            batch=ImportBatch.objects.get(pk=options['catalog_batch'])
            _,granted=CatalogAccess.objects.get_or_create(institution=institution,batch=batch,defaults={'granted_by':approver})
            if granted:record(approver,institution.pk,'catalog.granted',batch.pk,options['rationale'])
        self.stdout.write(f'Institución {institution.pk}; nombramiento {mandate.pk}. Sin roles clínicos ni preguntas publicadas.')
