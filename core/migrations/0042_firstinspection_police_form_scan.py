# Generated by Django 5.1.6 on 2025-04-04 11:44

import core.utils
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0041_complaint_edited_by_firstinspection_edited_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='firstinspection',
            name='police_form_scan',
            field=models.ImageField(blank=True, null=True, upload_to=core.utils.rename_uploaded_file, verbose_name='اسکن فرم پلیس راهور'),
        ),
    ]
