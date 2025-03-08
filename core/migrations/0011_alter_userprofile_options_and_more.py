from django.db import migrations, models
import uuid

def generate_unique_national_code(apps, schema_editor):
    UserProfile = apps.get_model('core', 'UserProfile')
    for profile in UserProfile.objects.all():
        # تولید یه کد 10 رقمی یکتا
        profile.national_code = str(uuid.uuid4().int)[:10]
        profile.save()

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0010_editlog'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='userprofile',
            options={'verbose_name': 'پروفایل کاربر', 'verbose_name_plural': 'پروفایل\u200cهای کاربران'},
        ),
        migrations.AddField(
            model_name='userprofile',
            name='national_code',
            field=models.CharField(
                max_length=10,
                unique=True,
                null=True,  # موقتاً nullable تا تابع اجرا بشه
                verbose_name='کد ملی'
            ),
        ),
        migrations.RunPython(generate_unique_national_code),
        migrations.AlterField(
            model_name='userprofile',
            name='national_code',
            field=models.CharField(
                max_length=10,
                unique=True,
                verbose_name='کد ملی'
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='phone_number',
            field=models.CharField(
                max_length=11,
                verbose_name='شماره موبایل',
                default='09120000000'
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='must_change_password',
            field=models.BooleanField(
                default=True,
                verbose_name='باید رمز را تغییر دهد'
            ),
        ),
    ]