# Generated by Django 5.1.6 on 2025-04-04 17:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0045_alter_company_national_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='company',
            name='National_ID',
            field=models.CharField(max_length=100, null=True, unique=True, verbose_name='شناسه ملی'),
        ),
    ]
