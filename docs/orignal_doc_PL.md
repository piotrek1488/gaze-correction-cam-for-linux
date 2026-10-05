> Wersja angielska (oryginalna): [orignal_doc.md](orignal_doc.md).
> To tłumaczenie oryginalnej dokumentacji projektu źródłowego (upstream).

Korekcja spojrzenia za pomocą splotowej sieci neuronowej opartej na deformacji (warping).

# Artykuł
@article{Hsu:2019:LMC:3339884.3311784,<br />
author = {Hsu, Chih-Fan and Wang, Yu-Shuen and Lei, Chin-Laung and Chen, Kuan-Ta},<br />
 title = {Look at Me\\\&Excl; Correcting Eye Gaze in Live Video Communication},<br />
 journal = {ACM Trans. Multimedia Comput. Commun. Appl.},<br />
 issue_date = {June 2019},<br />
 volume = {15},<br />
 number = {2},<br />
 month = jun,<br />
 year = {2019},<br />
 issn = {1551-6857},<br />
 pages = {38:1--38:21},<br />
 articleno = {38},<br />
 numpages = {21},<br />
 url = {[http://doi.acm.org/10.1145/3311784](http://doi.acm.org/10.1145/3311784)},<br />
 doi = {10.1145/3311784},<br />
 acmid = {3311784},<br />
 publisher = {ACM},<br />
 address = {New York, NY, USA},<br />
 keywords = {Eye contact, convolutional neural network, gaze correction, <br />image processing, live video communication},<br />
} <br />

# Film demonstracyjny na YouTube
[![Look at Me! Correcting Eye Gaze in Live Video Communication](https://github.com/chihfanhsu/gaze_correction/blob/master/imgs/YouTube_page.PNG)](https://youtu.be/9nAHINph5a4)

# Użycie systemu
```python
python regz_socket_MP_FD.py
```

# Parametry wymagające personalizacji w pliku „config.py”
Położenie wszystkich parametrów przedstawia poniższa ilustracja. P_o to punkt pierwotny (0,0,0) zdefiniowany w środku ekranu. <br />
<br />
Parametry „P_c_x”, „P_c_y”, „P_c_z”, „S_W”, „S_H” oraz „f” należy spersonalizować przed użyciem systemu. <br />
„P_c_x”, „P_c_y” i „P_c_z”: względna odległość między pozycją kamery a środkiem ekranu (cm) <br />
„S_W” i „S_H”: rozmiar ekranu (cm) <br />
„f”: ogniskowa kamery <br />
<br />
![Położenie parametrów](https://github.com/chihfanhsu/gaze_correction/blob/master/imgs/correcting_gaze.png)

# Kalibracja ogniskowej kamery przy użyciu dołączonych narzędzi
Uruchom skrypt „focal_length_calibration.ipynb” lub „focal_length_calibration.py”, aby oszacować ogniskową (f); wartość pojawi się w lewym górnym rogu okna. <br />
Kroki kalibracji:<br />
Krok 1: umieść głowę przed kamerą w odległości około 50 cm (wartość można zmienić w kodzie). <br />
Krok 2: wpisz w kodzie swój rozstaw źrenic (odległość między oczami) lub użyj wartości średniej 6,3 cm. <br />
<br />
![Przykład kalibracji](https://github.com/chihfanhsu/gaze_correction/blob/master/imgs/calibration.png)

# Zaczynamy korygować spojrzenie! (Self-demo)
Naciśnij klawisz „r”, gdy aktywne jest okno „local”, i skieruj wzrok na okno „remote”, aby rozpocząć korekcję spojrzenia. <br />
Naciśnij klawisz „q”, gdy aktywne jest okno „local”, aby zamknąć program. <br />
<br />
*Na początku obraz będzie opóźniony z powodu transmisji przez gniazdo TCP; po kilku sekundach obraz będzie już na bieżąco. <br />
<br />
![Przykład użycia systemu](https://github.com/chihfanhsu/gaze_correction/blob/master/imgs/system_usage.png)

# Komunikacja wideo online
Kod po stronie lokalnej i zdalnej jest taki sam. Parametry „tar_ip”, „sender_port” i „recver_port” trzeba jednak zdefiniować po obu stronach. <br />
„tar_ip”: adres IP drugiego użytkownika <br />
„sender_port”: numer portu do wysyłania wideo z przekierowanym spojrzeniem do drugiego użytkownika <br />
„sender_port”: numer portu do odbierania wideo z przekierowanym spojrzeniem od drugiego użytkownika <br />

# Konfiguracja IP dla self-demo
Kod po stronie lokalnej i zdalnej jest taki sam. Parametry „tar_ip”, „sender_port” i „recver_port” trzeba jednak zdefiniować po obu stronach. <br />
„tar_ip”: 127.0.0.1 <br />
„sender_port”: 5005 <br />
„sender_port”: 5005 <br />

# Konfiguracja środowiska
Python 3.5.3 <br />
Tensorflow 1.8.0 <br />
Cuda V9.0.176 i odpowiednie cuDNN <br />

# Wymagane pakiety
Dlib 18.17.100 <br />
OpenCV 3.4.1 <br />
Numpy 1.15.4 + mkl <br />
pypiwin32 <br />
scipy 0.19.1 <br />

# Zbiór danych DIRL Gaze
![Przykład użycia systemu](https://github.com/chihfanhsu/gaze_correction/blob/master/imgs/dataset_collection.PNG)
<br />
W zbieraniu zbioru danych wzięło udział 37 azjatyckich ochotników. Zebrano około 100 kierunków spojrzenia w zakresie od +40 do -40 stopni w poziomie i od +30 do -30 stopni w pionie, przy czym odpowiednio 63 i 37 obrazów to kierunki stałe i losowe. Obrazy z zamkniętymi oczami usunięto.
[Pobierz tutaj!](https://sites.google.com/site/chihfanhsuwebsite/dataset)

# Kilka interesujących projektów
[![2019 Eye Contact Correction using Deep Neural Networks]](https://arxiv.org/pdf/1906.05378.pdf) <br />
[![2019 Photo-Realistic Monocular Gaze Redirection Using Generative Adversarial Networks]](https://arxiv.org/pdf/1903.12530.pdf)
