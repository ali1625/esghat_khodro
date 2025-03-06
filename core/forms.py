from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CarEntry, CarParts, CarCosts, UserProfile
from jdatetime import datetime as jdatetime

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name']
        labels = {'first_name': 'نام', 'last_name': 'نام خانوادگی'}

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

class CarEntryForm(forms.ModelForm):
    persian_letter = forms.ChoiceField(
        label='حرف فارسی (خودرو)',
        choices=[(letter, letter) for letter in 'آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی'],
        required=True
    )
    driver_persian_letter = forms.ChoiceField(
        label='حرف فارسی (آورنده)',
        choices=[(letter, letter) for letter in 'آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی'],
        required=True
    )
    delivery_date = forms.CharField(
        label='تاریخ تحویل',
        widget=forms.TextInput(attrs={'class': 'form-control persian-date', 'placeholder': 'مثال: 1403/12/14'}),
        required=True
    )
    parking_number = forms.ChoiceField(
        label='شماره پارکینگ',
        choices=[('پارت 1', 'پارت 1'), ('پارت 2', 'پارت 2'), ('پارت 3', 'پارت 3'), ('پارت 4', 'پارت 4')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    class Meta:
        model = CarEntry
        fields = ['parking_number', 'delivery_date', 'car_type', 'license_plate', 'owner_name', 'engine_number', 
                  'chassis_number', 'has_cabin_plate', 'driver_name', 'driver_license_plate', 'driver_phone']  # accepted_by حذف شد
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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.delivery_date:
            self.initial['delivery_date'] = self.instance.delivery_date

    def clean(self):
        cleaned_data = super().clean()
        license_plate = cleaned_data.get('license_plate', '')
        driver_license_plate = cleaned_data.get('driver_license_plate', '')
        digits1 = cleaned_data.get('digits1', '')
        digits2 = cleaned_data.get('digits2', '')
        digits3 = cleaned_data.get('digits3', '')
        persian_letter = cleaned_data.get('persian_letter', '')
        driver_digits1 = cleaned_data.get('driver_digits1', '')
        driver_digits2 = cleaned_data.get('driver_digits2', '')
        driver_digits3 = cleaned_data.get('driver_digits3', '')
        driver_persian_letter = cleaned_data.get('driver_persian_letter', '')

        if not (digits1 and digits2 and digits3 and persian_letter):
            if license_plate:
                parts = license_plate.split(' - ')
                if len(parts) == 4:
                    digits1 = parts[0].split(' ')[0]
                    digits2 = parts[1]
                    persian_letter = parts[2]
                    digits3 = parts[3]
        if not (driver_digits1 and driver_digits2 and driver_digits3 and driver_persian_letter):
            if driver_license_plate:
                parts = driver_license_plate.split(' - ')
                if len(parts) == 4:
                    driver_digits1 = parts[0].split(' ')[0]
                    driver_digits2 = parts[1]
                    driver_persian_letter = parts[2]
                    driver_digits3 = parts[3]

        if not (digits1.isdigit() and len(digits1) == 2 and
                digits2.isdigit() and len(digits2) == 3 and
                persian_letter in 'آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی' and
                digits3.isdigit() and len(digits3) == 2):
            raise ValidationError("فرمت پلاک خودرو باید عدد دو رقمی (بالا: ایران)، خط، عدد سه رقمی، خط، حرف فارسی، خط، عدد دو رقمی باشد (مثال: 12 (ایران) - 123 - الف - 45)")

        if not (driver_digits1.isdigit() and len(driver_digits1) == 2 and
                driver_digits2.isdigit() and len(driver_digits2) == 3 and
                driver_persian_letter in 'آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی' and
                driver_digits3.isdigit() and len(driver_digits3) == 2):
            raise ValidationError("فرمت پلاک آورنده باید عدد دو رقمی (بالا: ایران)، خط، عدد سه رقمی، خط، حرف فارسی، خط، عدد دو رقمی باشد (مثال: 12 (ایران) - 123 - الف - 45)")

        cleaned_data['license_plate'] = f"{digits1} (ایران) - {digits2} - {persian_letter} - {digits3}"
        cleaned_data['driver_license_plate'] = f"{driver_digits1} (ایران) - {driver_digits2} - {driver_persian_letter} - {driver_digits3}"

        return cleaned_data

    def clean_delivery_date(self):
        delivery_date = self.cleaned_data['delivery_date']
        try:
            jdatetime.strptime(delivery_date, '%Y/%m/%d')
            return delivery_date
        except ValueError:
            raise forms.ValidationError("تاریخ را به فرمت درست وارد کنید (مثال: 1403/12/14)")
class CarPartsForm(forms.ModelForm):
    class Meta:
        model = CarParts
        fields = '__all__'
        exclude = ['car', 'recorded_by', 'recorded_at']  # اینا توی ویو پر می‌شن
        widgets = {
            'cabin_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
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
            'gas_cylinder': forms.Select(attrs={'class': 'form-control'}),
            'brake_booster': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'plate_status': forms.Select(attrs={'class': 'form-control'}),
            'plate_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'cabin_percentage': 'درصد اتاق',
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
            'gas_cylinder': 'کپسول',
            'brake_booster': 'پوستر ترمز',
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