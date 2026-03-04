from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .services import create_sumup_checkout, create_sumup_checkout_course
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.http import HttpResponseRedirect
from .forms import RegisterForm, CoiffeuseForm, CoiffeusePrestationsForm
from pydantic import BaseModel, BeforeValidator
from django.db.models import Exists, OuterRef
from typing_extensions import Annotated
from django.db.models import Sum
from django.core.mail import send_mail
from typing import Any
from .models import Payment, Proposition, User, Voiture, Taxi, Client, Course, Coiffeuse
from django.contrib.admin.views.decorators import staff_member_required
from sumup import Sumup
from django.utils import timezone
from datetime import timedelta
import os


def home(request):
    return render(request, 'home.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect("home")


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            
            role = user.role

            if role == 'taxi':
                return redirect('taxi_payment')
            
            elif role == 'client':
                return redirect('client_dashboard')
            
            elif role == 'coiffeuse':
                return redirect('coiffeuse_dashboard')

    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


def user_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # redirection selon rôle
            if user.role == 'client':
                return redirect('client_dashboard')
            elif user.role == 'coiffeuse':
                return redirect('coiffeuse_dashboard')
            elif user.role == 'taxi':
                return redirect('taxi_dashboard')
            elif user.is_staff:
                return redirect('admin_dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

#----------------------
#        TAXI
#----------------------

@login_required
def taxi_payment(request):
    checkout_id = create_sumup_checkout(request.user)
    return render(request, 'taxi/taxi_payment.html', {'checkout_id': checkout_id})


from .services import get_checkout_raw

@login_required
def taxi_payment_callback(request):
    checkout_id = request.GET.get("checkout_id")
    if not checkout_id:
        return HttpResponse("Erreur : checkout_id manquant")

    checkout_json = get_checkout_raw(checkout_id)
    if not checkout_json:
        return HttpResponse("Erreur API paiement")

    try:
        payment = Payment.objects.get(checkout_id=checkout_id)
    except Payment.DoesNotExist:
        return HttpResponse("Paiement introuvable.")

    checkout_status = checkout_json.get("status", "").lower()
    if checkout_status in ["paid", "success", "completed"]:
        payment.status = "success"
        payment.save()
        return redirect("taxi_dashboard")
    else:
        payment.status = "failed"
        payment.save()
        return HttpResponse(f"Paiement non validé. Statut reçu: {checkout_status}, {checkout_json}")
    

@login_required
def taxi_dashboard(request):
    if request.user.role != "taxi":
        return redirect("home")

    taxi = get_object_or_404(Taxi, user=request.user)
    
    if not taxi.phone_number:
        messages.warning(request, "Veuillez compléter votre profil avant de proposer des courses.")
        return redirect("taxi_profile")

    payments = Payment.objects.filter(user=request.user).order_by("-created_at")
    latest_payment = payments.first()
    is_paid = latest_payment and latest_payment.status == "success"

   # IDs des courses déjà proposées par ce taxi
    proposed_ids = Proposition.objects.filter(taxi=taxi).values_list("course_id", flat=True)

     # Courses pending que ce taxi n'a pas encore proposées
    courses_to_propose = Course.objects.filter(status="pending").exclude(id__in=proposed_ids).order_by("-created_at")

    return render(request, "taxi/taxi_dashboard.html", {
        "taxi": taxi,
        "payments": payments,
        "is_paid": is_paid,
        "courses": courses_to_propose,  # seulement celles à proposer
    })
    
@login_required
def taxi_profile(request):
    taxi, created = Taxi.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        
        if not phone_number:
            messages.error(request, "Veuillez entrer votre numéro de téléphone avant de continuer.")
            return redirect('taxi_profile')
        
        request.user.username = request.POST.get('username')
        request.user.email = request.POST.get('email')
        request.user.save()

        taxi.phone_number = phone_number
        taxi.save()
        
        
        return redirect('taxi_profile')
    return render(request, 'taxi/taxi_profile.html', {'taxi': taxi})

@login_required
def taxi_car(request):
    taxi, created = Taxi.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        taxi.marque = request.POST.get('marque')
        taxi.modele = request.POST.get('modele')
        taxi.couleur = request.POST.get('couleur')
        taxi.save()
        return redirect('taxi_car')
    return render(request, 'taxi/taxi_car.html', {'taxi': taxi})

@login_required
def proposer_course(request, course_id):

    taxi = get_object_or_404(Taxi, user=request.user)
    course = get_object_or_404(Course, id=course_id, status="pending")

    if request.method == "POST":

        # Empêcher double proposition
        if not Proposition.objects.filter(course=course, taxi=taxi).exists():

            Proposition.objects.create(
                course=course,
                taxi=taxi,
                prix_propose=request.POST.get("prix"),
                temps_arrivee=request.POST.get("temps"),
            )

    return redirect("taxi_dashboard")


from .models import Proposition

from django.utils import timezone
from datetime import timedelta

@login_required
def taxi_courses(request):
    taxi = get_object_or_404(Taxi, user=request.user)

    # Propositions envoyées (avant acceptation)
    propositions = Proposition.objects.filter(
        taxi=taxi,
        course__status="pending"
    ).select_related("course")

    # Courses acceptées (en attente paiement ou payées)
    courses_pending = Course.objects.filter(
        taxi=taxi,
        status__in=['accepted', 'paid']
    )

    # Calculer arrivee_estimee si absent
    for course in courses_pending:
        if not course.arrivee_estimee and course.temps_arrivee:
            try:
                minutes = int(course.temps_arrivee)
                course.arrivee_estimee = timezone.now() + timedelta(minutes=minutes)
                course.save()
            except ValueError:
                course.arrivee_estimee = timezone.now()

    # Courses payées confirmées
    courses_confirmed = Course.objects.filter(
        taxi=taxi,
        status='paid'
    )

    return render(request, "taxi/taxi_courses.html", {
        "propositions": propositions,
        "courses_pending": courses_pending,
        "courses_confirmed": courses_confirmed,
    })


@login_required
def taxi_service_client(request):
    return render(request, "taxi/taxi_service_client.html")


@login_required
def taxi_solde(request):
    if request.user.role != "taxi":
        return redirect("home")

    taxi = get_object_or_404(Taxi, user=request.user)

    # Courses payées par client
    courses_paid = Course.objects.filter(
        taxi=taxi,
        status="paid"
    )

    # 💰 A recevoir (non validées admin)
    courses_a_recevoir = courses_paid.filter(paiement_admin=False)

    # ✅ Déjà reçues (validées admin)
    courses_recues = courses_paid.filter(paiement_admin=True)

    solde_a_recevoir = courses_a_recevoir.aggregate(
        total=Sum("prix_propose")
    )["total"] or 0

    solde_recu = courses_recues.aggregate(
        total=Sum("prix_propose")
    )["total"] or 0

    return render(request, "taxi/taxi_solde.html", {
        "taxi": taxi,
        "courses_a_recevoir": courses_a_recevoir,
        "courses_recues": courses_recues,
        "solde_a_recevoir": solde_a_recevoir,
        "solde_recu": solde_recu,
    })

#---------------------
#      CLIENT
#---------------------

@login_required
def client_dashboard(request):
    return render(request, 'client/client_dashboard.html')

@login_required
def commander_taxi(request):
    client, created = Client.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        depart = request.POST.get('adresse_depart')
        arrivee = request.POST.get('adresse_arrivee')

        Course.objects.create(
            client=client,
            adresse_depart=depart,
            adresse_arrivee=arrivee,
        )

        return redirect('client_dashboard')

    return render(request, 'client/commander_taxi.html')

def client_all_propositions(request):
    client = request.user.client
    courses = Course.objects.filter(
    client=client,
    status="pending"
    ).prefetch_related("propositions")

    return render(request, "client/all_propositions.html", {
        "courses": courses
    })

@login_required
def accepter_course(request, course_id):
    client_user = request.user
    course = get_object_or_404(Course, id=course_id, client__user=client_user)
    if course.status != "pending":
        return redirect("client_dashboard")

    if request.method == "POST":
        proposition_id = request.POST.get("proposition_id")
        proposition = get_object_or_404(Proposition, id=proposition_id, course=course)

        course.taxi = proposition.taxi
        course.prix_propose = proposition.prix_propose
        course.temps_arrivee = proposition.temps_arrivee
        course.status = "accepted"
        course.save()

        checkout_id = create_sumup_checkout_course(client_user, course)
        return redirect('client_pay_course', course_id=course.id)

    return redirect('client_all_propositions')

@login_required
def client_pay_course(request, course_id):
    client_user = request.user
    course = get_object_or_404(Course, id=course_id, client__user=client_user)
    
  # Calcul de l'heure d'arrivée seulement si course.temps_arrivee est valide
    try:
        minutes = int(course.temps_arrivee)
        course.arrivee_estimee = timezone.now() + timedelta(minutes=minutes)
    except (TypeError, ValueError):
        course.arrivee_estimee = timezone.now()  # fallback si invalide

    course.save()

    payment = Payment.objects.filter(course=course).first()

    if not payment:
        checkout_id = create_sumup_checkout_course(client_user, course)
    else:
        checkout_id = payment.checkout_id

    return render(request, "client/client_course_payment.html", {"checkout_id": checkout_id})


@login_required
def client_course_payment_callback(request):
    checkout_id = request.GET.get("checkout_id")
    if not checkout_id:
        return redirect("client_dashboard")

    try:
        payment = Payment.objects.get(checkout_id=checkout_id)
    except Payment.DoesNotExist:
        return redirect("client_dashboard")

    checkout_json = get_checkout_raw(checkout_id)
    if not checkout_json:
        return redirect("client_dashboard")
    status = checkout_json.get("status", "").lower()

    if status in ["paid", "success", "completed"]:
        payment.status = "success"
        payment.save()

        # ⚡ Mettre à jour la course associée
        if payment.course:
            payment.course.status = "paid"
            payment.course.save()
            
            # ⚡ Mettre à jour la course associée
        if payment.course:
            course = payment.course
            course.status = "paid"
            
            # Calcul de l'heure d'arrivée
            if course.temps_arrivee:  # s'assure qu'on a bien un nombre
                try:
                    minutes = int(course.temps_arrivee)
                    course.arrivee_estimee = timezone.now() + timedelta(minutes=minutes)
                except ValueError:
                    # si temps_arrivee n'est pas un nombre valide
                    course.arrivee_estimee = timezone.now()
            else:
                course.arrivee_estimee = timezone.now()

            course.save()
    else:
        payment.status = "failed"
        payment.save()

    return redirect("client_courses_valides")


@login_required
def client_courses_valides(request):
    client = request.user.client
    courses = Course.objects.filter(client=client, status="paid").select_related("taxi")

    for course in courses:
        if not course.arrivee_estimee and course.temps_arrivee:
            try:
                minutes = int(course.temps_arrivee)
                course.arrivee_estimee = timezone.now() + timedelta(minutes=minutes)
                course.save()
            except ValueError:
                course.arrivee_estimee = timezone.now()

    return render(request, "client/client_courses_valides.html", {"courses": courses})


@login_required
def supprimer_course(request, course_id):
    client = request.user.client
    course = get_object_or_404(Course, id=course_id, client=client)

    if request.method == "POST":
        # Supprime toutes les propositions liées
        course.propositions.all().delete()
        # Supprime la course elle-même
        course.delete()
        return redirect('client_all_propositions')

    return redirect('client_all_propositions')


@login_required
def service_client(request):
    return render(request, "client/service_client.html")


@login_required
def historique_client(request):
    client = request.user.client  # On suppose que le modèle Client est lié à User

     # Paiements réussis seulement
    payments = Payment.objects.filter(user=request.user, status__in=["success", "paid"]).order_by("-created_at")

    # Courses payées seulement
    courses = Course.objects.filter(client=client, status="paid").order_by("-created_at")

    context = {
        'courses': courses,
        'payments': payments,
    }
    return render(request, 'client/historique.html', context)


@login_required
def client_search_coiffeuse(request):
    ville = request.GET.get("ville")
    coiffeuses = None

    if ville:
        coiffeuses = Coiffeuse.objects.filter(
            ville__iexact=ville,
            is_available=True
        )

    return render(request, "client/search_coiffeuse.html", {
        "coiffeuses": coiffeuses,
        "ville": ville,
        "cities":Coiffeuse.BELGIUM_CITY_CHOICES
    })


#---------------------------
#         AJAX
#---------------------------

@login_required
def ajax_courses(request):
    taxi = get_object_or_404(Taxi, user=request.user)

    proposed_ids = Proposition.objects.filter(taxi=taxi).values_list("course_id", flat=True)

    courses = Course.objects.filter(status="pending").exclude(id__in=proposed_ids).order_by("-created_at")

    data = []
    for course in courses:
        data.append({
            "id": course.id,
            "client": course.client.user.username,
            "pickup": course.adresse_depart,
            "destination": course.adresse_arrivee,
            "price": str(course.prix_propose) if course.prix_propose else "",
            "arrival_time": course.temps_arrivee if course.temps_arrivee else "",
            "created_at": course.created_at.strftime("%H:%M:%S")
        })

    return JsonResponse({"courses": data})


#---------------------------
#         ADMIN 
#---------------------------


@staff_member_required
def admin_dashboard(request):
    taxis = Taxi.objects.all()

    for taxi in taxis:
        # Toutes les courses payées par client
        courses_paid = Course.objects.filter(taxi=taxi, status='paid')

        # Courses encore à valider par admin
        courses_non_validees = courses_paid.filter(paiement_admin=False)

        # Calcul des soldes
        taxi.solde_a_recevoir = sum(c.prix_propose for c in courses_non_validees)
        taxi.solde_recu = sum(
            c.prix_propose for c in courses_paid.filter(paiement_admin=True)
        )

        # ⚠️ IMPORTANT : on envoie seulement celles non validées au template
        taxi.courses_a_payer = courses_non_validees

    return render(request, "admin/dashboard.html", {"taxis": taxis})


@staff_member_required
def payer_course(request, course_id):
    course = get_object_or_404(
        Course,
        id=course_id,
        status='paid',
        paiement_admin=False  # 👈 empêche double validation
    )

    course.paiement_admin = True
    course.save()

    return redirect('admin_dashboard')



#---------------------------
#       COIFFEUSE
#---------------------------

@login_required
def coiffeuse_dashboard(request):
    if request.user.role != "coiffeuse":
        return redirect("home")

    # Récupérer ou créer le profil coiffeuse
    coiffeuse, created = Coiffeuse.objects.get_or_create(user=request.user)

    # Vérifier que les infos essentielles sont remplies
    if not coiffeuse.salon_name or not coiffeuse.address or not coiffeuse.phone_number:
        messages.warning(request, "Veuillez compléter vos informations avant d'accéder au dashboard.")
        return redirect("coiffeuse_infos")

    # Vérifier si la coiffeuse a payé
    payments = Payment.objects.filter(user=request.user, role="coiffeuse").order_by("-created_at")
    latest_payment = payments.first()
    is_paid = latest_payment and latest_payment.status == "success"

    if not is_paid:
        messages.warning(request, "Vous devez compléter le paiement pour accéder au dashboard.")
        return redirect("coiffeuse_payment")


    return render(request, "coiffeuse/coiffeuse_dashboard.html", {
        "coiffeuse": coiffeuse,
        "payments": payments,
        "is_paid": is_paid,
    })

@login_required
def coiffeuse_payment(request):
    checkout_id = create_sumup_checkout(request.user)
    return render(request, 'coiffeuse/coiffeuse_payment.html', {'checkout_id': checkout_id})


@login_required
def coiffeuse_payment_callback(request):
    checkout_id = request.GET.get("checkout_id")
    if not checkout_id:
        return HttpResponse("Erreur : checkout_id manquant")

    checkout_json = get_checkout_raw(checkout_id)
    if not checkout_json:
        return HttpResponse("Erreur API paiement")

    try:
        payment = Payment.objects.get(checkout_id=checkout_id)
    except Payment.DoesNotExist:
        return HttpResponse("Paiement introuvable.")

    checkout_status = checkout_json.get("status", "").lower()
    if checkout_status in ["paid", "success", "completed"]:
        payment.status = "success"
        payment.save()
        return redirect("coiffeuse_dashboard")
    else:
        payment.status = "failed"
        payment.save()
        return HttpResponse(f"Paiement non validé. Statut reçu: {checkout_status}, {checkout_json}")
    
    
@login_required
def coiffeuse_infos(request):
    """
    Page pour remplir ou modifier les informations de la coiffeuse.
    """
    try:
        coiffeuse = request.user.coiffeuse
    except Coiffeuse.DoesNotExist:
        coiffeuse = Coiffeuse(user=request.user)

    if request.method == 'POST':
        form = CoiffeuseForm(request.POST, instance=coiffeuse)
        if form.is_valid():
            form.save()
            return redirect('coiffeuse_dashboard')
    else:
        form = CoiffeuseForm(instance=coiffeuse)

    return render(request, 'coiffeuse/coiffeuse_infos.html', {'form': form})


@login_required
@require_POST
def toggle_availability(request):
    try:
        coiffeuse = request.user.coiffeuse
        coiffeuse.is_available = not coiffeuse.is_available
        coiffeuse.save()
        return JsonResponse({"status": "success", "is_available": coiffeuse.is_available})
    except Coiffeuse.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Profil coiffeuse introuvable."}, status=400)
    
    
@login_required
def coiffeuse_prestations(request):
    if request.user.role != "coiffeuse":
        return redirect("home")

    coiffeuse, created = Coiffeuse.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = CoiffeusePrestationsForm(request.POST, instance=coiffeuse)
        if form.is_valid():
            form.save()
            return redirect("coiffeuse_dashboard")
    else:
        form = CoiffeusePrestationsForm(instance=coiffeuse)

    return render(request, "coiffeuse/coiffeuse_prestations.html", {"form": form})
    
    
def coiffeuse_service_client(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")

        if name and email and message:
            try:
                send_mail(
                    subject=f"[Service Client Coiffeuse] Message de {name}",
                    message=f"Nom : {name}\nEmail : {email}\n\nMessage :\n{message}",
                    from_email="no-reply@belafrigo.be",
                    recipient_list=["bib.kendy17@gmail.be"],
                    fail_silently=False,
                )
                messages.success(request, "Votre message a été envoyé avec succès !")
                return redirect("coiffeuse_service_client")
            except Exception as e:
                messages.error(request, f"Erreur lors de l'envoi du message : {e}")
        else:
            messages.error(request, "Merci de remplir tous les champs.")

    return render(request, "coiffeuse/coiffeuse_service_client.html")