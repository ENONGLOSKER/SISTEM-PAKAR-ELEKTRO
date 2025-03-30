from django.contrib import admin
from . models import Gejala, JenisElektronik, Kerusakan,Aturan, Diagnosa, Solusi
# Register your models here.
admin.site.register(Gejala)
admin.site.register(JenisElektronik)
admin.site.register(Kerusakan)
admin.site.register(Aturan)
admin.site.register(Diagnosa)
admin.site.register(Solusi)
