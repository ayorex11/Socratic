# Generated manually for payment app

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0001_initial'),  # Update this to your latest migration
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='reference',
            field=models.CharField(
                db_index=True,
                max_length=50,
                unique=True
            ),
        ),
    ]
