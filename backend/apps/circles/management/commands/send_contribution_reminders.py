from datetime import date

from django.core.management.base import BaseCommand

from apps.circles.reminders import send_reminders


class Command(BaseCommand):
    help = "Sends gentle contribution reminders for open community circles (run daily, e.g. from cron)."

    def add_arguments(self, parser):
        parser.add_argument("--days-before", type=int, default=3, help="Remind this many days before the due date.")
        parser.add_argument("--today", help="Override today's date (YYYY-MM-DD) for testing.")

    def handle(self, *args, **options):
        today = date.fromisoformat(options["today"]) if options["today"] else date.today()
        sent = send_reminders(today, days_before=options["days_before"])
        self.stdout.write(self.style.SUCCESS(f"Reminders sent: {sent['upcoming']} upcoming, {sent['overdue']} overdue."))
