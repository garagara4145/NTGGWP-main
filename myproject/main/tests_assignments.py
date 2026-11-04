import io
import zipfile
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .assignment_reminders import send_assignment_deadline_reminders
from .forms import GradeAssignmentForm, LessonAssignmentForm
from .models import (
    AssignmentSubmission,
    Course,
    CourseChapter,
    CourseLesson,
    Enrollment,
    LessonAssignment,
    LessonNote,
    Notification,
    Profile,
)


class AssignmentCriteriaTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user('rubric-teacher', password='test-password')
        Profile.objects.create(user=self.teacher, role='teacher')
        self.course = Course.objects.create(
            title='評分規準測試課程', teacher=self.teacher, price=0, description='測試課程',
        )
        chapter = CourseChapter.objects.create(course=self.course, title='第一章')
        self.lesson = CourseLesson.objects.create(chapter=chapter, title='第一單元')

    def test_criteria_must_total_assignment_max_score(self):
        form = LessonAssignmentForm(data={
            'title': '程式作業',
            'instructions': '請提交程式。',
            'rubric': '',
            'criteria_text': '正確性 | 70\n說明 | 20',
            'due_at': '',
            'max_score': '100',
            'max_attempts': '1',
            'is_published': 'on',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('criteria_text', form.errors)

    def test_assignment_form_saves_structured_criteria(self):
        form = LessonAssignmentForm(data={
            'title': '程式作業',
            'instructions': '請提交程式。',
            'rubric': '依照評分項目給分。',
            'criteria_text': '正確性 | 70\n說明 | 30',
            'due_at': '',
            'max_score': '100',
            'max_attempts': '1',
            'is_published': 'on',
        })
        self.assertTrue(form.is_valid(), form.errors)
        assignment = form.save(commit=False)
        assignment.lesson = self.lesson
        assignment.save()
        self.assertEqual(assignment.grading_criteria, [
            {'name': '正確性', 'max_points': '70'},
            {'name': '說明', 'max_points': '30'},
        ])

    def test_criteria_grade_calculates_total_and_keeps_breakdown(self):
        criteria = [
            {'name': '正確性', 'max_points': '70'},
            {'name': '說明', 'max_points': '30'},
        ]
        form = GradeAssignmentForm(
            data={'criterion_0': '62', 'criterion_1': '25', 'feedback': '寫得清楚。'},
            max_score=Decimal('100'),
            criteria=criteria,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['score'], Decimal('87'))
        self.assertEqual(form.criterion_scores, {'正確性': '62', '說明': '25'})

    def test_grade_rejects_score_over_a_criterion_limit(self):
        form = GradeAssignmentForm(
            data={'criterion_0': '71', 'criterion_1': '25', 'feedback': ''},
            max_score=Decimal('100'),
            criteria=[
                {'name': '正確性', 'max_points': '70'},
                {'name': '說明', 'max_points': '30'},
            ],
        )
        self.assertFalse(form.is_valid())


class AssignmentReminderTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user('reminder-teacher', password='test-password')
        Profile.objects.create(user=self.teacher, role='teacher')
        self.student = User.objects.create_user('reminder-student', password='test-password')
        Profile.objects.create(user=self.student, role='student')
        course = Course.objects.create(title='提醒課程', teacher=self.teacher, price=0, description='測試課程')
        Enrollment.objects.create(course=course, student=self.student)
        chapter = CourseChapter.objects.create(course=course, title='第一章')
        lesson = CourseLesson.objects.create(chapter=chapter, title='第一單元')
        self.assignment = LessonAssignment.objects.create(
            lesson=lesson, title='即將到期', instructions='請提交。',
            due_at=timezone.now() + timezone.timedelta(hours=12),
        )

    def test_reminder_is_created_once_per_student_per_day(self):
        now = timezone.now()
        self.assertEqual(send_assignment_deadline_reminders(now=now), 1)
        self.assertEqual(send_assignment_deadline_reminders(now=now), 0)
        self.assertEqual(Notification.objects.filter(user=self.student, title='作業即將截止').count(), 1)


class AssignmentPermissionTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user('owner-teacher', password='test-password')
        Profile.objects.create(user=self.teacher, role='teacher')
        self.other_teacher = User.objects.create_user('other-teacher', password='test-password')
        Profile.objects.create(user=self.other_teacher, role='teacher')
        self.student = User.objects.create_user('enrolled-student', password='test-password')
        Profile.objects.create(user=self.student, role='student')
        self.stranger = User.objects.create_user('stranger-student', password='test-password')
        Profile.objects.create(user=self.stranger, role='student')
        self.course = Course.objects.create(
            title='權限測試課程', teacher=self.teacher, price=0, description='測試課程',
        )
        chapter = CourseChapter.objects.create(course=self.course, title='第一章')
        self.lesson = CourseLesson.objects.create(chapter=chapter, title='第一單元')
        self.assignment = LessonAssignment.objects.create(
            lesson=self.lesson, title='權限測試作業', instructions='請繳交。',
        )
        Enrollment.objects.create(course=self.course, student=self.student)
        self.submission = AssignmentSubmission.objects.create(
            assignment=self.assignment, student=self.student, attempt_number=1,
            response_text='作答內容',
        )

    def test_other_teacher_cannot_open_assignment_management(self):
        self.client.force_login(self.other_teacher)
        response = self.client.get(reverse('manage_lesson_assignments', args=[self.lesson.id]))
        self.assertEqual(response.status_code, 404)

    def test_other_teacher_cannot_create_assignment_in_foreign_course(self):
        self.client.force_login(self.other_teacher)
        response = self.client.post(
            reverse('add_lesson_assignment', args=[self.lesson.id]),
            {'title': '不應建立', 'instructions': '無權限'},
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(LessonAssignment.objects.filter(title='不應建立').exists())

    def test_student_cannot_grade_submission(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse('grade_lesson_assignment', args=[self.submission.id]), {'score': '80'})
        self.assertEqual(response.status_code, 404)
        self.submission.refresh_from_db()
        self.assertIsNone(self.submission.graded_at)

    def test_unenrolled_student_cannot_submit_assignment(self):
        self.client.force_login(self.stranger)
        response = self.client.post(
            reverse('submit_lesson_assignment', args=[self.assignment.id]),
            {'response_text': '不應建立'},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(AssignmentSubmission.objects.filter(student=self.stranger).count(), 0)

    def test_unrelated_student_cannot_download_submission_file(self):
        self.submission.attachment.name = 'assignment_submissions/private.txt'
        self.submission.save(update_fields=['attachment'])
        self.client.force_login(self.stranger)
        response = self.client.get(reverse('download_assignment_submission', args=[self.submission.id]))
        self.assertEqual(response.status_code, 404)

    def test_only_course_teacher_can_download_submission_batch(self):
        self.submission.attachment.save('answer.txt', SimpleUploadedFile('answer.txt', b'answer'), save=True)
        self.client.force_login(self.other_teacher)
        denied = self.client.get(reverse('download_assignment_attachments', args=[self.assignment.id]))
        self.assertEqual(denied.status_code, 404)
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('download_assignment_attachments', args=[self.assignment.id]))
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(b''.join(response.streaming_content))) as archive:
            self.assertEqual(len(archive.namelist()), 1)
            self.assertTrue(archive.namelist()[0].startswith(f'{self.student.id}_enrolled-student/attempt-1_answer'))

    def test_teacher_and_student_overviews_render(self):
        self.client.force_login(self.teacher)
        teacher_response = self.client.get(reverse('assignment_overview'))
        self.assertEqual(teacher_response.status_code, 200)
        self.client.force_login(self.student)
        student_response = self.client.get(reverse('assignment_overview'))
        self.assertEqual(student_response.status_code, 200)

    def test_course_teacher_can_open_management_page(self):
        self.assignment.grading_criteria = [{'name': '正確性', 'max_points': '100'}]
        self.assignment.save(update_fields=['grading_criteria'])
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('manage_lesson_assignments', args=[self.lesson.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="criterion_0"')

    def test_teacher_criterion_grading_saves_breakdown_and_total(self):
        self.assignment.grading_criteria = [
            {'name': '正確性', 'max_points': '70'},
            {'name': '說明', 'max_points': '30'},
        ]
        self.assignment.save(update_fields=['grading_criteria'])
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse('grade_lesson_assignment', args=[self.submission.id]),
            {'criterion_0': '65', 'criterion_1': '17', 'feedback': '可再補充說明。'},
        )
        self.assertEqual(response.status_code, 302)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.score, Decimal('82'))
        self.assertEqual(self.submission.criterion_scores, {'正確性': '65', '說明': '17'})
        overview = self.client.get(reverse('assignment_overview'))
        self.assertEqual(overview.context['average_score'], Decimal('82'))

    def test_only_teacher_can_export_assignment_grades(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('export_assignment_grades'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('export_assignment_grades'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('assignment-grades.csv', response['Content-Disposition'])

    def test_teacher_assignment_search_and_pagination(self):
        for index in range(16):
            LessonAssignment.objects.create(
                lesson=self.lesson, title=f'分頁測試作業 {index}', instructions='測試',
            )
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('assignment_overview'), {'q': '分頁測試作業', 'assignment_page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['assignment_page'].paginator.count, 16)
        self.assertEqual(len(response.context['assignments']), 1)

    def test_teacher_submission_search_and_pagination(self):
        for index in range(20):
            student = User.objects.create_user(f'page-student-{index}')
            Profile.objects.create(user=student, role='student')
            AssignmentSubmission.objects.create(
                assignment=self.assignment, student=student, attempt_number=1,
                response_text='分頁測試繳交',
            )
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('assignment_overview'), {
            'q': '權限測試作業', 'status': 'all', 'sub_page': 2,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['submission_page'].paginator.count, 21)
        self.assertEqual(len(response.context['submissions']), 1)


class LessonNoteTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user('notes-teacher', password='test-password')
        Profile.objects.create(user=self.teacher, role='teacher')
        self.student = User.objects.create_user('notes-student', password='test-password')
        Profile.objects.create(user=self.student, role='student')
        self.outsider = User.objects.create_user('notes-outsider', password='test-password')
        Profile.objects.create(user=self.outsider, role='student')
        course = Course.objects.create(title='筆記課程', teacher=self.teacher, price=0, description='測試')
        chapter = CourseChapter.objects.create(course=course, title='第一章')
        self.lesson = CourseLesson.objects.create(chapter=chapter, title='影片單元')
        Enrollment.objects.create(course=course, student=self.student)

    def test_enrolled_student_can_create_edit_and_delete_bookmark(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse('add_lesson_note', args=[self.lesson.id]), {
            'timestamp_seconds': '125', 'title': '重要概念', 'content': '',
        })
        self.assertEqual(response.status_code, 302)
        note = LessonNote.objects.get(user=self.student, lesson=self.lesson)
        self.assertTrue(note.is_bookmark)
        self.assertEqual(note.timestamp_label, '02:05')
        response = self.client.post(reverse('edit_lesson_note', args=[note.id]), {
            'timestamp_seconds': '130', 'title': '重要概念', 'content': '補充說明',
        })
        self.assertEqual(response.status_code, 302)
        note.refresh_from_db()
        self.assertEqual(note.content, '補充說明')
        response = self.client.post(reverse('delete_lesson_note', args=[note.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(LessonNote.objects.filter(pk=note.id).exists())

    def test_student_cannot_create_note_without_enrollment(self):
        self.client.force_login(self.outsider)
        response = self.client.post(reverse('add_lesson_note', args=[self.lesson.id]), {
            'timestamp_seconds': '15', 'title': '不應建立', 'content': '無權限',
        })
        self.assertEqual(response.status_code, 404)
        self.assertFalse(LessonNote.objects.filter(user=self.outsider).exists())

    def test_student_cannot_edit_or_delete_another_users_note(self):
        note = LessonNote.objects.create(
            user=self.student, lesson=self.lesson, timestamp_seconds=12, title='私人筆記',
        )
        self.client.force_login(self.outsider)
        edit = self.client.post(reverse('edit_lesson_note', args=[note.id]), {
            'timestamp_seconds': '1', 'title': '竄改', 'content': '不應寫入',
        })
        delete = self.client.post(reverse('delete_lesson_note', args=[note.id]))
        self.assertEqual(edit.status_code, 404)
        self.assertEqual(delete.status_code, 404)
        note.refresh_from_db()
        self.assertEqual(note.title, '私人筆記')

    def test_watch_page_displays_only_current_users_notes(self):
        LessonNote.objects.create(user=self.student, lesson=self.lesson, timestamp_seconds=45, title='我的筆記')
        LessonNote.objects.create(user=self.outsider, lesson=self.lesson, timestamp_seconds=60, title='別人的筆記')
        self.client.force_login(self.student)
        response = self.client.get(reverse('watch_lesson', args=[self.lesson.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '我的筆記')
        self.assertNotContains(response, '別人的筆記')
