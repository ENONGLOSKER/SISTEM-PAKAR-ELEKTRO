from django.db import models

# Create your models here.
class JenisElektronik(models.Model):
    nama = models.CharField(max_length=255)
    def __str__(self):
        return self.nama
    
class Gejala(models.Model):
    jenis_elektronik = models.ForeignKey(JenisElektronik, on_delete=models.CASCADE)
    kodeGjl = models.CharField(max_length=10, unique=True)
    nama = models.CharField(max_length=255)
    deskripsi = models.TextField()

    def __str__(self):
        return f"{self.nama}"

class Kerusakan(models.Model):
    jenis_elektronik = models.ForeignKey(JenisElektronik, on_delete=models.CASCADE)
    kodeRsk = models.CharField(max_length=10, unique=True)
    nama_kerusakan = models.CharField(max_length=255)
    deskripsi = models.TextField()

    def __str__(self):
        return f"{self.nama_kerusakan}"

class Aturan(models.Model):
    jenis_elektronik = models.ForeignKey(JenisElektronik, on_delete=models.CASCADE)
    gejala = models.ManyToManyField(Gejala)
    kerusakan = models.ForeignKey(Kerusakan, on_delete=models.CASCADE)

    def __str__(self):
        return f"Aturan untuk {self.jenis_elektronik.nama} - {self.kerusakan.nama_kerusakan} ({self.akurasi * 100}%)"

class Solusi(models.Model):
    kerusakan = models.ForeignKey(Kerusakan, on_delete=models.CASCADE)
    nama_solusi = models.CharField(max_length=255)
    deskripsi = models.TextField()
    is_recommended = models.BooleanField(default=True)  # Menandai solusi yang direkomendasikan
    biaya_perbaikan = models.PositiveIntegerField(default=50)  # Biaya perbaikan dalam satuan rupiah
    waktu_perbaikan = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Solusi untuk {self.kerusakan.nama_kerusakan}: {self.nama_solusi}"

class Diagnosa(models.Model):
    jenis_elektronik = models.ForeignKey(JenisElektronik, on_delete=models.CASCADE)
    gejala = models.ManyToManyField(Gejala)  # Gejala yang dipilih oleh pengguna
    kerusakan = models.ForeignKey(Kerusakan, on_delete=models.CASCADE, null=True, blank=True)  # Kerusakan hasil diagnosa
    akurasi = models.FloatField(default=0.0)  # Tingkat akurasi diagnosa
    catatan = models.TextField(blank=True, null=True)  # Catatan tambahan
    solusi = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default="Selesai")  # Status diagnosa (misalnya "Selesai", "Dalam Proses")
    tanggal_diagnosa = models.DateTimeField(auto_now_add=True)  # Tanggal diagnosa dilakukan
    updated_at = models.DateTimeField(auto_now=True)  # Tanggal terakhir diperbarui

    def __str__(self):
        return f"Diagnosa {self.jenis_elektronik.nama} - {self.kerusakan.nama_kerusakan if self.kerusakan else 'Belum Ditemukan'} ({self.akurasi * 100}%)"

