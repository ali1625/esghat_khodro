from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CarEntry, CarParts, CarCosts, UserProfile, FinalRegistration, Document
from jdatetime import datetime as jdatetime_datetime
import re

class AdminChangePasswordForm(forms.Form):
    new_password = forms.CharField(
        label="رمز عبور جدید",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8,
        help_text="حداقل 8 کاراکتر"
    )
    confirm_password = forms.CharField(
        label="تأیید رمز عبور جدید",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("رمزهای عبور مطابقت ندارند.")
        return cleaned_data

class UserProfileEditForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,  # از مدل استفاده می‌کنه
        label="نقش",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'national_code', 'phone_number', 'role']
        labels = {
            'first_name': 'نام',
            'last_name': 'نام خانوادگی',
            'national_code': 'کد ملی',
            'phone_number': 'شماره تلفن',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'national_code': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'role'):
            self.fields['role'].initial = self.instance.role

    def clean_national_code(self):
        national_code = self.cleaned_data['national_code']
        if national_code and (not national_code.isdigit() or len(national_code) != 10):
            raise forms.ValidationError("کد ملی باید 10 رقم باشد.")
        return national_code

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if phone_number and (not phone_number.isdigit() or len(phone_number) != 11 or not phone_number.startswith('09')):
            raise forms.ValidationError("شماره موبایل باید 11 رقم باشد و با 09 شروع شود.")
        return phone_number
class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, label='نام')
    last_name = forms.CharField(max_length=50, label='نام خانوادگی')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            UserProfile.objects.create(
                user=user,
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name']
            )
        return user

class AdminUserCreationForm(forms.ModelForm):
    first_name = forms.CharField(
        label="نام",
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label="نام خانوادگی",
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    national_code = forms.CharField(
        label="کد ملی",
        max_length=10,
        min_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="کد ملی باید 10 رقم باشد."
    )
    phone_number = forms.CharField(
        label="شماره موبایل",
        max_length=11,
        min_length=11,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="شماره موبایل باید 11 رقم باشد (مثل 09123456789)."
    )

    role = forms.ChoiceField(
        label = "نقش",
        choices = UserProfile.ROLE_CHOICES,
        widget = forms.Select(attrs={'class': 'form-control'}),

    )

    class Meta:
        model = User
        fields = ['username']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_national_code(self):
        national_code = self.cleaned_data['national_code']
        if not national_code.isdigit() or len(national_code) != 10:
            raise forms.ValidationError("کد ملی باید 10 رقم باشد.")
        return national_code

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if not phone_number.isdigit() or len(phone_number) != 11 or not phone_number.startswith('09'):
            raise forms.ValidationError("شماره موبایل باید 11 رقم باشد و با 09 شروع شود.")
        return phone_number

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['national_code'])
        if commit:
            user.save()
            # استفاده از get_or_create برای جلوگیری از ایجاد پروفایل تکراری
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'first_name': self.cleaned_data['first_name'],
                    'last_name': self.cleaned_data['last_name'],
                    'national_code': self.cleaned_data['national_code'],
                    'phone_number': self.cleaned_data['phone_number'],
                    'role': self.cleaned_data['role'],
                    'must_change_password': True
                }
            )
            if not created:
                # اگر پروفایل از قبل وجود داشت، آن را به‌روزرسانی می‌کنیم
                profile.first_name = self.cleaned_data['first_name']
                profile.last_name = self.cleaned_data['last_name']
                profile.national_code = self.cleaned_data['national_code']
                profile.phone_number = self.cleaned_data['phone_number']
                profile.role = self.cleaned_data['role']
                profile.must_change_password = True
                profile.save()
        return user

class CustomPasswordChangeForm(forms.Form):
    new_password = forms.CharField(
        label="رمز عبور جدید",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8,
        help_text="رمز عبور باید حداقل 8 کاراکتر داشته باشد و شامل حروف بزرگ و کوچک باشد."
    )
    confirm_password = forms.CharField(
        label="تأیید رمز عبور جدید",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8
    )

    def clean_new_password(self):
        password = self.cleaned_data['new_password']
        if len(password) < 8:
            raise forms.ValidationError("رمز عبور باید حداقل 8 کاراکتر باشد.")
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError("رمز عبور باید حداقل یک حرف بزرگ داشته باشد.")
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError("رمز عبور باید حداقل یک حرف کوچک داشته باشد.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("رمزهای عبور مطابقت ندارند.")
        return cleaned_data


# class DocumentForm(forms.ModelForm):
#     class Meta:
#         model = Document
#         fields = ['engine_number', 'chassis_number', 'file1', 'file2', 'file3', 'car']
#         widgets = {
#             'engine_number': forms.TextInput(attrs={'class': 'form-control'}),
#             'chassis_number': forms.TextInput(attrs={'class': 'form-control'}),
#             'file1': forms.FileInput(attrs={'class': 'form-control'}),
#             'file2': forms.FileInput(attrs={'class': 'form-control'}),
#             'file3': forms.FileInput(attrs={'class': 'form-control'}),
#             'car': forms.Select(attrs={'class': 'form-control'}),
#         }
#         labels = {
#             'engine_number': 'شماره موتور',
#             'chassis_number': 'شماره شاسی',
#             'file1': 'فایل ۱',
#             'file2': 'فایل ۲',
#             'file3': 'فایل ۳',
#             'car': 'خودرو مرتبط',
#         }
#
#     def clean(self):
#         cleaned_data = super().clean()
#         car = cleaned_data.get('car')
#         engine_number = cleaned_data.get('engine_number')
#         chassis_number = cleaned_data.get('chassis_number')
#
#         if car and (car.engine_number != engine_number or car.chassis_number != chassis_number):
#             raise ValidationError("شماره موتور و شاسی سند باید با خودرو مرتبط مطابقت داشته باشد.")
#         return cleaned_data
class DocumentForm(forms.ModelForm):
    created_at = forms.CharField(
        label='تاریخ ایجاد',
        widget=forms.TextInput(attrs={'class': 'form-control persian-datepicker'}),
        required=False
    )

    class Meta:
        model = Document
        fields = ['engine_number', 'chassis_number', 'file1', 'file2', 'file3', 'created_at']  # اضافه کردن created_at
        widgets = {
            'engine_number': forms.TextInput(attrs={'class': 'form-control'}),
            'chassis_number': forms.TextInput(attrs={'class': 'form-control'}),
            'file1': forms.FileInput(attrs={'class': 'form-control'}),
            'file2': forms.FileInput(attrs={'class': 'form-control'}),
            'file3': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'engine_number': 'شماره موتور',
            'chassis_number': 'شماره شاسی',
            'file1': 'فایل ۱',
            'file2': 'فایل ۲',
            'file3': 'فایل ۳',
            'created_at': 'تاریخ ایجاد',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['engine_number'].required = True
        self.fields['chassis_number'].required = True
        if self.instance and self.instance.created_at:
            self.initial['created_at'] = self.instance.created_at

    def clean_created_at(self):
        created_at = self.cleaned_data.get('created_at')
        if created_at:
            try:
                jdatetime_datetime.strptime(created_at, '%Y/%m/%d')
                return created_at
            except ValueError:
                raise forms.ValidationError("فرمت تاریخ باید YYYY/MM/DD باشد (مثلاً 1403/12/25)")
        return created_at or jdatetime_datetime.now().strftime('%Y/%m/%d')
class CarEntryForm(forms.ModelForm):
    # فیلدهای پلاک خودرو
    #digits1 = forms.CharField(max_length=2, required=True, widget=forms.TextInput(attrs={'class': 'form-control modern-input no-spinner uniform-size'}))
    #persian_letter = forms.ChoiceField(choices=[(char, char) for char in "الف ب پ ت ث ج چ ح خ د ذ ر ز ژ س ش ص ض ط ظ ع غ ف ق ک گ ل م ن و ه ی"], required=True, widget=forms.Select(attrs={'class': 'form-select modern-select uniform-size'}))
    #digits2 = forms.CharField(max_length=3, required=True, widget=forms.TextInput(attrs={'class': 'form-control modern-input no-spinner uniform-size'}))
    #digits3 = forms.CharField(max_length=2, required=True, widget=forms.TextInput(attrs={'class': 'form-control modern-input no-spinner uniform-size'}))

    # فیلدهای پلاک راننده
    #driver_digits1 = forms.CharField(max_length=2, required=True, widget=forms.TextInput(attrs={'class': 'form-control modern-input no-spinner uniform-size'}))
    #driver_persian_letter = forms.ChoiceField(choices=[(char, char) for char in "الف ب پ ت ث ج چ ح خ د ذ ر ز ژ س ش ص ض ط ظ ع غ ف ق ک گ ل م ن و ه ی"], required=True, widget=forms.Select(attrs={'class': 'form-select modern-select uniform-size'}))
    #driver_digits2 = forms.CharField(max_length=3, required=True, widget=forms.TextInput(attrs={'class': 'form-control modern-input no-spinner uniform-size'}))
    #driver_digits3 = forms.CharField(max_length=2, required=True, widget=forms.TextInput(attrs={'class': 'form-control modern-input no-spinner uniform-size'}))

    delivery_date = forms.CharField(
        label='تاریخ تحویل',
        widget=forms.TextInput(attrs={'class': 'form-control persian-date', 'placeholder': 'مثال: 1403/12/14'}),
        required=False
    )
    parking_number = forms.ChoiceField(
        label='شماره پارکینگ',
        choices=[('پارت 1', 'پارت 1'), ('پارت 2', 'پارت 2'), ('پارت 3', 'پارت 3'), ('پارت 4', 'پارت 4')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = CarEntry
        fields = [
            'parking_number', 'delivery_date', 'car_type', 'license_plate', 'owner_name', 'engine_number',
            'chassis_number', 'driver_name', 'driver_license_plate', 'driver_phone', 'has_cabin_plate',
            'front_image', 'rear_image', 'chassis_image', 'engine_image',
        ]
        widgets = {
            'car_type': forms.TextInput(attrs={'class': 'form-control'}),
            'license_plate': forms.TextInput(attrs={'type': 'hidden'}),
            'owner_name': forms.TextInput(attrs={'class': 'form-control'}),
            'engine_number': forms.TextInput(attrs={'class': 'form-control'}),
            'chassis_number': forms.TextInput(attrs={'class': 'form-control'}),
            'has_cabin_plate': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'driver_name': forms.TextInput(attrs={'class': 'form-control'}),
            'driver_license_plate': forms.TextInput(attrs={'type': 'hidden'}),
            'driver_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'front_image': forms.FileInput(attrs={'class': 'form-control'}),
            'rear_image': forms.FileInput(attrs={'class': 'form-control'}),
            'chassis_image': forms.FileInput(attrs={'class': 'form-control'}),
            'engine_image': forms.FileInput(attrs={'class': 'form-control'}),

        }
        labels = {
            'parking_number': 'شماره پارکینگ',

            'delivery_date': 'تاریخ تحویل',
            'car_type': 'نوع خودرو',
            'license_plate': 'شماره انتظامی',
            'owner_name': 'نام مالک',
            'engine_number': 'شماره موتور',
            'chassis_number': 'شماره شاسی',
            'has_cabin_plate': 'پلاکت اتاق',
            'driver_name': 'نام و نام خانوادگی راننده/آورنده',
            'driver_license_plate': 'شماره پلاک راننده/آورنده',
            'driver_phone': 'شماره تماس راننده/آورنده',
            'front_image': 'عکس جلوی خودرو',
            'rear_image': 'عکس عقب خودرو',
            'chassis_image': 'عکس شماره شاسی',
            'engine_image': 'عکس شماره موتور',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.delivery_date:
            self.initial['delivery_date'] = self.instance.delivery_date
        if self.instance.pk and self.instance.license_plate:
            parts = self.instance.license_plate.split(' - ')
            if len(parts) == 4:
                self.initial['digits1'] = parts[0]
                self.initial['persian_letter'] = parts[1]
                self.initial['digits2'] = parts[2]
                self.initial['digits3'] = parts[3].replace('ایران ', '')
        if self.instance.pk and self.instance.driver_license_plate:
            parts = self.instance.driver_license_plate.split(' - ')
            if len(parts) == 4:
                self.initial['driver_digits1'] = parts[0]
                self.initial['driver_persian_letter'] = parts[1]
                self.initial['driver_digits2'] = parts[2]
                self.initial['driver_digits3'] = parts[3].replace('ایران ', '')

    def clean(self):
        cleaned_data = super().clean()
        digits1 = cleaned_data.get('digits1')
        persian_letter = cleaned_data.get('persian_letter')
        digits2 = cleaned_data.get('digits2')
        digits3 = cleaned_data.get('digits3')
        driver_digits1 = cleaned_data.get('driver_digits1')
        driver_persian_letter = cleaned_data.get('driver_persian_letter')
        driver_digits2 = cleaned_data.get('driver_digits2')
        driver_digits3 = cleaned_data.get('driver_digits3')
        document = cleaned_data.get('document')
        engine_number = cleaned_data.get('engine_number')
        chassis_number = cleaned_data.get('chassis_number')

        # اعتبارسنجی پلاک خودرو
        if digits1 and persian_letter and digits2 and digits3:
            if not (digits1.isdigit() and len(digits1) == 2 and
                    persian_letter in 'آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی' and
                    digits2.isdigit() and len(digits2) == 3 and
                    digits3.isdigit() and len(digits3) == 2):
                raise ValidationError("فرمت پلاک خودرو باید عدد دو رقمی، حرف فارسی، عدد سه رقمی، ایران عدد دو رقمی باشد.")
            cleaned_data['license_plate'] = f"{digits1} - {persian_letter} - {digits2} - ایران {digits3}"

        # اعتبارسنجی پلاک راننده
        if driver_digits1 and driver_persian_letter and driver_digits2 and driver_digits3:
            if not (driver_digits1.isdigit() and len(driver_digits1) == 2 and
                    driver_persian_letter in 'آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی' and
                    driver_digits2.isdigit() and len(driver_digits2) == 3 and
                    driver_digits3.isdigit() and len(driver_digits3) == 2):
                raise ValidationError("فرمت پلاک آورنده باید عدد دو رقمی، حرف فارسی، عدد سه رقمی، ایران عدد دو رقمی باشد.")
            cleaned_data['driver_license_plate'] = f"{driver_digits1} - {driver_persian_letter} - {driver_digits2} - ایران {driver_digits3}"

        # چک کردن تطابق سند

        return cleaned_data

    def clean_delivery_date(self):
        delivery_date = self.cleaned_data.get('delivery_date')
        if delivery_date:
            try:
                jdatetime_datetime.strptime(delivery_date, '%Y/%m/%d')
                return delivery_date
            except ValueError:
                raise forms.ValidationError("تاریخ را به فرمت درست وارد کنید (مثال: 1403/12/14)")
        return delivery_date
class CarPartsForm(forms.ModelForm):
    class Meta:
        model = CarParts
        fields = '__all__'
        exclude = ['car', 'recorded_by', 'recorded_at']  # اینا توی ویو پر می‌شن
        widgets = {

            'hood': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'radiator': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ecu': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'front_rear_doors': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'wiring': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'battery_cable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'heater': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'suspension_spring': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'alternator': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'wiper_motor': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'rims_tires': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'carburetor': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'starter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'gearbox': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'differential': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'distributor_coil': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fuel_pump': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'seats': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'front_disc': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'battery': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'steering_box': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'bumpers': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'wheel_drum': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'driveshaft_cv': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fuel_rail': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'trunk_lid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'documents': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'injector': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'glass': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ac': forms.CheckboxInput(attrs={'class': 'form-check-input'}),

            'brake_booster': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'gas_cylinder': forms.Select(attrs={'class': 'form-control'}),
            'cabin_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'plate_status': forms.Select(attrs={'class': 'form-control'}),
            'plate_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {

            'hood': 'درب موتور',
            'radiator': 'رادیاتور',
            'ecu': 'ایسیو',
            'front_rear_doors': 'درب جلو و عقب',
            'wiring': 'سیم‌کشی',
            'battery_cable': 'کابل باطری',
            'heater': 'بخاری',
            'suspension_spring': 'فنر زیر و بند',
            'alternator': 'دینام',
            'wiper_motor': 'موتور برف‌پاک‌کن',
            'rims_tires': 'رینگ و لاستیک',
            'carburetor': 'کاربراتور',
            'starter': 'استارت',
            'gearbox': 'گیربکس',
            'differential': 'دیفرانسیل',
            'distributor_coil': 'دلکو و کوئل',
            'fuel_pump': 'سیفون بنزین',
            'seats': 'صندلی',
            'front_disc': 'دیسک چرخ جلو',
            'battery': 'باطری',
            'steering_box': 'جعبه فرمان',
            'bumpers': 'سپر عقب و جلو',
            'wheel_drum': 'کاسه چرخ',
            'driveshaft_cv': 'پلوس و گاردان',
            'fuel_rail': 'ریل سوخت',
            'trunk_lid': 'درب صندوق',
            'documents': 'سند',
            'injector': 'انژکتور و سوزن انژکتور',
            'glass': 'شیشه',
            'ac': 'کولر',

            'brake_booster': 'پوستر ترمز',
            'gas_cylinder': 'کپسول',
            'cabin_percentage': 'درصد اتاق',
            'weight': 'وزن',
            'plate_status': 'وضعیت پلاک',
            'plate_description': 'توضیحات پلاک',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class CarCostsForm(forms.ModelForm):
    class Meta:
        model = CarCosts
        fields = '__all__'
        exclude = ['car', 'recorded_by', 'recorded_at', 'total_cost']  # total_cost خودکار پر می‌شه
        widgets = {
            'daily_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fine': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fine_document': forms.FileInput(attrs={'class': 'form-control'}),
            'court_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'court_document': forms.FileInput(attrs={'class': 'form-control'}),
            'transport_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'transport_document': forms.FileInput(attrs={'class': 'form-control'}),
            'proxy_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'proxy_document': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'daily_price': 'قیمت روز',
            'fine': 'خلافی',
            'fine_document': 'سند خلافی',
            'court_cost': 'هزینه دادگاهی',
            'court_document': 'سند دادگاهی',
            'transport_cost': 'هزینه حمل',
            'transport_document': 'سند حمل',
            'proxy_cost': 'هزینه وکالت',
            'proxy_document': 'سند وکالت',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class SearchLogForm(forms.Form):
    acceptance_number = forms.CharField(
        max_length=9,
        required=False,
        label="شماره پذیرش",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره پذیرش را وارد کنید'})
    )

class FinalRegistrationForm(forms.ModelForm):
    class Meta:
        model = FinalRegistration
        fields = ['photo', 'tracking_code', 'is_finalized']
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'tracking_code': forms.TextInput(attrs={'class': 'form-control'}),
            'is_finalized': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'photo': 'عکس',
            'tracking_code': 'کد رهگیری',
            'is_finalized': 'نهایی شده',
        }