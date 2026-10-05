# Analiza gaze-correction-cam i portu Ubuntu

Stan analizy: 2026-10-05. Punkt odniesienia: upstream `a94ec59` (pełny hash: `git rev-parse HEAD`). Zmiany portu pozostawiono lokalnie do przeglądu; nie publikowano ich w repozytorium autora.

## 1. Co faktycznie udostępnia repozytorium

README opisuje gotową aplikację macOS i rozszerzenie kamery. W publicznym drzewie źródeł znajdują się jednak moduły Python, nie projekt Swift/Xcode ani rozszerzenie CoreMediaIO. Oryginalny `bin_single_window.py` otwiera kamerę przez OpenCV i wyświetla wynik przez `imshow`. Nie tworzy kamery wirtualnej. Samo uruchomienie oryginału na Linux nie wystarcza więc do użycia korekcji w komunikatorze.

Rdzeń jest przenośny: NumPy, OpenCV, TensorFlow, YAML i SQLite. `pyobjc` występuje w zależnościach, lecz główny tor przetwarzania go nie importuje. To niepotrzebna przeszkoda instalacji na Linux, a nie niezbędny składnik algorytmu.

Repozytorium nie zawiera wag. Starsze wydanie v0.1.1 zawiera `weights.zip` i model landmarków dlib. Nowsze wydania zawierają instalatory DMG. W porcie pobrano wagi z v0.1.1 oraz wersjonowany model FaceLandmarker od MediaPipe.

## 2. Przepływ danych i odpowiedzialności

| Element | Rzeczywista rola |
|---|---|
| `bin_single_window.py` | Parser CLI, ustalenie rozdzielczości, konstrukcja obiektów, uruchomienie okna |
| `displayers/face_predictor.py` | Detekcja twarzy przez dlib lub MediaPipe, landmarki, wycięcie oczu, mapy kotwic |
| `displayers/dis_single_window.py` | Pierwsza wykryta twarz, korekcja, nakładki, obsługa klawiszy |
| `model_managers/gaze_corrector_v1.py` | Dwa grafy/sesje TensorFlow, geometria, inferencja, wklejenie oczu |
| `model_managers/user_settings_db.py` | SQLite z parametrami kamery jako JSON; zapytania parametryzowane |
| `tf_models/gaze_corrector_v1/gaze_warp_model.py` | Enkoder kąta, sieć zgrubna i dokładna, korekcja jasności |
| `tf_models/gaze_corrector_v1/layers.py` | Warstwy Keras w grafach zgodnych z TF1 |
| `tf_models/gaze_corrector_v1/spatial_transform.py` | Próbkowanie biliniowe według pola przemieszczeń |
| `ubuntu_camera.py` (port) | Przechwytywanie V4L2/plik, okno, zapis AVI, wyjście v4l2loopback, cykl życia zasobów |

Tor: klatka BGR → landmarki → dwa wycinki 48×64×3 i mapy 48×64×12 → kąt korekcji → oddzielne modele L/R → przeskalowanie wycinków → wklejenie do klatki → wyjście.

Każda mapa kotwic zawiera różnice współrzędnych względem sześciu landmarków (X i Y dla każdego punktu). Kolejność punktów lewego oka jest odwrócona zgodnie z formatem wejścia modelu. Enkoder zamienia parę kątów na 16 cech i rozciąga je przestrzennie. Sieć estymuje przepływ w dwóch skalach; `tanh` ogranicza przemieszczenia. Moduł LCM miesza wynik deformacji z bielą, aby skorygować jasność.

## 3. Co algorytm mierzy, a czego nie mierzy

To nie jest pełny estymator aktualnego kierunku spojrzenia. `estimate_gaze_angle` wyznacza odległość oczu z ich rozstawu w pikselach, zadanej ogniskowej i domyślnego IPD 6,3 cm. Następnie oblicza kąt z geometrii ekranu/kamery. Zakłada określone położenie celu i wymaga kalibracji. Nie odczytuje położenia okna rozmówcy na pulpicie ani tego, który tekst użytkownik właśnie czyta.

Domyślne przesunięcie kamery `(0, -21, -1)` cm i ogniskowa 650 px nie są uniwersalne. Zmiana rozdzielczości bez odpowiedniej korekty ogniskowej zmienia estymację. MediaPipe w upstreamie używa środków tęczówek do geometrii, natomiast dlib korzysta z kącików oczu; te backendy nie są idealnie równoważne.

Model jest historyczny. Dokumentacja źródłowa odsyła do „Look at Me! Correcting Eye Gaze in Live Video Communication” z 2019 r.; plik dołączony do wag podaje datę treningu 20180413 i `Trained head poses: 0`. Wnioskuję z tego ograniczoną odporność na duże obroty głowy; nie traktuję tego jako zmierzonej granicy jakości. Dokumentacja zbioru opisuje 37 uczestników, co dodatkowo ogranicza podstawy do twierdzeń o uniwersalnej jakości.

## 4. Znalezione problemy i sposób postępowania

| Problem w upstreamie | Skutek | Port |
|---|---|---|
| Bezwarunkowe `pyobjc` | Instalacja zależności macOS na Linux | Marker platformy; osobne wymagania Ubuntu |
| Brak wyjścia wirtualnego | Komunikator nie widzi wyniku | `pyvirtualcam` + istniejące urządzenie `v4l2loopback` |
| MediaPipe dostaje BGR jako SRGB | Niepoprawne kolory dla detektora | Jawne BGR→RGB wyłącznie na wejściu detekcji |
| Czas ze zwykłego zegara | Możliwe powtórzenia/cofnięcie timestampu | Zegar monotoniczny i minimum poprzedni+1 ms |
| Ujemne indeksy wycinków | Niepoprawne fragmenty obrazu/kształty | Pomijanie niepełnego wycinka przy granicy obrazu |
| Brak checkpointu tylko ostrzega | Sesja z niezainicjalizowanymi zmiennymi | Błąd startu z instrukcją pobrania modeli |
| Względny prefiks `L`/`R` z checkpointu | Odtwarzanie z niewłaściwego katalogu | Prefiks budowany z katalogu modelu |
| Przechwytywanie wszystkich błędów inferencji | Podgląd może udawać działającą korekcję | Błąd kończy program i trafia do stderr |
| Kody strzałek macOS i obcinanie do 8 bitów | Niedziałająca kalibracja Linux | Kody X11/Qt i `waitKeyEx` |
| Brak walidacji rozstawu oczu | Dzielenie przez zero | Walidacja przed obliczeniami |
| Ogniskowa może zejść do zera | Niepoprawna geometria | Dodatnia wartość, ograniczenie przy regulacji |
| Rozmiar konfiguracji zamiast klatki | Błędna geometria po negocjacji kamery | Rozmiar rzeczywistej klatki |
| Brak `finally` wokół oryginalnej pętli | Zasoby niezamknięte po wyjątku | Nowy runner używa `ExitStack` |
| Ścieżki zależne od katalogu wywołania | Start spoza repo nie działa | Launcher i runner ustalają katalog projektu |
| Nakładki zmieszane z wyjściem | Napisy w rozmowie | Osobna kopia dla podglądu |

Nie zmieniano formuł deformacji, kolejności kanałów wejścia sieci ani architektury tylko na podstawie estetyki kodu: muszą odpowiadać wytrenowanym wagom. Interpolator ma historyczną konwencję skalowania do szerokości/wysokości zamiast szerokości-1/wysokości-1; modyfikacja wymagałaby osobnego porównania jakości z oryginalnym modelem.

## 5. Jakość kodu i dokumentacji

Architektura rozdziela detekcję, model i prezentację, co ułatwia port. Dataclasses i wstrzykiwanie predyktora są przydatne w testach. SQLite jest wystarczający do kilku parametrów i nie wymaga serwera.

Są też oznaki nieukończonej refaktoryzacji. `docs/architecture.md` wspomina pliki `gaze_corrector.py`, `flx.py`, `transformation.py` i narzędzia kalibracyjne, których nie ma w bieżącym drzewie pod tymi nazwami. Dokumentacja opisuje detekcję w mniejszej rozdzielczości, lecz aktualny predyktor dlib pracuje na pełnej klatce; `face_detect_size` w konfiguracji nie steruje nim. Kod ekstrakcji oczu jest powielony między backendami. Oryginalne skrypty `bin_test_*` to ręczne demonstracje detekcji, nie automatyczne testy regresji.

W `utils/config.py` pozostały argumenty parsera z `type=eval`. Nowy runner nie korzysta z tego modułu; docelowo warto usunąć legacy parser lub zastąpić te konwersje `int`/`float`. Nie przeprowadzano osobnego audytu bezpieczeństwa całego projektu.

## 6. Zakres dostarczonego portu

- Kamera fizyczna przez V4L2, domyślnie 640×480.
- Detekcja MediaPipe bez kompilacji dlib; opcjonalnie zachowany dlib.
- Oryginalne wytrenowane sieci korekcji obu oczu.
- Podgląd z przełączaniem korekcji i kalibracją.
- Przetwarzanie plików, zapis MJPEG AVI, tryb headless i limit klatek.
- Czyste wyjście BGR do kamery wirtualnej.
- Zamknięcie kamery, pliku, detektora i modelu przy zakończeniu/wyjątku.
- Kontrola zgodności hashy pobranych modeli, wymagania i testy regresji.

Nie jest to port binarnego interfejsu macOS 1:1: jego kod nie został opublikowany w analizowanym repo. Nie dodano sterownika jądra własnej konstrukcji, instalatora DEB, panelu GTK/Qt ani autostartu. Celem jest uruchamialna lokalnie aplikacja i standardowa integracja wideo Linux.

## 7. Ograniczenia i dalszy rozwój

Przetwarzana jest pierwsza twarz. Nie ma śledzenia tożsamości między klatkami, wygładzania landmarków, detekcji mrugania ani bramkowania korekcji według pozy głowy. Oczy są wklejane prostokątnie z obcięciem brzegu; nie ma maski i płynnego mieszania. Te elementy mogą powodować migotanie lub szwy. Warstwa inferencji jest synchroniczna; dwóch sesji L/R nie połączono w batch. Zachowano zgodność modelu zamiast deklarować niezmierzone przyspieszenie.

Najbardziej uzasadnione dalsze prace: pomiar opóźnienia od kamery do odbiorcy, wygładzanie landmarków, wyłączenie deformacji przy mruganiu/dużej pozie, maska mieszania oczu, zapis profili ogniskowej dla różnych rozdzielczości, następnie ewentualna migracja formatu modelu po porównaniu numerycznym.

Kod upstreamu ma BSD-3-Clause. Zależności i pobrane modele mają własne warunki; licencja repozytorium sama w sobie nie rozstrzyga praw do redystrybucji wszystkich wag. Port pobiera modele z ich źródeł zamiast dołączać je do śledzonego drzewa Git.

## 8. Źródła

- Repozytorium: https://github.com/WangWilly/gaze-correction-cam
- Wagi: https://github.com/WangWilly/gaze-correction-cam/releases/tag/v0.1.1
- Artykuł wskazany przez repo: https://doi.org/10.1145/3311784
- Wyjście kamery Python: https://github.com/letmaik/pyvirtualcam
- Moduł kamery Linux: https://github.com/v4l2loopback/v4l2loopback

Wyniki rzeczywistych testów lokalnych znajdują się w `VALIDATION.md`.
