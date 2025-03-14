import sys

from arabic_reshaper import arabic_reshaper
from bidi import get_display
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
#from jdatetime import datetime as jdatetime
from jdatetime import datetime as jdatetime_datetime
from django.contrib import messages
from django.db.models import Q
from django.db import models
from django import forms
from reportlab.lib import colors

from .models import CarEntry, CarParts, EditLog, UserProfile, Document
from .forms import CarEntryForm, CarPartsForm, CarCostsForm, CustomUserCreationForm, SearchLogForm, \
    FinalRegistrationForm, DocumentForm
from .forms import AdminChangePasswordForm, UserProfileEditForm
from django.contrib.auth import update_session_auth_hash
from .forms import AdminChangePasswordForm, UserProfileEditForm, AdminUserCreationForm, CustomPasswordChangeForm
from django.http import HttpResponse
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from django.db import IntegrityError
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import re


def home(request):
    print(f"Home - User authenticated: {request.user.is_authenticated}")
    if request.user.is_authenticated:
        recent_cars = CarEntry.objects.order_by('-accepted_at')[:5]
        return render(request, 'core/home.html', {'recent_cars': recent_cars})
    print("Home - Redirecting to login")
    return redirect('login')


class RoleChangeForm(forms.Form):
    role = forms.ChoiceField(
        choices=[('admin', 'ادمین'), ('regular', 'کاربر معمولی')],
        label="نقش",
        widget=forms.Select(attrs={'class': 'form-select'})
    )


def is_admin(user):
    try:
        return user.is_authenticated and user.userprofile.role == 'admin'
    except UserProfile.DoesNotExist:
        return False

@login_required
@user_passes_test(is_admin)
def user_management(request):
    users = User.objects.all().order_by('-date_joined')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        user = get_object_or_404(User, id=user_id)

        if action == 'delete':
            if user == request.user:
                messages.error(request, 'شما نمی‌توانید خودتان را حذف کنید.')
            else:
                user.delete()
                messages.success(request, 'کاربر با موفقیت حذف شد.')
        elif action == 'toggle_active':
            if user == request.user:
                messages.error(request, 'شما نمی‌توانید خودتان را غیرفعال کنید.')
            else:
                user.is_active = not user.is_active
                user.save()
                status = 'فعال' if user.is_active else 'غیرفعال'
                messages.success(request, f'کاربر با موفقیت {status} شد.')
        return redirect('user_management')

    forms_list = []
    for user in users:
        try:
            role_form = RoleChangeForm(initial={'role': user.userprofile.role})
            forms_list.append((user, role_form))
        except UserProfile.DoesNotExist:
            forms_list.append((user, None))

    return render(request, 'core/user_management.html', {
        'users_with_forms': forms_list,
    })


@login_required
@user_passes_test(is_admin)
def admin_change_password(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = AdminChangePasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user.set_password(new_password)
            user.save()
            messages.success(request, f'رمز عبور کاربر {user.username} با موفقیت تغییر کرد.')
            return redirect('user_management')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
    else:
        form = AdminChangePasswordForm()
    return render(request, 'core/admin_change_password.html', {
        'form': form,
        'user': user,
    })

@login_required
@user_passes_test(is_admin)
def edit_user_profile(request, user_id):
    user = get_object_or_404(User, id=user_id)
    try:
        profile = user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile(user=user)

    if request.method == 'POST':
        form = UserProfileEditForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            # چک کن که ادمین نقش خودش رو به regular تغییر نده
            if user == request.user and form.cleaned_data['role'] == 'regular' and profile.role != 'regular':
                messages.error(request, 'شما نمی‌توانید نقش خودتان را به کاربر معمولی تغییر دهید.')
            else:
                profile.save()
                messages.success(request, f'پروفایل کاربر {user.username} با موفقیت ویرایش شد.')
                return redirect('user_management')
        else:
            messages.error(request, 'اطلاعات واردشده نامعتبر است.')
    else:
        form = UserProfileEditForm(instance=profile)
        # اگه کاربر خودشو ویرایش می‌کنه، فیلد نقش رو غیرفعال کن
        if user == request.user:
            form.fields['role'].disabled = True
            form.fields['role'].help_text = 'شما نمی‌توانید نقش خودتان را تغییر دهید.'

    return render(request, 'core/edit_user_profile.html', {
        'form': form,
        'user': user,
    })

@login_required
@user_passes_test(is_admin)
def add_user(request):
    if request.method == 'POST':

        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'کاربر {user.username} با موفقیت ثبت شد. رمز اولیه: {form.cleaned_data["national_code"]}')
            return redirect('user_management')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
    else:
        form = AdminUserCreationForm()
    return render(request, 'core/add_user.html', {'form': form})

@login_required
def update_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, 'رمز عبور شما با موفقیت تغییر کرد.')
            return redirect('home')  # یا هر صفحه‌ای که می‌خوای
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'core/update_password.html', {'form': form})

@login_required
def change_password(request):
    from .models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=request.user, defaults={'must_change_password': True})
    if not profile.must_change_password:
        return redirect('home')
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['new_password'])
            profile.must_change_password = False
            profile.save()
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'رمز عبور شما با موفقیت تغییر کرد.')
            return redirect('home')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
    else:
        form = CustomPasswordChangeForm()
    return render(request, 'core/change_password.html', {'form': form})
@login_required
@user_passes_test(is_admin, login_url='home')
def edit_logs(request, acceptance_number='all'):
    # فرم جستجو
    form = SearchLogForm(request.GET or None)
    logs = EditLog.objects.all().order_by('-edited_at')
    car = None

    # اعمال فیلتر جستجو
    if form.is_valid() and form.cleaned_data['acceptance_number']:
        search_term = form.cleaned_data['acceptance_number']
        logs = logs.filter(car_entry__acceptance_number__icontains=search_term)

    # اگه acceptance_number خاص باشه
    if acceptance_number != 'all':
        car = get_object_or_404(CarEntry, acceptance_number=acceptance_number)
        logs = logs.filter(car_entry=car)

    # صفحه‌بندی
    paginator = Paginator(logs, 50)  # 50 سطر در هر صفحه
    page_number = request.GET.get('page')
    try:
        page_logs = paginator.page(page_number)
    except PageNotAnInteger:
        page_logs = paginator.page(1)
    except EmptyPage:
        page_logs = paginator.page(paginator.num_pages)

    return render(request, 'core/edit_logs.html', {
        'car': car,
        'logs': page_logs,
        'form': form,
        'paginator': paginator,
    })
def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            profile, created = UserProfile.objects.get_or_create(user=user, defaults={'must_change_password': True})
            if profile.must_change_password:
                return redirect('change_password')
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})
def user_logout(request):
    logout(request)
    return redirect('login')

@login_required
def register_user(request):
    if not request.user.is_superuser:
        return redirect('registration_list')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'کاربر جدید با موفقیت ثبت شد.')
            return redirect('registration_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/register_user.html', {'form': form})

@login_required
def select_car_for_parts(request):
    cars_without_parts = CarEntry.objects.filter(parts__isnull=True)
    
    if request.method == 'POST':
        selected_car_number = request.POST.get('selected_car')
        if selected_car_number:
            return redirect('add_car_parts_step2', acceptance_number=selected_car_number)
        else:
            messages.error(request, 'لطفاً یک خودرو انتخاب کنید.')
    
    context = {
        'cars_without_parts': cars_without_parts,
    }
    return render(request, 'core/select_car_for_parts.html', context)

@login_required
def select_car_for_costs(request):
    cars_without_costs = CarEntry.objects.filter(costs__isnull=True)
    
    if request.method == 'POST':
        selected_car_number = request.POST.get('selected_car')
        if selected_car_number:
            return redirect('add_car_costs_step3', acceptance_number=selected_car_number)
        else:
            messages.error(request, 'لطفاً یک خودرو انتخاب کنید.')
    
    context = {
        'cars_without_costs': cars_without_costs,
    }
    return render(request, 'core/select_car_for_costs.html', context)


# @login_required
# def add_document(request):
#     sys.stdout.reconfigure(encoding='utf-8')
#     selected_car = request.session.get('selected_car')
#     car = None
#     if selected_car:
#         car = get_object_or_404(CarEntry, acceptance_number=selected_car)
#
#     if request.method == 'POST':
#         form = DocumentForm(request.POST, request.FILES)
#         if form.is_valid():
#             document = form.save(commit=False)
#             document.created_by = request.user
#             if car:
#                 # پر کردن شماره موتور و شاسی از ماشین انتخاب‌شده
#                 document.engine_number = car.engine_number
#                 document.chassis_number = car.chassis_number  # اضافه کردن شماره شاسی
#                 document.car = car  # اتصال سند به خودرو
#             document.save()
#
#             # برای ثبت معکوس توی CarEntry
#             if car:
#                 car.document = document
#                 car.save(update_fields=['document'])  # آپدیت فقط document_id
#
#             messages.success(request, f"سند با شماره موتور {document.engine_number} با موفقیت ثبت شد.")
#             if 'selected_car' in request.session:
#                 del request.session['selected_car']
#             return redirect('registration_list')
#         else:
#             messages.error(request, 'لطفاً خطاها را برطرف کنید.')
#             print("Form errors:", form.errors)
#     else:
#         initial_data = {}
#         if car:
#             initial_data['engine_number'] = car.engine_number
#             initial_data['chassis_number'] = car.chassis_number  # مقدار اولیه برای شاسی
#         form = DocumentForm(initial=initial_data)
#     return render(request, 'core/add_document.html', {'form': form, 'car': car})#

@login_required
def document_list(request):
    engine_number = request.GET.get('engine_number', '')
    chassis_number = request.GET.get('chassis_number', '')
    acceptance_number = request.GET.get('acceptance_number', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    car_status = request.GET.get('car_status', '')

    documents = Document.objects.all()

    if engine_number:
        documents = documents.filter(engine_number__icontains=engine_number)
    if chassis_number:
        documents = documents.filter(chassis_number__icontains=chassis_number)
    if acceptance_number:
        documents = documents.filter(car__acceptance_number__icontains=acceptance_number)
    if date_from:
        date_from_gregorian = jdatetime_datetime.strptime(date_from, '%Y/%m/%d').togregorian().date()
        documents = documents.filter(created_at_gregorian__gte=date_from_gregorian)
    if date_to:
        date_to_gregorian = jdatetime_datetime.strptime(date_to, '%Y/%m/%d').togregorian().date()
        documents = documents.filter(created_at_gregorian__lte=date_to_gregorian)
    if car_status:
        if car_status == 'connected':
            documents = documents.filter(car__isnull=False)
        elif car_status == 'not_connected':
            documents = documents.filter(car__isnull=True)

    documents = documents.order_by('-created_at_gregorian')  # مرتب‌سازی بر اساس تاریخ میلادی
    paginator = Paginator(documents, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/document_list.html', {
        'page_obj': page_obj,
        'engine_number': engine_number,
        'chassis_number': chassis_number,
        'acceptance_number': acceptance_number,
        'date_from': date_from,
        'date_to': date_to,
        'car_status': car_status,
    })

@login_required
def add_document(request):
    sys.stdout.reconfigure(encoding='utf-8')
    selected_car = request.session.get('selected_car')
    car = None
    if selected_car:
        car = get_object_or_404(CarEntry, acceptance_number=selected_car)

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.created_by = request.user
            if car:
                document.engine_number = car.engine_number
                document.chassis_number = car.chassis_number
            document.save()
            messages.success(request, f"سند با شماره موتور {document.engine_number} با موفقیت ثبت شد.")
            if 'selected_car' in request.session:
                del request.session['selected_car']
            return redirect('registration_list')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
            print("Form errors:", form.errors)
    else:
        initial_data = {}
        if car:
            initial_data['engine_number'] = car.engine_number
            initial_data['chassis_number'] = car.chassis_number
        form = DocumentForm(initial=initial_data)
    return render(request, 'core/add_document.html', {'form': form, 'car': car})

@login_required
def edit_document(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            document = form.save()
            messages.success(request, f"سند با شماره موتور {document.engine_number} با موفقیت ویرایش شد.")
            return redirect('document_list')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
            print("Form errors:", form.errors)
    else:
        form = DocumentForm(instance=document)
    return render(request, 'core/edit_document.html', {'form': form, 'document': document})

@login_required
def add_car_entry_step1(request):
    sys.stdout.reconfigure(encoding='utf-8')
    if request.method == 'POST':
        form = CarEntryForm(request.POST, request.FILES)  # اضافه کردن request.FILES برای فایل‌ها
        if form.is_valid():
            car_entry = form.save(commit=False)
            # ذخیره با کاربر لاگین‌شده
            car_entry.save(user=request.user)
            # ساخت پیام سفارشی با accepted_by و acceptance_number
            success_message = f"خودرو با شماره پذیرش {car_entry.acceptance_number} توسط {car_entry.accepted_by} با موفقیت ثبت شد"
            messages.success(request, success_message)
            return redirect('home')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
            print("Form errors:", form.errors)
    else:
        form = CarEntryForm()
    return render(request, 'core/add_car_entry_step1.html', {'form': form})

@login_required
def edit_car_entry(request, acceptance_number):
    sys.stdout.reconfigure(encoding='utf-8')
    car = get_object_or_404(CarEntry, acceptance_number=acceptance_number)
    if request.method == 'POST':
        form = CarEntryForm(request.POST, request.FILES, instance=car)
        if form.is_valid():
            car_instance = form.save(commit=False)
            car_instance.save(user=request.user)
            EditLog.objects.create(
                edit_type='CAR_ENTRY',
                car_entry=car_instance,
                edited_by=request.user
            )
            messages.success(request, f"اطلاعات خودرو با موفقیت توسط {car_instance.edited_by} ویرایش شد.")
            return redirect('registration_list')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
            print("Form errors:", form.errors)
    else:
        initial_data = {
            'delivery_date': car.delivery_date,  # تاریخ تحویل رو مستقیماً از نمونه می‌گیره
        }
        if car.license_plate:
            try:
                parts = car.license_plate.split(' - ')
                if len(parts) == 4:
                    initial_data['digits1'] = parts[0]
                    initial_data['persian_letter'] = parts[1]
                    initial_data['digits2'] = parts[2]
                    initial_data['digits3'] = parts[3].replace('ایران ', '')
            except Exception as e:
                print(f"Error parsing license_plate: {e}")
        if car.driver_license_plate:
            try:
                parts = car.driver_license_plate.split(' - ')
                if len(parts) == 4:
                    initial_data['driver_digits1'] = parts[0]
                    initial_data['driver_persian_letter'] = parts[1]
                    initial_data['driver_digits2'] = parts[2]
                    initial_data['driver_digits3'] = parts[3].replace('ایران ', '')
            except Exception as e:
                print(f"Error parsing driver_license_plate: {e}")
        form = CarEntryForm(instance=car, initial=initial_data)
    return render(request, 'core/edit_car_entry.html', {'form': form, 'car': car})
@login_required
def add_car_parts_step2(request, acceptance_number):
    car = get_object_or_404(CarEntry, acceptance_number=acceptance_number)

    if hasattr(car, 'parts') and car.parts:
        messages.error(request, 'قطعات این خودرو قبلاً ثبت شده است. لطفاً از ویرایش قطعات استفاده کنید.')
        return redirect('edit_car_parts', acceptance_number=car.acceptance_number)

    if request.method == 'POST':
        form = CarPartsForm(request.POST)
        if form.is_valid():
            car_parts = form.save(commit=False)
            car_parts.car = car
            car_parts.recorded_by = request.user
            car_parts.recorded_at = jdatetime_datetime.now().strftime('%Y/%m/%d')
            try:
                car_parts.save()
                full_name = f"{request.user.userprofile.first_name} {request.user.userprofile.last_name}" if hasattr(
                    request.user, 'userprofile') else request.user.username
                messages.success(request,
                                 f"قطعات خودرو با شماره پذیرش {car.acceptance_number} توسط {full_name} با موفقیت ثبت شد.")
                return redirect('registration_list')
            except IntegrityError:
                messages.error(request, 'خطا: قطعات برای این خودرو قبلاً ثبت شده است.')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
            print("Form errors:", form.errors)
    else:
        form = CarPartsForm()
    return render(request, 'core/add_car_parts_step2.html', {'form': form, 'car': car})


@login_required
def add_car_costs_step3(request, acceptance_number):
    car = get_object_or_404(CarEntry, acceptance_number=acceptance_number)

    if hasattr(car, 'costs') and car.costs:
        messages.error(request, 'هزینه‌های این خودرو قبلاً ثبت شده است. لطفاً از ویرایش هزینه‌ها استفاده کنید.')
        return redirect('edit_car_costs', acceptance_number=car.acceptance_number)

    if request.method == 'POST':
        form = CarCostsForm(request.POST, request.FILES)
        if form.is_valid():
            car_costs = form.save(commit=False)
            car_costs.car = car
            car_costs.recorded_by = request.user
            car_costs.recorded_at = jdatetime_datetime.now().strftime('%Y/%m/%d')
            try:
                car_costs.save()  # total_cost توی مدل محاسبه می‌شه
                messages.success(request, f"هزینه‌های خودرو با شماره پذیرش {car.acceptance_number} با موفقیت ثبت شد.")
                return redirect('registration_list')
            except IntegrityError:
                messages.error(request, 'خطا: هزینه‌ها برای این خودرو قبلاً ثبت شده است.')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
            print("Form errors:", form.errors)
    else:
        form = CarCostsForm()
    return render(request, 'core/add_car_costs_step3.html', {'form': form, 'car': car})

@login_required
def edit_car_parts(request, acceptance_number):
    car = get_object_or_404(CarEntry, acceptance_number=acceptance_number)
    parts = car.parts  # فرض می‌کنیم رابطه one-to-one برقراره
    if request.method == 'POST':
        form = CarPartsForm(request.POST, instance=parts)
        if form.is_valid():
            form.save()
            # ثبت لاگ
            EditLog.objects.create(
                edit_type='CAR_PARTS',
                car_entry=car,
                edited_by=request.user
            )
            messages.success(request, f"قطعات خودرو با شماره پذیرش {car.acceptance_number} با موفقیت ویرایش شد.")
            return redirect('registration_list')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
            print("Form errors:", form.errors)  # خطاها رو توی کنسول چاپ می‌کنه
    else:
        form = CarPartsForm(instance=parts)
    return render(request, 'core/edit_car_parts.html', {'form': form, 'car': car})
@login_required
def edit_car_costs(request, acceptance_number):
    car = get_object_or_404(CarEntry, acceptance_number=acceptance_number)
    costs = car.costs
    if not costs:
        messages.error(request, 'هزینه‌های این خودرو هنوز ثبت نشده است.')
        return redirect('add_car_costs_step3_form', acceptance_number=car.acceptance_number)
    
    if request.method == 'POST':
        form = CarCostsForm(request.POST, request.FILES, instance=costs)
        if form.is_valid():
            car_costs = form.save(commit=False)
            # recorded_by رو تغییر نمی‌دیم، همون مقدار اولیه می‌مونه
            car_costs.save()
            # ثبت لاگ
            EditLog.objects.create(
                edit_type='CAR_COSTS',
                car_entry=car,
                edited_by=request.user
            )
            #پیغام
            messages.success(request, 'هزینه‌های خودرو با موفقیت ویرایش شد.')
            return redirect('registration_list')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
            print("Form errors:", form.errors)
    else:
        form = CarCostsForm(instance=costs)
    return render(request, 'core/edit_car_costs.html', {'form': form, 'car': car})


@login_required
def car_details(request, acceptance_number):
    car = get_object_or_404(CarEntry, acceptance_number=acceptance_number)

    # خروجی PDF
    if 'export_pdf' in request.GET:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="car_details_{acceptance_number}.pdf"'
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        # ثبت فونت فارسی
        font_path = 'static/fonts/Vazirmatn-Regular.ttf'  # مسیر فونت رو چک کن
        pdfmetrics.registerFont(TTFont('Vazir', font_path))
        p.setFont('Vazir', 12)

        # تابع برای آماده‌سازی متن RTL
        def prepare_rtl_text(text):
            reshaped_text = arabic_reshaper.reshape(str(text))
            return get_display(reshaped_text)

        # عرض و ارتفاع صفحه
        page_width = A4[0]  # 595.27 pt
        page_height = A4[1]  # 841.89 pt
        column_width = page_width / 3  # تقریباً 198 pt برای هر ستون
        # تقسیم ارتفاع: اطلاعات خودرو و قطعات و هزینه‌ها هر کدوم 35%، سند 10%
        total_content_height = page_height - 100  # 100 pt برای عنوان
        section_height_main = total_content_height * 0.35  # برای اطلاعات خودرو، قطعات، هزینه‌ها
        section_height_doc = total_content_height * 0.10  # برای سند (فضای کمتر)
        margin = 20  # فاصله از لبه‌ها و بین ستون‌ها

        # مختصات شروع هر ستون در هر بخش (راست‌چین)
        col1_x = page_width - margin
        col2_x = page_width - column_width - margin
        col3_x = page_width - (2 * column_width) - margin

        # عنوان (وسط صفحه)
        p.setFont('Vazir', 16)
        p.setFillColor(colors.black)
        title = prepare_rtl_text(f"جزئیات خودرو: {car.acceptance_number}")
        title_width = p.stringWidth(title, 'Vazir', 16)
        p.drawString((page_width - title_width) / 2, page_height - 50, title)

        # بخش‌ها
        sections = [
            ("اطلاعات خودرو", [
                f"شماره پارکینگ: {car.parking_number or ''}",
                f"تاریخ تحویل: {car.delivery_date or ''}",
                f"نوع خودرو: {car.car_type or ''}",
                f"شماره انتظامی: {car.license_plate or ''}",
                f"نام مالک: {car.owner_name or ''}",
                f"شماره موتور: {car.engine_number or ''}",
                f"شماره شاسی: {car.chassis_number or ''}",
                f"پلاک اتاق: {'دارد' if car.has_cabin_plate else 'ندارد'}",
                f"شماره پذیرش: {car.acceptance_number}",
                f"مسئول پذیرش: {car.accepted_by or ''}",
                f"تاریخ پذیرش: {car.accepted_at or ''}",
                f"ویرایش‌کننده: {car.edited_by or ''}",
                f"نام راننده: {car.driver_name or ''}",
                f"شماره پلاک راننده: {car.driver_license_plate or ''}",
                f"شماره تماس راننده: {car.driver_phone or ''}",
            ], section_height_main),
            ("قطعات", [
                f"درصد اتاق: {car.parts.cabin_percentage or ''}" if hasattr(car,
                                                                            'parts') and car.parts else "قطعات هنوز ثبت نشده است.",
                (f"درب موتور: {'دارد' if car.parts.hood else 'ندارد'}",
                 car.parts.hood if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                              'parts') and car.parts else "",
                (f"رادیاتور: {'دارد' if car.parts.radiator else 'ندارد'}",
                 car.parts.radiator if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                  'parts') and car.parts else "",
                (f"ایسیو: {'دارد' if car.parts.ecu else 'ندارد'}",
                 car.parts.ecu if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                             'parts') and car.parts else "",
                (f"درب جلو و عقب: {'دارد' if car.parts.front_rear_doors else 'ندارد'}",
                 car.parts.front_rear_doors if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                          'parts') and car.parts else "",
                (f"سیم‌کشی: {'دارد' if car.parts.wiring else 'ندارد'}",
                 car.parts.wiring if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                'parts') and car.parts else "",
                (f"کابل باطری: {'دارد' if car.parts.battery_cable else 'ندارد'}",
                 car.parts.battery_cable if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                       'parts') and car.parts else "",
                (f"بخاری: {'دارد' if car.parts.heater else 'ندارد'}",
                 car.parts.heater if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                'parts') and car.parts else "",
                (f"فنر زیر و بند: {'دارد' if car.parts.suspension_spring else 'ندارد'}",
                 car.parts.suspension_spring if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                           'parts') and car.parts else "",
                (f"دینام: {'دارد' if car.parts.alternator else 'ندارد'}",
                 car.parts.alternator if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                    'parts') and car.parts else "",
                (f"موتور برف‌پاک‌کن: {'دارد' if car.parts.wiper_motor else 'ندارد'}",
                 car.parts.wiper_motor if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                     'parts') and car.parts else "",
                (f"رینگ و لاستیک: {'دارد' if car.parts.rims_tires else 'ندارد'}",
                 car.parts.rims_tires if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                    'parts') and car.parts else "",
                (f"کاربراتور: {'دارد' if car.parts.carburetor else 'ندارد'}",
                 car.parts.carburetor if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                    'parts') and car.parts else "",
                (f"استارت: {'دارد' if car.parts.starter else 'ندارد'}",
                 car.parts.starter if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                 'parts') and car.parts else "",
                (f"گیربکس: {'دارد' if car.parts.gearbox else 'ندارد'}",
                 car.parts.gearbox if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                 'parts') and car.parts else "",
                (f"دیفرانسیل: {'دارد' if car.parts.differential else 'ندارد'}",
                 car.parts.differential if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                      'parts') and car.parts else "",
                (f"دلکو و کوئل: {'دارد' if car.parts.distributor_coil else 'ندارد'}",
                 car.parts.distributor_coil if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                          'parts') and car.parts else "",
                (f"سیفون بنزین: {'دارد' if car.parts.fuel_pump else 'ندارد'}",
                 car.parts.fuel_pump if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                   'parts') and car.parts else "",
                (f"صندلی: {'دارد' if car.parts.seats else 'ندارد'}",
                 car.parts.seats if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                               'parts') and car.parts else "",
                (f"دیسک چرخ جلو: {'دارد' if car.parts.front_disc else 'ندارد'}",
                 car.parts.front_disc if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                    'parts') and car.parts else "",
                (f"باطری: {'دارد' if car.parts.battery else 'ندارد'}",
                 car.parts.battery if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                 'parts') and car.parts else "",
                (f"جعبه فرمان: {'دارد' if car.parts.steering_box else 'ندارد'}",
                 car.parts.steering_box if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                      'parts') and car.parts else "",
                (f"سپر عقب و جلو: {'دارد' if car.parts.bumpers else 'ندارد'}",
                 car.parts.bumpers if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                 'parts') and car.parts else "",
                (f"کاسه چرخ: {'دارد' if car.parts.wheel_drum else 'ندارد'}",
                 car.parts.wheel_drum if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                    'parts') and car.parts else "",
                (f"پلوس و گاردان: {'دارد' if car.parts.driveshaft_cv else 'ندارد'}",
                 car.parts.driveshaft_cv if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                       'parts') and car.parts else "",
                (f"ریل سوخت: {'دارد' if car.parts.fuel_rail else 'ندارد'}",
                 car.parts.fuel_rail if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                   'parts') and car.parts else "",
                (f"درب صندوق: {'دارد' if car.parts.trunk_lid else 'ندارد'}",
                 car.parts.trunk_lid if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                   'parts') and car.parts else "",
                (f"سند: {'دارد' if car.parts.documents else 'ندارد'}",
                 car.parts.documents if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                   'parts') and car.parts else "",
                (f"انژکتور و سوزن انژکتور: {'دارد' if car.parts.injector else 'ندارد'}",
                 car.parts.injector if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                  'parts') and car.parts else "",
                (f"شیشه: {'دارد' if car.parts.glass else 'ندارد'}",
                 car.parts.glass if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                               'parts') and car.parts else "",
                (f"کولر: {'دارد' if car.parts.ac else 'ندارد'}",
                 car.parts.ac if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                            'parts') and car.parts else "",
                f"کپسول: {car.parts.get_gas_cylinder_display() if hasattr(car, 'parts') and car.parts else ''}",
                (f"پوستر ترمز: {'دارد' if car.parts.brake_booster else 'ندارد'}",
                 car.parts.brake_booster if hasattr(car, 'parts') and car.parts else False) if hasattr(car,
                                                                                                       'parts') and car.parts else "",
                f"وزن: {car.parts.weight or ''}" if hasattr(car, 'parts') and car.parts else "",
                f"وضعیت پلاک: {car.parts.get_plate_status_display() if hasattr(car, 'parts') and car.parts else ''}",
                f"توضیحات پلاک: {car.parts.plate_description or ''}" if hasattr(car, 'parts') and car.parts else "",
                f"مسئول ثبت: {car.parts.recorded_by.username if car.parts.recorded_by else ''}" if hasattr(car,
                                                                                                           'parts') and car.parts else "",
                f"تاریخ ثبت: {car.parts.recorded_at or ''}" if hasattr(car, 'parts') and car.parts else "",
            ], section_height_main),
            ("هزینه‌ها", [
                f"قیمت روز: {car.costs.daily_price or ''}" if hasattr(car,
                                                                      'costs') and car.costs else "هزینه‌ها هنوز ثبت نشده است.",
                f"خلافی: {car.costs.fine or ''}" if hasattr(car, 'costs') and car.costs else "",
                f"سند خلافی: {car.costs.fine_document.name if car.costs.fine_document else ''}" if hasattr(car,
                                                                                                           'costs') and car.costs else "",
                f"هزینه دادگاهی: {car.costs.court_cost or ''}" if hasattr(car, 'costs') and car.costs else "",
                f"سند دادگاهی: {car.costs.court_document.name if car.costs.court_document else ''}" if hasattr(car,
                                                                                                               'costs') and car.costs else "",
                f"جمع کل: {car.costs.total_cost or ''}" if hasattr(car, 'costs') and car.costs else "",
                f"مسئول ثبت: {car.costs.recorded_by.username if car.costs.recorded_by else ''}" if hasattr(car,
                                                                                                           'costs') and car.costs else "",
                f"تاریخ ثبت: {car.costs.recorded_at or ''}" if hasattr(car, 'costs') and car.costs else "",
            ], section_height_main),
            ("سند", [
                (f"فایل ۱: {car.document.file1.name if car.document.file1 else ''}",
                 bool(car.document.file1)) if hasattr(car, 'document') and car.document else "سند هنوز ثبت نشده است.",
                (f"فایل ۲: {car.document.file2.name if car.document.file2 else ''}",
                 bool(car.document.file2)) if hasattr(car, 'document') and car.document else "",
                (f"فایل ۳: {car.document.file3.name if car.document.file3 else ''}",
                 bool(car.document.file3)) if hasattr(car, 'document') and car.document else "",
                f"ایجاد شده توسط: {car.document.created_by.username if car.document.created_by else ''}" if hasattr(car,
                                                                                                                    'document') and car.document else "",
                f"تاریخ ایجاد: {car.document.created_at.strftime('%Y/%m/%d %H:%M') if car.document.created_at else ''}" if hasattr(
                    car, 'document') and car.document else "",
            ], section_height_doc),
        ]

        # نمایش هر بخش با 3 ستون
        y_start = page_height - 100
        for section_idx, (section_title, section_data, section_height) in enumerate(sections):
            y = y_start - (sum(sections[i][2] for i in range(section_idx)))  # موقعیت عمودی هر بخش
            p.setFont('Vazir', 14)
            p.setFillColor(colors.black)
            rtl_title = prepare_rtl_text(section_title)
            title_width = p.stringWidth(rtl_title, 'Vazir', 14)
            p.drawString((page_width - title_width) / 2, y, rtl_title)
            y -= 20

            # حذف خطوط خالی و تقسیم داده‌ها به 3 ستون
            filtered_data = [item if isinstance(item, str) else item[0] for item in section_data if item]
            items_per_column = len(filtered_data) // 3 + (len(filtered_data) % 3 > 0)
            col1_data = filtered_data[:items_per_column]
            col2_data = filtered_data[items_per_column:2 * items_per_column]
            col3_data = filtered_data[2 * items_per_column:]

            # تنظیمات برای رنگ (آبی برای قطعات، سبز برای فایل‌ها)
            boolean_items = {item[0]: item[1] for item in section_data if isinstance(item, tuple)}

            # ستون اول
            p.setFont('Vazir', 10)
            y_col = y
            for line in col1_data:
                rtl_line = prepare_rtl_text(line)
                line_width = p.stringWidth(rtl_line, 'Vazir', 10)
                if line in boolean_items:
                    if section_title == "سند" and boolean_items[line]:
                        p.setFillColor(colors.green)  # سبز برای فایل‌های آپلود شده
                    elif section_title == "قطعات" and boolean_items[line]:
                        p.setFillColor(colors.blue)  # آبی برای قطعات True
                    else:
                        p.setFillColor(colors.black)
                else:
                    p.setFillColor(colors.black)
                p.drawString(col1_x - line_width, y_col, rtl_line)
                y_col -= 15

            # ستون دوم
            y_col = y
            for line in col2_data:
                rtl_line = prepare_rtl_text(line)
                line_width = p.stringWidth(rtl_line, 'Vazir', 10)
                if line in boolean_items:
                    if section_title == "سند" and boolean_items[line]:
                        p.setFillColor(colors.green)
                    elif section_title == "قطعات" and boolean_items[line]:
                        p.setFillColor(colors.blue)
                    else:
                        p.setFillColor(colors.black)
                else:
                    p.setFillColor(colors.black)
                p.drawString(col2_x - line_width, y_col, rtl_line)
                y_col -= 15

            # ستون سوم
            y_col = y
            for line in col3_data:
                rtl_line = prepare_rtl_text(line)
                line_width = p.stringWidth(rtl_line, 'Vazir', 10)
                if line in boolean_items:
                    if section_title == "سند" and boolean_items[line]:
                        p.setFillColor(colors.green)
                    elif section_title == "قطعات" and boolean_items[line]:
                        p.setFillColor(colors.blue)
                    else:
                        p.setFillColor(colors.black)
                else:
                    p.setFillColor(colors.black)
                p.drawString(col3_x - line_width, y_col, rtl_line)
                y_col -= 15

        p.showPage()
        p.save()
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response

    return render(request, 'core/car_details.html', {'car': car})
@login_required
def registration_list(request):
    cars = CarEntry.objects.filter(final_registration__isnull=True).order_by('-accepted_at')

    # گرفتن مقادیر از درخواست GET (فیلترها)
    query = request.GET.get('q', '').strip()
    acceptance_number = request.GET.get('acceptance_number', '').strip()
    license_plate = request.GET.get('license_plate', '').strip()
    parking_number = request.GET.get('parking_number', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    has_parts = request.GET.get('has_parts', '')
    has_costs = request.GET.get('has_costs', '')
    part_type = request.GET.get('part_type', '')

    # اعتبارسنجی تاریخ‌ها
    date_pattern = r'^\d{4}/\d{2}/\d{2}$'  # فرمت: 1403/12/15
    if start_date and not re.match(date_pattern, start_date):
        messages.error(request, 'فرمت "از تاریخ" اشتباه است. لطفاً از فرمت 1403/12/15 استفاده کنید.')
        start_date = ''
    if end_date and not re.match(date_pattern, end_date):
        messages.error(request, 'فرمت "تا تاریخ" اشتباه است. لطفاً از فرمت 1403/12/15 استفاده کنید.')
        end_date = ''
    if start_date and end_date:
        try:
            start_jdate = jdatetime_datetime.strptime(start_date, '%Y/%m/%d')
            end_jdate = jdatetime_datetime.strptime(end_date, '%Y/%m/%d')
            if start_jdate > end_jdate:
                messages.error(request, '"از تاریخ" نمی‌تواند بزرگ‌تر از "تا تاریخ" باشد.')
                start_date = ''
                end_date = ''
        except ValueError:
            messages.error(request, 'تاریخ‌ها نامعتبر هستند.')
            start_date = ''
            end_date = ''

    # اعمال فیلترها
    if query:
        cars = cars.filter(
            Q(acceptance_number__icontains=query) |
            Q(license_plate__icontains=query) |
            Q(car_type__icontains=query) |
            Q(owner_name__icontains=query) |
            Q(parking_number__icontains=query) |
            Q(engine_number__icontains=query) |
            Q(chassis_number__icontains=query) |
            Q(driver_name__icontains=query) |
            Q(driver_license_plate__icontains=query) |
            Q(driver_phone__icontains=query)
        )
    else:
        if acceptance_number:
            if len(acceptance_number) > 9:
                messages.error(request, 'شماره پذیرش نمی‌تواند بیشتر از 9 کاراکتر باشد.')
            else:
                cars = cars.filter(acceptance_number__icontains=acceptance_number)
        if license_plate:
            if len(license_plate) > 30:
                messages.error(request, 'شماره انتظامی نمی‌تواند بیشتر از 30 کاراکتر باشد.')
            else:
                cars = cars.filter(license_plate__icontains=license_plate)
        if parking_number:
            if len(parking_number) > 20:
                messages.error(request, 'شماره پارکینگ نمی‌تواند بیشتر از 20 کاراکتر باشد.')
            else:
                cars = cars.filter(parking_number__icontains=parking_number)
        if start_date:
            start_date_gregorian = jdatetime_datetime.strptime(start_date, '%Y/%m/%d').togregorian()
            cars = cars.filter(accepted_at__gte=start_date_gregorian)
        if end_date:
            end_date_gregorian = jdatetime_datetime.strptime(end_date, '%Y/%m/%d').togregorian()
            cars = cars.filter(accepted_at__lte=end_date_gregorian)
        if has_parts in ('yes', 'no'):
            cars = cars.filter(parts__isnull=(has_parts == 'no'))
        if has_costs in ('yes', 'no'):
            cars = cars.filter(costs__isnull=(has_costs == 'no'))
        if part_type:
            valid_parts = [field.name for field in CarParts._meta.fields if isinstance(field, models.BooleanField)]
            if part_type in valid_parts:
                cars = cars.filter(parts__isnull=False, **{f"parts__{part_type}": True})
            else:
                messages.error(request, 'نوع قطعه انتخاب‌شده نامعتبر است.')


    # مدیریت درخواست‌های POST (عملیات روی سطر انتخاب‌شده)
    if request.method == 'POST':
        selected_car = request.POST.get('selected_car')
        if not selected_car:
            messages.error(request, 'لطفاً یک ماشین را انتخاب کنید.')
        else:
            try:
                car = CarEntry.objects.get(acceptance_number=selected_car)

                if 'edit_entry' in request.POST:
                    return redirect('edit_car_entry', acceptance_number=selected_car)
                elif 'edit_parts' in request.POST:
                    if hasattr(car, 'parts') and car.parts:
                        return redirect('edit_car_parts', acceptance_number=selected_car)
                    else:
                        messages.error(request, 'قطعات برای این ماشین ثبت نشده است.')
                elif 'add_parts' in request.POST:
                    if not (hasattr(car, 'parts') and car.parts):
                        return redirect('add_car_parts_step2', acceptance_number=selected_car)
                    else:
                        messages.error(request, 'قطعات برای این ماشین قبلاً ثبت شده است.')
                elif 'edit_costs' in request.POST:
                    if hasattr(car, 'costs') and car.costs:
                        return redirect('edit_car_costs', acceptance_number=selected_car)
                    else:
                        messages.error(request, 'هزینه‌ها برای این ماشین ثبت نشده است.')
                elif 'add_costs' in request.POST:
                    if not (hasattr(car, 'costs') and car.costs):
                        return redirect('add_car_costs_step3', acceptance_number=selected_car)
                    else:
                        messages.error(request, 'هزینه‌ها برای این ماشین قبلاً ثبت شده است.')
                elif 'view_details' in request.POST:
                    return redirect('car_details', acceptance_number=selected_car)
                elif 'finalize' in request.POST:
                    return redirect('finalize_registration', acceptance_number=selected_car)
                elif 'add_document' in request.POST:
                    if not (hasattr(car, 'document') and car.document):
                        request.session['selected_car'] = selected_car
                        return redirect('add_document')
                    else:
                        messages.error(request, 'سند برای این ماشین قبلاً ثبت شده است.')
                elif 'edit_document' in request.POST:
                    if hasattr(car, 'document') and car.document:
                        return redirect('edit_document', pk=car.document.pk)
                    else:
                        messages.error(request, 'سندی برای این ماشین ثبت نشده است.')
            except CarEntry.DoesNotExist:
                messages.error(request, 'ماشین انتخاب‌شده وجود ندارد.')
    # خروجی اکسل
    if request.GET.get('export') == 'excel':
        wb = Workbook()
        ws = wb.active
        ws.title = "لیست ثبت"
        headers = [
            'شماره پذیرش', 'شماره پارکینگ', 'تاریخ تحویل', 'نوع خودرو', 'شماره انتظامی',
            'نام مالک', 'شماره موتور', 'شماره شاسی', 'پلاک اتاق', 'مسئول پذیرش',
            'تاریخ پذیرش', 'نام راننده', 'شماره پلاک راننده', 'شماره تماس راننده',
            'درصد اتاق', 'درب موتور', 'رادیاتور', 'ایسیو', 'درب جلو و عقب', 'سیم‌کشی',
            'کابل باطری', 'بخاری', 'فنر زیر و بند', 'دینام', 'موتور برف‌پاک‌کن', 'رینگ و لاستیک',
            'کاربراتور', 'استارت', 'گیربکس', 'دیفرانسیل', 'دلکو و کوئل', 'سیفون بنزین', 'صندلی',
            'دیسک چرخ جلو', 'باطری', 'جعبه فرمان', 'سپر عقب و جلو', 'کاسه چرخ', 'پلوس و گاردان',
            'ریل سوخت', 'درب صندوق', 'سند', 'انژکتور و سوزن انژکتور', 'شیشه', 'کولر', 'کپسول',
            'پوستر ترمز', 'وزن', 'وضعیت پلاک', 'توضیحات پلاک', 'مسئول ثبت قطعات', 'تاریخ ثبت قطعات',
            'قیمت روز', 'خلافی', 'هزینه دادگاهی', 'هزینه حمل', 'هزینه وکالت', 'جمع کل',
            'مسئول ثبت هزینه‌ها', 'تاریخ ثبت هزینه‌ها'
        ]
        ws.append(headers)

        for car in cars:
            parts_data = car.parts if hasattr(car, 'parts') and car.parts else None
            costs_data = car.costs if hasattr(car, 'costs') and car.costs else None

            row = [
                car.acceptance_number,
                car.parking_number,
                car.delivery_date,
                car.car_type,
                car.license_plate,
                car.owner_name,
                car.engine_number,
                car.chassis_number,
                'دارد' if car.has_cabin_plate else 'ندارد',
                car.accepted_by.username if car.accepted_by else '',
                car.accepted_at,
                car.driver_name,
                car.driver_license_plate,
                car.driver_phone,
                parts_data.cabin_percentage if parts_data else '',
                'دارد' if parts_data and parts_data.hood else 'ندارد',
                'دارد' if parts_data and parts_data.radiator else 'ندارد',
                'دارد' if parts_data and parts_data.ecu else 'ندارد',
                'دارد' if parts_data and parts_data.front_rear_doors else 'ندارد',
                'دارد' if parts_data and parts_data.wiring else 'ندارد',
                'دارد' if parts_data and parts_data.battery_cable else 'ندارد',
                'دارد' if parts_data and parts_data.heater else 'ندارد',
                'دارد' if parts_data and parts_data.suspension_spring else 'ندارد',
                'دارد' if parts_data and parts_data.alternator else 'ندارد',
                'دارد' if parts_data and parts_data.wiper_motor else 'ندارد',
                'دارد' if parts_data and parts_data.rims_tires else 'ندارد',
                'دارد' if parts_data and parts_data.carburetor else 'ندارد',
                'دارد' if parts_data and parts_data.starter else 'ندارد',
                'دارد' if parts_data and parts_data.gearbox else 'ندارد',
                'دارد' if parts_data and parts_data.differential else 'ندارد',
                'دارد' if parts_data and parts_data.distributor_coil else 'ندارد',
                'دارد' if parts_data and parts_data.fuel_pump else 'ندارد',
                'دارد' if parts_data and parts_data.seats else 'ندارد',
                'دارد' if parts_data and parts_data.front_disc else 'ندارد',
                'دارد' if parts_data and parts_data.battery else 'ندارد',
                'دارد' if parts_data and parts_data.steering_box else 'ندارد',
                'دارد' if parts_data and parts_data.bumpers else 'ندارد',
                'دارد' if parts_data and parts_data.wheel_drum else 'ندارد',
                'دارد' if parts_data and parts_data.driveshaft_cv else 'ندارد',
                'دارد' if parts_data and parts_data.fuel_rail else 'ندارد',
                'دارد' if parts_data and parts_data.trunk_lid else 'ندارد',
                'دارد' if parts_data and parts_data.documents else 'ندارد',
                'دارد' if parts_data and parts_data.injector else 'ندارد',
                'دارد' if parts_data and parts_data.glass else 'ندارد',
                'دارد' if parts_data and parts_data.ac else 'ندارد',
                parts_data.gas_cylinder if parts_data else '',
                'دارد' if parts_data and parts_data.brake_booster else 'ندارد',
                parts_data.weight if parts_data else '',
                parts_data.plate_status if parts_data else '',
                parts_data.plate_description if parts_data else '',
                parts_data.recorded_by.username if parts_data and parts_data.recorded_by else '',
                parts_data.recorded_at if parts_data else '',
                costs_data.daily_price if costs_data else '',
                costs_data.fine if costs_data else '',
                costs_data.court_cost if costs_data else '',
                costs_data.transport_cost if costs_data else '',
                costs_data.proxy_cost if costs_data else '',
                costs_data.total_cost if costs_data else '',
                costs_data.recorded_by.username if costs_data and costs_data.recorded_by else '',
                costs_data.recorded_at if costs_data else ''
            ]
            ws.append(row)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="registration_list.xlsx"'
        wb.save(response)
        return response

    # صفحه‌بندی
    paginator = Paginator(cars, 10)  # تغییر به 10 سطر در هر صفحه
    page_number = request.GET.get('page')
    try:
        page_cars = paginator.page(page_number)
    except PageNotAnInteger:
        page_cars = paginator.page(1)
    except EmptyPage:
        page_cars = paginator.page(paginator.num_pages)

    context = {
        'cars': page_cars,  # فقط صفحه فعلی رو می‌فرستیم
    }
    return render(request, 'core/registration_list.html', context)

# @login_required
# def check_status(request, acceptance_number):
#     car = get_object_or_404(CarEntry, acceptance_number=acceptance_number)
#     return JsonResponse({
#         'has_parts': hasattr(car, 'parts') and car.parts is not None,
#         'has_costs': hasattr(car, 'costs') and car.costs is not None,
#         'has_document': hasattr(car, 'document') and car.document is not None,
#     })
def check_status(request, acceptance_number):
    car = CarEntry.objects.filter(acceptance_number=acceptance_number).first()
    if car:
        return JsonResponse({
            'has_parts': bool(car.parts),
            'has_costs': bool(car.costs),
            'has_document': bool(car.document)
        })
    return JsonResponse({'error': 'Car not found'}, status=404)

@login_required
def finalize_registration(request, acceptance_number):
    car = get_object_or_404(CarEntry, acceptance_number=acceptance_number)

    # اگه قبلاً ثبت نهایی شده، نذار دوباره انجام بشه
    if hasattr(car, 'final_registration'):
        messages.error(request, 'این خودرو قبلاً ثبت نهایی شده است.')
        return redirect('registration_list')

    if request.method == 'POST':
        form = FinalRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            final_reg = form.save(commit=False)
            final_reg.car = car
            final_reg.finalized_by = request.user
            final_reg.save()
            messages.success(request, f'خودرو {car.acceptance_number} با موفقیت ثبت نهایی شد.')
            return redirect('registration_list')
    else:
        form = FinalRegistrationForm()

    return render(request, 'core/finalize_registration.html', {
        'form': form,
        'car': car,
    })

@login_required
def finalized_list(request):
    cars = CarEntry.objects.filter(final_registration__isnull=False).order_by('-final_registration__finalized_at')
    # کپی کد registration_list برای فیلتر و صفحه‌بندی
    query = request.GET.get('q', '').strip()
    if query:
        cars = cars.filter(
            Q(acceptance_number__icontains=query) |
            Q(license_plate__icontains=query) |
            Q(car_type__icontains=query) |
            Q(owner_name__icontains=query)
        )

    paginator = Paginator(cars, 10)
    page_number = request.GET.get('page')
    try:
        page_cars = paginator.page(page_number)
    except PageNotAnInteger:
        page_cars = paginator.page(1)
    except EmptyPage:
        page_cars = paginator.page(paginator.num_pages)

    return render(request, 'core/finalized_list.html', {
        'cars': page_cars,
    })


@login_required
def connect_car_document(request):
    if request.method == 'POST':
        engine_number = request.POST.get('engine_number')
        try:
            car = CarEntry.objects.get(engine_number=engine_number)
            doc = Document.objects.get(engine_number=engine_number)
            if car.document or doc.car:
                messages.error(request, 'این خودرو یا سند قبلاً به هم متصل شده‌اند.')
            else:
                car.document = doc
                car.save()
                messages.success(request,
                                 f'خودرو {car.acceptance_number} با سند {doc.engine_number} با موفقیت متصل شد.')
                return redirect('home')  # یا هر URL دیگه‌ای که بخواید
        except CarEntry.DoesNotExist:
            messages.error(request, f'خودرویی با شماره موتور {engine_number} پیدا نشد.')
        except Document.DoesNotExist:
            messages.error(request, f'سندی با شماره موتور {engine_number} پیدا نشد.')
        except Exception as e:
            messages.error(request, f'خطایی رخ داد: {str(e)}')

    return render(request, 'core/connect_car_document.html', {})