# Generated migration for account pause feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_mfa_and_password_reset'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='account_paused',
            field=models.BooleanField(
                default=False,
                help_text='Account is paused - data retained but not processed',
            ),
        ),
        migrations.AddField(
            model_name='profile',
            name='account_paused_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When the account was paused',
                null=True,
            ),
        ),
    ]
