# Generated by Django 4.2.16 on 2025-03-02 19:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='carentry',
            name='license_plate',
            field=models.CharField(max_length=30, verbose_name='شماره انتظامی'),
        ),
    ]
