"""Local operational observations; never send alerts or alter business records."""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone as dt_timezone
from decimal import Decimal
import fcntl
import hashlib
import http.client
from urllib.parse import urlsplit
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from cryptography import x509
from django.conf import settings
from django.db import connection,transaction
from django.db.models import Sum,Q
from django.utils import timezone
from .models import EvidenceExtraction,EvidenceDocument,OutboxEvent,AIRequest,AIServicePolicy,SecurityEvent


def private_directory(value):
    path=Path(value)
    path.mkdir(mode=0o700,parents=True,exist_ok=True)
    info=path.stat()
    if path.is_symlink() or info.st_uid!=os.getuid() or info.st_mode&0o077:
        raise ValueError('El estado necesita un directorio propio con permisos 0700.')
    return path


@contextmanager
def lock(directory,name):
    fd=os.open(directory/name,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally:os.close(fd)


def write_json(path,value):
    fd,name=tempfile.mkstemp(prefix='.monitor-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            json.dump(value,stream,sort_keys=True,ensure_ascii=False,indent=2)
            stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def read_json(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size>256*1024:raise ValueError('Archivo no regular o demasiado grande.')
        value=json.loads(stream.read())
        if not isinstance(value,dict):raise ValueError('Se esperaba un objeto JSON.')
        return value


def moment(value):
    result=datetime.fromisoformat(value)
    if result.tzinfo is None:raise ValueError('Fecha sin zona horaria.')
    return result


def observation(key,status,message,**metrics):
    return {'key':key,'status':status,'message':message,'metrics':metrics}


def db_checks(now):
    checks=[]
    # Bound queries and take a consistent read-only view. Errors don't masquerade as empty queues.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            cursor.execute("SET LOCAL statement_timeout = '5s'")
            cursor.execute('SELECT 1')
        checks.append(observation('database','ok','Base accesible; lectura comprobada.'))
        waiting=EvidenceExtraction.objects.filter(state='pending',document__created_at__lt=now-timedelta(minutes=15)).count()
        expired=EvidenceExtraction.objects.filter(state='running').filter(Q(leased_until__lt=now)|Q(leased_until__isnull=True)).count()
        failed=EvidenceExtraction.objects.filter(state='failed').count()
        unqueued=EvidenceDocument.objects.filter(extraction__isnull=True).count()
        checks.append(observation('documents','critical' if expired or failed else 'warning' if waiting or unqueued else 'ok','Cola documental y arrendamientos.',old_pending=waiting,expired_leases=expired,failed=failed,without_job=unqueued))
        pending=AIRequest.objects.filter(state='pending',created_at__lt=now-timedelta(minutes=15)).count()
        stuck=AIRequest.objects.filter(state='running').filter(Q(started_at__lt=now-timedelta(minutes=2))|Q(started_at__isnull=True)).count()
        ai_errors=AIRequest.objects.filter(state='failed',finished_at__gte=now-timedelta(hours=1)).count()
        checks.append(observation('ai_queue','critical' if stuck else 'warning' if pending or ai_errors else 'ok','Cola IA; no se ejecutan llamadas desde el monitor.',old_pending=pending,stuck=stuck,failed_last_hour=ai_errors))
        backlog=OutboxEvent.objects.filter(delivered_at__isnull=True).count()
        checks.append(observation('outbox','critical' if backlog>=100 else 'warning' if backlog else 'ok','Avisos internos pendientes; la tabla no dispone de fecha de encolado.',pending=backlog))
        failures=SecurityEvent.objects.filter(action='mfa.failed',created_at__gte=now-timedelta(minutes=15)).count()
        checks.append(observation('mfa_attempts','critical' if failures>=20 else 'warning' if failures>=5 else 'ok','Intentos MFA fallidos en quince minutos; no es conteo de contraseñas.',failures=failures))
        month=timezone.localtime(now).replace(day=1,hour=0,minute=0,second=0,microsecond=0)
        high=exhausted=policies=0
        for policy in AIServicePolicy.objects.filter(enabled=True).iterator():
            policies+=1
            usage=AIRequest.objects.filter(instance__service_id=policy.service_id,started_at__gte=month,reserved_tokens__gt=0)
            totals=usage.aggregate(tokens=Sum('reserved_tokens'),cost=Sum('reserved_cost'))
            pairs=[(usage.count(),policy.monthly_calls),(totals['tokens'] or 0,policy.monthly_tokens),(totals['cost'] or Decimal(0),policy.monthly_cost_limit)]
            if any(limit<=0 or used>=limit for used,limit in pairs):exhausted+=1
            elif any(Decimal(used)>=Decimal(limit)*Decimal('0.8') for used,limit in pairs):high+=1
        checks.append(observation('ai_budget','critical' if exhausted else 'warning' if high else 'ok','Reservas mensuales por servicio; no representan facturación del proveedor.',enabled_policies=policies,at_least_80_percent=high,exhausted=exhausted,external_enabled=settings.AI_EXTERNAL_ENABLED))
    return checks


def heartbeat_check(directory,now):
    try:
        data=read_json(directory/'worker.json')
        age=(now-moment(data['updated_at'])).total_seconds()
        if age<0:raise ValueError('Reloj futuro')
        if data['state'] not in {'running','ok','failed'}:raise ValueError('Estado inválido')
        state='critical' if data['state']=='failed' or age>2700 else 'ok'
        return observation('worker',state,'Última señal del ciclo del trabajador; no acredita salud de todos los procesos.',state=data['state'],age_seconds=round(age),last_success=data.get('last_success'))
    except FileNotFoundError:return observation('worker','unknown','Sin señal del trabajador; no se ha configurado o ejecutado el ciclo observado.')
    except (ValueError,KeyError,TypeError,OSError):return observation('worker','critical','Señal del trabajador inválida o inaccesible.')


def disk_check(storage):
    try:
        info=shutil.disk_usage(storage)
        percent=100*info.free/info.total
        state='critical' if info.free<1024**3 or percent<5 else 'warning' if info.free<5*1024**3 or percent<10 else 'ok'
        return observation('disk',state,'Espacio del volumen de adjuntos; no mide inodos ni otros volúmenes.',free_bytes=info.free,total_bytes=info.total,free_percent=round(percent,2))
    except OSError:return observation('disk','critical','No se pudo comprobar el volumen de adjuntos.')


def http_check(key,url,path):
    if not url:return observation(key,'unknown','Ruta HTTP local del proyecto no configurada.')
    conn=None
    try:
        parsed=urlsplit(url)
        if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or not parsed.port or parsed.username or parsed.password or parsed.path!=path or parsed.query or parsed.fragment:
            raise ValueError('Destino no permitido')
        conn=http.client.HTTPConnection('127.0.0.1',parsed.port,timeout=2)
        conn.request('HEAD',path,headers={'Connection':'close'})
        response=conn.getresponse()
        return observation(key,'ok' if response.status==200 else 'critical','Sonda HEAD local configurada; no sigue redirecciones ni demuestra operación completa.',http_status=response.status)
    except (ValueError,OSError,http.client.HTTPException):return observation(key,'critical','Sonda local inválida o sin respuesta válida.')
    finally:
        if conn:conn.close()


def certificate_check(path,now):
    if not path:return observation('certificate','unknown','Certificado de este proyecto no configurado para observación.')
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise ValueError('Certificado no regular')
            raw=stream.read(128*1024+1)
        if len(raw)>128*1024:raise ValueError('Certificado demasiado grande')
        cert=x509.load_pem_x509_certificate(raw)
        remaining=(cert.not_valid_after_utc-now).total_seconds()/86400
        state='critical' if remaining<=7 or cert.not_valid_before_utc>now else 'warning' if remaining<=30 else 'ok'
        return observation('certificate',state,'Vigencia del certificado local; no verifica dominio, cadena, renovación ni HTTPS servido.',days_remaining=round(remaining,2))
    except (ValueError,OSError):return observation('certificate','critical','Certificado configurado inválido o inaccesible.')


def backup_check(directory,report_path,now):
    if not directory:return [observation('backup','unknown','No se configuró el corte de respaldo a observar.'),observation('restore','unknown','Ensayo de recuperación no configurado.'),observation('offsite','unknown','Copia fuera del VPS no comprobada.')]
    result=[]
    try:
        root=Path(directory);receipt=read_json(root/'receipt.json')
        if receipt.get('status')!='encrypted_local_only':raise ValueError('Recibo incompatible')
        age=(now-moment(receipt['snapshot_at'])).total_seconds()
        completed=moment(receipt['completed_at'])
        if age<0 or completed>now or completed<moment(receipt['snapshot_at']):raise ValueError('Fechas inválidas')
        archive=root/'backup.tar.age'
        fd=os.open(archive,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            st=os.fstat(stream.fileno())
            if not stat.S_ISREG(st.st_mode) or st.st_size>1024**3+64*1024**2 or st.st_size!=receipt['encrypted_bytes']:raise ValueError('Tamaño incompatible')
            header=stream.read(len(b'age-encryption.org/v1\n'))
            if header!=b'age-encryption.org/v1\n':raise ValueError('Cabecera no reconocida')
            h=hashlib.sha256(header)
            for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
        if h.hexdigest()!=receipt['encrypted_sha256']:raise ValueError('Huella incompatible')
        result.append(observation('backup','critical' if age>3600 else 'ok','Integridad y antigüedad del corte local; no demuestra RPO.',snapshot_age_seconds=round(age)))
        if not report_path:result.append(observation('restore','unknown','No se configuró informe de ensayo.'))
        else:
            report=read_json(Path(report_path))
            elapsed=(now-moment(report['verified_at'])).total_seconds()
            if elapsed<0 or report.get('status')!='isolated_restore_verified' or report['encrypted_sha256']!=receipt['encrypted_sha256']:raise ValueError('Ensayo no corresponde al corte observado')
            result.append(observation('restore','warning' if elapsed>7*86400 else 'ok','Informe local para el mismo corte; no es firma ni prueba de RTO de producción.',age_seconds=round(elapsed)))
    except (ValueError,KeyError,TypeError,OSError):
        if not result:result.append(observation('backup','critical','Respaldo configurado inaccesible o inconsistente.'))
        result.append(observation('restore','unknown','Informe ausente, inválido o no correspondiente al corte.'))
    # A receipt's offsite boolean is not independent evidence of remote custody.
    result.append(observation('offsite','unknown','Transferencia y recuperación desde destino externo no comprobadas.'))
    return result


def collect(directory,certificate=None,backup=None,restore_report=None,backend_url=None,frontend_url=None):
    now=timezone.now()
    connection.settings_dict.setdefault('OPTIONS',{}).setdefault('connect_timeout',5)
    try:checks=db_checks(now)
    except Exception:
        # Do not leak SQL, credentials, filenames, usernames or clinical data in operational reports.
        checks=[observation('database','critical','Falló la lectura de la base; las métricas de colas y presupuesto no están disponibles.')]
        checks += [observation(key,'unknown','No se pudo consultar la base.') for key in ['documents','ai_queue','outbox','mfa_attempts','ai_budget']]
    checks += [heartbeat_check(directory,now),disk_check(settings.MEDIA_ROOT),certificate_check(certificate,now)]
    checks += backup_check(backup,restore_report,now)
    checks += [http_check('backend_http',backend_url,'/api/v1/session/'),http_check('frontend_http',frontend_url,'/'),observation('web_errors','unknown','Agregación de errores HTTP/5xx y supervisión externa aún no configuradas.')]
    from .checks import mfa_configuration
    issues=mfa_configuration(None)
    checks.append(observation('mfa_configuration','critical' if issues else 'ok','Comprobación de obligatoriedad y formato de clave; no acredita enrolamiento ni custodia.',errors=[e.id for e in issues]))
    severity={'ok':0,'warning':1,'unknown':1,'critical':2}
    level=max(severity[c['status']] for c in checks)
    return {'format':1,'observed_at':now.isoformat(),'status':('ok','attention','critical')[level],'checks':checks,
            'scope':'Observación técnica local; sin supervisión externa ni aceptación institucional.','exit_code':level}


def persist(directory,report):
    with lock(directory,'monitor.lock'):
        try:previous=read_json(directory/'monitor.json')
        except FileNotFoundError:previous={'checks':[],'transitions':[]}
        if previous.get('observed_at') and moment(previous['observed_at'])>moment(report['observed_at']):
            raise ValueError('No se reemplaza una observación más reciente.')
        if not isinstance(previous.get('checks'),list) or not isinstance(previous.get('transitions',[]),list):
            raise ValueError('Estado anterior incompatible.')
        before={c['key']:c['status'] for c in previous['checks']}
        transitions=previous.get('transitions',[])
        for check in report['checks']:
            old=before.get(check['key'])
            if old!=check['status']:
                transitions.append({'at':report['observed_at'],'check':check['key'],'previous':old,'current':check['status']})
        report={**report,'transitions':transitions[-200:]}
        write_json(directory/'monitor.json',report)
    return report
