# Walidacja lokalna — 2026-10-05

> Wersja angielska (domyślna): [VALIDATION.md](VALIDATION.md).

Środowisko: Ubuntu 26.04.1 LTS, x86_64, jądro 7.0.0-34-generic, izolowany Python 3.12.15. TensorFlow 2.19.0, MediaPipe 0.10.32, OpenCV contrib 4.11.0.86, NumPy 2.1.3, pyvirtualcam 0.14.0. Pełny zestaw: `requirements-ubuntu.lock`.

## Wykonane sprawdzenia

- `python -m pytest -q tests`: **10 testów zaliczonych**. Obejmują wycinki oczu, granice obrazu, BGR→RGB, monotoniczne timestampy, plik wejściowy/wyjściowy, błędne urządzenie, zapobieganie pętli kamery, prawdziwe checkpointy L/R, brakujące wagi, zamykanie zasobów i czyste klatki na wyjściu wirtualnym (mock).
- Porównanie grafu z checkpointem: 59 zmiennych grafu, 140 zmiennych checkpointu, **0 niezgodności nazw/kształtów**. Nadmiarowe zmienne checkpointu nie są potrzebne grafowi inferencji.
- Inferencja na obu rzeczywistych checkpointach daje skończone wyniki o oczekiwanym kształcie i wynik zależny od kąta; nie użyto losowych wag jako zamiennika.
- `./run-ubuntu.sh --headless --max-frames 90`: **90 klatek**, 30,2 FPS z fizycznej kamery HP `/dev/video0`. Nie zapisywano ani nie wysyłano obrazu. Ten pomiar nie zlicza wykrytych twarzy, więc nie jest samodzielnym benchmarkiem korekcji twarzy.
- Pełna detekcja i korekcja na publicznym `https://storage.googleapis.com/mediapipe-assets/portrait.jpg`: jedna wykryta twarz, 30 iteracji, **29,0 FPS**, 1763 zmienione piksele w ostatniej klatce. Obraz skalowany do szerokości 640 px z zachowaniem proporcji. Wynik obejrzano: zmiana dotyczy oczu, reszta obrazu pozostaje zachowana. To pojedynczy test funkcjonalny, nie ocena jakości na reprezentatywnym zbiorze.
- Przetwarzanie 15-klatkowego filmu utworzonego z publicznego zdjęcia: **15 klatek zapisanych**, 23,7 FPS przetwarzania. `artifacts/portrait-input.avi` → `artifacts/portrait-output.avi`.
- `./run-ubuntu.sh --max-frames 10`: uruchomienie podglądu OpenCV w sesji GNOME/Wayland przez XWayland, odczyt 10 klatek, poprawne zakończenie. Krótki test startu, nie miarodajny benchmark FPS.
- `uv pip check`: zgodne zależności. `git diff --check` i `bash -n`: bez błędów.
- Hashy obu pobranych modeli zweryfikowano przez `scripts/download_models.py`.

## Ograniczenia walidacji

Podczas pierwszej walidacji moduł `v4l2loopback` nie był dostępny dla uruchomionego jądra. `sudo -n true` zwróciło wymaganie hasła. **Nie wykonano rzeczywistego testu odbioru przez kamerę wirtualną ani Zoom/Teams/przeglądarkę.** Kod wyjścia jest sprawdzony testem interfejsu z atrapą backendu; to nie zastępuje testu sterownika. Do konfiguracji przygotowano `scripts/setup-virtual-camera.sh`.

Nie wykonano testu backendu dlib, CUDA, innych wydań Ubuntu ani długotrwałego testu stabilności. Testy inferencji działały na CPU. Biblioteka TensorFlow wypisywała komunikaty inicjalizacji CUDA/cuDNN i `cuInit 303`, ale poprawnie wykonywała inferencję CPU; nie świadczy to o działającym przyspieszeniu GPU.

Nie testowano ręcznie każdego klawisza kalibracji. Nie wykonano pomiaru opóźnienia od ekspozycji kamery do wyświetlenia w komunikatorze. Podane FPS nie są gwarancją płynności na innych urządzeniach.

Artefakty z publicznego zdjęcia są w ignorowanym przez Git katalogu `artifacts/`. Żaden artefakt testowy nie zawiera nagrania użytkownika.

## Dodatkowa weryfikacja po instalacji modułu przez użytkownika

2026-10-05, około 11:41 czasu lokalnego środowiska poleceń:

- `v4l2loopback` jest załadowany; `v4l2-ctl --list-devices` pokazuje **Gaze Correction**, `/dev/video10`.
- Uruchomiono rzeczywisty program z korekcją: `./run-ubuntu.sh --virtual-camera /dev/video10 --headless --max-frames 1800`.
- Niezależny proces OpenCV otworzył `/dev/video10` przez V4L2 i odebrał **90 klatek 640×480 BGR**, około **31,0 FPS** w krótkim pomiarze. Średnia jasność klatek zmieniała się w zakresie 152,0–195,53. Nie zapisywano obrazu z kamery.
- Podczas nadawania urządzenie zgłasza `Video Capture`, format `YU12`, 640×480, 30 FPS. Przed nadawaniem zgłaszało `Video Output`, zgodnie z trybem exclusive_caps.
- Potwierdzono więc rzeczywisty tor aplikacja → pyvirtualcam → v4l2loopback → osobny odbiornik V4L2. Wcześniejsze ograniczenie dotyczące braku testu sterownika jest już nieaktualne.
- **Teams nadal niezweryfikowany**: narzędzie Browser zwróciło `No browser is available`, a lista dostępnych przeglądarek była pusta. Nie wykonano połączenia ani spotkania. Test V4L2 nie stanowi potwierdzenia podglądu Teams ani negocjacji WebRTC.

## Próba w Teams Web / Edge — 2026-10-05, 13:26–13:30

Po połączeniu rozszerzenia Browser otwarto zalogowany Teams (`https://teams.cloud.microsoft/`) w Edge i panel Ustawienia → Urządzenia. Pole Kamera było nieaktywne z wartością „Brak”; tak samo listy mikrofonu i głośnika. Nie było podglądu wideo. Równolegle aplikacja nadawała do `/dev/video10`, a osobny odbiornik ponownie odczytał 30 klatek 640×480. Działanie Teams nie jest więc jeszcze potwierdzone. Następny krok: ręczne sprawdzenie uprawnień witryny i odświeżenie. Próba otwarcia wewnętrznej strony ustawień Edge przez narzędzie została odrzucona przez politykę adresów Browser. Nie wykonywano połączenia ani nie dołączano do spotkania.

## Potwierdzenie Teams Web — 2026-10-05

**Wynik: podgląd kamery Gaze Correction w Teams Web działa.**

Sprawdzono Edge 154.0.4258.53 i `https://teams.cloud.microsoft/` na tym komputerze. Po udzieleniu przez użytkownika zgody na kamerę Teams widział początkowo wyłącznie fizyczną kamerę HP. `wpctl inspect` wykazał, że WirePlumber zapamiętał `/dev/video10` jako `:video_output:` przed rozpoczęciem nadawania. Restart `systemctl --user restart wireplumber` przy aktywnym nadajniku utworzył źródło **Gaze Correction (V4L2)**; kamera pojawiła się następnie na liście Teams.

W Teams wybrano Gaze Correction, a potem na ekranie przygotowania szybkiego spotkania potwierdzono tę pozycję jako wybraną. Włączono lokalny podgląd i wybrano „Nie używaj dźwięku”. Potwierdzono wizualnie obraz, a element `video` zgłaszał 512×384, `readyState=4`, `paused=false` i czas odtwarzania ponad 27 s. Proces `msedge` miał otwarte `/dev/video10` równolegle z nadajnikiem Python. To potwierdza rzeczywisty tor aplikacja → v4l2loopback → Edge → podgląd Teams, nie tylko widoczność nazwy urządzenia.

Nie klikano „Dołącz teraz”, nie wykonywano rozmowy testowej ani nie wysyłano zaproszeń. Ekran przygotowania zamknięto przyciskiem „Anuluj”. Nie testowano odbioru obrazu przez drugiego uczestnika ani jakości transmisji sieciowej. Zrzuty oglądano w narzędziu podczas testu; nie zapisano prywatnego obrazu jako pliku w repozytorium.
