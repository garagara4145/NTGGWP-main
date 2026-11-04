from django.core.management.base import BaseCommand

from main.assignment_reminders import send_assignment_deadline_reminders


class Command(BaseCommand):
    help = 'Notify enrolled students about assignments due within the next 24 hours.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours', type=int, default=24,
            help='Reminder window in hours (default: 24).',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        if hours < 1:
            self.stderr.write('--hours must be at least 1.')
            return
        count = send_assignment_deadline_reminders(within_hours=hours)
        self.stdout.write(self.style.SUCCESS(f'已建立 {count} 則作業截止提醒。'))
