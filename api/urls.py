from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Incidents
    path('incidents/',             views.incident_list,   name='incident-list'),
    path('incidents/<int:pk>/',    views.incident_detail, name='incident-detail'),
    path('incidents/bulk/',        views.incident_bulk,   name='incident-bulk'),

    # Forgot Password
    path('forgot-password/', views.forgot_password, name='forgot-password'),
    path('verify-otp/',      views.verify_otp,      name='verify-otp'),
    path('reset-password/',  views.reset_password,  name='reset-password'),
]