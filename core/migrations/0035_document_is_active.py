# Generated by Django 5.1.6 on 2025-03-27 15:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_remove_complaint_delivery_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='فعال'),
        ),
    ]
