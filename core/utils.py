from django.db import models
import os
from django.utils.text import slugify
from django.conf import settings
from jdatetime import datetime as jdatetime_datetime


def is_company_admin(user):
    return user.is_authenticated and hasattr(user, 'userprofile') and user.userprofile.role == 'admin'

def is_admin_or_superuser(user):
    return user.is_superuser or is_company_admin(user)


def rename_uploaded_file(instance, filename):
    """
    تغییر نام فایل و پوشه‌بندی به فرمت: سال/ماه/شماره پذیرش خودرو/شماره پذیرش + نام فیلد + عدد ۳ رقمی
    سال و ماه از delivery_date گرفته می‌شه
    مثال: media/1404/06/140325001/140325001-front-001.png
    """
    # گرفتن شماره پذیرش خودرو و تاریخ تحویل
    if hasattr(instance, 'car') and instance.car:
        acceptance_number = instance.car.acceptance_number
        delivery_date = instance.car.delivery_date
    elif hasattr(instance, 'acceptance_number') and hasattr(instance, 'delivery_date'):
        acceptance_number = instance.acceptance_number
        delivery_date = instance.delivery_date
    else:
        raise ValueError("شماره پذیرش خودرو یا تاریخ تحویل پیدا نشد!")

    # گرفتن سال و ماه از تاریخ تحویل
    try:
        jalali_date = jdatetime_datetime.strptime(delivery_date, '%Y/%m/%d')
        year = jalali_date.strftime('%Y')  # مثلاً 1404
        month = jalali_date.strftime('%m')  # مثلاً 06
    except ValueError:
        raise ValueError("فرمت تاریخ تحویل اشتباه است. باید به شکل '1404/06/25' باشد.")

    # گرفتن نام فیلد
    field_name = None
    for field in instance._meta.fields:
        if isinstance(field, (models.FileField, models.ImageField)) and getattr(instance, field.name) == filename:
            field_name = slugify(field.name)  # مثلاً front_image -> front
            break
    if not field_name:
        field_name = "file"  # پیش‌فرض

    # گرفتن پسوند فایل
    ext = filename.split('.')[-1]

    # پیدا کردن آخرین عدد ترتیبی برای این خودرو و این فیلد
    base_path = os.path.join(year, month, acceptance_number)
    full_path = os.path.join(settings.MEDIA_ROOT, base_path)
    os.makedirs(full_path, exist_ok=True)  # اگه پوشه نبود، می‌سازه

    existing_files = []
    if os.path.exists(full_path):
        for f in os.listdir(full_path):
            if f.startswith(f"{acceptance_number}-{field_name}-") and f.endswith(f".{ext}"):
                existing_files.append(f)

    if existing_files:
        last_number = max(int(f.split('-')[-1].split('.')[0]) for f in existing_files)
        next_number = last_number + 1
    else:
        next_number = 1  # از 001 شروع می‌کنه

    # ساخت عدد ۳ رقمی
    number_str = f"{next_number:03d}"  # همیشه ۳ رقمی مثلاً 001, 002

    # ساخت اسم جدید
    new_filename = f"{acceptance_number}-{field_name}-{number_str}.{ext}"

    # مسیر نهایی
    upload_path = os.path.join(base_path, new_filename)

    return upload_path