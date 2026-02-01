# Generated migration for adding user_type field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Account', '0005_alter_user_last_login'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='user_type',
            field=models.CharField(
                choices=[('free', 'Free'), ('premium', 'Premium'), ('student', 'Student')],
                default='free',
                max_length=20
            ),
        ),
    ]
