# Generated by Django 5.1.6 on 2025-03-22 19:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_carentry_serial_number_alter_carentry_accepted_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='carentry',
            name='Physical_readiness',
            field=models.BooleanField(default=False, verbose_name='آمادگی فیزیکی'),
        ),
    ]
