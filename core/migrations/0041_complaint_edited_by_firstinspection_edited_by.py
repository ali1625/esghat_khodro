# Generated by Django 5.1.6 on 2025-04-03 12:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0040_firstinspection_diagnosis_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='complaint',
            name='edited_by',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='ویرایش\u200cکننده'),
        ),
        migrations.AddField(
            model_name='firstinspection',
            name='edited_by',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='ویرایش\u200cکننده'),
        ),
    ]
