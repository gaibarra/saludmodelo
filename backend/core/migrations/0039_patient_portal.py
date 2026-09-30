import uuid
from django.conf import settings
from django.db import migrations,models
from django.db.models import Q
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[('core','0038_exceptional_mfa_recovery'),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.AddField(model_name='service',name='public_slug',field=models.CharField(max_length=40,unique=True,null=True,blank=True)),
        migrations.CreateModel(name='PatientProfile',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('email_normalized',models.EmailField(max_length=254,unique=True)),('phone',models.CharField(max_length=20)),('created_at',models.DateTimeField(auto_now_add=True)),('user',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name='patient_profile',to=settings.AUTH_USER_MODEL))]),
        migrations.CreateModel(name='AppointmentRequest',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('public_id',models.UUIDField(default=uuid.uuid4,editable=False,unique=True)),('service_slug',models.CharField(max_length=40)),('site_preference',models.CharField(max_length=20)),('preferred_day',models.DateField(null=True)),('status',models.CharField(choices=[('pending','Pendiente'),('confirmed','Confirmada'),('declined','No disponible'),('withdrawn','Retirada')],default='pending',max_length=15)),('confirmed_start',models.DateTimeField(null=True)),('confirmed_site',models.CharField(blank=True,max_length=20)),('reviewed_at',models.DateTimeField(null=True)),('client_key',models.UUIDField()),('etag',models.PositiveIntegerField(default=1)),('created_at',models.DateTimeField(auto_now_add=True)),('patient',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='appointment_requests',to='core.patientprofile')),('reviewed_by',models.ForeignKey(null=True,on_delete=django.db.models.deletion.PROTECT,related_name='+',to=settings.AUTH_USER_MODEL))],options={'constraints':[models.UniqueConstraint(fields=('patient','client_key'),name='patient_appointment_retry_key'),models.UniqueConstraint(condition=Q(status='pending'),fields=('patient','service_slug'),name='one_pending_appointment_per_service')]}),
    ]
