# GO_1.12.0

> Auto-generated from GO_1.12.0.pdf for AI consumption.

---


<!-- Page 1 -->

# Spezifikation

# GO – Generic Office Library

# (OFML-Part II)

# Version 1.12

Annett Wiegand, Andrea Schramm, Falk Zühlsdorff, Ekkehard Beier
(EasternGraphics GmbH)

1
© 1998 - 2015 Der Verband Büro-, Sitz- und Objektmöbel e.V. (BSO)

4. November 2015

Die Klassenbibliothek GO stellt grundlegende Funktionalität für den
Anwendungsbereich der Büromöbelindustrie bereit. Diese Spezifikation
beschreibt die Eigenschaften und Einsatzmöglichkeiten der aktuell
definierten GO-Typen.

1
GO wurde im Auftrag des Verbandes Büro-, Sitz- und Objektmöbel e.V. durch die EasternGraphics GmbH entwickelt.
Seite 1 von 43

<!-- Page 2 -->

# Inhaltsverzeichnis

1. GO-Typen für elementare Interaktionen ................................................................................ 3
GOXRot ........................................................................................................................................... 4
GOYRot ........................................................................................................................................... 4
GOZRot ........................................................................................................................................... 5
GOXLRot ........................................................................................................................................ 5
GOYLRot ........................................................................................................................................ 6
GOZLRot ......................................................................................................................................... 7
GOXTrans ........................................................................................................................................ 7
GOYTrans ........................................................................................................................................ 8
GOZTrans ........................................................................................................................................ 8
GOXLTrans ..................................................................................................................................... 9
GOYLTrans ..................................................................................................................................... 9
GOZLTrans .................................................................................................................................... 10
GOYRotYLTrans .......................................................................................................................... 10
GOXLRotYLTrans ........................................................................................................................ 11
GOXLRotYLZLTrans ................................................................................................................... 12
GoYLRotZLTrans ......................................................................................................................... 13
2. GO-Typen für komplexe Interaktionen ................................................................................. 14
2.1 Container mit Auszugssperre ............................................................................................. 15
2.2 Flügeltürenschrank mit Sperre der L/R Tür ....................................................................... 15
2.3 Querrolladenschrank gerade mit unprofilierter Front ........................................................ 16
2.4 Vertikalrolladenschrank gerade mit unprofilierter Front ................................................... 18
2.5 Querrolladenschrank gerade mit profilierter Front ............................................................ 19
2.6 Vertikalrolladenschrank gerade mit profilierter Front ....................................................... 21
2.7 Querrolladenschrank gebogen mit unprofilierter Front ..................................................... 23
2.8 Vertikalrolladenschrank gebogen mit unprofilierter Front ................................................ 25
2.9 Verschieben im Raster x und z .......................................................................................... 28
2.10 Verschieben im Raster x und y .......................................................................................... 28
2.11 Verschieben im Raster y und z .......................................................................................... 29
2.12 GoYLTransYRotS ............................................................................................................. 29
2.13 GoYLTransYRotS2 ........................................................................................................... 30
2.14 Höhenverstellung für Tisch mit A-Fuß .............................................................................. 32
2.15 Synchronschiebebewegung entlang der X-Achse ............................................................. 33
2.16 Synchronschiebebewegung entlang der Y-Achse ............................................................. 35
2.17 Synchronschiebebewegung entlang der Z-Achse .............................................................. 36
2.18 Einschub-Klappe ................................................................................................................ 38
2.19 Y-Verschiebung mit gleichzeitiger abhängiger Z-Verschiebung ...................................... 39
3. Sonstige Typen ......................................................................................................................... 40
3.1 Zubehörplazierungsparameter (GoAccParameters) ........................................................... 40
3.2 Skalierungsknoten (GoScaling) ......................................................................................... 41
Historie .............................................................................................................................................. 43

Seite 2 von 43

<!-- Page 3 -->

# 1. GO-Typen für elementare Interaktionen

Anmerkung zum Koordinatensystem:
In der Virtual Reality (VR=OFML) und im ACAD werden verschiedene Koordinatensysteme
verwendet.

z
y

# VR ACAD

y

x
x
z

Das CAD-Koordinatensystem ist im Vergleich zu OFML um 90° um die x-Achse gedreht, so dass
die y-Achse nicht mehr in die Tiefe, sondern in die Höhe zeigt. Der GO-Klassenname gibt die
Bewegung innerhalb des OFML Systems an. Als Hilfestellung wird in der bildlichen Darstellung die
CAD Variante verwendet.

Seite 3 von 43

<!-- Page 4 -->

GOXRot

Kurzbeschreibung: Basisklasse für uneingeschränkte Rotation um die x-Achse.
Parameter:
Langbeschreibung: Diese Klasse ermöglicht die uneingeschränkte Rotation um die x-Achse.
Jede Verschiebung entlang irgendeiner Achse ist jedoch unterbunden.
Beispiel: Kurbel zur Höhenverstellung

z

x

-y

GOYRot

Kurzbeschreibung: Basisklasse für uneingeschränkte Rotation um die y-Achse.
Parameter:
Langbeschreibung: Diese Klasse ermöglicht die uneingeschränkte Rotation um die y-Achse.
Jede Verschiebung entlang irgendeiner Achse ist jedoch unterbunden.
Beispiel: Anwendungsgebiet ist bspw. das Oberteil von Drehstühlen ohne
Höhenverstellung.

z

x

-y

Seite 4 von 43

| Kurzbeschreibung: | Basisklasse für uneingeschränkte Rotation um die x-Achse. |
| --- | --- |
| Parameter: |  |
| Langbeschreibung: | Diese Klasse ermöglicht die uneingeschränkte Rotation um die x-Achse.
Jede Verschiebung entlang irgendeiner Achse ist jedoch unterbunden. |
| Beispiel: | Kurbel zur Höhenverstellung |

| Kurzbeschreibung: | Basisklasse für uneingeschränkte Rotation um die y-Achse. |
| --- | --- |
| Parameter: |  |
| Langbeschreibung: | Diese Klasse ermöglicht die uneingeschränkte Rotation um die y-Achse.
Jede Verschiebung entlang irgendeiner Achse ist jedoch unterbunden. |
| Beispiel: | Anwendungsgebiet ist bspw. das Oberteil von Drehstühlen ohne
Höhenverstellung. |

<!-- Page 5 -->

GOZRot

Kurzbeschreibung: Basisklasse für uneingeschränkte Rotation um die z-Achse.
Parameter:
Langbeschreibung: Diese Klasse ermöglicht die uneingeschränkte Rotation um die z-Achse.
Jede Verschiebung entlang irgendeiner Achse ist jedoch unterbunden.
Beispiel: Drehgriff, Kurbel nach vorn

z

x

-y

GOXLRot

Kurzbeschreibung: Basisklasse für eingeschränkte Rotation um die x-Achse.
Parameter: 1. Der geöffnete Winkel
2. Der geschlossene Winkel
3. Initialwert des Winkels. Dieser kann natürlich auch einer der beiden
Randwinkel sein.
Langbeschreibung: Diese Klasse ermöglicht die eingeschränkte Rotation um die x-Achse. Jede
Verschiebung entlang irgendeiner Achse ist jedoch unterbunden.
Beispiel: Zum Beispiel eine Klapptür, die nach oben oder unten zu öffnen ist.
Eingeschränkte Rotation um die x-Achse.

Seite 5 von 43

| Kurzbeschreibung: | Basisklasse für uneingeschränkte Rotation um die z-Achse. |
| --- | --- |
| Parameter: |  |
| Langbeschreibung: | Diese Klasse ermöglicht die uneingeschränkte Rotation um die z-Achse.
Jede Verschiebung entlang irgendeiner Achse ist jedoch unterbunden. |
| Beispiel: | Drehgriff, Kurbel nach vorn |

| Kurzbeschreibung: | Basisklasse für eingeschränkte Rotation um die x-Achse. |
| --- | --- |
| Parameter: | 1. Der geöffnete Winkel
2. Der geschlossene Winkel
3. Initialwert des Winkels. Dieser kann natürlich auch einer der beiden
Randwinkel sein. |
| Langbeschreibung: | Diese Klasse ermöglicht die eingeschränkte Rotation um die x-Achse. Jede
Verschiebung entlang irgendeiner Achse ist jedoch unterbunden. |
| Beispiel: | Zum Beispiel eine Klapptür, die nach oben oder unten zu öffnen ist.
Eingeschränkte Rotation um die x-Achse. |

<!-- Page 6 -->

z

x

-y

GOYLRot

Kurzbeschreibung: Basisklasse für eingeschränkte Rotation um die y-Achse.
Parameter: 1. der geöffnete Winkel
2. der geschlossene Winkel
3. der Initialwert des Winkels. Dieser kann natürlich auch einer der beiden
Randwinkel sein.
Langbeschreibung: Diese Klasse ermöglicht die eingeschränkte Rotation um die y-Achse. Jede
Verschiebung entlang irgendeiner Achse ist jedoch unterbunden.
Beispiel: Eine einfache Schranktür.

z

x

-y

Seite 6 von 43

| Kurzbeschreibung: | Basisklasse für eingeschränkte Rotation um die y-Achse. |
| --- | --- |
| Parameter: | 1. der geöffnete Winkel
2. der geschlossene Winkel
3. der Initialwert des Winkels. Dieser kann natürlich auch einer der beiden
Randwinkel sein. |
| Langbeschreibung: | Diese Klasse ermöglicht die eingeschränkte Rotation um die y-Achse. Jede
Verschiebung entlang irgendeiner Achse ist jedoch unterbunden. |
| Beispiel: | Eine einfache Schranktür. |

<!-- Page 7 -->

GOZLRot

Kurzbeschreibung: Basisklasse für eingeschränkte Rotation um die z-Achse.
Parameter: 1. Winkel links der z-Achse
2. Winkel rechts der z-Achse
3. Initialwert des Winkels. Dieser kann natürlich auch einer der beiden
Randwinkel sein.
Langbeschreibung: Diese Klasse ermöglicht die eingeschränkte Rotation um die z-Achse. Jede
Verschiebung entlang irgendeiner Achse ist jedoch unterbunden.
Beispiel: Fenstergriffe, Klapptheken

z

x

-y

GOXTrans

Kurzbeschreibung: Basisklasse für uneingeschränkte Verschiebung entlang der x-Achse.
Parameter:
Langbeschreibung: Diese Klasse ermöglicht die uneingeschränkte Verschiebung entlang der x-
Achse. Jegliche Rotation ist ausgeschlossen.
Beispiel: Wandanbauelement

z

x

-y

Seite 7 von 43

| Kurzbeschreibung: | Basisklasse für eingeschränkte Rotation um die z-Achse. |
| --- | --- |
| Parameter: | 1. Winkel links der z-Achse
2. Winkel rechts der z-Achse
3. Initialwert des Winkels. Dieser kann natürlich auch einer der beiden
Randwinkel sein. |
| Langbeschreibung: | Diese Klasse ermöglicht die eingeschränkte Rotation um die z-Achse. Jede
Verschiebung entlang irgendeiner Achse ist jedoch unterbunden. |
| Beispiel: | Fenstergriffe, Klapptheken |

| Kurzbeschreibung: | Basisklasse für uneingeschränkte Verschiebung entlang der x-Achse. |
| --- | --- |
| Parameter: |  |
| Langbeschreibung: | Diese Klasse ermöglicht die uneingeschränkte Verschiebung entlang der x-
Achse. Jegliche Rotation ist ausgeschlossen. |
| Beispiel: | Wandanbauelement |

<!-- Page 8 -->

GOYTrans

Kurzbeschreibung: Basisklasse für uneingeschränkte Verschiebung entlang der y-Achse.
Parameter:
Langbeschreibung: Diese Klasse ermöglicht die uneingeschränkte Verschiebung entlang der y-
Achse. Jegliche Rotation ist ausgeschlossen.
Beispiel: Wandanbauelement

z

x

-y

GOZTrans

Kurzbeschreibung: Basisklasse für uneingeschränkte Verschiebung entlang der z-Achse.
Parameter:
Langbeschreibung: Diese Klasse ermöglicht die uneingeschränkte Verschiebung entlang der z-
Achse. Jegliche Rotation ist ausgeschlossen.
Beispiel: Verschiebung entlang der negativen CAD y-Achse.

z

x

-y

Seite 8 von 43

| Kurzbeschreibung: | Basisklasse für uneingeschränkte Verschiebung entlang der y-Achse. |
| --- | --- |
| Parameter: |  |
| Langbeschreibung: | Diese Klasse ermöglicht die uneingeschränkte Verschiebung entlang der y-
Achse. Jegliche Rotation ist ausgeschlossen. |
| Beispiel: | Wandanbauelement |

| Kurzbeschreibung: | Basisklasse für uneingeschränkte Verschiebung entlang der z-Achse. |
| --- | --- |
| Parameter: |  |
| Langbeschreibung: | Diese Klasse ermöglicht die uneingeschränkte Verschiebung entlang der z-
Achse. Jegliche Rotation ist ausgeschlossen. |
| Beispiel: | Verschiebung entlang der negativen CAD y-Achse. |

<!-- Page 9 -->

GOXLTrans

Kurzbeschreibung: Basisklasse für eingeschränkte Verschiebung entlang der x-Achse.
Parameter: 1. die linke Obergrenze
2. die rechte Obergrenze
3. der Initialwert. Dieser kann natürlich auch einer der beiden Grenzwerte
sein.
Langbeschreibung: Diese Klasse ermöglicht die eingeschränkte Verschiebung entlang der x-
Achse. Jegliche Rotation ist ausgeschlossen.
Beispiel: Schiebetüren

z

x

-y

GOYLTrans

Kurzbeschreibung: Basisklasse für eingeschränkte Verschiebung entlang der y-Achse.
Parameter: 1. die untere Grenze
2. die obere Grenze
3. die Starthöhe
Langbeschreibung: Diese Klasse ermöglicht die eingeschränkte Verschiebung entlang der y-
Achse. Jegliche Rotation ist ausgeschlossen.
Beispiel: Höhenverstellbare Tischplatten

z

x

-y

Seite 9 von 43

| Kurzbeschreibung: Basisklasse für eingeschränkte Verschiebung entlang der x-Achse. |  |
| --- | --- |
| Parameter: | 1. die linke Obergrenze
2. die rechte Obergrenze
3. der Initialwert. Dieser kann natürlich auch einer der beiden Grenzwerte
sein. |
| Langbeschreibung: | Diese Klasse ermöglicht die eingeschränkte Verschiebung entlang der x-
Achse. Jegliche Rotation ist ausgeschlossen. |
| Beispiel: | Schiebetüren |

| Kurzbeschreibung: | Basisklasse für eingeschränkte Verschiebung entlang der y-Achse. |
| --- | --- |
| Parameter: | 1. die untere Grenze
2. die obere Grenze
3. die Starthöhe |
| Langbeschreibung: | Diese Klasse ermöglicht die eingeschränkte Verschiebung entlang der y-
Achse. Jegliche Rotation ist ausgeschlossen. |
| Beispiel: | Höhenverstellbare Tischplatten |

<!-- Page 10 -->

GOZLTrans

Kurzbeschreibung: Basisklasse für eingeschränkte Verschiebung entlang der z-Achse.
Parameter: 1. die vorderste Grenze
2. die hinterste Grenze
3. die Startposition
Langbeschreibung: Diese Klasse ermöglicht die eingeschränkte Verschiebung entlang der z-
Achse. Jegliche Rotation ist ausgeschlossen.
Beispiel: Schubladen, Aktenauszüge

z

x

-y

GOYRotYLTrans

Kurzbeschreibung: Basisklasse für uneingeschränkte Rotation um die y-Achse und
eingeschränkte Verschiebung entlang der y-Achse.
Parameter: 1. die untere Grenze
2. die obere Grenze
3. die Starthöhe
Langbeschreibung: Diese Klasse ermöglicht die uneingeschränkte Rotation um die y-Achse,
sowie die eingeschränkte Verschiebung entlang der y-Achse.
Beispiel: Anwendungsgebiet ist bspw. das Oberteil von Drehstühlen.

z

x

-y

Seite 10 von 43

| Kurzbeschreibung: | Basisklasse für eingeschränkte Verschiebung entlang der z-Achse. |
| --- | --- |
| Parameter: | 1. die vorderste Grenze
2. die hinterste Grenze
3. die Startposition |
| Langbeschreibung: | Diese Klasse ermöglicht die eingeschränkte Verschiebung entlang der z-
Achse. Jegliche Rotation ist ausgeschlossen. |
| Beispiel: | Schubladen, Aktenauszüge |

| Kurzbeschreibung: | Basisklasse für uneingeschränkte Rotation um die y-Achse und
eingeschränkte Verschiebung entlang der y-Achse. |
| --- | --- |
| Parameter: | 1. die untere Grenze
2. die obere Grenze
3. die Starthöhe |
| Langbeschreibung: | Diese Klasse ermöglicht die uneingeschränkte Rotation um die y-Achse,
sowie die eingeschränkte Verschiebung entlang der y-Achse. |
| Beispiel: | Anwendungsgebiet ist bspw. das Oberteil von Drehstühlen. |

|  |  |
| --- | --- |
|  |  |

<!-- Page 11 -->

GOXLRotYLTrans

Kurzbeschreibung: Basisklasse für eingeschränkte Rotation um die x-Achse und
eingeschränkte Verschiebung entlang der y-Achse.
Parameter: 1. Öffnungswinkel
2. Geschlossener Winkel
3. Initialwert des Winkels. Dieser kann natürlich auch einer der beiden
Randwinkel sein.
4. die vorderste Grenze
5. die hinterste Grenze
6. die Startposition. Diese kann natürlich auch zwischen den beiden
Grenzwerten liegen.
Langbeschreibung: Diese Klasse ermöglicht die eingeschränkte Rotation um die x-Achse,
sowie die eingeschränkte Verschiebung entlang der y-Achse.
Beispiel: Höhenverstellbare und neigbare Tischplatten

z

x

-y

Seite 11 von 43

| Kurzbeschreibung: | Basisklasse für eingeschränkte Rotation um die x-Achse und
eingeschränkte Verschiebung entlang der y-Achse. |
| --- | --- |
| Parameter: | 1. Öffnungswinkel
2. Geschlossener Winkel
3. Initialwert des Winkels. Dieser kann natürlich auch einer der beiden
Randwinkel sein.
4. die vorderste Grenze
5. die hinterste Grenze
6. die Startposition. Diese kann natürlich auch zwischen den beiden
Grenzwerten liegen. |
| Langbeschreibung: | Diese Klasse ermöglicht die eingeschränkte Rotation um die x-Achse,
sowie die eingeschränkte Verschiebung entlang der y-Achse. |
| Beispiel: | Höhenverstellbare und neigbare Tischplatten |

<!-- Page 12 -->

GOXLRotYLZLTrans

Kurzbeschreibung: Basisklasse für eingeschränkte Rotation um die x-Achse und
eingeschränkte Verschiebung entlang der y- und der z-Achse.
Parameter: 1. Öffnungswinkel
2. Geschlossener Winkel
3. Initialwert des Winkels. Dieser kann natürlich auch einer der beiden
Randwinkel sein.
4. die untere Grenze
5. die obere Grenze
6. die Starthöhe, diese kann natürlich auch zwischen den beiden
Grenzwerten liegen
7. die vorderste Grenze
8. die hinterste Grenze
9. die Startposition
Langbeschreibung: Diese Klasse ermöglicht die eingeschränkte Rotation um die x-Achse und
die eingeschränkte Verschiebung entlang der y- und der z-Achse.

Beispiel: Höhenverstellbare, neigbare Tischplatten, die nach vorn und hinten zu
verschieben sind

z

x

-y

Seite 12 von 43

| Kurzbeschreibung: | Basisklasse für eingeschränkte Rotation um die x-Achse und
eingeschränkte Verschiebung entlang der y- und der z-Achse. |
| --- | --- |
| Parameter: | 1. Öffnungswinkel
2. Geschlossener Winkel
3. Initialwert des Winkels. Dieser kann natürlich auch einer der beiden
Randwinkel sein.
4. die untere Grenze
5. die obere Grenze
6. die Starthöhe, diese kann natürlich auch zwischen den beiden
Grenzwerten liegen
7. die vorderste Grenze
8. die hinterste Grenze
9. die Startposition |
| Langbeschreibung: | Diese Klasse ermöglicht die eingeschränkte Rotation um die x-Achse und
die eingeschränkte Verschiebung entlang der y- und der z-Achse. |
| Beispiel: | Höhenverstellbare, neigbare Tischplatten, die nach vorn und hinten zu
verschieben sind |

|  |  |
| --- | --- |
|  |  |
|  |  |

<!-- Page 13 -->

GoYLRotZLTrans

Kurzbeschreibung: Basisklasse für eingeschränkte Rotation um die y-Achse und
eingeschränkte Verschiebung entlang der z-Achse.
Parameter: 1. Geschlossener Winkel
2. Öffnungswinkel
3. Initialwert des Winkels. Dieser kann natürlich auch einer der beiden
Randwinkel sein
4. die hinterste Grenze
5. die vorderste Grenze
6. die Startposition
Langbeschreibung: Diese Klasse ermöglicht die eingeschränkte Rotation um die y-Achse,
sowie die eingeschränkte Verschiebung entlang der z-Achse.
Beispiel: Anwendungsgebiet ist bspw. Die Armlehne von Drehstühlen.

z

x

-y

Seite 13 von 43

| Kurzbeschreibung: | Basisklasse für eingeschränkte Rotation um die y-Achse und
eingeschränkte Verschiebung entlang der z-Achse. |
| --- | --- |
| Parameter: | 1. Geschlossener Winkel
2. Öffnungswinkel
3. Initialwert des Winkels. Dieser kann natürlich auch einer der beiden
Randwinkel sein
4. die hinterste Grenze
5. die vorderste Grenze
6. die Startposition |
| Langbeschreibung: | Diese Klasse ermöglicht die eingeschränkte Rotation um die y-Achse,
sowie die eingeschränkte Verschiebung entlang der z-Achse. |
| Beispiel: | Anwendungsgebiet ist bspw. Die Armlehne von Drehstühlen. |

<!-- Page 14 -->

# 2. GO-Typen für komplexe

# Interaktionen

Komplexe Typen enthalten immer mindestens einen bestimmten GO-Typ als Kind. Der
übergeordnete Typ muß davon ausgehen können, dass dieser oder diese existieren.

Typenübersicht:

2.1 Container mit Auszugssperre

2.2 Flügeltürenschrank mit Sperre der L/R Tür

2.3 Querrolladenschrank gerade mit unprofilierter Front

2.4 Vertikalrolladenschrank gerade mit unprofilierter Front

2.5 Querrolladenschrank gerade mit profilierter Front

2.6 Vertikalrolladenschrank gerade mit profilierter Front

2.7 Querrolladenschrank gebogen mit unprofilierter Front

2.8 Vertikalrolladenschrank gebogen mit unprofilierter Front

2.9 Verschieben im Raster x und z

2.10 Verschieben im Raster x und y

2.11 Verschieben im Raster y und z

2.12 GoYLTransYRotS (Lehne neigt sich n mal so stark wie der Sitz)

2.13 GoYLTransYRotS2

2.14 Höhenverstellung für Tisch mit A-Fuß

2.15 Synchronschiebebewegung entlang der X-Achse

2.16 Synchronschiebebewegung entlang der Y-Achse

2.17 Synchronschiebebewegung entlang der Z-Achse

2.18 Einschub-Klappe

2.19 GoYLTransZDepTrans (Y-Verschiebung mit gleichzeitiger abhängiger Z-Verschiebung)

Seite 14 von 43

<!-- Page 15 -->

2.1 Container mit Auszugssperre

2.1.1 GoContainerPart

Beschreibung: Oberklasse für alle mit einer Auszugssperre versehenen
Schubkästen. Diesem Typ muß mind. ein GoDrawer untergeordnet
sein.

Parameter:

2.1.2 GoDrawer

Beschreibung: Klasse für eingeschränkte Verschiebung entlang der z-Achse, nur
dann, wenn nicht bereits ein anderer Schubkasten geöffnet ist.
Jedem Schubkasten, der mit einer Auszugssperre versehen werden
soll, wird dieser Typ einmal zugeordnet.
Parameter: 1. die hinterste Grenze (Schubkasten ist geschlossen )
2. die vorderste Grenze
3. die Startposition

2.2 Flügeltürenschrank mit Sperre der L/R Tür

2.2.1 GoDDoor

Beschreibung: GoDDoor ist die Oberklasse der Türen. Ihr müssen ein GoDoor und
ein GoDoorFix untergeordnet sein.
Parameter:

2.2.2 GoDoor

Beschreibung: Klasse für die Tür, die zuerst geöffnet werden muß. Ansonsten ist die
andere gesperrt.
Zu beachten: Ist dies die linke Tür, werden die Winkel positiv angegeben; ist es die
rechte Tür, sind die Winkel negativ anzugeben.
Parameter: 1. geöffneter Winkel
2. geschlossener Winkel

Seite 15 von 43

| Beschreibung: | Oberklasse für alle mit einer Auszugssperre versehenen
Schubkästen. Diesem Typ muß mind. ein GoDrawer untergeordnet
sein. |
| --- | --- |
| Parameter: |  |

| Beschreibung: | Klasse für eingeschränkte Verschiebung entlang der z-Achse, nur
dann, wenn nicht bereits ein anderer Schubkasten geöffnet ist.
Jedem Schubkasten, der mit einer Auszugssperre versehen werden
soll, wird dieser Typ einmal zugeordnet. |
| --- | --- |
| Parameter: | 1. die hinterste Grenze (Schubkasten ist geschlossen )
2. die vorderste Grenze
3. die Startposition |

| Beschreibung: | GoDDoor ist die Oberklasse der Türen. Ihr müssen ein GoDoor und
ein GoDoorFix untergeordnet sein. |
| --- | --- |
| Parameter: |  |

| Beschreibung: | Klasse für die Tür, die zuerst geöffnet werden muß. Ansonsten ist die
andere gesperrt. |
| --- | --- |
| Zu beachten: | Ist dies die linke Tür, werden die Winkel positiv angegeben; ist es die
rechte Tür, sind die Winkel negativ anzugeben. |
| Parameter: | 1. geöffneter Winkel
2. geschlossener Winkel |

<!-- Page 16 -->

3. Startwinkel
4. Winkel, wie weit diese Tür geöffnet sein muß, bevor GoDoorFix
geöffnet werden kann.
Bsp.: 90, 0, 0, 25

2.2.3 GoDoorFix

Beschreibung: Klasse für die Tür, die nur geöffnet werden kann, wenn die andere
bereits auf ist.
Zu beachten: Ist dies die linke Tür, werden die Winkel positiv angegeben; ist es die
rechte Tür, sind die Winkel negativ anzugeben.
Parameter: 1. geöffneter Winkel
2. geschlossener Winkel
3. Startwinkel
4. Winkel, wie weit diese Tür geöffnet sein muß (falls sie nicht
geschlossen ist), um GoDoor wieder zu schließen
5. Winkel, wie weit diese Tür geschlossen werden kann, wenn
GoDoor geschlossen ist
Bsp.: -90, 0, 0, -25, -10

2.3 Querrolladenschrank gerade mit unprofilierter Front

Wird verwendet, wenn die Lamellen aus einer Geometrie bestehen.

Alle Punkte / Werte sind vom Einfügepunkt der entsprechenden Klasse ausgehend
anzugeben.

Öffnung nach links Öffnung nach rechts

GoHRHand GoHRHand GoHRDoor
le le GoHRDo R
GoHRDoor
or
L
Seite 16 von 43
GoHRDoor

|  | 3. Startwinkel
4. Winkel, wie weit diese Tür geöffnet sein muß, bevor GoDoorFix
geöffnet werden kann.
Bsp.: 90, 0, 0, 25 |
| --- | --- |

| Beschreibung: | Klasse für die Tür, die nur geöffnet werden kann, wenn die andere
bereits auf ist. |
| --- | --- |
| Zu beachten: | Ist dies die linke Tür, werden die Winkel positiv angegeben; ist es die
rechte Tür, sind die Winkel negativ anzugeben. |
| Parameter: | 1. geöffneter Winkel
2. geschlossener Winkel
3. Startwinkel
4. Winkel, wie weit diese Tür geöffnet sein muß (falls sie nicht
geschlossen ist), um GoDoor wieder zu schließen
5. Winkel, wie weit diese Tür geschlossen werden kann, wenn
GoDoor geschlossen ist
Bsp.: -90, 0, 0, -25, -10 |

<!-- Page 17 -->

2.3.1 GoHRDoorL

Beschreibung: Oberklasse für Querrolladenschrank mit Öffnung nach links. Diesem
Typ muß ein GoHRDoor und ein GoHRHandle untergeordnet sein.
Zu beachten: Die Klasse ist immer an der linken unteren Vorderecke der gesamten
Tür einzufügen.
Parameter: 1. die rechte Grenze (Tür ist geschlossen)
2. die linke Grenze (Tür ist komplett auf)
3. der Initialwert
4. die Breite einer Lamelle
5. die Höhe der Lamellen
Bsp.: 1.0, 0.1, 1.0, 0.035, 0.75

2.3.2 GoHRDoorR

Beschreibung: Oberklasse für Querrolladenschrank mit Öffnung nach rechts. Diesem
Typ muß ein GoHRDoor und ein GoHRHandle untergeordnet sein.
Zu beachten: Die Klasse ist immer an der rechten unteren Vorderecke der
gesamten Tür einzufügen.
Parameter: 1. die linke Grenze (Tür ist geschlossen)
2. die rechte Grenze (Tür ist komplett auf)
3. der Initialwert
4. die Breite einer Lamelle
5. die Höhe der Lamellen
Bsp.: -1.0, -0.1, -1.0, 0.035, 0.75

2.3.3 GoHRDoor

Beschreibung: Klasse für die Lamellen.
Zu beachten: Die Klasse ist immer an der linken unteren Vorderecke des gesamten
Lamellenteils einzufügen.
Parameter: 1. die Breite einer Lamelle
2. die Höhe der Lamellen
Bsp.: 0.035, 0.75

Seite 17 von 43

| Beschreibung: | Oberklasse für Querrolladenschrank mit Öffnung nach links. Diesem
Typ muß ein GoHRDoor und ein GoHRHandle untergeordnet sein. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der linken unteren Vorderecke der gesamten
Tür einzufügen. |
| Parameter: | 1. die rechte Grenze (Tür ist geschlossen)
2. die linke Grenze (Tür ist komplett auf)
3. der Initialwert
4. die Breite einer Lamelle
5. die Höhe der Lamellen
Bsp.: 1.0, 0.1, 1.0, 0.035, 0.75 |

| Beschreibung: | Oberklasse für Querrolladenschrank mit Öffnung nach rechts. Diesem
Typ muß ein GoHRDoor und ein GoHRHandle untergeordnet sein. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der rechten unteren Vorderecke der
gesamten Tür einzufügen. |
| Parameter: | 1. die linke Grenze (Tür ist geschlossen)
2. die rechte Grenze (Tür ist komplett auf)
3. der Initialwert
4. die Breite einer Lamelle
5. die Höhe der Lamellen
Bsp.: -1.0, -0.1, -1.0, 0.035, 0.75 |

| Beschreibung: | Klasse für die Lamellen. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der linken unteren Vorderecke des gesamten
Lamellenteils einzufügen. |
| Parameter: | 1. die Breite einer Lamelle
2. die Höhe der Lamellen
Bsp.: 0.035, 0.75 |

<!-- Page 18 -->

2.3.4 GoHRHandle

Beschreibung: Klasse für das Griffstück
Zu beachten: Die Klasse ist immer an der linken unteren Vorderecke des gesamten
Griffteils einzufügen.
Parameter:

2.4 Vertikalrolladenschrank gerade mit unprofilierter Front

Wird verwendet, wenn die Lamellen aus einer Geometrie bestehen.

Alle Punkte/Werte sind von Einfügepunkt der entsprechenden Klasse ausgehend
anzugeben.

Öffnung nach unten Öffnung nach oben

GoVRDoor
U
GoVRHand
le
GoVRDo
or
GoVRHand
GoVRDoor le
D

GoVRDoor
2.4.1 GoVRDoorD

Beschreibung: Oberklasse für Vertikalrolladenschrank mit Öffnung nach unten.
Diesem Typ muß ein GoVRDoor und ein GoVRHandle untergeordnet
sein.
Zu beachten: Die Klasse ist immer an der unteren linken Vorderecke der gesamten
Tür einzufügen.
Parameter: 1. die obere Grenze (Tür ist geschlossen)
2. die untere Grenze (Tür ist komplett auf)
3. der Initialwert
4. die Breite der Lamellen
5. die Höhe einer Lamelle
Bsp.: 1.5, 0.2, 1.3, 0.75, 0.05

Seite 18 von 43

| Beschreibung: | Klasse für das Griffstück |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der linken unteren Vorderecke des gesamten
Griffteils einzufügen. |
| Parameter: |  |

| Beschreibung: | Oberklasse für Vertikalrolladenschrank mit Öffnung nach unten.
Diesem Typ muß ein GoVRDoor und ein GoVRHandle untergeordnet
sein. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der unteren linken Vorderecke der gesamten
Tür einzufügen. |
| Parameter: | 1. die obere Grenze (Tür ist geschlossen)
2. die untere Grenze (Tür ist komplett auf)
3. der Initialwert
4. die Breite der Lamellen
5. die Höhe einer Lamelle
Bsp.: 1.5, 0.2, 1.3, 0.75, 0.05 |

<!-- Page 19 -->

2.4.2 GoVRDoorU

Beschreibung: Oberklasse für Vertikalrolladenschrank mit Öffnung nach rechts.
Diesem Typ muß ein GoVRDoor und ein GoVRHandle untergeordnet
sein.
Zu beachten: Die Klasse ist immer an der oberen linken Vorderecke der gesamten
Tür einzufügen.
Parameter: 1. die untere Grenze (Tür ist geschlossen)
2. die obere Grenze (Tür ist komplett auf)
3. der Initialwert
4. die Breite der Lamellen
5. die Höhe einer Lamelle
Bsp.: -1.5, -0.2, -1.3, 0.75, 0.05

2.4.3 GoVRDoor

Beschreibung: Klasse für die Lamellen.
Zu beachten: Die Klasse ist immer an der unteren linken Vorderecke des gesamten
Lamellenteils einzufügen.
Parameter: 1. die Breite der Lamellen
2. die Höhe einer Lamelle
Bsp.: 0.75, 0.05

2.4.4 GoVRHandle

Beschreibung:
Klasse für das Griffstück
Zu beachten: Die Klasse ist immer an der unteren linken Vorderecke des gesamten
Griffteils einzufügen.
Parameter:

2.5 Querrolladenschrank gerade mit profilierter Front
Ein solcher Querrolladenschrank muß initial geschlossen dargestellt werden!
Für jede Lamelle wird genau eine einzelne Geometrie benötigt.
Die einzelnen Lamellen haben immer die gleiche Stärke (Breite). Die Öffnung der Tür ist nur
in Vielfachen der Lamellenbreite möglich.

Seite 19 von 43

| Beschreibung: | Oberklasse für Vertikalrolladenschrank mit Öffnung nach rechts.
Diesem Typ muß ein GoVRDoor und ein GoVRHandle untergeordnet
sein. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der oberen linken Vorderecke der gesamten
Tür einzufügen. |
| Parameter: | 1. die untere Grenze (Tür ist geschlossen)
2. die obere Grenze (Tür ist komplett auf)
3. der Initialwert
4. die Breite der Lamellen
5. die Höhe einer Lamelle
Bsp.: -1.5, -0.2, -1.3, 0.75, 0.05 |

| Beschreibung: | Klasse für die Lamellen. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der unteren linken Vorderecke des gesamten
Lamellenteils einzufügen. |
| Parameter: | 1. die Breite der Lamellen
2. die Höhe einer Lamelle
Bsp.: 0.75, 0.05 |

| Beschreibung: | Klasse für das Griffstück |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der unteren linken Vorderecke des gesamten
Griffteils einzufügen. |
| Parameter: |  |

<!-- Page 20 -->

2.5.1 GoHRDoorLP

Beschreibung: Oberklasse für Querrolladenschrank mit Öffnung nach links. Diesem
Typ muß ein GoHRDoorP und ein GoHRHandleP untergeordnet sein.
Zu beachten: Die Klasse ist immer an der linken unteren Vorderecke der gesamten
Tür einzufügen.
Parameter: 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. die Breite einer Lamelle
4. die Höhe der Lamellen
Bsp.: 18, 2, 0.035, 0.75

2.5.2 GoHRDoorRP

Beschreibung:
Oberklasse für Querrolladenschrank mit Öffnung nach rechts. Diesem
Typ muß ein GoHRDoorP und ein GoHRHandleP untergeordnet sein.
Zu beachten: Die Klasse ist immer an der rechten unteren Vorderecke der
gesamten Tür einzufügen.
Parameter: 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. die Breite einer Lamelle
4. die Höhe der Lamellen
Bsp.: 18, 2, 0.035, 0.75

2.5.3 GoHRDoorP

Beschreibung: Klasse für die Lamellen.
Zu beachten: Die Klasse ist immer an der linken unteren Vorderecke des gesamten
Lamellenteils einzufügen.
Die Geometrien für die Lamellen werden immer von links nach rechts
angegeben (zuerst die Lamelle links außen, dann die rechts
daneben... zuletzt die rechts außen). Diese Reihenfolge ist unbedingt
einzuhalten.
Parameter: 1. die Breite einer Lamelle
2. die Höhe der Lamellen
Bsp.: 0.035, 0.75

Seite 20 von 43

| Beschreibung: | Oberklasse für Querrolladenschrank mit Öffnung nach links. Diesem
Typ muß ein GoHRDoorP und ein GoHRHandleP untergeordnet sein. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der linken unteren Vorderecke der gesamten
Tür einzufügen. |
| Parameter: | 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. die Breite einer Lamelle
4. die Höhe der Lamellen
Bsp.: 18, 2, 0.035, 0.75 |

| Beschreibung: | Oberklasse für Querrolladenschrank mit Öffnung nach rechts. Diesem
Typ muß ein GoHRDoorP und ein GoHRHandleP untergeordnet sein. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der rechten unteren Vorderecke der
gesamten Tür einzufügen. |
| Parameter: | 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. die Breite einer Lamelle
4. die Höhe der Lamellen
Bsp.: 18, 2, 0.035, 0.75 |

| Beschreibung: | Klasse für die Lamellen. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der linken unteren Vorderecke des gesamten
Lamellenteils einzufügen.
Die Geometrien für die Lamellen werden immer von links nach rechts
angegeben (zuerst die Lamelle links außen, dann die rechts
daneben... zuletzt die rechts außen). Diese Reihenfolge ist unbedingt
einzuhalten. |
| Parameter: | 1. die Breite einer Lamelle
2. die Höhe der Lamellen
Bsp.: 0.035, 0.75 |

<!-- Page 21 -->

2.5.4 GoHRHandleP

Beschreibung: Klasse für das Griffstück
Zu beachten: Die Klasse ist immer an der linken unteren Vorderecke des gesamten
Griffteils einzufügen.
Parameter:

2.6 Vertikalrolladenschrank gerade mit profilierter Front
Ein solcher Vertikalrolladenschrank muß initial geschlossen dargestellt werden!
Für jede Lamelle wird genau eine einzelne Geometrie benötigt.
Die einzelnen Lamellen haben immer die gleiche Stärke (Höhe). Die Öffnung der Tür ist nur
in Vielfachen der Lamellenhöhe möglich.

2.6.1 GoVRDoorDP

Beschreibung: Oberklasse für Vertikalrolladenschrank mit Öffnung nach unten.
Diesem Typ muß ein GoVRDoorP und ein GoVRHandleP
untergeordnet sein.
Zu beachten: Die Klasse ist immer an der unteren linken Vorderecke der gesamten
Tür einzufügen.
Parameter: 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. die Breite der Lamellen
4. die Höhe einer Lamelle
Bsp.: 25, 0, 0.75, 0.035

Seite 21 von 43

| Beschreibung: | Klasse für das Griffstück |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der linken unteren Vorderecke des gesamten
Griffteils einzufügen. |
| Parameter: |  |

| Beschreibung: | Oberklasse für Vertikalrolladenschrank mit Öffnung nach unten.
Diesem Typ muß ein GoVRDoorP und ein GoVRHandleP
untergeordnet sein. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der unteren linken Vorderecke der gesamten
Tür einzufügen. |
| Parameter: | 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. die Breite der Lamellen
4. die Höhe einer Lamelle
Bsp.: 25, 0, 0.75, 0.035 |

<!-- Page 22 -->

2.6.2 GoVRDoorUP

Beschreibung: Oberklasse für Vertikalrolladenschrank mit Öffnung nach oben.
Diesem Typ muß ein GoVRDoorP und ein GoVRHandleP
untergeordnet sein.
Zu beachten: Die Klasse ist immer an der oberen linken Vorderecke der gesamten
Tür einzufügen.
Parameter: 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. die Breite der Lamellen
4. die Höhe einer Lamelle
Bsp.: 25, 0, 0.75, 0.035

2.6.3 GoVRDoorP

Beschreibung: Klasse für die Lamellen.
Zu beachten: Die Klasse ist immer an der unteren linken Vorderecke des gesamten
Lamellenteils einzufügen.
Die Geometrien für die Lamellen werden immer von unten nach oben
angegeben (zuerst die Lamelle ganz unten, dann die darüber...
zuletzt die ganz oben). Diese Reihenfolge ist unbedingt einzuhalten.
Parameter:
1. die Breite der Lamellen
2. die Höhe einer Lamelle
Bsp.: 0.75, 0.035

2.6.4 GoVRHandleP

Beschreibung: Klasse für das Griffstück
Zu beachten: Die Klasse ist immer an der unteren linken Vorderecke des gesamten
Griffteils einzufügen.
Parameter:

Seite 22 von 43

| Beschreibung: | Oberklasse für Vertikalrolladenschrank mit Öffnung nach oben.
Diesem Typ muß ein GoVRDoorP und ein GoVRHandleP
untergeordnet sein. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der oberen linken Vorderecke der gesamten
Tür einzufügen. |
| Parameter: | 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. die Breite der Lamellen
4. die Höhe einer Lamelle
Bsp.: 25, 0, 0.75, 0.035 |

| Beschreibung: | Klasse für die Lamellen. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der unteren linken Vorderecke des gesamten
Lamellenteils einzufügen.
Die Geometrien für die Lamellen werden immer von unten nach oben
angegeben (zuerst die Lamelle ganz unten, dann die darüber...
zuletzt die ganz oben). Diese Reihenfolge ist unbedingt einzuhalten. |
| Parameter: | 1. die Breite der Lamellen
2. die Höhe einer Lamelle
Bsp.: 0.75, 0.035 |

| Beschreibung: | Klasse für das Griffstück |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der unteren linken Vorderecke des gesamten
Griffteils einzufügen. |
| Parameter: |  |

<!-- Page 23 -->

2.7 Querrolladenschrank gebogen mit unprofilierter Front
Bei dieser Klasse ist eine Liste mit den x, z - Eckpunkten der einzelnen Lamellen und des
Griffstücks erforderlich. Diese Liste wird von links nach rechts angegeben.

(Für jedes Element wird der linke und der rechte vordere Eckpunkt aufgeführt. Wobei der
rechte Punkt eines Elementes gleichzeitig der linke Punkt des nachfolgenden ist und
demnach nur einmal angegeben wird.)

Angegeben werden die Breiten- und die Tiefenwerte; die Höhenwerte bleiben für diese Liste
unbeachtet.

Alle Punkte / Werte sind vom Einfügepunkt der entsprechenden Klasse ausgehend
anzugeben.

Öffnung nach links Öffnung nach rechts

GoHIRDoorL GoHIRHandle GoHIRHandle GoHIRDoorR
GoHIRDoor GoHIRDoor

2.7.1 GoHIRDoorL

Beschreibung: Oberklasse für Querrolladenschrank mit gebogener unprofilierter
Front und Öffnung nach links. Diesem Typ muß ein GoHIRDoor und
ein GoHIRHandle untergeordnet sein.
Zu beachten: Die Klasse ist immer an der linken unteren Vorderecke der Front der
Tür einzufügen.
Parameter: 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. initiale Anzahl von Lamellen
4. Punktliste (Anzahl der Punkte = max. Anzahl der Lamellen plus
zwei)
5. Höhe der Lamellen
Bsp.: 3, 0, 3, [[0.0, 0.0], [0.25, 0.14], [0.5, 0.2], [0.75, 0.14], [1.0, 0.0]],
0.75

Seite 23 von 43

| Beschreibung: | Oberklasse für Querrolladenschrank mit gebogener unprofilierter
Front und Öffnung nach links. Diesem Typ muß ein GoHIRDoor und
ein GoHIRHandle untergeordnet sein. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der linken unteren Vorderecke der Front der
Tür einzufügen. |
| Parameter: | 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. initiale Anzahl von Lamellen
4. Punktliste (Anzahl der Punkte = max. Anzahl der Lamellen plus
zwei)
5. Höhe der Lamellen
Bsp.: 3, 0, 3, [[0.0, 0.0], [0.25, 0.14], [0.5, 0.2], [0.75, 0.14], [1.0, 0.0]],
0.75 |

<!-- Page 24 -->

2.7.2 GoHIRDoorR

Beschreibung: Oberklasse für Querrolladenschrank mit gebogener unprofilierter
Front und Öffnung nach rechts. Diesem Typ muß ein GoHIRDoor
und ein GoHIRHandle untergeordnet sein.
Zu beachten: Die Klasse ist immer an der rechten unteren Vorderecke der Front
der Tür einzufügen.
Parameter: 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. initiale Anzahl von Lamellen
4. Punktliste (Anzahl der Punkte = max. Anzahl der Lamellen plus
zwei)
5. Höhe der Lamellen
Bsp.: 3, 0, 3, [[-1.0, 0.0], [-0.75, 0.14], [-0.5, 0.2], [-0.25, 0.14], [0, 0]],
0.75

2.7.3 GoHIRDoor

Beschreibung:
Klasse für die Lamellen.
Zu beachten: Bei einen Schrank mit Öffnung nach links wird die Klasse an der
linken unteren Vorderecke des gesamten Lamellenteils eingefügt.
Bei einen Schrank mit Öffnung nach rechts ist die Klasse an der
rechten unteren Vorderecke einzufügen.
Parameter: 1. Punktliste (siehe GoHIRDoorL bzw. GoHIRDoorR)
2. Höhe der Lamellen
Bsp. Öffnung nach links:
[[0.0, 0.0], [0.25, 0.14], [0.5, 0.2], [0.75, 0.14], [1.0, 0.0]], 0.75 bzw.
Bsp. Öffnung nach rechts:
[[-1.0, 0.0], [-0.75, 0.14], [-0.5, 0.2], [-0.25, 0.14], [0.0, 0.0]], 0.75

Seite 24 von 43

| Beschreibung: | Oberklasse für Querrolladenschrank mit gebogener unprofilierter
Front und Öffnung nach rechts. Diesem Typ muß ein GoHIRDoor
und ein GoHIRHandle untergeordnet sein. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der rechten unteren Vorderecke der Front
der Tür einzufügen. |
| Parameter: | 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. initiale Anzahl von Lamellen
4. Punktliste (Anzahl der Punkte = max. Anzahl der Lamellen plus
zwei)
5. Höhe der Lamellen
Bsp.: 3, 0, 3, [[-1.0, 0.0], [-0.75, 0.14], [-0.5, 0.2], [-0.25, 0.14], [0, 0]],
0.75 |

| Beschreibung: | Klasse für die Lamellen. |
| --- | --- |
| Zu beachten: | Bei einen Schrank mit Öffnung nach links wird die Klasse an der
linken unteren Vorderecke des gesamten Lamellenteils eingefügt.
Bei einen Schrank mit Öffnung nach rechts ist die Klasse an der
rechten unteren Vorderecke einzufügen. |
| Parameter: | 1. Punktliste (siehe GoHIRDoorL bzw. GoHIRDoorR)
2. Höhe der Lamellen
Bsp. Öffnung nach links:
[[0.0, 0.0], [0.25, 0.14], [0.5, 0.2], [0.75, 0.14], [1.0, 0.0]], 0.75 bzw.
Bsp. Öffnung nach rechts:
[[-1.0, 0.0], [-0.75, 0.14], [-0.5, 0.2], [-0.25, 0.14], [0.0, 0.0]], 0.75 |

<!-- Page 25 -->

2.7.4 GoHIRHandle

Beschreibung: Klasse für das Griffstück.
Zu beachten: Bei einen Schrank mit Öffnung nach links wird die Klasse an der
linken unteren Vorderecke des gesamten Lamellenteils eingefügt.
Bei einen Schrank mit Öffnung nach rechts ist die Klasse an der
rechten unteren Vorderecke einzufügen.
Die für das Griffstück initial eventuell benötigte Drehung wird bei den
Geometrie festlegt. (Sie darf nicht in der Klasse hinterlegt werden.)
Parameter:

2.8 Vertikalrolladenschrank gebogen mit unprofilierter Front
Bei dieser Klasse ist eine Liste mit den y, z - Eckpunkten der einzelnen Lamellen und des
Griffstücks erforderlich. Diese Liste wird von unten nach oben angegeben.

(Für jedes Element wird der untere und der obere vordere Eckpunkt aufgeführt. Wobei der
obere Punkt eines Elementes gleichzeitig der untere Punkt des nachfolgenden ist und
demnach nur einmal angegeben wird.)

Angegeben werden die Höhen- und die Tiefenwerte; die Breitenwerte bleiben für diese Liste
unbeachtet.

Alle Punkte / Werte sind vom Einfügepunkt der entsprechenden Klasse ausgehend
anzugeben.

Öffnung nach unten Öffnung nach oben

GoVIRDoorU
GoVIRDoor
GoVIRHandle

GoVIRHandle
GoVIRDoorD
GoVIRDoor

Seite 25 von 43

| Beschreibung: | Klasse für das Griffstück. |
| --- | --- |
| Zu beachten: | Bei einen Schrank mit Öffnung nach links wird die Klasse an der
linken unteren Vorderecke des gesamten Lamellenteils eingefügt.
Bei einen Schrank mit Öffnung nach rechts ist die Klasse an der
rechten unteren Vorderecke einzufügen.
Die für das Griffstück initial eventuell benötigte Drehung wird bei den
Geometrie festlegt. (Sie darf nicht in der Klasse hinterlegt werden.) |
| Parameter: |  |

<!-- Page 26 -->

2.8.1 GoVIRDoorD

Beschreibung: Oberklasse für Vertikalrolladenschrank mit gebogener unprofilierter
Front und Öffnung nach unten. Diesem Typ muß ein GoVIRDoor und
ein GoVIRHandle untergeordnet sein.
Zu beachten: Die Klasse ist immer an der unteren linken Vorderecke der Front der
Tür einzufügen.
Parameter: 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. initiale Anzahl von Lamellen
4. Punktliste (Anzahl der Punkte = max. Anzahl der Lamellen plus
zwei)
5. Breite der Lamellen
Bsp.: 3, 0, 3, [[0.0, 0.0], [0.25, 0.14], [0.5, 0.2], [0.75, 0.14], [1.0, 0.0]],
0.75

2.8.2 GoVIRDoorU

Beschreibung:
Oberklasse für Vertikalrolladenschrank mit gebogener unprofilierter
Front und Öffnung nach oben. Diesem Typ muß ein GoVIRDoor und
ein GoVIRHandle untergeordnet sein.
Zu beachten: Die Klasse ist immer an der oberen linken Vorderecke der Front der
Tür einzufügen.
Parameter: 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. initiale Anzahl von Lamellen
4. Punktliste (Anzahl der Punkte = max. Anzahl der Lamellen plus
zwei)
5. Breite der Lamellen
Bsp.: 3, 0, 3, [[-1.0, 0.0], [-0.75, 0.14], [-0.5, 0.2], [-0.25, 0.14], [0, 0]],
0.75

Seite 26 von 43

| Beschreibung: | Oberklasse für Vertikalrolladenschrank mit gebogener unprofilierter
Front und Öffnung nach unten. Diesem Typ muß ein GoVIRDoor und
ein GoVIRHandle untergeordnet sein. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der unteren linken Vorderecke der Front der
Tür einzufügen. |
| Parameter: | 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. initiale Anzahl von Lamellen
4. Punktliste (Anzahl der Punkte = max. Anzahl der Lamellen plus
zwei)
5. Breite der Lamellen
Bsp.: 3, 0, 3, [[0.0, 0.0], [0.25, 0.14], [0.5, 0.2], [0.75, 0.14], [1.0, 0.0]],
0.75 |

| Beschreibung: | Oberklasse für Vertikalrolladenschrank mit gebogener unprofilierter
Front und Öffnung nach oben. Diesem Typ muß ein GoVIRDoor und
ein GoVIRHandle untergeordnet sein. |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der oberen linken Vorderecke der Front der
Tür einzufügen. |
| Parameter: | 1. maximale Anzahl von Lamellen (Tür ist geschlossen)
2. minimale Anzahl von Lamellen (Tür ist komplett auf)
3. initiale Anzahl von Lamellen
4. Punktliste (Anzahl der Punkte = max. Anzahl der Lamellen plus
zwei)
5. Breite der Lamellen
Bsp.: 3, 0, 3, [[-1.0, 0.0], [-0.75, 0.14], [-0.5, 0.2], [-0.25, 0.14], [0, 0]],
0.75 |

<!-- Page 27 -->

2.8.3 GoVIRDoor

Beschreibung: Klasse für die Lamellen.
Zu beachten: Bei einen Schrank mit Öffnung nach unten wird die Klasse an der
unteren linken Vorderecke des gesamten Lamellenteils eingefügt.
Bei einen Schrank mit Öffnung nach oben ist die Klasse an der
oberen linken Vorderecke einzufügen.
Parameter: 1. Punktliste (siehe GoVIRDoorD bzw. GoVIRDoorU)
2. Breite der Lamellen
Bsp. Öffnung nach unten:
[[0.0, 0.0], [0.25, 0.14], [0.5, 0.2], [0.75, 0.14], [1.0, 0.0]], 0.75 bzw.
Bsp. Öffnung nach oben:
[[-1.0, 0.0], [-0.75, 0.14], [-0.5, 0.2], [-0.25, 0.14], [0.0, 0.0]], 0.75

2.8.4 GoVIRHandle

Beschreibung: Klasse für das Griffstück.
Zu beachten: Bei einen Schrank mit Öffnung nach unten wird die Klasse an der
unteren linken Vorderecke des gesamten Lamellenteils eingefügt.
Bei einen Schrank mit Öffnung nach oben ist die Klasse an der
oberen rechten Vorderecke einzufügen.
Die für das Griffstück initial eventuell benötigte Drehung wird bei den
Geometrie festlegt. (Sie darf nicht in der Klasse hinterlegt werden.)
Parameter:

Seite 27 von 43

| Beschreibung: | Klasse für die Lamellen. |
| --- | --- |
| Zu beachten: | Bei einen Schrank mit Öffnung nach unten wird die Klasse an der
unteren linken Vorderecke des gesamten Lamellenteils eingefügt.
Bei einen Schrank mit Öffnung nach oben ist die Klasse an der
oberen linken Vorderecke einzufügen. |
| Parameter: | 1. Punktliste (siehe GoVIRDoorD bzw. GoVIRDoorU)
2. Breite der Lamellen
Bsp. Öffnung nach unten:
[[0.0, 0.0], [0.25, 0.14], [0.5, 0.2], [0.75, 0.14], [1.0, 0.0]], 0.75 bzw.
Bsp. Öffnung nach oben:
[[-1.0, 0.0], [-0.75, 0.14], [-0.5, 0.2], [-0.25, 0.14], [0.0, 0.0]], 0.75 |

| Beschreibung: | Klasse für das Griffstück. |
| --- | --- |
| Zu beachten: | Bei einen Schrank mit Öffnung nach unten wird die Klasse an der
unteren linken Vorderecke des gesamten Lamellenteils eingefügt.
Bei einen Schrank mit Öffnung nach oben ist die Klasse an der
oberen rechten Vorderecke einzufügen.
Die für das Griffstück initial eventuell benötigte Drehung wird bei den
Geometrie festlegt. (Sie darf nicht in der Klasse hinterlegt werden.) |
| Parameter: |  |

<!-- Page 28 -->

2.9 Verschieben im Raster x und z

2.9.1 GoXLRTRansZLRTrans

Beschreibung: Dieser GO-Typ erlaubt das Verschieben in der XZ-Ebene im Raster.
Parameter: 1. linke Grenze
2. rechte Grenze
3. X – Raster
4. hintere Grenze
5. vordere Grenze
6. Z – Raster

2.10 Verschieben im Raster x und y

2.10.1 GoXLRTransYLRTrans

Beschreibung: Dieser GO-Typ erlaubt das Verschieben in der XY-Ebene im Raster.
Parameter: 1. linke Grenze
2. rechte Grenze
3. X – Raster
4. untere Grenze
5. obere Grenze
6. Y – Raster

Seite 28 von 43

| Beschreibung: | Dieser GO-Typ erlaubt das Verschieben in der XZ-Ebene im Raster. |
| --- | --- |
| Parameter: | 1. linke Grenze
2. rechte Grenze
3. X – Raster
4. hintere Grenze
5. vordere Grenze
6. Z – Raster |

| Beschreibung: | Dieser GO-Typ erlaubt das Verschieben in der XY-Ebene im Raster. |
| --- | --- |
| Parameter: | 1. linke Grenze
2. rechte Grenze
3. X – Raster
4. untere Grenze
5. obere Grenze
6. Y – Raster |

<!-- Page 29 -->

2.11 Verschieben im Raster y und z

2.11.1 GoYLRTransZLRTrans

Beschreibung: Dieser GO-Typ erlaubt das Verschieben in der YZ-Ebene im Raster.
Parameter: 1. untere Grenze
2. obere Grenze
3. Y – Raster
4. hintere Grenze
5. vordere Grenze
6. Z – Raster

2.12 GoYLTransYRotS

Diese Klasse wird genutzt, wenn bei einem Stuhl (zusätzlich zur Höhenverstellung und
Rotation um die y-Achse) die Sitzfläche und die Rückenlehne nach hinten neigbar sein
sollen. Dabei wird die Rückenlehne n mal so stark rotiert wie der Sitz.

Bsp.: Wenn der Sitz sich um 10° neigt, soll sich die Rückenlehne zusätzlich dazu noch 15°
mehr neigen (insgesamt 25°). Dann ist n = 2.5.

Die Neigung von Sitzfläche und Rückenlehne erfolgt um die x-Achse. (Darauf ist bei den
Geometrien zu achten - die Lehne sollte nach hinten weisen.)

2.12.1 GoYLTransYRotS

Beschreibung:
Klasse für die eingeschränkte Verschiebung entlang der y-Achse und
uneingeschränkte Rotation um die y-Achse.
Diesem Typ muß ein GoSSeat und ein GoSBackrest untergeordnet
sein. Für diese gilt: GoSBackrest neigt sich n mal so viel um die x-
Achse wie GoSSeat.
Zu beachten: Die Klasse wird allen Geometrien übergeordnet, die höhenverstellbar
und um die y-Achse rotierbar seinen sollen.
Parameter: 1. die untere Grenze
2. die obere Grenze
3. die Starthöhe
Bsp.: 0.35, 0.5, 0.45

Seite 29 von 43

| Beschreibung: | Dieser GO-Typ erlaubt das Verschieben in der YZ-Ebene im Raster. |
| --- | --- |
| Parameter: | 1. untere Grenze
2. obere Grenze
3. Y – Raster
4. hintere Grenze
5. vordere Grenze
6. Z – Raster |

| Beschreibung: | Klasse für die eingeschränkte Verschiebung entlang der y-Achse und
uneingeschränkte Rotation um die y-Achse.
Diesem Typ muß ein GoSSeat und ein GoSBackrest untergeordnet
sein. Für diese gilt: GoSBackrest neigt sich n mal so viel um die x-
Achse wie GoSSeat. |
| --- | --- |
| Zu beachten: | Die Klasse wird allen Geometrien übergeordnet, die höhenverstellbar
und um die y-Achse rotierbar seinen sollen. |
| Parameter: | 1. die untere Grenze
2. die obere Grenze
3. die Starthöhe
Bsp.: 0.35, 0.5, 0.45 |

<!-- Page 30 -->

2.12.2 GoSSeat

Beschreibung: GoSSeat ist die Klasse für die Sitzläche des Stuhls. (Und für alle
Geometrien, die sich wie die Sitzfläche neigen sollen z.B.
Armlehnen.)
Zu beachten: Die Neigung erfolgt um eine x-Achse, die durch den Einfügepunkt der
Klasse verläuft.
Parameter:

2.12.3 GoSBackrest

Beschreibung: GoSBackrest ist die Klasse für die Rückenlehne. (Und für alle
Geometrien, die sich wie die Lehne n mal so viel wie der Sitz neigen
sollen.)
Zu beachten: Die Klasse muß an der Rotationskante der Lehne eingefügt werden.
Wenn die Lehne sich in negative z-Richtung neigen soll (nach
hinten), sind die Winkel positiv anzugeben.
Parameter: 1. kleinster Winkel der Lehne (sie ist komplett aufgerichtet)
2. größter Winkel der Lehne (sie ist ganz nach hinten geneigt)
3. initialer Winkel der Lehne
4. n
Bsp.: 5, 45, 20, 2.5

2.13 GoYLTransYRotS2

Diese Klasse wird genutzt, wenn bei einem Stuhl (zusätzlich zur Höhenverstellung und
Rotation um die y-Achse) die Sitzfläche und die Rückenlehne nach hinten neigbar sein
sollen. Dabei wird die Rückenlehne n mal so stark rotiert wie der Sitz.

Bsp.: Wenn der Sitz sich um 10° neigt, soll sich die Rückenlehne zusätzlich dazu noch 15°
mehr neigen (insgesamt 25°). Dann ist n = 2.5.

Die Neigung von Sitzfläche und Rückenlehne erfolgt um die x-Achse. (Darauf ist bei den
Geometrien zu achten - die Lehne sollte nach hinten weisen.)

Dieser Typ wird verwendet, wenn die Lehne unabhängig vom Sitz am Stuhl befestigt ist.

Seite 30 von 43

| Beschreibung: | GoSSeat ist die Klasse für die Sitzläche des Stuhls. (Und für alle
Geometrien, die sich wie die Sitzfläche neigen sollen z.B.
Armlehnen.) |
| --- | --- |
| Zu beachten: | Die Neigung erfolgt um eine x-Achse, die durch den Einfügepunkt der
Klasse verläuft. |
| Parameter: |  |

| Beschreibung: | GoSBackrest ist die Klasse für die Rückenlehne. (Und für alle
Geometrien, die sich wie die Lehne n mal so viel wie der Sitz neigen
sollen.) |
| --- | --- |
| Zu beachten: | Die Klasse muß an der Rotationskante der Lehne eingefügt werden.
Wenn die Lehne sich in negative z-Richtung neigen soll (nach
hinten), sind die Winkel positiv anzugeben. |
| Parameter: | 1. kleinster Winkel der Lehne (sie ist komplett aufgerichtet)
2. größter Winkel der Lehne (sie ist ganz nach hinten geneigt)
3. initialer Winkel der Lehne
4. n
Bsp.: 5, 45, 20, 2.5 |

<!-- Page 31 -->

2.13.1 GoYLTransYRotS2

Beschreibung: Klasse für die eingeschränkte Verschiebung entlang der y-Achse und
uneingeschränkte Rotation um die y-Achse.
Diesem Typ muß ein GoSSeat2 und ein GoSBackrest2 untergeordnet
sein. Für diese gilt: GoSBackrest2 neigt sich n mal so viel um die x-
Achse wie GoSSeat2.
Zu beachten: Die Klasse wird allen Geometrien übergeordnet, die höhenverstellbar
und um die y-Achse rotierbar seinen sollen.
Parameter: 1. Die untere Grenze
2. Die obere Grenze
3. Die Starthöhe
Bsp.: 0.35, 0.5, 0.45

2.13.2 GoSSeat2

Beschreibung: GoSSeat2 ist die Klasse für die Sitzfläche des Stuhls. (Und für alle
Geometrien, die sich wie die Sitzfläche neigen sollen z.B.
Armlehnen.)
Zu beachten: Die Neigung erfolgt um eine x-Achse, die durch den Einfügepunkt der
Klasse verläuft.
Parameter:

2.13.3 GoSBackrest2

Beschreibung:
GoSBackrest2 ist die Klasse für die Rückenlehne. (Und für alle
Geometrien, die sich wie die Lehne n mal so viel wie der Sitz neigen
sollen.)
Zu beachten: Die Klasse muß an der Rotationskante der Lehne eingefügt werden.
Wenn die Lehne sich in negative z-Richtung neigen soll (nach
hinten), sind die Winkel positiv anzugeben.
Parameter: 1. kleinster Winkel der Lehne (sie ist komplett aufgerichtet)
2. größter Winkel der Lehne (sie ist ganz nach hinten geneigt)
3. initialer Winkel der Lehne
4. n
Bsp.: 5, 45, 20, 2.5

Seite 31 von 43

| Beschreibung: | Klasse für die eingeschränkte Verschiebung entlang der y-Achse und
uneingeschränkte Rotation um die y-Achse.
Diesem Typ muß ein GoSSeat2 und ein GoSBackrest2 untergeordnet
sein. Für diese gilt: GoSBackrest2 neigt sich n mal so viel um die x-
Achse wie GoSSeat2. |
| --- | --- |
| Zu beachten: | Die Klasse wird allen Geometrien übergeordnet, die höhenverstellbar
und um die y-Achse rotierbar seinen sollen. |
| Parameter: | 1. Die untere Grenze
2. Die obere Grenze
3. Die Starthöhe
Bsp.: 0.35, 0.5, 0.45 |

| Beschreibung: | GoSSeat2 ist die Klasse für die Sitzfläche des Stuhls. (Und für alle
Geometrien, die sich wie die Sitzfläche neigen sollen z.B.
Armlehnen.) |
| --- | --- |
| Zu beachten: | Die Neigung erfolgt um eine x-Achse, die durch den Einfügepunkt der
Klasse verläuft. |
| Parameter: |  |

| Beschreibung: | GoSBackrest2 ist die Klasse für die Rückenlehne. (Und für alle
Geometrien, die sich wie die Lehne n mal so viel wie der Sitz neigen
sollen.) |
| --- | --- |
| Zu beachten: | Die Klasse muß an der Rotationskante der Lehne eingefügt werden.
Wenn die Lehne sich in negative z-Richtung neigen soll (nach
hinten), sind die Winkel positiv anzugeben. |
| Parameter: | 1. kleinster Winkel der Lehne (sie ist komplett aufgerichtet)
2. größter Winkel der Lehne (sie ist ganz nach hinten geneigt)
3. initialer Winkel der Lehne
4. n
Bsp.: 5, 45, 20, 2.5 |

<!-- Page 32 -->

2.14 Höhenverstellung für Tisch mit A-Fuß

Dieser GO-Typ wird benutzt, um bei Tischen mit A-Fußgestell eine Höhenverstellung
umzusetzen.

2.14.1 GoYLTransADeskTop

Beschreibung: Oberklasse für diesen GO-Typ.
Zu beachten: Dieser Klasse werden alle Teile, die höhenverstellbar sein sollen,
zugeordnet. Ebenso alle notwendigen Fußklassen
(GoYLTransAFootB und GoYLTransAFootF).
Die Grenzen der Höhenverstellung werden von der Position dieser
Klasse ausgehend angegeben.
Parameter: 1. die untere Grenze
2. die obere Grenze
Bsp.: -0.05, 0.15

2.14.2 GoYLTransAFootB

Beschreibung: Klasse für den Teil eines hinteren Fußes, der von der
Höhenverschiebung ausgeschlossen ist (der auf dem Boden stehen
bleibt).
Zu beachten: Für jeden Fuß wird eine extra GO-Eintrag benötigt.
Mit dem Parameter wird angegeben, um wieviel Grad das Tischbein
von der Senkrechten abweicht.
Parameter: 1. Winkel (Wert zwischen 0 und 90)
Bsp.: 15

Seite 32 von 43

| Beschreibung: | Oberklasse für diesen GO-Typ. |
| --- | --- |
| Zu beachten: | Dieser Klasse werden alle Teile, die höhenverstellbar sein sollen,
zugeordnet. Ebenso alle notwendigen Fußklassen
(GoYLTransAFootB und GoYLTransAFootF).
Die Grenzen der Höhenverstellung werden von der Position dieser
Klasse ausgehend angegeben. |
| Parameter: | 1. die untere Grenze
2. die obere Grenze
Bsp.: -0.05, 0.15 |

| Beschreibung: | Klasse für den Teil eines hinteren Fußes, der von der
Höhenverschiebung ausgeschlossen ist (der auf dem Boden stehen
bleibt). |
| --- | --- |
| Zu beachten: | Für jeden Fuß wird eine extra GO-Eintrag benötigt.
Mit dem Parameter wird angegeben, um wieviel Grad das Tischbein
von der Senkrechten abweicht. |
| Parameter: | 1. Winkel (Wert zwischen 0 und 90)
Bsp.: 15 |

<!-- Page 33 -->

2.14.3 GoYLTransAFootF

Beschreibung: Klasse für den Teil eines vorderen Fußes, der von der
Höhenverschiebung ausgeschlossen ist (der auf dem Boden stehen
bleibt).
Zu beachten: Für jeden Fuß wird eine extra GO-Eintrag benötigt.
Mit dem Parameter wird angegeben, um wieviel Grad das Tischbein
von der Senkrechten abweicht.
Parameter:
1. Winkel (Wert zwischen 0 und 90)
Bsp.: 15

2.15 Synchronschiebebewegung entlang der X-Achse

Mit diesem GO-Typen kann eine Synchron-Schiebebewegung entlang der X-Achse
umgesetzt werden.
Eine Teilgeometrie wird durch den Anwender bewegt. Dabei wird gleichzeitig eine zweite
Teilgeometrie in die entgegengesetzte Richtung verschoben.

2.15.1 GoXLTransSynchr

Beschreibung: Klasse für die Synchronschiebebewegung entlang der x-Achse.
Diesem Typ muß ein GoXLTransSynchr_A und ein
GoXLTransSynchr_B untergeordnet sein.
Wobei GoXLTransSynchr_A der durch den Anwender bewegte Teil
ist und GoXLTransSynchr_B derjenige, der automatisch
entgegengesetzt verschoben wird.
Zu beachten:
Parameter: 1. Strecke für Bewegung nach links
2. Strecke für Bewegung nach rechts
3. Faktor für die Bewegung von Teil B (ist 1, wenn Teil B genauso
weit bewegt werden soll wie Teil A)
Beispiel: Parameter: -0.1, 0.4, 0.5
Damit kann Teil A 10 cm nach links und 40 cm nach rechts bewegt
werden – ausgehend von seiner initialen Position. Teil B wird dabei
jeweils die halbe Strecke in die entgegengesetzte Richtung
verschoben.

Seite 33 von 43

| Beschreibung: | Klasse für den Teil eines vorderen Fußes, der von der
Höhenverschiebung ausgeschlossen ist (der auf dem Boden stehen
bleibt). |
| --- | --- |
| Zu beachten: | Für jeden Fuß wird eine extra GO-Eintrag benötigt.
Mit dem Parameter wird angegeben, um wieviel Grad das Tischbein
von der Senkrechten abweicht. |
| Parameter: | 1. Winkel (Wert zwischen 0 und 90)
Bsp.: 15 |

| Beschreibung: | Klasse für die Synchronschiebebewegung entlang der x-Achse.
Diesem Typ muß ein GoXLTransSynchr_A und ein
GoXLTransSynchr_B untergeordnet sein.
Wobei GoXLTransSynchr_A der durch den Anwender bewegte Teil
ist und GoXLTransSynchr_B derjenige, der automatisch
entgegengesetzt verschoben wird. |
| --- | --- |
| Zu beachten: |  |
| Parameter: | 1. Strecke für Bewegung nach links
2. Strecke für Bewegung nach rechts
3. Faktor für die Bewegung von Teil B (ist 1, wenn Teil B genauso
weit bewegt werden soll wie Teil A) |
| Beispiel: | Parameter: -0.1, 0.4, 0.5
Damit kann Teil A 10 cm nach links und 40 cm nach rechts bewegt
werden – ausgehend von seiner initialen Position. Teil B wird dabei
jeweils die halbe Strecke in die entgegengesetzte Richtung
verschoben. |

<!-- Page 34 -->

2.15.2 GoXLTransSynchr_A

Beschreibung: Klasse für Teil A – den Teil, der durch den Anwender bewegt wird.
Wird der Klasse GoXLTransSynchr untergeordnet.
Zu beachten:
Parameter:

2.15.3 GoXLTransSynchr_B

Beschreibung: Klasse für Teil B – den Teil, der automatisch in die entgegengesetzte
Richtung verschoben wird.
Wird der Klasse GoXLTransSynchr untergeordnet.
Zu beachten:
Parameter:

Seite 34 von 43

| Beschreibung: | Klasse für Teil A – den Teil, der durch den Anwender bewegt wird.
Wird der Klasse GoXLTransSynchr untergeordnet. |
| --- | --- |
| Zu beachten: |  |
| Parameter: |  |

| Beschreibung: | Klasse für Teil B – den Teil, der automatisch in die entgegengesetzte
Richtung verschoben wird.
Wird der Klasse GoXLTransSynchr untergeordnet. |
| --- | --- |
| Zu beachten: |  |
| Parameter: |  |

<!-- Page 35 -->

2.16 Synchronschiebebewegung entlang der Y-Achse

Mit diesem GO-Typen kann eine Synchron-Schiebebewegung entlang der Y-Achse
umgesetzt werden.
Eine Teilgeometrie wird durch den Anwender bewegt. Dabei wird gleichzeitig eine zweite
Teilgeometrie in die entgegengesetzte Richtung verschoben.

2.16.1 GoYLTransSynchr

Beschreibung: Klasse für die Synchronschiebebewegung entlang der y-Achse.
Diesem Typ muß ein GoYLTransSynchr_A und ein
GoYLTransSynchr_B untergeordnet sein.
Wobei GoYLTransSynchr_A der durch den Anwender bewegte Teil
ist und GoYLTransSynchr_B derjenige, der automatisch
entgegengesetzt verschoben wird.
Zu beachten:
Parameter: 1. Strecke für Bewegung nach unten
2. Strecke für Bewegung nach oben
3. Faktor für die Bewegung von Teil B (ist 1, wenn Teil B genauso
weit bewegt werden soll wie Teil A)
Beispiel: Parameter: -0.1, 0.4, 2.0
Damit kann Teil A 10 cm nach unten und 40 cm nach oben bewegt
werden – ausgehend von seiner initialen Position. Teil B wird dabei
jeweils die doppelte Strecke in die entgegengesetzte Richtung
verschoben.

2.16.2 GoYLTransSynchr_A

Beschreibung: Klasse für Teil A – den Teil, der durch den Anwender bewegt wird.
Wird der Klasse GoYLTransSynchr untergeordnet.
Zu beachten:
Parameter:

Seite 35 von 43

| Beschreibung: | Klasse für die Synchronschiebebewegung entlang der y-Achse.
Diesem Typ muß ein GoYLTransSynchr_A und ein
GoYLTransSynchr_B untergeordnet sein.
Wobei GoYLTransSynchr_A der durch den Anwender bewegte Teil
ist und GoYLTransSynchr_B derjenige, der automatisch
entgegengesetzt verschoben wird. |
| --- | --- |
| Zu beachten: |  |
| Parameter: | 1. Strecke für Bewegung nach unten
2. Strecke für Bewegung nach oben
3. Faktor für die Bewegung von Teil B (ist 1, wenn Teil B genauso
weit bewegt werden soll wie Teil A) |
| Beispiel: | Parameter: -0.1, 0.4, 2.0
Damit kann Teil A 10 cm nach unten und 40 cm nach oben bewegt
werden – ausgehend von seiner initialen Position. Teil B wird dabei
jeweils die doppelte Strecke in die entgegengesetzte Richtung
verschoben. |

| Beschreibung: | Klasse für Teil A – den Teil, der durch den Anwender bewegt wird.
Wird der Klasse GoYLTransSynchr untergeordnet. |
| --- | --- |
| Zu beachten: |  |
| Parameter: |  |

<!-- Page 36 -->

2.16.3 GoYLTransSynchr_B

Beschreibung: Klasse für Teil B – den Teil, der automatisch in die entgegengesetzte
Richtung verschoben wird.
Wird der Klasse GoYLTransSynchr untergeordnet.
Zu beachten:
Parameter:

2.17 Synchronschiebebewegung entlang der Z-Achse

Mit diesem GO-Typen kann eine Synchron-Schiebebewegung entlang der Z-Achse
umgesetzt werden.
Eine Teilgeometrie wird durch den Anwender bewegt. Dabei wird gleichzeitig eine zweite
Teilgeometrie in die entgegengesetzte Richtung verschoben.

2.17.1 GoZLTransSynchr

Beschreibung: Klasse für die Synchronschiebebewegung entlang der z-Achse.
Diesem Typ muß ein GoZLTransSynchr_A und ein
GoZLTransSynchr_B untergeordnet sein.
Wobei GoZLTransSynchr_A der durch den Anwender bewegte Teil
ist und GoZLTransSynchr_B derjenige, der automatisch
entgegengesetzt verschoben wird.
Zu beachten:
Parameter: 1. Strecke für Bewegung nach hinten
2. Strecke für Bewegung nach vorne
3. Faktor für die Bewegung von Teil B (ist 1, wenn Teil B genauso
weit bewegt werden soll wie Teil A)
Beispiel: Parameter: -0.15, 0.5, 1.0
Damit kann Teil A 15 cm nach hinten und 50 cm nach vorne bewegt
werden – ausgehend von seiner initialen Position. Teil B wird dabei
jeweils die gleiche Strecke in die entgegengesetzte Richtung
verschoben.

Seite 36 von 43

| Beschreibung: | Klasse für Teil B – den Teil, der automatisch in die entgegengesetzte
Richtung verschoben wird.
Wird der Klasse GoYLTransSynchr untergeordnet. |
| --- | --- |
| Zu beachten: |  |
| Parameter: |  |

| Beschreibung: | Klasse für die Synchronschiebebewegung entlang der z-Achse.
Diesem Typ muß ein GoZLTransSynchr_A und ein
GoZLTransSynchr_B untergeordnet sein.
Wobei GoZLTransSynchr_A der durch den Anwender bewegte Teil
ist und GoZLTransSynchr_B derjenige, der automatisch
entgegengesetzt verschoben wird. |
| --- | --- |
| Zu beachten: |  |
| Parameter: | 1. Strecke für Bewegung nach hinten
2. Strecke für Bewegung nach vorne
3. Faktor für die Bewegung von Teil B (ist 1, wenn Teil B genauso
weit bewegt werden soll wie Teil A) |
| Beispiel: | Parameter: -0.15, 0.5, 1.0
Damit kann Teil A 15 cm nach hinten und 50 cm nach vorne bewegt
werden – ausgehend von seiner initialen Position. Teil B wird dabei
jeweils die gleiche Strecke in die entgegengesetzte Richtung
verschoben. |

<!-- Page 37 -->

2.17.2 GoZLTransSynchr_A

Beschreibung: Klasse für Teil A – den Teil, der durch den Anwender bewegt wird.
Wird der Klasse GoZLTransSynchr untergeordnet.
Zu beachten:
Parameter:

2.17.3 GoZLTransSynchr_B

Beschreibung: Klasse für Teil B – den Teil, der automatisch in die entgegengesetzte
Richtung verschoben wird.
Wird der Klasse GoZLTransSynchr untergeordnet.
Zu beachten:
Parameter:

Seite 37 von 43

| Beschreibung: | Klasse für Teil A – den Teil, der durch den Anwender bewegt wird.
Wird der Klasse GoZLTransSynchr untergeordnet. |
| --- | --- |
| Zu beachten: |  |
| Parameter: |  |

| Beschreibung: | Klasse für Teil B – den Teil, der automatisch in die entgegengesetzte
Richtung verschoben wird.
Wird der Klasse GoZLTransSynchr untergeordnet. |
| --- | --- |
| Zu beachten: |  |
| Parameter: |  |

<!-- Page 38 -->

2.18 Einschub-Klappe

Mit diesem GO-Typen wird eine Klappe umgesetzt, die in den Schrank eingeschoben
werden kann, sobald sie komplett aufgeklappt ist.

2.18.1 GoFlapXLRot

Beschreibung: Klasse für eine Einschubklappe
Zu beachten: Die Klasse ist immer an der Vorderkante der Front zu positionieren,
und zwar an der Kante, um die die Klappe gedreht werden soll (oben
oder unten).
Gesteuert wird sowohl die Rotation als auch das Einschieben mit der
rechten Maustaste.
Parameter: 1. kleinerer Winkel
2. größerer Winkel
3. Startwinkel
4. Strecke, die die Klappe eingeschoben werden soll
Bsp.: 0, 90, 0, 0.5
Wenn die Rotationskante oben ist (d.h. wenn die Klappe nach
oben geklappt wird) und die Klappe initial geschlossen
dargestellt ist.
Bsp.: -90, 0, 0, 0.5
Wenn die Rotationskante unten ist (d.h. wenn die Klappe nach
unten geklappt wird) und die Klappe initial geschlossen
dargestellt ist.

Seite 38 von 43

| Beschreibung: | Klasse für eine Einschubklappe |
| --- | --- |
| Zu beachten: | Die Klasse ist immer an der Vorderkante der Front zu positionieren,
und zwar an der Kante, um die die Klappe gedreht werden soll (oben
oder unten).
Gesteuert wird sowohl die Rotation als auch das Einschieben mit der
rechten Maustaste. |
| Parameter: | 1. kleinerer Winkel
2. größerer Winkel
3. Startwinkel
4. Strecke, die die Klappe eingeschoben werden soll
Bsp.: 0, 90, 0, 0.5
Wenn die Rotationskante oben ist (d.h. wenn die Klappe nach
oben geklappt wird) und die Klappe initial geschlossen
dargestellt ist.
Bsp.: -90, 0, 0, 0.5
Wenn die Rotationskante unten ist (d.h. wenn die Klappe nach
unten geklappt wird) und die Klappe initial geschlossen
dargestellt ist. |

<!-- Page 39 -->

2.19
Y-Verschiebung mit gleichzeitiger abhängiger Z-Verschiebung

GO-Typ für eine Verschiebung entlang der Y-Achse und einer gleichzeitigen abhängigen
Verschiebung entlang der Z-Achse.
Damit kann eine nach vorne oder nach hinten abgeschrägte Höhenverschiebung umgesetzt
werden.

2.19.1 GoYLTransZDepTrans

Kurzbeschreibung: Basisklasse für eingeschränkte Verschiebung entlang der y-Achse.
Anhängig davon erfolgt gleichzeitig eine Verschiebung entlang der z-
Achse.
Parameter: 1. die untere Grenze
2. die obere Grenze
3. die Starthöhe
4. Winkel a (Abweichung der Verschiebungsachse zur Senkrechten)
Neigung der Verschiebungsachse nach hinten – Winkel ist negativ
Neigung der Verschiebungsachse nach vorne – Winkel ist positiv
Langbeschreibung: Diese Klasse ermöglicht die eingeschränkte Verschiebung entlang der
y-Achse; zugleich erfolgt eine entsprechende Verschiebung entlang
der z-Achse. Jegliche Rotation ist ausgeschlossen.
Beispiel: Kopfstützen

z
Seitenansicht

a
x

-y

Seite 39 von 43

<!-- Page 40 -->

# 3. Sonstige Typen

3.1 Zubehörplazierungsparameter (GoAccParameters)

Kurzbeschreibung: Hilfsklasse zur Integration der automatischen Zubehörplatzierung in
Objekthierarchien im Kontext von Metatypanwendungen.
Parameter: AccID [String]
Width [String/Symbol/Float]
Height [String/Symbol/Float]
Depth [String/Symbol/Float]
Langbeschreibung: Durch Verwendung dieses Typs ist es möglich, in (typischerweise
ODB-basierte) Objektstrukturen Metainformation zu verlinken, welche
dann die automatische Zubehörplatzierung auslöst und para-
metrisiert. Zu diesem Zweck werden entsprechende Knoten des Typs
GoAccParameters platziert. Diese können existierende Knoten
ersetzen oder als zusätzliche Kinder eingefügt werden, bsp.sweise
wenn der existierende Knoten ebenfalls bereits ein GO-Typ ist.
Der Typ GoAccParameters ist speziell zur Verwendung im
Zusammenhang mit Metatypen konzipiert wurden.
Im Rahmen der Parameter werden nur die geometrischen
Grundinformationen sowie ein Parameterschlüssel (AccID)
bereitgestellt. Durch Auflösung des Parameterschlüssels erfolgt
letztendlich der Zugriff auf die Zubehörparameter.
Der Parameter AccID verweist auf die Tabelle go_metainfo zugehörig
zu dem Metatyp welcher per Aufwärtstraversierung ausgehend von
dem GO I-Objekt ermittelt wird.
Im Rahmen der o.g. Tabelle kann die für die Metatypen übliche
Variantenparametrik verwendet werden. Innerhalb der para-
metrischen Werte und Bedingungen können die Variablen W, H und
D verwendet werden, welche für Breite, Höhe und Tiefe stehen.
Diese Werte werden dem Typ GoAccParameters als Erzeu-
gungsparameter mitgegeben. Dabei ist folgendes zu beachten:
 Ist der Parameter ein String und beginnt er mit ‚MT_’, wie z.B.
‚MT_GWidth’ dann wird der Teil nach dem Unterstrich als MT -

Seite 40 von 43

| Kurzbeschreibung: | Hilfsklasse zur Integration der automatischen Zubehörplatzierung in
Objekthierarchien im Kontext von Metatypanwendungen. |
| --- | --- |
| Parameter: | AccID [String]
Width [String/Symbol/Float]
Height [String/Symbol/Float]
Depth [String/Symbol/Float] |
| Langbeschreibung: | Durch Verwendung dieses Typs ist es möglich, in (typischerweise
ODB-basierte) Objektstrukturen Metainformation zu verlinken, welche
dann die automatische Zubehörplatzierung auslöst und para-
metrisiert. Zu diesem Zweck werden entsprechende Knoten des Typs
GoAccParameters platziert. Diese können existierende Knoten
ersetzen oder als zusätzliche Kinder eingefügt werden, bsp.sweise
wenn der existierende Knoten ebenfalls bereits ein GO-Typ ist.
Der Typ GoAccParameters ist speziell zur Verwendung im
Zusammenhang mit Metatypen konzipiert wurden.
Im Rahmen der Parameter werden nur die geometrischen
Grundinformationen sowie ein Parameterschlüssel (AccID)
bereitgestellt. Durch Auflösung des Parameterschlüssels erfolgt
letztendlich der Zugriff auf die Zubehörparameter.
Der Parameter AccID verweist auf die Tabelle go_metainfo zugehörig
zu dem Metatyp welcher per Aufwärtstraversierung ausgehend von
dem GO I-Objekt ermittelt wird.
Im Rahmen der o.g. Tabelle kann die für die Metatypen übliche
Variantenparametrik verwendet werden. Innerhalb der para-
metrischen Werte und Bedingungen können die Variablen W, H und
D verwendet werden, welche für Breite, Höhe und Tiefe stehen.
Diese Werte werden dem Typ GoAccParameters als Erzeu-
gungsparameter mitgegeben. Dabei ist folgendes zu beachten:
 Ist der Parameter ein String und beginnt er mit ‚MT_’, wie z.B.
‚MT_GWidth’ dann wird der Teil nach dem Unterstrich als MT- |

<!-- Page 41 -->

Property (hier: GWidth) interpretiert. Per Aufwärts-
traversierung wird der zugehörige Metatyp ermittelt und der
entsprechende Merkmalswert ermittelt.
 Ist der Parameter ein Symbol und hat er den Wert @AUTO,
dann wird die zugehörige Dimension anhand der Bounding-
Box des aktuellen Objekts ermittelt. Sofern diese Ermittlung
einen ungültigen Wert liefert (leere Bounding-Box) erfolgt
ebenfalls eine Aufwärtstraversierung bis ein gültiger Wert
ermittelt wurde (oder ein Abbruch).
 Konnte kein Wert ermittelt werden, wird 1.0 angenommen.
 Das Format des Wertes sowie die Interpretation desselben ist
nicht festgelegt. Gültige Repräsentationen einer Breite von 0.8
Meter könnten daher sein: @W800, „800“, 0.8 und 800. Es
obliegt somit der Verantwortung der Datenanlage für eine
diesbezügliche Kompatibilität der Einträge in der odb3d.csv
(Erzeugungsparameter der GoAccParameters-Objekte) und
go_metainfo.csv (Interpretation derselben und Bereitstellung
der Parameter für die Zubehörplatzierung) zu sorgen.
Beispiel:
-

3.2 Skalierungsknoten (GoScaling)

Kurzbeschreibung: Hilfsklasse zur Skalierung von geometrischen Objekten
Parameter: X-Scaling [Float]
Y- Scaling [Float]
Z- Scaling [Float]
Langbeschreibung: Durch Verwendung dieser Hilfsklasse ist es möglich, Objekte wie z.B.
ODB-Teilbäume zu skalieren. Dies kann bei Objekten sinnvoll sein,
die von sich aus keine komplette Skalierung über ihre
Konstruktionsparameter unterstützen.
Die Skalierung darf nur für rein geometrische Unterobjekte
angewendet werden!
Die drei Parameter steuern die Skalierung in der jeweiligen
Dimension. Sofern ein nichtnumerischer Wert bzw. ein Wert kleiner
oder gleich 0.0 angegeben wird, wird diese Angabe ignoriert und 1.0
verwendet.

Seite 41 von 43

|  | Property (hier: GWidth) interpretiert. Per Aufwärts-
traversierung wird der zugehörige Metatyp ermittelt und der
entsprechende Merkmalswert ermittelt.
 Ist der Parameter ein Symbol und hat er den Wert @AUTO,
dann wird die zugehörige Dimension anhand der Bounding-
Box des aktuellen Objekts ermittelt. Sofern diese Ermittlung
einen ungültigen Wert liefert (leere Bounding-Box) erfolgt
ebenfalls eine Aufwärtstraversierung bis ein gültiger Wert
ermittelt wurde (oder ein Abbruch).
 Konnte kein Wert ermittelt werden, wird 1.0 angenommen.
 Das Format des Wertes sowie die Interpretation desselben ist
nicht festgelegt. Gültige Repräsentationen einer Breite von 0.8
Meter könnten daher sein: @W800, „800“, 0.8 und 800. Es
obliegt somit der Verantwortung der Datenanlage für eine
diesbezügliche Kompatibilität der Einträge in der odb3d.csv
(Erzeugungsparameter der GoAccParameters-Objekte) und
go_metainfo.csv (Interpretation derselben und Bereitstellung
der Parameter für die Zubehörplatzierung) zu sorgen. |
| --- | --- |
| Beispiel: | - |

| Kurzbeschreibung: | Hilfsklasse zur Skalierung von geometrischen Objekten |
| --- | --- |
| Parameter: | X-Scaling [Float]
Y- Scaling [Float]
Z- Scaling [Float] |
| Langbeschreibung: | Durch Verwendung dieser Hilfsklasse ist es möglich, Objekte wie z.B.
ODB-Teilbäume zu skalieren. Dies kann bei Objekten sinnvoll sein,
die von sich aus keine komplette Skalierung über ihre
Konstruktionsparameter unterstützen.
Die Skalierung darf nur für rein geometrische Unterobjekte
angewendet werden!
Die drei Parameter steuern die Skalierung in der jeweiligen
Dimension. Sofern ein nichtnumerischer Wert bzw. ein Wert kleiner
oder gleich 0.0 angegeben wird, wird diese Angabe ignoriert und 1.0
verwendet. |

<!-- Page 42 -->

Für den Skalierungsknoten ist die lokale Translation möglich. Lokale
Rotationen dürfen dagegen nicht verwendet werden.
Für das Kind bzw. die Kinder von Skalierungsknoten sind weder
Translation noch Rotation erlaubt.
Beispiel: -

Seite 42 von 43

|  | Für den Skalierungsknoten ist die lokale Translation möglich. Lokale
Rotationen dürfen dagegen nicht verwendet werden.
Für das Kind bzw. die Kinder von Skalierungsknoten sind weder
Translation noch Rotation erlaubt. |
| --- | --- |
| Beispiel: | - |

<!-- Page 43 -->

# Historie

Version 1.12.0

 Folgende Typen wurden entfernt:
o GoTable
o GoChainingElement
o
GoCupboard
o
GoChair
o GoAddOn
o
GoNotClassified
o
GoReplacement
o GoSalesOnly
o
GoProgInfo
Wo möglich, sollen/können stattdessen die entsprechenden, moderneren
Funktionalitäten der Metatyp-Datenanlage verwendet werden.

Version 1.11.0

 [NEU] – GoAccParameters
 [NEU] - GoScaling

Seite 43 von 43