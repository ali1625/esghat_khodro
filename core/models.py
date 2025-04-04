from django.contrib.humanize.templatetags.humanize import intcomma
from django.contrib.postgres.fields import ArrayField
from django.db import models, IntegrityError, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.models import User
from jdatetime import datetime as jdatetime_datetime
from decimal import Decimal

from core.utils import rename_uploaded_file


class Company(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام شرکت")
    National_ID = models.CharField(max_length=100, unique=True, verbose_name="شناسه ملی")
    code = models.CharField(max_length=10, unique=True, verbose_name="کد شرکت")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "شرکت"
        verbose_name_plural = "شرکت‌ها"


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
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='regular')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="شرکت")

    def __str__(self):
        return f"{self.user.username} - {self.role}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'userprofile'):
        # فقط اگه پروفایل از قبل وجود نداشته باشه، بساز
        role = 'admin' if instance.is_superuser else 'regular'
        UserProfile.objects.create(user=instance, role=role)


class ActiveDocumentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Document(models.Model):
    engine_number = models.CharField(max_length=50, unique=True, verbose_name="شماره موتور")
    chassis_number = models.CharField(max_length=50, unique=True, verbose_name="شماره شاسی")
    car_document = models.ImageField(upload_to='documents/', verbose_name="سند خودرو", blank=True, null=True)
    car_card = models.ImageField(upload_to='documents/', verbose_name="کارت خودرو", blank=True, null=True)
    delivery_date = models.CharField(max_length=10, verbose_name="تاریخ تحویل", blank=False, null=False,
                                     default='1111/11/11')
    company_paper = models.ImageField(upload_to='deceased_docs/', verbose_name="مدرک فوتی ۱", blank=True, null=True)
    delivery_date_gregorian = models.DateField(verbose_name="تاریخ تحویل (میلادی)", blank=True, null=True)
    vekalat = models.ImageField(upload_to='documents/', verbose_name="وکالت نامه", blank=True, null=True)
    is_deceased = models.BooleanField(default=False, verbose_name="فوتی")
    deceased_doc1 = models.ImageField(upload_to='deceased_docs/', verbose_name="مدرک فوتی ۱", blank=True, null=True)
    deceased_doc2 = models.ImageField(upload_to='deceased_docs/', verbose_name="مدرک فوتی ۲", blank=True, null=True)
    created_by = models.CharField(max_length=100, null=True, blank=True, verbose_name="مسئول ثبت ")
    edited_by = models.CharField(max_length=50, null=True, blank=True, verbose_name="ویرایش‌کننده")
    created_at = models.CharField(max_length=10, verbose_name="تاریخ ایجاد", blank=True)  # تاریخ شمسی
    created_at_gregorian = models.DateField(verbose_name="تاریخ ایجاد (میلادی)", blank=True,
                                            null=True)  # تاریخ میلادی مخفی
    car = models.ForeignKey('CarEntry', on_delete=models.SET_NULL, null=True, blank=True, related_name='documents',
                            verbose_name="خودرو مرتبط")
    company = models.ForeignKey(Company, on_delete=models.PROTECT, verbose_name="شرکت")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    objects = ActiveDocumentManager()  # فقط فعال‌ها
    all_objects = models.Manager()  #

    def __str__(self):
        return f"سند {self.engine_number} - {self.chassis_number}"

    @property
    def combined_key(self):
        return f"{self.engine_number}-{self.chassis_number}"

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if user:
            full_name = f"{user.userprofile.first_name} {user.userprofile.last_name}" if hasattr(user,
                                                                                                 'userprofile') else user.username
            if not self.created_by:
                self.created_by = full_name
            if self.pk:
                self.edited_by = full_name
        # تنظیم تاریخ شمسی و میلادی
        if not self.created_at:
            self.created_at = jdatetime_datetime.now().strftime('%Y/%m/%d')
        if not self.created_at_gregorian:
            self.created_at_gregorian = timezone.now().date()

        if self.delivery_date and not self.delivery_date_gregorian:
            jalali_date = jdatetime_datetime.strptime(self.delivery_date, '%Y/%m/%d')
            self.delivery_date_gregorian = jalali_date.togregorian().date()

        # فقط اگه از سیگنال نیومده باشه، چک کنیم
        if not getattr(self, '_from_signal', False) and self.car and (
                self.engine_number != self.car.engine_number or
                self.chassis_number != self.car.chassis_number
        ):
            self.car.document = None
            self.car.save(update_fields=['document'])
            self.car = None

        # # اگر خودرو متصل است و ناهماهنگی وجود دارد، ارتباط را قطع می‌کنیم
        # if self.car and (
        #         self.engine_number != self.car.engine_number or
        #         self.chassis_number != self.car.chassis_number
        # ):
        #     self.car.document = None
        #     self.car.save(update_fields=['document'])
        #     self.car = None

        super().save(*args, **kwargs)


class Complaint(models.Model):
    car = models.ForeignKey('CarEntry', on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints',
                            verbose_name='خودرو')
    company = models.ForeignKey('Company', on_delete=models.PROTECT, null=True, verbose_name='شرکت')  # فیلد جدید

    title = models.CharField(max_length=200, verbose_name='عنوان شکایت')
    complaint_document = models.ImageField(upload_to=rename_uploaded_file, null=True, blank=True,
                                           verbose_name='سند شکایت')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    created_by = models.CharField(max_length=100, null=True, blank=True, verbose_name="مسئول ثبت ")
    edited_by = models.CharField(max_length=50, null=True, blank=True, verbose_name="ویرایش‌کننده")
    created_at = models.CharField(max_length=10, verbose_name='تاریخ ثبت')
    created_at_gregorian = models.DateField(verbose_name="تاریخ ایجاد (میلادی)", blank=True, null=True)
    is_resolved = models.BooleanField(default=False, verbose_name='رفع شده')

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        # تنظیم تاریخ شمسی و میلادی
        if not self.created_at:
            self.created_at = jdatetime_datetime.now().strftime('%Y/%m/%d')
        if not self.created_at_gregorian:
            self.created_at_gregorian = timezone.now().date()

        if user:
            full_name = f"{user.userprofile.first_name} {user.userprofile.last_name}" if hasattr(user,
                                                                                                 'userprofile') else user.username
            if not self.created_by :
                self.created_by  = full_name
            if self.pk:
                self.edited_by = full_name

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'شکایت'
        verbose_name_plural = 'شکایت‌ها'

    def __str__(self):
        return f"{self.title} ({self.car.acceptance_number if self.car else 'بدون خودرو'} - {self.company.name if self.company else 'بدون شرکت'})"


class ActiveCarEntryManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class CarEntry(models.Model):
    parking_number = models.CharField(max_length=20, verbose_name="شماره پارکینگ", blank=True, null=True)
    delivery_date = models.CharField(max_length=10, verbose_name="تاریخ تحویل", blank=False, null=False)
    delivery_date_gregorian = models.DateField(verbose_name="تاریخ تحویل (میلادی)", blank=True, null=True)
    car_system = models.CharField(max_length=50, verbose_name="سیستم", blank=True, null=True)
    car_type = models.CharField(max_length=50, verbose_name="نوع خودرو", blank=True, null=True)
    car_color = models.CharField(max_length=50, verbose_name="رنگ", blank=True, null=True)
    license_plate = models.CharField(max_length=30, verbose_name="شماره انتظامی", blank=True, null=True)
    owner_name = models.CharField(max_length=50, verbose_name="نام مالک", blank=True, null=True)
    engine_number = models.CharField(max_length=50, unique=True, verbose_name="شماره موتور", blank=True, null=True)
    chassis_number = models.CharField(max_length=50, unique=True, verbose_name="شماره شاسی", blank=True, null=True)
    has_cabin_plate = models.BooleanField(default=False, verbose_name="پلاکت اتاق", blank=True, null=True)
    acceptance_number = models.CharField(max_length=13, unique=True, editable=False, verbose_name="شماره پذیرش")
    accepted_by = models.CharField(max_length=50, verbose_name="مسئول پذیرش")
    accepted_at = models.CharField(max_length=10, verbose_name="تاریخ پذیرش")
    edited_by = models.CharField(max_length=50, null=True, blank=True, verbose_name="ویرایش‌کننده")
    driver_name = models.CharField(max_length=50, verbose_name="نام و نام خانوادگی راننده/آورنده", blank=True,
                                   null=True)
    driver_license_plate = models.CharField(max_length=30, verbose_name="شماره پلاک راننده/آورنده", blank=True,
                                            null=True)
    driver_phone = models.CharField(max_length=15, verbose_name="شماره تماس راننده/آورنده", blank=True, null=True)
    front_image = models.ImageField(upload_to=rename_uploaded_file, verbose_name="عکس جلوی خودرو")
    rear_image = models.ImageField(upload_to=rename_uploaded_file, verbose_name="عکس عقب خودرو")
    chassis_image = models.ImageField(upload_to=rename_uploaded_file, verbose_name="عکس شماره شاسی", blank=True,
                                      null=True)
    engine_image = models.ImageField(upload_to=rename_uploaded_file, verbose_name="عکس شماره موتور", blank=True,
                                     null=True)

    Physical_readiness = models.BooleanField(default=False, verbose_name="آمادگی فیزیکی")
    document = models.ForeignKey('Document', on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='car_entries', verbose_name="سند مرتبط")
    company = models.ForeignKey(Company, on_delete=models.PROTECT, verbose_name="شرکت")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    objects = ActiveCarEntryManager()  # فقط فعال‌ها
    all_objects = models.Manager()  # همه رکوردها

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        company = kwargs.pop('company', None)  # شرکت رو از kwargs می‌گیریم

        if not self.delivery_date:
            raise ValueError("تاریخ تحویل نمی‌تواند خالی باشد.")
        # تبدیل تاریخ شمسی به میلادی
        if self.delivery_date and not self.delivery_date_gregorian:
            jalali_date = jdatetime_datetime.strptime(self.delivery_date, '%Y/%m/%d')
            self.delivery_date_gregorian = jalali_date.togregorian().date()

        if not self.acceptance_number and self.delivery_date:
            self.acceptance_number = self._generate_unique_acceptance_number()

        if not self.accepted_at:
            self.accepted_at = jdatetime_datetime.now().strftime('%Y/%m/%d')

        if user:
            full_name = f"{user.userprofile.first_name} {user.userprofile.last_name}" if hasattr(user,
                                                                                                 'userprofile') else user.username
            if not self.accepted_by:
                self.accepted_by = full_name
            if self.pk:
                self.edited_by = full_name

        if company is not None:  # اگه شرکت پاس داده شده، اعمالش می‌کنیم
            self.company = company

        if not getattr(self, '_from_signal', False) and self.document and (
                self.engine_number != self.document.engine_number or
                self.chassis_number != self.document.chassis_number
        ):
            self.document.car = None
            self.document.save(update_fields=['car'])
            self.document = None

        # اگر سند وجود دارد و ناهماهنگی پیدا شد، ارتباط را قطع می‌کنیم
        # if self.document and (
        #         self.engine_number != self.document.engine_number or
        #         self.chassis_number != self.document.chassis_number
        # ):
        #     self.document.car = None
        #     self.document.save(update_fields=['car'])  # قطع ارتباط از سمت سند
        #     self.document = None  # قطع ارتباط از سمت خودرو

        super().save(*args, **kwargs)

    def _generate_unique_acceptance_number(self):
        delivery_date = jdatetime_datetime.strptime(self.delivery_date, '%Y/%m/%d')
        date_part = delivery_date.strftime('%Y%m')
        while True:
            last_entry = CarEntry.objects.filter(acceptance_number__startswith=date_part).order_by(
                '-acceptance_number').first()
            if last_entry:
                last_num = int(last_entry.acceptance_number[-4:])
                new_num = last_num + 1
            else:
                new_num = 1
            new_acceptance_number = f"{date_part}{new_num:04d}"
            if not CarEntry.objects.filter(acceptance_number=new_acceptance_number).exists():
                return new_acceptance_number

    def has_all_images(self):
        return all([self.front_image, self.rear_image, self.chassis_image, self.engine_image])

    @property
    def combined_key(self):
        return f"{self.engine_number}-{self.chassis_number}"

    def __str__(self):
        return f"{self.acceptance_number} - {self.license_plate or 'بدون پلاک'}"

class Serialnumber (models.Model):
    serial_number = models.CharField(max_length=20, verbose_name="شماره سریال", blank=True, null=True)
    Registration_nnhk = models.ImageField(upload_to=rename_uploaded_file, verbose_name="عکس جلوی خودرو")
    recorded_by = models.CharField(max_length=100, null=True, blank=True, verbose_name="برگه ثبت نام nnhk ")
    recorded_at = models.CharField(max_length=10, verbose_name="تاریخ ثبت شماره سریال", null=True, blank=True)  # به شمسی
    recorded_at_gregorian = models.DateField(verbose_name="تاریخ ثبت (میلادی)", blank=True, null=True)
    car = models.OneToOneField(CarEntry, on_delete=models.CASCADE, to_field='acceptance_number', verbose_name="خودرو", related_name="serial")

    def save(self, *args, **kwargs):
        if not self.recorded_at:
            self.recorded_at = jdatetime_datetime.now().strftime('%Y/%m/%d')

        if not self.recorded_at_gregorian:
            self.recorded_at_gregorian = timezone.now().date()
            super().save(*args, **kwargs)

    def __str__(self):
        return f"شماره سریال {self.car}"

class CarParts(models.Model):
    car = models.OneToOneField(CarEntry, on_delete=models.CASCADE, to_field='acceptance_number', verbose_name="خودرو",
                               related_name="parts")
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
    gas_cylinder = models.CharField(max_length=10, choices=[('LNG', 'LNG'), ('CNG', 'CNG'), ('None', 'ندارد')],
                                    default='None', verbose_name="کپسول")
    brake_booster = models.BooleanField(default=False, verbose_name="پوستر ترمز")
    weight = models.FloatField(verbose_name="وزن", null=True, blank=True)
    plate_status = models.CharField(max_length=20,
                                    choices=[('Single', 'تک پلاک'), ('Double', 'جفت پلاک'), ('None', 'فاقد پلاک')],
                                    default='None', verbose_name="وضعیت پلاک")
    plate_description = models.TextField(verbose_name="توضیحات پلاک", blank=True)
    recorded_by = models.CharField(max_length=100, null=True, blank=True, verbose_name="مسئول ثبت ")
    recorded_at = models.CharField(max_length=10, verbose_name="تاریخ ثبت قطعات", null=True, blank=True)  # به شمسی
    recorded_at_gregorian = models.DateField(verbose_name="تاریخ ایجاد (میلادی)", blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, verbose_name="شرکت")

    def save(self, *args, **kwargs):
        if not self.recorded_at:
            self.recorded_at = jdatetime_datetime.now().strftime('%Y/%m/%d')

        if not self.recorded_at_gregorian:
            self.recorded_at_gregorian = timezone.now().date()
            super().save(*args, **kwargs)

    def __str__(self):
        return f"قطعات {self.car}"


class CarCosts(models.Model):
    # گزینه‌های انتخاب برای هزینه آگاهی
    AGAHI_CHOICES = (
        ('room_replacement', 'اتاق تعویض'),
        ('engine_replacement', 'موتور تعویض'),
        ('chassis_replacement', 'شاسی تعویض'),
    )

    car = models.OneToOneField(
        'CarEntry',
        on_delete=models.CASCADE,
        to_field='acceptance_number',
        verbose_name="خودرو",
        related_name="costs",
        null=True,
        blank=True
    )
    daily_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="قیمت روز", null=True, blank=True)
    signature_fee = models.DecimalField(max_digits=15, decimal_places=0, verbose_name="هزینه گواهی امضا", null=True,
                                        blank=True)
    signature_document = models.ImageField(upload_to='documents/', null=True, blank=True, verbose_name="سند گواهی امضا")
    notary_commitment = models.DecimalField(max_digits=15, decimal_places=0, verbose_name="تعهد محضری", null=True,
                                            blank=True)
    notary_document = models.ImageField(upload_to='documents/', null=True, blank=True, verbose_name="سند تعهد محضری")
    tax_fee = models.DecimalField(max_digits=15, decimal_places=0, verbose_name="کارمزد مالیات", null=True, blank=True)
    tax_document = models.ImageField(upload_to='documents/', null=True, blank=True, verbose_name="سند کارمزد مالیات")
    municipal_clearance_fee = models.DecimalField(max_digits=15, decimal_places=0,
                                                  verbose_name="کارمزد عوارض مفاصا شهرداری", null=True, blank=True)
    municipal_document = models.ImageField(upload_to='documents/', null=True, blank=True,
                                           verbose_name="سند عوارض مفاصا شهرداری")
    highway_fee = models.DecimalField(max_digits=15, decimal_places=0, verbose_name="کارمزد عوارض آزادراهی", null=True,
                                      blank=True)
    highway_document = models.ImageField(upload_to='documents/', null=True, blank=True,
                                         verbose_name="سند عوارض آزادراهی")
    transport_cost = models.DecimalField(max_digits=15, decimal_places=0, verbose_name="هزینه حمل و نقل", null=True,
                                         blank=True)
    transport_document = models.ImageField(upload_to='documents/', null=True, blank=True, verbose_name="سند حمل و نقل")
    agahi_cost = models.DecimalField(max_digits=15, decimal_places=0, verbose_name="هزینه آگاهی", null=True, blank=True)
    agahi_type = ArrayField(
        models.CharField(max_length=20, choices=AGAHI_CHOICES),
        verbose_name="نوع آگاهی",
        null=True,
        blank=True,
        size=3,  # حداکثر 3 گزینه (اختیاری)
    )
    agahi_document = models.ImageField(upload_to='documents/', null=True, blank=True, verbose_name="سند آگاهی")
    purchase_price = models.DecimalField(max_digits=15, decimal_places=0, verbose_name="قیمت خرید", null=True,
                                         blank=True)
    total_cost = models.DecimalField(max_digits=15, decimal_places=0, editable=False, verbose_name="جمع کل")
    recorded_by = models.CharField(max_length=100, null=True, blank=True, verbose_name="مسئول ثبت هزینه‌ها")
    recorded_at = models.CharField(max_length=10, verbose_name="تاریخ ثبت هزینه‌ها", null=True, blank=True)  # به شمسی
    recorded_at_gregorian = models.DateField(verbose_name="تاریخ ایجاد (میلادی)", blank=True, null=True)
    company = models.ForeignKey('Company', on_delete=models.PROTECT, verbose_name="شرکت")

    def save(self, *args, **kwargs):
        # تبدیل None به 0 برای هر فیلد
        signature = self.signature_fee or Decimal('0')
        notary = self.notary_commitment or Decimal('0')
        tax = self.tax_fee or Decimal('0')
        municipal = self.municipal_clearance_fee or Decimal('0')
        highway = self.highway_fee or Decimal('0')
        transport = self.transport_cost or Decimal('0')
        agahi = self.agahi_cost or Decimal('0')
        purchase = self.purchase_price or Decimal('0')

        # محاسبه مجموع (فقط هزینه‌ها)
        self.total_cost = signature + notary + tax + municipal + highway + transport + agahi

        # تنظیم تاریخ اگر خالی باشد
        if not self.recorded_at:
            self.recorded_at = jdatetime_datetime.today().strftime('%Y/%m/%d')

        if not self.recorded_at_gregorian:
            self.recorded_at_gregorian = timezone.now().date()

        super().save(*args, **kwargs)

    def formatted_price(self, field_name):
        value = getattr(self, field_name, None)
        if value is not None:
            return f"{intcomma(int(value))} ریال"
        return "ثبت نشده"

    def __str__(self):
        return f"هزینه‌های {self.car}"

    class Meta:
        verbose_name = "هزینه خودرو"
        verbose_name_plural = "هزینه‌های خودرو"


class EditLog(models.Model):
    EDIT_TYPES = (
        ('CAR_ENTRY', 'ویرایش ورود خودرو'),
        ('CAR_PARTS', 'ویرایش قطعات خودرو'),
        ('CAR_COSTS', 'ویرایش هزینه‌ها'),
    )

    edit_type = models.CharField(max_length=20, choices=EDIT_TYPES, verbose_name="نوع ویرایش")
    car_entry = models.ForeignKey(CarEntry, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="خودرو", related_name="edit_logs")
    edited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="ویرایش‌کننده",
                                  related_name="edit_logs")
    edited_at = models.CharField(max_length=10, verbose_name="تاریخ ویرایش")  # تاریخ شمسی
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name="شرکت")
    changes = models.JSONField(null=True, blank=True, verbose_name="تغییرات")  # فیلدهای ویرایش‌شده

    def save(self, *args, **kwargs):
        if not self.edited_at:
            self.edited_at = jdatetime_datetime.now().strftime('%Y/%m/%d')
        super().save(*args, **kwargs)

    def get_changes_display(self):
        if not self.changes:
            return "بدون تغییر"
        changes_str = []
        for field, values in self.changes.items():
            old = values.get('old', '---')
            new = values.get('new', '---')
            changes_str.append(f"{field}: از '{old}' به '{new}'")
        return "، ".join(changes_str)

    def __str__(self):
        return f"{self.get_edit_type_display()} - {self.car_entry.acceptance_number} - {self.edited_at}"

    class Meta:
        verbose_name = "لاگ ویرایش"
        verbose_name_plural = "لاگ‌های ویرایش"


class FirstInspection(models.Model):

    DIAGNOSIS_CHOICES = (
        ('room_replacement', 'اتاق تعویض'),
        ('engine_replacement', 'موتور تعویض'),
        ('chassis_replacement', 'شاسی تعویض'),
    )


    car = models.ForeignKey('CarEntry', on_delete=models.CASCADE, related_name='first_inspections',
                            verbose_name="خودرو")
    inspection_date = models.CharField(max_length=10, verbose_name="تاریخ بازدید اول", blank=True,
                                       null=True)  # تاریخ شمسی
    inspection_date_gregorian = models.DateField(verbose_name="تاریخ بازدید اول (میلادی)", blank=True, null=True)
    two_wheeler = models.BooleanField(default=False, verbose_name="دو رکنی")
    two_wheeler_description = models.TextField(blank=True, verbose_name="توضیحات دو رکنی")
    heavy_vehicle_video = models.FileField(upload_to=rename_uploaded_file, blank=True, null=True,
                                           verbose_name="ویدیو خودرو سنگین")
    Diagnosis_type = ArrayField(
        models.CharField(max_length=20, choices=DIAGNOSIS_CHOICES),
        verbose_name="نوع آگاهی",
        null=True,
        blank=True,
        size=3,  # حداکثر 3 گزینه (اختیاری)
    )
    police_form_scan = models.ImageField(upload_to=rename_uploaded_file, blank=True, null=True,
                                         verbose_name="اسکن فرم پلیس راهور")
    agahi_report = models.ImageField(upload_to=rename_uploaded_file, blank=True, null=True, verbose_name='استعلام آگاهی')
    accept = models.BooleanField(default=False, verbose_name='تایید')
    exit = models.BooleanField(default=False, verbose_name='خروج از چرخه')
    comment_exit = models.TextField(blank=True, verbose_name="علت خروج")
    recorded_by = models.CharField(max_length=100, null=True, blank=True, verbose_name="مسئول ثبت")
    edited_by = models.CharField(max_length=50, null=True, blank=True, verbose_name="ویرایش‌کننده")
    recorded_at = models.CharField(max_length=10, verbose_name="تاریخ ثبت", blank=True, null=True)  # تاریخ شمسی
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name="شرکت")

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)

        if not self.recorded_at:
            self.recorded_at = jdatetime_datetime.now().strftime('%Y/%m/%d')

        # تبدیل تاریخ شمسی به میلادی با مدیریت خطا
        if not self.inspection_date_gregorian and self.inspection_date:
            jalali_date = jdatetime_datetime.strptime(self.inspection_date, '%Y/%m/%d')
            self.inspection_date_gregorian = jalali_date.togregorian()

        if user:
            full_name = f"{user.userprofile.first_name} {user.userprofile.last_name}" if hasattr(user,
                                                                                                 'userprofile') else user.username
            if not self.recorded_by:
                self.recorded_by = full_name
            if self.pk:
                self.edited_by = full_name

            super().save(*args, **kwargs)


    def __str__(self):
        return f"بازدید اول {self.car.acceptance_number} - {self.inspection_date}"

    class Meta:
        verbose_name = "بازدید اول"
        verbose_name_plural = "بازدیدهای اول"


# class SecondInspection(models.Model):
#     car = models.OneToOneField(CarEntry, on_delete=models.CASCADE, primary_key=True, related_name='second_inspection', verbose_name="خودرو")
#     second_inspection_date = models.CharField(max_length=10, verbose_name="تاریخ بازدید دوم", blank=True, null=True)  # تاریخ شمسی
#     second_inspection_date_gregorian = models.DateField(verbose_name="تاریخ بازدید دوم (میلادی)", blank=True, null=True)
#     police_form_scan = models.ImageField(upload_to=rename_uploaded_file, blank=True, null=True, verbose_name="اسکن فرم پلیس راهور")
#     virtual_plate = models.CharField(max_length=20, blank=True, null=True, verbose_name="پلاک مجازی")
#     recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="ثبت‌کننده")
#     recorded_at = models.CharField(max_length=10, verbose_name="تاریخ ثبت", blank=True, null=True)  # تاریخ شمسی
#     company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name="شرکت")
#
#     def save(self, *args, **kwargs):
#         if not self.second_inspection_date:
#             self.second_inspection_date = jdatetime_datetime.now().strftime('%Y/%m/%d')
#         if not self.second_inspection_date_gregorian and self.second_inspection_date_gregorian:
#             jalali_date = jdatetime_datetime.strptime(self.second_inspection_date_gregorian, '%Y/%m/%d')
#             self.recorded_at_gregorian = jalali_date.togregorian().date()
#
#
#         if not self.recorded_at:
#             self.recorded_at = jdatetime_datetime.now().strftime('%Y/%m/%d')
#
#
#         super().save(*args, **kwargs)
#
#     def __str__(self):
#         return f"بازدید دوم {self.car.acceptance_number} - {self.second_inspection_date}"
#
#     class Meta:
#         verbose_name = "بازدید دوم"
#         verbose_name_plural = "بازدیدهای دوم"

class FinalRegistration(models.Model):
    car = models.OneToOneField('CarEntry', on_delete=models.CASCADE, related_name='finalRegistration',
                               verbose_name="خودرو")
    second_inspection_date = models.CharField(max_length=10, verbose_name="تاریخ بازدید دوم", blank=True, null=True)
    second_inspection_date_gregorian = models.DateField(verbose_name="تاریخ بازدید دوم (میلادی)", blank=True, null=True)
    police_form_scan = models.ImageField(upload_to=rename_uploaded_file, blank=True, null=True,
                                         verbose_name="اسکن فرم پلیس راهور")

    virtual_plate = models.CharField(max_length=20, blank=True, null=True, verbose_name="پلاک مجازی")
    finalized_by = models.CharField(max_length=100, null=True, blank=True, verbose_name="مسئول ثبت")
    edited_by = models.CharField(max_length=50, null=True, blank=True, verbose_name="ویرایش‌کننده")
    recorded_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت نهایی')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name="شرکت")

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)


        if self.second_inspection_date and not self.second_inspection_date_gregorian:
            jalali_date = jdatetime_datetime.strptime(self.second_inspection_date, '%Y/%m/%d')
            self.second_inspection_date_gregorian = jalali_date.togregorian()

        if user:
            full_name = f"{user.userprofile.first_name} {user.userprofile.last_name}" if hasattr(user,
                                                                                                 'userprofile') else user.username
            if not self.finalized_by:
                self.recorded_by = full_name
            if self.pk:
                self.edited_by = full_name

        super().save(*args, **kwargs)

    def __str__(self):
        return f"ثبت نهایی {self.car.acceptance_number}"

    class Meta:
        verbose_name = "ثبت نهایی"
        verbose_name_plural = "ثبت‌های نهایی"
