from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import User
from logs.models import LogEntry


@shared_task
def check_expired_subscriptions():
    """
    Daily task to check and expire subscriptions.
    Runs at midnight UTC to ensure timely expiration.
    """
    try:
        # Find all users with expired subscriptions
        expired_users = User.objects.filter(
            premium_user=True,
            subscription_end_date__lt=timezone.now().date()
        )
        
        expired_count = 0
        for user in expired_users:
            # Send expiration notification email
            try:
                send_subscription_expired_email(user)
            except Exception as email_error:
                LogEntry.objects.create(
                    user=user,
                    timestamp=timezone.now(),
                    level='Error',
                    status_code='500',
                    message=f'Failed to send expiration email: {str(email_error)}'
                )
            
            # Update user status
            user.premium_user = False
            user.subscription_end_date = None
            user.save(update_fields=['premium_user', 'subscription_end_date'])
            expired_count += 1
        
        # Log the task completion
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='Normal',
            status_code='200',
            message=f'Expired {expired_count} subscriptions via scheduled task'
        )
        
        return f'Successfully expired {expired_count} subscriptions'
        
    except Exception as e:
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='Error',
            status_code='500',
            message=f'Error in check_expired_subscriptions task: {str(e)}'
        )
        raise


@shared_task
def send_expiration_warnings():
    """
    Daily task to send warning emails to users before subscription expires.
    Sends notifications at 7 days and 1 day before expiration.
    """
    try:
        today = timezone.now().date()
        
        # 7-day warning
        seven_days_from_now = today + timezone.timedelta(days=7)
        users_7day = User.objects.filter(
            premium_user=True,
            subscription_end_date=seven_days_from_now
        )
        
        seven_day_count = 0
        for user in users_7day:
            try:
                send_subscription_warning_email(user, days_remaining=7)
                seven_day_count += 1
            except Exception as email_error:
                LogEntry.objects.create(
                    user=user,
                    timestamp=timezone.now(),
                    level='Error',
                    status_code='500',
                    message=f'Failed to send 7-day warning email: {str(email_error)}'
                )
        
        # 1-day warning
        tomorrow = today + timezone.timedelta(days=1)
        users_1day = User.objects.filter(
            premium_user=True,
            subscription_end_date=tomorrow
        )
        
        one_day_count = 0
        for user in users_1day:
            try:
                send_subscription_warning_email(user, days_remaining=1)
                one_day_count += 1
            except Exception as email_error:
                LogEntry.objects.create(
                    user=user,
                    timestamp=timezone.now(),
                    level='Error',
                    status_code='500',
                    message=f'Failed to send 1-day warning email: {str(email_error)}'
                )
        
        # Log the task completion
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='Normal',
            status_code='200',
            message=f'Sent {seven_day_count} 7-day warnings and {one_day_count} 1-day warnings'
        )
        
        return f'Sent {seven_day_count} 7-day warnings and {one_day_count} 1-day warnings'
        
    except Exception as e:
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='Error',
            status_code='500',
            message=f'Error in send_expiration_warnings task: {str(e)}'
        )
        raise


def send_subscription_warning_email(user, days_remaining):
    """
    Send warning email to user before subscription expires.
    
    Args:
        user: User object
        days_remaining: Number of days until expiration (7 or 1)
    """
    subject = f'[Socratic] Your Premium Subscription Expires in {days_remaining} Day{"s" if days_remaining > 1 else ""}'
    
    message = f"""Hi {user.get_full_name() or user.username},

This is a friendly reminder that your Socratic Premium subscription will expire in {days_remaining} day{"s" if days_remaining > 1 else ""}.

Expiration Date: {user.subscription_end_date.strftime('%B %d, %Y')}

To continue enjoying unlimited document processing and premium features, please renew your subscription before it expires.

Renew Now: {settings.FRONTEND_URL}/pricing

Premium Features You'll Lose:
• Unlimited document generations
• Advanced AI summaries
• Access to community documents
• Priority support

If you have any questions, feel free to reach out to our support team.

Best regards,
The Socratic Team

---
This is an automated message. Please do not reply to this email.
"""
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_subscription_expired_email(user):
    """
    Send notification email when subscription has expired.
    
    Args:
        user: User object
    """
    subject = '[Socratic] Your Premium Subscription Has Expired'
    
    message = f"""Hi {user.get_full_name() or user.username},

Your Socratic Premium subscription has expired as of {timezone.now().date().strftime('%B %d, %Y')}.

You've been moved back to the Free plan, which includes:
• 3 document generations
• Basic AI summaries
• Standard features

Want to Continue with Premium?
Renew your subscription to regain access to:
• Unlimited document generations
• Advanced AI summaries
• Access to community documents
• Priority support

Renew Now: {settings.FRONTEND_URL}/pricing

We'd love to have you back as a Premium member!

Best regards,
The Socratic Team

---
This is an automated message. Please do not reply to this email.
"""
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
