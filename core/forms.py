from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

from .models import CarEntry, CarParts, CarCosts, UserProfile, FinalRegistration, Document, Company, Complaint, \
    FirstInspection, Serialnumber
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
        choices=UserProfile.ROLE_CHOICES,
        label="نقش",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        required=True,
        label="شرکت",
        widget=forms.Select(attrs={'class': 'form-select'})  # پیش‌فرض برای سوپرادمین
    )

    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'national_code', 'phone_number', 'role', 'company']
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
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'role'):
            self.fields['role'].initial = self.instance.role
        if self.instance and hasattr(self.instance, 'company'):
            self.fields['company'].initial = self.instance.company

        # منطق دسترسی بر اساس کاربر لاگین‌شده
        if request and request.user.is_authenticated and hasattr(request.user, 'userprofile'):
            if not request.user.is_superuser:  # ادمین شرکت
                self.fields['company'].initial = request.user.userprofile.company
                self.fields['company'].widget = forms.HiddenInput()  # مخفی برای ادمین شرکت
            # سوپرادمین می‌تونه شرکت رو تغییر بده (widget پیش‌فرض Select می‌مونه)

    def clean_national_code(self):
        national_code = self.cleaned_data['national_code']
        if national_code and (not national_code.isdigit() or len(national_code) != 10):
            raise forms.ValidationError("کد ملی باید 10 رقم باشد.")
        return national_code

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if phone_number and (
                not phone_number.isdigit() or len(phone_number) != 11 or not phone_number.startswith('09')):
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
        label="نقش",
        choices=UserProfile.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        required=True,
        label="شرکت",
        widget=forms.Select(attrs={'class': 'form-control'})  # پیش‌فرض برای سوپرادمین
    )

    class Meta:
        model = User
        fields = ['username']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if request and request.user.is_authenticated and hasattr(request.user, 'userprofile'):
            if not request.user.is_superuser:  # ادمین شرکت
                self.fields['company'].initial = request.user.userprofile.company
                self.fields['company'].widget = forms.HiddenInput()  # مخفی برای ادمین شرکت
            # سوپرادمین می‌تونه شرکت رو انتخاب کنه (widget پیش‌فرض Select می‌مونه)

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
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'first_name': self.cleaned_data['first_name'],
                    'last_name': self.cleaned_data['last_name'],
                    'national_code': self.cleaned_data['national_code'],
                    'phone_number': self.cleaned_data['phone_number'],
                    'role': self.cleaned_data['role'],
                    'company': self.cleaned_data['company'],  # ذخیره شرکت
                    'must_change_password': True
                }
            )
            if not created:
                # به‌روزرسانی پروفایل موجود
                profile.first_name = self.cleaned_data['first_name']
                profile.last_name = self.cleaned_data['last_name']
                profile.national_code = self.cleaned_data['national_code']
                profile.phone_number = self.cleaned_data['phone_number']
                profile.role = self.cleaned_data['role']
                profile.company = self.cleaned_data['company']
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

class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['title', 'complaint_document', 'description']  # company رو اینجا نمی‌ذاریم
        exclude = ['created_at', 'created_at_gregorian', 'company', 'created_by']
        labels = {
            'title': 'عنوان شکایت',
            'complaint_document': 'سند شکایت',
            'description': 'توضیحات',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class DocumentForm(forms.ModelForm):
    delivery_date = forms.CharField(
        label='تاریخ تحویل',
        widget=forms.TextInput(attrs={'class': 'form-control persian-date', 'placeholder': 'مثال: 1403/12/14'}),
        required=True
    )

    # اضافه کردن فیلد فوتی
    is_deceased = forms.BooleanField(
        label='فوتی',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    deceased_doc1 = forms.ImageField(
        label='مدرک فوتی ۱',
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    deceased_doc2 = forms.ImageField(
        label='مدرک فوتی ۲',
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Document
        fields = [
            'engine_number', 'chassis_number', 'car_document', 'car_card', 'vekalat', 'company',
            'delivery_date', 'is_deceased', 'deceased_doc1', 'deceased_doc2', 'company_paper',
        ]
        exclude = ['created_at', 'created_at_gregorian', 'edited_by', 'created_by']
        widgets = {
            'engine_number': forms.TextInput(attrs={'class': 'form-control'}),
            'chassis_number': forms.TextInput(attrs={'class': 'form-control'}),
            'car_document': forms.FileInput(attrs={'class': 'form-control'}),
            'car_card': forms.FileInput(attrs={'class': 'form-control'}),
            'vekalat': forms.FileInput(attrs={'class': 'form-control'}),
            'company_paper': forms.FileInput(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'engine_number': 'شماره موتور',
            'chassis_number': 'شماره شاسی',
            'car_document': 'سند خودرو',
            'car_card': 'کارت خودرو',
            'vekalat': 'وکالت نامه',
            'company': 'شرکت',
            'company_paper': 'برگه کمپانی',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.request:
            if not self.request.user.is_superuser:
                self.fields.pop('company')
            elif self.request.user.is_superuser and not self.initial.get('company'):
                self.initial['company'] = None
        if self.instance.pk and self.instance.delivery_date:
            self.initial['delivery_date'] = self.instance.delivery_date

    def clean(self):
        cleaned_data = super().clean()
        is_deceased = cleaned_data.get('is_deceased')
        deceased_doc1 = cleaned_data.get('deceased_doc1')
        deceased_doc2 = cleaned_data.get('deceased_doc2')

        # اگه "فوتی" انتخاب شده باشه، هر دو عکس باید آپلود بشن
        if is_deceased:
            if not deceased_doc1:
                raise ValidationError({'deceased_doc1': 'لطفاً مدرک فوتی ۱ را آپلود کنید.'})
            if not deceased_doc2:
                raise ValidationError({'deceased_doc2': 'لطفاً مدرک فوتی ۲ را آپلود کنید.'})

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.request:
            instance.save(user=self.request.user)  # کاربر رو به مدل پاس می‌دیم
        if commit:
            instance.save()
        return instance


    # def clean(self):
    #     cleaned_data = super().clean()
    #     if self.request:
    #         if not self.request.user.is_superuser:
    #             if not hasattr(self.request.user, 'userprofile') or not self.request.user.userprofile.company:
    #                 raise ValidationError("کاربر باید به یک شرکت متصل باشد.")
    #             cleaned_data['company'] = self.request.user.userprofile.company
    #         elif self.request.user.is_superuser and not cleaned_data.get('company'):
    #             raise ValidationError("لطفاً یک شرکت انتخاب کنید.")
    #     return cleaned_data

    def clean_delivery_date(self):
        delivery_date = self.cleaned_data.get('delivery_date')
        if not delivery_date:  # اگر خالی باشد و اجباری باشد، خطا بدهد
            raise forms.ValidationError("تاریخ تحویل الزامی است.")
        try:
            jdatetime_datetime.strptime(delivery_date, '%Y/%m/%d')
            return delivery_date
        except ValueError:
            raise forms.ValidationError("تاریخ را به فرمت درست وارد کنید (مثال: 1403/12/14)")

    def clean(self):
        cleaned_data = super().clean()
        if self.request and not self.request.user.is_superuser:
            # برای غیر سوپر یوزرها، شرکت از پروفایل کاربر میاد
            if not self.request.user.userprofile.company:
                raise ValidationError("کاربر باید به یک شرکت متصل باشد.")
            cleaned_data['company'] = self.request.user.userprofile.company
        return cleaned_data


class CarEntryForm(forms.ModelForm):
    delivery_date = forms.CharField(
        label='تاریخ تحویل',
        widget=forms.TextInput(attrs={'class': 'form-control persian-date', 'placeholder': 'مثال: 1403/12/14'}),
        required=True
    )
    parking_number = forms.ChoiceField(
        label='شماره پارکینگ',
        choices=[('پارت 1', 'پارت 1'), ('پارت 2', 'پارت 2'), ('پارت 3', 'پارت 3'), ('پارت 4', 'پارت 4')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(is_active=True),
        label='شرکت',
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False  # برای سوپر یوزرها اختیاریه
    )

    class Meta:
        model = CarEntry
        fields = [
            'company', 'parking_number', 'delivery_date', 'car_type', 'license_plate', 'owner_name', 'engine_number',
            'chassis_number', 'driver_name', 'driver_license_plate', 'driver_phone', 'has_cabin_plate',
            'front_image', 'rear_image', 'chassis_image', 'engine_image', 'Physical_readiness',
        ]
        widgets = {
            'car_type': forms.TextInput(attrs={'class': 'form-control'}),
            'license_plate': forms.TextInput(attrs={'class': 'form-control'}),
            'owner_name': forms.TextInput(attrs={'class': 'form-control'}),
            'engine_number': forms.TextInput(attrs={'class': 'form-control'}),
            'chassis_number': forms.TextInput(attrs={'class': 'form-control'}),
            'has_cabin_plate': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'driver_name': forms.TextInput(attrs={'class': 'form-control'}),
            'driver_license_plate': forms.TextInput(attrs={'class': 'form-control'}),
            'driver_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'front_image': forms.FileInput(attrs={'class': 'form-control'}),
            'rear_image': forms.FileInput(attrs={'class': 'form-control'}),
            'chassis_image': forms.FileInput(attrs={'class': 'form-control'}),
            'engine_image': forms.FileInput(attrs={'class': 'form-control'}),
            'Physical_readiness': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'company': 'شرکت',
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
            'Physical_readiness': 'آماده فیزیکی برای بازدید',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.request:
            if not self.request.user.is_superuser:
                # برای غیر سوپر یوزرها، فیلد شرکت رو حذف می‌کنیم
                self.fields.pop('company')
            elif self.request.user.is_superuser and not self.initial.get('company'):
                # برای سوپر یوزر، شرکت رو پیش‌فرض خالی بذاریم
                self.initial['company'] = None
        if self.instance.pk and self.instance.delivery_date:
            self.initial['delivery_date'] = self.instance.delivery_date

    def clean_delivery_date(self):
        delivery_date = self.cleaned_data.get('delivery_date')
        if not delivery_date:  # اگر خالی باشد و اجباری باشد، خطا بدهد
            raise forms.ValidationError("تاریخ تحویل الزامی است.")
        try:
            jdatetime_datetime.strptime(delivery_date, '%Y/%m/%d')
            return delivery_date
        except ValueError:
            raise forms.ValidationError("تاریخ را به فرمت درست وارد کنید (مثال: 1403/12/14)")

    def clean_license_plate(self):
        license_plate = self.cleaned_data.get('license_plate')
        if license_plate:
            parts = license_plate.split(' - ')
            if len(parts) != 4 or not (
                    parts[0].startswith('ایران ') and parts[0][6:].isdigit() and len(parts[0][6:]) == 2 and  # ایران 99
                    parts[1].isdigit() and len(parts[1]) == 3 and  # 999
                    parts[2] in 'آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی' and  # س
                    parts[3].isdigit() and len(parts[3]) == 2  # 99
            ):
                raise ValidationError(
                    "فرمت پلاک خودرو باید 'ایران عدد دو رقمی - عدد سه رقمی - حرف فارسی - عدد دو رقمی' باشد.")
        return license_plate

    def clean_driver_license_plate(self):
        driver_license_plate = self.cleaned_data.get('driver_license_plate')
        if driver_license_plate:
            parts = driver_license_plate.split(' - ')
            if len(parts) != 4 or not (
                    parts[0].startswith('ایران ') and parts[0][6:].isdigit() and len(parts[0][6:]) == 2 and  # ایران 22
                    parts[1].isdigit() and len(parts[1]) == 3 and  # 787
                    parts[2] in 'آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی' and  # س
                    parts[3].isdigit() and len(parts[3]) == 2  # 33
            ):
                raise ValidationError(
                    "فرمت پلاک راننده باید 'ایران عدد دو رقمی - عدد سه رقمی - حرف فارسی - عدد دو رقمی' باشد.")
        return driver_license_plate

    def clean(self):
        cleaned_data = super().clean()
        if self.request and not self.request.user.is_superuser:
            # برای غیر سوپر یوزرها، شرکت از پروفایل کاربر میاد
            if not self.request.user.userprofile.company:
                raise ValidationError("کاربر باید به یک شرکت متصل باشد.")
            cleaned_data['company'] = self.request.user.userprofile.company
        return cleaned_data


class SerialNumberform(forms.ModelForm):
    serial_validator = RegexValidator(
        regex=r'^\d{5}-\d{7}-\d{4}$',
        message='شماره سریال باید ۱۶ رقم باشد و به شکل ۰۰۰۰۰-۱۱۱۱۱۱۱-۲۲۲۲ وارد شود.'
    )

    class Meta:
        model = Serialnumber
        fields = ['serial_number', 'Registration_nnhk']
        exclude = ['car', 'recorded_by', 'recorded_at', 'recorded_at_gregorian', 'company']
        widgets = {
           'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
           'Registration_nnhk': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'serial_number': 'شماره سریال',
            'Registration_nnhk': 'فرم ثبت نام nnhk',
        }
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_serial_number(self):
        serial_number = self.cleaned_data['serial_number']
        # چک کن که فرمت درست باشه و 16 رقم داشته باشه
        if not self.serial_validator.regex.match(serial_number):
            raise forms.ValidationError(self.serial_validator.message)
        if len(serial_number.replace('-', '')) != 16:
            raise forms.ValidationError('شماره سریال باید دقیقاً ۱۶ رقم باشد.')
        return serial_number  # با خط تیره‌ها برمی‌گردونه


class CarPartsForm(forms.ModelForm):
    class Meta:
        model = CarParts
        fields = '__all__'
        exclude = ['car', 'recorded_by', 'recorded_at', 'recorded_at_gregorian', 'company']  # توی ویو یا مدل پر می‌شن
        widgets = {
            'hood': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'radiator': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'ecu': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'front_rear_doors': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'wiring': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'battery_cable': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'heater': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'suspension_spring': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'alternator': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'wiper_motor': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'rims_tires': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'carburetor': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'starter': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'gearbox': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'differential': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'distributor_coil': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'fuel_pump': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'seats': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'front_disc': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'battery': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'steering_box': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'bumpers': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'wheel_drum': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'driveshaft_cv': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'fuel_rail': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'trunk_lid': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'documents': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'injector': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'glass': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'ac': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'brake_booster': forms.CheckboxInput(attrs={'class': 'form-check-input toggle-btn-input'}),
            'gas_cylinder': forms.Select(attrs={'class': 'form-control small-input'}),
            'cabin_percentage': forms.NumberInput(attrs={'class': 'form-control small-input', 'min': 0, 'max': 100}),
            'weight': forms.NumberInput(attrs={'class': 'form-control small-input'}),
            'plate_status': forms.Select(attrs={'class': 'form-control small-select'}),
            'plate_description': forms.Textarea(
                attrs={'class': 'form-control large-input', 'rows': 3, 'style': 'width: 100%;'}),
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
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        return cleaned_data


class CarCostsForm(forms.ModelForm):
    agahi_type = forms.MultipleChoiceField(
        choices=CarCosts.AGAHI_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="نوع آگاهی"
    )

    class Meta:
        model = CarCosts
        fields = '__all__'
        exclude = ['car', 'recorded_by', 'recorded_at', 'total_cost', 'company', 'recorded_at_gregorian']
        widgets = {
            'daily_price': forms.NumberInput(attrs={'class': 'form-control small-input', 'step': '0.01'}),
            'signature_fee': forms.NumberInput(attrs={'class': 'form-control modern-input'}),
            'signature_document': forms.FileInput(attrs={'class': 'form-control modern-input'}),
            'notary_commitment': forms.NumberInput(attrs={'class': 'form-control modern-input'}),
            'notary_document': forms.FileInput(attrs={'class': 'form-control modern-input'}),
            'tax_fee': forms.NumberInput(attrs={'class': 'form-control modern-input'}),
            'tax_document': forms.FileInput(attrs={'class': 'form-control modern-input'}),
            'municipal_clearance_fee': forms.NumberInput(attrs={'class': 'form-control modern-input'}),
            'municipal_document': forms.FileInput(attrs={'class': 'form-control modern-input'}),
            'highway_fee': forms.NumberInput(attrs={'class': 'form-control modern-input'}),
            'highway_document': forms.FileInput(attrs={'class': 'form-control modern-input'}),
            'transport_cost': forms.NumberInput(attrs={'class': 'form-control modern-input'}),
            'transport_document': forms.FileInput(attrs={'class': 'form-control modern-input'}),
            'agahi_cost': forms.NumberInput(attrs={'class': 'form-control modern-input'}),
            'agahi_document': forms.FileInput(attrs={'class': 'form-control modern-input'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control modern-input'}),
        }
        labels = {
            'daily_price': 'قیمت روز',
            'signature_fee': 'هزینه گواهی امضا',
            'signature_document': 'سند گواهی امضا',
            'notary_commitment': 'تعهد محضری',
            'notary_document': 'سند تعهد محضری',
            'tax_fee': 'کارمزد مالیات',
            'tax_document': 'سند کارمزد مالیات',
            'municipal_clearance_fee': 'کارمزد عوارض مفاصا شهرداری',
            'municipal_document': 'سند عوارض مفاصا شهرداری',
            'highway_fee': 'کارمزد عوارض آزادراهی',
            'highway_document': 'سند عوارض آزادراهی',
            'transport_cost': 'هزینه حمل و نقل',
            'transport_document': 'سند حمل و نقل',
            'agahi_cost': 'هزینه آگاهی',
            'agahi_type': 'نوع آگاهی',
            'agahi_document': 'سند آگاهی',
            'purchase_price': 'قیمت خرید',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # تنظیم مقدار اولیه برای agahi_type
        if self.instance and self.instance.agahi_type:
            self.fields['agahi_type'].initial = self.instance.agahi_type
        # اضافه کردن فیلد company به فرم
        self.fields['company'] = forms.ModelChoiceField(
            queryset=Company.objects.filter(is_active=True),
            label='شرکت',
            widget=forms.Select(attrs={'class': 'form-control'}),
            required=False
        )

    def clean(self):
        cleaned_data = super().clean()
        # اعتبارسنجی برای مقادیر منفی
        for field in ['daily_price', 'signature_fee', 'notary_commitment', 'tax_fee',
                      'municipal_clearance_fee', 'highway_fee', 'transport_cost',
                      'agahi_cost', 'purchase_price']:
            value = cleaned_data.get(field)
            if value is not None and value < 0:
                self.add_error(field, "هزینه نمی‌تواند منفی باشد.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # ذخیره مقدار agahi_type به صورت لیست در مدل
        instance.agahi_type = self.cleaned_data['agahi_type']
        if commit:
            instance.save()
        return instance
class SearchLogForm(forms.Form):
    acceptance_number = forms.CharField(
        max_length=9,
        required=False,
        label="شماره پذیرش",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره پذیرش را وارد کنید'})
    )


class FirstInspectionForm(forms.ModelForm):
    inspection_date = forms.CharField(
        label='تاریخ بازدید اول',
        widget=forms.TextInput(attrs={'class': 'form-control persian-date', 'placeholder': 'مثال: 1403/12/14'}),
        required=False
    )

    Diagnosis_type = forms.MultipleChoiceField(
        choices=FirstInspection.DIAGNOSIS_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="نوع آگاهی"
    )


    class Meta:
        model = FirstInspection
        fields = ['inspection_date', 'two_wheeler', 'two_wheeler_description', 'heavy_vehicle_video', 'Diagnosis_type', 'agahi_report', 'police_form_scan']
        exclude = ['car', 'recorded_by', 'recorded_at', 'company', 'inspection_date_gregorian', 'exit', 'accept']
        widgets = {
            'two_wheeler': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'two_wheeler_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'heavy_vehicle_video': forms.FileInput(attrs={'class': 'form-control'}),
         #   'Diagnosis_type': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'police_form_scan': forms.FileInput(attrs={'class': 'form-control'}),
            'agahi_report': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'inspection_date': 'تاریخ بازدید اول',
            'two_wheeler': 'دو رکنی',
            'two_wheeler_description': 'توضیحات دو رکنی',
            'heavy_vehicle_video': 'ویدیو خودرو سنگین',
            'Diagnosis_type': 'نوع آگاهی',
            'agahi_report': 'استعلام آگاهی',
            'police_form_scan': 'فرم بازدید'
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.inspection_date:
            self.initial['inspection_date'] = self.instance.inspection_date

    def clean_inspection_date(self):
        inspection_date = self.cleaned_data.get('inspection_date')
        if inspection_date:
            try:
                jdatetime_datetime.strptime(inspection_date, '%Y/%m/%d')
                return inspection_date
            except ValueError:
                raise forms.ValidationError("تاریخ را به فرمت درست وارد کنید (مثال: 1403/12/14)")
        return inspection_date

# class SecondInspectionForm(forms.ModelForm):
#     second_inspection_date = forms.CharField(
#         label='تاریخ بازدید دوم',
#         widget=forms.TextInput(attrs={'class': 'form-control persian-date', 'placeholder': 'مثال: 1403/12/15'}),
#         required=False
#     )

    # class Meta:
    #     model = SecondInspection
    #     fields = ['second_inspection_date', 'police_form_scan', 'virtual_plate']
    #     exclude = ['car', 'company']
    #     widgets = {
    #         'police_form_scan': forms.FileInput(attrs={'class': 'form-control'}),
    #         'virtual_plate': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'پلاک مجازی'}),
    #     }
    #     labels = {
    #         'second_inspection_date': 'تاریخ بازدید دوم',
    #         'police_form_scan': 'اسکن فرم پلیس راهور',
    #         'virtual_plate': 'پلاک مجازی',
    #     }
    #
    # def __init__(self, *args, **kwargs):
    #     self.request = kwargs.pop('request', None)
    #     super().__init__(*args, **kwargs)
    #     if self.instance.pk and self.instance.second_inspection_date:
    #         self.initial['second_inspection_date'] = self.instance.second_inspection_date
    #
    # def clean_second_inspection_date(self):
    #     inspection_date = self.cleaned_data.get('second_inspection_date')
    #     if inspection_date:
    #         try:
    #             jdatetime_datetime.strptime(inspection_date, '%Y/%m/%d')
    #             return inspection_date
    #         except ValueError:
    #             raise forms.ValidationError("تاریخ را به فرمت درست وارد کنید (مثال: 1403/12/15)")
    #     return inspection_date


class FinalRegistrationForm(forms.ModelForm):
    second_inspection_date = forms.CharField(
        label='تاریخ بازدید دوم',
        widget=forms.TextInput(attrs={'class': 'form-control persian-date', 'placeholder': 'مثال: 1403/12/14'}),
        required=False
    )

    class Meta:
        model = FinalRegistration
        fields = ['second_inspection_date', 'police_form_scan', 'virtual_plate']
        exclude = ['car', 'company', 'finalized_by', 'recorded_at', 'second_inspection_date_gregorian']
        widgets = {
            'police_form_scan': forms.FileInput(attrs={'class': 'form-control'}),
            'virtual_plate': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'second_inspection_date': 'تاریخ بازدید دوم',
            'police_form_scan': 'اسکن فرم پلیس راهور',
            'virtual_plate': 'پلاک مجازی',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.second_inspection_date:
            self.initial['second_inspection_date'] = self.instance.second_inspection_date

    def clean_second_inspection_date(self):
        second_inspection_date = self.cleaned_data.get('second_inspection_date')
        if second_inspection_date:
            try:
                jdatetime_datetime.strptime(second_inspection_date, '%Y/%m/%d')
                return second_inspection_date
            except ValueError:
                raise forms.ValidationError("تاریخ را به فرمت درست وارد کنید (مثال: 1403/12/14)")
        return second_inspection_date

    # def save(self, commit=True):
    #     instance = super().save(commit=False)
    #     if self.request:
    #         instance.finalized_by = self.request.user
    #     if commit:
    #         instance.save()
    #     return instance
