import hashlib,json
from pathlib import Path
from datetime import date
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from core.models import Institution,School,Campus,Site,Service,InstitutionalService
from core.governance import require_institution,record

class Command(BaseCommand):
    help='Importa fichas públicas revisadas; no confirma operación, asigna roles ni habilita citas.'
    def add_arguments(self,parser):
        parser.add_argument('--institution',type=int,required=True)
        parser.add_argument('--actor',required=True)
        parser.add_argument('--apply',action='store_true')
    @transaction.atomic
    def handle(self,*args,**options):
        institution=Institution.objects.select_for_update().get(pk=options['institution'])
        actor=get_user_model().objects.get(username=options['actor'],is_active=True)
        require_institution(actor,institution.pk)
        raw=(Path(__file__).resolve().parents[2]/'data/institutional_services_20261001_1.json').read_bytes()
        data=json.loads(raw)
        schools={s.code:s for s in School.objects.filter(institution=institution,code__in=['salud','odontologia'])}
        if set(schools)!={'salud','odontologia'}:raise CommandError('Se requieren ambas escuelas previamente configuradas.')
        if data['source_url']!='https://www.unimodelo.edu.mx/servicios':raise CommandError('Fuente no revisada.')
        changes=[];created=[];renamed=[];relocated=[]
        for item in data['services']:
            row=InstitutionalService.objects.select_related('service__site__campus').filter(code=item['code']).first()
            school=schools.get(item['school'])
            if row:
                if row.service.site.campus.institution_id!=institution.pk or row.service.school_id!=(school.pk if school else None):
                    raise CommandError('La ficha ya está vinculada a otra institución o escuela; revisar sin sobrescribir.')
            else:
                campus,_=Campus.objects.get_or_create(institution=institution,name='Directorio institucional · ubicación por confirmar')
                site,_=Site.objects.get_or_create(campus=campus,name=item.get('site_name','Ubicación por confirmar con el servicio'))
                # Never match or rename a synthetic or user-created service merely by its name.
                service=Service.objects.create(site=site,school=school,name=item['name'],confirmed=False,kind='service')
                row=InstitutionalService(code=item['code'],service=service)
                created.append(item['code'])
            values={'public_name':item['name'],'area':item['area'],'description':item['description'],'audience':item['audience'],
                    'schedule':item['schedule'],'contacts':item['contacts'],'notes':item['notes'],'location_note':item.get('location_note',data['location_note']),
                    'additional_areas':item.get('additional_areas',[]),'additional_sources':item.get('additional_sources',[]),
                    'classification_basis':item.get('classification_basis',data['classification_basis']),'source_url':data['source_url'],
                    'source_checked_on':date.fromisoformat(data['source_checked_on']),'source_sha256':data['source_sha256']}
            if item.get('previous_operational_name') and row.service.name==item['previous_operational_name']:
                service=Service.objects.select_for_update().get(pk=row.service_id)
                if service.name==item['previous_operational_name']:
                    service.name=item['name'];service.etag+=1;service.save(update_fields=['name','etag']);renamed.append(item['code'])
            # Assign the confirmed site only from the importer's original placeholder.
            # Never move a service whose site was customized by its administrators.
            if item.get('site_name') and row.service.site.name=='Ubicación por confirmar con el servicio':
                service=Service.objects.select_for_update().select_related('site__campus').get(pk=row.service_id)
                if service.site.name=='Ubicación por confirmar con el servicio':
                    site,_=Site.objects.get_or_create(campus=service.site.campus,name=item['site_name'])
                    service.site=site;service.etag+=1;service.save(update_fields=['site','etag']);relocated.append(item['code'])
            changed=not row.pk or any(getattr(row,k)!=v for k,v in values.items())
            if changed:
                for k,v in values.items():setattr(row,k,v)
                row.full_clean();row.save();changes.append(item['code'])
        if options['apply'] and (changes or renamed or relocated):
            record(actor,institution.pk,'institutional_services.imported',institution.pk,'Importación del directorio público; dataset SHA256 '+hashlib.sha256(raw).hexdigest())
        if not options['apply']:transaction.set_rollback(True)
        self.stdout.write(json.dumps({'applied':options['apply'],'created':created,'changed':changes,'renamed':renamed,'relocated':relocated,'count':len(data['services']),'operational_confirmation_unchanged':True}))
