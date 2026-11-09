# Campus Tycoon: Audit-Bericht

Stand: 2026-11-09, Branch `audit` (von `main`, Commit `abc439a`). Reiner Analyse-Auftrag: Es wurde
kein Code, kein Test und keine Spec geändert. Die einzige neue Datei ist dieser Bericht.

Gemessen wurde auf einer Kopie der App (Port 8770, eigener leerer Spielstand), damit der echte
Spielstand in `data/` unberührt bleibt. Der Code der Kopie ist identisch mit dem Branch.

## 1. Kurzfazit

1. Alle 785 Tests bestehen. Die Regeln aus `AGENTS.md` (Cent als Ganzzahl, abgelehnte Aktion ändert nichts, Seed, keine Regel im Browser, nichts von außen) sind eingehalten, mit den Ausnahmen unten.
2. **Das Ruckeln hat eine Hauptursache:** der Weichzeichner für Schatten in `static/world/primitives.js:110`. Er kostet 66 bis 160 ms pro Frame. Mit ihm läuft die Welt mit 6 bis 12 Bildern pro Sekunde, ohne ihn mit 60.
3. Zweite Ursache: Der Zeitschritt ist bei 40 ms gedeckelt (`main.js:300`). Bei niedriger Bildrate läuft die Figur deshalb in Zeitlupe (gemessen 1,05 statt 3,5 Felder pro Sekunde).
4. Der Server ist nicht die Ursache: Ein Tick braucht 1 bis 4 ms.
5. Während ein Tag läuft, wird das offene Seiten-Fenster jede Sekunde neu aufgebaut. Getippte Mengen springen zurück, Klicks gehen verloren (`ui.js:277`).
6. Das echte Wetter ist vor dem Öffnen des Tages ablesbar ("Why this number?"). Die Vorhersage mit 20 % Fehlerquote ist damit wirkungslos.
7. Die Balance kippt: Der Surf Shop bringt rund 25.000 € pro Saison, das ganze Cafe rund 1.500 €. Es gibt eine Sackgasse (Kasse 0, Lager leer) und eine Falle (Shop ohne Mitarbeiterplatz verdient nichts).
8. Empfehlung: zuerst vier kleine Fix-Specs (Schatten und Zeitschritt, Fenster-Neuaufbau, Wetter-Leck, Balance), dann die Roadmap-Features.

## 2. Priorisierte Tabelle

Schwere: kritisch, hoch, mittel, niedrig. Aufwand: S (bis ein halber Tag), M (ein bis zwei Tage), L (drei Tage und mehr).

| ID | Titel | Schwere | Aufwand | Datei:Zeile | Fix-Vorschlag |
|---|---|---|---|---|---|
| P1 | Schatten-Weichzeichner: 35 Mal pro Frame, 66 bis 160 ms | kritisch | S | `static/world/primitives.js:110` | `ctx.filter` entfernen. Weichen Schatten als radialen Verlauf zeichnen oder einmal vorzeichnen und als Bild einsetzen |
| P2 | Zeitschritt gedeckelt: Zeitlupe unter 25 Bildern pro Sekunde | hoch | S | `static/world/main.js:300` | Deckel auf 0,1 s anheben und die Bewegung in Teilschritten von höchstens 0,04 s rechnen |
| U1 | Seiten-Fenster wird bei jedem Tick neu gebaut: Eingabe und Klicks gehen verloren | hoch | S bis M | `static/world/ui.js:277`, `ui.js:341` | Fenster nur neu zeichnen, wenn sich sein Inhalt geändert hat (wie beim Shift-Fenster, `ui.js:648`); getippte Werte behalten |
| B1 | Echtes Wetter vor dem Öffnen des Tages sichtbar | hoch | M | `app.py:176`, `logic.py:824`, `logic.py:904` | Vor dem Öffnen Kunden und Erklärung mit dem Vorhersage-Wetter rechnen; neuer Test |
| G1 | Surf Shop dominiert, Geld explodiert ab Tag 10 | hoch | M | `logic.py:26-39`, `logic.py:114-135`, `logic.py:808-814` | Kosten, Preise, Kundenzahl und Freischalt-Preise der teuren Shops neu ansetzen; Simulation als Prüfung |
| B2 | Sackgasse: Kasse 0 und Lager leer, Lauf ist verloren | mittel | S | `logic.py:351-392`, `logic.py:293-315` | Kauf ablehnen oder warnen, wenn danach keine einzige Einheit mehr bezahlbar ist und kein Lager da ist; oder Notkredit (Feature F9) |
| B3 | Falle: Shop ohne Mitarbeiterplatz kann nichts verkaufen | mittel | S | `logic.py:79`, `logic.py:1057` | Freischalten enthält den ersten Platz, oder deutlicher Hinweis im Shops-Fenster; endgültig mit `shop-walk` |
| B5 | `/api/open` verkauft ohne Arbeit und ohne Lohn (nur per direktem Aufruf) | mittel | M | `app.py:580-596`, `logic.py:487-525` | Endpunkt entfernen oder hinter den Editor-Schalter legen; Vorschau getrennt halten. Tests nennen ihn: Änderung muss der Spec-Besitzer bestätigen |
| U3 | Veraltete Texte für den Spieler | mittel | S | `static/world/ui.js:1003-1005`, `static/app.js:394` | Den Satz "The weather does not change the number of customers yet" löschen; "above twice the reference" an die Preiskurve anpassen |
| B7 | Editor setzt nicht den ganzen Spielstand (Mitarbeiter, offener Tag, Verlauf) | mittel | M | `logic.py:726-788` | Patch um `employees` erweitern; Plätze per Editor bekommen ihren Mitarbeiter. Voraussetzung für `demo-scenarios` |
| P3 | Dach-Blende: 22 ms statt 17 ms pro Frame, 22 % der Frames über 20 ms | mittel | M | `static/world/nova.js:414-442` | Dach einmal in ein eigenes Canvas zeichnen und beim Blenden nur dieses Bild mit Deckkraft einsetzen |
| P4 | Alles wird jedes Frame neu gezeichnet, 347 Objekte ohne Sichtfeld-Prüfung (4,1 ms) | mittel | M | `static/world/render.js:45-53`, `campus.js:35-80`, `beach.js:1856-1962` | Boden in ein Offscreen-Canvas legen; Objektliste einmal bauen; Objekte außerhalb des Bilds überspringen |
| P5 | Rund 1 MB neuer Speicher pro Frame, 6 bis 7 Aufräumläufe pro Sekunde | niedrig bis mittel | M | `static/world/scene.js:56`, `primitives.js:14-19`, `render.js:45-53` | Farben aus `mixColor` zwischenspeichern, Objektliste wiederverwenden, feste Punkte vorberechnen |
| B4 | Lagerlimit umgehbar: Ware auf der Theke zählt nicht mit | niedrig | S | `logic.py:235-242` | Einheiten auf der Theke zum Lager des Shops dazuzählen |
| P6 | Dashboard baut sich bei jeder Aktion ganz neu (13 ms spät im Spiel) | niedrig | S | `static/app.js:678-699`, `static/views.js:31` | Nur neu zeichnen, wenn das Dashboard sichtbar ist; sonst beim Öffnen |
| P7 | Jede Antwort enthält den ganzen Verlauf (39,5 von 50 KB), jede Sekunde | niedrig | S bis M | `app.py:222`, `app.py:257` | Tick-Antwort schlank halten; Verlauf nur beim Tageswechsel senden |
| P8 | Auflösung 2-fach: 6,5 Millionen Pixel | niedrig | S | `static/world/main.js:315` | Erst nach P1 nötig: Faktor auf 1,5 begrenzen, wenn die Bildrate fällt |
| P9 | Wegsuche 5 bis 27 ms pro Klick | niedrig | S | `static/world/paths.js:61-109` | Offene Knoten in einem Heap halten statt jedes Mal alle zu durchsuchen |
| P10 | Tag überspringen: 235 ms spät im Spiel (300 Kopien des Spielstands) | niedrig | S | `logic.py:1254-1262`, `logic.py:1162` | Einmal kopieren, dann auf der Kopie weiterzählen |
| U2 | Klick wird still verworfen, solange eine Anfrage läuft | niedrig | S | `static/world/ui.js:664`, `ui.js:682`, `static/app.js:18` | Aktion einreihen statt verwerfen |
| B6 | Preis-Eingaben wie `1e2` oder `1_0` werden angenommen | niedrig | S | `logic.py:203-214` | Vor `Decimal` nur Ziffern mit höchstens zwei Nachkommastellen zulassen |
| B8 | Dashboard bricht ab, wenn der Verlauf ein Produkt nennt, das nicht mehr im Besitz ist (nur per Editor) | niedrig | S | `static/app.js:586-588`, `static/world/ui.js:974` | Name mit Rückfall auf die Produkt-Id lesen |
| Q1 | Toter Code und doppelte Wege | niedrig | S | siehe Abschnitt 3.1.5 | Entfernen, soweit kein Test daran hängt |
| D1 | README und Roadmap widersprechen dem Code | niedrig | S | `README.md:87`, `README.md:89`, `README.md:98-100`, `docs/feature-roadmap.md:36`, `:139` | Auf den Stand nach PR #65 bringen |
| S1 | Nicht bereit für ein öffentliches Deployment | nur bei Deployment | M bis L | `app.py:24`, `app.py:619` | Sitzung pro Spieler, Produktions-Server, Sicherheits-Header (Roadmap 3a, Punkt 8) |

## 3. Details

### 3.1 Teil 1: Korrektheit und Regeln

#### 3.1.1 Tests

`uv run pytest` zu Beginn des Audits:

```
configfile: pyproject.toml
testpaths: tests, checks
collected 785 items

tests/test_click_walk.py .                                               [  0%]
tests/test_day_context.py ...........................                    [  3%]
tests/test_day_cycle.py .........                                        [  4%]
tests/test_editor_mode.py .............................................. [ 10%]
.....................................................                    [ 17%]
tests/test_first_feature.py ...............                              [ 19%]
tests/test_full_run.py .......                                           [ 20%]
tests/test_map_view.py .......                                           [ 21%]
tests/test_nova_wings.py ..........................                      [ 24%]
tests/test_nova_zones.py ...................                             [ 26%]
tests/test_outlook.py ...............................                    [ 30%]
tests/test_outlook_hidden_weather.py .                                   [ 30%]
tests/test_outlook_leftovers.py .                                        [ 30%]
tests/test_pricing.py .................................................. [ 37%]
.................................................                        [ 43%]
tests/test_shop_process.py ..............................                [ 47%]
tests/test_shop_scenarios.py .............                               [ 49%]
tests/test_shop_skip.py .............                                    [ 50%]
tests/test_shop_unlock.py .............................................  [ 56%]
tests/test_staff.py .................................................... [ 63%]
.......................                                                  [ 65%]
tests/test_staff_all_shops.py ............                               [ 67%]
tests/test_staff_leftovers.py .....                                      [ 68%]
tests/test_staff_review.py .....                                         [ 68%]
tests/test_stock_overview.py ....                                        [ 69%]
tests/test_stock_panel.py .......                                        [ 70%]
tests/test_walk_in.py ........................                           [ 73%]
tests/test_world_api.py ................................................ [ 79%]
........                                                                 [ 80%]
tests/test_world_art.py ..........................................       [ 85%]
tests/test_world_core.py ............................................... [ 91%]
......................................                                   [ 96%]
tests/test_world_paths.py ...................                            [ 98%]
checks/test_finite_prices.py ........                                    [100%]

============================= 785 passed in 21.50s =============================
```

Kein Test sieht falsch aus. `tests/test_outlook_hidden_weather.py` ist richtig, prüft aber nur das
Feld `weather` und übersieht deshalb das Leck B1.

Die BRD selbst liegt nicht im Repository. Geprüft wurde gegen die Regeln, wie sie in
`specs/first-feature.md`, `specs/full-run.md` und den Kommentaren in `logic.py` stehen
(CT01 bis CT05, CT R1 bis R5).

#### 3.1.2 Regeln aus AGENTS.md

| Regel | Ergebnis | Beleg |
|---|---|---|
| Geld nur als ganze Cent | eingehalten | Simulation einer ganzen Saison mit Personal in allen Shops: kein `float` im Verlauf oder im Spielstand. Der Browser teilt nur für die Anzeige durch 100 (`common.js:26-33`). Die Spielerposition ist bewusst eine Kommazahl |
| Abgelehnte Aktion ändert nichts | eingehalten | `app.py:247-257` speichert nur nach Annahme. Jede Regel arbeitet auf einer Kopie |
| Zufall nur über den Seed | eingehalten | `logic.py:549`, `:572`, `:574`: eigener Generator aus Seed und Tag. `secrets` nur in `new_seed` (`logic.py:155`). In `static/` kein `Math.random` (Suche ohne Treffer). Die Passanten nutzen eine feste Rechenformel (`walkers.js:19-20`), nicht den Seed: erlaubt, aber in jedem Lauf gleich |
| Keine Regel im Browser | eingehalten | Der Browser rechnet nur Hinweise: "up to N affordable" (`app.js:165`, `ui.js:327`), Summe einer Bestellung (`app.js:236`), Frage vor dem Tagesende (`ui.js:900-911`). Der Server prüft alles erneut |
| Nichts von außen geladen | eingehalten | Im Browser gemessen: alle Abrufe gehen an den eigenen Server. Symbol der Seite ist eine Daten-Adresse, Schriften sind System-Schriften |
| Spielstand vollständig setzbar | **teilweise** | Der Editor setzt Tag, Kasse, Seed, Wetter, Lager, Preise, Shops, Position. Er setzt nicht: Mitarbeiter (Stufe, arbeitet oder nicht), offenen Tag, Verlauf (`logic.py:732`). Plätze per Editor bleiben leer: 2 Plätze, 0 Mitarbeiter (B7) |
| Tageskontext überschreibbar | eingehalten | `make_day_context(seed, day, override)` (`logic.py:544`) |

#### 3.1.3 Trennung der Schichten

Die Trennung stimmt. `logic.py` kennt weder Datenbank noch Bildschirm (es liest aus `world.py` nur
die Zone und den Startpunkt). `db.py` speichert und lädt. `app.py` ruft Regeln auf und baut die
Ansicht. `static/world/` zeichnet und läuft.

Auffällig zwischen Dashboard und Campus:

- Es gibt zwei Kopien des Spielstands im Browser (`app.js:7` und `ui.js:13`) und zwei
  Sende-Funktionen (`app.js:17`, `ui.js:44`). Sie werden über Nachrichten abgeglichen.
- Der Campus meldet dem Dashboard nur Aktionen und den Tageswechsel, keine Ticks
  (`ui.js:672-675`). Verkäufe durch Mitarbeiter während des Tages kommen im Dashboard erst am
  Tagesende an. Aus dem Code abgeleitet, im Browser nicht eigens nachgestellt.
- `common.js:1` nennt eine Datei `map.js`, die es nicht mehr gibt.

#### 3.1.4 Fehler und Randfälle (alle mit Skript gegen die echten Regeln nachgeprüft)

**B1, echtes Wetter vor dem Öffnen.** `weather` ist vor dem Öffnen leer, wie gewollt. Aber
`products[].breakdown` und `products[].customers` rechnen schon mit dem echten Wetter und nennen es
beim Namen. In 28 von 40 Seeds stand "Weather: …" in der Erklärung, bevor der Tag offen war.
Beispiel Seed 12: Vorhersage Sturm, echtes Wetter Regen, Erklärung zeigt "Weather: Rainy" und 13
Kunden. In den übrigen 12 Seeds verrät das Fehlen der Zeile das Wetter (Faktor genau 100 %). Die
gleichen Zahlen stehen in der Lager-Übersicht, im HUD ("about N customers today") und in der
Vorschau des Dashboards. README (`README.md:87`) und Roadmap (`:121`) beschreiben das Leck noch
über das alte Feld; das Feld ist zu, das Leck besteht über die Erklärung.

**B2, Sackgasse.** Tag 1: Kuchen (40 €) und Mitarbeiterplatz 1 (60 €) kaufen. Kasse 0, Lager leer,
kein Produkt mehr kaufbar. Der Mitarbeiter hört am ersten Abend auf (kein Geld für den Lohn).
Ergebnis nach 30 Tagen: −100 €. Nur "New run" hilft.

**B3, Shop ohne Platz.** Beach Cafe freigeschaltet (200 €), 20 Bier gekauft: `start_shift` antwortet
"A day cannot be played in the Beach Cafe yet.", am Tagesende 0 verkauft. Der Shop verdient erst
mit dem Platz für weitere 60 €. In der Simulation kostet dieser Fehlkauf 200 € von 1.500 €.

**B4, Lagerlimit.** 100 Kaffee kaufen, Tag öffnen, 20 auf die Theke tragen, 20 nachkaufen: Am Abend
liegen 120 im Lager, das Limit ist 100.

**B5, `/api/open`.** Gleicher Spielstand, 30 Kaffee: `trade_day` verkauft 6 Stück für 12 €, ein
geöffneter und übersprungener Tag ohne Arbeit verkauft 0. Kein Knopf ruft `/api/open` noch auf
(Suche in `static/` ohne Treffer); der Endpunkt ist nur direkt erreichbar. Er widerspricht der
beschlossenen Regel "Whoever does not work earns nothing". Der Editor (`editor_skip_days`) nutzt
`trade_day` zu Recht weiter.

**B6, Preis-Text.** `1e2` wird als 100,00 € angenommen, `1_0` als 10,00 €, `٣` als 3,00 €.
Kein Schaden (der Wert ist gültig), aber nicht das, was die Fehlermeldung verspricht.

**B7, Editor.** Siehe Tabelle in 3.1.2.

**B8, Verlauf und Produkte.** `state.products.find(...)` kann leer sein, wenn der Editor ein
Produkt wegnimmt, das im Verlauf steht; `p.name` wirft dann einen Fehler und das Dashboard bleibt
halb gezeichnet. Aus dem Code abgeleitet, nicht im Browser nachgestellt.

**Weitere Beobachtungen**

- `skip_shift` sagt im Kommentar "no customer is served" (`logic.py:1254-1257`). Mit einem
  Mitarbeiter verkauft ein übersprungener Tag aber alles (6 von 6, Lohn 8 €). Das Verhalten ist so
  gewollt (`specs/staff.md`), der Kommentar ist falsch.
- Preise ändern ist gesperrt, sobald der Tag offen ist, auch ohne Schicht. Die Meldung sagt
  "while a shift is running" (`logic.py:270-271`).
- Gleichzeitige Aufrufe: Ein Schloss (`app.py:24`) reiht Laden, Regel und Speichern. Das trägt bei
  einem Prozess. Antworten können im Browser in anderer Reihenfolge ankommen als gesendet
  (Tick und Kauf laufen getrennt, `ui.js:663` und `ui.js:815`); der nächste Tick nach höchstens
  einer Sekunde korrigiert die Anzeige. Möglich, im Test nicht beobachtet.
- Zwei offene Seiten verdoppeln das Tempo des Tages (steht schon unter "Known issues").
- `db.load` schließt seine Verbindung nicht selbst (`db.py:87`); `connect` schreibt bei jedem
  Aufruf das Schema neu (0,14 ms, ohne Folgen).

#### 3.1.5 Toter Code, tote Dateien, Doppelungen

| Was | Wo | Bemerkung |
|---|---|---|
| Abspielen eines Tages vom Dashboard aus (`playDay`, `animating`, `dayRunning`, `fast`, Knopf "Skip") | `ui.js:14-16`, `:870-883`, `:928-932`, `map.html:69` | Das Dashboard sendet nie `kind: "open"`. Der Weg ist unerreichbar |
| `novaIsOpen` | `nova.js:41` | nie benutzt |
| `rectCollider`, `circleCollider` | `physics.js:7-13` | nie benutzt |
| `drawColumnLine` | `primitives.js:140` | nie benutzt |
| `drawFacadeBandX` | `primitives.js:255` | leere Funktion, 14 Nennungen |
| Feld `shift_day_ticks` | `app.py:221` | kein Leser in `static/` |
| `demand()` | `logic.py:475` | alte Regel, nur noch von `tests/test_first_feature.py` gehalten |
| `/api/day-override` mit `CAMPUS_TYCOON_DEMO` | `app.py:417-440` | tut dasselbe wie `/api/editor/weather`; Tests nennen ihn 10 Mal |
| `specs/employees.md`, `investments.md`, `multi-business.md`, `net-worth.md` | `specs/` | verworfener Plan (Roadmap 4.3) |
| Text "Play day" | `map.html:67` | wird bei jedem Zeichnen mit "Shift" überschrieben (`ui.js:253`) |

Doppelungen: zwei `send` (`app.js:17`, `ui.js:44`); zweimal "New run"-Abfrage (`app.js:646`,
`ui.js:1028`); die Bestell-Bedienung mit Stepper, Chips und Summe zweimal (`app.js:204-240`,
`ui.js:328-351`, `:702-715`); in `logic.py` dreimal die Prüfung "ganze Zahl" (`:250`, `:411`,
`:629`) und dreimal der Eintrag eines gesperrten oder neuen Shops (`:184-190`, `:309-314`, `:679`).

#### 3.1.6 Testlücken (nur Vorschläge)

1. Vor dem Öffnen darf keine Zahl der Ansicht vom echten Wetter abhängen: zwei Läufe mit gleicher
   Vorhersage und verschiedenem echten Wetter liefern die gleiche Ansicht (B1).
2. Das Lagerlimit zählt die Theke mit (B4).
3. Ein Kauf, der in die Sackgasse führt, wird abgelehnt oder gewarnt (B2, nach Entscheidung).
4. Preis-Texte `1e2`, `1_0`, arabische Ziffern (B6).
5. `ui.js` hat keinen einzigen Verhaltens-Test (1.143 Zeilen). Vorschlag wie bei `paths.js` und
   `roofs.js`: die Entscheidung "muss das Fenster neu gezeichnet werden" als reine Funktion
   herausziehen und mit Node prüfen (U1).
6. Wächter gegen Rückfall bei der Bildrate, ohne Browser: In `static/world/` kommt kein
   `ctx.filter` vor (so wie heute `Math.random` geprüft wird).
7. `/api/shift/tick` wird in den Tests nur zweimal genannt. Es fehlt: parallele Aufrufe aus zwei
   Threads lassen Kasse und Lager stimmig.
8. Größe der Antwort: Ein Tick spät im Spiel bleibt unter einer festen Grenze (P7).
9. Balance-Wächter: Eine feste Strategie über feste Seeds bleibt in einem Zielbereich (G1).
10. Das Dashboard verkraftet einen Verlauf mit einem Produkt, das nicht mehr im Besitz ist (B8).

### 3.2 Teil 2: Warum hakt und laggt es?

#### 3.2.1 Aufbau der Messung

- Rechner: Apple M3, Chrome mit Grafik-Beschleunigung (Metal). Fenster 1710 × 952 Punkte bei
  doppelter Auflösung, das Canvas hat also 3420 × 1904 Pixel.
- Bildzeiten: Abstände zwischen `requestAnimationFrame`-Aufrufen im Campus-Fenster, je 2 bis 10
  Sekunden.
- Zuordnung der Ursachen: Einzelne Canvas-Funktionen wurden zur Laufzeit im Browser abgeschaltet
  (nichts im Code geändert) und die Bildzeit erneut gemessen. Zeichen-Funktionen wurden einzeln
  aufgerufen und gestoppt.
- Grenzen: nur ein Rechner, ein schneller. Auf schwächeren Geräten sind alle Zahlen höher; das
  wurde nicht gemessen. Der Bildschirm begrenzt auf 16,7 ms; was darunter liegt, wurde über die
  Rechenzeit im Skript bestimmt. Ein Flammen-Diagramm aus den Entwickler-Werkzeugen wurde nicht
  aufgenommen.

#### 3.2.2 Ursachen, sortiert nach Wirkung

| Rang | Ursache | Messung | Datei:Zeile | Fix | Aufwand | Risiko |
|---|---|---|---|---|---|---|
| 1 | Weichzeichner für Schatten | mit: 82 bis 177 ms pro Frame (5,6 bis 12 Bilder/s); ohne: 16,7 ms (60 Bilder/s). Also 66 bis 160 ms | `primitives.js:106-115`, Zeile 110 | Filter weg; weicher Schatten als radialer Verlauf oder vorgezeichnetes Bild | S | gering: Schatten sehen leicht anders aus |
| 2 | Gedeckelter Zeitschritt | bei 7,5 Bildern/s läuft die Figur 1,05 Felder/s, bei 56 Bildern/s 3,43 (Soll 3,5) | `main.js:300` | Deckel 0,1 s, Bewegung in Teilschritten | S | gering: Kollision in Teilschritten prüfen |
| 3 | Dach-Blende | ohne Weichzeichner: 22,4 ms im Mittel, 58 von 268 Frames über 20 ms, Spitze 33 ms. Geschlossen oder offen: 16,7 ms | `nova.js:414-442` (Dach mit Deckkraft), `rooms.js:1089` (Räume kommen dazu) | Dach in eigenes Canvas, beim Blenden nur das Bild | M | mittel: Reihenfolge von vorn und hinten |
| 4 | Alles jedes Frame neu, kein Sichtfeld für Objekte | 4,1 ms Rechenzeit pro Frame; 5.861 Füllungen, 4.205 Linienzüge, 21.900 `lineTo`, 2.769 `save`/`restore`, 347 Objekte | `render.js:45-53`, `campus.js:35-80`, `beach.js:1856-1962` | Boden cachen, Liste einmal bauen, außerhalb des Bilds überspringen | M | mittel: bewegte Teile (Wasser, Fahnen) bleiben live |
| 5 | Speicher pro Frame | 976 KB pro Frame, 267 MB in 5 s, 33 Aufräumläufe in 5 s | `scene.js:56-58`, `primitives.js:14-19`, `render.js:45-53` | Farben cachen, Listen wiederverwenden | M | gering |
| 6 | Dashboard-Neuaufbau | 0,8 ms an Tag 1; 13 ms mit 12 Produkten und 30 Tagen (nachgestellt), 2.156 Elemente | `app.js:678-699` | nur wenn sichtbar | S | gering |
| 7 | Wegsuche | 5 bis 27 ms pro Klick, einmalig | `paths.js:61-109` | Heap | S | gering |
| 8 | Server | Tick 1,0 ms (früh) bis 3,7 ms (spät); Zustand 0,5 bis 3,0 ms; Überspringen 7 bis 235 ms | `app.py:247-257`, `logic.py:1254` | schlankere Antwort, eine Kopie beim Überspringen | S | gering |

**Zu Rang 1.** `drawSoftShadow` setzt für jede Schatten-Ellipse `ctx.filter = "blur(2px)"`. Das
passiert 35 Mal pro Frame, an jeder der zehn gemessenen Stellen der Karte gleich oft, auch wenn die
Schatten nicht im Bild sind. Aufrufer: `beach.js:271`, `:365`, `:630`, `:710`, `:809`, `:1255`,
`:1311`, `:1510`, `:1530`, `:1740` und `nova.js:63`.

| Szene | mit Weichzeichner | ohne |
|---|---|---|
| Platz, stehend (drei Läufe) | 86,6 / 86,6 / 82,7 ms | 16,7 ms |
| Erster Lauf direkt nach dem Laden | 177 ms | nicht gemessen |
| Nach einer Größenänderung des Canvas | 145 ms | nicht gemessen |
| Im Nova (Hauptbau) | 80,2 ms | 16,7 ms |
| Learning Center / Mercado / Hub / Dorm | 82,1 / 84,6 / 87,3 / 82,6 ms | 16,7 ms |
| Strand Mitte / West | 89,7 / 88,9 ms | 16,7 ms |
| Platz am Abend | 104,9 ms | 16,7 ms |
| Strand bei Nacht | 116,6 ms | 16,7 ms |
| Beim Laufen | 134,1 ms | 18,0 ms |
| Während die Dächer blenden | 89,1 ms | 22,4 ms |
| Kleines Fenster auf dem Dashboard (957 × 538 Pixel) | 21,7 ms, Spitzen 50 ms | nicht gemessen |
| Canvas mit einfacher statt doppelter Auflösung | 39,3 ms | nicht gemessen |

Die Kosten des Filters hängen von der Pixelzahl ab (39 ms bei einfacher Auflösung). Warum der
erste Lauf nach dem Laden doppelt so langsam war, ist nicht geklärt. Ohne Filter passen vier
vollständige Zeichendurchläufe in ein Frame von 16,7 ms; das Zeichnen selbst ist auf diesem
Rechner also nicht das Problem.

**Zu Rang 2.** `const dt = Math.min(..., 0.04)`: Dauert ein Frame länger als 40 ms, rechnet das
Spiel trotzdem nur 40 ms weiter. Laufen, Kamera und Dach-Blende werden dann langsamer statt
ruckelig. Zusammen mit Rang 1 fühlt sich das Spiel zäh an: 3 Sekunden Taste halten ergab 3,2
Felder statt 10,4.

**Zu Rang 3.** Die Rechenzeit steigt beim Blenden kaum (4,3 ms gegen 2,8 geschlossen und 3,4
offen). Die Mehrkosten entstehen also beim Zeichnen selbst. Vermutung, nicht belegt: Das halb
durchsichtige Dach und die Räume darunter werden gleichzeitig gezeichnet.

**Zu Rang 4, Aufteilung der 4,1 ms:** Boden-Kacheln 1,2 bis 1,3 ms (`campus.js:35`, Kacheln
außerhalb des Bilds werden hier schon ausgelassen), Strand-Objekte 1,4 ms (235 Stück), Strand-Boden
0,65 ms, Nova-Objekte 0,27 ms (75), Brandung 0,25 ms, Campus-Objekte 0,15 ms (23), Bodenplan
0,13 ms, Passanten 0,07 ms (14). Statisch und trotzdem jedes Frame neu berechnet: die Farbe jeder
Kachel über `mixColor` (zerlegt jedes Mal zwei Farb-Texte), die 110 Sand-Flecken
(`beach.js:128-139`), die Objektliste mit einer neuen Funktion pro Objekt.

**Zu Rang 5.** Aussetzer ohne Weichzeichner: 3 von 578 Frames über 33 ms in 10 Sekunden, Spitze
133 ms. Ob das Aufräumläufe des Speichers sind, ist nicht belegt.

#### 3.2.3 Was keine Ursache ist

- **Anfragen und Abfragen:** Während ein Tag offen ist, geht genau eine Anfrage pro Sekunde raus
  (`/api/shift/tick`, `ui.js:656`). Sonst gibt es kein Abfragen im Takt. Die Position wird nur
  beim Stehenbleiben gespeichert. Die Antwort ist spät im Spiel 50 KB groß, davon 39,5 KB Verlauf.
- **Kollision:** unter 0,01 ms pro Schritt, unter der Auflösung der Messung.
- **Layout im Campus:** Pro Frame liest die Schleife `clientWidth` und `clientHeight`
  (`render.js:19-20`, `main.js:284-286`) und fragt drei Elemente ab (`ui.js:1080`). Mit offenem
  Tag blieben es 57,6 Bilder/s bei 16 DOM-Änderungen pro Sekunde. Nicht messbar teuer.
- **Dashboard-Schleife:** `followSlot` (`views.js:44-55`) läuft dauerhaft mit, misst aber nur in
  der Dashboard-Ansicht. Obere Seite und Campus liefen dort gleich schnell.
- **Größenänderung:** `resize` (`main.js:313-319`) legt das Canvas bei jedem Ereignis neu an, ohne
  Pause. Nicht gemessen.

### 3.3 Teil 3: Verbesserungen

#### 3.3.1 Code-Qualität und Struktur

- **Zu große Dateien:** `beach.js` 1.966 Zeilen, `logic.py` 1.391, `rooms.js` 1.164, `ui.js`
  1.143. Vorschlag: `beach.js` in Boden, Shops und Leben am Strand teilen; `ui.js` in HUD, Fenster,
  Schicht, Editor und Tagesablauf; `logic.py` in Grundregeln, Preislogik, Schicht und Personal,
  Editor. Jeweils eine eigene Spec, reines Umziehen ohne Verhaltensänderung.
- **Ansicht bei jeder Anfrage:** `view()` (`app.py:194-227`) rechnet alles neu, auch für das
  Speichern der Position, und spielt für die Vorschau einen ganzen Tag durch (`app.py:213`).
  Heute billig (1 ms), aber die Antwort wächst mit dem Verlauf.
- **Schicht als verschachteltes JSON:** Der Tag des Spielers und die Shops mit Personal liegen in
  `shift` und `shift["extra"]` mit gleichen Feldern, aber verschiedenen Wegen
  (`logic.py:1006-1032`, `:1186-1198`). Eine Liste gleichartiger Schichten wäre lesbarer.
- **Stil:** `physics.js` ist ohne Leerzeichen gesetzt und fällt aus dem Rest heraus.
- **Doppelungen und toter Code:** siehe 3.1.5.

#### 3.3.2 Bedienung

- **U1 (im Browser bestätigt):** Tag offen, Bestell-Fenster offen, Menge 37 getippt. Nach 1,3
  Sekunden steht wieder 10 im Feld, das Feld ist ein neues Element, der Fokus ist weg. Im
  Shops-Fenster werden alle Knöpfe jede Sekunde ersetzt; ein Klick, der über den Tick hinweg
  gedrückt wird, geht verloren.
- **U2:** Läuft gerade der Tick, wird ein Klick auf "Sell" ohne Rückmeldung verworfen
  (`ui.js:682`). Bei 1 bis 4 ms selten, bei einem langsamen Server häufiger.
- **Rückmeldung:** Gut gelöst sind Toasts, Fehlermeldung am Feld und die Frage vor dem Tagesende.
  Es fehlt eine Anzeige, wie viele Kunden gerade warten, wenn das Shift-Fenster zu ist.
- **Länge einer Saison:** Eine Schicht dauert 90 Sekunden, ein Tag ohne Überspringen 300. 30 Tage
  sind mindestens 45 Minuten reine Schicht, ohne Überspringen 2,5 Stunden. Für eine Vorführung zu
  lang (offene Entscheidung 2 der Roadmap).
- **Barrierefreiheit:** Fokus-Rahmen und reduzierte Bewegung sind bedacht. Lücken: Die Karte im
  Canvas hat für Screenreader nur einen Namen (`map.html:13`); das Karten-Fenster am Tagesende
  hält den Fokus nicht fest und hat keinen Titel (`map.html:87-89`); alle Toasts sind
  `aria-live="assertive"`, auch Erfolgsmeldungen (`map.html:114`); die Diagramme haben
  `role="img"` ohne Beschreibung (`app.js:463`).
- **Kleine Fenster:** Die Stile haben Stufen bei 980 und 760 Punkten (`map.css:370`, `:375`),
  Laufen per Tipp geht über den Klick. Im schmalen Fenster wurde nicht getestet (das Testfenster
  ließ sich nicht verkleinern).

#### 3.3.3 Spielbalance

Simulation mit den echten Regeln, Seeds 1 bis 20. Der Spieler bedient das Cafe fehlerfrei, das
Personal arbeitet wie im Spiel. Gekauft wird jeden Morgen der Bedarf des Tages.

| Strategie | Ergebnis im Mittel | Spanne | Surf Shop ab Tag |
|---|---|---|---|
| A: nur Kaffee, Referenzpreis | +332 € | 299 bis 359 | – |
| B: ganzes Cafe (Kuchen, Bagel) | +1.500 € | 1.349 bis 1.634 | – |
| C: wie B, täglich bester Preis | +1.671 € | 1.522 bis 1.789 | – |
| D: Shops in Listen-Reihenfolge, je 1 Mitarbeiter | +22.697 € | 18.388 bis 25.158 | 16 |
| E: nach dem Cafe direkt zum Surf Shop | +25.345 € | 20.007 bis 28.467 | 10 |
| F: wie E, je 2 Mitarbeiter | +24.529 € | 19.317 bis 27.473 | 10 |
| G: nie selbst arbeiten, nur Personal | +8.668 € | 4.259 bis 11.165 | 19 |
| H: Beach Cafe ohne Mitarbeiterplatz | +1.300 € | 1.149 bis 1.434 | – |

Gewinn pro Tag und Produkt an einem neutralen Tag, beim Referenzpreis: Kaffee 12 €, Kuchen 25 €,
Bagel 20 €, Bier 25 €, Coke Zero 17 €, Sandwich 20 €, Cap 80 €, T-Shirt 90 €, Hoodie 170 €,
Surf-Stunde 170 €, Wetsuit 350 €, Surfboard 500 €.

Was das bedeutet:

- **Dominante Strategie:** so schnell wie möglich zum Surf Shop (E). Ein Surfboard-Tag bringt mehr
  als acht Tage ganzes Cafe. Jeder Shop hat rund 10 Kunden pro Produkt, die Marge pro Stück
  unterscheidet sich aber um den Faktor 40.
- **Die Saison zerfällt in zwei Teile:** bis Tag 10 knapp (186 € Kasse bei E), ab dann explodiert
  das Geld (10.506 € an Tag 20). Die ersten zehn Tage sind spannend, die letzten zwanzig nicht.
- **Das Beach Cafe lohnt sich nie zuerst:** 260 € Einstieg für 25 € pro Tag.
- **Der zweite Mitarbeiter lohnt sich nicht:** F liegt 816 € unter E, bei gleich vielen
  verlorenen Kunden.
- **Preise sind fast egal:** Der beste Preis bringt 11 % mehr als der Referenzpreis (C gegen B).
  Im Cafe liegt er bei 120 %, im Surf Shop bei 140 %.
- **Sackgasse und Falle:** B2 und B3.
- **Wetter:** Die Vorhersage sollte ein Risiko sein. Durch B1 ist sie keines.

Vorschlag für den Balance-Durchgang: Kundenzahl der teuren Shops senken (`SHOP_MIX` ist heute
überall 10), Freischalt-Preise an den Tagesgewinn koppeln, dem zweiten Mitarbeiter einen Nutzen
geben (mehr Kunden als ein Mitarbeiter schafft), und die Simulation als Test behalten.

### 3.4 Teil 4: Ideen für neue Features

Alle Vorschläge halten die drei Regeln: Zufall nur aus dem Seed, Geld in ganzen Cent, jede
Entscheidung auf dem Server.

| Nr | Feature | Nutzen | Wo einbauen | Regeln | Testidee | Aufwand | Hängt ab von |
|---|---|---|---|---|---|---|---|
| F1 | `events-and-disruptions` (#14) | Tage unterscheiden sich: Prüfungszeit, Party, Stromausfall | `logic.py`: Tabelle `EVENTS`, Eintrag in `make_day_context`, ein weiterer Faktor in `FACTORS`; `app.py`: Ansicht; `ui.js`: Abendbericht | Ereignis aus `random.Random(f"{seed}:{day}:event")`, Faktoren ganze Prozent, Override wie beim Wetter | gleicher Seed, gleiches Ereignis; Override setzt es fest; Kunden ändern sich um den Faktor | M | B1 (sonst verrät die Erklärung auch das Ereignis) |
| F2 | `popularity` (#13) | Folgen über den Tag hinaus: leere Regale und hohe Preise kosten morgen Kunden | `logic.py`: `state["popularity"][shop]`, Änderung in `_close_shift`, Faktor in `FACTORS`; `db.py`: Spalte in `shops`; Editor-Patch | ganze Zahl 0 bis 100, nur auf dem Server | verlorene Kunden senken, volle Bedienung hebt; bleibt in 0 bis 100; alter Spielstand lädt | M | G1 |
| F3 | `badges` (#15) | Ziele neben dem Geld, guter Einstieg für ein Teammitglied | `logic.py`: `BADGES` und Prüfung in `_close_shift`; `db.py`: in `meta`; `app.js` und `ui.js`: Anzeige | nur der Server vergibt, kein Endpunkt zum Setzen | Abzeichen genau einmal; kein Aufruf kann eines vergeben | S | – |
| F4 | `weather-visuals` (#16) | Wetter ist sichtbar: Regen, Sturm, Hitze | `environment.js`, `render.js` | zeichnet nur `state.weather` (vor dem Öffnen nichts); kein `Math.random`, Tropfen aus fester Formel | Quelltext-Prüfung wie heute; Node-Test der Tropfen-Formel | M | P1 (sonst noch langsamer) |
| F5 | Wartende Kunden als Figuren (`queue-figures`, kleiner Teil von `guests`) | Man sieht ohne Fenster, dass jemand wartet | `rooms.js`: aus `server.shift.waiting` zeichnen; `world.py`: Plätze der Schlange | reine Anzeige der Server-Zahl | Node-Test: Zahl der Figuren gleich Zahl der Wartenden, höchstens N | S bis M | – |
| F6 | `shop-walk` (#40) | Die Schicht wird gelaufen statt geklickt; alle vier Shops spielbar | `main.js`, `locations.js`, `world.py` (Lager- und Theken-Punkte), `logic.py` (`SHIFT_SHOPS`) | jeder Schritt bleibt eine Anfrage; keine Regel liest die Position | Auffüllen ohne Bestand abgelehnt, egal wo die Figur steht | L | U1, F5, `shop-art` |
| F7 | Tempo-Stufe für den Tag (`fast-forward`) | Saison in vertretbarer Zeit; löst die Frage der Tageslänge | `app.py`: `/api/shift/tick` nimmt `steps` aus {1, 2, 4}; `logic.py`: mehrere Ticks in einer Kopie; `ui.js`: Umschalter | Server zählt weiter die Ticks; Wert aus fester Liste | 4 Schritte geben denselben Stand wie 4 einzelne Ticks; anderer Wert abgelehnt | S | P10 |
| F8 | Notkredit (`emergency-loan`) | Keine Sackgasse mehr | `logic.py`: `take_loan`, Rückzahlung mit Aufschlag in `_close_shift`, zählt in `overall_gain`; `db.py`: `meta`; Dorm-Fenster | ganze Cent, einmal pro Lauf, nur bei Kasse unter dem billigsten Produkt und leerem Lager | Kredit nur in der Notlage; Rückzahlung zieht nie unter 0; Ergebnis rechnet ihn ab | S bis M | Entscheidung zu B2 |
| F9 | Saison-Abschluss mit Bestenliste (`season-result`) | Grund, noch einmal zu spielen; guter Schluss für die Vorführung | `db.py`: Tabelle `scores` (bleibt bei "New run"); `logic.py`: Note aus Schwellen; `app.py`: `GET /api/scores`; Abschlusskarte | Eintrag schreibt der Server beim Abschluss von Tag 30, der Seed wird nicht gezeigt | genau ein Eintrag pro Lauf; neuer Lauf löscht die Liste nicht | S bis M | G1 (sonst sind die Schwellen wertlos) |
| F10 | Editor für Personal, dann `demo-scenarios` (#23) | Vorführung in 5 Minuten | `logic.py`: `employees` im Patch; neues `scenarios.py`; `app.py`: Lader hinter dem Schalter; `ui.js`: Erklär-Karte | nur lokal mit Schalter; ganzer Zustand geprüft | Szenario laden ergibt genau den Zustand; ohne Schalter abgelehnt | M | B7, die gewählten Features |
| F11 | `outfits` (#21) | Kleiner Geld-Abfluss spät im Spiel, sichtbar an der Figur | `logic.py`: `OUTFITS`, `buy_outfit`; `people.js`: Farbe; Merchandise-Fenster | Kauf auf dem Server, Id aus fester Liste | ohne Geld abgelehnt, nichts geändert | S | – |

Das in der Roadmap vorgeschlagene `warehouse` bleibt sinnvoll, ist aber groß (L) und ändert `buy`
und viele Tests. Empfehlung: erst nach dem Balance-Durchgang entscheiden.

**Reihenfolge**

| Stufe | Inhalt | Parallel für 3 bis 4 Personen |
|---|---|---|
| 0, sofort | vier Fix-Specs: `smooth-frames` (P1, P2), `calm-panels` (U1, U3, U2), `hidden-weather` (B1), `balance-pass` (G1, B2, B3, B4) | ja, alle vier gleichzeitig: sie berühren verschiedene Dateien (`primitives.js` und `main.js` / `ui.js` / `app.py` und `logic.py`-Preislogik / `logic.py`-Tabellen). `hidden-weather` und `balance-pass` in `logic.py` absprechen |
| 1 | F3 `badges`, F7 `fast-forward`, F5 `queue-figures`, F4 `weather-visuals` | ja, vier Personen: zwei Logik, zwei Optik |
| 2 | F1 `events-and-disruptions`, F2 `popularity`, F8 `emergency-loan`, `shop-art` (Roadmap) | ja; F1 und F2 hängen beide einen Faktor an `FACTORS`, nacheinander zusammenführen |
| 3 | F6 `shop-walk`, F9 `season-result`, F11 `outfits`, Aufräumen (Q1, D1) | ja; F6 braucht eine Person für mehrere Tage |
| 4, zuletzt | F10 Editor für Personal, dann `demo-scenarios`, dann `final-polish` | nacheinander |

## 4. Vorschlag für eigene Specs und Issues

| Titel | Inhalt | Out of scope |
|---|---|---|
| `smooth-frames` | P1 und P2: Schatten ohne Filter, Zeitschritt mit Teilschritten. Fertig, wenn die Welt auf dem Testrechner 60 Bilder/s hält und 3 Sekunden Laufen rund 10,5 Felder ergeben | Boden-Cache, Sichtfeld für Objekte, Dach-Blende, neue Optik |
| `calm-panels` | U1, U2, U3: Fenster nur bei geändertem Inhalt neu zeichnen, getippte Werte behalten, Klicks einreihen, veraltete Texte weg | Neues Aussehen der Fenster, `shop-walk`, Dashboard |
| `hidden-weather` | B1: Vor dem Öffnen hängt keine gesendete Zahl am echten Wetter. Neuer Test in neuer Datei | Änderung der Fehlerquote, Ereignisse, Wetter-Optik |
| `balance-pass` | G1, B2, B3, B4: Zahlen der Shops, Sackgasse, Falle, Lagerlimit. Simulation als Wächter-Test. Geänderte alte Tests einzeln in "Decide" nennen | Neue Regeln wie Beliebtheit oder Ereignisse, `warehouse`, Notkredit |
| `retire-trade-endpoint` | B5: `/api/open` entfernen oder hinter den Editor-Schalter; `/api/day-override` mit dem Editor-Weg zusammenlegen. Test-Änderungen bestätigt der Spec-Besitzer | `trade_day` als Funktion (der Editor braucht sie), Änderungen an der Schicht |
| `render-cache` | P3, P4, P5: Boden und Dach in Offscreen-Canvas, Objektliste einmal, Sichtfeld | Neue Zeichnungen, Wetter-Optik, Auflösung |
| `lean-responses` | P6, P7, P10: schlanke Tick-Antwort, Dashboard nur sichtbar zeichnen, Überspringen mit einer Kopie | Neue Endpunkte für Features, Sitzungen |
| `editor-staff` | B7: Mitarbeiter im Editor-Patch, Plätze bekommen ihren Mitarbeiter | Szenarien, Erklär-Karten, offener Tag im Patch |
| `cleanup-dead-code` | Q1, D1, B6, B8: toter Code, alte Specs markieren, README und Roadmap berichtigen, Preis-Text, Rückfall beim Produktnamen | Aufteilen der großen Dateien (eigene Spec je Datei), Verhaltensänderungen |
| `deploy-ready` | S1: nur wenn die App öffentlich laufen soll: Sitzung pro Spieler, Produktions-Server, Header | Benutzerkonten, Bestenliste über mehrere Spieler |
| Features | F1 bis F11 je eine Spec, siehe 3.4 | je Zeile in 3.4 |

## 5. Geänderte Dateien und Testausgabe

Geändert: nur `docs/audit-report.md` (neu). Nichts in `tests/`, kein Code, keine Spec. Der Branch
`audit` ist angelegt, es wurde nichts committet.

Finale Ausgabe von `uv run pytest` nach dem Schreiben des Berichts:

```
platform darwin -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
configfile: pyproject.toml
testpaths: tests, checks
collected 785 items

tests/test_click_walk.py .                                               [  0%]
tests/test_day_context.py ...........................                    [  3%]
tests/test_day_cycle.py .........                                        [  4%]
tests/test_editor_mode.py .............................................. [ 10%]
.....................................................                    [ 17%]
tests/test_first_feature.py ...............                              [ 19%]
tests/test_full_run.py .......                                           [ 20%]
tests/test_map_view.py .......                                           [ 21%]
tests/test_nova_wings.py ..........................                      [ 24%]
tests/test_nova_zones.py ...................                             [ 26%]
tests/test_outlook.py ...............................                    [ 30%]
tests/test_outlook_hidden_weather.py .                                   [ 30%]
tests/test_outlook_leftovers.py .                                        [ 30%]
tests/test_pricing.py .................................................. [ 37%]
.................................................                        [ 43%]
tests/test_shop_process.py ..............................                [ 47%]
tests/test_shop_scenarios.py .............                               [ 49%]
tests/test_shop_skip.py .............                                    [ 50%]
tests/test_shop_unlock.py .............................................  [ 56%]
tests/test_staff.py .................................................... [ 63%]
.......................                                                  [ 65%]
tests/test_staff_all_shops.py ............                               [ 67%]
tests/test_staff_leftovers.py .....                                      [ 68%]
tests/test_staff_review.py .....                                         [ 68%]
tests/test_stock_overview.py ....                                        [ 69%]
tests/test_stock_panel.py .......                                        [ 70%]
tests/test_walk_in.py ........................                           [ 73%]
tests/test_world_api.py ................................................ [ 79%]
........                                                                 [ 80%]
tests/test_world_art.py ..........................................       [ 85%]
tests/test_world_core.py ............................................... [ 91%]
......................................                                   [ 96%]
tests/test_world_paths.py ...................                            [ 98%]
checks/test_finite_prices.py ........                                    [100%]

============================= 785 passed in 20.33s =============================
```
