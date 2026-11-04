from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0029_lessonprogress_page_open_count_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LessonSubtitle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language_code', models.CharField(choices=[('zh-TW', '繁體中文'), ('zh-CN', '简体中文'), ('en', 'English'), ('ja', '日本語'), ('ko', '한국어')], max_length=10, verbose_name='字幕語言')),
                ('file', models.FileField(upload_to='lesson_subtitles/', verbose_name='WebVTT 字幕檔')),
                ('uploaded_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subtitles', to='main.courselesson', verbose_name='單元')),
            ],
            options={
                'verbose_name': '單元字幕',
                'verbose_name_plural': '單元字幕',
            },
        ),
        migrations.CreateModel(
            name='LessonTranscriptCue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_milliseconds', models.PositiveIntegerField(verbose_name='開始毫秒')),
                ('end_milliseconds', models.PositiveIntegerField(verbose_name='結束毫秒')),
                ('text', models.TextField(verbose_name='逐字稿')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='排序')),
                ('subtitle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cues', to='main.lessonsubtitle', verbose_name='字幕')),
            ],
            options={
                'verbose_name': '逐字稿片段',
                'verbose_name_plural': '逐字稿片段',
                'ordering': ['subtitle', 'sort_order'],
            },
        ),
        migrations.AddConstraint(
            model_name='lessonsubtitle',
            constraint=models.UniqueConstraint(fields=('lesson', 'language_code'), name='subtitle_lesson_lang_uniq'),
        ),
        migrations.AddIndex(
            model_name='lessontranscriptcue',
            index=models.Index(fields=['subtitle', 'start_milliseconds'], name='subtitle_start_ms_idx'),
        ),
    ]
