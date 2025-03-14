from django.db import transaction
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, CarEntry, Document

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if not UserProfile.objects.filter(user=instance).exists():
            role = 'admin' if instance.is_superuser else 'regular'
            UserProfile.objects.create(user=instance, role=role)


# @receiver(post_save, sender=CarEntry)
# def connect_car_to_document(sender, instance, created, **kwargs):
#     def _connect_car():
#         print(f"سیگنال CarEntry اجرا شد برای {instance.acceptance_number}")
#         if instance.engine_number and instance.chassis_number and not instance.document:
#             try:
#                 doc = Document.objects.get(
#                     engine_number=instance.engine_number,
#                     chassis_number=instance.chassis_number,
#                     car__isnull=True
#                 )
#                 instance.document = doc
#                 instance.save(update_fields=['document'])
#                 print(f"سند {doc.id} به خودرو {instance.acceptance_number} وصل شد (سیگنال)")
#             except Document.DoesNotExist:
#                 print("سندی با این مشخصات پیدا نشد (سیگنال CarEntry)")
#             except Document.MultipleObjectsReturned:
#                 print("چند سند با این مشخصات پیدا شد، اتصال انجام نشد (سیگنال CarEntry)")
#
#     transaction.on_commit(_connect_car)

@receiver(post_save, sender=CarEntry)
def connect_car_to_document(sender, instance, created, **kwargs):
    def _connect_car():
        print(f"سیگنال CarEntry اجرا شد برای {instance.acceptance_number}")
        print(f"شماره موتور فعلی: {instance.engine_number}, شماره شاسی فعلی: {instance.chassis_number}")

        if instance.engine_number and instance.chassis_number:
            current_doc = instance.document

            if created and not current_doc:
                try:
                    doc = Document.objects.get(
                        engine_number=instance.engine_number,
                        chassis_number=instance.chassis_number,
                        car__isnull=True
                    )
                    CarEntry.objects.filter(id=instance.id).update(document=doc)
                    Document.objects.filter(id=doc.id).update(car=instance)
                    print(f"سند {doc.id} به خودرو {instance.acceptance_number} وصل شد")
                except Document.DoesNotExist:
                    print("سندی با این مشخصات پیدا نشد")
                    print(f"جستجو برای: engine_number={instance.engine_number}, chassis_number={instance.chassis_number}, car__isnull=True")
                except Document.MultipleObjectsReturned:
                    print("چند سند با این مشخصات پیدا شد، اتصال انجام نشد")

            elif not created:  # تغییر: همیشه بررسی سند جدید حتی اگر current_doc باشد
                if current_doc and (
                    current_doc.engine_number != instance.engine_number or
                    current_doc.chassis_number != instance.chassis_number
                ):
                    Document.objects.filter(id=current_doc.id).update(car=None)
                    CarEntry.objects.filter(id=instance.id).update(document=None)
                    print("ارتباط با سند قبلی قطع شد")

                try:
                    new_doc = Document.objects.get(
                        engine_number=instance.engine_number,
                        chassis_number=instance.chassis_number,
                        car__isnull=True
                    )
                    CarEntry.objects.filter(id=instance.id).update(document=new_doc)
                    Document.objects.filter(id=new_doc.id).update(car=instance)
                    print(f"سند جدید {new_doc.id} به خودرو {instance.acceptance_number} وصل شد")
                except Document.DoesNotExist:
                    print("سند جدیدی با این مشخصات پیدا نشد")
                    print(f"جستجو برای: engine_number={instance.engine_number}, chassis_number={instance.chassis_number}, car__isnull=True")
                except Document.MultipleObjectsReturned:
                    print("چند سند با این مشخصات پیدا شد، به سند جدید متصل نشد")

    transaction.on_commit(_connect_car)

@receiver(post_save, sender=Document)
def connect_document_to_car(sender, instance, created, **kwargs):
    def _connect_document():
        print(f"سیگنال Document اجرا شد برای سند {instance.id}")
        print(f"شماره موتور فعلی: {instance.engine_number}, شماره شاسی فعلی: {instance.chassis_number}")

        if instance.engine_number and instance.chassis_number:
            current_car = instance.car

            # اگر سند تازه ایجاد شده و خودرو ندارد
            if created and not current_car:
                try:
                    new_car = CarEntry.objects.get(
                        engine_number=instance.engine_number,
                        chassis_number=instance.chassis_number,
                        document__isnull=True
                    )
                    Document.objects.filter(id=instance.id).update(car=new_car)
                    CarEntry.objects.filter(id=new_car.id).update(document=instance)
                    print(f"سند {instance.id} به خودرو {new_car.acceptance_number} وصل شد")
                except CarEntry.DoesNotExist:
                    print("خودرویی با این مشخصات پیدا نشد")
                    print(f"جستجو برای: engine_number={instance.engine_number}, chassis_number={instance.chassis_number}, document__isnull=True")
                except CarEntry.MultipleObjectsReturned:
                    print("چند خودرو با این مشخصات پیدا شد، اتصال انجام نشد")

            # اگر سند به‌روزرسانی شده
            elif not created:
                # قطع ارتباط با خودرو فعلی در صورت ناهماهنگی
                if current_car and (
                    current_car.engine_number != instance.engine_number or
                    current_car.chassis_number != instance.chassis_number
                ):
                    CarEntry.objects.filter(id=current_car.id).update(document=None)
                    Document.objects.filter(id=instance.id).update(car=None)
                    print("ارتباط با خودرو قبلی قطع شد")

                # اتصال به خودرو جدید
                try:
                    new_car = CarEntry.objects.get(
                        engine_number=instance.engine_number,
                        chassis_number=instance.chassis_number,
                        document__isnull=True
                    )
                    Document.objects.filter(id=instance.id).update(car=new_car)
                    CarEntry.objects.filter(id=new_car.id).update(document=instance)
                    print(f"سند {instance.id} به خودرو {new_car.acceptance_number} وصل شد")
                except CarEntry.DoesNotExist:
                    print("خودرویی با این مشخصات پیدا نشد")
                    print(f"جستجو برای: engine_number={instance.engine_number}, chassis_number={instance.chassis_number}, document__isnull=True")
                except CarEntry.MultipleObjectsReturned:
                    print("چند خودرو با این مشخصات پیدا شد، اتصال انجام نشد")

    transaction.on_commit(_connect_document)
# @receiver(post_save, sender=Document)
# def connect_document_to_car(sender, instance, created, **kwargs):
#     def _connect_document():
#         print(f"سیگنال Document اجرا شد برای id={instance.id}")
#         if instance.engine_number and instance.chassis_number and not instance.car:
#             try:
#                 car = CarEntry.objects.get(
#                     engine_number=instance.engine_number,
#                     chassis_number=instance.chassis_number,
#                     document__isnull=True
#                 )
#                 instance.car = car
#                 instance.save(update_fields=['car'])
#                 print(f"خودرو {car.acceptance_number} به سند {instance.id} وصل شد (سیگنال)")
#             except CarEntry.DoesNotExist:
#                 print("خودرویی با این مشخصات پیدا نشد (سیگنال Document)")
#             except CarEntry.MultipleObjectsReturned:
#                 print("چند خودرو با این مشخصات پیدا شد، اتصال انجام نشد (سیگنال Document)")
#
#     transaction.on_commit(_connect_document)