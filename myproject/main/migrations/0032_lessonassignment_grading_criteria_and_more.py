from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0031_lessonassignment_assignmentsubmission'),
    ]

    operations = [
        migrations.AddField(
            model_name='lessonassignment',
            name='grading_criteria',
            field=models.JSONField(blank=True, default=list, verbose_name='評分項目'),
        ),
        migrations.AddField(
            model_name='assignmentsubmission',
            name='criterion_scores',
            field=models.JSONField(blank=True, default=dict, verbose_name='各項得分'),
        ),
    ]
