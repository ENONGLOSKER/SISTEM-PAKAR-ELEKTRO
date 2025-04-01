from django.db import models
from django.db.models import Count

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
    gejala = models.ManyToManyField(Gejala, blank=True)
    kerusakan_sebelumnya = models.ManyToManyField('Kerusakan', blank=True, related_name='aturan_dari_kerusakan')
    kerusakan = models.ForeignKey(Kerusakan, on_delete=models.CASCADE, related_name='aturan_menuju_kerusakan')

    def __str__(self):
        return f"Aturan untuk {self.jenis_elektronik.nama} - {self.kerusakan.nama_kerusakan}"

class Solusi(models.Model):
    kerusakan = models.ForeignKey(Kerusakan, on_delete=models.CASCADE)
    nama_solusi = models.CharField(max_length=255)
    deskripsi = models.TextField()
    is_recommended = models.BooleanField(default=True)
    biaya_perbaikan = models.PositiveIntegerField(default=50)
    waktu_perbaikan = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.nama_solusi}"

class Diagnosa(models.Model):
    jenis_elektronik = models.ForeignKey('JenisElektronik', on_delete=models.CASCADE)
    gejala = models.ManyToManyField('Gejala')
    solusi = models.TextField(blank=True)
    catatan = models.TextField(blank=True, null=True)
    tanggal_diagnosa = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Diagnosa {self.id} - {self.jenis_elektronik.nama}"

class DiagnosaKerusakan(models.Model):
    diagnosa = models.ForeignKey(Diagnosa, on_delete=models.CASCADE, related_name='diagnosa_kerusakan')
    kerusakan = models.ForeignKey('Kerusakan', on_delete=models.CASCADE)
    akurasi = models.FloatField(default=0.0)  

    class Meta:
        unique_together = ('diagnosa', 'kerusakan') 

    def __str__(self):
        return f"{self.diagnosa} - {self.kerusakan} ({self.akurasi}%)"