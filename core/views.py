from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from jdatetime import datetime as jdatetime
from django.contrib import messages
from django.db.models import Q
from .models import CarEntry
from .forms import CarEntryForm, CarPartsForm, CarCostsForm, CustomUserCreationForm
from django.http import HttpResponse
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from django.db import IntegrityError
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO


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
    users = User.objects.all()
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        user = User.objects.get(id=user_id)
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
            car_entry.save(user=request.user)
            messages.success(request, 'خودرو با موفقیت ثبت شد.')
            return redirect('registration_list')
        else:
            print("Form errors:", form.errors)
    else:
        form = CarEntryForm()
    return render(request, 'core/add_car_entry_step1.html', {'form': form})

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
            messages.success(request, 'اطلاعات خودرو با موفقیت ویرایش شد.')
            return redirect('registration_list')
        else:
            messages.error(request, 'لطفاً خطاها را برطرف کنید.')
            print("Form errors:", form.errors)
    else:
        # پر کردن مقادیر اولیه برای پلاک‌ها
        initial_data = {}
        if car.license_plate:
            try:
                parts = car.license_plate.split(' - ')
                if len(parts) == 4:
                    initial_data['digits1'] = parts[0].split(' ')[0]  # مثلاً 12
                    initial_data['digits2'] = parts[1]  # مثلاً 123
                    initial_data['persian_letter'] = parts[2]  # مثلاً الف
                    initial_data['digits3'] = parts[3]  # مثلاً 45
            except Exception as e:
                print(f"Error parsing license_plate: {e}")
        if car.driver_license_plate:
            try:
                parts = car.driver_license_plate.split(' - ')
                if len(parts) == 4:
                    initial_data['driver_digits1'] = parts[0].split(' ')[0]
                    initial_data['driver_digits2'] = parts[1]
                    initial_data['driver_persian_letter'] = parts[2]
                    initial_data['driver_digits3'] = parts[3]
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
    # گرفتن پارامترهای جستجو از GET
    acceptance_number = request.GET.get('acceptance_number', '').strip()
    license_plate = request.GET.get('license_plate', '').strip()
    parking_number = request.GET.get('parking_number', '').strip()
    has_parts = request.GET.get('has_parts', '')
    has_costs = request.GET.get('has_costs', '')
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    # مرتب‌سازی نزولی بر اساس id
    cars = CarEntry.objects.all().order_by('-id')
    print(f"Initial cars: {cars.count()}")

    # اعمال فیلترهای جستجو فقط اگه مقدار غیرخالی باشه
    if acceptance_number:
        cars = cars.filter(acceptance_number__icontains=acceptance_number)
    if license_plate:
        cars = cars.filter(license_plate__icontains=license_plate)
    if parking_number:
        cars = cars.filter(parking_number__icontains=parking_number)
    if has_parts == 'yes':
        cars = cars.filter(parts__isnull=False)
    elif has_parts == 'no':
        cars = cars.filter(parts__isnull=True)
    if has_costs == 'yes':
        cars = cars.filter(costs__isnull=False)
    elif has_costs == 'no':
        cars = cars.filter(costs__isnull=True)
    if start_date:
        try:
            jdatetime.strptime(start_date, '%Y/%m/%d')  # اعتبارسنجی فرمت
            cars = cars.filter(accepted_at__gte=start_date)
        except ValueError:
            messages.error(request, "فرمت تاریخ شروع اشتباه است (مثال: 1403/12/15)")
    if end_date:
        try:
            jdatetime.strptime(end_date, '%Y/%m/%d')  # اعتبارسنجی فرمت
            cars = cars.filter(accepted_at__lte=end_date)
        except ValueError:
            messages.error(request, "فرمت تاریخ پایان اشتباه است (مثال: 1403/12/15)")

    print(f"Filtered cars: {cars.count()}")

    # خروجی اکسل (بدون تغییر)
    if 'export' in request.GET:
        wb = Workbook()
        ws = wb.active
        ws.title = "لیست ثبت"
        headers = [
            'شماره پذیرش', 'شماره پارکینگ', 'تاریخ تحویل', 'نوع خودرو', 'شماره انتظامی',
            'نام مالک', 'شماره موتور', 'شماره شاسی', 'پلاک اتاق',
            'مسئول پذیرش', 'تاریخ پذیرش', 'نام راننده', 'شماره پلاک راننده', 'شماره تماس راننده',
            'درصد اتاق', 'درب موتور', 'رادیاتور', 'ایسیو', 'درب جلو و عقب', 'سیم‌کشی',
            'کابل باطری', 'بخاری', 'فنر زیر و بند', 'دینام', 'موتور برف‌پاک‌کن', 'رینگ و لاستیک',
            'کاربراتور', 'استارت', 'گیربکس', 'دیفرانسیل', 'دلکو و کوئل', 'سیفون بنزین', 'صندلی',
            'دیسک چرخ جلو', 'باطری', 'جعبه فرمان', 'سپر عقب و جلو', 'کاسه چرخ', 'پلوس و گاردان',
            'ریل سوخت', 'درب صندوق', 'سند', 'انژکتور و سوزن انژکتور', 'شیشه', 'کولر', 'کپسول',
            'پوستر ترمز', 'وزن', 'وضعیت پلاک', 'توضیحات پلاک', 'مسئول قطعات', 'تاریخ ثبت قطعات',
            'قیمت روز', 'خلافی', 'سند خلافی', 'هزینه دادگاهی', 'سند دادگاهی', 'هزینه حمل',
            'سند حمل', 'هزینه وکالت', 'سند وکالت', 'جمع کل', 'مسئول هزینه‌ها', 'تاریخ ثبت هزینه‌ها'
        ]
        ws.append(headers)

        for car in cars:
            accepted_by = car.accepted_by or ''
            parts_recorded_by = cabin_percentage = hood = radiator = ecu = front_rear_doors = wiring = ''
            battery_cable = heater = suspension_spring = alternator = wiper_motor = rims_tires = ''
            carburetor = starter = gearbox = differential = distributor_coil = fuel_pump = seats = ''
            front_disc = battery = steering_box = bumpers = wheel_drum = driveshaft_cv = fuel_rail = ''
            trunk_lid = documents = injector = glass = ac = gas_cylinder = brake_booster = ''
            weight = plate_status = plate_description = parts_recorded_at = ''
            if hasattr(car, 'parts') and car.parts:
                parts_recorded_by = car.parts.recorded_by or ''
                cabin_percentage = car.parts.cabin_percentage or ''
                hood = 'دارد' if car.parts.hood else 'ندارد'
                radiator = 'دارد' if car.parts.radiator else 'ندارد'
                ecu = 'دارد' if car.parts.ecu else 'ندارد'
                front_rear_doors = 'دارد' if car.parts.front_rear_doors else 'ندارد'
                wiring = 'دارد' if car.parts.wiring else 'ندارد'
                battery_cable = 'دارد' if car.parts.battery_cable else 'ندارد'
                heater = 'دارد' if car.parts.heater else 'ندارد'
                suspension_spring = 'دارد' if car.parts.suspension_spring else 'ندارد'
                alternator = 'دارد' if car.parts.alternator else 'ندارد'
                wiper_motor = 'دارد' if car.parts.wiper_motor else 'ندارد'
                rims_tires = 'دارد' if car.parts.rims_tires else 'ندارد'
                carburetor = 'دارد' if car.parts.carburetor else 'ندارد'
                starter = 'دارد' if car.parts.starter else 'ندارد'
                gearbox = 'دارد' if car.parts.gearbox else 'ندارد'
                differential = 'دارد' if car.parts.differential else 'ندارد'
                distributor_coil = 'دارد' if car.parts.distributor_coil else 'ندارد'
                fuel_pump = 'دارد' if car.parts.fuel_pump else 'ندارد'
                seats = 'دارد' if car.parts.seats else 'ندارد'
                front_disc = 'دارد' if car.parts.front_disc else 'ندارد'
                battery = 'دارد' if car.parts.battery else 'ندارد'
                steering_box = 'دارد' if car.parts.steering_box else 'ندارد'
                bumpers = 'دارد' if car.parts.bumpers else 'ندارد'
                wheel_drum = 'دارد' if car.parts.wheel_drum else 'ندارد'
                driveshaft_cv = 'دارد' if car.parts.driveshaft_cv else 'ندارد'
                fuel_rail = 'دارد' if car.parts.fuel_rail else 'ندارد'
                trunk_lid = 'دارد' if car.parts.trunk_lid else 'ندارد'
                documents = 'دارد' if car.parts.documents else 'ندارد'
                injector = 'دارد' if car.parts.injector else 'ندارد'
                glass = 'دارد' if car.parts.glass else 'ندارد'
                ac = 'دارد' if car.parts.ac else 'ندارد'
                gas_cylinder = car.parts.gas_cylinder or ''
                brake_booster = 'دارد' if car.parts.brake_booster else 'ندارد'
                weight = car.parts.weight or ''
                plate_status = car.parts.plate_status or ''
                plate_description = car.parts.plate_description or ''
                parts_recorded_at = str(car.parts.recorded_at) if car.parts.recorded_at else ''

            costs_recorded_by = daily_price = fine = fine_document = court_cost = court_document = ''
            transport_cost = transport_document = proxy_cost = proxy_document = total_cost = costs_recorded_at = ''
            if hasattr(car, 'costs') and car.costs:
                costs_recorded_by = car.costs.recorded_by or ''
                daily_price = car.costs.daily_price or ''
                fine = car.costs.fine or ''
                fine_document = car.costs.fine_document.name if car.costs.fine_document else ''
                court_cost = car.costs.court_cost or ''
                court_document = car.costs.court_document.name if car.costs.court_document else ''
                transport_cost = car.costs.transport_cost or ''
                transport_document = car.costs.transport_document.name if car.costs.transport_document else ''
                proxy_cost = car.costs.proxy_cost or ''
                proxy_document = car.costs.proxy_document.name if car.costs.proxy_document else ''
                total_cost = car.costs.total_cost or ''
                costs_recorded_at = str(car.costs.recorded_at) if car.costs.recorded_at else ''

            row = [
                car.acceptance_number, car.parking_number, str(car.delivery_date), car.car_type, car.license_plate,
                car.owner_name, car.engine_number, car.chassis_number, 'دارد' if car.has_cabin_plate else 'ندارد',
                accepted_by, str(car.accepted_at), car.driver_name, car.driver_license_plate, car.driver_phone,
                cabin_percentage, hood, radiator, ecu, front_rear_doors, wiring, battery_cable, heater,
                suspension_spring, alternator, wiper_motor, rims_tires, carburetor, starter, gearbox,
                differential, distributor_coil, fuel_pump, seats, front_disc, battery, steering_box,
                bumpers, wheel_drum, driveshaft_cv, fuel_rail, trunk_lid, documents, injector, glass,
                ac, gas_cylinder, brake_booster, weight, plate_status, plate_description,
                parts_recorded_by, parts_recorded_at,
                daily_price, fine, fine_document, court_cost, court_document, transport_cost,
                transport_document, proxy_cost, proxy_document, total_cost, costs_recorded_by, costs_recorded_at
            ]
            ws.append(row)
            print(f"Added row: {row}")

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="registration_list.xlsx"'
        wb.save(response)
        return response

    context = {
        'cars': cars,
        'acceptance_number': acceptance_number,
        'license_plate': license_plate,
        'parking_number': parking_number,
        'has_parts': has_parts,
        'has_costs': has_costs,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'core/registration_list.html', context)