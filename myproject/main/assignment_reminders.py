from datetime import timedelta

from django.utils import timezone

from .models import AssignmentSubmission, Enrollment, LessonAssignment, Notification


def send_assignment_deadline_reminders(within_hours=24, now=None, student=None):
    """Create one daily reminder for enrolled students with an unsubmitted task due soon."""
    now = now or timezone.now()
    deadline = now + timedelta(hours=within_hours)
    enrollments = Enrollment.objects.select_related('student')
    if student is not None:
        enrollments = enrollments.filter(student=student)
    assignments = LessonAssignment.objects.filter(
        is_published=True,
        due_at__gt=now,
        due_at__lte=deadline,
        lesson__chapter__course_id__in=enrollments.values_list('course_id', flat=True),
    ).select_related('lesson__chapter__course')
    today = timezone.localdate(now)
    created_count = 0

    for assignment in assignments:
        course = assignment.lesson.chapter.course
        course_enrollments = enrollments.filter(course=course)
        student_ids = course_enrollments.values_list('student_id', flat=True)
        already_submitted = set(
            AssignmentSubmission.objects.filter(
                assignment=assignment, student_id__in=student_ids
            ).values_list('student_id', flat=True)
        )
        title = '作業即將截止'
        content = (
            f'「{course.title}」的單元「{assignment.lesson.title}」作業「{assignment.title}」'
            f'將於 {timezone.localtime(assignment.due_at).strftime("%Y/%m/%d %H:%M")} 截止，請記得完成繳交。'
        )
        for enrollment in course_enrollments:
            student = enrollment.student
            if student.id in already_submitted:
                continue
            if Notification.objects.filter(
                user=student, title=title, content=content, created_at__date=today
            ).exists():
                continue
            Notification.objects.create(user=student, title=title, content=content)
            created_count += 1

    return created_count
