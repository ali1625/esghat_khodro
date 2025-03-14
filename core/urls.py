from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register_user, name='register_user'),
    path('add_car_entry_step1/', views.add_car_entry_step1, name='add_car_entry_step1'),
    path('add-car-parts-form/', views.add_car_parts_step2, name='add_car_parts_step2'),
    path('add-car-parts/<str:acceptance_number>/', views.add_car_parts_step2, name='add_car_parts_step2'),
    path('add-car-costs-form/<str:acceptance_number>/', views.add_car_costs_step3, name='add_car_costs_step3'),  # جدید
    path('edit-car-entry/<str:acceptance_number>/', views.edit_car_entry, name='edit_car_entry'),
    path('edit-car-parts/<str:acceptance_number>/', views.edit_car_parts, name='edit_car_parts'),
    path('edit-car-costs/<str:acceptance_number>/', views.edit_car_costs, name='edit_car_costs'),
    path('car-details/<str:acceptance_number>/', views.car_details, name='car_details'),
    path('registration-list/', views.registration_list, name='registration_list'),  # تغییر از combined_list
    path('check_status/<str:acceptance_number>/', views.check_status, name='check_status'),
    path('select_car_for_parts/', views.select_car_for_parts, name='select_car_for_parts'),  # مسیر جدید
    path('select_car_for_costs/', views.select_car_for_costs, name='select_car_for_costs'),
    # path('', views.registration_list, name='registration_list'),
    path('change_password/', views.change_password, name='change_password'),
    path('update-password/', views.update_password, name='update_password'),

    #لاگ ویرایش
    path('edit-logs/', views.edit_logs, name='edit_logs'),
    path('edit-logs/<str:acceptance_number>/', views.edit_logs, name='edit_logs'),
    #مدیریت کاربران
    path('user-management/', views.user_management, name='user_management'),
    path('user/<int:user_id>/change-password/', views.admin_change_password, name='admin_change_password'),
    path('user/<int:user_id>/edit-profile/', views.edit_user_profile, name='edit_user_profile'),
    path('add-user/', views.add_user, name='add_user'),

    path('finalize/<str:acceptance_number>/', views.finalize_registration, name='finalize_registration'),
    path('finalized-list/', views.finalized_list, name='finalized_list'),
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=True)),

    path('add_document', views.add_document, name='add_document'),
    path('documents/', views.document_list, name='document_list'),

    path('edit_document/<int:pk>/', views.edit_document, name='edit_document'),

]



