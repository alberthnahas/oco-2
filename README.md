# Pengolahan Total Kolom CO<sub>2</sub> dengan menggunakan data Satelit OCO-2 NASA
## Satelit OCO-2 NASA

Karbon dioksida (CO<sub>2</sub>) merupakan salah satu gas rumah kaca yang kenaikan konsentrasinya di atmosfer dijadikan sebagai indikator terhadap terjadinya perubahan iklim. Peningkatan konsentrasi CO<sub>2</sub> di atmosfer terjadi secara global yang ditandai dengan kenaikan konsentrasinya sejak revolusi industri di tahun 1750.

Dalam kajian mengenai perubahan iklim, peningkatan konsentrasi CO<sub>2</sub> penting untuk diinformasikan. Oleh karena itu, pengukuran konsentrasinya di atmosfer menjadi komponen yang harus dilakukan untuk dapat memberikan profil laju peningkatannya. Informasi mengenai konsentrasi CO<sub>2</sub> dapat diperoleh dengan beberapa metode, seperti pengukuran dengan menggunakan instrumentasi yang dipasang secara <i>in situ</i> di suatu lokasi, pengukuran secara mobil dengan menggunakan kapal laut dan pesawat udara, pemantauan menggunakan satelit, dan pemodelan.

Salah satu sumber informasi mengenai konsentrasi CO<sub>2</sub> diperoleh dari Satelit Orbiting Carbon Observatory-2 atau OCO-2. Kegiatan pemantauan CO<sub>2</sub> menggunakan Satelit OCO-2 ini dilakukan oleh NASA sejak peluncuran satelit pada tanggal 2 Juli 2014. Satelit OCO-2 merupakan satelit milik NASA pertama yang didedikasikan untuk melakukan pemantauan CO<sub>2</sub> secara <i>remote sensing</i>. Oleh karena dipantau dari luar angkasa, nilai CO<sub>2</sub> yang diberikan merupakan total kolom konsentrasi CO<sub>2</sub>. Total kolom CO<sub>2</sub> adalah hasil pantauan konsentrasi CO<sub>2</sub> dari permukaan bumi sampai dengan puncak atmosfer yang tercakup dalam resolusi spasial satelit.

Untuk mendapatkan nilai total kolom CO<sub>2</sub>, satelit ini menggabungkan tiga spektrometer dengan resolusi tinggi yang mengukur refleksi sinar matahari pada panjang gelombang 1,61 dan 2,06 micrometer atau pada daerah absorpsi <i>near-infrared</i> CO<sub>2</sub>. Resolusi spasial dari sapuan Satelit OCO-2 adalah 2,25 km x 1,29 km, dengan waktu perulangan setiap 16 hari.

Informasi mengenai Satelit OCO-2 dapat dilihat dari video berikut.
[![Watch the video](https://img.youtube.com/vi/-uP_fqEfYWg/maxresdefault.jpg)](https://youtu.be/-uP_fqEfYWg)

<br></br>
## Pengunduhan Data

Data satelit OCO-2 yang digunakan pada pengolahan ini bersumber dari data OCO-2 Level 2 geolocated XCO2 retrievals results, physical model V11.2 (https://disc.gsfc.nasa.gov/datasets/OCO2_L2_Standard_11.2/summary). Versi ini merupakan versi terbaru yang diimplementasikan sejak data periode Maret 2022. Data ini merupakan luaran dari algoritma yang digunakan untuk memperoleh rerata total kolom CO<sub>2</sub> (XCO2). 

Pengunduhan data dilakukan dengan menggunakan fasilitas cuplikan file yang dapat mengumpulkan data berekstensi .h5 secara kolektif pada batasan koordinat wilayah Indonesia. Akses data ini dapat dilakukan melalui pranala di atas dengan memilih menu Get Data. Untuk kemudahan, pengumpulan data diproses menggunakan wget. Cara penggunaan wget untuk pengunduhan data untuk sistem operasi Windows, MacOS, dan Linux dapat dilihat pada pranala berikut: https://disc.gsfc.nasa.gov/data-access. Pengunduhan data baru dapat diproses jika sudah memiliki akun Earthdata NASA (https://wiki.earthdata.nasa.gov/display/EL/How+To+Register+For+an+EarthData+Login+Profile).
<br></br>
## Pengolahan Data

Pengolahan data yang dilakukan terhadap data yang telah diunduh untuk periode bulanan. Pengolahan dilakukan dengan menggunakan skrip R. Dalam skrip ini, nilai total kolom CO<sub>2</sub> (xco2) beserta koordinat lintang dan bujur pada titik-titik dengan nilai xco2 diekstrak dari data satelit (format .h5). Titik-titik ini kemudian diinterpolasikan dengan menggunakan metode <i>Inverse Distance Weighting</i> (IDW) pada resolusi spasial 0,5 derajat. Luaran dari proses ini adalah file binary dengan format .nc.

Visualisasi dari hasil pengolahan data dilakukan dengan skrip GrADS yang menampilkan total kolom CO<sub>2</sub> untuk wilayah Indonesia (90BT- 145BT, 10LU-15LS).

![](https://github.com/alberthnahas/OCO-2/blob/main/ghg-indonesia.gif)

Kode R dibuat dengan Sistem Operasi Ubuntu 24.04 LTS.
