# odb_2.4_en

> Auto-generated from odb_2.4_en.pdf for AI consumption.

---


<!-- Page 1 -->

# Spezifikation

# ODB

### *

# OFML Database

# (OFML Part I)

# Version 2.4

Status: Release

Jochen Pohl, Ekkehard Beier, Sebastian Schmidt (EasternGraphics GmbH) (cid:132)

### January 6, 2022

*
Copyright' 2003–2022IndustrieverbandBu¨roundArbeitswelte. V.(IBA)
(cid:132)
ODBwasdevelopedbyEasternGraphicsGmbHonbehalfofindustrialassociationBu¨roundArbeitswelt
e. V.(IBA).

1

<!-- Page 2 -->

# Contents

1 Introduction 5

1.1 Survey of Tables . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5

1.2 Regulations regarding the format . . . . . . . . . . . . . . . . . . . . . . . . . 7

2 2D-Geometries 8

2.1 ODB Name . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8

2.2 Hierarchy Level . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8

2.3 Visibility . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10

2.4 Offset . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11

2.5 Rotation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 12
2.6 Scaling . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 13

2.7 Creating Objects . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14

2.7.1 Lines. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15

2.7.2 Squares and Rectangles . . . . . . . . . . . . . . . . . . . . . . . . . . 15

2.7.3 Circles, Arcs and Ellipses . . . . . . . . . . . . . . . . . . . . . . . . . 16

2.7.4 Points . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 17
2.7.5 Text . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 18

2.7.6 Stretch . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19

2.7.7 External Geometries . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19

2.8 Attributes . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 20

2.8.1 Color . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 20

2.8.2 Line Width . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 21
2.8.3 Line Style . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 21

2.8.4 Point Size . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 22

2.8.5 Font Height . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 22

2.8.6 Font Aspect . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 22

2.8.7 Layer . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 22

2

<!-- Page 3 -->

3 3D Geometries 23
3.1 ODB Name . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 23
3.2 Creating Objects . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 23
3.3 Controlling the Creation Process . . . . . . . . . . . . . . . . . . . . . . . . . 24
3.4 Offset . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 24
3.5 Rotation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 25
3.6 Creating Objects . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 26
3.6.1 Ellipsoid . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 26
3.6.2 Import . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 27
3.6.3 Top . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 28
3.6.4 Sphere . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 28
3.6.5 Hole . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 29
3.6.6 Parametric plane . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 31
3.6.7 Polygon . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 32
3.6.8 Block . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 32
3.6.9 Frame . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 33
3.6.10 Rotating Solid Object . . . . . . . . . . . . . . . . . . . . . . . . . . . 33
3.6.11 Extrusion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 35
3.6.12 Cylinder . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 36
3.6.13 OFML Reference . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 37
3.6.14 ODB Reference . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 37
3.7 Material Assignment . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 38
3.8 Constructive Solid Geometry (CSG) . . . . . . . . . . . . . . . . . . . . . . . 38
3.8.1 Union . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 39
3.8.2 Difference . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 39
3.8.3 Intersection . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 39
3.8.4 Stretch . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 39
3.9 Attributes . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 40
3.9.1 Selectability . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 40
3.9.2 Collision Response . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 40
3.9.3 Editing Response . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 40
3.9.4 Degree of Freedom for Translation . . . . . . . . . . . . . . . . . . . . 40
3.9.5 Degree of Freedom for Rotation . . . . . . . . . . . . . . . . . . . . . 41
3.9.6 Properties . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 41
3.9.7 Layer . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 41
3.10 Link . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 41

3

<!-- Page 4 -->

4 Attachment Points 42
4.1 How To Use Attachment Points . . . . . . . . . . . . . . . . . . . . . . . . . . 42
4.2 Defining Attachment Points . . . . . . . . . . . . . . . . . . . . . . . . . . . . 42
4.3 Definition of opposite attachment points . . . . . . . . . . . . . . . . . . . . . 44
4.4 Standard attachment points . . . . . . . . . . . . . . . . . . . . . . . . . . . . 45

5 Functions 47
5.1 Built-in Functions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 47
5.2 User-defined Functions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 47
5.2.1 Function Arguments . . . . . . . . . . . . . . . . . . . . . . . . . . . . 48
5.2.2 Return Value . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 50
5.2.3 Example . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 50

6 Layers 51
6.1 Functioning of Layers . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 51
6.2 Definition of Layers. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 51

4

<!-- Page 5 -->

# 1 Introduction

Using the ODB you can describe the geometric and, to a certain extent, the logical charac-
teristics of planned objects. The ODB’s goal is to have a descriptive form that can be easily
written into a program and that can be checked for consistency. In order to achieve this, the
ODB data are arranged in a table.

### 1.1 Survey of Tables

(cid:136)
Geometry–tables
There are two separate tables for the 2D- and the 3D-geometries. They are described
in the sections 2 and 3.
(cid:136)
Tables for attachment points
Planningobjectsareplacedinrelationtootherplanningobjectsotherusingattachment
points. The attachment points are defined in the ODB using three tables described in
section 4.
(cid:136)
Function table
In the table columns, arithmetic and logical expressions can often be used, which are
formulated in Reversed Polish Notation. These expressions can reference predefined or
user defined functions. The user defined functions are defined in the table described in
section 5.
(cid:136)
Layer table
3D layers are optionally defined in the table described in section 6.

5

<!-- Page 6 -->

## 2D 2d fun2cDs

odb_name odb_name name
level level body
visible visible
x_offs x_offs
y_offs y_offs
rot rot
x_scale x_scale
y_scale y_scale
ctor ctor
attrib attrib

## 2D la2yDer

## 3d

odb_name odb_name layer_name
obj_name level attributes
visible visible
x_offs x_offs
y_offs y_offs
z_offs rot
x_rot x_scale
y_rot y_scale
z_rot ctor
ctor attrib
mat
attrib
link

## 2D opp2aDttpt std2aDttpt

## attpt

odb_name odb_name odb_name odb_name
name level select has_stdattpts
select visible opposite prep_stdattpts
text_idx x_offs direction stdattpts
x_pos y_offs att_points
y_pos rot
z_pos x_scale
direction y_scale
rotation ctor
mode attrib

Figure 1: Survey of Tables

6

| 22Dd |
| --- |
| ooddbb__nnaammee
lelevevell
vivsiisbilbele
x_x_ooffsffs
y_y_ooffsffs
rorott
x_x_scsacalele
y_y_scsacalele
ctcotorr
atattrtibrib |

| fun2cDs |
| --- |
| name
body |

| 23Dd |
| --- |
| ooddbb__nnaammee
oblejv_enlame
vivsiisbilbele
x_x_ooffsffs
y_y_ooffsffs
z_rootffs
x_x_rostcale
y_y_rostcale
z_ctroort
ctaotrtrib
mat |
| attrib
link |

| la2yDer |
| --- |
| layer_name
attributes |

| a2ttDpt |
| --- |
| ooddbb__nnaammee
nalemveel
sevilseicbtle
texx_to_fidfsx
x_y_poofsfs
y_roptos
z_x_psocsale
diyr_escctiaolne
rocttaotrion
maotdtreib |

| opp2aDttpt |
| --- |
| odb_name
select
opposite
direction
att_points |

| std2aDttpt |
| --- |
| odb_name
has_stdattpts
prep_stdattpts
stdattpts |

<!-- Page 7 -->

### 1.2 Regulations regarding the format

CSV tables (comma separated values) are used as the physical exchange format between
OFML conform applications. The following regulations apply for this:
(cid:136)
Eachofthetablesdescribedbelowisincludedinexactlyonefile. Thefilenameismade
of the prefix ” ocd ”, the specified table name and the suffix ” .csv ”; the table name is
written completely in small letters.
(cid:136)
ISO-8859-1 (Latin-1) is used as the character set.
(cid:136)
Each line of the file represents a data record 1 .
Blanklines,i.e. linesconsistingofzeroorseveralblankcharacters(0x20)ortabulators
(0x09), are ignored. Lines starting with a number sign (’ # ’=0x23) are interpreted as a
comment and are ignored, too.
(cid:136)
The representations of the individual fields of a data record are separated from each
other by a semicolon (’ ; ’=0x3B).
(cid:136)
The value of a field consists of zero or more printable characters from ISO-8859-1
(0x20-0x7E, 0xA1-0xFF).
(cid:136)
The representation of a field is derived from the value of the field by replacing each
quotationmark(’"’=0x22)bytwoquotationmarksandenclosingtheresultingstringin
quotation marks. If the value of a field does not start with a quotation mark and does
not contain a semicolon (’;’=0x3B), the value itself (i.e. without any modifications)
can be used as the field representation.

1
AlineisterminatedeitherbyanLFcharacter(0x0A)orbyasequenceofCR(0x0D)andLF.

7

<!-- Page 8 -->

# 2 2D-Geometries

Table name: odb2d
Obligatory table: yes
The 2D-geometry of an OFML object is described by one or more consecutive entries in the
2D-table. Thepurposeofeachoftheseentriesistocreateagraphicalprimitive 2 andcontains
their scale, rotation, offset, and, if applicable, additional attributes, such as color, line width
etc.
The structure of the 2D-geometry table is summarized in the 1 table and described in detail
below.
field field description
number name
1 odb_name ODB name
2 hierarchy level
level
3 visible visibility control
4 x_offs X-offset
5 y_offs Y-offset
6 rot Rotation (around Z-axis)
7 x_scale X-scale
8 y_scale Y-scale
9 ctor creating 2D objects
10 attrib setting graphical attributes

Table 1: 2D geometries

### 2.1 ODB Name

Objectsforwhichyouwanttocreatea2D-geometryusingtheODB,provideafullyqualified
ODB name. It is comprised of the package name containing the used ODB and the basic
ODB name, which determines the entries to be used for the 2D- and 3D-tables. An example
of a fully qualified ODB name is ::foo::bar::BAZ, where is the package name,
::foo::bar
and is the basic ODB name.
BAZ
The2D-tableconsistsofaseriesofODBblocks. AnODBblockconsistsofseveralconsecutive
entries; the first entry in the column odb_name contains the basic ODB name, while in all
following entries in this block, the column odb_name is blank.

### 2.2 Hierarchy Level

Within an ODB name, the entries in the 2D-table can be sorted by hierarchy. This enables
you to group a variety of elements and transform them as a group (to scale, rotate, and
offset.)
2
When referencing external geometries, an entry can also create complex 2D geometries, which will be
handledaswholeobjects.

8

| field
number | field
name | description |
| --- | --- | --- |
| 1 | odb_name | ODB name |
| 2 | level | hierarchy level |
| 3 | visible | visibility control |
| 4 | x_offs | X-offset |
| 5 | y_offs | Y-offset |
| 6 | rot | Rotation (around Z-axis) |
| 7 | x_scale | X-scale |
| 8 | y_scale | Y-scale |
| 9 | ctor | creating 2D objects |
| 10 | attrib | setting graphical attributes |

<!-- Page 9 -->

ThedefaulthierarchylevelforfirstentryofanODBnameis0. Ifyouneedtocombineseveral
elements of a group, they list them as consecutive entries in the 2D-table and give them the
same hierarchy level, which must be one level above the level of the entry determining the
transformation of the group. The entry determining the transformation of a group is always
the last entry before the group whose hierarchy level is lower than the hierarchy level of the
group.

In the final form of the following example, four lines forming a square are combined into a
group, where the entire group has an X-offset of 0.6 and a Y-offset of 0.4. The origin of the
localcoordinatesystemislocatedinthecenterpointofthenon-rotatedsquare. Furthermore,
the square is contained in a rectangle with the dimensions 1.2×0.8 so that the center points
of the square and the rectangle are identical.
In the first step, the square consists of four lines, so that the center point of the square is
identical with the origin of the coordinate system of the OFML object:
odb_name level visible offs rot scale ctor attrib
x y x y
BAZ 0 −0.1 −0.1 0.0 0.2 1.0 hline
0 −0.1 0.1 0.0 0.2 1.0 hline
0 −0.1 −0.1 0.0 1.0 0.2 vline
0 0.1 −0.1 0.0 1.0 0.2 vline
y
(cid:54)
0.4
0.1,0.1
(cid:0)(cid:9)(cid:0)
(cid:45)
0.5 x
(cid:0)(cid:0)(cid:18)
−0.1,−0.1

Intheexampleabove,fourlinesarecreatedfromtoptobottom: from−0.1,−0.1to0.1,−0.1,
from −0.1,0.1 to 0.1,0.1, from −0.1,−0.1 to −0.1,0.1, and from 0.1,−0.1 to 0.1,0.1. For
detailed information on creating lines using the functions hline and vline, refer to section
2.7.1.

In the next step, the lines are combined into a group without moving the group yet. The
lines are still where they were in the above illustration.
odb_name level visible offs rot scale ctor attrib
x y x y
BAZ 0 0.0 0.0 0.0 1.0 1.0
1 −0.1 −0.1 0.0 0.2 1.0
hline
1 −0.1 0.1 0.0 0.2 1.0 hline
1 −0.1 −0.1 0.0 1.0 0.2 vline
1 0.1 −0.1 0.0 1.0 0.2 vline
You can see that the lines are merely preceded by a blank object 3 with the hierarchy level
0, and the hierarchy level of the lines is consequently raised to 1. This is how the lines are
created in relation to the object in the table’s first line.
3
Objectswithablankctorcolumnarenotgraphicallyrepresented.

9

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| BAZ | 0 |  | −0.1 | −0.1 | 0.0 | 0.2 | 1.0 | hline |  |
|  | 0 |  | −0.1 | 0.1 | 0.0 | 0.2 | 1.0 | hline |  |
|  | 0 |  | −0.1 | −0.1 | 0.0 | 1.0 | 0.2 | vline |  |
|  | 0 |  | 0.1 | −0.1 | 0.0 | 1.0 | 0.2 | vline |  |

|  |  |
| --- | --- |
|  |  |

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| BAZ | 0 |  | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 |  |  |
|  | 1 |  | −0.1 | −0.1 | 0.0 | 0.2 | 1.0 | hline |  |
|  | 1 |  | −0.1 | 0.1 | 0.0 | 0.2 | 1.0 | hline |  |
|  | 1 |  | −0.1 | −0.1 | 0.0 | 1.0 | 0.2 | vline |  |
|  | 1 |  | 0.1 | −0.1 | 0.0 | 1.0 | 0.2 | vline |  |

<!-- Page 10 -->

In the first step, the group is offset by 0.6 in X-direction, and by −0.4 in Y-direction, and
at the same time, a rectangle with the dimensions 1.2 (width) and 0.8 (height) is added. Its
upper left corner is located at the origin of the coordinate system of the OFML object. The
followingfigureshowsthegroup’smovedlocalcoordinatesystemwiththeaxisnamesx’and
y’.
odb_name level visible offs rot scale ctor attrib
x y x y
0 0.6 −0.4 0.0 1.0 1.0
BAZ
1 −0.1 −0.1 0.0 0.2 1.0 hline
1 −0.1 0.1 0.0 0.2 1.0 hline
1 −0.1 −0.1 0.0 1.0 0.2 vline
1 0.1 −0.1 0.0 1.0 0.2 vline
0 0.0 0.0 0.0 1.2 −0.8 quadrat
y
(cid:54)
0.5 1.0 1.5 (cid:45)
x
y’
(cid:54)

(cid:45)
x’
−0.5

−1.0

The table illustrates how the upper level object of a moved group must contain the offset for
this group, in this case in the first row of the table. The rectangle is created in the last row
of the table, in which a default square with the dimensions 1.0×1.0 is scaled in X-direction
to1.2andinY-directionto−0.8. Fordetailedinstructionsonhowtocreaterectangles,refer
to section2.7.2.

### 2.3 Visibility

In some cases, you may want to display parts of a 2D-symbol only for certain configurations
of the OFML object on which the symbol is based. The visibility can be controlled by an
entry in the visible column. The entry is displayed when the visible column is blank or
when it contains a value other than 0. If the value in the column is 0, neither the
visible
entry nor any existing lower hierarchy entries are displayed.

In the following example, we want to display a short line (representing a door handle) to the
leftorrightinfrontofawardrobe(representedbyarectangle). Thedecisionisbasedonthe
value of the parameter $ HANDLE , based on the OFML object and is either "L" for left or "R"
for right.
In the first table, a wardrobe is displayed with the dimensions 0.8 (width) and 0.6 (depth)
andtwohandles,oneontheright,andoneontheleft. Thelinessymbolizingthehandlesare
0.1 long. They start or end at a distance of 0.05 from the left or right edge of the wardrobe,
and they are offset 0.3 forward from the wardrobe.

10

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| BAZ | 0 |  | 0.6 | −0.4 | 0.0 | 1.0 | 1.0 |  |  |
|  | 1 |  | −0.1 | −0.1 | 0.0 | 0.2 | 1.0 | hline |  |
|  | 1 |  | −0.1 | 0.1 | 0.0 | 0.2 | 1.0 | hline |  |
|  | 1 |  | −0.1 | −0.1 | 0.0 | 1.0 | 0.2 | vline |  |
|  | 1 |  | 0.1 | −0.1 | 0.0 | 1.0 | 0.2 | vline |  |
|  | 0 |  | 0.0 | 0.0 | 0.0 | 1.2 | −0.8 | quadrat |  |

|  |  |
| --- | --- |
|  |  |

<!-- Page 11 -->

In this case, the symbol representing the wardrobe is created differently than in section 2.2.
Whileinsection2.2,therectanglewasnotmovedandhadtobescalednegativeinY-direction
in order to flip it down; in this example, the origin of the rectangle is being moved to its
lower left corner so that it can be scaled positive in Y-direction.
Thesecondrowinthetablerepresentsthelefthandle,andthethirdrowrepresentstheright
handle. Since the origin (the starting point) of the line representing the right handle was
indicated as its end point, the line must be scaled negative in X-direction in order to place
its end point left of its starting point.
odb_name level visible offs rot scale ctor attrib
x y x y
CUPBOARD 0 0.0 −0.6 0.0 0.8 0.6 quadrat
0 0.05 −0.63 0.0 0.1 1.0
hline
0 0.75 −0.63 0.0 −0.1 1.0
hline
y
(cid:54)
0.5 1.0 (cid:45)
x

−0.5

Inorderselectthehandlestodisplay,thelasttworowsofthecolumnvisiblemustbefilled.
However, we cannot use a constant value as in the previous examples. Also, the parameter
$HANDLEcannotbeusedbecauseitsvalueisastring,whiletheexpectedresultinthevisible
column is a number. Therefore, in order to display the handle, we need an expression with a
result of 1.0 for the left handle and the right handle, and a result of 0.0 in other cases. The
expression for the left handle in Reverse Polish Notation is ”‘$HANDLE "L" ==”’, and for the
left handle it is ”‘$HANDLE "R" ==”’ accordingly.
Sincethevisiblecolumnhasalimitedfieldwidth,theexpressionsaretypicallynotentered
directly in the column; they are written as a function. The function is saved in a separate
table, as described in section 5. The two following tables show the relevant entries in the
2D-table and in the function table.
odb_name level visible offs rot scale ctor attrib
x y x y
CUPBOARD 0 0.0 −0.6 0.0 0.8 0.6 quadrat
0 GL 0.05 −0.63 0.0 0.1 1.0 hline
0 GR 0.75 −0.63 0.0 −0.1 1.0 hline
name body
GL $HANDLE "L" ==
GR $HANDLE "R" ==

### 2.4 Offset

Every object you want to add has an insertion point that is used to place it in the origin
of a coordinate system. This insertion point is always the origin of the coordinate system

11

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| CUPBOARD | 0 |  | 0.0 | −0.6 | 0.0 | 0.8 | 0.6 | quadrat |  |
|  | 0 |  | 0.05 | −0.63 | 0.0 | 0.1 | 1.0 | hline |  |
|  | 0 |  | 0.75 | −0.63 | 0.0 | −0.1 | 1.0 | hline |  |

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| CUPBOARD | 0 |  | 0.0 | −0.6 | 0.0 | 0.8 | 0.6 | quadrat |  |
|  | 0 | GL | 0.05 | −0.63 | 0.0 | 0.1 | 1.0 | hline |  |
|  | 0 | GR | 0.75 | −0.63 | 0.0 | −0.1 | 1.0 | hline |  |

| name | body |
| --- | --- |
| GL | $HANDLE "L" == |
| GR | $HANDLE "R" == |

<!-- Page 12 -->

in which the object’s coordinates were captured. Using the offset parameter, the insertion
point can be moved in X-direction and the Y-axis. The object will be moved after scaling
and rotating the added object, if applicable.

This offset can be demonstrated using a diagonal line. A diagonal line that has been added
using the dline command in the ctor column extends from point 0.0,0.0 (the insertion
point) to point 1.0,1.0. If this diagonal line is not moved, it extends from 0.0,0.0 to 1.0,1.0
in the coordinate system of the OFML object as well. If you want to move it to extend
from 3.0,2.0 to 4.0,3.0, you need to move its insertion point 3.0 in X-direction and 2.0 in
Y-direction.

The following table and the corresponding figure show two diagonal lines being added; the
first line is not offset, and the second is offset by 3.0,2.0.

odb_name level visible offs rot scale ctor attrib
x y x y
FOO 0 0.0 0.0 0.0 1.0 1.0 dline
0 3.0 2.0 0.0 1.0 1.0 dline

y
(cid:54)
3
(cid:0)(cid:0)
(cid:0)
2

1
(cid:0)(cid:0)
(cid:0) (cid:45)
0
1 2 3 4 x

### 2.5 Rotation

The rotation parameter is used to rotate added objects around the origin of their local coor-
dinate system. The rotation angle is indicated as a mathematically positive value (counter-
clockwise) in degrees. The object is rotated after completion of scaling and offset, if applica-
ble.

Thefollowingexampleshowsthreesquares. Everysquarecreatedusing quadrat inthe ctor
column has a side length of 1.0 before scaling. The first square is added without rotation or
offset. The second square is rotated 30 degrees. The third square is rotated 30 degrees and
then offset 2.0 in X-direction and 1.0 in Y-direction.

odb_name level visible offs rot scale ctor attrib
x y x y
FOO 0 0.0 0.0 0.0 1.0 1.0 quadrat
0 0.0 0.0 30.0 1.0 1.0 quadrat
0 2.0 1.0 30.0 1.0 1.0
quadrat

12

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 | dline |  |
|  | 0 |  | 3.0 | 2.0 | 0.0 | 1.0 | 1.0 | dline |  |

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 | quadrat |  |
|  | 0 |  | 0.0 | 0.0 | 30.0 | 1.0 | 1.0 | quadrat |  |
|  | 0 |  | 2.0 | 1.0 | 30.0 | 1.0 | 1.0 | quadrat |  |

<!-- Page 13 -->

y
(cid:54)

(cid:34)
(cid:84)
(cid:34)
2.0
(cid:84)
(cid:84)
(cid:34)
(cid:34)
(cid:84) (cid:84)(cid:34)
(cid:34)
(cid:84)
(cid:84)
(cid:34)
(cid:84)(cid:34) (cid:45)
−1.0 1.0 2.0 3.0 x

### 2.6 Scaling

Scaling, next to offsetting, is the most important transformation for the creation of 2D-
geometries using the ODB. The reason for this is that many graphical primitives are created
in the shape of ”unit primitives.” The primary feature of the unit primitives is that for all
corner and end points, x ,y applies, since x as well as y are either 0.0 or 1.0. By scaling in
i i i i
X-andY-direction, theunitprimitivescanbesizedasdesired. Sincetheircoordinatevalues
are either 0.0 or 1.0 their dimension in X- or Y-direction can generally be used as scaling
factor.

In addition, objects can be mirrored using scaling parameters. If, for instance, the value in
thex_scalecolumnissetto−1.0theobjectismirroredattheY-axisofitslocalcoordinate
system. Likewise, a −1.0 in the column mirrors the object along the X-axis of its
y_scale
local coordinate system.

Finally, scaling and mirroring can be combined in one scaling factor. If, for instance, you
want to increase an object in size in X-direction by 2.5 and mirror it along the Y-axis at the
same time, enter −2.5 in the x_scale column.

The scaling will be performed on the object before any rotation or offsetting.

Toensurethatanobjectwillnotbescaledinacertaindirection,enterthescalingfactor1.0.
The value 0.0 as scaling factor is not permissible.

In the following example, a ”unit square” is created in the first row. The same square is
createdinthesecondrow,thoughthisoneisscaled4.0inX-directionand3.0inY-direction.
The following figure shows both squares.

odb_name level visible offs rot scale ctor attrib
x y x y
FOO 0 0.0 0.0 0.0 1.0 1.0 quadrat
0 0.0 0.0 0.0 4.0 3.0
quadrat

13

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 | quadrat |  |
|  | 0 |  | 0.0 | 0.0 | 0.0 | 4.0 | 3.0 | quadrat |  |

<!-- Page 14 -->

y
(cid:54)
4.0

3.0
B C
2.0

1.0
(cid:45)
A D
0 1.0 2.0 3.0 4.0 5.0 x

Inthenextexample,thesamerectangleastheoneinthesecondlineofthepreviousexample
iscreated,theonlydifferencebeingthatitismirroredalongtheX-axisbynegatingthescaling
factor. You can recognize that the object is mirrored by looking at the letters indicating the
corner points of the rectangle.
In this case, the same effect could have been achieved without mirroring, by offsetting the
rectangle by −3.0 in Y-direction. The effect is different, however, when the mirrored object
is not symmetric to the mirroring axis.
odb_name level visible offs rot scale ctor attrib
x y x y
FOO 0 0.0 0.0 0.0 4.0 −3.0 quadrat
y (cid:54)
1.0 2.0 3.0 4.0 5.0
0 (cid:45)
A D
x
−1.0

−2.0
B C
−3.0

−4.0

### 2.7 Creating Objects

The is used to create 2D-objects. There are generally three different scenarios:
ctor

(cid:136)
The column is blank. Inthiscasethe2D-objectwillnotbegraphicallyrepresented.
This can be useful when you want to create a group of objects, as described in section
2.2, and you want their transformation to be determined by the object at the next
higher level in the hierarchy.
(cid:136)
This column directly creates an object. The available objects are vertical, hori-
zontal and diagonal lines, squares, circles and arcs, ellipses, points, text and stretch.
(cid:136)
The column references an external geometry. In this case, it refers to a file that
may contain a complex 2D-geometry.

14

| B C
A D |
| --- |
| A |

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 0.0 | 0.0 | 0.0 | 4.0 | −3.0 | quadrat |  |

<!-- Page 15 -->

Ifitisnotblank,the ctor columnalwayscontainsafunctioncallinReversePolishNotation
causing the creation of a 2D-object.
The ctor column can also contain a function defined in the function table. This function, as
well as functions indirectly or directly invoked by this function, can all invoke the following
functions.

2.7.1 Lines

Threedifferentfunctionsareusedinthe ctor columntocreate”unitlines”. Thesefunctions
are listed in the 2 table.

function start point end point
hline x=0.0; y =0.0 x=1.0; y =0.0.
vline x=0.0; y =0.0 x=0.0; y =1.0.
dline x=0.0; y =0.0 x=1.0; y =1.0.

Table 2: Functions for line creation

Thedlinefunctionhelpsyoucreatediagonallines. Byusingappropriatescalingyoucancre-
ate lines of any length and slope. The exceptions are horizontal and vertical lines, since they
would need to be created using a scaling factor of 0.0, which is not permissible. Therefore,
horizontal and vertical lines need to be created using hline and vline.
Inordertodisplayalinewiththestartingpointx ,y andtheendpointx ,y theparameters
0 0 1 1
x ,y for offset, and x ,y for scaling (as shown in table 3) can be calculated.
offs offs scale scale
condition function x y x y
offs offs scale scale
y =y hline x y x −x 1.0
0 1 0 0 1 0
x =x vline x y 1.0 y −y
0 1 0 0 1 0
in other cases dline x y x −x y −y
0 0 1 0 1 0
Table 3: Calculating offset and scaling for lines

2.7.2 Squares and Rectangles

You can create squares and rectangles using the function in the column. The
quadrat ctor
functioncreatesasquarewithasidelengthof1.0,whoseleftlowercornerislocated
quadrat
at the origin of the local coordinate system. To create a rectangle with a width of w and a
height of h, set the scaling factor in X-direction to w and the scaling factor in Y-direction to
h. The rectangle created using this method can now be rotated and moved as desired.

The following example shows two tables represented by rectangles. These tables are posi-
tioned in a 90-degree angle to each other and are linked by a connector. Both tables are 1.6
wide and 0.8 deep. The first table is positioned horizontally with its upper left corner (A) at
the origin of the OFML object’s coordinate system. The lower left corner (C) of the second
table, which is rotated by 90 degrees, is located at the first table’s lower right corner (B). A

15

| function | start point | end point |
| --- | --- | --- |
| hline | x=0.0; y =0.0 | x=1.0; y =0.0. |
| vline | x=0.0; y =0.0 | x=0.0; y =1.0. |
| dline | x=0.0; y =0.0 | x=1.0; y =1.0. |

| condition | function | x
offs | y
offs | x
scale | y
scale |
| --- | --- | --- | --- | --- | --- |
| y =y
0 1 | hline | x
0 | y
0 | x −x
1 0 | 1.0 |
| x =x
0 1 | vline | x
0 | y
0 | 1.0 | y −y
1 0 |
| in other cases | dline | x
0 | y
0 | x −x
1 0 | y −y
1 0 |

<!-- Page 16 -->

connectingboardislocatedbetweenthetables,symbolizedbyalinebetweenthefirsttable’s
4
upper left corner (D) and the second table’s upper left corner (E) .
In the first row, the table (T1) is created in a horizontal position. This is trivial since the
unitsquaremerelyneedstobescaledcorrectlyinX-andY-directionwithanegativescaling
factor in Y-direction in order to mirror the table on its X-axis 5 . In the second row, the
table in vertical position, T2, is created. It is scaled using the same method as the table
in horizontal position, then turned 90 degrees in clockwise direction 6 and then moved into
position. In the third row, the line between the two tables is drawn.

odb_name level visible offs rot scale ctor attrib
x y x y
FOO 0 0.0 0.0 0.0 1.6 −0.8 quadrat
0 2.4 −0.8 −90.0 1.6 −0.8 quadrat
0 1.6 0.0 0.0 0.8 −0.8 dline

y
(cid:54)
1.0

# T1’

−1.0 1.0 2.0 (cid:45)
A D (cid:64)
x
(cid:64)

# T1

(cid:64)
(cid:64)
(cid:64)

### T2’ B

C E
−1.0

# T2

−2.0

2.7.3 Circles, Arcs and Ellipses

The three functions listed in the 4 table are used to draw circles, arcs and ellipses.
For all three functions, the center point is always located at the origin of the coordinate
system. For arcs ( ) the arc runs mathematically positive (counter-clockwise) from the
arc
start to the end angle.

The following simple example shows a round table with a diameter of 1.2 and a center point
located at 0.6,−0.6. There is no illustration for this example.
4 This example is not particularly relevant for practice since typically, the tables would be handled sepa-
rately.
5
Intheillustration,thenon-mirroredtable,T1’,isshownwithdashedlines.
6
Therotatedtable,T2’,isshownwithdashedlines.

16

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 0.0 | 0.0 | 0.0 | 1.6 | −0.8 | quadrat |  |
|  | 0 |  | 2.4 | −0.8 | −90.0 | 1.6 | −0.8 | quadrat |  |
|  | 0 |  | 1.6 | 0.0 | 0.0 | 0.8 | −0.8 | dline |  |

| A D
T1
B |  |
| --- | --- |
|  | C E
T2 |

<!-- Page 17 -->

syntax x–radius y-radius start angle end angle
1.0 1.0 0.0 360.0
circle
α α arc 1.0 1.0 α α
start end start end
x y ellipse x y 0.0 360.0
radius radius radius radius
Table 4: Commands for circles, arcs and ellipses

odb_name level visible offs rot scale ctor attrib
x y x y
FOO 0 0.6 −0.6 0.0 0.6 0.6 circle

The following example demonstrates the use of arcs. You may want to create a semicircular
tablewitharadiusof0.4. Thetable’sstraightsideintersectsthecenterpointofthesemicircle
and is located on the negative Y-axis.

odb_name level visible offs rot scale ctor attrib
x y x y
FOO 0 0.0 −0.4 0.0 0.4 0.4 -90.0 90.0 arc
0 0.0 0.0 0.0 1.0 −0.8 vline

y
(cid:54)
0.4 (cid:36) (cid:45)
x
−0.4
(cid:37)
−0.8

7
Sinceellipsearcsarecurrentlynotsupported,theyaredrawnusingscaledarcs . Pleasenote,
though, that the start and end angles typically change with a difference in scaling in X- and
Y-direction. You can calculate the angle for the arc using the equation
(cid:18) (cid:19)
y
scale
α =arctan tanα
kreis ellipse
x
scale
, making sure you use the appropriate quadrant.

2.7.4 Points

Use the point function to create a single point at the origin of the coordinate system.
8
Rotation and scaling are not considered for a point object .

INthefollowingexample,apointisplacedat1.0,−0.5. Intheillustrationthepointisshown
as a small cross for better visibility. In reality, it the point displays as a placed pixel.
7 We do not recommend drawing ellipses by scaling circles because several snap modes, especially the
perpendicularsnapmodewillceasetofunctionproperlyduetothedifferenceinscalinginX-andY-direction.
8
If rotation and/or scaling are indicated for a point object, and if there are objects below the hierarchy
levelofthepointobject,theseobjectsareinfluencedbytheindicatedrotationand/orhierarchy.

17

| syntax | x–radius | y-radius | start angle | end angle |
| --- | --- | --- | --- | --- |
| circle | 1.0 | 1.0 | 0.0 | 360.0 |
| α α arc
start end | 1.0 | 1.0 | α
start | α
end |
| x y ellipse
radius radius | x
radius | y
radius | 0.0 | 360.0 |

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 0.6 | −0.6 | 0.0 | 0.6 | 0.6 | circle |  |

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 0.0 | −0.4 | 0.0 | 0.4 | 0.4 | -90.0 90.0 arc |  |
|  | 0 |  | 0.0 | 0.0 | 0.0 | 1.0 | −0.8 | vline |  |

<!-- Page 18 -->

odb_name level visible offs rot scale ctor attrib
x y x y
FOO 0 1.0 −0.5 0.0 1.0 1.0 point
y
(cid:54)
1
0 (cid:45)
x

−1

2.7.5 Text

The text function creates a text object with a reference point at the origin of the local
coordinate system. The parameters should indicate the orientation of the text prior to its
rotation in relation to the reference point, as well as the text itself. The default character
size for uppercase text excluding descenders is 0.1.
The first parameter of the function determines the horizontal orientation of the text
text
prior to its rotation. Valid values for the parameter are found in the 5 table 9 . The text is
oriented vertically in a way that the base line 10 of the text intersects the reference point.

value meaning
−1.0 The text is always located to the immediate right of the reference point.
0.0 The text is centered horizontally to the reference point.
1.0 The text is located to the immediate left of the reference point.

Table 5: Orienting text objects

Usingscalingfactorstocontrolthetextheightandwidthisnotrecommended. Althoughthis
mayworkwellwiththecurrentvector-basedtextimplementation,itmightcauseproblemsif
bitmap fonts are introduced in the future. Instead, use the fheight and faspect attribute
functions to control the text height and extension. These functions are described in section
2.8.

The following example shows vertically oriented text, readable from the right. The text
is created left-aligned to the reference point (A) with the coordinates 0.15,−0.4. Since the
orientationisindicatedforthenon-rotatedtext,thetextislocatedabovethereferencepoint.
The text has a frame with an upper left corner (B) at 0.0,−0.2 and a lower left corner (C)
at 0.2,−0.45.
odb_name level visible offs rot scale ctor attrib
x y x y
FOO 0 0.15 −0.4 90.0 1.0 1.0 -1.0 "foo" text
0 0.0 −0.45 0.0 0.2 0.25 quadrat
9
Allfloatingpointvaluesareallowedfortheorientation. Forpositivevalues,thecenterpointofthetextis
alwayslocatedtotheleftofthereferencepoint,anditsdistancefromthereferencepointgrowswithgrowing
absolute values. The same applies to negative values, except that the center point of the text is located to
therightofthereferencepoint.
10
Thebaselineisthelineonwhichuppercasecharacterssit-excludingdescenders.

18

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 1.0 | −0.5 | 0.0 | 1.0 | 1.0 | point |  |

| value | meaning |
| --- | --- |
| −1.0 | The text is always located to the immediate right of the reference point. |
| 0.0 | The text is centered horizontally to the reference point. |
| 1.0 | The text is located to the immediate left of the reference point. |

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 0.15 | −0.4 | 90.0 | 1.0 | 1.0 | -1.0 "foo" text |  |
|  | 0 |  | 0.0 | −0.45 | 0.0 | 0.2 | 0.25 | quadrat |  |

<!-- Page 19 -->

y ................................
0.1 0.2 0.3
0
...............................
.
x
−0.1

−0.2
B
......... .........
......... .........
−0.3
......... .........
......... .........
.........
−0.4 A
C

2.7.6 Stretch

The function len a b c stretch doesn’t create an object but changes the geometries of the
objects below it’s hierarchy level.
The parameters are defined as follows:
Theparameterlenspecifiesthelenghtofthesegmenttoinsert,negativevaluesarepermitted
and are interpreted as contraction.
The parameters a b c describe the cutting line in the form ax+by =d. The vector a b is the
normal vector of the line, d is the distance of the line to the origin of the coordinate system.
The following example shows an object which is stretched by 0.7 units along the y-axis.

odb_name level visible offs rot scale ctor attrib
x y x y
FOO 0 0.0 0.0 0.0 1.0 1.0 0.7 0 1 0.25 stretch
1 0.0 0.0 0.0 1.0 1.0 "foo" egms

2.7.7 External Geometries

If you want to draw more complex geometries that you don’t want scaled as whole objects,
it may make sense to save them as EGM symbol file and to integrate them in the ODB as
11
external geometry .
The integration function is called egms. The expected argument for the function is a string
containing the name of the external geometry. This name can be either fully qualified or
not qualified. In the latter case, the system will try to find the geometry in the package
containing the ODB.
The coordinates in the external geometry are interpreted in the local coordinate system of
theODBentryreferencingtheexternalgeometry. Theycansubsequentlybetransformedby
scaling, rotating or moving.
Currently, you cannot set attributes for external geometries.
11 This is a standard procedure to create geometries in an ODB created from a FOS format conversion.
When initially saving ODB-based geometries, the use of external geometries is not recommended since the
useofgraphicalprimitivesdirectlysupportedbyODBismoreefficient.

19

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 | 0.7 0 1 0.25 stretch |  |
|  | 1 |  | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 | "foo" egms |  |

<!-- Page 20 -->

The following example references an EGM symbol. The EGM symbol is shown in the illus-
tration on the left in its local coordinate system. The resulting geometry in the coordinate
systemoftheOFMLisshownintheillustrationontheright. ThenameoftheEGMsymbol
is bar . Since the name is not qualified, the package containing the ODB should also contain
a file with the name bar.egms .
odb_name level visible offs rot scale ctor attrib
x y x y
FOO 0 3.0 −5.0 90.0 2.0 1.0 "bar" egms
y
(cid:54)
(cid:45)
0
y
1 2 3 x
(cid:54)
3
−1
(cid:1)(cid:1)
2 (cid:1)
(cid:64)(cid:64)
−2
(cid:1)(cid:1)
1 (cid:1)
−3
(cid:65)(cid:65)
(cid:0)(cid:0)(cid:64)(cid:64)
(cid:45)
(cid:65)
−4
0 1 2 3 x

−5

### 2.8 Attributes

In the 2D table’s attrib column, you can set several attributes valid for the 2D-object that
was created for the respective entry.
The attrib column can also contain a function defined in the function table. This function,
as well as functions they may invoke, can invoke any of the following functions.

2.8.1 Color

The color-setting function is called col. It expects three arguments in the range from 0.0
through 1.0, specifying the red, green and blue values of the color. If no color is set for an
object, that object is displayed black.
Color can be set for all graphical primitives. Graphical primitives are hline , vline , dline ,
quadrat , circle , arc , ellipse , point and text .

Thefollowingexampleshowshowaredrectanglewithtwobluediagonalsandthedimensions
2.0×1.0 is created. The rectangle’s upper left corner is located at the origin of the OFML
object’s coordinate system, and the lower right corner is located at 2.0,−1.0.
odb_name level visible offs rot scale ctor attrib
x y x y
FOO 0 0.0 −1.0 0.0 2.0 1.0
1 0.0 0.0 0.0 1.0 1.0 quadrat 1.0 0.0 0.0 col
1 0.0 0.0 0.0 1.0 1.0 dline 0.0 0.0 1.0 col
1 0.0 1.0 0.0 1.0 −1.0
dline 0.0 0.0 1.0 col

20

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 3.0 | −5.0 | 90.0 | 2.0 | 1.0 | "bar" egms |  |

| (cid:1)(cid:1)
(cid:1)
(cid:1)(cid:1)
(cid:1)
(cid:65)(cid:65)
(cid:65) |
| --- |
|  |

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 0.0 | −1.0 | 0.0 | 2.0 | 1.0 |  |  |
|  | 1 |  | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 | quadrat | 1.0 0.0 0.0 col |
|  | 1 |  | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 | dline | 0.0 0.0 1.0 col |
|  | 1 |  | 0.0 | 1.0 | 0.0 | 1.0 | −1.0 | dline | 0.0 0.0 1.0 col |

<!-- Page 21 -->

2.8.2 Line Width

Thefunctionforsettingthelinewidthiscalled . Theargumentitexpectsisapositive
lwidth
number specifying the line width in pixels. The standard line width is 1 pixels.
The line width can be set only for the primitives hline , vline , dline , quadrat , circle ,
arc , and ellipse .

The following example shows how to create an ellipse with a center point at 1.0,−0.5, a
radius of 1.0 in X-direction and a radius of 0.5 in Y-direction. The line width is 2 pixels.

odb_name level visible offs rot scale ctor attrib
x y x y
0 1.0 −0.5 0.0 1.0 1.0
FOO 1.0 0.5 ellipse 2 lwidth

2.8.3 Line Style

The function for setting the line style is called lstyle. The arguments it expects are two
numbersindicatingthelinepatternandextensionfactor. Linesaresolidbydefault,ordashed
when the object they are associated with is selected.
The line style can be set for the primitives hline, vline, dline, quadrat, circle, arc, and
ellipse.
Thefirstargumentisthelinepattern,anditcanacceptthevaluesinthe6table. Thesecond
argument is a factor whose value is interpreted as number of pixels. The exact meaning of
12
the factor depending on the used pattern is also described in the 6 table .

value description
−1 Using a predefined line style.
0 Drawing a solid line.
1 Drawing a dashed line. The factor determines the length of the displayed
and non-displayed line segments.
2 Drawing a dotted line. The factor determines the distance between the
center points of two neighboring points.
3 Drawingapoint-dotline. Thefactordeterminesthelengthofthedisplayed
line segment and the half length of the non-displayed segments.
4 Drawing a dashed double-dotted line. The factor determines the length of
the displayed line segment and a third of the length of the non-displayed
segments.
5 Drawing a dashed triple-dotted line. The factor determines the length of
the displayed line segment and a quarter of the non-displayed segments.

Table 6: Line Pattern

When using line patterns, please be aware that the display of selected object is based on
dashed lines. This applies only to lines that were not explicitly assigned a line pattern
12 The actual line segment length can differ from the information in the 6 table, depending on the driver
used for the 2D-version. This means that especially the OpenGL driver provides very limited possibilities,
whiletheX11driverprovidesratherexactresultsconsideringtheabilitiesofapixeldisplay.

21

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 1.0 | −0.5 | 0.0 | 1.0 | 1.0 | 1.0 0.5 ellipse | 2 lwidth |

| value | description |
| --- | --- |
| −1 | Using a predefined line style. |
| 0 | Drawing a solid line. |
| 1 | Drawing a dashed line. The factor determines the length of the displayed
and non-displayed line segments. |
| 2 | Drawing a dotted line. The factor determines the distance between the
center points of two neighboring points. |
| 3 | Drawingapoint-dotline. Thefactordeterminesthelengthofthedisplayed
line segment and the half length of the non-displayed segments. |
| 4 | Drawing a dashed double-dotted line. The factor determines the length of
the displayed line segment and a third of the length of the non-displayed
segments. |
| 5 | Drawing a dashed triple-dotted line. The factor determines the length of
the displayed line segment and a quarter of the non-displayed segments. |

<!-- Page 22 -->

differing from −1. Therefore, when creating 2D-symbols, make sure you do not assign a line
pattern to all lines of the symbol.

Inthefollowingexample, adashedrectanglewithdotteddiagonalsiscreatedusingthesame
dimensions as the example in section 2.8.1. The extension factor is 4 in all cases, which
typically provides good visual results.

odb_name level visible offs rot scale ctor attrib
x y x y
FOO 0 0.0 0.0 0.0 2.0 −1.0 quadrat 1 4 lstyle
0 0.0 0.0 0.0 2.0 −1.0 dline 2 4 lstyle
0 0.0 −1.0 0.0 2.0 1.0 dline 2 4 lstyle

2.8.4 Point Size

The diameter of a point is set using the function . It expects an argument indicating
psize
the point size in pixels.The standard size of a point is 1 pixels.
The point size can be set for objects created with the point function.

Thefollowingexampleisidenticaltotheoneinsection2.7.4,exceptthatthepointisdisplayed
with a diameter of 5.
odb_name level visible offs rot scale ctor attrib
x y x y
FOO 0 1.0 −0.5 0.0 1.0 1.0 point 5 psize

2.8.5 Font Height

For objects created with the function text, use the fheight function to set the font height.
Thefheightfunctionexpectsafloatingpointargumentindicatingthefontheightinunitsof
thelocalcoordinatesystem. Thefontheightistheheightofanuppercasecharacterexcluding
descenders. The standard height is 0.1.

2.8.6 Font Aspect

The function faspect determines the aspect of the used fonts for objects created using the
text function.
The faspect function expects a floating point argument indicating the font aspect. The
standardvaluefortheaspectis1.0. Avaluebetween0.0and1.0decreasesthecharactersize
in X-direction, and a value greater than 1.0 increases the character size in X-direction. An
aspect value of 0.0 is not permissible. For negative values the response is not defined.

2.8.7 Layer

Withthe function layer each object can be assignedto a layer (seesection 6). Thefunction
expects a string argument containing the name of the layer.

22

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 0.0 | 0.0 | 0.0 | 2.0 | −1.0 | quadrat | 1 4 lstyle |
|  | 0 |  | 0.0 | 0.0 | 0.0 | 2.0 | −1.0 | dline | 2 4 lstyle |
|  | 0 |  | 0.0 | −1.0 | 0.0 | 2.0 | 1.0 | dline | 2 4 lstyle |

| odb_name | level | visible | offs |  | rot | scale |  | ctor | attrib |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y |  | x | y |  |  |
| FOO | 0 |  | 1.0 | −0.5 | 0.0 | 1.0 | 1.0 | point | 5 psize |

<!-- Page 23 -->

# 3 3D Geometries

Table name: odb3d
Obligatory table: yes
The3DgeometryofanOFMLobjectisdescribedbyoneormoresuccessiveentriesinthe3D
table. The purpose of each of these entries is to create a graphical primitive 13 and contains
their position, rotation and other attributes, such as materials, selectability etc.
The structure of the 3D geometry table is summarized in table 7 and described in detail
below.
field field description
number name
1 ODB name
odb_name
2 obj_name object name
3 exist creation control
4 x_offs x-offset
5 y_offs y-offset
6 z-offset
z_offs
7 x_rot x-rotation
8 y_rot y-rotation
9 z_rot z-rotation
10 ctor 3D object creation
11 mat material(s) assignment
12 setting graphical attributes
attrib
13 link reserved for future use

Table 7: 3D geometries

### 3.1 ODB Name

Objectsforwhichyouwanttocreatea3D-geometryusingtheODB,provideafullyqualified
ODB name. The name is comprised of the package name containing the used ODB and
the basic ODB name, which determines the entries to be used for the 2D and 3D tables.
An example of a fully qualified ODB name is ::foo::bar::BAZ, where ::foo::bar is the
package name, and BAZ is the basic ODB name.
The3D-tableconsistsofaseriesofODBblocks. AnODBblockconsistsofseveralconsecutive
entries, of which the first in the column odb_name contains the basic ODB name, while for
all following entries in this block, the column odb_name is blank.

### 3.2 Creating Objects

In order to create an object, you need to indicate a relative name that refers to the OFML
object on the higher hierarchy level. The following rules apply to object names:
13
When referencing external geometries, an entry can also create complex 3D geometries, which will be
handledaswholeobjects.

23

| field
number | field
name | description |
| --- | --- | --- |
| 1 | odb_name | ODB name |
| 2 | obj_name | object name |
| 3 | exist | creation control |
| 4 | x_offs | x-offset |
| 5 | y_offs | y-offset |
| 6 | z_offs | z-offset |
| 7 | x_rot | x-rotation |
| 8 | y_rot | y-rotation |
| 9 | z_rot | z-rotation |
| 10 | ctor | 3D object creation |
| 11 | mat | material(s) assignment |
| 12 | attrib | setting graphical attributes |
| 13 | link | reserved for future use |

<!-- Page 24 -->

(cid:136) 14
Within an ODB block, a name may be given out only once .
(cid:136)
There can be no hierarchical assignment within one name. To this extent, in general a
name consists of linked basic names using the point ( . ) as a linking operator.
(cid:136)
Ifthenameofanobjectimpliestheexistenceofahierarchicalpredecessor,thesuccessor
must define the predecessor in the table.
(cid:136)
Asaconvention,thebasicnameconsistsoftheprefix o ,followedbyaninteger. Foreach
given predecessor, this number begins at 1 for the first successor and is incremented
accordingly for the following successors.

The following (incomplete) example shows how four objects are created. At the highest
level–correspondingtoLevel0inthe2DODB–twoobjectsarecreatedandnamed o1 and o2
based on the convention above. The other two objects’ features are to be defined in relation
toobject o2 . Forthisreason, ahierarchylevelreferringto o2 isintroduced, andaccordingly,
their names will be o2.o1 and o2.o2 .
odb_ obj_ ex offs rot ctor mat attrib link
name name ist x y z x y z
BAZ o1
o2
o2.o1
o2.o2

### 3.3 Controlling the Creation Process

The process of creating an object can be controlled using the column. The object
exist
described in the row is created when the column is blank or the expression contained
exist
(typicallyafunction)providesanumericalvalueotherthan0. Otherwise,theobjectwillnot
be created.
An object will also not be created if one of its hierarchical predecessors is not created based
on an entry in the exist column.

### 3.4 Offset

Everyaddedobjecthasauniqueattachmentpointthatisalwayslocatedattheoriginofthe
local coordinate system. For a cube this is its left lower back corner, for a sphere it is its
center point. When creating an object, this attachment point is located at the origin of the
predecessor’s coordinate system. Using the offset parameter, the attachment point can be
offset in all three directions in relation to the attachment point.
When you move an object using this method, all successors are moved accordingly.
Offsetting always occurs independently from a possible rotation.

Inthefollowingexample, o1 isnotoffsetfromtheOFMLobject’scoordinatesystem. Theori-
gin of o2 in relation to the OFML object’s coordinate system is at (0.0,3.0,0.0). The origins
14
AnODBblockiscomprisedofallentriesunderoneODBname.

24

| odb_
name | obj_
name | ex
ist | offs |  |  | rot |  |  | ctor | mat | attrib | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z | x | y | z |  |  |  |  |
| BAZ | o1
o2
o2.o1
o2.o2 |  |  |  |  |  |  |  |  |  |  |  |

<!-- Page 25 -->

of o2.o1 and o2.o2 in relation to the OFML object’s coordinate system are at (0.0,0.5,0.0)
and (0.4,0.5,0.0).

odb_ obj_ ex offs rot ctor mat attrib link
name name ist x y z x y z
BAZ o1 0.0 0.0 0.0 0.0 0.0 0.0 0.5 0.2 0.2 block
o2 0.0 0.3 0.0 0.0 0.0 0.0 0.5 0.2 0.2 block
0.0 0.2 0.0 0.0 0.0 0.0
o2.o1 0.1 0.2 0.2 block
o2.o2 0.4 0.2 0.0 0.0 0.0 0.0 0.1 0.3 0.2 block

### 3.5 Rotation

When you indicate rotation angles that are not equal 0.0, you can rotate an object out of
its orientation predefined by its type and give it a new orientation in reference to the OFML
object or its predecessor.
A (x,y,z) rotation will be shown on basic rotations as follows:

1. x rotation in reference to the initial X-axis

2. y rotation in reference to the Y-axis of the coordinate system after step 1

3. z rotation in reference to the Y-axis of the coordinate system after step 2

Be aware that when you indicate several rotation angles not equal 0.0, there will be some
interaction between the basic rotations.
Note. Whenusinghierarchylevelswhereeachhierarchylevelhasexactlyoneassignedbasic
rotation, you may determine the processing sequence for the basic rotations.
Rotation angles are indicated in degrees and in mathematically positive sense, i.e. counter-
clockwise.
When you rotate an object using this method, all successors are rotated accordingly.
Rotating always occurs independently from any possible offset.

25

| odb_
name | obj_
name | ex
ist | offs |  |  | rot |  |  | ctor | mat | attrib | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z | x | y | z |  |  |  |  |
| BAZ | o1
o2
o2.o1
o2.o2 |  | 0.0
0.0
0.0
0.4 | 0.0
0.3
0.2
0.2 | 0.0
0.0
0.0
0.0 | 0.0
0.0
0.0
0.0 | 0.0
0.0
0.0
0.0 | 0.0
0.0
0.0
0.0 | 0.5 0.2 0.2 block
0.5 0.2 0.2 block
0.1 0.2 0.2 block
0.1 0.3 0.2 block |  |  |  |

<!-- Page 26 -->

odb_ obj_ ex offs rot ctor mat attrib link
name name ist x y z x y z
BAZ o1 0.0 0.0 0.0 0.0 −143.2 0.0 0.5 0.2 0.2 block
o2 0.0 0.3 0.0 0.8 0.0 0.0 0.5 0.2 0.2 block
o2.o1 0.0 0.2 0.0 0.0 22.9 0.0 0.1 0.2 0.2 block
o2.o2 0.4 0.2 0.0 0.0 −22.9 0.0 0.1 0.3 0.2 block

### 3.6 Creating Objects

Thectorisusedtocreate3D-objects. Thisisdonebyinvokingoneofthefollowingfunctions
and providing the necessary parameters.

Note. For all of the primitives introduced in the following section, the origin of the local
coordinate system is part of the local volume limit.

3.6.1 Ellipsoid

The ellipsoid function creates a homogeneous ellipsoid beginning at the origin of the local
coordinate system and extending to all sides in accordance with the three radiuses.

The parameters are set by defining three radiuses: x, y, and z.

odb_ obj_ ex offs rot ctor mat attrib link
name name ist x y z x y z
BAZ o1 0.1 0.15 0.2 0.0 0.0 0.0 0.10.150.2ellipsoid
o2 0.4 0.1 0.6 0.0 0.0 0.0 0.40.10.6ellipsoid

26

| odb_
name | obj_
name | ex
ist | offs |  |  | rot |  |  | ctor | mat | attrib | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z | x | y | z |  |  |  |  |
| BAZ | o1
o2
o2.o1
o2.o2 |  | 0.0
0.0
0.0
0.4 | 0.0
0.3
0.2
0.2 | 0.0
0.0
0.0
0.0 | 0.0
0.8
0.0
0.0 | −143.2
0.0
22.9
−22.9 | 0.0
0.0
0.0
0.0 | 0.5 0.2 0.2 block
0.5 0.2 0.2 block
0.1 0.2 0.2 block
0.1 0.3 0.2 block |  |  |  |

| odb_
name | obj_
name | ex
ist | offs |  |  | rot
x y z |  |  | ctor | mat | attrib | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z | x | y |  |  |  |  |  |
| BAZ | o1
o2 |  | 0.1
0.4 | 0.15
0.1 | 0.2
0.6 | 0.0
0.0 | 0.0
0.0 | 0.0
0.0 | 0.10.150.2ellipsoid
0.40.10.6ellipsoid |  |  |  |

<!-- Page 27 -->

3.6.2 Import

The imp functionimportsanexternal3D-recordinordertocreateacorrespondingprimitive.
The following formats are supported:

1. 3DS
3DS is a binary format describing geometries based on triangle lists. Other 3DS file
components are material, lighting, and camera data, though these components are
ignored during the input.
A 3DS record is imported into the ODB in a way that the minimal coordinate of its
orthogonal volume limit is matched with the local coordinate system’s origin.
The file extension for 3DS files is .3ds.
2. OFF
OFF is a simple ASCII format to describe indexed polygonal objects. In addition to
the geometry file with the extension .geo, the ODB runtime environment optionally
supports files with the extension .vnm, in which normal vectors can be assigned to
vertices.

In general, the input records for the ODB should be unilateral and should describe closed
bodies. The basic planes (triangles or polygons) should be simple, planar, convex and clock-
wise oriented.
Each record optionally supports a resolution reducing variant. This record’s files differ from
the primary record in that they are preceded by an underscore.
The first function parameter is the optionally fully qualified name of the record without the
file extension. If the name is not or not fully qualified, it will be preceded by the qualifier of
the fully qualified ODB name. Therefore, the record must be contained in the same package
with the ODB.
The geometry is scaled using the following parameters in the sequence x, y, and z.
odb_ obj_ ex offs rot ctor mat attrib link
name name ist x y z x y z
BAZ o1 0.0 0.0 0.0 0.0 −50.1 0.0 "w140" 0.2 0.2 0.2 imp

27

| odb_
name | obj_
name | ex
ist | offs |  |  | rot |  |  | ctor | mat | attrib | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z | x | y | z |  |  |  |  |
| BAZ | o1 |  | 0.0 | 0.0 | 0.0 | 0.0 | −50.1 | 0.0 | "w140" 0.2 0.2 0.2 imp |  |  |  |

<!-- Page 28 -->

3.6.3 Top

The top function creates an invisible object generally used in order to combine objects and
place them together.
Please note that neither the top object nor any of its direct or indirect successors is allowed
to be selectable.

odb_ obj_ ex offs rot ctor mat attrib link
name name ist x y z x y z
BAZ o1 0.0 0.3 0.0 0.0 0.0 0.0 top
o1.o1 0.0 0.2 0.0 0.0 0.0 0.0 0.1 0.2 0.2 block
o1.o2 0.4 0.2 0.0 0.0 0.0 0.0 0.1 0.3 0.2 block

3.6.4 Sphere

The sphere function creates a homogeneous sphere beginning at the origin of the local
coordinate system and extending to all sides.
The parameters are implemented by indicating a radius.

28

| odb_
name | obj_
name | ex
ist | offs |  |  | rot |  | ctor | mat | attrib | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z | x | y z |  |  |  |  |
| BAZ | o1
o1.o1
o1.o2 |  | 0.0
0.0
0.4 | 0.3
0.2
0.2 | 0.0
0.0
0.0 | 0.0
0.0
0.0 | 0.0 0.0
0.0 0.0
0.0 0.0 | top
0.1 0.2 0.2 block
0.1 0.3 0.2 block |  |  |  |

<!-- Page 29 -->

odb_ obj_ ex offs rot ctor mat attrib link
name name ist x y z x y z
BAZ o1 0.0 0.0 0.0 0.0 0.0 0.0 0.4 sphere
o2 0.3 0.0 0.5 0.0 0.0 0.0 0.2 sphere

3.6.5 Hole

Theholefunctioncreatescircularorrectangularholesincircularorrectangularareas. Itcan
beusedtosimulatebooleanoperations(especiallysubtraction)inspecialcases. However,the
actual subtraction in the sense of a boolean operation is not performed. The actual purpose
oftheholefunctionistogenerateplanesforthecombinationscircularouterline–rectangular
hole, and rectangular outer line–circular hole. However, no outer planes along the outer line
are created in the local Z-direction.
A hole object is created at the local origin, centered in relation to the outer plane. In the
depth, aholeobjectstartsattheoriginofthelocalcoordinatesystemandextendsalongthe
negative Z-axis.
As a general rule, a hole should always be contained in the contour. The hole should not
touch the contour. Exception: the depths of the outline and the hole can be identical. In
this case, the hole is transparent; in all other cases it has a base.
The creation parameters are as follows:

1. outline
When the value "R" is indicated, the outer shape ofthe object is a rectangle, when the
value "C" is indicated, it is a circle.
2. Outer width
If the outer shape of the object is a rectangle, this value determines the outer width;
in all other cases it indicates the radius of the contour.

3. Outer height
If the outer shape of the object is a rectangle, this value determines the outer height;
in all other cases the value is ignored.

29

| odb_
name | obj_
name | ex
ist | offs |  |  | rot |  |  | ctor | mat | attrib | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z | x | y | z |  |  |  |  |
| BAZ | o1
o2 |  | 0.0
0.3 | 0.0
0.0 | 0.0
0.5 | 0.0
0.0 | 0.0
0.0 | 0.0
0.0 | 0.4 sphere
0.2 sphere |  |  |  |

<!-- Page 30 -->

4. Outer depth
This value indicates the outer depth of the object.
5. Back plane
This value controls the creation of a back plane in reference to the already generated
front plane. If the value 1 is indicated, the plane will be created. In all other cases,
indicate 0 .
6. Hole shape
When the value "R" is indicated, the outer shape of the hole is a rectangle, when the
value "C" is indicated, it is a circle.
7. Hole width
If the outer shape of the hole is a rectangle, this value determines the hole’s width; in
all other cases it indicates the hole’s radius.
8. Hole height
If the outer shape of the hole is a rectangle, this value determines the hole’s height; in
all other cases the value is ignored.
9. Hole depth
This value indicates the depth of the hole.
10. Hole offset in X-direction
This value indicates the offset of the hole’s center point in X-direction in reference to
the local coordinate system’s origin, which is also the center point of the object.
11. Hole offset in Y-direction
This value indicates the offset of the hole’s center point in Y-direction in reference to
the local coordinate system’s origin, which is also the center point of the object.

odb_ obj_ ex offs rot ctor ...
name name ist x y z
0.2 0.15 0.2 ...
BAZ o1 "R" 0.4 0.3 0.2 1 "C" 0.08 0.1 0.2 0.0 0.0 hole
o2 0.2 0.65 0.2 ... "R" 0.4 0.3 0.2 1 "R" 0.08 0.1 0.2 0.0 0.0 hole
o3 0.7 0.15 0.2 ... "C" 0.2 0.2 0.2 1 "C" 0.08 0.1 0.2 0.0 0.0 hole
o4 0.7 0.65 0.2 ... "C" 0.2 0.2 0.2 1 "R" 0.08 0.1 0.2 0.0 0.0 hole

30

| odb_
name | obj_
name | ex
ist | offs |  |  | rot | ctor | ... |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z |  |  |  |
| BAZ | o1
o2
o3
o4 |  | 0.2
0.2
0.7
0.7 | 0.15
0.65
0.15
0.65 | 0.2
0.2
0.2
0.2 | ...
...
...
... | "R" 0.4 0.3 0.2 1 "C" 0.08 0.1 0.2 0.0 0.0 hole
"R" 0.4 0.3 0.2 1 "R" 0.08 0.1 0.2 0.0 0.0 hole
"C" 0.2 0.2 0.2 1 "C" 0.08 0.1 0.2 0.0 0.0 hole
"C" 0.2 0.2 0.2 1 "R" 0.08 0.1 0.2 0.0 0.0 hole |  |

<!-- Page 31 -->

3.6.6 Parametric plane

The surf function creates a three-dimensional object based on a two-dimensional grid. The
grid’s coordinates function as support points that are connected by the resulting plane with-
out edges. The specification for the ctor column is:

x y z ...x y z udim wdim umode wmode surf
0 0 0 udim×wdim−1 udim×wdim−1 udim×wdim−1

Thegrid’sdimensionsareudimandwdim. Accordingly,forudim×wdimthree-dimensional
coordinatesshouldbeenteredtodefinethegrid. Withineachbasicplane,theright-hand-rule
15
determines the orientation .
Theumodeandwmodeflagscanbeusedtoindicatewhether( 1 )ornot( 0 )theplaneshould
be closed along the corresponding grid direction.
Thefollowingexamplecreatesaparametricplanefrom32supportpoints. Theplaneisclosed
along the grid direction and was subsequently turned.

-0.150815 0.064026 -0.919388 0.075575 -0.269460 -0.810568 \
0.329356 -0.102473 -0.677988 0.576438 -0.273374 -0.555442 \
0.772948 0.063867 -0.448708 0.563432 0.366948 -0.549524 \
0.327520 0.171928 -0.673550 0.062688 0.355544 -0.804890 \
-0.490592 -0.095985 -0.379506 -0.371192 -0.281256 -0.307272 \
-0.237910 -0.188485 -0.220444 -0.107800 -0.283430 -0.139519 \
-0.004815 -0.096073 -0.070032 -0.115308 0.072304 -0.136939 \
-0.239162 -0.036040 -0.218088 -0.378620 0.065969 -0.304818 \
-0.565542 -0.069120 0.606108 -0.431332 -0.277990 0.529648 \
-0.275384 -0.175605 0.441702 -0.126945 -0.283430 0.357456 \
-0.004079 -0.074762 0.288498 -0.128341 0.115085 0.359282 \
-0.273712 -0.004849 0.441200 -0.432810 0.110994 0.531496 \
0.122084 -0.013038 0.885150 0.226666 -0.273824 0.722364 \
0.348838 -0.145497 0.535098 0.464742 -0.279946 0.355724 \
0.561242 -0.018840 0.208880 0.464406 0.218190 0.359580 \
0.350472 0.067949 0.534016 0.226248 0.212398 0.726268 \
8 4 1 0 surf

15
Withthethumboftherighthandverticaltotheplane,theotherfingersofthatsamehandindicatethe
orientation.

31

<!-- Page 32 -->

3.6.7 Polygon

The polyg functioncreatesapolygoninthespacebasedonalistofthree-dimensionalcoordi-
nates. Theseshouldbeindicatedinclockwisedirection. Thelastcoordinateisautomatically
connected to the first. The described polygon should be simple, convex and planar. The
generated polygon has no back plane.

The specification for the ctor column is:

x y z ...x y z n polyg
0 0 0 n−1 n−1 n−1

The following example creates a simple polygon:

0.0 0.0 0.0 0.0 0.7 0.0 0.35 1.0 0.0 0.7 0.7 0.0 0.7 0.0 0.0 5 polyg

3.6.8 Block

The functioncreatesahomogeneouscubestartingattheoriginofthelocalcoordinate
block
system and extending along the local coordinate system’s positive axes.

The parameters are implemented by indicating width, height, and depth.

odb_ obj_ ex offs rot ctor mat attrib link
name name ist x y z x y z
BAZ o1 0.0 0.0 0.0 0.0 0.0 0.0 0.2 0.3 0.4 block
o2 0.3 0.0 0.5 0.0 0.0 0.0 0.3 0.15 0.2 block

32

| odb_
name | obj_
name | ex
ist | offs |  |  | rot |  |  | ctor | mat | attrib | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z | x | y | z |  |  |  |  |
| BAZ | o1
o2 |  | 0.0
0.3 | 0.0
0.0 | 0.0
0.5 | 0.0
0.0 | 0.0
0.0 | 0.0
0.0 | 0.2 0.3 0.4 block
0.3 0.15 0.2 block |  |  |  |

<!-- Page 33 -->

3.6.9 Frame

The function creates a frame starting at the origin of the local coordinate system and
frame
extending along the local coordinate system’s positive axes. This is achieved by subtracting
an orthogonal volume from the solid. The thickness of the frame is identical in X- and Y-
direction. For the dimensions in X- and Y-direction w and h and for the x/y-thickness th,
w,h>2×th should always apply.
The parameters are implemented by indicating frame width, height, depth, and thickness.

odb_ obj_ ex offs rot ctor mat attrib link
name name ist x y z x y z
BAZ o1 0.0 0.0 0.0 0.0 0.0 0.0 0.3 0.5 0.1 0.05 frame
o2 0.5 0.0 0.0 0.0 0.0 0.0 0.2 0.2 0.2 0.05 frame

3.6.10 Rotating Solid Object

The rot functioncreatesathree-dimensionalobjectbyrotatingathree-dimensionaldefinition
curve. The specification for the ctor column is:

axis axis axis x y z ...x y z n angle smooth u w c0 c1 rot
x y z 0 0 0 n−1 n−1 n−1

33

| odb_
name | obj_
name | ex
ist | offs |  |  | rot |  |  | ctor | mat | attrib | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z | x | y | z |  |  |  |  |
| BAZ | o1
o2 |  | 0.0
0.5 | 0.0
0.0 | 0.0
0.0 | 0.0
0.0 | 0.0
0.0 | 0.0
0.0 | 0.3 0.5 0.1 0.05 frame
0.2 0.2 0.2 0.05 frame |  |  |  |

<!-- Page 34 -->

Theparametersaxis ,axis ,andaxis specifytherotationaxisusingastandardizedvector.
x y z
Theparametersx throughz describethedefinitioncurve, andtheparameterncontains
0 n−1
the number of the definition curve’s coordinates. The definition curve and the rotation
axis should always be in the same plane. Avoid coordinates that are located exactly on
the rotation axis. The curve should be defined according to the right-hand-rule: When the
thumb of the right hand points in the direction of the rotation, the other fingers on that
hand show the orientation.
The angle parameter determines the angle. To create a homogeneous rotating solid body,
enter the value 360.0.
The smooth parameter determines whether the coordinates of the definition curve are con-
nected in a linear ( 0 ) way or using soft transitions( 1 ).
The u indicates whether the last and first point of the definition curve should be connected
( 1 ) or not connected ( 0 ).
The w indicates, whether the solid isclosed( 1 ) along therotation or not closed ( 0 ). If angle
has the value 360.0, generally the value 1 is indicated, otherwise the value 0 is indicated.
The c0 parameter indicates whether for the first and last coordinate of the definition axis a
linear lid plane, positioned vertically to the rotation axis, should (1) or should not (0) be
created.
The c1 parameter indicates whether the inner planes being created should (1) or should not
(0) be created if angle<360.0 and w are not equal 1.
The following example shows how to create a homogeneous rotating solid body around a
local Y-axis, which is subsequently moved in X- and Z-direction.

0.0 0.1 0.0 \
0.2 0.0 0.0 0.05 0.1 0.0 0.1 0.2 0.0 0.2 0.5 0.0 0.05 0.55 0.0 0.2 0.6 0.0 0.1 0.7 0.0 \
7 360.0 1 0 1 1 0 rot

The rotx function creates a rotating solid body around the local X-axis. The specification
for the ctor column is:

x y ...x y n angle smooth u w c0 c1 rotx
0 0 n−1 n−1

34

<!-- Page 35 -->

The roty function creates a rotating solid body around the local X-axis. The specification
for the ctor column is:

x y ...x y n angle smooth u w c0 c1 roty
0 0 n−1 n−1

The rotz function creates a rotating solid body around the local X-axis. The specification
for the ctor column is:

y z ...y z n angle smooth u w c0 c1 rotz
0 0 n−1 n−1

3.6.11 Extrusion

The sweep functioncreatesathree-dimensionalobjectbydraggingathree-dimensionalcurve
in a predetermined direction. The specification for the ctor column is:

axis axis axis len x y z ...x y z n smooth u c0 c1
sweep
x y z 0 0 0 n−1 n−1 n−1

The parameters axis , axis and axis specify the dragging direction using a standardized
x y z
vector.
The parameter len indicates the length along the dragging direction.
Theparametersx throughz describethedefinitioncurve,andtheparameterndescribes
0 n−1
the number of the definition curve’s coordinates. The definition curve should always be
located in one plane to which the dragging vector should be vertical. The curve should be
defined according to the right-hand-rule: When the thumb of the right hand points in the
direction of the dragging vector, the other fingers on that hand show the orientation of the
definition curve.
The smooth parameter determines whether the coordinates of the definition curve are con-
nected in a linear (0) way or using soft transitions(1).
The u indicates whether, according to the value of smooth, the last and first point of the
definition curve should be connected (1) or not connected (0) .
The c0 parameter indicates whether (1) or not (0) the solid should receive lid planes vertical
to the dragging vector.
The c1 parameter indicates whether ( 1 ) or not ( 0 ) the connection between the last and firs
coordinate should be handled as a plane. If both coordinates are in the same location, enter
0 .
The following example creates an extrusion along the local Y-axis.

0.0 1.0 0.0 0.05 \
0.5 0.0 -0.5 -0.5 0.0 -0.5 -0.5 0.0 0.5 0.0 0.0 0.5 0.0 0.0 0.7 0.25 0.0 0.7 \
0.25 0.0 0.5 0.7 0.0 0.5 0.7 0.0 0.25 -0.25 0.0 0.25 -0.25 0.0 -0.25 0.25 0.0 -0.25 \
0.25 0.0 0.1 0.7 0.0 0.1 0.7 0.0 -0.15 0.5 0.0 -0.15 16 0 0 1 1 sweep

35

<!-- Page 36 -->

The sweepx creates an extrusion along the local X-axis. The specification for the ctor
column is:

len z y ...z y n smooth u c0 c1 sweepx
0 0 n−1 n−1

The sweepy creates an extrusion along the local Y-axis. The specification for the ctor
column is:

len x z ...x z n smooth u c0 c1 sweepy
0 0 n−1 n−1

ThesweepzcreatesanextrusionalongthelocalZ-axis. Thespecificationforthectorcolumn
is:

len x y ...x y n smooth u c0 c1 sweepz
0 0 n−1 n−1

3.6.12 Cylinder

The cyl function creates a homogeneous cylinder symmetrical in rotation to the local Y-
axis. The cylinder starts at the origin of the local coordinate system and extends along
the coordinate system’s positive Y-axis. The parameters are implemented by indicating two
positive numbers for length and radius as arguments for the cyl function.

odb_ obj_ ex offs rot ctor mat attrib link
name name ist x y z x y z
BAZ o1 0.0 0.0 0.0 0.0 0.0 0.0 0.4 0.2 cyl
o2 0.5 0.0 0.2 0.0 0.0 0.0 0.1 0.2 cyl

36

| odb_
name | obj_
name | ex
ist | offs |  |  | rot |  |  | ctor | mat | attrib | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z | x | y | z |  |  |  |  |
| BAZ | o1
o2 |  | 0.0
0.5 | 0.0
0.0 | 0.0
0.2 | 0.0
0.0 | 0.0
0.0 | 0.0
0.0 | 0.4 0.2 cyl
0.1 0.2 cyl |  |  |  |

<!-- Page 37 -->

3.6.13 OFML Reference

The clsref function creates an instance of an OFML class. The specification for the ctor
column is:

p ...p n " classname " clsref
0 n−1

where the class specific creation or initialization parameters are p through p . The are
0 n−1
mapped to the initialization function as follows:

classname pFa pNa p ... p
::initialize( , , , , )
0 n−1

classname is the optional, fully qualified name of the OFML class to be used. If the name
is not or not fully qualified, the name of the package containing the ODB will automatically
precede the name.

3.6.14 ODB Reference

The odbref function creates an instance of an ODB definition. The specification for the
ctor column is:

p ...p n "odbname" odbref
0 n−1

where p through p are the specific parameters you can access in the referenced ODB
0 n−1
block using the ODB parameters P0 through P n-1.
odbname is the optional, fully qualified name of the ODB definition to be used. If odbname
is not or not fully qualified, the name of the package containing the ODB will automatically
precede the name.

37

<!-- Page 38 -->

### 3.7 Material Assignment

The mat column is used for assigning materials. If it is not empty, it specifies a material or
several materials as follows:

(cid:136)
If the entry references a primitive type, the material expression should return only
one result as a material name. This material will be transferred to the object method
setMaterial() .
(cid:136)
Iftheentryreferencesaclasstype( clsref ),theentrycancontainanyamountofmate-
rialnames,whichcanalsobecombinedusingvectors. Theywillbecombinedintoavec-
torinthebasicOFMLlanguageandtransferredtotheobjectmethod setMaterials()
as an argument.
Example. Letusassumethatthe Mat ODBparameterissetto "foo" andthematerial
column contains the expression "bar" $Mat "baz" 2] . The method setMaterials()
is invoked for the object as follows:

obj.setMaterials(["bar", ["foo", "baz"]])

(cid:136)
If the entry references an ODB block (odbref), this entry can contain any amount of
materialnameswhichcanalsobecombinedusingvectors. WithinthereferencedODB
block, the materials can be accessed using the ODB parameters M0 through M(n-1).

Material names can optionally be indicated as fully qualified names. If they are not fully
qualified or only partially qualified, the material name is automatically preceded by the
package name containing the ODB.

### 3.8 Constructive Solid Geometry (CSG)

CSG allows the creation of complex shaped solid objects by combining primitive objects
using Boolean operators. With the exception of the stretch operation, these operators are
specified in column ctor via the function csg, their operands are the children in the object
hierarchy.
The following regulations apply to these children:

1. Onlyelementarygeometries(ellipsoid,imp,sphere,surf,block,frame,rot,sweep
or cyl ) and CSG nodes are allowed.
2. All geometries (especially those of type imp or surf ) must be closed three-dimensional
shapes.
3. Field obj_name only serves to define the hierarchy. Except for the topmost CSG node,
no OFML objects are created.
4. Alldatainthefields mat and attrib areignored. Therefore, thesefieldsshouldbeleft
blank.

The following subsections describe the available operators.

38

<!-- Page 39 -->

3.8.1 Union

The operation union generates the union (logical OR) of the geometries of their operands.
The following example shows a bar with a rounded end:
odb_ obj_ ex offs rot ctor mat attrib link
name name ist x y z x y z
BAZ o1 0.0 0.0 0.0 0.0 0.0 0.0 union csg
o1.o1 0.0 0.0 0.0 0.0 0.0 0.0 0.5 0.02 cyl
o1.o2 0.0 0.5 0.0 0.0 0.0 0.0 0.02 sphere

3.8.2 Difference

The operation diff generates the difference of the geometries of their operands. In the case
of more than two operands, operands 2..n first are united and then subtracted from the first
operand.
The following example shows a block with a cylindrical hole:
odb_ obj_ ex offs rot ctor mat attrib link
name name ist x y z x y z
BAZ o1 0.0 0.0 0.0 0.0 0.0 0.0 diff csg
0.0 0.0 0.0 0.0 0.0 0.0
o1.o1 2.0 0.5 2.0 block
o1.o2 1.0 0.0 1.0 0.0 0.0 0.0 0.2 cyl

3.8.3 Intersection

The operation inter generates the intersection (logical AND) of the geometries of their
operands.
The following example shows a lens-like object:
odb_ obj_ ex offs rot ctor mat attrib link
name name ist x y z x y z
BAZ o1 0.0 0.0 0.0 0.0 0.0 0.0 inter csg
o1.o1 −0.8 0.0 0.0 0.0 0.0 0.0 1.0 sphere
o1.o2 0.8 0.0 0.0 0.0 0.0 0.0 1.0 sphere

3.8.4 Stretch

Thestretchoperationisrepresentedbythefunctionlenabcdstretchinthectorcolumn.
The parameters are defined as follows:
Theparameterlenspecifiesthelenghtofthesegmenttoinsert,negativevaluesarepermitted
and are interpreted as contraction.
The parameters a b c d describe the cutting plane in the form ax+by+cz =d. The vector
a b c is the normal vector of the plane, d is the distance of the plane to the origin of the
coordinate system.
The following example shows an object which is stretched by 0.5 units along the x-axis.
odb_ obj_ ex offs rot ctor mat attrib link
name name ist x y z x y z
BAZ o1 0.0 0.0 0.0 0.0 0.0 0.0 0.5 1.0 0.0 0.0 0.0 stretch
0.0 0.0 0.0 0.0 0.0 0.0
o1.o1 "sitz" 1.0 1.0 1.0 imp

39

| odb_
name | obj_
name | ex
ist | offs |  |  | rot |  |  | ctor | mat | attrib | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z | x | y | z |  |  |  |  |
| BAZ | o1
o1.o1
o1.o2 |  | 0.0
0.0
0.0 | 0.0
0.0
0.5 | 0.0
0.0
0.0 | 0.0
0.0
0.0 | 0.0
0.0
0.0 | 0.0
0.0
0.0 | union csg
0.5 0.02 cyl
0.02 sphere |  |  |  |

| odb_
name | obj_
name | ex
ist | offs |  |  | rot |  |  | ctor | mat | attrib | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z | x | y | z |  |  |  |  |
| BAZ | o1
o1.o1
o1.o2 |  | 0.0
0.0
1.0 | 0.0
0.0
0.0 | 0.0
0.0
1.0 | 0.0
0.0
0.0 | 0.0
0.0
0.0 | 0.0
0.0
0.0 | diff csg
2.0 0.5 2.0 block
0.2 cyl |  |  |  |

| odb_
name | obj_
name | ex
ist | offs |  |  | rot |  |  | ctor | mat | attrib | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z | x | y | z |  |  |  |  |
| BAZ | o1
o1.o1
o1.o2 |  | 0.0
−0.8
0.8 | 0.0
0.0
0.0 | 0.0
0.0
0.0 | 0.0
0.0
0.0 | 0.0
0.0
0.0 | 0.0
0.0
0.0 | inter csg
1.0 sphere
1.0 sphere |  |  |  |

| odb_
name | obj_
name | ex
ist | offs |  |  | rot |  |  | ctor | mat | attrib | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | x | y | z | x | y | z |  |  |  |  |
| BAZ | o1
o1.o1 |  | 0.0
0.0 | 0.0
0.0 | 0.0
0.0 | 0.0
0.0 | 0.0
0.0 | 0.0
0.0 | 0.5 1.0 0.0 0.0 0.0 stretch
"sitz" 1.0 1.0 1.0 imp |  |  |  |

<!-- Page 40 -->

### 3.9 Attributes

The attrib column can contain zero or more of the following expressions.

3.9.1 Selectability

The object’s selectability is explicitly prohibited through the expression 0 sel and it is
permitted through 1 sel .
If there is no indication, and if the object was created by referencing an ODB block (using
odbref ) it is not selectable. If it was created by instancing an OFML class (using clsref ),
the object’s selectability depends on the implementation of the OFML class. In all other
cases, theobjectisaprimitiveobjectwhichisnotselectablebydefault. Theselectabilityfor
this object should not be permitted.

3.9.2 Collision Response

The expression 0 cd excludes the object from the collision determination. If there is no
entryortheexpression1 cdisentered,theobjectistakenintoconsiderationforthecollision
determination.
This expression should only be used for entries referencing an ODB block (using odbref) or
an OFML class (using clsref).
Ifthecollisiondeterminationisdeactivatedforanobject,thisdeactivationalsoappliestoits
direct or indirect successors.

3.9.3 Editing Response

An object’s response to editor operations such as using the clipboard (clipboard) is defined
by an expression in the form of value cut. The following values are permissible for value:

-1 In general, deleting the object is not permitted.
0 Deletingtheobjectitselfisnotpermitted,however,itmaybedeletedthroughanupper
level. Incaseofanattempted”cut”-operation(cut, delete)ontheobject,theoperation
is applied to the first object that can be cut in an upward traversing action.
1 Deleting the object and copying it to the clipboard is permitted. This is applicable
even when the editing response was not specified in an ODB entry.
Deleting the object is permitted, however, it should not be copied to the clipboard.
2

3.9.4 Degree of Freedom for Translation

The trx function can be used to indicate whether or not the object can be moved in the
direction of each axis on the local coordinate system. The function expects a single, integer
argumentresultingfromanadditionofthepermittedaxes, wheretheX-, Y-, andZ-axesare
represented by 1, 2, and 4. If the argument is 0, the object cannot be moved.

40

<!-- Page 41 -->

3.9.5 Degree of Freedom for Rotation

Usingthe rtx functionyoucanindicateforeachaxisonthelocalcoordinatesystemwhether
or not the object can be rotated around the respective axis. The function expects a single,
integer argument resulting from an addition of the permitted axes, where the X-, Y-, and
Z-axes are represented by 1, 2, and 4. If the argument is 0, the object cannot be moved.

3.9.6 Properties

The prop functioncanbeusedtosetoptionalparametersafterobjectcreation. Thisisdone
16
by calling the method setPropValue() (see interface Property in OFML specification ).
The function expects two arguments: The first argument specifies the key of the property
andmustbeanOFMLsymbol(i.e. includingtheleading @ character). Thesecondargument
specifies the value to be set and must match the type of the property. This function may be
called repeatedly to set an arbitrary number of properties.

3.9.7 Layer

With the function layer each object canbe assignedto a layer (seesection 6). Thefunction
expects a string argument containing the name of the layer.

### 3.10 Link

17
The link column is not supported in this version .

16
EasternGraphicsGmbH:OFML – Standardisiertes Datenbeschreibungsformat der Bu¨romo¨belindustrie.
17
Itwillbeincludedinlaterupgradesandlinkstoothertablesusingakey.

41

<!-- Page 42 -->

# 4 Attachment Points

### 4.1 How To Use Attachment Points

When you add a new object to a plan and select an existing object, the system attempts to
place the new object in relation to the selected object. For this purpose, the existing object
needs an attachment point, and the object you are inserting needs a matching element 18 .
Every attachment point can be identified by its own unique symbolic name. This name is
used to assign matching attachment points.
The position of the attachment points is indicated in relation to the local coordinate system
of the specific object. A new object is always placed in a way that its attachment point is at
the same location with the existing object’s matching attachment point. Furthermore, the
new object can be rotated to a certain angle around the Y-axis intersecting this point.
In order to be able to add different object types in different locations, you can assign a
list of attachment points for every object. When you are adding an object to an existing
object, the system will browse the existing object’s list from beginning to end until it finds
anattachmentpointmatchingtheonedefinedbytheobjectyouwanttoinsert, andthenew
object can be placed without causing a collision

### 4.2 Defining Attachment Points

Table name: attpt
Obligatory table: yes
The attachment points for an object are described in the attpt table, which is described in
the 8 table.

field- field description
nummer name
1 odb_name ODB–Name
2 name symbolic name of attachment point
3 select selection of attachment point
4 text_idx index in text table
5 local x–position of attachment point
x_pos
6 y_pos local y–position of attachment point
7 z_pos local z–position of attachment point
8 direction attachment direction
9 rotation rotation of object to be inserted
10 mode insert mode (child/neighbor)

Table 8: Definition of attachment points

In the following section the individual columns of this table are described in more detail:
18
Inadditiontoorinsteadofattachmentpoints,theODBplanningelement’sclasscanalsoimplementits
ownlogicforattachingobjects.

42

| field-
nummer | field
name | description |
| --- | --- | --- |
| 1 | odb_name | ODB–Name |
| 2 | name | symbolic name of attachment point |
| 3 | select | selection of attachment point |
| 4 | text_idx | index in text table |
| 5 | x_pos | local x–position of attachment point |
| 6 | y_pos | local y–position of attachment point |
| 7 | z_pos | local z–position of attachment point |
| 8 | direction | attachment direction |
| 9 | rotation | rotation of object to be inserted |
| 10 | mode | insert mode (child/neighbor) |

<!-- Page 43 -->

(cid:136)
odb_name
Column odb_name containsthebasicnameoftheODBnameforwhomthisattachment
point definition is valid.
When determining the attachment point of an object, the prefix of the ODB name
determines the ODB in which the attachment points are to be searched for. The basic
ODB name is used for the attpt table.
In the current implementation, all entries of this table that correspond to the key are
supplied as potential attachment points in the order of their appearance in the table,
unless they have been explicitly deselected in column select .
(cid:136)
name
Column name contains the symbolic name of the attachment point. It consists of any
series of letters, digits, and underscores. The first character must not be a digit and
the series is case-sensitive.
Toensurethatthenamesoftheattachmentpointsfromdifferentpackagesdon’tcollide,
the names of the attachment points should have a prefix that is as unique as possible
and that e.g. may be comprised of the manufacturer or serial abbreviation of the
packet. An exception to this rule is a combination of elements from different series of
a manufacturer.
Thenameoftheattachmentpointshouldbeuniquewithinallentriesoftheattpt table
with the same ODB name.
(cid:136)
select
Column select is used for the selection of the attachment point. Using this column,
an attachment point can be explicitly enabled or disabled. The attachment point
is implicitly enabled,if this column is blank. If it is not blank, it must contain an
expression in Reverse Polish Notation whose result is a numerical value. If the result
is 0, the attachment point is disabled; otherwise, it is enabled.
(cid:136)
text_idx
Thiscolumncontainsanindexinatexttablecontaininganattachmentpointdescribing
the text. The text can be used in a tree consisting of an object and attachment point
19
hierarchy in the user interface .
(cid:136)
x_pos, y_pos, z_pos
These columns contain the local coordinates of the position of the attachment point in
the form of an expression in Reverse Polish Notation.
(cid:136)
direction
In column direction , the direction is set in which this attachment point should be
inserted. Thepredefineddirectionsareasfollows: R (right), L (left), B (back), F (front),
and (top). In addition, any other directions can be defined.
T
If the column is blank, there is no concrete preset attachment direction. This is rel-
evant for determining the opposite attachment points using the table oppattpt that is
described in section 4.3, since all attachment points that are contained in this table
and are identical by name are considered opposite attachment points regardless of a
direction that may have been specified.
19
Inthecurrentimplementation,thecolumnisnotusedandshouldcontain0.

43

<!-- Page 44 -->

(cid:136)
rotation
In column rotation , you can specify a rotation of the object to be inserted around
the y axis that passes through the attachment point. You specify this mathematically
positive (counterclockwise) as an expression in Reverse Polish Notation using degree
measure.
(cid:136)
mode
In column mode you determine if the object to be inserted is to be inserted as a child
or neighbor of the existing object. To insert it as a child, this column must contain a
C ; otherwise it must contain a S .

### 4.3 Definition of opposite attachment points

Table name: oppattpt
Obligatory table: yes
The table oppattpt described in table 9 determines which attachment points from different
objects match each other. This is determined from the point of view of the object to be
inserted which supplies a list of its own matching attachment points for possible attachment
points of other objects taking their attachment direction into account 20 .

field field description
number name
1 odb_name ODB name
2 select selection of opposite attachment point
3 opposite name of opposite attachment point
4 direction direction of opposite attachment point
5 list of its own matching attachment points
att_points
Table 9: opposite attachment points

The following section describes the columns listed in table 9 in greater detail:

(cid:136)
odb_name
Column contains the basic name of the ODB name of the object to be
odb_name
inserted. The attachment points of the object are listed in column att_points.
(cid:136)
select
Column select is used to select the opposite attachment point specified in column
opposite . You can explicitly enable or disable the attachment point in this column.
The attachment point is implicitly enabled if the column is blank. If it is not blank,
it must contain an expression in Reverse Polish Notation whose result is a numerical
value. If the result is 0, the opposite attachment point is disabled; otherwise, it is
enabled.
(cid:136)
opposite
Column opposite contains the name of the opposite attachment point. In addition to
20
Theobjecttobeinsertedisrequestedtosupplyalistofitsownattachmentpointsthatmaybepossible
counterpartsofthecurrentlyviewedattachmentpointoftheexistingobject.

44

| field
number | field
name | description |
| --- | --- | --- |
| 1 | odb_name | ODB name |
| 2 | select | selection of opposite attachment point |
| 3 | opposite | name of opposite attachment point |
| 4 | direction | direction of opposite attachment point |
| 5 | att_points | list of its own matching attachment points |

<!-- Page 45 -->

theODBnameincolumn odb_name andthedirectionincolumn direction , isusedas
a key when accessing table oppattpt.
(cid:136)
direction
Column direction containsthedirectionoftheoppositeattachmentpoint. Inaddition
to the ODB name in column odb_name and the name of the opposite attachment point
in column opposite , it is used as a key when accessing table oppattpt.
The opposite attachment point is only considered either if no attachment direction
was specified for it, or if the direction field in this table is blank, of if the specified
attachment direction is identical to the direction indicated in this table.
(cid:136)
att_points
Column contains a list of attachment points of the objects to be inserted
att_points
with the ODB names indicated in column . The names match the oppo-
odb_name
site attachment point specified in column . The list is delimited by blank
opposite
characters.

### 4.4 Standard attachment points

Table name: stdattpt
Obligatory table: yes
In addition to the user-defined attachment points, there is a set of 18 standard attachment
points, that are located in the eight corners, in the center of the top and bottom edges, and
in the middle of the deck and floor areas of the terminating volume of an OFML object.
Theorderandattachmentdirectionoftheseattachmentpointsaredependentonthecurrent
planning direction. The names of these standard attachment points are described in table
10.
name position
bottom top
left front corner
LBF LTF
CBF CTF middle of the front edge
RBF RTF right front corner
LBC LTC middle of the left edge
CBC CTC middle of the floor or deck area
RBC RTC middle of the right edge
left back corner
LBB LTB
CBB CTB middle of the back edge
RBB RTB right back corner

Table 10: names of standard attachment points

The first letter of the name of a standard attachment point determines the position of the
attachment point in x direction (left: L , middle: C , right: R ). The second letter determines
itspositioninydirection(bottom: B ,top: T ).Finally,thethirdletterdeterminesitsposition
in z direction (front: F , middle: C , back: B ).
Using table stdattpt described in table 11, it is possible to control the use of standard at-
tachment points for ODB objects by their ODB names. In particular, you can determine if

45

| name |  | position |
| --- | --- | --- |
| bottom | top |  |
| LBF | LTF | left front corner |
| CBF | CTF | middle of the front edge |
| RBF | RTF | right front corner |
| LBC | LTC | middle of the left edge |
| CBC | CTC | middle of the floor or deck area |
| RBC | RTC | middle of the right edge |
| LBB | LTB | left back corner |
| CBB | CTB | middle of the back edge |
| RBB | RTB | right back corner |

<!-- Page 46 -->

standardattachmentpoints shouldbeused atallfor anobjectwith agiven ODBname, and
if so, whether these are to be taken into account before or after the user-defined attachment
points. Further, it is possible to only take a subset of the standard attachment points into
account.
field field description
number name
1 odb_name ODB name
2 general use of standard attachment points
has_stdattpts
3 prep_stdattpts position of standard attachment points
4 stdattpts selection of subset of standard attachment points

Table 11: standard attachment points

The following section describes the individual columns in table stdattpt in greater detail.

(cid:136)
odb_name
Column odb_name contains the basic name of the ODB name of the respective object.
(cid:136)
has_stdattpts
Column has_stdattpts determines if objects with the appropriate ODB name have
standard attachment points or not. The column must contain an unsigned integer
value. If this value is 0, standard attachment points are not used regardless of the
content of the other columns in this table. Otherwise, the standard attachment points
are used as indicated in the following columns.
(cid:136)
prep_stdattpts
Column prep_stdattpts determines, if the standard attachment points are to be
viewed before or after any user-defined attachment points. It must contain an un-
21
signed integer value. If this value is 0, they are viewed after the user-defined points ,
or before them.
(cid:136)
stdattpts
Columnstdattptseitherisblankorcontainsalistofstandardattachmentpointnames
thataredelimitedbyblankcharacters. Inthefirstcase,allstandardattachmentpoints
are taken into account; in the second case, only the specified ones are.

If there is no entry in the stdattpt table for a ODB name, all standard attachment points
after any user-defined attachment points are taken into account for objects with this ODB
name.

21
Thisisprobablythenormalcase.

46

| field
number | field
name | description |
| --- | --- | --- |
| 1 | odb_name | ODB name |
| 2 | has_stdattpts | general use of standard attachment points |
| 3 | prep_stdattpts | position of standard attachment points |
| 4 | stdattpts | selection of subset of standard attachment points |

<!-- Page 47 -->

# 5 Functions

Table name:
funcs
Obligatory table: no

Functions can have two distinguishing characteristics: built-in and user-defined functions.
In principle, the function arguments are noted before invoking the function. For example, in
order to calculate the square root of 2.0, one must write ”‘ 2.0 sqrt ”’.
Generally it must be said that the possibilities offered by ODB for processing and defining
functions are hardly used to their fullest extent, at least for generating 2D geometries. Nor-
mally, used expressions and functions used by 2D ODB are limited to processing arithmetic
standard operators + , - , * , and / .

### 5.1 Built-in Functions

In addition to the functions regarding object generation and setting of attributes described
in sections 2 and 3, particularly mathematical functions are built into the interpreter for the
expressions used in ODB.
The return value of some of theses functions is a frequently used constant. For example, the
M_PIfunctionreturnsthevalueofπ. Forotherfunctions,thereturnvaluedependsononeor
severalargumentsthatthefunctionexpects. Oneexampleisthefunctionsinthatcalculates
the sine of its argument using the radian measure.
Table 12 contains a summary of all built-in functions that return constants. The built-in
mathematical functions are listed in table 13. Table 14 describes the built-in function for
manipulating the stack. Table 15 documents the use of two functions that are particularly
interesting for 2D ODB.

Name returned value name returned value
M_1_PI 1/π M_2_PI 2/π
√
M_2_SQRTPI 2/ π M_2PI 2π
M_E e M_LN10 ln10=log 10
e
M_LN2 ln2=log 2 M_LOG10E lge=log e
e 10
1/ln2=log e π
M_LOG2E M_PI
2
M_PI_2 π/2 M_PI_4 π/4
√ √
M_SQRT1_2 1/ 2 M_SQRT2 2

Table 12: built-in constants

### 5.2 User-defined Functions

User-definedfunctionsareplacedintothefunctiontable. Thestructureofthisfunctiontable
is shown in table 16.

47

| Name | returned value | name | returned value |
| --- | --- | --- | --- |
| M_1_PI | 1/π
√ | M_2_PI | 2/π |
| M_2_SQRTPI | 2/ π | M_2PI | 2π |
| M_E | e | M_LN10 | ln10=log 10
e |
| M_LN2 | ln2=log 2
e | M_LOG10E | lge=log e
10 |
| M_LOG2E | 1/ln2=log e
2 | M_PI | π |
| M_PI_2 | π/2
√ | M_PI_4 | π/4
√ |
| M_SQRT1_2 | 1/ 2 | M_SQRT2 | 2 |

<!-- Page 48 -->

Arguments name event description
x y y =arccosx
acos
x asin y y =arcsinx
x atan y y =arctanx
x y atan2 z z =arctan(y/x)
The signs of x and y are used to calculate the quadrant
of the event.
x ceil y Calculates the smallest integer value y that is greater
than or equal to x.
x cos y y =cosx
x y y =coshx
cosh
x
x exp y y =e
x fabs y y =|x|
x floor y Calculates the largest integer value y that is smaller
than or equal to x.
x y fmod z Calculates the floating point remainder of x/y.
x log y y =lnx
x y y =lg10
log10
x modf i f Divides the x argument into the integer part i and the
fractional part f so both have the same sign as x.
x neg y y =−x
y
x y pow z z =x
x sin y y =sinx
x sinh y y =sinhx
√
x sqrt y y = x
x tan y y =tanx
x tanh y y =tanhx

Table 13: built-in mathematical functions

Thefirstcolumncontainsthenameofthefunction. Thefunctionnamecanconsistofaseries
of letters of any length 22 , digits, and underscores. The first character must be a letter or an
underscore 23 .
ThesecondcolumncontainsthebodyofthefunctionintheformofanexpressioninReverse
Polish Notation.

5.2.1 Function Arguments

A user-defined function can have any number of arguments, including none.
No special measures have to be taken for functions without argument.
For functions with arguments, the number of arguments must be at the beginning of the
function body, followed by the invocation of the built-in argc function. This makes it pos-
sible to remove the specified number of arguments from the local stack of the expression
22
OnlylettersAtoZandatozarepermitted. Therefore,anumlautcannotbeused.
23
We recommend against using an underscore at the beginning of a function name, since such names are
reservedforinternaluse.

48

| Arguments | name | event | description |
| --- | --- | --- | --- |
| x | acos | y | y =arccosx |
| x | asin | y | y =arcsinx |
| x | atan | y | y =arctanx |
| x y | atan2 | z | z =arctan(y/x)
The signs of x and y are used to calculate the quadrant
of the event. |
| x | ceil | y | Calculates the smallest integer value y that is greater
than or equal to x. |
| x | cos | y | y =cosx |
| x | cosh | y | y =coshx |
| x | exp | y | y =ex |
| x | fabs | y | y =|x| |
| x | floor | y | Calculates the largest integer value y that is smaller
than or equal to x. |
| x y | fmod | z | Calculates the floating point remainder of x/y. |
| x | log | y | y =lnx |
| x | log10 | y | y =lg10 |
| x | modf | i f | Divides the x argument into the integer part i and the
fractional part f so both have the same sign as x. |
| x | neg | y | y =−x |
| x y | pow | z | z =xy |
| x | sin | y | y =sinx |
| x | sinh | y | y =sinhx
√ |
| x | sqrt | y | y = x |
| x | tan | y | y =tanx |
| x | tanh | y | y =tanhx |

<!-- Page 49 -->

Arguments name event description
n The functionmustbeinvokeddirectlyatthe
argc argc
beginning of a user-defined function. The n pa-
rameteristhenumberofargumentsthatthisuser-
defined function expects. It removes this number
of values from the stack of the invoker and makes
it available for the argument access using $a.
x dup x x The dup function duplicates the top element on
the stack.
x y dup2 x y x The dup2 function duplicates the element on the
stack that is second to the top.
s ...s s x dupx s ...s s s The dupx function duplicates the xth object from
i 2 1 i 2 1 x
the top of the stack.
x pop The pop function removes the top element from
the stack.
x y swap y x The swap function swaps the two top elements on
the stack.
s ...s s x swapx s ...s s The swapx function swaps the top element of the
x 2 1 1 2 x
stack with the xth element from the top of the
stack.

Table 14: functions for stack manipulation

Arguments name event description
x utos s Theutosfunctionchangesthexfloatingpointvalueto
thesstringaccordingtothesettingsforunitformatting
in the user interface.
x atos s The atos function changes the a floating point value to
the s string according to the settings for angle format-
ting in the user interface .

Table 15: functions for 2D ODB

Field field description
number name
1 name function name
2 body function body

Table 16: function table

that invoked the function and to temporarily store them for the duration of processing the
function. Then, the function can access the arguments using $n, with n being the number of
the argument. Numbering of the arguments begins at 0.

49

| Arguments | name | event | description |
| --- | --- | --- | --- |
| n | argc |  | Theargcfunctionmustbeinvokeddirectlyatthe
beginning of a user-defined function. The n pa-
rameteristhenumberofargumentsthatthisuser-
defined function expects. It removes this number
of values from the stack of the invoker and makes
it available for the argument access using $a. |
| x | dup | x x | The dup function duplicates the top element on
the stack. |
| x y | dup2 | x y x | The dup2 function duplicates the element on the
stack that is second to the top. |
| s ...s s x
i 2 1 | dupx | s ...s s s
i 2 1 x | The dupx function duplicates the xth object from
the top of the stack. |
| x | pop |  | The pop function removes the top element from
the stack. |
| x y | swap | y x | The swap function swaps the two top elements on
the stack. |
| s ...s s x
x 2 1 | swapx | s ...s s
1 2 x | The swapx function swaps the top element of the
stack with the xth element from the top of the
stack. |

| Arguments | name | event | description |
| --- | --- | --- | --- |
| x | utos | s | Theutosfunctionchangesthexfloatingpointvalueto
thesstringaccordingtothesettingsforunitformatting
in the user interface. |
| x | atos | s | The atos function changes the a floating point value to
the s string according to the settings for angle format-
ting in the user interface . |

| Field
number | field
name | description |
| --- | --- | --- |
| 1 | name | function name |
| 2 | body | function body |

<!-- Page 50 -->

5.2.2 Return Value

A user-defined function can have any number of return values, including none.
To return one or several values, the values are simply left on the stack once the processing
of the function bodies is completed. After the return of the function, these values are listed
in the same order at the top of the local stack of the expression that invoked the function.
It is the responsibility of the invoking expression to remove the return values from the stack.

5.2.3 Example

The following example shows the DIST function that calculates the distance between two
points that are defined by their x and y coordinates.The arguments are put on the stack by
theinvokerinthefollowingorder: x , y , x , y . Ifthefunctionreturns, theargumentshave
0 0 1 1
been removed from the stack and are replaced by the result of the function.

name body
DIST 4 argc $2 $0 - dup * $3 $1 - dup * + sqrt
The following table shows the processing of the function body using the local stack of the
function.
Stack token operation
4 4 ⇒ Stack
4 argc Applying the 4 argument values from the stack of the invoking
expression
$2 x ⇒ Stack
1
x $0 x ⇒ Stack
1 0
x x - dx=x −x ; x and x remove from stack and replace with dx
1 0 1 0 1 0
dx dup dx ⇒ Stack
2 2
dx dx * dx =dx×dx; remove both dx from stack and replace with dx
dx 2 $3 y ⇒ Stack
1
dx 2 y $1 y ⇒ Stack
1 0
2
dx y y - dy =y −y ; remove y and y from stack and replace with dy
1 0 1 0 1 0
2
dx dy dup dy ⇒ Stack
2 2 2
dx dy dy * dy =dy×dy; remove both dy from stack and replace with dy
dx 2 dy 2 + sq =dx 2 +dy 2 ; remove both dx 2 and dy 2 from stack and replace
with sq
√
sq sqrt dist= sq; remove sq from stack and replace with dist
dist return value

50

| name | body |
| --- | --- |
| DIST | 4 argc $2 $0 - dup * $3 $1 - dup * + sqrt |

| Stack | token | operation |
| --- | --- | --- |
|  | 4 | 4 ⇒ Stack |
| 4 | argc | Applying the 4 argument values from the stack of the invoking
expression |
|  | $2 | x ⇒ Stack
1 |
| x
1 | $0 | x ⇒ Stack
0 |
| x x
1 0 | - | dx=x −x ; x and x remove from stack and replace with dx
1 0 1 0 |
| dx | dup | dx ⇒ Stack |
| dx dx | * | dx2 =dx×dx; remove both dx from stack and replace with dx2 |
| dx2 | $3 | y ⇒ Stack
1 |
| dx2 y
1 | $1 | y ⇒ Stack
0 |
| dx2 y y
1 0 | - | dy =y −y ; remove y and y from stack and replace with dy
1 0 1 0 |
| dx2 dy | dup | dy ⇒ Stack |
| dx2 dy dy | * | dy2 =dy×dy; remove both dy from stack and replace with dy2 |
| dx2 dy2 | + | sq =dx2+dy2; remove both dx2 and dy2 from stack and replace
with sq
√ |
| sq | sqrt | dist= sq; remove sq from stack and replace with dist |
| dist |  | return value |

<!-- Page 51 -->

# 6 Layers

Table name: layer
Obligatory table: no

### 6.1 Functioning of Layers

By means of the respective layer –function (see sections 2.8.7 resp. 3.9.7) objects can be
assigned to an layer. This allows to assign properties such as visibility, color, etc. simulta-
neously to multiple objects, regardless of their position in the object hierarchy.

### 6.2 Definition of Layers

The properties of 2D layers are exclusively defined by the application.
3D layers are defined via table layer. The definition of layers is optional. For non-defined
layers preset values are used. The values in this table on their part are default values that
can be overwritten by the application.

field- field- description
number name
1 layer_name name of the layer
2 attributes properties

Table 17: Definition of 3D Layers

In the following the individual fields of this table are described in more detail:

(cid:136)
layer_name
This field specifies the name of the layer. The following characters can be used: all
alphanumeric characters, _ (underscore), - (hyphen) and $ (dollar sign).
24
Layer names should conform to the OLAYERS specification .
(cid:136)
attributes
The layer properties are defined in this field by means of predefined functions. The
function calls are formulated in Reverse Polish Notation, i.e., the arguments are stated
in front of the function name.
Currently only the function visible is defined. If the argument of this function has
the integer value 0, then the objects on the layer are invisible. This affects rendering
(real-time, photo-realism), printing and graphics export.

24
VerbandBu¨ro-,Sitz-undObjektmo¨bele.V.: OLAYERS – OFML compatible Layers.

51

| field-
number | field-
name | description |
| --- | --- | --- |
| 1
2 | layer_name
attributes | name of the layer
properties |
