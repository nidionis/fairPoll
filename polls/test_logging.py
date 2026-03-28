from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from polls.models import HousePoll, QuickPoll, PollLog
from houses.models import House
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class PollLoggingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password')
        self.house = House.objects.create(name='Test House', creator=self.user)
        self.house.members.add(self.user)
        self.house_poll = HousePoll.objects.create(
            question='House Poll Question?',
            options=['Yes', 'No'],
            house=self.house,
            creator=self.user,
            dead_line=timezone.now() + timedelta(days=1),
            max_participants=10,
            is_ticket_secured=False
        )
        self.quick_poll = QuickPoll.objects.create(
            question='Quick Poll Question?',
            options=['A', 'B'],
            dead_line=timezone.now() + timedelta(days=1),
            max_participants=10,
            is_ticket_secured=False
        )
        self.client = Client()
        self.client.login(username='testuser', password='password')

    def test_house_poll_visit_logging(self):
        # Visit vote page
        url = reverse('polls:house_poll_vote', kwargs={'external_id': self.house_poll.external_id})
        self.client.get(url)
        
        # logs = PollLog.objects.filter(content_type__model='housepoll', object_id=self.house_poll.id, action_type='VISIT')
        logs = PollLog.objects.filter(object_id=self.house_poll.id, action_type='VISIT')
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().user, self.user)

        # Visit results page
        url = reverse('polls:house_poll_results', kwargs={'external_id': self.house_poll.external_id})
        self.client.get(url)
        self.assertEqual(PollLog.objects.filter(object_id=self.house_poll.id, action_type='VISIT').count(), 2)

    def test_quick_poll_visit_logging(self):
        # Visit vote page
        url = reverse('polls:quickpoll_vote', kwargs={'external_id': self.quick_poll.external_id})
        self.client.get(url)
        
        logs = PollLog.objects.filter(object_id=self.quick_poll.id, action_type='VISIT')
        self.assertEqual(logs.count(), 1)
        # Quick poll visit should also log the user if authenticated
        self.assertEqual(logs.first().user, self.user)

    def test_vote_logging(self):
        # Vote in house poll
        url = reverse('polls:house_poll_vote', kwargs={'external_id': self.house_poll.external_id})
        # Condorcet vote expects ranked choices. VoteForm expects choices in a specific format usually.
        # Let's check VoteForm in polls/forms.py
        data = {
            'choice_0': 'Yes',
            'choice_1': 'No'
        }
        # Wait, I need to know how the form is structured.
        
        # Actually I can just test the model method save_ballot directly to ensure it logs,
        # and then a simple client post if I can figure out the form.
        
        self.house_poll.save_ballot(choices={'Yes': 1, 'No': 2}, user=self.user, ip_address='127.0.0.1')
        logs = PollLog.objects.filter(object_id=self.house_poll.id, action_type='VOTE')
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().user, self.user)
        self.assertEqual(logs.first().ip_address, '127.0.0.1')

    def test_anonymous_visit_logging(self):
        self.client.logout()
        url = reverse('polls:quickpoll_vote', kwargs={'external_id': self.quick_poll.external_id})
        self.client.get(url)
        
        logs = PollLog.objects.filter(object_id=self.quick_poll.id, action_type='VISIT')
        self.assertEqual(logs.count(), 1)
        self.assertIsNone(logs.first().user)
