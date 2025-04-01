from django.shortcuts import render, get_object_or_404, redirect
from .models import JenisElektronik, Gejala, Kerusakan, Aturan, Diagnosa,DiagnosaKerusakan, Solusi
from django.db import models
from django.db.models import Count
from django.http import JsonResponse
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import pandas as pd
from django.core.files.storage import FileSystemStorage
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta

def index(request):
    return render(request, 'index.html')

# DASHBOARD ==================================
@login_required()
def dashboard(request):
    jenis = JenisElektronik.objects.count()
    gejala = Gejala.objects.count()
    kerusakan = Kerusakan.objects.count()
    aturan = Aturan.objects.count()
    solusi = Solusi.objects.count()

    diagnosa = Diagnosa.objects.all()
    diagnosa_terakhir = Diagnosa.objects.order_by('-tanggal_diagnosa').first()

    # Hitung akurasi rata-rata dari DiagnosaKerusakan
    akurasi_rata_rata = 0
    if diagnosa_terakhir:
        akurasi_values = diagnosa_terakhir.diagnosa_kerusakan.values_list('akurasi', flat=True)
        akurasi_rata_rata = sum(akurasi_values) / len(akurasi_values) if akurasi_values else 0

    context = {
        'jenis_count': jenis,
        'gejala_count': gejala,
        'kerusakan_count': kerusakan,
        'kerusakan_count': kerusakan,
        'aturan_count': aturan,
        'solusi_count': solusi,
        'diagnosa': diagnosa,
        'diagnosa_terakhir': diagnosa_terakhir,
        'akurasi_rata_rata': akurasi_rata_rata,
    }
    return render(request, 'dashboard.html', context)
# VISUALISASI DATA GRAFIK 
def get_diagnosis_pie_data(request):
    # Hitung jumlah diagnosa untuk setiap jenis elektronik
    diagnosis_data = (
        Diagnosa.objects.values('jenis_elektronik__nama')
        .annotate(count=Count('id'))
        .order_by('-count')  # Urutkan dari yang paling banyak
    )

    # Format data untuk frontend
    labels = [item['jenis_elektronik__nama'] for item in diagnosis_data]
    data = [item['count'] for item in diagnosis_data]

    return JsonResponse({
        "labels": labels,
        "data": data
    })
def get_visualization_data(request):
    # Hitung jumlah masing-masing kategori
    jenis_count = JenisElektronik.objects.count()
    gejala_count = Gejala.objects.count()
    kerusakan_count = Kerusakan.objects.count()

    # Kirim data sebagai JSON
    return JsonResponse({
        "jenis_elektronik": jenis_count,
        "gejala": gejala_count,
        "kerusakan": kerusakan_count
    })
# DIAGNOSIS 
def get_jenis_elektronik(request):
    jenis_list = JenisElektronik.objects.all().values("id", "nama")
    return JsonResponse(list(jenis_list), safe=False)
def get_gejala(request, jenis_id):
    gejala_list = Gejala.objects.filter(jenis_elektronik_id=jenis_id).values("id", "nama")
    return JsonResponse(list(gejala_list), safe=False)
@csrf_exempt
def diagnose(request):
    if request.method == "POST":
        data = json.loads(request.body)
        jenis_id = data.get("jenis_id")
        gejala_ids = data.get("gejala", [])

        if not jenis_id or not gejala_ids:
            return JsonResponse({"error": "Jenis elektronik dan gejala harus dipilih"}, status=400)

        # Inisialisasi fakta awal
        fakta_gejala = set(gejala_ids)
        fakta_kerusakan = set()
        hasil_diagnosa = {}

        # Iterasi Forward Chaining
        while True:
            aturan_terkait = Aturan.objects.filter(
                jenis_elektronik_id=jenis_id
            ).annotate(
                matched_gejala=Count('gejala', filter=models.Q(gejala__id__in=fakta_gejala), distinct=True),
                matched_kerusakan=Count('kerusakan_sebelumnya', filter=models.Q(kerusakan_sebelumnya__id__in=fakta_kerusakan), distinct=True),
                total_fakta=Count('gejala') + Count('kerusakan_sebelumnya')
            ).filter(
                models.Q(matched_gejala__gt=0) | models.Q(matched_kerusakan__gt=0)
            )

            if not aturan_terkait.exists():
                break

            baru_ditemukan = False
            for aturan in aturan_terkait:
                kerusakan = aturan.kerusakan
                if kerusakan.id not in fakta_kerusakan and kerusakan.id not in hasil_diagnosa:
                    total_fakta_aturan = aturan.total_fakta
                    matched_fakta = aturan.matched_gejala + aturan.matched_kerusakan
                    akurasi = round((matched_fakta / total_fakta_aturan) * 100, 2) if total_fakta_aturan > 0 else 0

                    hasil_diagnosa[kerusakan.id] = {
                        "nama": kerusakan.nama_kerusakan,
                        "akurasi": akurasi,
                        "solusi": None
                    }
                    fakta_kerusakan.add(kerusakan.id)
                    baru_ditemukan = True

            if not baru_ditemukan:
                break

        # Proses hasil diagnosa
        if hasil_diagnosa:
            kerusakan_ids = list(hasil_diagnosa.keys())
            solusi_dict = {s.kerusakan_id: s.nama_solusi for s in Solusi.objects.filter(kerusakan__id__in=kerusakan_ids, is_recommended=True)}

            # Isi solusi untuk setiap kerusakan
            for kerusakan_id, info in hasil_diagnosa.items():
                info["solusi"] = solusi_dict.get(kerusakan_id, "Tidak ada solusi yang tersedia")

            # Simpan diagnosa
            diagnosa = Diagnosa.objects.create(
                jenis_elektronik_id=jenis_id,
                catatan="Diagnosa otomatis dengan multiple kerusakan",
                solusi="\n".join([f"{v['nama']}: {v['solusi']}" for v in hasil_diagnosa.values()])
            )
            diagnosa.gejala.set(gejala_ids)

            # Simpan relasi DiagnosaKerusakan
            diagnosa_kerusakan_objects = [
                DiagnosaKerusakan(
                    diagnosa=diagnosa,
                    kerusakan_id=kerusakan_id,
                    akurasi=info["akurasi"]
                )
                for kerusakan_id, info in hasil_diagnosa.items()
            ]
            DiagnosaKerusakan.objects.bulk_create(diagnosa_kerusakan_objects)

            # Response ke client
            response = {
                "kerusakan": [{"nama": v["nama"], "akurasi": v["akurasi"], "solusi": v["solusi"]} for v in hasil_diagnosa.values()]
            }
            return JsonResponse(response)
        else:
            # Jika tidak ada hasil diagnosa
            diagnosa = Diagnosa.objects.create(
                jenis_elektronik_id=jenis_id,
                catatan="Tidak ditemukan kerusakan yang sesuai",
                solusi="Tidak ada solusi yang tersedia"
            )
            diagnosa.gejala.set(gejala_ids)

            return JsonResponse({
                "kerusakan": "Tidak ditemukan",
                "akurasi": 0,
                "solusi": "Tidak ada solusi yang tersedia"
            })

    return JsonResponse({"error": "Metode tidak diizinkan"}, status=405)
@login_required()
@csrf_exempt
def hapus_histori_multiple(request):
    if request.method == "POST":
        data = json.loads(request.body)
        ids = data.get("ids", [])

        if ids:
            Diagnosa.objects.filter(id__in=ids).delete()
            messages.success(request, "Data berhasil di hapus.")
            return JsonResponse({"message": "Data berhasil dihapus."}, status=200)
        return JsonResponse({"error": "Tidak ada data yang dipilih."}, status=400)

    return JsonResponse({"error": "Metode tidak valid."}, status=405)

# JENIS ELEKTRONIK ==================================
@login_required()
def dsb_jenisE(request):
    data = JenisElektronik.objects.all()
    context = {
        'jenis': data,
    }
    return render(request, 'dsb_jenisE.html', context)
def tambah_jenis(request):
    if request.method == "POST":
        nama = request.POST.get("nama")

        if JenisElektronik.objects.filter(nama=nama).exists():
            return JsonResponse({"status": "error", "message": "Jenis Elektronik sudah ada!"})

        JenisElektronik.objects.create(nama=nama)
        messages.success(request, "Data berhasil di tambah.")
        return JsonResponse({"status": "success", "message": "Data gejala berhasil ditambahkan!"})

    return JsonResponse({"status": "error", "message": "Metode tidak diperbolehkan!"})
def edit_jenis(request):
    if request.method == "POST":
        jenis_id = request.POST.get("id")
        nama = request.POST.get("nama")

        if not jenis_id:
            return JsonResponse({"status": "error", "message": "ID Gejala tidak ditemukan!"})

        jenis = get_object_or_404(JenisElektronik, id=jenis_id)

        # Perbarui data yang sudah ada
        jenis.nama = nama
        jenis.save()
        messages.success(request, "Data berhasil di edit.")
        return JsonResponse({"status": "success", "message": "Gejala berhasil diperbarui!"})

    return JsonResponse({"status": "error", "message": "Metode tidak diperbolehkan!"})
@csrf_exempt
def hapus_jenis(request):
    if request.method == "POST":
        data = json.loads(request.body)
        jenis_id = data.get("id")

        jenis = get_object_or_404(JenisElektronik, id=jenis_id)
        jenis.delete()

        messages.success(request, "Data berhasil di hapus.")
        return JsonResponse({"status": "success", "message": "Gejala berhasil dihapus!"})

    return JsonResponse({"status": "error", "message": "Metode tidak diperbolehkan!"})
@csrf_exempt
def hapus_jenis_multiple(request):
    if request.method == "POST":
        data = json.loads(request.body)
        ids = data.get("ids", [])

        if ids:
            JenisElektronik.objects.filter(id__in=ids).delete()
            messages.success(request, "Data berhasil di hapus.")
            return JsonResponse({"message": "Data berhasil dihapus."}, status=200)
        return JsonResponse({"error": "Tidak ada data yang dipilih."}, status=400)

    return JsonResponse({"error": "Metode tidak valid."}, status=405)

# GEJALA ============================================
@login_required()
def dsb_gejala(request):
    data = Gejala.objects.all().order_by('-id')
    jenis_elektronik_list = JenisElektronik.objects.all()
    context = {
        'gejala': data,
        "jenis_elektronik": jenis_elektronik_list
    }
    return render(request, 'dsb_gejala.html', context)
@login_required()
def tambah_gejala(request):
    if request.method == "POST":
        jenis_elektronik_id = request.POST.get("jenis_elektronik")
        kodeGjl = request.POST.get("kodeGjl")
        nama = request.POST.get("nama")
        deskripsi = request.POST.get("deskripsi")

        if Gejala.objects.filter(kodeGjl=kodeGjl).exists():
            return JsonResponse({"status": "error", "message": "Kode gejala sudah ada!"})
        jenis_elektronik = get_object_or_404(JenisElektronik, id=jenis_elektronik_id)
        Gejala.objects.create(
            jenis_elektronik=jenis_elektronik,
            kodeGjl=kodeGjl,
            nama=nama,
            deskripsi=deskripsi
        )
        messages.success(request, "Data berhasil di tambah.")
        return JsonResponse({"status": "success", "message": "Data gejala berhasil ditambahkan!"})

    return JsonResponse({"status": "error", "message": "Metode tidak diperbolehkan!"})
@login_required()
def edit_gejala(request):
    if request.method == "POST":
        gejala_id = request.POST.get("id")
        jenis_elektronik_id = request.POST.get("jenis_elektronik")
        kodeGjl = request.POST.get("kodeGjl")
        nama = request.POST.get("nama")
        deskripsi = request.POST.get("deskripsi")

        if not gejala_id:
            return JsonResponse({"status": "error", "message": "ID Gejala tidak ditemukan!"})

        gejala = get_object_or_404(Gejala, id=gejala_id)
        jenis_elektronik = get_object_or_404(JenisElektronik, id=jenis_elektronik_id)

        # Perbarui data yang sudah ada
        gejala.jenis_elektronik = jenis_elektronik
        gejala.kodeGjl = kodeGjl
        gejala.nama = nama
        gejala.deskripsi = deskripsi
        gejala.save()
        messages.success(request, "Data berhasil di edit.")
        return JsonResponse({"status": "success", "message": "Gejala berhasil diperbarui!"})

    return JsonResponse({"status": "error", "message": "Metode tidak diperbolehkan!"})
@login_required()
@csrf_exempt
def hapus_gejala(request):
    if request.method == "POST":
        data = json.loads(request.body)
        gejala_id = data.get("id")

        gejala = get_object_or_404(Gejala, id=gejala_id)
        gejala.delete()

        messages.success(request, "Data berhasil di hapus.")
        return JsonResponse({"status": "success", "message": "Gejala berhasil dihapus!"})

    return JsonResponse({"status": "error", "message": "Metode tidak diperbolehkan!"})
@login_required()
@csrf_exempt
def hapus_gejala_multiple(request):
    if request.method == "POST":
        data = json.loads(request.body)
        ids = data.get("ids", [])

        if ids:
            Gejala.objects.filter(id__in=ids).delete()
            messages.success(request, "Data berhasil di hapus.")
            return JsonResponse({"message": "Data berhasil dihapus."}, status=200)
        return JsonResponse({"error": "Tidak ada data yang dipilih."}, status=400)

    return JsonResponse({"error": "Metode tidak valid."}, status=405)
@login_required()
def import_gejala(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        
        # Simpan file sementara
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        filepath = fs.path(filename)
        
        try:
            # Membaca file Excel
            df = pd.read_excel(filepath)
            
            # Pastikan file memiliki kolom yang sesuai
            required_columns = {"jenis_elektronik", "kodeGjl", "nama", "deskripsi"}
            if not required_columns.issubset(df.columns):
                messages.error(request, "Format file tidak sesuai.")
                return redirect("gejala")
            
            for _, row in df.iterrows():
                jenis_elektronik, created = JenisElektronik.objects.get_or_create(nama=row["jenis_elektronik"])
                
                Gejala.objects.update_or_create(
                    kodeGjl=row["kodeGjl"],
                    defaults={
                        "jenis_elektronik": jenis_elektronik,
                        "nama": row["nama"],
                        "deskripsi": row["deskripsi"]
                    }
                )
            
            messages.success(request, "Data berhasil diimpor.")
        except Exception as e:
            messages.error(request, f"Terjadi kesalahan: {e}")
        
        return redirect("gejala")
    
    return render(request, "import_gejala.html")
@login_required()
def filter_gejala(request):
    jenis_elektronik_id = request.GET.get('jenis_elektronik')
    gejala_nama = request.GET.get('gejala_nama')

    filtered_data = Gejala.objects.all()

    if jenis_elektronik_id:
        filtered_data = filtered_data.filter(jenis_elektronik_id=jenis_elektronik_id)
    
    if gejala_nama:
        filtered_data = filtered_data.filter(nama__icontains=gejala_nama)

    data = list(filtered_data.values('id', 'jenis_elektronik__nama', 'kodeGjl', 'nama', 'deskripsi'))

    return JsonResponse({'gejala': data})

# KERUSAKAN ============================================
@login_required()
def dsb_kerusakan(request):
    data = Kerusakan.objects.all().order_by('-id')
    jenis_elektronik_list = JenisElektronik.objects.all()
    context = {
            'kerusakan': data,
            "jenis_elektronik": jenis_elektronik_list
    }
    return render(request, 'dsb_kerusakan.html', context)
@login_required()
def tambah_kerusakan(request):
    if request.method == "POST":
        jenis_elektronik_id = request.POST.get("jenis_elektronik")
        kodeRsk = request.POST.get("kodeRsk")
        nama_kerusakan = request.POST.get("nama_kerusakan")
        deskripsi = request.POST.get("deskripsi")

        if Kerusakan.objects.filter(kodeRsk=kodeRsk).exists():
            return JsonResponse({"status": "error", "message": "Kode gejala sudah ada!"})
        jenis_elektronik = get_object_or_404(JenisElektronik, id=jenis_elektronik_id)
        Kerusakan.objects.create(
            jenis_elektronik=jenis_elektronik,
            kodeRsk=kodeRsk,
            nama_kerusakan=nama_kerusakan,
            deskripsi=deskripsi
        )
        messages.success(request, "Data berhasil di tambah.")
        return JsonResponse({"status": "success", "message": "Data gejala berhasil ditambahkan!"})

    return JsonResponse({"status": "error", "message": "Metode tidak diperbolehkan!"})
@login_required()
def edit_kerusakan(request):
    if request.method == "POST":
        kerusakan_id = request.POST.get("id")
        jenis_elektronik_id = request.POST.get("jenis_elektronik")
        kodeRsk = request.POST.get("kodeRsk")
        nama_kerusakan = request.POST.get("nama_kerusakan")
        deskripsi = request.POST.get("deskripsi")

        if not kerusakan_id:
            return JsonResponse({"status": "error", "message": "ID Gejala tidak ditemukan!"})

        kerusakan = get_object_or_404(Kerusakan, id=kerusakan_id)
        jenis_elektronik = get_object_or_404(JenisElektronik, id=jenis_elektronik_id)

        # Perbarui data yang sudah ada
        kerusakan.jenis_elektronik = jenis_elektronik
        kerusakan.kodeRsk = kodeRsk
        kerusakan.nama_kerusakan = nama_kerusakan
        kerusakan.deskripsi = deskripsi
        kerusakan.save()
        messages.success(request, "Data berhasil di edit.")
        return JsonResponse({"status": "success", "message": "kerusakan berhasil diperbarui!"})

    return JsonResponse({"status": "error", "message": "Metode tidak diperbolehkan!"})
@login_required()
@csrf_exempt
def hapus_kerusakan(request):
    if request.method == "POST":
        data = json.loads(request.body)
        kerusakan_id = data.get("id")

        kerusakan = get_object_or_404(Kerusakan, id=kerusakan_id)
        kerusakan.delete()

        messages.success(request, "Data berhasil di hapus.")
        return JsonResponse({"status": "success", "message": "Kerusakan berhasil dihapus!"})

    return JsonResponse({"status": "error", "message": "Metode tidak diperbolehkan!"})
@login_required()
@csrf_exempt
def hapus_kerusakan_multiple(request):
    if request.method == "POST":
        data = json.loads(request.body)
        ids = data.get("ids", [])

        if ids:
            Kerusakan.objects.filter(id__in=ids).delete()
            messages.success(request, "Data berhasil di hapus.")
            return JsonResponse({"message": "Data berhasil dihapus."}, status=200)
        return JsonResponse({"error": "Tidak ada data yang dipilih."}, status=400)

    return JsonResponse({"error": "Metode tidak valid."}, status=405)
@login_required()
def import_kerusakan(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        
        # Simpan file sementara
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        filepath = fs.path(filename)
        
        try:
            # Membaca file Excel
            df = pd.read_excel(filepath)
            
            # Pastikan file memiliki kolom yang sesuai
            required_columns = {"jenis_elektronik", "kodeRsk", "nama_kerusakan", "deskripsi"}
            if not required_columns.issubset(df.columns):
                messages.error(request, "Format file tidak sesuai.")
                return redirect("kerusakan")
            
            for _, row in df.iterrows():
                jenis_elektronik, created = JenisElektronik.objects.get_or_create(nama=row["jenis_elektronik"])
                
                Kerusakan.objects.update_or_create(
                    kodeRsk=row["kodeRsk"],
                    defaults={
                        "jenis_elektronik": jenis_elektronik,
                        "nama_kerusakan": row["nama_kerusakan"],
                        "deskripsi": row["deskripsi"]
                    }
                )
            
            messages.success(request, "Data berhasil diimpor.")
        except Exception as e:
            messages.error(request, f"Terjadi kesalahan: {e}")
        
        return redirect("kerusakan")
    
    return render(request, "import_kerusakan.html")
@login_required()
def filter_kerusakan(request):
    jenis_elektronik_id = request.GET.get('jenis_elektronik')
    nama_kerusakan = request.GET.get('nama_kerusakan')

    filtered_data = Kerusakan.objects.all()

    if jenis_elektronik_id:
        filtered_data = filtered_data.filter(jenis_elektronik_id=jenis_elektronik_id)
    
    if nama_kerusakan:
        filtered_data = filtered_data.filter(nama_kerusakan__icontains=nama_kerusakan)

    data = list(filtered_data.values('id', 'jenis_elektronik__nama', 'kodeRsk', 'nama_kerusakan', 'deskripsi'))

    return JsonResponse({'kerusakan': data})

# ATURAN =====================================================
def get_gejala_kerusakan(request):
    jenis_id = request.GET.get("jenis_id")
    
    if jenis_id:
        # Ambil gejala dan kerusakan yang sesuai dengan jenis elektronik
        gejalas = Gejala.objects.filter(jenis_elektronik_id=jenis_id).values("id", "kodeGjl", "nama")
        kerusakans = Kerusakan.objects.filter(jenis_elektronik_id=jenis_id).values("id", "kodeRsk", "nama_kerusakan")

        return JsonResponse({"gejalas": list(gejalas), "kerusakans": list(kerusakans)})

    return JsonResponse({"gejalas": [], "kerusakans": []})
def get_aturan(request, aturan_id):
    aturan = get_object_or_404(Aturan, id=aturan_id)
    data = {
        "gejala_ids": list(aturan.gejala.values_list('id', flat=True)),
        "kerusakan_sebelumnya_ids": list(aturan.kerusakan_sebelumnya.values_list('id', flat=True)),
    }
    return JsonResponse(data)
@login_required()
def dsb_aturan(request):
    data = Aturan.objects.all().order_by('-id')
    jenis_elektronik_list = JenisElektronik.objects.all()
    gejala = Gejala.objects.all()
    keruskan = Kerusakan.objects.all()
    context = {
            'aturan': data,
            "jenis_elektronik": jenis_elektronik_list,
            "gejalas": gejala,
            "kerusakans": keruskan
    }
    return render(request, 'dsb_aturan.html', context)
@login_required()
def tambah_aturan(request):
    if request.method == "POST":
        jenis_elektronik_id = request.POST.get("jenis_elektronik")
        gejala_ids = request.POST.getlist("gejala[]")
        kerusakan_sebelumnya_ids = request.POST.getlist("kerusakan_sebelumnya[]")  # Tambah ini
        kerusakan_id = request.POST.get("kodeRsk")

        # Validasi input
        if not jenis_elektronik_id or not kerusakan_id:
            return JsonResponse({"status": "error", "message": "Jenis elektronik dan kerusakan harus diisi!"}, status=400)

        try:
            jenis_elektronik = JenisElektronik.objects.get(id=jenis_elektronik_id)
            kerusakan = Kerusakan.objects.get(id=kerusakan_id)

            # Buat aturan baru
            aturan = Aturan.objects.create(
                jenis_elektronik=jenis_elektronik,
                kerusakan=kerusakan
            )

            # Set gejala (opsional, boleh kosong)
            if gejala_ids:
                aturan.gejala.set(Gejala.objects.filter(id__in=gejala_ids))

            # Set kerusakan sebelumnya (opsional, boleh kosong)
            if kerusakan_sebelumnya_ids:
                aturan.kerusakan_sebelumnya.set(Kerusakan.objects.filter(id__in=kerusakan_sebelumnya_ids))

            messages.success(request, "Data berhasil ditambah.")
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Terjadi kesalahan: {str(e)}"}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)
@login_required()
def edit_aturan(request):
    if request.method == "POST":
        aturan_id = request.POST.get("id")
        jenis_elektronik_id = request.POST.get("jenis_elektronik")
        gejala_ids = request.POST.getlist("gejala[]")
        kerusakan_sebelumnya_ids = request.POST.getlist("kerusakan_sebelumnya[]")  # Tambah ini
        kerusakan_id = request.POST.get("kodeRsk")

        # Validasi input
        if not aturan_id or not jenis_elektronik_id or not kerusakan_id:
            return JsonResponse({"status": "error", "message": "Semua field wajib harus diisi!"}, status=400)

        try:
            aturan = get_object_or_404(Aturan, id=aturan_id)
            aturan.jenis_elektronik = JenisElektronik.objects.get(id=jenis_elektronik_id)
            aturan.kerusakan = Kerusakan.objects.get(id=kerusakan_id)

            # Update gejala
            aturan.gejala.set(Gejala.objects.filter(id__in=gejala_ids) if gejala_ids else [])

            # Update kerusakan sebelumnya
            aturan.kerusakan_sebelumnya.set(Kerusakan.objects.filter(id__in=kerusakan_sebelumnya_ids) if kerusakan_sebelumnya_ids else [])

            aturan.save()
            messages.success(request, "Data berhasil diperbarui!")
            return JsonResponse({"status": "success", "message": "Aturan berhasil diperbarui!"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Terjadi kesalahan: {str(e)}"}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)
@login_required()
@csrf_exempt
def hapus_aturan(request):
    if request.method == "POST":
        data = json.loads(request.body)
        aturan_id = data.get("id")

        aturan = get_object_or_404(Aturan, id=aturan_id)
        aturan.delete()

        messages.success(request, "Data berhasil di hapus.")
        return JsonResponse({"status": "success", "message": "aturan berhasil dihapus!"})

    return JsonResponse({"status": "error", "message": "Metode tidak diperbolehkan!"})
@login_required()
@csrf_exempt
def hapus_aturan_multiple(request):
    if request.method == "POST":
        data = json.loads(request.body)
        ids = data.get("ids", [])

        if ids:
            Aturan.objects.filter(id__in=ids).delete()
            messages.success(request, "Data berhasil di hapus.")
            return JsonResponse({"message": "Data berhasil dihapus."}, status=200)
        return JsonResponse({"error": "Tidak ada data yang dipilih."}, status=400)

    return JsonResponse({"error": "Metode tidak valid."}, status=405)
@login_required()
def filter_aturan(request):
    jenis_elektronik_id = request.GET.get('jenis_elektronik')
    kerusakan_query = request.GET.get('kerusakan')

    # Query awal dengan optimasi
    filtered_data = Aturan.objects.select_related('jenis_elektronik', 'kerusakan').prefetch_related('gejala', 'kerusakan_sebelumnya').all()

    # Filter berdasarkan jenis elektronik
    if jenis_elektronik_id:
        filtered_data = filtered_data.filter(jenis_elektronik_id=jenis_elektronik_id)

    # Filter berdasarkan nama kerusakan (kerusakan utama atau kerusakan sebelumnya)
    if kerusakan_query:
        filtered_data = filtered_data.filter(
            models.Q(kerusakan__nama_kerusakan__icontains=kerusakan_query) |
            models.Q(kerusakan_sebelumnya__nama_kerusakan__icontains=kerusakan_query)
        ).distinct()

    # Siapkan data untuk JSON
    data = []
    for aturan in filtered_data:
        data.append({
            "id": aturan.id,
            "jenis_elektronik": aturan.jenis_elektronik.nama,
            "gejala": [{"kodeGjl": g.kodeGjl, "nama": g.nama} for g in aturan.gejala.all()],
            "kerusakan": aturan.kerusakan.nama_kerusakan,
            "kodeRsk": aturan.kerusakan.kodeRsk,
            "kerusakan_sebelumnya": [{"kodeRsk": k.kodeRsk, "nama": k.nama_kerusakan} for k in aturan.kerusakan_sebelumnya.all()],
        })

    return JsonResponse({'aturan': data})

# SOLUSI ============================================
@login_required
def dsb_solusi(request):
    """Menampilkan semua solusi"""
    data = Solusi.objects.all().order_by('-id')
    kerusakan = Kerusakan.objects.all()
    context = {
        'solusi': data,
        'kerusakan': kerusakan,
    }
    return render(request, 'dsb_solusi.html', context)
@login_required
def edit_solusi(request, id):
    solusi = get_object_or_404(Solusi, id=id)

    if request.method == "GET":
        # Mengembalikan data solusi untuk diisi di modal via AJAX
        data = {
            "id": solusi.id,
            "kerusakan_id": solusi.kerusakan.id,
            "nama_solusi": solusi.nama_solusi,
            "deskripsi": solusi.deskripsi,
            "biaya_perbaikan": solusi.biaya_perbaikan,
            "waktu_perbaikan": solusi.waktu_perbaikan or "",
        }
        return JsonResponse(data)

    elif request.method == "POST":
        # Proses penyimpanan perubahan via AJAX
        kerusakan_id = request.POST.get("kerusakan")
        nama_solusi = request.POST.get("nama_solusi")
        deskripsi = request.POST.get("deskripsi")
        biaya_perbaikan = request.POST.get("biaya_perbaikan")
        waktu_perbaikan = request.POST.get("waktu_perbaikan")

        # Validasi input
        if not all([kerusakan_id, nama_solusi, deskripsi]):
            return JsonResponse({"status": "error", "message": "Kerusakan, nama solusi, dan deskripsi harus diisi!"}, status=400)

        try:
            solusi.kerusakan = Kerusakan.objects.get(id=kerusakan_id)
            solusi.nama_solusi = nama_solusi
            solusi.deskripsi = deskripsi
            solusi.biaya_perbaikan = int(biaya_perbaikan) if biaya_perbaikan else 0
            solusi.waktu_perbaikan = waktu_perbaikan if waktu_perbaikan else None
            solusi.save()

            messages.success(request, "Solusi berhasil diperbarui!")
            return JsonResponse({"status": "success", "message": "Solusi berhasil diperbarui!"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Terjadi kesalahan: {str(e)}"}, status=500)

    return JsonResponse({"status": "error", "message": "Metode tidak diizinkan"}, status=405)
@login_required
def tambah_solusi(request):
    if request.method == "POST":
        kerusakan_id = request.POST.get("kerusakan")
        nama_solusi = request.POST.get("nama_solusi")
        deskripsi = request.POST.get("deskripsi")
        biaya_perbaikan = request.POST.get("biaya_perbaikan")
        waktu_perbaikan = request.POST.get("waktu_perbaikan")

        # Validasi input
        if not all([kerusakan_id, nama_solusi, deskripsi]):
            return JsonResponse({"status": "error", "message": "Kerusakan, nama solusi, dan deskripsi harus diisi!"}, status=400)

        try:
            kerusakan = Kerusakan.objects.get(id=kerusakan_id)
            solusi = Solusi.objects.create(
                kerusakan=kerusakan,
                nama_solusi=nama_solusi,
                deskripsi=deskripsi,
                biaya_perbaikan=int(biaya_perbaikan) if biaya_perbaikan else 0,
                waktu_perbaikan=waktu_perbaikan if waktu_perbaikan else None,
                is_recommended=True  # Default value
            )
            messages.success(request, "Solusi berhasil ditambahkan!")
            return JsonResponse({"status": "success", "message": "Solusi berhasil ditambahkan!"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Terjadi kesalahan: {str(e)}"}, status=500)

    return JsonResponse({"status": "error", "message": "Metode tidak diizinkan"}, status=405)
@login_required
@csrf_exempt
def hapus_solusi(request):
    if request.method == "POST":
        data = json.loads(request.body)
        solusi_id = data.get("id")

        solusi = get_object_or_404(Solusi, id=solusi_id)
        solusi.delete()

        messages.success(request, "Solusi berhasil dihapus.")
        return JsonResponse({"status": "success", "message": "Solusi berhasil dihapus!"})

    return JsonResponse({"status": "error", "message": "Metode tidak diperbolehkan!"})
@login_required
@csrf_exempt
def hapus_solusi_multiple(request):
    """ Menghapus beberapa solusi berdasarkan list ID """
    if request.method == "POST":
        data = json.loads(request.body)
        ids = data.get("ids", [])

        if ids:
            Solusi.objects.filter(id__in=ids).delete()
            messages.success(request, "Data berhasil dihapus.")
            return JsonResponse({"message": "Data berhasil dihapus."}, status=200)

        return JsonResponse({"error": "Tidak ada data yang dipilih."}, status=400)

    return JsonResponse({"error": "Metode tidak valid."}, status=405)
@login_required
def filter_solusi(request):
    """Filter dan cari data solusi"""
    kerusakan_id = request.GET.get('kerusakan')
    nama_query = request.GET.get('nama_solusi')

    # Query awal dengan optimasi
    filtered_data = Solusi.objects.select_related('kerusakan').all().order_by('-id')

    # Filter berdasarkan kerusakan
    if kerusakan_id:
        filtered_data = filtered_data.filter(kerusakan_id=kerusakan_id)

    # Pencarian berdasarkan nama solusi
    if nama_query:
        filtered_data = filtered_data.filter(nama_solusi__icontains=nama_query)

    # Siapkan data untuk JSON
    data = []
    for solusi in filtered_data:
        data.append({
            "id": solusi.id,
            "kerusakan": {
                "kodeRsk": solusi.kerusakan.kodeRsk,
                "nama": solusi.kerusakan.nama_kerusakan
            },
            "nama_solusi": solusi.nama_solusi,
            "deskripsi": solusi.deskripsi,
            "is_recommended": solusi.is_recommended,
            "biaya_perbaikan": solusi.biaya_perbaikan,
            "waktu_perbaikan": solusi.waktu_perbaikan or "-"
        })

    return JsonResponse({'solusi': data})

# AUTH =====================================
def signin_form(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Sign in Berhasil")
            return redirect("dashboard")
        else:
            messages.error(request, "Username atau password salah.")

    return render(request, 'signin.html')
def signout_form(request):
    logout(request)
    messages.success(request, "Logout Berhasil")
    return render(request, 'signin.html')