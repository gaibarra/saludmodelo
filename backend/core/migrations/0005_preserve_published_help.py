from django.db import migrations


def preserve_help(apps, schema_editor):
    Instance = apps.get_model('core', 'QuestionnaireInstance')
    Legacy = apps.get_model('core', 'QuestionHelpVersion')
    Revision = apps.get_model('core', 'HelpRevision')
    Review = apps.get_model('core', 'HelpReview')
    AnswerRevision = apps.get_model('core', 'AnswerRevision')
    Audit = apps.get_model('core', 'AuditEvent')
    Member = apps.get_model('core', 'InstitutionMember')
    Assignment = apps.get_model('core', 'RoleAssignment')
    for user_id, institution_id in Assignment.objects.values_list('user_id', 'service__site__campus__institution_id').distinct():
        Member.objects.get_or_create(user_id=user_id, institution_id=institution_id)
    for instance in Instance.objects.filter(published=True, published_help__isnull=True).iterator():
        legacy = Legacy.objects.filter(question_version_id=instance.question_version_id).first()
        if legacy is None or legacy.author_id is None:
            # Keep all answers and old source data, but do not present untraceable help as approved.
            instance.published = False
            instance.etag += 1
            instance.save(update_fields=['published', 'etag'])
            continue
        revision = Revision.objects.create(instance_id=instance.pk, number=1, author_id=legacy.author_id, content=legacy.content)
        if legacy.reviewed_by_id and legacy.reviewed_at and legacy.reviewed_by_id != legacy.author_id:
            review = Review.objects.create(revision_id=revision.pk, reviewer_id=legacy.reviewed_by_id, decision='approved', rationale='Aprobación histórica conservada del incremento 0.1; no es una nueva revisión.')
            Review.objects.filter(pk=review.pk).update(created_at=legacy.reviewed_at)
            instance.published_help_id = revision.pk
            AnswerRevision.objects.filter(answer__instance_id=instance.pk).update(help_revision_id=revision.pk)
            Audit.objects.create(actor_id=legacy.reviewed_by_id, service_id=instance.service_id, action='help.legacy_preserved', object_id=f'{instance.pk}:help:{revision.pk}')
        else:
            instance.published = False
        instance.etag += 1
        instance.save(update_fields=['published', 'published_help', 'etag'])


class Migration(migrations.Migration):
    dependencies = [('core', '0004_questionnaireinstance_etag_roleassignment_rationale_and_more')]
    # No destructive reverse migration: restoration of earlier application code requires review.
    operations = [migrations.RunPython(preserve_help, migrations.RunPython.noop)]
