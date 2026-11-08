# Portal Unit Kepatuhan Internal

Portal statis dengan panel admin Flask dan penyimpanan menu SQLite. Admin dapat menambah, mengedit, mengurutkan, menyembunyikan dan menghapus menu. Nama, tautan, deskripsi, kategori, ilustrasi, serta lokasi tampil (navigasi/footer dan kartu layanan) dapat diatur tanpa Git.

## Jalankan secara lokal

Python 3.11 atau lebih baru:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python server.py --port 8765
```

Buka http://localhost:8765/ untuk portal dan http://localhost:8765/admin untuk panel. Pada awal penggunaan lokal, panel menawarkan pembuatan akun admin pertama. Tentukan sendiri nama pengguna dan kata sandi minimal 12 karakter. Tidak ada kata sandi bawaan. Setelah akun pertama dibuat, formulir ini tidak tersedia lagi. Semua perubahan tersimpan di `.data/uki.sqlite3` dan terlihat pada semua pengunjung. Tab yang sedang terbuka memperbarui menu ketika kembali aktif atau paling lambat setelah 60 detik.

`python3 -m http.server` hanya dapat menampilkan halaman statis; perintah itu tidak menjalankan panel admin atau database.

## Mengelola tautan Dialog Kinerja

1. Masuk ke `/admin` dengan akun admin yang sudah ada.
2. Pilih **Dialog Kinerja**, lalu pilih bagian halaman.
3. Untuk dokumen utama, klik **Tambah tautan** dan isi nama dokumen serta URL.
4. Untuk folder bulanan, klik **Edit** pada bulan yang ingin diperbarui lalu isi URL folder. URL kosong ditampilkan sebagai “Belum tersedia”. Setiap bulan hanya memiliki satu folder dan mengikuti urutan kalender.
5. Untuk laporan unit, pilih **Dokumen per unit kerja**, klik **Tambah tautan**, lalu isi nama unit, nama laporan dan URL. Nama unit yang sama mengelompokkan tautan pada satu bagian di halaman publik. Nama unit baru membuat kelompok baru ketika memiliki laporan yang ditampilkan.
6. Klik **Simpan tautan**. Gunakan tombol **Sembunyikan**, **Hapus**, atau panah urutan jika diperlukan. Penghapusan hanya menghilangkan tautan di portal, bukan dokumen di layanan asal.

Tautan lama diimpor sekali saat aplikasi diperbarui. Akun admin dan menu portal tetap tersedia. Tautan Dialog Kinerja memiliki revisi tersendiri sehingga perubahan menu navigasi tidak menimbulkan konflik pada dokumen. Tab pengunjung mengambil perubahan ketika kembali aktif atau paling lambat 60 detik.

## Hosting

Aplikasi perlu server yang menjalankan Python dan disk persisten. GitHub Pages tidak menjalankan API/database ini; halaman statis masih bisa ditampilkan, tetapi pengelolaan menu membutuhkan hosting aplikasi. Jalankan portal dan API pada domain yang sama.

Contoh setelah memasang dependensi pada server:

```bash
export UKI_DATABASE=/var/lib/uki/uki.sqlite3
export UKI_PUBLIC_ORIGIN=https://portal.example.org
.venv/bin/python server.py --admin admin
.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 'server:create_app()'
```

Ganti domain dan lokasi database dengan konfigurasi server sebenarnya. Buat direktori database dengan izin tulis bagi pengguna aplikasi. Pasang reverse proxy HTTPS di depan Gunicorn dan teruskan `/`, `/admin`, `/assets/` serta `/api/` ke aplikasi. `UKI_PUBLIC_ORIGIN` harus sama persis dengan origin browser (tanpa path); mengaktifkan cookie Secure. Jangan mengekspos server preview Flask ke internet. Panduan server WSGI: https://flask.palletsprojects.com/en/stable/deploying/.

Pada proses Gunicorn, pembuatan akun lewat browser dinonaktifkan. Buat atau pulihkan akun dari terminal server menggunakan `python server.py --admin nama_pengguna`. Kata sandi diminta secara tersembunyi dan sesi lama akun tersebut diakhiri setelah pemulihan. Perintah ini juga dapat digunakan untuk menambahkan administrator lain.

## Penyimpanan dan pencadangan

Menu, tautan Dialog Kinerja, hash kata sandi, pembatasan login dan sesi disimpan di SQLite. Data ini berada di `.data/` yang diabaikan Git. Jangan meletakkan database di direktori assets atau membagikannya kepada pengunjung. Hindari hosting dengan filesystem sementara karena data akan hilang saat redeploy.

Untuk mencadangkan database yang sedang dipakai, gunakan SQLite backup API:

```bash
python3 -c "import sqlite3; source=sqlite3.connect('.data/uki.sqlite3'); target=sqlite3.connect('/lokasi/aman/uki-backup.sqlite3'); source.backup(target); target.close(); source.close()"
```

Simpan backup di lokasi privat. Saat memulihkan, hentikan aplikasi dahulu dan pulihkan database beserta izin filenya. Untuk deployment gunakan nilai `UKI_DATABASE` yang sesuai sebagai lokasi sumber backup.

## Pengujian

```bash
python3 -m unittest discover -s tests -v
```

Pengujian memakai database sementara, tidak menyentuh akun atau menu portal sebenarnya. Mencakup autentikasi, sesi, CSRF, pembatasan login, pembuatan akun pertama, CRUD, urutan, konflik perubahan, persistensi, validasi tautan, serta perlindungan berkas privat.

## Batas fitur

Panel mengelola menu dan tautan; tidak membuat halaman baru, mengunggah dokumen, atau mengedit isi pengumuman. Tautan dalam Dialog Kinerja dapat dikelola melalui panel; tautan dalam halaman LHK dan Pengelolaan Kinerja masih dikelola di HTML. Jika API tidak dapat dihubungi saat halaman pertama dimuat, portal menampilkan menu bawaan dari HTML; perubahan berikutnya dimuat ulang ketika koneksi pulih. Login admin tidak memberikan akses ke dokumen eksternal yang masih mengikuti izin layanan masing-masing.
