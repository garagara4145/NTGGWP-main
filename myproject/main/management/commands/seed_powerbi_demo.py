"""建立 Power BI 展示用的完整學習資料。

在既有課程/學生/選課（seed_data.py）之上，補出 LearnMate 閉環要展示的資料：
  - 每章一份 topic_tag 標記的測驗（4 題、2 個知識點）
  - 每位學生的作答（弱點依學生而異，確保資料有變化）
  - 透過 ai_diagnosis.diagnose_attempt 把弱點「落地」（非虛構，依實際錯題推導）
  - 一半學生有補救後的第二次作答（提供補救前後對照）
  - 觀看進度（含重看等行為指標）
  - 每課一份 AI 課程摘要

所有「分數」都來自實際作答的對錯，不是手填的假數字。

⚠️ 安全：預設拒絕在正式庫 course_platform_db 執行；要在正式庫跑需加 --force。
用法（建議在 scratch / demo 資料庫）：
    python manage.py seed_powerbi_demo
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from main import ai_diagnosis
from main.models import (
    Course, CourseLesson, CourseSummary, Enrollment,
    LessonProgress, Quiz, QuizAnswer, QuizAttempt, QuizQuestion,
)

PROTECTED_DB = 'course_platform_db'
TOPIC_POOL = ['核心概念', '語法應用', '常見錯誤', '實作練習']


class Command(BaseCommand):
    help = '建立 Power BI 展示用的完整學習資料（測驗/作答/診斷落地/觀看/摘要）'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='允許在正式庫 course_platform_db 執行（預設拒絕）')
        parser.add_argument('--courses', type=int, default=3, help='處理前幾門已上架課程')

    @transaction.atomic
    def handle(self, *args, **options):
        db = connection.settings_dict.get('NAME')
        if db == PROTECTED_DB and not options['force']:
            raise CommandError(
                f"安全檢查：目前是正式庫 {db!r}，預設不在此建立 demo 資料。"
                f"若確定要，請加 --force。")

        courses = list(
            Course.objects.filter(is_published=True)
            .prefetch_related('chapters__lessons').order_by('id')[:options['courses']]
        )
        if not courses:
            raise CommandError('找不到已上架課程，請先執行 seed_data.py。')

        n_quiz = n_attempt = n_progress = 0

        for course in courses:
            CourseSummary.objects.update_or_create(course=course, defaults={
                'summary': f'「{course.title}」涵蓋多個核心知識點，本摘要由 AI 依課程教材生成。',
                'core_concepts': [{'concept': t, 'explanation': f'{t}的說明'} for t in TOPIC_POOL[:2]],
                'key_terms': [{'term': t, 'definition': f'{t}的定義'} for t in TOPIC_POOL[:2]],
            })

            students = list(
                User.objects.filter(
                    id__in=Enrollment.objects.filter(course=course).values_list('student_id', flat=True),
                    profile__role='student',
                ).order_by('id')
            )
            if not students:
                continue

            for chapter in course.chapters.all():
                quiz, _ = Quiz.objects.get_or_create(
                    chapter=chapter,
                    defaults={'title': f'{chapter.title}｜診斷測驗',
                              'quiz_type': 'standard', 'is_published': True},
                )
                # 4 題、兩個知識點各 2 題
                topics = [TOPIC_POOL[0], TOPIC_POOL[0], TOPIC_POOL[1], TOPIC_POOL[1]]
                questions = []
                for i, topic in enumerate(topics, start=1):
                    q, _ = QuizQuestion.objects.get_or_create(
                        quiz=quiz, sort_order=i,
                        defaults={
                            'question_text': f'關於「{topic}」的觀念題 Q{i}',
                            'options': ['選項A', '選項B', '選項C', '選項D'],
                            'correct_index': 0, 'explanation': f'{topic}的正解說明。',
                            'topic_tag': topic,
                        })
                    if q.topic_tag != topic:
                        q.topic_tag = topic
                        q.save(update_fields=['topic_tag'])
                    questions.append(q)
                if quiz.questions.exists():
                    n_quiz += 1

                for idx, student in enumerate(students):
                    if QuizAttempt.objects.filter(user=student, quiz=quiz).exists():
                        continue  # 已有作答則跳過，保持可重複執行
                    # 讓不同學生在不同知識點卡關：idx 偶數→卡 topic0，奇數→卡 topic1
                    weak_topic = TOPIC_POOL[0] if idx % 2 == 0 else TOPIC_POOL[1]
                    a1 = self._make_attempt(student, quiz, questions,
                                            wrong_topic=weak_topic)
                    n_attempt += 1
                    # 一半學生補救後再測一次（全對）→ 補救前後對照
                    if idx % 2 == 0:
                        self._make_attempt(student, quiz, questions, wrong_topic=None)
                        n_attempt += 1

            # 觀看進度（含行為指標）
            lessons = CourseLesson.objects.filter(chapter__course=course)
            for idx, student in enumerate(students):
                for lidx, lesson in enumerate(lessons):
                    dur = (lesson.duration_minutes or 10) * 60
                    # 後面的單元完成度遞減，製造「棄看熱點」
                    ratio = max(0.2, 1.0 - lidx * 0.15 - (idx % 3) * 0.1)
                    watched = int(dur * min(1.0, ratio))
                    _, created = LessonProgress.objects.update_or_create(
                        user=student, lesson=lesson,
                        defaults={
                            'course': course, 'duration': dur, 'watched_seconds': watched,
                            'last_position': watched, 'is_completed': ratio >= 0.9,
                            'view_count': 1 + (lidx % 3), 'page_open_count': 2 + (lidx % 2),
                            'replayed_seconds': int(dur * 0.15) if ratio < 0.6 else 0,
                        })
                    if created:
                        n_progress += 1

        self.stdout.write(self.style.SUCCESS(
            f'Power BI demo 資料完成（DB={db}）：測驗 {n_quiz}、作答 {n_attempt}、觀看進度 {n_progress}。'))
        self.stdout.write('提示：接著執行 export_powerbi_json 再 build_workbook.py 產生 .xlsx。')

    def _make_attempt(self, student, quiz, questions, wrong_topic):
        """建立一次作答：wrong_topic 指定的知識點全答錯，其餘答對。回傳 attempt。"""
        attempt = QuizAttempt.objects.create(
            user=student, quiz=quiz, total_count=len(questions))
        correct = 0
        for q in questions:
            is_wrong = (wrong_topic is not None and q.topic_tag == wrong_topic)
            selected = 1 if is_wrong else q.correct_index  # 1 ≠ 正解(0)
            ok = (selected == q.correct_index)
            if ok:
                correct += 1
            QuizAnswer.objects.create(
                attempt=attempt, question=q, selected_index=selected, is_correct=ok)
        attempt.correct_count = correct
        attempt.score = round(correct / len(questions) * 100)
        attempt.save(update_fields=['correct_count', 'score'])
        ai_diagnosis.diagnose_attempt(attempt)  # 弱點落地（依實際錯題推導）
        return attempt
