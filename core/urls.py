from django.urls import path
from . import views

urlpatterns = [
    
    # Principales
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path("logout/", views.logout_view, name="logout"),
    
    # AJAX
    path("ajax/courses/", views.ajax_courses, name="ajax_courses"),
    
    # Taxi
    path('taxi/profile', views.taxi_profile, name='taxi_profile'),
    path('taxi/payment/', views.taxi_payment, name='taxi_payment'),
    path('taxi/payment/callback/', views.taxi_payment_callback, name='taxi_payment_callback'),
    path('taxi/dashboard', views.taxi_dashboard, name='taxi_dashboard'),
    path('taxi/car', views.taxi_car, name='taxi_car'),
    path('taxi/courses', views.taxi_courses, name='taxi_courses'),
    path('taxi/service/client', views.taxi_service_client, name='taxi_service_client'),
    path("taxi/solde/", views.taxi_solde, name="taxi_solde"),

    # Client
    path('client/', views.client_dashboard, name='client_dashboard'),
    path('client/commander-taxi/', views.commander_taxi, name='commander_taxi'),
    path('taxi/proposer-course/<int:course_id>/', views.proposer_course, name='proposer_course'),
    path('client/propositions/', views.client_all_propositions, name='client_all_propositions'),
    path('client/course/<int:course_id>/accepter/', views.accepter_course, name='accepter_course'),
    path('client/course/<int:course_id>/payment/', views.client_pay_course, name='client_pay_course'),
    path('client/course/payment/callback/', views.client_course_payment_callback, name='client_course_payment_callback'),
    path('client/courses-valides/', views.client_courses_valides, name='client_courses_valides'),
    path('course/<int:course_id>/supprimer/', views.supprimer_course, name='supprimer_course'),
    path('client/service-client/', views.service_client, name='service_client'),
    path('client/historique/', views.historique_client, name='historique_client'),
    path('client/recherche/', views.client_search_coiffeuse, name='client_search_coiffeuse'),

    # Coiffeuse
    path('coiffeuse/dashboard/', views.coiffeuse_dashboard, name='coiffeuse_dashboard'),
    path('coiffeuse/infos/', views.coiffeuse_infos, name='coiffeuse_infos'),
    path('coiffeuse/payment/', views.coiffeuse_payment, name='coiffeuse_payment'),
    path('coiffeuse/payment/callback/', views.coiffeuse_payment_callback, name='coiffeuse_payment_callback'),
    path('toggle-availability/', views.toggle_availability, name='toggle_availability'),
    path('prestations/', views.coiffeuse_prestations, name='coiffeuse_prestations'),
    path('coiffeuse/service/client/', views.coiffeuse_service_client, name='coiffeuse_service_client'),
     
    
    # Admin
    path('adminis/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('adminis/payer-course/<int:course_id>/', views.payer_course, name='payer_course'),
]