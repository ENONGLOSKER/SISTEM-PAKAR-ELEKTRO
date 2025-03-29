from django import forms
from .models import Gejala

class GejalaForm(forms.ModelForm):
    class Meta:
        model = Gejala
        fields = ['jenis_elektronik', 'kodeGjl', 'nama', 'deskripsi']
