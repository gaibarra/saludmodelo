from django.db import migrations
from django.utils import timezone


def revoke_sharing(apps, schema_editor):
    # Preserve the original authorization and its history; never restore it on rollback.
    apps.get_model('core', 'SchoolAcademicGrant').objects.using(schema_editor.connection.alias).filter(
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())


class Migration(migrations.Migration):
    dependencies = [('core', '0044_institutional_service_areas_sources')]
    operations = [migrations.RunPython(revoke_sharing, migrations.RunPython.noop)]
