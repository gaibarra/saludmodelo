from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('core', '0043_institutional_service_directory')]
    operations = [
        migrations.AddField(model_name='institutionalservice', name='additional_areas', field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name='institutionalservice', name='additional_sources', field=models.JSONField(blank=True, default=list)),
    ]
