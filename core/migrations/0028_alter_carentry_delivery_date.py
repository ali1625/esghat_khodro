# Generated by Django 5.1.6 on 2025-03-23 22:56

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_secondinspection'),
    ]

    operations = [
        migrations.AlterField(
            model_name='carentry',
            name='delivery_date',
            field=models.CharField(default=datetime.date.today, max_length=10, verbose_name='تاریخ تحویل'),
            preserve_default=False,
        ),
    ]
