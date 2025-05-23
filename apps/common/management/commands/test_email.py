
import os
import platform
import tarfile
import requests
from django.core.management.base import BaseCommand
from django.core.mail import send_mail


class Command(BaseCommand):
    help = "Download and install Geckodriver"

    def handle(self, *args, **options):
        
        send_mail(
            subject='Test Email',
            message='This is a test email sent from Django.',
            from_email=''
        )
       