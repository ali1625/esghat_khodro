from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from jdatetime import datetime as jdatetime
from django.contrib import messages
from django.db.models import Q
from django.db import models
from .models import CarEntry, CarParts, EditLog, UserProfile
from .forms import CarEntryForm, CarPartsForm, CarCostsForm, CustomUserCreationForm, SearchLogForm
from .forms import AdminChangePasswordForm, UserProfileForm
from django.contrib.auth import update_session_auth_hash
from .forms import AdminChangePasswordForm, UserProfileForm, AdminUserCreationForm, CustomPasswordChangeForm
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
    if request.user.is_authenticated:
        recent_cars = CarEntry.objects.order_by('-accepted_at')[:5]
        return render(request, 'core/home.html', {'recent_cars': recent_cars})
    return redirect('login')

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)  # نگه داشتن کاربر لاگین شده
            messages.success(request, 'رمز عبور شما با موفقیت تغییر کرد.')
            return redirect('change_password')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'core/change_password.html', {'form': form})

# تابع برای چک کردن مدیر بودن
def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def user_management(request):
    users = User.objects.all().order_by('-date_joined')
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        user = get_object_or_404(User, id=user_id)
        if action == 'delete':
            user.delete()
            messages.success(request, 'کاربر با موفقیت حذف شد.')
        elif action == 'toggle_active':
            user.is_active = not user.is_active
            user.save()
            status = 'فعال' if user.is_active else 'غیرفعال'
            messages.success(request, f'کاربر با موفقیت {status} شد.')
        return redirect('user_management')
    return render(request, 'core/user_management.html', {'users': users})

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
    profile, created = UserProfile.objects.get_or_create(user=user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f'پروفایل کاربر {user.username} با موفقیت به‌روزرسانی شد.')
            return redirect('user_management')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
    else:
        form = UserProfileForm(instance=profile)
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
def change_password(request):
    if not hasattr(request.user, 'userprofile') or not request.user.userprofile.must_change_password:
        return redirect('home')  # اگه نیازی به تغییر رمز نباشه
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['new_password'])
            request.user.userprofile.must_change_password = False
            request.user.userprofile.save()
            request.user.save()
            update_session_auth_hash(request, request.user)  # نگه داشتن سشن
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

@login_required
def add_car_entry_step1(request):
    if request.method == 'POST':
        form = CarEntryForm(request.POST)
        if form.is_valid():
            car_entry = form.save(commit=False)
            # ذخیره با کاربر لاگین‌شده
            car_entry.save(user=request.user)
            # ساخت پیام سفارشی با accepted_by و acceptance_number
            success_message = f" خودرو با شماره پذیرش {car_entry.acceptance_number} توسط {car_entry.accepted_by} با موفقیت ثبت شد "
            messages.success(request, success_message)
            return redirect('home')
        else:
            print("Form errors:", form.errors)
    else:
        form = CarEntryForm()
    return render(request, 'core/add_car_entry_step1.html', {'form': form})
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
            car_parts.recorded_at = jdatetime.now().strftime('%Y/%m/%d')  # اینجا از jdatetime استفاده می‌شه
            try:
                car_parts.save()
                messages.success(request, 'قطعات خودرو با موفقیت ثبت شد.')
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
            car_costs.recorded_at = jdatetime.now().strftime('%Y/%m/%d')
            try:
                car_costs.save()  # total_cost توی مدل محاسبه می‌شه
                messages.success(request, 'هزینه‌های خودرو با موفقیت ثبت شد.')
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
def edit_car_entry(request, acceptance_number):
    car = get_object_or_404(CarEntry, acceptance_number=acceptance_number)
    if request.method == 'POST':
        form = CarEntryForm(request.POST, instance=car)
        if form.is_valid():
            car_instance = form.save(commit=False)
            car_instance.save(user=request.user)
            #ثبت لاگ
            EditLog.objects.create(
                edit_type='CAR_ENTRY',
                car_entry=car_instance,
                edited_by=request.user
            )
            #پیغام
            messages.success(request, f"اطلاعات خودرو با موفقیت توسط {car_instance.edited_by} ویرایش شد.")
            return redirect('registration_list')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
            print("Form errors:", form.errors)
    else:
        initial_data = {}
        # جدا کردن پلاک خودرو
        if car.license_plate:
            try:
                parts = car.license_plate.split(' - ')
                if len(parts) == 4:
                    initial_data['digits1'] = parts[0]
                    initial_data['persian_letter'] = parts[1]
                    initial_data['digits2'] = parts[2]
                    initial_data['digits3'] = parts[3].replace('ایران ', '')
                else:
                    print(f"Invalid license_plate format: {car.license_plate}")
            except Exception as e:
                print(f"Error parsing license_plate: {e}")
        # جدا کردن پلاک راننده
        if car.driver_license_plate:
            try:
                parts = car.driver_license_plate.split(' - ')
                if len(parts) == 4:
                    initial_data['driver_digits1'] = parts[0]
                    initial_data['driver_persian_letter'] = parts[1]
                    initial_data['driver_digits2'] = parts[2]
                    initial_data['driver_digits3'] = parts[3].replace('ایران ', '')
                else:
                    print(f"Invalid driver_license_plate format: {car.driver_license_plate}")
            except Exception as e:
                print(f"Error parsing driver_license_plate: {e}")
        form = CarEntryForm(instance=car, initial=initial_data)
    return render(request, 'core/edit_car_entry.html', {'form': form, 'car': car})
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
            #پیغام
            messages.success(request, 'قطعات خودرو با موفقیت ویرایش شد.')
            return redirect('registration_list')
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

        # ثبت فونت فارسی (فونت رو باید توی پروژه داشته باشی)
        pdfmetrics.registerFont(TTFont('PersianFont', 'static/fonts/Vazirmatn-Black.ttf'))  # مسیر فونت رو درست کن
        p.setFont('PersianFont', 12)

        # عنوان
        p.setFont('PersianFont', 16)
        p.drawCentredString(A4[0]/2, A4[1]-50, f"جزئیات خودرو: {car.acceptance_number}")

        # اطلاعات خودرو
        y = A4[1] - 100
        p.setFont('PersianFont', 12)
        details = [
            f"شماره پارکینگ: {car.parking_number or ''}",
            f"تاریخ تحویل: {car.delivery_date or ''}",
            f"نوع خودرو: {car.car_type or ''}",
            f"شماره انتظامی: {car.license_plate or ''}",
            f"نام مالک: {car.owner_name or ''}",
            f"شماره موتور: {car.engine_number or ''}",
            f"شماره شاسی: {car.chassis_number or ''}",
            f"پلاکت اتاق: {'دارد' if car.has_cabin_plate else 'ندارد'}",
            f"شماره ثبت: {car.registration_number or ''}",
            f"مسئول پذیرش: {car.accepted_by.username if car.accepted_by else ''}",
            f"تاریخ پذیرش: {car.accepted_at or ''}",
            f"نام راننده: {car.driver_name or ''}",
            f"شماره پلاک راننده: {car.driver_license_plate or ''}",
            f"شماره تماس راننده: {car.driver_phone or ''}",
        ]
        for line in details:
            p.drawRightString(A4[0]-50, y, line)
            y -= 20

        # قطعات
        y -= 20
        p.setFont('PersianFont', 14)
        p.drawRightString(A4[0]-50, y, "قطعات")
        y -= 20
        p.setFont('PersianFont', 12)
        if hasattr(car, 'parts') and car.parts:
            parts_details = [
                f"درصد اتاق: {car.parts.cabin_percentage or ''}",
                f"درب موتور: {'دارد' if car.parts.hood else 'ندارد'}",
               
                f"توضیحات پلاک: {car.parts.plate_description or ''}",
                f"مسئول ثبت: {car.parts.recorded_by.username if car.parts.recorded_by else ''}",
                f"تاریخ ثبت: {car.parts.recorded_at or ''}",
            ]
            for line in parts_details:
                p.drawRightString(A4[0]-50, y, line)
                y -= 20
        else:
            p.drawRightString(A4[0]-50, y, "قطعات هنوز ثبت نشده است.")
            y -= 20

        # هزینه‌ها
        y -= 20
        p.setFont('PersianFont', 14)
        p.drawRightString(A4[0]-50, y, "هزینه‌ها")
        y -= 20
        p.setFont('PersianFont', 12)
        if hasattr(car, 'costs') and car.costs:
            costs_details = [
                f"قیمت روز: {car.costs.daily_price or ''}",
                f"خلافی: {car.costs.fine or ''}",
                f"سند خلافی: {car.costs.fine_document.name if car.costs.fine_document else ''}",
                f"هزینه دادگاهی: {car.costs.court_cost or ''}",
                f"سند دادگاهی: {car.costs.court_document.name if car.costs.court_document else ''}",
                f"هزینه حمل: {car.costs.transport_cost or ''}",
                f"سند حمل: {car.costs.transport_document.name if car.costs.transport_document else ''}",
                f"هزینه وکالت: {car.costs.proxy_cost or ''}",
                f"سند وکالت: {car.costs.proxy_document.name if car.costs.proxy_document else ''}",
                f"جمع کل: {car.costs.total_cost or ''}",
                f"مسئول ثبت: {car.costs.recorded_by.username if car.costs.recorded_by else ''}",
                f"تاریخ ثبت: {car.costs.recorded_at or ''}",
            ]
            for line in costs_details:
                p.drawRightString(A4[0]-50, y, line)
                y -= 20
        else:
            p.drawRightString(A4[0]-50, y, "هزینه‌ها هنوز ثبت نشده است.")

        # پایان PDF
        p.showPage()
        p.save()
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response

    return render(request, 'core/car_details.html', {'car': car})




@login_required
def registration_list(request):
    cars = CarEntry.objects.all().order_by('-accepted_at')  # مرتب‌سازی نزولی

    # گرفتن مقادیر از درخواست
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
            start_jdate = jdatetime.strptime(start_date, '%Y/%m/%d')
            end_jdate = jdatetime.strptime(end_date, '%Y/%m/%d')
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
            start_date_gregorian = jdatetime.strptime(start_date, '%Y/%m/%d').togregorian()
            cars = cars.filter(accepted_at__gte=start_date_gregorian)

        if end_date:
            end_date_gregorian = jdatetime.strptime(end_date, '%Y/%m/%d').togregorian()
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