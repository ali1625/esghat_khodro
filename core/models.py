from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from jdatetime import datetime as jdatetime

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="کاربر")
    first_name = models.CharField(max_length=50, verbose_name="نام")
    last_name = models.CharField(max_length=50, verbose_name="نام خانوادگی")
    national_code = models.CharField(max_length=10, unique=True, verbose_name="کد ملی")  # بدون default
    phone_number = models.CharField(max_length=11, verbose_name="شماره موبایل", default="09120000000")
    must_change_password = models.BooleanField(default=True, verbose_name="باید رمز را تغییر دهد")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "پروفایل‌های کاربران"
class CarEntry(models.Model):
    parking_number = models.CharField(max_length=20, verbose_name="شماره پارکینگ")
    delivery_date = models.CharField(max_length=10, verbose_name="تاریخ تحویل")
    car_type = models.CharField(max_length=50, verbose_name="نوع خودرو")
    license_plate = models.CharField(max_length=30, verbose_name="شماره انتظامی")
    owner_name = models.CharField(max_length=100, verbose_name="نام مالک")
    engine_number = models.CharField(max_length=50, unique=True, verbose_name="شماره موتور")
    chassis_number = models.CharField(max_length=50, unique=True, verbose_name="شماره شاسی")
    has_cabin_plate = models.BooleanField(default=False, verbose_name="پلاک اتاق")
    acceptance_number = models.CharField(max_length=9, unique=True, editable=False, verbose_name="شماره پذیرش")
    accepted_by = models.CharField(max_length=100, verbose_name="مسئول پذیرش")  # نام و نام خانوادگی
    accepted_at = models.CharField(max_length=10, verbose_name="تاریخ پذیرش")
    edited_by = models.CharField(max_length=100, null=True, blank=True, verbose_name="ویرایش‌کننده")  # نام و نام خانوادگی
    driver_name = models.CharField(max_length=100, verbose_name="نام و نام خانوادگی راننده/آورنده")
    driver_license_plate = models.CharField(max_length=30, verbose_name="شماره پلاک راننده/آورنده")
    driver_phone = models.CharField(max_length=15, verbose_name="شماره تماس راننده/آورنده")

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # گرفتن کاربر از kwargs
        if not self.acceptance_number and self.delivery_date:
            year_month = jdatetime.strptime(self.delivery_date, '%Y/%m/%d').strftime('%Y%m')  # مثلاً 140312 از 1403/12/15
            last_entry = CarEntry.objects.filter(acceptance_number__startswith=year_month).order_by('-acceptance_number').first()
            if last_entry:
                last_num = int(last_entry.acceptance_number[-3:])
                new_num = last_num + 1
            else:
                new_num = 1
            self.acceptance_number = f"{year_month}{new_num:03d}"  # مثلاً 140312001

        if not self.accepted_at:
            self.accepted_at = jdatetime.now().strftime('%Y/%m/%d')

        if user:
            full_name = f"{user.userprofile.first_name} {user.userprofile.last_name}" if hasattr(user, 'userprofile') else user.username
            if not self.accepted_by:  # فقط موقع ثبت اولیه
                self.accepted_by = full_name
            if self.pk:  # اگه ویرایش باشه
                self.edited_by = full_name

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.car_type} - {self.acceptance_number}"

class CarParts(models.Model):
    car = models.OneToOneField(CarEntry, on_delete=models.CASCADE, to_field='acceptance_number', verbose_name="خودرو", related_name="parts")
    cabin_percentage = models.IntegerField(verbose_name="درصد اتاق", default=100)
    hood = models.BooleanField(default=False, verbose_name="درب موتور")
    radiator = models.BooleanField(default=False, verbose_name="رادیاتور")
    ecu = models.BooleanField(default=False, verbose_name="ایسیو")
    front_rear_doors = models.BooleanField(default=False, verbose_name="درب جلو و عقب")
    wiring = models.BooleanField(default=False, verbose_name="سیم‌کشی")
    battery_cable = models.BooleanField(default=False, verbose_name="کابل باطری")
    heater = models.BooleanField(default=False, verbose_name="بخاری")
    suspension_spring = models.BooleanField(default=False, verbose_name="فنر زیر و بند")
    alternator = models.BooleanField(default=False, verbose_name="دینام")
    wiper_motor = models.BooleanField(default=False, verbose_name="موتور برف‌پاک‌کن")
    rims_tires = models.BooleanField(default=False, verbose_name="رینگ و لاستیک")
    carburetor = models.BooleanField(default=False, verbose_name="کاربراتور")
    starter = models.BooleanField(default=False, verbose_name="استارت")
    gearbox = models.BooleanField(default=False, verbose_name="گیربکس")
    differential = models.BooleanField(default=False, verbose_name="دیفرانسیل")
    distributor_coil = models.BooleanField(default=False, verbose_name="دلکو و کوئل")
    fuel_pump = models.BooleanField(default=False, verbose_name="سیفون بنزین")
    seats = models.BooleanField(default=False, verbose_name="صندلی")
    front_disc = models.BooleanField(default=False, verbose_name="دیسک چرخ جلو")
    battery = models.BooleanField(default=False, verbose_name="باطری")
    steering_box = models.BooleanField(default=False, verbose_name="جعبه فرمان")
    bumpers = models.BooleanField(default=False, verbose_name="سپر عقب و جلو")
    wheel_drum = models.BooleanField(default=False, verbose_name="کاسه چرخ")
    driveshaft_cv = models.BooleanField(default=False, verbose_name="پلوس و گاردان")
    fuel_rail = models.BooleanField(default=False, verbose_name="ریل سوخت")
    trunk_lid = models.BooleanField(default=False, verbose_name="درب صندوق")
    documents = models.BooleanField(default=False, verbose_name="سند")
    injector = models.BooleanField(default=False, verbose_name="انژکتور و سوزن انژکتور")
    glass = models.BooleanField(default=False, verbose_name="شیشه")
    ac = models.BooleanField(default=False, verbose_name="کولر")
    gas_cylinder = models.CharField(max_length=10, choices=[('LNG', 'LNG'), ('CNG', 'CNG'), ('None', 'ندارد')], default='None', verbose_name="کپسول")
    brake_booster = models.BooleanField(default=False, verbose_name="پوستر ترمز")
    weight = models.FloatField(verbose_name="وزن", null=True, blank=True)
    plate_status = models.CharField(max_length=20, choices=[('Single', 'تک پلاک'), ('Double', 'جفت پلاک'), ('None', 'فاقد پلاک')], default='None', verbose_name="وضعیت پلاک")
    plate_description = models.TextField(verbose_name="توضیحات پلاک", blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="مسئول ثبت قطعات", related_name="car_parts")
    recorded_at = models.CharField(max_length=10, verbose_name="تاریخ ثبت قطعات", null=True, blank=True)  # به شمسی

    def save(self, *args, **kwargs):
        if not self.recorded_at:
            self.recorded_at = jdatetime.now().strftime('%Y/%m/%d')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"قطعات {self.car}"

class CarCosts(models.Model):
    car = models.OneToOneField(CarEntry, on_delete=models.CASCADE, to_field='acceptance_number', verbose_name="خودرو", related_name="costs")
    daily_price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="قیمت روز")
    fine = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="خلافی")
    fine_document = models.FileField(upload_to='documents/fines/', null=True, blank=True, verbose_name="سند خلافی")
    court_cost = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="هزینه دادگاهی")
    court_document = models.FileField(upload_to='documents/court/', null=True, blank=True, verbose_name="سند دادگاهی")
    transport_cost = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="هزینه حمل")
    transport_document = models.FileField(upload_to='documents/transport/', null=True, blank=True, verbose_name="سند حمل")
    proxy_cost = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="هزینه وکالت")
    proxy_document = models.FileField(upload_to='documents/proxy/', null=True, blank=True, verbose_name="سند وکالت")
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, editable=False, verbose_name="جمع کل")
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="مسئول ثبت هزینه‌ها", related_name="car_costs")
    recorded_at = models.CharField(max_length=10, verbose_name="تاریخ ثبت هزینه‌ها", null=True, blank=True)  # به شمسی

    def save(self, *args, **kwargs):
        self.total_cost = self.daily_price + self.fine + self.court_cost + self.transport_cost + self.proxy_cost
        if not self.recorded_at:
            self.recorded_at = jdatetime.now().strftime('%Y/%m/%d')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"هزینه‌های {self.car}"


class EditLog(models.Model):
    EDIT_TYPES = (
        ('CAR_ENTRY', 'ویرایش ورود خودرو'),
        ('CAR_PARTS', 'ویرایش قطعات خودرو'),
        ('CAR_COSTS', 'ویرایش هزینه‌ها'),
    )

    edit_type = models.CharField(max_length=20, choices=EDIT_TYPES, verbose_name="نوع ویرایش")
    car_entry = models.ForeignKey('CarEntry', on_delete=models.CASCADE, verbose_name="خودرو", related_name="edit_logs")
    edited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="ویرایش‌کننده",
                                  related_name="edit_logs")
    edited_at = models.CharField(max_length=10, verbose_name="تاریخ ویرایش")  # تاریخ شمسی

    def save(self, *args, **kwargs):
        if not self.edited_at:
            self.edited_at = jdatetime.now().strftime('%Y/%m/%d')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_edit_type_display()} - {self.car_entry.acceptance_number} - {self.edited_at}"

    class Meta:
        verbose_name = "لاگ ویرایش"
        verbose_name_plural = "لاگ‌های ویرایش"