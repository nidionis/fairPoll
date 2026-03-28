from django.test import TestCase
from polls.forms import HousePollForm, QuickPollForm

class PollFormsTest(TestCase):
    def test_house_poll_form_options_comma_separated_fails(self):
        # New behavior: options are NOT comma-separated anymore, they are line-separated.
        # So "Red, Green, Blue" should be treated as ONE option (if no newline).
        form_data = {
            'question': 'What is your favorite color?',
            'options_text': 'Red, Green, Blue',
            'dead_line': '2026-12-31T23:59:59',
            'is_ticket_secured': False,
        }
        form = HousePollForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Please provide at least two options.', form.errors['options_text'])

    def test_house_poll_form_options_line_separated(self):
        # Desired behavior: options are line-separated
        form_data = {
            'question': 'What is your favorite color?',
            'options_text': 'Red\nGreen\nBlue',
            'dead_line': '2026-12-31T23:59:59',
            'is_ticket_secured': False,
        }
        form = HousePollForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['options_text'], ['Red', 'Green', 'Blue'])

    def test_quick_poll_form_options_line_separated(self):
        # Desired behavior: options are line-separated
        form_data = {
            'question': 'What is your favorite color?',
            'options_text': 'Red\r\nGreen\r\nBlue',
            'dead_line': '2026-12-31T23:59:59',
            'max_participants': 10,
            'is_ticket_secured': False,
        }
        form = QuickPollForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['options_text'], ['Red', 'Green', 'Blue'])
