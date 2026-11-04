import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('main', '0032_lessonassignment_grading_criteria_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LessonNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp_seconds', models.PositiveIntegerField(default=0, verbose_name='影片時間（秒）')),
                ('title', models.CharField(blank=True, default='', max_length=160, verbose_name='標題')),
                ('content', models.TextField(blank=True, default='', verbose_name='筆記內容')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='learning_notes', to='main.courselesson', verbose_name='單元')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lesson_notes', to=settings.AUTH_USER_MODEL, verbose_name='使用者')),
            ],
            options={
                'verbose_name': '影片學習筆記',
                'verbose_name_plural': '影片學習筆記',
                'ordering': ['timestamp_seconds', 'created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='lessonnote',
            index=models.Index(fields=['user', 'lesson', 'timestamp_seconds'], name='lnote_user_lesson_sec_idx'),
        ),
    ]
