from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Coiffeuse

class RegisterForm(UserCreationForm):

    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'password1', 'password2']
        
        
        
        
class CoiffeuseForm(forms.ModelForm):
    
    services = forms.MultipleChoiceField(
        choices=Coiffeuse.SERVICE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = Coiffeuse
        fields = ['salon_name', 'address', 'ville', 'services', 'phone_number']
        widgets = {
            'salon_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'ville': forms.Select(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
        
    def clean_services(self):
        """
        Transforme la liste des services choisis en CSV pour le stockage.
        """
        services = self.cleaned_data.get('services', [])
        return ','.join(services)
    
    
class CoiffeusePrestationsForm(forms.ModelForm):
    
    class Meta:
        model = Coiffeuse
        fields = ['instagram_link', 'website_or_tiktok_link', 'wants_website']
        widgets = {
            'instagram_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://instagram.com/...'}),
            'website_or_tiktok_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'wants_website': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }