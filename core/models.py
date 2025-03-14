from django.db import models, IntegrityError, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.models import User
from jdatetime import datetime as jdatetime_datetime
from decimal import Decimal


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'ادمین'),
        ('regular', 'کاربر معمولی'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    national_code = models.CharField(max_length=10, blank=True, null=True)
    phone_number = models.CharField(max_length=11, blank=True, null=True)
    must_change_password = models.BooleanField(default=True, verbose_name="باید رمز را تغییر دهد")
    role = models.CharField(max_length=20,choices=ROLE_CHOICES,default='regular')

    def __str__(self):
        return f"{self.user.username} - {self.role}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'userprofile'):
        # فقط اگه پروفایل از قبل وجود نداشته باشه، بساز
        role = 'admin' if instance.is_superuser else 'regular'
        UserProfile.objects.create(user=instance, role=role)




class Document(models.Model):
    engine_number = models.CharField(max_length=50, unique=True, verbose_name="شماره موتور")
    chassis_number = models.CharField(max_length=50, unique=True, verbose_name="شماره شاسی")
    file1 = models.FileField(upload_to='documents/', verbose_name="فایل ۱", blank=True, null=True)
    file2 = models.FileField(upload_to='documents/', verbose_name="فایل ۲", blank=True, null=True)
    file3 = models.FileField(upload_to='documents/', verbose_name="فایل ۳", blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, verbose_name="ایجاد شده توسط")
    created_at = models.CharField(max_length=10, verbose_name="تاریخ ایجاد", blank=True)  # تاریخ شمسی
    created_at_gregorian = models.DateField(verbose_name="تاریخ ایجاد (میلادی)", blank=True, null=True)  # تاریخ میلادی مخفی
    car = models.ForeignKey('CarEntry', on_delete=models.SET_NULL, null=True, blank=True, related_name='documents', verbose_name="خودرو مرتبط")

    def __str__(self):
        return f"سند {self.engine_number} - {self.chassis_number}"

    @property
    def combined_key(self):
        return f"{self.engine_number}-{self.chassis_number}"

    def save(self, *args, **kwargs):
        # تنظیم تاریخ شمسی و میلادی
        if not self.created_at:
            self.created_at = jdatetime_datetime.now().strftime('%Y/%m/%d')
        if not self.created_at_gregorian and self.created_at:
            jalali_date = jdatetime_datetime.strptime(self.created_at, '%Y/%m/%d')
            self.created_at_gregorian = jalali_date.togregorian().date()

        # اگر خودرو متصل است و ناهماهنگی وجود دارد، ارتباط را قطع می‌کنیم
        if self.car and (
            self.engine_number != self.car.engine_number or
            self.chassis_number != self.car.chassis_number
        ):
            self.car.document = None
            self.car.save(update_fields=['document'])
            self.car = None

        super().save(*args, **kwargs)
class CarEntry(models.Model):
    parking_number = models.CharField(max_length=20, verbose_name="شماره پارکینگ", blank=True, null=True)
    delivery_date = models.CharField(max_length=10, verbose_name="تاریخ تحویل", blank=True, null=True)
    car_type = models.CharField(max_length=50, verbose_name="نوع خودرو", blank=True, null=True)
    license_plate = models.CharField(max_length=30, verbose_name="شماره انتظامی", blank=True, null=True)
    owner_name = models.CharField(max_length=100, verbose_name="نام مالک", blank=True, null=True)
    engine_number = models.CharField(max_length=50, unique=True, verbose_name="شماره موتور", blank=True, null=True)
    chassis_number = models.CharField(max_length=50, unique=True, verbose_name="شماره شاسی", blank=True, null=True)
    has_cabin_plate = models.BooleanField(default=False, verbose_name="پلاکت اتاق", blank=True, null=True)
    acceptance_number = models.CharField(max_length=13, unique=True, editable=False, verbose_name="شماره پذیرش")
    accepted_by = models.CharField(max_length=100, verbose_name="مسئول پذیرش")
    accepted_at = models.CharField(max_length=10, verbose_name="تاریخ پذیرش")
    edited_by = models.CharField(max_length=100, null=True, blank=True, verbose_name="ویرایش‌کننده")
    driver_name = models.CharField(max_length=100, verbose_name="نام و نام خانوادگی راننده/آورنده", blank=True, null=True)
    driver_license_plate = models.CharField(max_length=30, verbose_name="شماره پلاک راننده/آورنده", blank=True, null=True)
    driver_phone = models.CharField(max_length=15, verbose_name="شماره تماس راننده/آورنده", blank=True, null=True)
    front_image = models.FileField(upload_to='car_images/front/', verbose_name="عکس جلوی خودرو")
    rear_image = models.FileField(upload_to='car_images/rear/', verbose_name="عکس عقب خودرو")
    chassis_image = models.FileField(upload_to='car_images/chassis/', verbose_name="عکس شماره شاسی", blank=True, null=True)
    engine_image = models.FileField(upload_to='car_images/engine/', verbose_name="عکس شماره موتور", blank=True, null=True)
    document = models.ForeignKey('Document', on_delete=models.SET_NULL, null=True, blank=True, related_name='car_entries', verbose_name="سند مرتبط")

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)

        if not self.acceptance_number and self.delivery_date:
            self.acceptance_number = self._generate_unique_acceptance_number()

        if not self.accepted_at:
            self.accepted_at = jdatetime_datetime.now().strftime('%Y/%m/%d')

        if user:
            full_name = f"{user.userprofile.first_name} {user.userprofile.last_name}" if hasattr(user, 'userprofile') else user.username
            if not self.accepted_by:
                self.accepted_by = full_name
            if self.pk:
                self.edited_by = full_name

        # اگر سند وجود دارد و ناهماهنگی پیدا شد، ارتباط را قطع می‌کنیم
        if self.document and (
            self.engine_number != self.document.engine_number or
            self.chassis_number != self.document.chassis_number
        ):
            self.document.car = None
            self.document.save(update_fields=['car'])  # قطع ارتباط از سمت سند
            self.document = None  # قطع ارتباط از سمت خودرو

        super().save(*args, **kwargs)

    def _generate_unique_acceptance_number(self):
        delivery_date = jdatetime_datetime.strptime(self.delivery_date, '%Y/%m/%d')
        date_part = delivery_date.strftime('%Y%d')
        while True:
            last_entry = CarEntry.objects.filter(acceptance_number__startswith=date_part).order_by('-acceptance_number').first()
            if last_entry:
                last_num = int(last_entry.acceptance_number[-4:])
                new_num = last_num + 1
            else:
                new_num = 1
            new_acceptance_number = f"{date_part}{new_num:04d}"
            if not CarEntry.objects.filter(acceptance_number=new_acceptance_number).exists():
                return new_acceptance_number

    @property
    def combined_key(self):
        return f"{self.engine_number}-{self.chassis_number}"

    def __str__(self):
        return f"{self.acceptance_number} - {self.license_plate or 'بدون پلاک'}"
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
            self.recorded_at = jdatetime_datetime.now().strftime('%Y/%m/%d')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"قطعات {self.car}"

class CarCosts(models.Model):
    car = models.OneToOneField(CarEntry, on_delete=models.CASCADE, to_field='acceptance_number', verbose_name="خودرو", related_name="costs", null=True, blank=True)
    daily_price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="قیمت روز", null=True, blank=True)
    fine = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="خلافی", null=True, blank=True)
    fine_document = models.FileField(upload_to='documents/fines/', null=True, blank=True, verbose_name="سند خلافی")
    court_cost = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="هزینه دادگاهی", null=True, blank=True)
    court_document = models.FileField(upload_to='documents/court/', null=True, blank=True, verbose_name="سند دادگاهی")
    transport_cost = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="هزینه حمل", null=True, blank=True)
    transport_document = models.FileField(upload_to='documents/transport/', null=True, blank=True, verbose_name="سند حمل")
    proxy_cost = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="هزینه وکالت", null=True, blank=True)
    proxy_document = models.FileField(upload_to='documents/proxy/', null=True, blank=True, verbose_name="سند وکالت")
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, editable=False, verbose_name="جمع کل")
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="مسئول ثبت هزینه‌ها", related_name="car_costs")
    recorded_at = models.CharField(max_length=10, verbose_name="تاریخ ثبت هزینه‌ها", null=True, blank=True)  # به شمسی

    def save(self, *args, **kwargs):
        # تبدیل None به 0 برای هر فیلد
        daily = self.daily_price or Decimal('0.00')
        fine = self.fine or Decimal('0.00')
        court = self.court_cost or Decimal('0.00')
        transport = self.transport_cost or Decimal('0.00')
        proxy = self.proxy_cost or Decimal('0.00')
        # محاسبه مجموع
        self.total_cost =  fine + court + transport + proxy
        # تنظیم تاریخ اگه خالی باشه
        if not self.recorded_at:
            self.recorded_at = jdatetime_datetime.now().strftime('%Y/%m/%d')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"هزینه‌های {self.car}"

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
            self.edited_at = jdatetime_datetime.now().strftime('%Y/%m/%d')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_edit_type_display()} - {self.car_entry.acceptance_number} - {self.edited_at}"

    class Meta:
        verbose_name = "لاگ ویرایش"
        verbose_name_plural = "لاگ‌های ویرایش"

class FinalRegistration(models.Model):
    car = models.OneToOneField('CarEntry', on_delete=models.CASCADE, related_name='final_registration')
    photo = models.ImageField(upload_to='final_photos/', blank=True, null=True, verbose_name='عکس')
    tracking_code = models.CharField(max_length=50, verbose_name='کد رهگیری')
    is_finalized = models.BooleanField(default=False, verbose_name='نهایی شده')
    finalized_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='ثبت‌کننده')
    finalized_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت نهایی')

    def __str__(self):
        return f"ثبت نهایی {self.car.acceptance_number}"

