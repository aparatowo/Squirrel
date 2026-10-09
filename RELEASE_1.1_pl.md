# 🐿️ Squirrel! 1.1

*[English version](RELEASE_1.1_en.md)*

W wersji 1.1 Squirrel może sygnalizować zdarzenia na dwa nowe sposoby: brzęczykiem i wbudowaną diodą RGB. Nowy tryb ciszy nocnej sprawia, że w wybranych godzinach urządzenie milczy. Po powrocie do menu podświetlona jest ostatnio otwarta pozycja, a czcionka z polskimi znakami jest wbudowana w firmware, więc nie trzeba już wgrywać jej osobno. Naprawiony został też skrypt budujący: wgrywanie działa niezawodnie, a urządzenie samo uruchamia nowy firmware.

---

## Nowości

### 🔔 Brzęczyk (opcjonalny) — działa

Do Cardputera ADV można dolutować brzęczyk sterowany tranzystorem NPN. Jego działanie sprawdzono na urządzeniu.

- **Podłączenie:**
  - G13 na złączu EXT, przez rezystor (np. 1 kΩ), do bazy tranzystora;
  - emiter do GND;
  - brzęczyk między zasilaniem a kolektorem;
  - dodatkowy rezystor ok. 10 kΩ między bazą a GND, żeby brzęczyk nie odezwał się przy włączaniu, zanim program przejmie pin.
- **Stan spoczynku:** gdy brzęczyk milczy, pin jest zawsze w stanie niskim.
- **Niedozwolone piny:** G8 i G9 to magistrala I2C klawiatury, więc Squirrel nie pozwoli ich użyć. Na złączu EXT wolne są G5, G13 i G15.
- **Funkcje:** dla każdej z nich osobno włączasz brzęczyk i wybierasz tryb (domyślnie brzęczyk jest wyłączony we wszystkich):
  - powiadomienia,
  - bloki Pomodoro i Treningu,
  - metronom,
  - kukułka.
- **Tryby:** click, short, double, triple, long, alarm, sos albo auto. Auto oznacza, że funkcja sama dobiera sygnał, tak samo jak dla głośnika, np. inny dla ciężkiego bloku treningu, a inny dla przerwy.
- **Ustawienia i status:** *Settings → Personalize → Buzzer*. Po wybraniu trybu brzęczyk od razu go odtwarza, żeby było słychać, jak brzmi.
- **Wypróbowanie trybów:** *Settings → Experimental → Buzzer test*.
- **Konfiguracja w `nuts.py`:**
  - bez brzęczyka: `BUZZER_INSTALLED = False`;
  - brzęczyk pasywny (bez własnego generatora): w `BUZZER_PWM_FREQ` wpisz częstotliwość tonu, np. 2700.

### 🌈 Dioda RGB — działa

Squirrel korzysta teraz z diody RGB wbudowanej w Cardputer ADV (G21); jej działanie sprawdzono na urządzeniu. Dioda jest zasilana przez obwód podświetlenia ekranu, dlatego gdy coś pokazuje, podświetlenie przechodzi na pełną jasność (szczegóły w części *Znane ograniczenia*).

- **Powiadomienia, Pomodoro i Trening, metronom, kukułka:** dla każdej funkcji osobno wybierasz kolor i tryb: flash, double, triple, long, pulse, alarm, sos albo off.
- **Ćwiczenie oddechowe:**
  - przy wdechu dioda świeci na zielono coraz jaśniej;
  - przy wstrzymaniu oddechu świeci na zielono;
  - przy wydechu świeci na niebiesko i powoli gaśnie.
- **Ładowanie:** dioda wolno miga w kolorze odpowiadającym poziomowi baterii, tak jak paski stanu: niebieski, zielony, żółty, czerwony. Działa to tylko na urządzeniach, które zgłaszają ładowanie; Cardputer ADV tego nie robi, więc na nim światło ładowania się nie zapala.
- **Jasność:** regulowana, domyślnie 30%, bo dioda świeci bardzo mocno.
- **Domyślnie** wszystkie funkcje diody są wyłączone. Włącza się je w *Settings → Personalize → LED*.
- **Podgląd:** po wybraniu trybu lub koloru dioda od razu go pokazuje, a po zmianie jasności błyska na biało.
- **Testy:** *Settings → Experimental → LED test* zawiera cztery osobne testy (stałe kolory, miganie w różnych odstępach, skokowa zmiana jasności, płynne rozjaśnianie i ściemnianie) oraz podmenu *Modes* do wypróbowania trybów.

### 🌙 Cisza nocna

W *Settings → Silent mode* godziny ciszy ustawia się osobno dla dźwięku, brzęczyka i diody.

- **Godziny:** domyślnie od 22:00 do 6:00. Ustawienie 00:00–00:00 wyłącza ciszę nocną.
- **Dni tygodnia:** wybiera się je tak samo jak w rutynach. Noc należy do dnia, w którym się zaczyna: zaznaczony piątek oznacza ciszę od piątku 22:00 do soboty 6:00.
- **Co jest wyciszane:** powiadomienia, rutyny, kukułka i sygnały Pomodoro nie wydają dźwięku i nie migają. Gaśnie też światło ładowania. Same powiadomienia nadal pojawiają się na ekranie.
- **Co działa dalej:** funkcje uruchamiane ręcznie, czyli metronom, ćwiczenie oddechowe i testy.
- **Bez ustawionego zegara** cisza nocna nie działa, bo urządzenie nie wie, która jest godzina.

### 🧭 Menu zapamiętuje pozycję

**Przy cofaniu się** podświetlona jest ostatnio otwarta pozycja:
- po zamknięciu notatki — ta notatka;
- po wyjściu z odtwarzacza — to nagranie;
- w menu nadrzędnym — podmenu, z którego się wróciło.

**Przy wchodzeniu** do menu podświetlona jest pierwsza pozycja, tak jak dotąd.

### 📊 Dziennik energii (domyślnie włączony)

Squirrel co 10 minut zapisuje jedną linię danych o zużyciu energii:
- poziom i napięcie baterii;
- ile czasu ekran był przygaszony, a procesor zwolniony;
- ile razy urządzenie usypiało;
- ile czasu świeciła dioda, działał głośnik i radio.

- **Po co:** te dane pomogą rozwijać zaplanowane funkcje, czyli tryb hiperoszczędny i spokojniejszy ekran.
- **Gdzie:** plik `/sd/Squirrel/battery.csv` na karcie SD. Można go otworzyć na komputerze, np. w arkuszu kalkulacyjnym. Zdarzenia i błędy trafiają osobno do `/flash/boot_log.txt` w pamięci urządzenia.
- **Prywatność:** dane nie są nigdzie automatycznie przesyłane i zostają na urządzeniu. Udostępnienie pliku autorowi jest wyłącznie dobrą wolą użytkownika, ale każda taka pomoc jest bardzo cenna.
- **Koszt:** jedna linia co 10 minut, a stan urządzenia jest sprawdzany raz na sekundę, więc logowanie praktycznie nie zużywa energii.
- **Wyłączenie:** *Settings → Personalize → Power → Battery log*.

### ✍️ Polskie znaki w firmware

Czcionka z polskimi znakami jest częścią obrazu firmware. Nie trzeba jej wgrywać osobno, a aktualizacja jej nie usunie.

---

## Pozostałe zmiany

- **Wygaszanie ekranu:** osobne ustawienia dla zegara i dla pozostałych ekranów, oba domyślnie 5 s (*Personalize → Screen*).
- **Metronom:** nowe odstępy między uderzeniami: 1/8, 1/4 i 1/2 sekundy (obok dotychczasowych 1, 2, 5, 30, 60 i 120 s).
- **Krótkie nagrania:** nagranie krótsze niż sekunda nie jest zapisywane, więc przypadkowe naciśnięcie G0 nie zostawia pustych plików.
- **Statystyki:**
  - wykonane rutyny i zadania trafiają na kartę od razu;
  - czas skupienia — co 15 minut i przy każdej pauzie;
  - historia jest wczytywana dopiero po otwarciu statystyk.
- **Plik `config.txt`:**
  - przechowuje ustawienia na wypadek wyłączenia urządzenia i nie jest już sprawdzany co kilka sekund;
  - zmiany wprowadzone w pliku na komputerze zaczynają działać po wybudzeniu ekranu, po *Settings → Reload config* albo po ponownym uruchomieniu.
- **Mniej zapisów w pamięci flash:** rutynowe zdarzenia, np. przejścia między ekranami, nie trafiają już do logu. W trybie DEV log nadal zapisuje wszystko.
- **Menu:**
  - nowa kolejność w *Focus Tools*: Cuckoo Clock, Routines, Pomodoro, Metronome, Training, Breathing, Statistics;
  - nowa pozycja w *Settings*: *Silent mode*;
  - nowe pozycje w *Experimental*: *Buzzer test* i *LED test*;
  - wszystkie nazwy ustawień mieszczą się na ekranie; wskazówki, które były w nich zawarte (jednostki, znaczenie zera itp.), pokazują się po wejściu w ustawienie i jako komentarze w `config.txt`;
  - dni tygodnia są wyświetlane z odstępami, a niezaznaczone oznacza kreska (`M T W T F - -`); menu *Silent mode* pokazuje je przy każdej pozycji.
- **Nagłówki menu:** belki z `#` wypełniają całą szerokość ekranu, a tytuł jest wyśrodkowany niezależnie od używanej czcionki.
- **Powroty z ekranów:** *Set Time* i *Time via WiFi* wracają do *Time and date*, a *WiFi networks* do *Connections*, zamiast do *Settings*.

---

## Aktualizacja z poprzedniej wersji

- **Ustawienia:** `config.txt` na karcie SD zostaje. Przy pierwszym uruchomieniu Squirrel dopisze do niego nowe ustawienia, chyba że plik zawiera błędną linię. Błąd jest wtedy opisany w logu, w wierszach zaczynających się od `[CONFIG]`.
- **Dawne ustawienie wygaszania:** linia `SCREEN_DIM_SECONDS` nie jest już używana. Trafi na koniec pliku jako nierozpoznana i można ją usunąć.
- **Dziennik energii:** zachowane ustawienia obejmują też dawne wyłączenie dziennika (`BATTERY_LOG = false`). Aby go włączyć, wybierz *Settings → Personalize → Power → Battery log*. Plik dziennika z poprzedniej wersji zostanie zachowany jako `battery.old.csv`.
- **Notatki, zadania, nagrania i statystyki** pozostają bez zmian. Plik statystyk skupienia w starym formacie jest odczytywany poprawnie.

---

## Dla osób budujących firmware

- **Naprawiony skrypt budujący (`build_firmware.py`):**
  - urządzenie, które przed wgrywaniem jest już w trybie pobierania (G0 przytrzymany przy podłączaniu), nie jest resetowane. Wcześniej reset wyprowadzał je z tego trybu, port USB znikał i wgrywanie się nie udawało. Z resetu skrypt korzysta dopiero wtedy, gdy na urządzeniu działa aplikacja;
  - po wgraniu urządzenie jest restartowane watchdogiem, dzięki czemu nowy firmware startuje sam. Po zwykłym resecie ESP32-S3 zostawał w trybie pobierania;
  - czcionka trafia do partycji systemowej obrazu (`/system/common/font/squirrel.vlw`);
  - raport `sq_info` sprawdza także folder `hw/`.
- **Pakiet `hw/`:** moduły bezpośrednio obsługujące sprzęt (klawiaturę, kartę SD, zegar, dźwięk, baterię, zarządzanie energią, radio, brzęczyk i diodę) przeniesiono do nowego pakietu `hw/`. Przy instalacji z plików i w trybie DEV wgrywaj cały folder `hw/`, tak jak `screens/`. Folder o tej nazwie na urządzeniu przesłania cały pakiet wbudowany w firmware.
- **Miejsce:** partycja aplikacji jest zajęta w 95%, wolne jest ok. 250 KB.

---

## Znane ograniczenia

- **Dioda i podświetlenie:** dioda Cardputera ADV jest zasilana przez ten sam obwód co podświetlenie ekranu. Jasność podświetlenia regulowana jest szybkim włączaniem i wyłączaniem zasilania (PWM), więc przy jasności niższej niż pełna dioda nie dostaje stałego zasilania i działa zawodnie. Dlatego, dopóki dioda coś pokazuje, Squirrel ustawia podświetlenie na pełną jasność, 255 (`LED_MIN_BACKLIGHT` w `nuts.py`), i przy przygaszonym ekranie mignięcie diody na chwilę go rozjaśnia. Gdy funkcje diody są wyłączone, podświetlenie działa normalnie.
- **Stan ładowania:** Cardputer ADV nie zgłasza, czy się ładuje (napięcie baterii jest jedynie mierzone przez przetwornik ADC). Firmware odpowiadał wtedy zawsze „ładuje się”, więc Squirrel traktuje ten stan jako nieznany: światło ładowania się nie zapala, a w logu baterii kolumna `charging` jest pusta.
- **Wgrywanie przy działającej aplikacji:** esptool nie zawsze przełączy urządzenie w tryb pobierania. Wtedy przytrzymaj G0 podczas podłączania kabla USB.
- **Brak modułu DS1302:** zegar jest wtedy ustawiany przy starcie przez Wi-Fi. Przez kilka sekund urządzenie może wtedy nie reagować na klawisze.
