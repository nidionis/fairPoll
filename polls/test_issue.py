from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from polls.models import HousePoll, Ticket
from houses.models import House
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class HousePollTicketsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.house = House.objects.create(name='Test House', creator=self.user)
        self.house.members.add(self.user)
        self.poll = HousePoll.objects.create(
            question='Test Question',
            house=self.house,
            creator=self.user,
            dead_line=timezone.now() + timedelta(days=1),
            max_participants=10,
            is_ticket_secured=True
        )
        # Create some tickets
        Ticket.objects.create(poll=self.poll, code='TICKET1')
        Ticket.objects.create(poll=self.poll, code='TICKET2')
        self.client = Client()
        self.client.login(username='testuser', password='password')

    def test_house_poll_detail_displays_download_link(self):
        url = reverse('polls:house_poll_detail', kwargs={'external_id': self.poll.external_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # New behavior: tickets are NOT displayed in <li> tags
        self.assertNotContains(response, '<li><code>TICKET1</code></li>')
        self.assertNotContains(response, '<li><code>TICKET2</code></li>')
        # Download link is present
        download_url = reverse('polls:house_poll_tickets_export', kwargs={'external_id': self.poll.external_id})
        self.assertContains(response, f'href="{download_url}"')

    def test_house_poll_tickets_export(self):
        url = reverse('polls:house_poll_tickets_export', kwargs={'external_id': self.poll.external_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
        content = response.content.decode('utf-8')
        self.assertIn('TICKET1', content)
        self.assertIn('TICKET2', content)
        self.assertEqual(content.split('\n'), ['TICKET1', 'TICKET2'])
