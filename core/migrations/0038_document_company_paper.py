# Generated by Django 5.1.6 on 2025-03-30 22:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0037_document_deceased_doc1_document_deceased_doc2_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='company_paper',
            field=models.ImageField(blank=True, null=True, upload_to='deceased_docs/', verbose_name='مدرک فوتی ۱'),
        ),
    ]
