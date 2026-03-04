# services.py
from sumup import Sumup
from sumup.checkouts.resource import CreateCheckoutBody
import os
from .models import Payment
import uuid
import requests

def create_sumup_checkout(user):
    
    
    client = Sumup(api_key=os.getenv("SUMUP_API_KEY"))
    merchant_code = os.getenv("SUMUP_MERCHANT_CODE")

    if not merchant_code:
        raise ValueError("MERCHANT_CODE non défini")

    checkout_reference = str(uuid.uuid4())  # identifiant unique
    
     # Déterminer montant et description selon rôle
    if user.role == "taxi":
        amount = 5.0
        description = "Inscription Taxi BelAfriGo"
        redirect_url = "http://127.0.0.1:8000/taxi/payment/callback/"
    elif user.role == "coiffeuse":
        amount = 5.0
        description = "Inscription Coiffeuse BelAfriGo"
        redirect_url = "http://127.0.0.1:8000/coiffeuse/payment/callback/"
    else:
        raise ValueError("Rôle non pris en charge pour paiement")

    checkout = client.checkouts.create(
        CreateCheckoutBody(
            merchant_code=merchant_code,
            amount=amount,
            currency="EUR",
            checkout_reference=checkout_reference,
            description=description,
            redirect_url=redirect_url
        )
    )

    Payment.objects.create(
        user=user,
        role=user.role,
        amount=amount,
        status="pending",
        checkout_id=checkout.id
    )

    return checkout.id


def get_checkout_raw(checkout_id):
    """
    Récupère le checkout SumUp en JSON brut (ignore la validation Pydantic)
    """
    api_key = os.getenv("SUMUP_API_KEY")
    url = f"https://api.sumup.com/v0.1/checkouts/{checkout_id}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    checkout_json = resp.json()

    # Normalisation entry_mode
    for tx in checkout_json.get("transactions", []):
        if "entry_mode" in tx:
            tx["entry_mode"] = tx["entry_mode"].lower().replace("_", " ")

    return checkout_json


def create_sumup_checkout_course(client_user, course):
    """
    Crée un checkout SumUp pour le client pour payer le prix proposé par le taxi
    """
    client = Sumup(api_key=os.getenv("SUMUP_API_KEY"))
    merchant_code = os.getenv("SUMUP_MERCHANT_CODE")
    if not merchant_code:
        raise ValueError("MERCHANT_CODE non défini")

    if not course.prix_propose:
        raise ValueError("Prix non défini pour cette course")

    checkout_reference = str(uuid.uuid4())

    checkout = client.checkouts.create(
        CreateCheckoutBody(
            merchant_code=merchant_code,
            amount=float(course.prix_propose),
            currency="EUR",
            checkout_reference=checkout_reference,
            description=f"Course Taxi BelAfriGo #{course.id}",
            redirect_url="http://127.0.0.1:8000/client/course/payment/callback/"
        )
    )

    Payment.objects.create(
        user=client_user,
        role="client",
        amount=float(course.prix_propose),
        status="pending",
        checkout_id=checkout.id,
        course=course   # si ton modèle Payment a un FK vers Course
    )

    return checkout.id


