# Architektura i dokumentacja modułów

> Wersja angielska (domyślna): [architecture.md](architecture.md).
> Dokumentacja dla programistów systemu Gaze Correction Camera.
> Instrukcja instalacji i użycia dla użytkownika: [README](../README.md).

## Przegląd systemu

To **system korekcji spojrzenia w czasie rzeczywistym**, który przekierowuje kierunek wzroku w strumieniach wideo, tworząc naturalny kontakt wzrokowy podczas rozmów wideo. System wykorzystuje detekcję twarzy, punkty charakterystyczne twarzy (landmarki) oraz modele uczenia głębokiego do deformacji obszarów oczu.

## Struktura plików i organizacja modułów

### 1. Punkty wejścia (bin\_\*.py)

#### bin_single_window.py ⭐ *Główna aplikacja*

- **Cel**: jednookienkowa aplikacja korekcji spojrzenia ze sterowaniem w czasie rzeczywistym
- **Funkcje**:
  - Automatyczne wykrywanie rozdzielczości kamery
  - Włączanie/wyłączanie korekcji spojrzenia (klawisz `g`)
  - Tryb kalibracji do regulacji przesunięcia kamery (klawisz `c`)
  - Obsługa wielu backendów (dlib/MediaPipe)
- **Przepływ**: `Wejście kamery → FacePredictor → GazeCorrector → Wyświetlanie`

#### bin_focal_length_calibration.py

- Samodzielne narzędzie do kalibracji ogniskowej kamery

#### bin_test_mediapipe_detection.py

- Narzędzie testowe do detekcji twarzy przez MediaPipe

### 2. Moduły rdzenia (displayers/)

Katalog `displayers/` zawiera główne komponenty logiki biznesowej:

#### face_predictor.py — detekcja twarzy i ekstrakcja landmarków

**Cel**: abstrakcyjny interfejs dla backendów detekcji twarzy

**Kluczowe klasy**:

- `FacePredictor` (ABC): interfejs detekcji twarzy
- `DlibFacePredictor`: implementacja z użyciem dlib (68 landmarków)
- `MediaPipeFacePredictor`: implementacja z użyciem Google MediaPipe
- Klasy danych: `FaceData`, `EyeData`, `EyeLandmarks`

**Proces**: `Klatka wejściowa → Detekcja twarzy → Predykcja landmarków → Ekstrakcja oczu → EyeData`

**Wyjście**: `FaceData` zawierające:

- Obrazy lewego/prawego oka (znormalizowane 48×64)
- Mapy kotwic (mapy punktów charakterystycznych do naprowadzania przestrzennego)
- Współrzędne środka oka
- Pierwotne położenia w klatce

#### gaze_corrector.py — model korekcji spojrzenia

**Cel**: opakowuje modele TensorFlow do korekcji spojrzenia

**Kluczowe klasy**:

- `GazeModel`: opakowanie modelu TensorFlow (ładuje modele oka L/R)
- `GazeCorrector`: interfejs wysokiego poziomu do korekcji spojrzenia
- `CameraConfig`: geometria kamery (ogniskowa, IPD, przesunięcie kamery)

**Proces**:

```
EyeData + geometria kamery → inferencja modelu TF → zdeformowany obraz oka
                           ↓
                    obliczenie kąta (geometria 3D)
```

**Komponenty**:

1. **Ładowanie modelu**: ładuje osobne modele TensorFlow oka L/R z `weights/`
2. **Obliczenie kąta**: wyznacza kąt przekierowania spojrzenia na podstawie:
   - Pozycji oka w przestrzeni 3D
   - Pozycji kamery względem ekranu
   - Docelowego kierunku spojrzenia (ku kamerze)
3. **Deformacja oka**: stosuje wyuczoną transformację do przekierowania spojrzenia

**Geometria kamery**:

- `focal_length`: ogniskowa kamery (piksele)
- `ipd`: rozstaw źrenic (cm)
- `camera_offset`: pozycja kamery (X, Y, Z) względem środka ekranu

#### dis_single_window.py — orkiestrator aplikacji

**Cel**: główna logika aplikacji koordynująca wszystkie komponenty

**Kluczowa klasa**: `SingleWindowGazeCorrector`

**Odpowiedzialności**:

1. Przechwytywanie obrazu z kamery i przetwarzanie klatek
2. Potok FacePredictor → GazeCorrector
3. Przełączanie korekcji w czasie rzeczywistym
4. Interfejs trybu kalibracji
5. Składanie klatki wynikowej

**Potok**:

```
Klatka z kamery
    ↓
Skalowanie do detekcji twarzy (320×240)
    ↓
FacePredictor.list_eye_data()
    ↓
Dla każdego oka:
    - Jeśli gaze_enabled: GazeCorrector.correct_eye()
    - W przeciwnym razie: użyj oryginalnego obrazu oka
    ↓
Wklejenie skorygowanych oczu do oryginalnej klatki
    ↓
Narysowanie nakładki statusu
    ↓
Wyświetlenie w oknie
```

### 3. Modele TensorFlow (tf_models/)

#### flx.py — architektura modelu FLX

**Cel**: definiuje architekturę sieci neuronowej do korekcji spojrzenia

**Kluczowe komponenty**:

- `encoder()`: koduje kąt spojrzenia w przestrzenną mapę cech
- `trans_module()`: moduł transformacji z połączeniami skrótowymi (skip connections)
- `apply_lcm()`: modulacja barwy światła (Light Color Modulation) dla realistycznego renderowania
- `inference()`: główny przebieg w przód łączący wszystkie komponenty

**Architektura**:

```
Obraz oka + mapa kotwic + kąt
    ↓
[CNN ekstrakcji cech]
    ↓
[Enkoder kąta] → przestrzenna mapa cech
    ↓
[Moduł transformacji (gęsty CNN)]
    ↓
[Generowanie pola przepływu]
    ↓
[Transformator przestrzenny] → zdeformowany obraz
    ↓
[Modulacja barwy światła]
    ↓
Skorygowany obraz oka
```

#### transformation.py — transformator przestrzenny

**Cel**: implementuje różniczkowalną deformację obrazu

**Kluczowe funkcje**:

- `meshgrid()`: generuje siatkę współrzędnych
- `interpolate()`: interpolacja biliniowa dla płynnej deformacji
- `apply_transformation()`: stosuje pole przepływu do deformacji obrazu

**Zastosowanie**: nakładanie wyuczonych pól przemieszczenia pikseli na obrazy oczu

#### tf_utils.py

- Wspólne narzędzia TensorFlow
- Bloki CNN/DNN z normalizacją wsadową (batch normalization)

### 4. Narzędzia (utils/)

#### config.py — zarządzanie konfiguracją

**Cel**: scentralizowana konfiguracja przy użyciu argparse

**Parametry**:

- Wymiary modelu (height=48, width=64, ef_dim=12)
- Parametry kamery (ogniskowa, IPD, przesunięcie kamery)
- Ustawienia sieciowe (IP, porty dla trybu wieloprocesowego)

#### logger.py — narzędzie logowania

**Cel**: sformatowane logowanie ze znacznikami czasu i identyfikatorami wątków

**Format**: `2026-01-27 10:30:45.123 Python[12345:67890] +[ClassName]: Message`

## Potok przepływu danych

```
┌─────────────────────────────────────────────────────────────────┐
│                        GŁÓWNA APLIKACJA                         │
│                     (bin_single_window.py)                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ↓
         ┌─────────────────────────────┐
         │  Przechwytywanie (OpenCV)   │
         │  Oryginał: 640×480          │
         └─────────────┬───────────────┘
                       │
                       ↓
         ┌─────────────────────────────┐
         │  Skalowanie do detekcji     │
         │  Zmniejszone: 320×240       │
         └─────────────┬───────────────┘
                       │
                       ↓
┌──────────────────────────────────────────────────────────────────┐
│                    WARSTWA DETEKCJI TWARZY                       │
│                  (displayers/face_predictor.py)                  │
├──────────────────────────────────────────────────────────────────┤
│  • Wykryj twarz(e) w klatce                                      │
│  • Przewidź 68 landmarków twarzy (dlib) LUB                      │
│  • Przewidź 478 landmarków (MediaPipe)                           │
│  • Wytnij obszary oczu (6 punktów na oko)                        │
│  • Przeskaluj obrazy oczu do 48×64                               │
│  • Wygeneruj mapy kotwic (mapy cech landmarków)                  │
└─────────────┬────────────────────────────────────────────────────┘
              │
              ↓ Wyjście: List[FaceData]
              │
┌─────────────────────────────────────────────────────────────────┐
│  FaceData {                                                     │
│    left_eye: EyeData {                                          │
│      image: 48×64×3 (znormalizowane)                            │
│      anchor_map: 48×64×12 (punkty cech)                         │
│      center: (x, y)                                             │
│      top_left: (row, col)                                       │
│    }                                                            │
│    right_eye: EyeData {...}                                     │
│  }                                                              │
└─────────────┬───────────────────────────────────────────────────┘
              │
              ↓
┌──────────────────────────────────────────────────────────────────┐
│                   WARSTWA KOREKCJI SPOJRZENIA                    │
│                 (displayers/gaze_corrector.py)                   │
├──────────────────────────────────────────────────────────────────┤
│  Dla każdego oka:                                                │
│    1. Oblicz pozycję oka 3D z landmarków                         │
│    2. Wyznacz kąt przekierowania spojrzenia (ku kamerze)         │
│    3. Podaj do modelu TensorFlow:                                │
│       • Obraz oka (48×64×3)                                      │
│       • Mapę kotwic (48×64×12)                                   │
│       • Kąt spojrzenia (θx, θy)                                  │
│    4. Model zwraca zdeformowany obraz oka                        │
└─────────────┬────────────────────────────────────────────────────┘
              │
              ↓
┌──────────────────────────────────────────────────────────────────┐
│                      MODEL TensorFlow                           │
│                     (tf_models/flx.py)                           │
├──────────────────────────────────────────────────────────────────┤
│  [Enkoder] → kąt na przestrzenną mapę cech                       │
│  [CNN ekstrakcji cech] → cechy obrazu                            │
│  [Moduł transformacji] → predykcja pola przepływu                │
│  [Transformator przestrzenny] → nałożenie deformacji             │
│  [Moduł barwy światła] → dostosowanie oświetlenia                │
└─────────────┬────────────────────────────────────────────────────┘
              │
              ↓ Skorygowany obraz oka (48×64×3)
              │
┌──────────────────────────────────────────────────────────────────┐
│                    SKŁADANIE I WYŚWIETLANIE                      │
│                (dis_single_window.py)                            │
├──────────────────────────────────────────────────────────────────┤
│  1. Przeskaluj skorygowane oczy do pierwotnego rozmiaru          │
│  2. Wklej na oryginalną klatkę 640×480 w pozycjach oczu          │
│  3. Narysuj nakładkę statusu (GAZE ON/OFF)                       │
│  4. Narysuj nakładkę kalibracji (jeśli włączona)                 │
│  5. Wyświetl w oknie OpenCV                                      │
└──────────────────────────────────────────────────────────────────┘
```

## Kluczowe wzorce projektowe

### 1. Wstrzykiwanie zależności (Dependency Injection)

- `FacePredictor` jest wstrzykiwalny → łatwa zamiana backendów (dlib ↔ MediaPipe)
- `GazeCorrector` jest wstrzykiwalny → testowalny i modułowy

### 2. Interfejs abstrakcyjny

- `FacePredictor` to abstrakcyjna klasa bazowa
- Implementacje: `DlibFacePredictor`, `MediaPipeFacePredictor`

### 3. Obiekty konfiguracji

- Dataclasses dla konfiguracji (niezmienne, bezpieczne typowo)
- `DisplayConfig`, `CameraConfig`, `GazeModelConfig` itd.

### 4. Rozdzielenie odpowiedzialności

- Detekcja twarzy ≠ korekcja spojrzenia
- Logika wyświetlania ≠ inferencja modelu
- Konfiguracja ≠ logika biznesowa

## Odpowiedzialności modułów

| Moduł                 | Wejście                    | Wyjście          | Odpowiedzialność                   |
| --------------------- | -------------------------- | ---------------- | ---------------------------------- |
| **face_predictor**    | Klatka (BGR)               | `List[FaceData]` | Wykrywanie twarzy, ekstrakcja oczu |
| **gaze_corrector**    | `FaceData` + konfig kamery | Skorygowana klatka | Nałożenie modelu korekcji spojrzenia |
| **flx.py**            | Obraz oka + kotwice + kąt  | Zdeformowane oko | Inferencja sieci neuronowej        |
| **transformation.py** | Pole przepływu + obraz     | Zdeformowany obraz | Transformacja przestrzenna       |
| **dis_single_window** | Strumień z kamery          | Okno wyświetlania | Orkiestracja potoku, interfejs    |

## Jak to działa (ogólnie)

1. **Przechwyć** klatkę wideo z kamery
2. **Wykryj** twarz i wyodrębnij 68 landmarków twarzy
3. **Wytnij** obszary lewego/prawego oka (po 48×64)
4. **Oblicz** pozycję oka 3D i wymagany kąt spojrzenia
5. **Przeprowadź inferencję** przez wytrenowany CNN, aby wygenerować pole przepływu deformacji
6. **Zdeformuj** obraz oka przy użyciu transformatora przestrzennego
7. **Złóż** skorygowane oczy z powrotem na oryginalną klatkę
8. **Wyświetl** wynik w czasie rzeczywistym

Kluczową innowacją jest **wyuczona transformacja deformująca**, która realistycznie przekierowuje spojrzenie, zachowując wygląd, oświetlenie i teksturę oka.

## Źródła

Implementacja opiera się na badaniach nad technikami korekcji spojrzenia z użyciem splotowych sieci neuronowych bazujących na deformacji (warping).
