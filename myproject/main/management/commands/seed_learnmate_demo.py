"""建立 LearnMate AI 本機展示所需的最小資料。

此指令刻意只允許在 learnmate_demo_db 執行，避免誤改正式或原始資料庫。
它會建立／更新 Demo 學生、選課紀錄，以及課程 1 第一章的基礎測驗；
不會建立作答紀錄，因此前後測分數仍必須由實際操作產生。
"""

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from main.models import Course, Enrollment, LessonMaterial, Quiz, QuizQuestion


DEMO_DATABASE = "learnmate_demo_db"
DEMO_USERNAME = "demo_student"
DEMO_PASSWORD = "LearnMateDemo2026!"
DEMO_MATERIAL_TITLE = "第一章｜Django 基礎教材"
DEMO_MATERIAL_SOURCE = (
    Path(__file__).resolve().parents[3]
    / "demo_content"
    / "learnmate_django_ch1.txt"
)


QUESTIONS = [
    {
        "question_text": "在 Django 專案中，通常使用哪個檔案執行開發伺服器與資料庫 migration 指令？",
        "options": ["admin.py", "settings.py", "manage.py", "views.py"],
        "correct_index": 2,
        "explanation": "manage.py 是 Django 專案執行管理指令的入口，例如 runserver 與 migrate。",
        "topic_tag": "Django 專案指令",
    },
    {
        "question_text": "Django 常用的架構縮寫是什麼？",
        "options": ["MVC", "MVT", "MVVM", "REST"],
        "correct_index": 1,
        "explanation": "Django 通常以 Model、View、Template（MVT）描述其架構。",
        "topic_tag": "Django 架構",
    },
    {
        "question_text": "Django Model 的主要用途是什麼？",
        "options": [
            "設定網頁配色",
            "描述資料結構並與資料庫互動",
            "管理瀏覽器分頁",
            "編譯前端 JavaScript",
        ],
        "correct_index": 1,
        "explanation": "Model 定義欄位與關聯，並透過 ORM 讀寫資料庫。",
        "topic_tag": "Django Model",
    },
    {
        "question_text": "Django URL routing 的主要工作是什麼？",
        "options": [
            "把網址對應到處理請求的 view",
            "建立 MySQL 使用者",
            "壓縮圖片",
            "計算 Quiz 分數",
        ],
        "correct_index": 0,
        "explanation": "URLconf 會把符合的網址路徑交給指定的 view 處理。",
        "topic_tag": "URL 路由",
    },
    {
        "question_text": "建立 migration 後，哪個指令會把變更套用到資料庫？",
        "options": [
            "python manage.py collectstatic",
            "python manage.py createsuperuser",
            "python manage.py migrate",
            "python manage.py testserver",
        ],
        "correct_index": 2,
        "explanation": "migrate 會依 migration 檔案把資料表結構變更套用到資料庫。",
        "topic_tag": "Django 專案指令",
    },
]


class Command(BaseCommand):
    help = "建立 LearnMate AI Demo 學生、選課紀錄與第一份基礎 Quiz"

    @transaction.atomic
    def handle(self, *args, **options):
        database_name = connection.settings_dict.get("NAME")
        if database_name != DEMO_DATABASE:
            raise CommandError(
                f"安全檢查失敗：目前資料庫是 {database_name!r}，"
                f"此指令只能在 {DEMO_DATABASE!r} 執行。"
            )

        course = Course.objects.filter(pk=1).first()
        if course is None:
            raise CommandError("找不到 Demo 課程 ID 1。")

        chapter = course.chapters.order_by("sort_order", "id").first()
        if chapter is None:
            raise CommandError("Demo 課程尚未建立章節。")

        User = get_user_model()
        student, student_created = User.objects.get_or_create(
            username=DEMO_USERNAME,
            defaults={
                "email": "demo.student@learnmate.local",
                "first_name": "LearnMate",
                "last_name": "Demo Student",
            },
        )
        student.email = "demo.student@learnmate.local"
        student.first_name = "LearnMate"
        student.last_name = "Demo Student"
        student.is_active = True
        if student_created or not student.check_password(DEMO_PASSWORD):
            student.set_password(DEMO_PASSWORD)
        student.save()

        enrollment, enrollment_created = Enrollment.objects.get_or_create(
            student=student,
            course=course,
        )

        first_lesson = chapter.lessons.order_by("sort_order", "id").first()
        if first_lesson is None:
            raise CommandError("Demo 課程第一章尚未建立單元。")
        if not DEMO_MATERIAL_SOURCE.exists():
            raise CommandError(f"找不到 Demo 教材來源：{DEMO_MATERIAL_SOURCE}")

        material, material_created = LessonMaterial.objects.get_or_create(
            lesson=first_lesson,
            title=DEMO_MATERIAL_TITLE,
            defaults={
                "material_type": "reading",
                "sort_order": 1,
            },
        )
        material_bytes = DEMO_MATERIAL_SOURCE.read_bytes()
        material.material_type = "reading"
        material.sort_order = 1
        material.size_bytes = len(material_bytes)
        stored_bytes = None
        if material.file:
            try:
                with material.file.open("rb") as stored_file:
                    stored_bytes = stored_file.read()
            except (FileNotFoundError, OSError):
                stored_bytes = None
        if stored_bytes != material_bytes:
            if material.file and material.file.storage.exists(material.file.name):
                material.file.storage.delete(material.file.name)
            material.file.save(
                "learnmate_django_ch1.txt",
                ContentFile(material_bytes),
                save=False,
            )
        material.save()

        quiz, quiz_created = Quiz.objects.get_or_create(
            chapter=chapter,
            defaults={
                "title": "第一章｜Django 基礎診斷測驗",
                "pass_score": 60,
                "is_published": True,
            },
        )
        quiz.title = "第一章｜Django 基礎診斷測驗"
        quiz.pass_score = 60
        quiz.is_published = True
        quiz.save(update_fields=["title", "pass_score", "is_published"])

        for index, item in enumerate(QUESTIONS, start=1):
            QuizQuestion.objects.update_or_create(
                quiz=quiz,
                sort_order=index,
                defaults={**item, "sort_order": index},
            )

        self.stdout.write(self.style.SUCCESS("LearnMate AI Demo 初始化完成。"))
        self.stdout.write(f"資料庫：{database_name}")
        self.stdout.write(
            f"學生：{student.username}（{'新增' if student_created else '已更新'}）"
        )
        self.stdout.write(
            f"選課：課程 {course.pk}（{'新增' if enrollment_created else '已存在'}）"
        )
        self.stdout.write(
            f"教材：{material.title}（{'新增' if material_created else '已更新'}，"
            f"{material.size_bytes} bytes）"
        )
        self.stdout.write(
            f"Quiz：{quiz.title}（{'新增' if quiz_created else '已更新'}，"
            f"{quiz.questions.count()} 題）"
        )
