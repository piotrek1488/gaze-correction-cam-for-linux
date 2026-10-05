# Ubuntu — instalacja i uruchomienie

> Wersja angielska (domyślna): [UBUNTU.md](UBUNTU.md).

Port znajduje się w `ubuntu_camera.py`. Oryginalny interfejs macOS nie jest częścią publicznego kodu; wersja Ubuntu używa okna OpenCV i kamery V4L2. Przetwarzanie odbywa się lokalnie.

## Ten komputer

Przygotowano lokalne `.venv` z Pythonem 3.12 oraz modele. Uruchom:

```bash
cd ~/git/gaze-correction-cam
./run-ubuntu.sh
```

Domyślne wejście: `/dev/video0`, detekcja MediaPipe. `g` włącza/wyłącza korekcję, `c` otwiera kalibrację, `q` lub Escape kończy. W kalibracji strzałki zmieniają położenie kamery XY, `+/-` — Z, `[/]` — ogniskową, `r` przywraca wartości z początku sesji. Ustawienia są zapisywane w `user_settings.db`. Domyślna geometria pochodzi z upstreamu i wymaga dopasowania do monitora/laptopa.

```bash
./run-ubuntu.sh --camera /dev/video2
./run-ubuntu.sh --headless --max-frames 100
./run-ubuntu.sh --input /ścieżka/wejście.mp4 --output /ścieżka/wynik.avi --headless
./run-ubuntu.sh --no-correction  # jawny test samej kamery
```

Plik wynikowy zawiera wyłącznie obraz, bez dźwięku. `--fps` ustawia oczekiwaną szybkość kamery/wyjścia, ale nie gwarantuje szybkości inferencji. Przy powolnym przetwarzaniu nagranie z kamery może odtwarzać się szybciej niż czas rzeczywisty. Nagrania z plików zachowują FPS źródła.

## Kamera w Zoom / Teams / przeglądarce

Jednorazowo zainstaluj moduł dla bieżącego jądra (skrypt pyta `sudo` o hasło):

```bash
./scripts/setup-virtual-camera.sh
./run-ubuntu.sh --virtual-camera /dev/video10
```

W komunikatorze wybierz **Gaze Correction**. Najpierw uruchom producenta obrazu, potem otwórz listę kamer komunikatora. Podgląd zawiera napisy, lecz kamera wirtualna i nagranie otrzymują czysty obraz.

Po restarcie moduł trzeba ponownie załadować:

```bash
sudo modprobe v4l2loopback devices=1 video_nr=10 card_label='Gaze Correction' exclusive_caps=1
```

Jeśli moduł jest już załadowany, `modprobe` nie zmieni jego istniejących parametrów: wybierz istniejące urządzenie loopback z `v4l2-ctl --list-devices`. Nie usuwaj modułu, gdy używa go OBS lub inny program. Numer 10 musi być wolny. Secure Boot może wymagać zapisania klucza MOK podczas instalacji DKMS. Wejście i wyjście muszą być różnymi urządzeniami.

Mechanizm wyjścia oparto na [pyvirtualcam](https://github.com/letmaik/pyvirtualcam) i [v4l2loopback](https://github.com/v4l2loopback/v4l2loopback).

## Instalacja na innym Ubuntu

Wspierana konfiguracja zależności portu: Python **3.12**, Linux x86_64. Nie używaj systemowego Pythona 3.14 do instalacji tych przypiętych bibliotek.

```bash
sudo apt-get install python3.12-venv libgl1 libglib2.0-0
./scripts/setup-ubuntu.sh
```

Jeśli dystrybucja nie dostarcza Pythona 3.12, zainstaluj go oddzielnie, np. przez uv, i przekaż ścieżkę w `PYTHON_BIN`. Skrypt nie zmienia systemowego interpretera. Można też przygotować środowisko przez `uv venv --python 3.12 .venv`, zainstalować `requirements-ubuntu.txt` przez `uv pip install --python .venv/bin/python -r requirements-ubuntu.txt`, a następnie uruchomić `.venv/bin/python scripts/download_models.py`.

Główne zależności mają przypięte wersje w `requirements-ubuntu.txt`; pełny zestaw sprawdzony lokalnie zapisano w `requirements-ubuntu.lock`. Plik `poetry.lock` pochodzi z upstreamu i nie jest używany przez instalator Ubuntu.

Domyślny backend MediaPipe nie wymaga kompilowania dlib. Backend `--backend dlib` wymaga dodatkowej instalacji dlib i `lm_feat/shape_predictor_68_face_landmarks.dat` z upstreamowego wydania v0.1.1.

Pobieranie modeli sprawdza SHA256. Wagi korekcji pochodzą z [wydania v0.1.1](https://github.com/WangWilly/gaze-correction-cam/releases/tag/v0.1.1), a detektor z wersjonowanego magazynu modeli MediaPipe. Nie są to modele wytrenowane ponownie w ramach portu.

## Diagnostyka

- Brak obrazu: sprawdź urządzenie, uprawnienia oraz czy kamera nie jest zajęta.
- Błąd checkpointu: uruchom `.venv/bin/python scripts/download_models.py`. Program przerywa pracę przy błędzie inferencji, zamiast pokazywać niezmieniony obraz jako działającą korekcję.
- Brak okna: uruchom w sesji graficznej albo użyj `--headless` z wyjściem lub limitem klatek.
- Nie instaluj jednocześnie `opencv-python`, `opencv-contrib-python` i wariantów headless w tym środowisku: współdzielą moduł `cv2`.
- Jakość: okulary, silny obrót głowy, mruganie i duże kąty mogą powodować artefakty. Model koryguje małe wycinki oczu; nie rekonstruuje całej twarzy.

Testy: `.venv/bin/python -m pytest -q tests`. Wymagają zainstalowanego pytest i pobranych modeli. Test checkpointów wykonuje inferencję dla obu oczu i sprawdza reakcję na zmianę kąta; nie jest oceną fotorealizmu.

## Teams / Edge widzi HP, ale nie Gaze Correction

Na tym Ubuntu 26.04 / PipeWire 1.6.2 wykryto, że WirePlumber może zapamiętać urządzenie `v4l2loopback` jako wyjściowe, gdy zeskanuje je przed startem nadajnika. Wtedy poprawny odbiór przez OpenCV nie oznacza jeszcze widoczności w Teams.

1. Uruchom `./run-ubuntu.sh --virtual-camera /dev/video10` i pozostaw aplikację działającą.
2. W drugim terminalu sprawdź `wpctl status`: kamera musi występować w **Video → Sources**, nie tylko w Devices.
3. Jeśli nie ma jej w Sources, poza trwającą rozmową wykonaj `systemctl --user restart wireplumber`. To na chwilę przerywa obsługę audio/wideo; sprawdź potem wyjście dźwięku, szczególnie słuchawki Bluetooth.
4. W Teams wybierz **Ustawienia → Urządzenia → Kamera → Gaze Correction**. Jeśli lista nie odświeży się automatycznie, odśwież kartę Teams.
5. Witryna `teams.cloud.microsoft` musi mieć zgodę przeglądarki na dostęp do kamery.

Na tym komputerze potwierdzono działający lokalny podgląd w Teams. Aplikacja Python musi nadawać przez cały czas używania kamery w rozmowie.
