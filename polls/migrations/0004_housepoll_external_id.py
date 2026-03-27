import polls.models
import secrets
import string
from django.db import migrations, models

def generate_unique_external_ids(apps, schema_editor):
    HousePoll = apps.get_model('polls', 'HousePoll')
    for poll in HousePoll.objects.all():
        if not poll.external_id:
            # Generate a unique 8-char ID
            while True:
                new_id = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                if not HousePoll.objects.filter(external_id=new_id).exists():
                    poll.external_id = new_id
                    break
            poll.save()

class Migration(migrations.Migration):

    dependencies = [
        ('polls', '0003_alter_quickpoll_external_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='housepoll',
            name='external_id',
            field=models.CharField(max_length=8, null=True),
        ),
        migrations.RunPython(generate_unique_external_ids),
        migrations.AlterField(
            model_name='housepoll',
            name='external_id',
            field=models.CharField(default=polls.models.generate_ticket_code, editable=False, max_length=8, unique=True),
        ),
    ]
