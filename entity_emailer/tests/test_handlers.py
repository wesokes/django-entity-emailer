from datetime import datetime, timedelta

from entity.models import Entity
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django_dynamic_fixture import G
from mock import patch

from entity_emailer.models import Email, EmailTemplate, EmailType


class HandelEmailSaveTest(TestCase):
    def setUp(self):
        self.email_type = EmailType.objects.create(
            name='test_email',
            description='Do not actually send this. It is only for testing.'
        )
        self.send_to = G(Entity)

    @patch('entity_emailer.tasks.SendEmailAsyncNow')
    def test_calls_send_email_async_now(self, email_async_mock):
        template = G(EmailTemplate, text_template='Hi!')
        Email.objects.create(
            email_type=self.email_type,
            send_to=self.send_to,
            subentity_type=None,
            subject='Test Email Please Ignore',
            template=template,
            context={'some': 'content'},
            uid=None,
            scheduled=None,
            sent=None,
        )
        self.assertTrue(email_async_mock.return_value.delay.called)

    @patch('entity_emailer.tasks.SendEmailAsyncNow')
    def test_scheduled_emails_dont_call_async_email(self, email_async_mock):
        template = G(EmailTemplate, text_template='Hi!')
        Email.objects.create(
            email_type=self.email_type,
            send_to=self.send_to,
            subentity_type=None,
            subject='Test Email Please Ignore',
            template=template,
            context={'some': 'content'},
            uid=None,
            scheduled=datetime.utcnow() + timedelta(days=100),
            sent=None,
        )
        self.assertFalse(email_async_mock.called)

    @override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, BROKER_BACKEND='memory')
    @patch('entity_emailer.tasks.render_to_string')
    @patch('entity_emailer.tasks.get_email_addresses')
    def test_actually_sends_immediate_email(self, address_mock, loader_mock):
        loader_mock.side_effect = ['<p>This is a test html email.</p>',
                                   'This is a test text email.']
        address_mock.return_value = ['test1@example.com', 'test2@example.com']
        template = G(EmailTemplate, text_template='Hi')
        G(Email, template=template, context={}, scheduled=None)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, BROKER_BACKEND='memory')
    @patch('entity_emailer.tasks.render_to_string')
    @patch('entity_emailer.tasks.get_email_addresses')
    def test_updates_sent_time(self, address_mock, loader_mock):
        loader_mock.side_effect = ['<p>This is a test html email.</p>',
                                   'This is a test text email.']
        address_mock.return_value = ['test1@example.com', 'test2@example.com']
        template = G(EmailTemplate, text_template='Hi')
        email = G(Email, template=template, context={}, scheduled=None)
        self.assertIsNotNone(email.sent)
