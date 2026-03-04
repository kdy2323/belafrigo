from django import forms
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

class User(AbstractUser):
    ROLE_CHOICES = (
        ('client', 'Client'),
        ('coiffeuse', 'Coiffeuse'),
        ('taxi', 'Taxi'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

# Table spécifique pour les taxis
class Taxi(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='taxi')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    # Voiture
    marque = models.CharField(max_length=50, blank=True, null=True)
    modele = models.CharField(max_length=50, blank=True, null=True)
    couleur = models.CharField(max_length=30, blank=True, null=True)
    # Paiement
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - Taxi"
    
    

class Payment(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20)
    amount = models.FloatField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    checkout_id = models.CharField(max_length=100, blank=True, null=True)  # obligatoire pour retrouver
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    course = models.ForeignKey("Course", null=True, blank=True, on_delete=models.CASCADE)
    
class Voiture(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='voiture')
    marque = models.CharField(max_length=50)
    modele = models.CharField(max_length=50)
    couleur = models.CharField(max_length=30)

    def __str__(self):
        return f"{self.marque} {self.modele} ({self.couleur})"
    
    
class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Client - {self.user.username}"



class Course(models.Model):

    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('proposed', 'Proposition taxi'),
        ('accepted', 'Acceptée'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée'),
    )

    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='courses')
    taxi = models.ForeignKey('Taxi', on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')

    adresse_depart = models.CharField(max_length=255)
    adresse_arrivee = models.CharField(max_length=255)

    prix_propose = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    temps_arrivee = models.CharField(max_length=50, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    temps_arrivee = models.CharField(max_length=50, null=True, blank=True)
    arrivee_estimee = models.DateTimeField(null=True, blank=True)
    
    paiement_admin = models.BooleanField(default=False) 

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Course {self.id} - {self.client.user.username}"
    

class Proposition(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="propositions")
    taxi = models.ForeignKey(Taxi, on_delete=models.CASCADE)

    prix_propose = models.DecimalField(max_digits=8, decimal_places=2)
    temps_arrivee = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Proposition {self.taxi.user.username} - Course {self.course.id}"
    
    
    
class Coiffeuse(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='coiffeuse')
    salon_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    
    
    BELGIUM_CITY_CHOICES = [
        ("bruxelles", "Bruxelles"),
        ("anvers", "Anvers"),
        ("gand", "Gand"),
        ("charleroi", "Charleroi"),
        ("liege", "Liège"),
        ("namur", "Namur"),
        ("mons", "Mons"),
        ("bruge", "Bruges"),
        ("louvain", "Louvain"),
        ("malines", "Malines"),
        ("aalst", "Alost"),
        ("hasselt", "Hasselt"),
        ("kortrijk", "Courtrai"),
        ("ostende", "Ostende"),
        ("la_louviere", "La Louvière"),
    ]
    
    # 🔹 Ville en liste déroulante
    ville = models.CharField(
        max_length=50,
        choices=BELGIUM_CITY_CHOICES,
        blank=True,
        null=True
    )
    
    is_available = models.BooleanField(default=True, help_text="Indique si la coiffeuse est disponible pour des propositions")
    
    # Nouveau champ pour les services
    SERVICE_CHOICES = [
        ("coiffure", "Coiffure"),
        ("manicure_pedicure", "Manicure & Pédicure"),
        ("pose_cils", "Pose cils"),
        ("maquillage", "Maquillage"),
    ]
    services = models.CharField(max_length=255, blank=True, null=True, help_text="Selectionnez un ou plusieurs services proposés par la coiffeuse (ex: coiffure, manicure_pedicure, pose_cils, maquillage)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 🔹 NOUVEAUX CHAMPS
    instagram_link = models.URLField(blank=True, null=True)
    website_or_tiktok_link = models.URLField(blank=True, null=True)
    wants_website = models.BooleanField(default=False)

    def __str__(self):
        return f"Coiffeuse - {self.user.username}"
    
    def get_services_list(self):
        if self.services:
            return self.services.split(",")  # suppose que les services sont stockés sous forme de chaîne séparée par des virgules
        return []
    
    
    