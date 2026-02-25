from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings

from django.core.mail import EmailMessage
from django.template.loader import render_to_string

class CustomAccountAdapter(DefaultAccountAdapter):
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        current_site = get_current_site(request)
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://www.socraseek.com')
        activate_url = f"{frontend_url}/registration/account-confirm-email/{emailconfirmation.key}"
        ctx = {
            "user": emailconfirmation.email_address.user,
            "activate_url": activate_url,
            "site_name": current_site.name,
            "site_domain": current_site.domain,
        }
        subject = render_to_string("templates/account/email_subject.txt", ctx)
        subject = subject.strip()
        email_body = render_to_string("templates/account/email_message.txt", ctx)

        msg = EmailMessage(subject, email_body, to=[emailconfirmation.email_address.email])
        msg.send()

