# OLAYERS_1.3.1_en

> Auto-generated from OLAYERS_1.3.1_en.pdf for AI consumption.

---


<!-- Page 1 -->

1

## Title OLAYERS – OFML-compatible Layers

## Author/Editor Ekkehard Beier/Thomas Gerth, EasternGraphics

## On behalf of the working group Industrielle Aspekte der OFML-Normung

## (IAON).

## Reference Title: OLAYERS Specification

### Version: 1.3, 1 st revised version

## Date: 2015-08-18

## History See end of document

# Contents

1. Introduction .................................................................................................................................................... 2
2. Generic layer name ......................................................................................................................................... 2
3. General layers ................................................................................................................................................. 3
4. 3D-Layers ....................................................................................................................................................... 4
5. 2D-Layers ....................................................................................................................................................... 4
6. Snapping Layer .............................................................................................................................................. 5
7. General recommendations regarding data creation in AutoCAD ................................................................... 6
8. OFML data and application aspects ............................................................................................................... 6
8.1. OFML data aspects ................................................................................................................................ 6
8.2. Application aspects ................................................................................................................................ 6
Appendix ................................................................................................................................................................. 7
History................................................................................................................................................................. 7

## References

[DSR] – Description 'Data Structure and Registration', Version 3.3, EasternGraphics, 2014.
[OFML] – OFML – Standardized Data Description Format of the Office Furniture Industry, Version 2.0, 2 nd
revised edition, BSO e.V., 2002.
[TAGS] – OLAYERS TAGS – Tag Names for OFML-compatible Layers, Version 1.2, BSO e.V., 2013.

1
Copyright (C) 2006 – 2015 Working Group Industrielle Aspekte der OFML-Normung. All rights reserved.

Page 1 of 7

| Title | OLAYERS – OFML-compatible Layers1 |
| --- | --- |
| Author/Editor | Ekkehard Beier/Thomas Gerth, EasternGraphics
On behalf of the working group Industrielle Aspekte der OFML-Normung
(IAON). |
|  |  |
| Reference | Title: OLAYERS Specification
Version: 1.3, 1st revised version
Date: 2015-08-18 |
|  |  |
| History | See end of document |

<!-- Page 2 -->

# 1. Introduction

The enhanced opportunities of OFML compared to FOS – in particular in the field of manufacturer and product
series identification – necessarily require an adaptation of the FOS-oriented layer concepts. In the following a
layer structure will be described, which is OFML compatible.

This is a „living“ document, i.e., the specific layer modes and pre-defined identifiers will grow gradually. To
limit the number of releases of this document, proposals for uniform tags are listed in a separate document,
pertinent to this specification, see [TAGS].

# 2. Generic layer name

The generic layer name is defined as follows:

72_<MAN>_<SERIES>_<MOD>[_<TAG>]

Here, the following rules apply:

 72 – is a pre-determined qualification of AutoDesk for furniture. This qualification is followed by
an underline to distinguish from the FOS layer qualifications.
 <MAN> – is the OFML identifier of the manufacturer (DSR key manufacturer, see [DSR]). After
<MAN> an underline follows to separate from the series identifier (even if <MAN> already has an
underline at the end).
 <SERIES> – is the OFML identifier of the library/series (DSR key program). After <SERIES> an
underline follows to separate the mode qualification (even if <SERIES> already has an underline at
the end).
 <MOD> – describes a specific mode. (The possible modes are defined below). If the optional
qualification <TAG> follows, an underline has to be inserted after <MOD>.
In the following descriptions optional modes (layers) are marked with [*].
 <TAG> – this qualification is data specific and it depends on the respective <MOD> whether the
<TAG> qualification is available or not.

Example:
72_EGR_OFFICE2_D3_ANY – 'Manufacturer' EasternGraphics (EGR), Series ‘Office elements’
(OFFICE2), 3D geometry

Note: Layer names are defined as case-insensitive. In this document upper cases are applied; in practice upper
cases should be used, too. It is not allowed to use layer names that differ only in upper and lower case.

Page 2 of 7

<!-- Page 3 -->

# 3. General layers

These layers are independent of the specific 2D or 3D view. Some layers might be used only in a specific view
(primarily 2D). Nevertheless, by definition they are view-independent and, therefore, assigned to this section. If
a given layer unambiguously can be assigned to specific view type, this is named in brackets after the layer
mode.

The following modes are defined:

 *_DIMENSIONS_MM [2D]

On this layer the geometric dimension text of the object can be stored.
The general recommendation to structure the text is the following: width x depth x height, where the
dimensions are stated in millimeters and a point (.) is used as the thousands separator. However, different
descriptions are possible, e.g. other measures (radius) or a subset of the stated dimensions (width x depth).
The color of the layer is green (ACAD color index: 3).

 *_TEXT_<LANG> [2D][*]

On this layer an additional text (beyond the geometric dimension text) can be added to the object, e.g. the
quantity of folder heights of a cabinet.
There, <LANG> is the language according to ISO 639-1, e.g. DE for German, EN for English and so on.
The color of the layer is green (ACAD color index: 3).

 *_ARTICLE_INFO [2D][*]

On this layer article information can be stored. Usually this is the commercial article number, but additional
structural information are possible as well, e.g. main and sub positions.
The color of the layer is black/white (ACAD color index: 7).

 *_ ARTICLE_INFO_DPOS [2D][*]

On this layer the so-called Drawing Position can be stored. The drawing position is an application-
dependent number that represents a linkage between the CAD article and the bill of materials resp. basket.
The color of the layer is black/white (ACAD color index: 7).

 *_SPECIAL [2D][*]

In case of special articles further information can be stored on this layer.
The color of the layer is magenta (ACAD color index: 6).

 *_MISC [2D][*]

On this layer optional additional information can be stored, whose meaning and purpose is not described in
detail. For example, it can be used for accessories, for which there is no 3D geometry.
The color of the layer is blue (ACAD color index: 5).

Page 3 of 7

<!-- Page 4 -->

# 4. 3D-Layers

This section covers layer, which are relevant only in 3D views. The following modes are defined:

 *_D3_<TAG> [*]

On this layer specific 3D information can be stored.
The declaration of a <TAG> is mandatory. However, there are no standards regarding the values, as these
are dependent on the manufacturer data creation, especially on the material mapping. In the appendant
document [TAGS] in section “Geometry Tags” suggestions are made for the description of these <TAG>’s.
The color of the layer can be chosen individually.

 *_ D3FRONT_<TAG> [*]

On this layer specific 3D information for front elements can be stored. Objects that lie on that layer, can be
hidden or displayed by a corresponding filter of the planning system.
The declaration of a <TAG> is mandatory. However, there are no standards regarding the values, as these
are dependent on the manufacturer data creation, especially on the material mapping. In the appendant
document [TAGS] in section “Geometry Tags” suggestions are made for the description of these <TAG>’s.
The color of the layer can be chosen individually.

 *_ ACOUSTICS_<TAG> [*]

On this layer additional 3D geometries are stored which are used as acoustic representations of the objects.
These are taken into account in the context of acoustic evaluations of the planning.
The indication of a <TAG> is optional and results from the need for different material assignments. The
values of these <TAG>’s are not standardized.
The color of the layer can be chosen individually.

# 5. 2D-Layers

This section covers layer, which are relevant only in 2D views. The following modes are defined:

 *_D2_<TAG>

On this layer specific 2D information is stored.
The declaration of a <TAG> is mandatory. However, there are no standards regarding the values, as these
are dependent of the manufacturer data creation, especially on the material mapping. In the appendant
document [TAGS] in section “Geometry Tags” suggestions are made for the description of these <TAG>’s.
The color of the layer is yellow (ACAD color index: 2).

 *_D2DETAIL_<TAG> [*]

On this layer additional 2D information is stored, e.g. pedestals or cable ducts.
For <TAG> the rules stated above do apply.
The color of the layer is yellow (ACAD color index: 2).

Page 4 of 7

<!-- Page 5 -->

 *_D2SNAP [*]

On this layer 2D snapping points can be stored. These will be preferred by the snapping mechanism of the
OFML planning system over snapping points, which are derived from the product geometry.
This refers to objects which can be snapped to other objects 2 , as well as objects to which can be snapped.
The color of the layer is red (ACAD color index: 1).

# 6. Snapping Layer

These layers can be used in an OFML planning system in order to realize a simple planning logic between
elements on sibling level based on the snapping mechanism 3 .

 *_ ATTACH_<TAG> [*]
On this layer the target objects are stored, i.e., the objects to which other objects can be snapped.
Currently, the following object types are allowed: points, lines and planes.
The color of the layer can be chosen individually.

 *_ ORIGIN_<TAG> [*]

On this layer the snap objects are stored, i.e., the objects which can snap to target objects.
Currently, the following object types are allowed: points.
The color of the layer can be chosen individually.
The snapping behavior is controlled by the combination of letters in the <TAG> identifiers: If a letter is both
contained in *_ ATTACH_<TAG> as well as in *_ ORIGIN_<TAG>, then the geometries can be put together 4 .

Example:
- plane on layer *_ATTACH_AB
- object 1 with point on layer *_ORIGIN_A
- object 2 with point on layer *_ORIGIN_C
- object 3 with point on layer *_ORIGIN_BCG
Snapping between the plane and the points is activated for object 1 and object 3, because their <TAG>
identifiers contain a letter which also is included in the <TAG> of the ATTACH-layer of the plane.

If there are 2D snapping points stored on layer *_D2SNAP, the following applies:
 With target objects, points on *_ATTACH_<TAG> are preferred over points on *_D2SNAP, insofar
the snap object is attached to the mouse pointer at an appropriate point of the *_ORIGIN_<TAG> layer.
 With snap objects, points from both layers *_D2SNAP and *_ORIGIN_<TAG> are considered. At
which of the points the object is attached to the mouse pointer first, depends on the position of the
points.

2
In this case, the object to be placed is attached to the mouse pointer at one of the possible snap points, and the user, if applicable
(depending on the application), then can switch between the points.
3
Currently this is supported, e.g., in pCon.planner since version 6.6. Metatypes or specifically programmed OFML classes need not to be
created.
4
The matching snapping points then can be highlighted in the planning system in order to facilitate the planning by the user.

Page 5 of 7

<!-- Page 6 -->

# 7. General recommendations regarding data creation in AutoCAD

 Regarding the insertion points of articles the following recommendations apply:

o Normally the left bottom back corner of the volume boundary box should be used.
o For independently placeable, symmetric articles (like chairs and rotary tables) a centralized
insertion point should be used.

 For text primitives text style txt.shx should be used.

# 8. OFML data and application aspects

## 8.1. OFML data aspects

The references to external graphic data from within ODB are fully qualified:

::<man>::<series>::<geometry>

(ODB data completely must be written in lower case.)

5
The external graphic data is located in the directory <data>/<man>/<series>/1 and uses the following naming
convention: <geometry>.{geo|egms|dwg|3ds}.

6
The layer assignment is done on ODB level via attribute layer . The applied layer names correspond to the
OLAYERS convention.

The external graphic data itself does not contain layer assignments 7 . For the purpose of backward compatibility,
layer assignments in 2D data are possible. In this case the layer convention as described in this document
applies.

If block references and sub-block structures are used inside DWG data they have to apply the <MAN>-
<SERIES> qualification in order to avoid conflicts with the data of other manufacturers!

## 8.2. Application aspects

If it should be possible to transfer the structure of the OFML data from the OFML application into the AutoCAD
system, the corresponding blocks must be fully qualified and contain the appropriate information inside the
block name.

For the OFML objects to be inserted, the following layer has to be used:

72_<MAN2>_INSERT

Here, <MAN2> is either ANY if a unique manufacturer mapping is impossible (e.g. in case of configurations), or
corresponds to <MAN> as defined above.

The names of any blocks to represent OFML articles are application-specific.

5
We assume version 1 here.
6 For details see [OFML] and accompanying documents on ODB data creation.
7
Thus, it is drawn in AutoCAD on special layer 0.

Page 6 of 7

<!-- Page 7 -->

# Appendix

## History

Version 1.3, 1st revised version – 2015-08-18
 Removed obsolete section regarding migration from FOS
 Minor fixes and improved descriptions

Version 1.3 – 2014-03-21
 New layer *_D3FRONT_<TAG>

Version 1.2 – 2013-07-17
 New layers *_ATTACH_<TAG> and *_ORIGIN_<TAG>
 New layer *_ ACOUSTICS_<TAG>
 Minor restructuring of the document

Version 1.1 – 2007-10-04
 New layer *_ARTICLE_INFO_DPOS
 New color for *_ARTICLE_INFO
 Improved OFML compatibility
 OFML data and application aspects
 Tag names moved into separate document
 Redefinition of generic layer name

Version 1.0 – 2006-05-03
 initial version

Page 7 of 7