"""
URL configuration for expert_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from expert_system_app import views

urlpatterns = [
    # AUTH
    path('admin/', admin.site.urls),
    path('signin/', views.signin_form, name='signin'),
    path('signout/', views.signin_form, name='signout'),
    #DASHBOARD
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    #GEJALA
    path('dashboard/gejala/', views.dsb_gejala, name='gejala'),
    path('dashboard/gejala/add', views.tambah_gejala, name='tambah_gejala'),
    path('dashboard/gejala/edit', views.edit_gejala, name='edit_gejala'),
    path('dashboard/gejala/delete', views.hapus_gejala, name='hapus_gejala'),
    path('dashboard/gejala/delete/multiple', views.hapus_gejala_multiple, name='hapus_gejala_multiple'),
    path('dashboard/gejala/filter_gejala', views.filter_gejala, name='filter_gejala'),
    path('import/gejala/', views.import_gejala, name='import_gejala'),
    # JENIS ELEKTRONIK
    path('dashboard/jenis/elektronik/', views.dsb_jenisE, name='jenisE'),
    path('dashboard/jenis/add', views.tambah_jenis, name='tambah_jenis'),
    path('dashboard/jenis/edit', views.edit_jenis, name='edit_jenis'),
    path('dashboard/jenis/delete', views.hapus_jenis, name='hapus_jenis'),
    path('dashboard/jenis/delete/multiple', views.hapus_jenis_multiple, name='hapus_jenis_multiple'),
    # KERUSAKAN
    path('dashboard/kerusakan/', views.dsb_kerusakan, name='kerusakan'),
    path('dashboard/kerusakan/add', views.tambah_kerusakan, name='tambah_kerusakan'),
    path('dashboard/kerusakan/edit', views.edit_kerusakan, name='edit_kerusakan'),
    path('dashboard/kerusakan/delete', views.hapus_kerusakan, name='hapus_kerusakan'),
    path('dashboard/kerusakan/delete/multiple', views.hapus_kerusakan_multiple, name='hapus_kerusakan_multiple'),
    path('dashboard/kerusakan/filter_kerusakan', views.filter_kerusakan, name='filter_kerusakan'),
    path('import/kerusakan/', views.import_kerusakan, name='import_kerusakan'),
    # ATURAN
    path('dashboard/aturan/', views.dsb_aturan, name='aturan'),
    path('dashboard/aturan/add', views.tambah_aturan, name='tambah_aturan'),
    path('dashboard/aturan/edit', views.edit_aturan, name='edit_aturan'),
    path('dashboard/aturan/delete', views.hapus_aturan, name='hapus_aturan'),
    path('dashboard/aturan/delete/multiple', views.hapus_aturan_multiple, name='hapus_aturan_multiple'),
    path('dashboard/aturan/filter_aturan', views.filter_aturan, name='filter_aturan'),
    path('get_gejala_kerusakan/', views.get_gejala_kerusakan, name='get_gejala_kerusakan'),
    path('get_aturan/<int:aturan_id>/', views.get_aturan, name='get_aturan'),
    # SOLUSI
    path('dashboard/solusi/', views.dsb_solusi, name='dsb_solusi'),
    path('dashboard/solusi/edit/<int:id>/', views.edit_solusi, name='edit_solusi'),
    path('dashboard/solusi/add', views.tambah_solusi, name='tambah_solusi'),
    path('dashboard/solusi/delete', views.hapus_solusi, name='hapus_solusi'),
    path('dashboard/solusi/delete/multiple', views.hapus_solusi_multiple, name='hapus_solusi_multiple'),
    path('dashboard/solusi/filter/', views.filter_solusi, name='filter_solusi'),
    # api
    path("dashboard/api/jenis-elektronik/", views.get_jenis_elektronik),
    path("dashboard/api/gejala/<int:jenis_id>/", views.get_gejala),
    path("dashboard/api/diagnosa/", views.diagnose),
    path('dashboard/histori/delete/multiple', views.hapus_histori_multiple, name='hapus_histori_multiple'),
    path('dashboard/api/visualization/', views.get_visualization_data, name='get_visualization_data'),
    path('dashboard/api/diagnosis-visualization/', views.get_diagnosis_pie_data, name='get_diagnosis_pie_data'),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
