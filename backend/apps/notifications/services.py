"""
Sending notifications. Notifications are a side effect of business actions: a failure to notify
is logged but never undoes or blocks the action that triggered it.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

from apps.accounts.models import User

from .models import EmailStatus, Notification

logger = logging.getLogger("apps")


def _send_email(notification):
    if not notification.recipient_email:
        return
    try:
        send_mail(
            subject=notification.title,
            message=notification.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.recipient_email],
            fail_silently=False,
        )
        notification.email_status = EmailStatus.SENT
    except Exception as exc:  # delivery problems are recorded, not raised
        logger.warning("Email delivery failed for notification %s: %s", notification.pk, exc)
        notification.email_status = EmailStatus.FAILED
        notification.email_error = str(exc)[:255]
    notification.save(update_fields=["email_status", "email_error", "updated_at"])


def notify_users(tenant, users, *, category, title, body="", link="", related=None, email=False, exclude=None):
    """In-app notification for each user (optionally also emailed to the user's address)."""

    created = []
    try:
        seen = set()
        for user in users:
            if user is None or user.pk in seen or (exclude is not None and user.pk == exclude.pk):
                continue
            seen.add(user.pk)
            notification = Notification.objects.create(
                tenant=tenant,
                recipient_user=user,
                recipient_email=user.email if email else "",
                category=category,
                title=title,
                body=body,
                link=link,
                related_model=related[0] if related else "",
                related_id=str(related[1]) if related else "",
            )
            if email:
                _send_email(notification)
            created.append(notification)
    except Exception:
        logger.exception("Could not create notifications for %s", title)
    return created


def notify_roles(tenant, roles, **kwargs):
    """Notify every active user of the tenant holding one of `roles`."""

    users = User.objects.filter(tenant=tenant, role__in=list(roles), is_active=True)
    return notify_users(tenant, users, **kwargs)


def notify_email(tenant, email, *, category, title, body="", link="", related=None):
    """An email to an external person (no user account), recorded with its delivery status."""

    if not email:
        return None
    try:
        notification = Notification.objects.create(
            tenant=tenant,
            recipient_email=email,
            category=category,
            title=title,
            body=body,
            link=link,
            related_model=related[0] if related else "",
            related_id=str(related[1]) if related else "",
        )
        _send_email(notification)
        return notification
    except Exception:
        logger.exception("Could not send email notification %s", title)
        return None
