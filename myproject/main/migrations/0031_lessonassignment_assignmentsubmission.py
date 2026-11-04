import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0030_lessonsubtitle_lessontranscriptcue'),
    ]

    operations = [
        migrations.CreateModel(
            name='LessonAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='作業名稱')),
                ('instructions', models.TextField(verbose_name='作業說明')),
                ('rubric', models.TextField(blank=True, default='', verbose_name='評分規準')),
                ('due_at', models.DateTimeField(blank=True, null=True, verbose_name='截止時間')),
                ('max_score', models.DecimalField(decimal_places=2, default=100, max_digits=7, verbose_name='滿分')),
                ('max_attempts', models.PositiveSmallIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(10)], verbose_name='可繳交次數')),
                ('allow_late_submissions', models.BooleanField(default=False, verbose_name='截止後仍可繳交')),
                ('is_published', models.BooleanField(default=True, verbose_name='開放繳交')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='main.courselesson', verbose_name='單元')),
            ],
            options={
                'verbose_name': '單元作業',
                'verbose_name_plural': '單元作業',
                'ordering': ['due_at', 'id'],
            },
        ),
        migrations.CreateModel(
            name='AssignmentSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempt_number', models.PositiveSmallIntegerField(verbose_name='繳交次數')),
                ('response_text', models.TextField(blank=True, default='', verbose_name='文字作答')),
                ('attachment', models.FileField(blank=True, null=True, upload_to='assignment_submissions/%Y/%m/', verbose_name='繳交檔案')),
                ('submitted_at', models.DateTimeField(auto_now_add=True, verbose_name='繳交時間')),
                ('score', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name='得分')),
                ('feedback', models.TextField(blank=True, default='', verbose_name='講師回饋')),
                ('graded_at', models.DateTimeField(blank=True, null=True, verbose_name='批改時間')),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='main.lessonassignment', verbose_name='作業')),
                ('graded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='graded_assignment_submissions', to='auth.user', verbose_name='批改講師')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignment_submissions', to='auth.user', verbose_name='學生')),
            ],
            options={
                'verbose_name': '作業繳交紀錄',
                'verbose_name_plural': '作業繳交紀錄',
                'ordering': ['-attempt_number', '-submitted_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='assignmentsubmission',
            constraint=models.UniqueConstraint(fields=('assignment', 'student', 'attempt_number'), name='assignment_student_attempt_uq'),
        ),
    ]
