# core/admin.py
from django.contrib import admin
from .models import Company

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')  # ستون‌هایی که توی لیست نشون داده می‌شن
    list_filter = ('is_active',)  # فیلتر بر اساس فعال/غیرفعال
    search_fields = ('name', 'code')  # جستجو بر اساس نام و کد