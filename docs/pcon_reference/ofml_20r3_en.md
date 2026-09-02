# ofml_20r3_en

> Auto-generated from ofml_20r3_en.pdf for AI consumption.

---


<!-- Page 1 -->

# OFML – Standardized Data Description Format of the Office

# Furniture Industry

# Version 2.0

# 3rd revised edition

### (cid:13)c

### Copyright 1998 – 2015

### Der Verband Bu¨ro-, Sitz- und Objektmo¨bel e.V. (BSO)

### November 4, 2015

<!-- Page 2 -->

(cid:13)c
Copyright 1998 – 2015
Verband Bu¨ro-, Sitz- und Objektm¨obel e.V. (BSO)
Bierstadter Strasse 3
D-65189 Wiesbaden
www.buero-forum.de

ThescientificsupportandcoordinationofthedevelopmentoftheOFMLdatastandardwasperformedby
Dr. Ing. habil. Ekkehard Beier from the Institute of Practical Informatics and Media Informatics of the
Faculty of Informatics and Automation at the Technical University Ilmenau.
Ekkehard Beier holds the intellectual copyright for the OFML object model, including the scene archi-
tecture, rules, and base interfaces. Referring to this, any scientific, patent-related or in any other way
copyright-related exploitation requires the permission of Ekkehard Beier.

The OFML standard (parts I-III) was developed by EasternGraphics GmbH on behalf of industrial asso-
ciation Bu¨ro-, Sitz- und Objektmo¨bel e.V. (BSO).
EasternGraphicsGmbHholdstheintellectualcopyrightforthesegmentsGlobalPlanningTypes,Product
Data Model, and Planning Environment. The same applies to the OFML Database (ODB), the OFML
Metafile Format EGM, and the OFML 2D Interface. Referring to this, any scientific, patent-related or in
any other way copyright-related exploitation requires the permission of EasternGraphics GmbH.
BasicsyntaxandsemanticsofOFMLarebasedontheCobraprogramminglanguagefromEasternGraphics
GmbH. Copyright (cid:13)c 1995 – 2015 EasternGraphics GmbH and Jochen Pohl.

The OFML standard was developed with great care. Nevertheless, mistakes and inconsistencies cannot
be ruled out. The industrial association Bu¨ro-, Sitz- und Objektmo¨bel e.V. as well as EasternGraphics
GmbH refuse to accept any respective liability in this regard.

<!-- Page 3 -->

# Contents

References . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6

1 Introduction 7

2 Concepts 10
2.1 Types . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
2.2 Entities . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
2.3 Property . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14
2.4 Methods . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14
2.5 Rules. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15
2.6 Categories . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 16
2.7 Initialization . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 16
2.8 Interactors. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 17

3 Basic Syntax and Semantics 18
3.1 Introduction . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 18
3.2 Lexical Structure . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19
3.3 Types . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 25
3.4 Predefined Reference Types . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 30
3.5 Statements . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 43
3.6 Expressions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 51
3.7 Packages and Namespaces . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 64
3.8 Classes . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 69
3.9 Predefined Functions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 73

1

<!-- Page 4 -->

4 Basic Interfaces 77
4.1 MObject . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 77
4.2 Base . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 79
4.3 Material . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 87
4.4 Property . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 89
4.5 Complex . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 94
4.6 Article . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 98

5 Predefined Rule Reasons 103
5.1 Element Rules . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 103
5.2 Selection Rules . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 105
5.3 Move Rules . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 105
5.4 Persistence Rules . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 107
5.5 Other Rules . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 108

6 Global functions 109
6.1 Formatted Output . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 109
6.2 oiApplPaste() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 110
6.3 oiClone() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 110
6.4 oiCollision() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 111
6.5 oiCopy() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 111
6.6 oiCut() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 111
6.7 oiDialog() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 111
6.8 oiDump2String() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 112
6.9 oiExists() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 113
6.10 oiGetDistance() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 113
6.11 oiGetNearestObject() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 113
6.12 oiGetRoots() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 113
6.13 oiGetStringResource() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 113
6.14 oiLink() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 114
6.15 oiOutput() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 114
6.16 oiPaste(). . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 114
6.17 oiReplace() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 115
6.18 oiSetCheckString() . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 115
6.19 oiTable(). . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 115

2

<!-- Page 5 -->

7 Geometric types 117
7.1 OiGeometry . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 117
7.2 OiBlock . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 118
7.3 OiCylinder . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 119
7.4 OiEllipsoid . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 120
7.5 OiFrame . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 121
7.6 OiHole . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 122
7.7 OiHPolygon . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 124
7.8 OiImport . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 125
7.9 OiPolygon . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 126
7.10 OiRotation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 127
7.11 OiSphere . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 128
7.12 OiSweep . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 129
7.13 OiSurface . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 131

8 Global Planning Types 132
8.1 OiPlanning . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 132
8.2 OiProgInfo . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 140
8.3 OiPlElement . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 142
8.4 OiPart . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 148
8.5 OiUtility . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 153
8.6 OiPropertyObj . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 153
8.7 OiOdbPlElement . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 154

9 Types for Product Data Management 156
9.1 OiPDManager. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 157
9.2 OiProductDB . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 160

10 Types of the Planning Environment 164
10.1 The Wall Interface . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 164
10.2 OiLevel . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 164
10.3 OiWall . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 166
10.4 OiWallSide . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 166

3

<!-- Page 6 -->

A Product Data Model 167

B The 2D Interface 169
B.1 Introduction . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 169
B.2 The 2D Object Hierarchy . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 169
B.3 Coordinates . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 170
B.4 Methods . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 170
B.5 Object Types . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 171
B.6 Attributes . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 174

C The 2D vector file format 180
C.1 Introduction . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 180
C.2 data types . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 180
C.3 File header . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 186
C.4 General structured data types . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 187
C.5 Graphic 2D objects . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 188

D External data formats 200
D.1 Geometries . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 200
D.2 Materials . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 201
D.3 Fonts. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 203
D.4 External Tables . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 204
D.5 Text Resources . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 204
D.6 Archives . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 205

E Format Specifications 206
E.1 Format Specifications for Properties . . . . . . . . . . . . . . . . . . . . . . . . . . 206
E.2 Definition Format for Properties . . . . . . . . . . . . . . . . . . . . . . . . . . . . 207

F Additional Types 209
F.1 Interactor . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 209
F.2 Light . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 210
F.3 MLine . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 211
F.4 MSymbol . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 213
F.5 MText . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 214

4

<!-- Page 7 -->

G Applied Notation 216
G.1 Class Diagrams based on Rumbaugh . . . . . . . . . . . . . . . . . . . . . . . . . . 216

H Categories 218
H.1 Interface Categories . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 218
H.2 Material Categories. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 218
H.3 Planning Categories . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 219

I Terms 220

Index 223

5

<!-- Page 8 -->

# References

[GO] EasternGraphics GmbH: GO – Generic OFML types (OFML part II).
[OAM] Verband Bu¨ro-, Sitz- und Objektmo¨bel e.V.: OAM – OFML Article Mappings (OFML Part
VI).
[OAS] VerbandBu¨ro-,Sitz-undObjektmo¨bele.V.: OAS– OFML ArticleSelection (OFMLPart V).
[OCD] Verband Bu¨ro-, Sitz- und Objektmo¨bel e.V.: OCD – OFML Commercial Data (OFML Part
IV).
[ODB] EasternGraphics GmbH: ODB – OFML database (OFML part I).
[OEX] Verband Bu¨ro-, Sitz- und Objektmo¨bel e.V.: OEX – OFML Business Data Exchange (OFML
Part VII).
[Rumb91] J.Rumbaugh et al: Object–Oriented Modelling And Design. Prentice–Hall, New Jersey, 1991

6

<!-- Page 9 -->

# Chapter 1

# Introduction

The motivation for the new standard of office furniture (OFML 1 ) is the result of a series of re-
quirements that could generally not be met with past and present solutions:

• Thenewrequirementsintheareaofplanningandvisualizationof(office)furniturecannotbe
metsufficientlybyCAD-basedsystems. ThemainproblemsofCAD-basedsolutionsaretheir
enormous data size, the poor parameterizability and configurability, insufficient coverage of
product logics, insufficient display quality in the interactive range, complicated operation,
and costly licensing.
• These disadvantages are magnified in the area of marketing-oriented solutions that may, for
example,settheframeworkforusingenduser-orientedsystemsonCD-ROMortheInternet.
• Aplatform-independentand(software)manufacturer-independentdataformatallowsanun-
limitednumberofsoftwaremanufacturerstooffersystemsandsolutionssothatmonopolizing
conditions can be avoided or eliminated.
• The new data format also allows for the implementation of a series of applications that are
compatiblewithrespecttothedatainspiteofadifferentorientation. Inthiswayitispossible
to achieve a compatibility and, therefore, technological uniformity between manufacturer,
trade, and end user systems.

(Traditional)CADsystemscontinuetohavearaisond’tre, especiallythroughtheirabilitiesinthe
designandmanufacturingsector. Consequently,thenewstandarddoesnotlayclaimtoacomplete
removalofexistingCAD-basedsolutions. Instead,acoexistencebetweentraditionalCADsolutions
andthenewstandardisaimedat. Thecoexistenceshouldbeimplementedonthebasisofdirectly
compatible data formats or suitable conversion tools.
In particular, the OFML standard offers the following features:

• consistent application of the object-oriented paradigm,
1
Office Furniture Modeling Language

7

<!-- Page 10 -->

• conversionofconceptsofsemanticmodelingtoachieveamatchofvirtualobjectswithactual
products,
• combination of geometric, visual, interactive, and semantic features of real products in a
uniform and holistic data model,
• mapping of real configuration logics and parametrics,
• independence of system or interface platforms, and
• independence of a concrete runtime environment.

The OFML standard consists of the following parts, each covering different aspects of OFML
datacreationorvariousapplicationprocesses. Thepartsaremoreorlessstronglylinkedtogether,
primarily by cross-reference such as article numbers and type identifiers.

1. OFML database (ODB)
The OFML database [ODB] defines a table-based interface for description of hierarchical
geometries in 2D and 3D.
2. Generic Office library (GO)
The class library GO [GO] provides basic functionality for the scope of the office furniture
industry.
3. Object model
This part defines a complete programming language, basic interfaces of OFML types, prede-
fined rule reasons, global (type-independent) functions as well as a set of base types. On the
basis of this object model arbitrarily complex data can be created and external commercial
data can be integrated.
4. OFML Commercial Data (OCD)
OCD [OCD] defines a set of tables for the creation of (commercial) product data which is
needed and exchanged within business processes of the furniture trade. Primarily, OCD
is supposed to cover tasks like configuration of complex articles, price determination and
creation of offer resp. order forms.
5. OFML Article Selection (OAS)
OAS[OAS]describesaformatforstructuredrepresentationandselectionofarticlesindigital
catalogs.
6. OFML Article Mappings (OAM)
Thetablesspecifiedinthispart[OAM]areusedtodefinemorecomplexrelationshipsbetween
data that has been created according to the specification of various other OFML parts.
7. OFML Business Data Exchange (OEX)
OEX [OEX] describes a format for the electronic exchange of business documents, such as
purchase orders and invoices.

8

<!-- Page 11 -->

Parts I-III were developed by EasternGraphics GmbH on behalf of industrial association Bu¨ro-,
Sitz-undObjektm¨obele.V.(BSO).Allotherpartsarespecifiedbythestandardizationcommittee
of the BSO.
In the following, in this document only the object model (part III) is described. All other parts
are specified in separate documents (see references above).
This document is structured as follows:

Introduction and Overview

• Thischapterdescribesmotivation,featuresandthepartsoftheOFMLstandard,andpresents
an overview of the document.
• Chapter 2 summarizes the relevant concepts and metaphors of the object model.

OFML part III (Object model)
• Chapter3describesthebasicsyntaxandsemanticsoftheprogramminglanguageunderlying
OFML.
• Chapter 4 presents an overview of the basic interfaces that form the basis for the concrete
types of the standard.
• Chapter 5 describes the set of predefined rule reasons.
• Chapter 6 describes the set of type-independent functions predefined for OFML.
• Chapters 7 and 8 describe the complete set of OFML basic types.
• Chapter 9 specifies types that are required for access to external product data.
• Chapter 10 describes the generic types of planning environments.

Appendix

• Appendix A describes a generic format for the external writing of product data.
• Appendix B documents an explicit 2D programming interface available in OFML.
• Appendix C documents a metafile format that is used by OFML to describe 2D vector
graphics.
• Appendix D documents the set of external data formats and their application.
• Appendix E describes the formats relevant for using properties.
• Appendix F describes the additional types that may be applied within the framework of
OFML.
• AppendixGdescribesthenotationalconventionsusedwithintheframeworkofthisstandard.
• Appendix H describes the categories predefined within the framework of this standard.
• Appendix I defines the most important terms used within the framework of this standard.

9

<!-- Page 12 -->

# Chapter 2

# Concepts

This chapter contains a description of the basic OFML concepts. All concepts documented in the
subsequent chapters are invariably based on these fundamentals. As such, an understanding of
these concepts is a necessary basis for additional dealings with the standard.

# 2.1 Types

1
Atype isacombinationofentitiesofthesamekind. Atypedefinesthefollowingfortheseentities:

• a set of methods,
• a set of rules,
• a set of instance variables, and
• exactly one initialization function.

Eachinstancebelongstoexactlyoneimmediatetype. Atypemayhaveonlyonedirectsupertype;
the features are inherited from this super type in a certain way. As such, a type should always be
considered in connection with its (direct or indirect) super types.
Atypenamemustbeuniquewithinthedefiningmodule. Atypenamemustalsobeuniquewithin
the global context. This is accomplished using a uniform name prefix or by integrating it in a
name range.
A type is either abstract or concrete. An abstract type cannot be used to form entities.

Example: The concept of a carcass cabinet can be interpreted as type. A certain carcass cabinet (type)
that also features a corresponding order number is one example of a concrete type. The generalization of
all carcass cabinet types is an example of an abstract type.
1 Thetermstypeandclassaresynonymous.

10

<!-- Page 13 -->

The term interface resembles the term type with respect to its use within OFML. However, the
following exception exists:

• An interface is a descriptive tool and does not necessarily correspond to a type.
• An interface is not derived from another interface.
• The name of an interface does not receive a name prefix.

# 2.2 Entities

Aninstance 2 isaconcreteembodimentofatype. Itdistinguishesitselffromotherentitiesthrough
its identity which is implemented through a hierarchical name. In general, it also distinguishes
itself through the assignment of the instance variables of which it always possesses its own copy.

Example: Twocarcasscabinetswiththesameordernumberarereferredtoasentitiesofthesametype.
Theyhavecommonfeatures,suchasthesameordernumberorthesamephysicaldimensions. Theydiffer
from each other, for example, through the or the material design.

In general, entities should be topologically independent. This means:

• An instance should not store any object references in its instance variables, that is, name
references to objects.

Example: This would be violated if one instance remembers a certain other instance (e.g., on the
same topological level).

• An instance cannot assume that its topological ancestors are from a certain type.

Example: In the course of the temporary generation of entities, any random instance can be an
ancestor of an instance.

Underspecialcircumstances,theserulesmaybeviolated. Theresultingconsequencesmayinclude:

• loss of ability to save and
• incorrect behavior during copying and inserting.
2
Thetermsinstanceandobjectaresynonymous.

11

<!-- Page 14 -->

### 2.2.1 Children

An instance can have a number of children. A child is an instance that exists in the name space
of the father object. The father-child-relation is described as follows in OFML:

• Childrenaregenerated,modifiedanddeletedduringruntime. Assuch,thenumberofchildren
is time-dependent.
• The father must be indicated at the generation of an instance and cannot be changed after-
wards.
• Deleting an instance always results in the deletion of its children.
• A child inherits the features of its father in a certain way. For example, the complete global
space modeling of the child results from interlinking the global space modeling of the father
and the local space modeling of the child.
• A child knows its father. This fact may be used for an upward traversing within the scene.
• A father knows his children. This fact may be used for a downward traversing within the
scene.

Entities are placed in a scene. Based on the features of the father-child relation described above,
the resulting scene topology is a set of trees.
Thesetofelementsisasubsetofthesetofchildren. Anelementisaspecialchildwhosegeneration
and removal can be controlled via rules (see below). Thus, every element is a child, but not every
child is an element. Elements are normally used for accessible components of a complex instance.
Non-elements are normally components of a combined instance that evade access by the user.

Example: Thechildrenofacarcasscabinetarestringer,backwall,base,front,andbuilt-incomponents.
The shelves are elements that can be inserted, moved, and deleted separately.
The individual boards of the carcass, on the other hand, are non-elements since there is usually no access
to them.
Moving a shelf is controlled by the father of the shelf, that is, the carcass cabinet (rasterization, avoiding
collision,sectormonitoring). Theshelfmust,therefore,knowitsfathertotransfercontroloverthedesired
move to him.
Ifthecarcasscabinetismoved,thechildrenmustbemovedaccordingly. Forthisreason,thechildrenmust
be known to the father.
If a carcass cabinet is deleted, all shelves, etc. of this carcass cabinet are automatically deleted.

Syntactically, children are treated like instance variables (Section 3.8.4). Since they are created
dynamically, access by name within methods must be carried out using a prefixed self in addition
to an access operator, e.g., for the child b5: self.b5.

12

<!-- Page 15 -->

### 2.2.2 Instance Identity

The identity of an instance is implemented by means of a hierarchical name space. Every name
withinthisnamespacecorrespondsbiuniquelytoatopologicalpositionintheobjectworld(scene).
The name of an instance results from the following rule:

Name : Name(Father) ’.’ LocalName
| LocalName

LocalName : Character
| LocalName Character

Character : ’A’ - ’z’ | ’0’ - ’9’ | ’_’

Consequently, the name of an instance results from the interlinking of the name of the father, if
one exists, via a point-to-point operator with the local name.

Example:

• env – is the name of a fatherless root object.
• env.sky – is the name of a child of env. The local name is sky.
• env.sky-1 – is an invalid name.
• env.sky 1 – is a valid name.
• env.env – is the name of a child of env and designates a sibling object of env.sky at the same time.
• top – is the name of another fatherless root object.
• – is not allowed, neither as global nor as local name.

The following absolute names are predefined:

• t – is the root object that combines the planning hierarchy.
• e – is the root object that combines the environment hierarchy, if necessary.
• m – is the root object that combines the dimensioning hierarchy, if necessary.

At the same time, additional root objects can be defined for specific applications.

Restriction: The(local)namesintheforme<n>,wherebynisanaturalnumber,arereservedandmay
not be assigned explicitly. These names are assigned automatically during the generation of elements.

13

<!-- Page 16 -->

### 2.2.3 Instance Variables

A type (in combination with its super types) defines a set of instance variables of which each
instanceownsitsowncopy. Theconventionsdictatethatthenameofaninstancevariableconsists
of the prefix m plus a non-empty set of words that each start with a capital letter. In addition,
the name of an instance variable is a valid designator as defined by the basic syntax (Chapter 3).
Examples for valid names of instance variables include: mWidth and mIsCutable.
Aninstancevariablethatisdefinedinatype,maynotbere-definedinaderivedtype. Inaddition,
an instance variable must at least be initialized in the type in which it was defined. Direct access
to an instance variable is permitted only within the defined type. An external access can be
accomplished only via respective methods.
Instance variables may also be defined via interfaces.

Example: An instance variable could be used to define whether a roll container features an espagnolette
or not.

# 2.3 Property

A property (property) is a special instance variable that represents an implicit interface of an
instance to the (graphical) user interface. A property has a type, a symbolic designator, and an
actual value. In most cases, a discrete value range is assigned to a property. Additional optional
features of a property include the initial assignment as well as usually for geometric properties
the minimum value and the maximum value.
Thecurrentembodimentofthesetofpropertiesofaninstancegenerallycorrespondstoaconcrete
article number.
Properties are read out by a (property editor) and can interactively be set by this editor.
The concept of properties allows for combining any large set of configurations that correspond to
exactly one article number each by using a type that covers all possible configurations, while also
considering dependencies between individual properties.

Example: The (interactive) configurability of a carcass cabinet can be implemented using the three
properties width, height, and depth. In general, a manufacturer-specific discrete value range is defined for
each of these properties, e.g., for the width: 600 mm, 800 mm, 1000 mm, and 1200 mm.

# 2.4 Methods

A type (in combination with a super type) defines a set of methods or type-specific functions
(Section 3.8.4). The name of a method results from a non-empty set of words that all start with a
capital letter, except for the first one. In addition, the name of a method is a valid designator as

14

<!-- Page 17 -->

definedbythebasicsyntax(Chapter3). Examplesforvalidnamesofmethodsinclude: selectable()
and isSelectable().
A method that is defined in a type, may be redefined in a derived type only if it features the same
signature. In the case of OFML this means that number, format, and semantics of the parameters
must be identical.
Methods may also be defined via interfaces.

Example: Thestopchangeofadoorcanbeimplementedviaacorrespondingmethod. Thismethodthen
implements the stop change without the internal design of the door being known to the outside.

# 2.5 Rules

Atype(incombinationwithitssupertypes)definesasetofrules. Aruleisaproceduralconstruct
that is defined analogous to a method within the range of a type. A rule differs from a method
through the following features:

• A rule is a type-dependent construct whose signature consists of a rule reason in form of a
predefinedoruser-definedsymbols, anoptionalspecificruleparameter, andaformalparam-
eter.
• The return value of a rule is of type Int. The value 0 signals the successful processing of the
rule. The value −1 denotes a failed rule. The user can be informed about the failure of a
rule, if required, through the use of a corresponding text message.
• Several rules may exist for one and the same rule reason within a type or a hierarchy of a
type.
• A rule cannot be overwritten, for example, by a rule with identical reason in a derived type.
• A rule is classified as anterior rule or posterior rule. An anterior rule is called before an
action is performed. The failure of an anterior rule prevents the corresponding action from
beingperformed. Aposteriorruleiscalledafteranactionwasperformed. Consequently,this
action cannot be prevented. However, the effect of the action can be reversed by applying a
suitable counter-action.

For an action that was performed or still needs to be performed and a given instance, a list is first
compiled that contains the rules defined by the type and its super type for the respective reason.
The order of the rules in the list corresponds to the derivative hierarchy of the respective type.
That is, a rule defined by a certain type is located in the list ahead of a rule defined by a derived
type. The list of rules is then processed sequentially. Processing is interrupted provided that a
rule has failed. In this case, and if the rule was an anterior rule, the corresponding action is not
performed.
The rule reasons predefined in OFML are documented in chapter 5.

15

<!-- Page 18 -->

Example: Inserting any object, e.g. in a carcass cabinet, can be controlled by a corresponding anterior
rule. For example, the carcass cabinet can ensure using this rule that only shelves of a certain type and a
certain number can be inserted.
Movinganobjectcanbecontrolledbyacorrespondingposteriorrule. Forexample,ifthemoveresultsin
a collision, the move should subsequently be corrected accordingly.

# 2.6 Categories

A category is a classification of types or entities that results from a certain philosophy.
Categoriesrepresentanextensiontotheconceptoftypes: typesthatbelongtoacommoncategory
do not have to be derived from a common type. In addition, a type can be assigned to several
categories.
The association with a category is determined by each type itself. It can be determined for an
instance whether its type or super types belong to a certain category (Section 4.1).
The concept of categories can be used to circumvent the limitation of simple inheritance of types
in the classification of entities based on orthogonal categorization criteria. It is also useful if rolls
must be modeled.

Examples Material and planning categories (see Appendix H).

# 2.7 Initialization

The initialization of an instance is carried out via the initialize() procedure. The functions of
initialization are essentially the initialization of instance variables and the generation of child
objects. The following properties refer to the initialization:

• Exactly one initialization function exists for each type. It is labeled initialize().
• Within the implementation of the initialization function, the initialization function of the
direct super type is called first.

The standard signature for the initialization function is as follows:

initialize(pFather(MObject), pName(Symbol)) → MObject

Where pFather is the father object and pName the local name of the new object to be created.
The return value of the initialization function is a reference to the created object.
If required, additional random parameters can be defined for the initialization function of a type.
However, this is only allowed for abstract types or internal components. All types that can be
instantiated interactively must conform with the standard signature of the initialization function.

16

<!-- Page 19 -->

Example: Theinitializationfunctionofacarcasscabinetmustcreateandparameterizethecorresponding
children (stringer, base, back wall, etc.). However, the creation of shelves can be done interactively at a
later time.

# 2.8 Interactors

InOFML,interactorsrepresentaspecialtypethat, incontrasttomostotherOFMLobjects, does
not represent an object of the real world. Interactors are objects that exist only at runtime and in
a simple way allow the user actions that go beyond elementary manipulations such as translation
and rotation. Corresponding examples are the marking of connection points or ”handles” for
interactively changing the size of an object.
Interactors distinguish themselves with respect to other objects through the following features:

• They are not stored persistently.
• They cannot be selected directly. The attempt to select an interactor triggers the INTER-
ACTOR rule at the father (Section 5.5).
• Interactors cannot cause a collision.
• They are ignored during photorealistic output and export into an external data format.

Example: Designs can be mounted to an organizational wall at different positions. If interactors are
defined for these positions, the user can interactively select the desired mounting point.

17

<!-- Page 20 -->

# Chapter 3

# Basic Syntax and Semantics

# 3.1 Introduction

ThischapterdescribestheprogramminglanguagefundamentalsofOFMLwhosesyntaxisoriented
totheprogramminglanguagesC,C++,andJava. Fromasemanticspointofview,OFMLissimilar
to Smalltalk or Python since it is based on a dynamic type concept.

### 3.1.1 Syntax Representation

A slightly modified version of the familiar Backus-Naur form is used in this document to repre-
sent syntax. The following typographical conventions apply: reserved identifiers, characters and
character combinations are represented in Schreibmaschine. All other grammatical symbols are
written in kursiv. Multiple alternatives for the right side of a production are separated either by
a linebreak and indent or by ”‘|”’ within a line. Optional symbols are identified by a subscript
”‘opt”’:
{ stmt }
opt

### 3.1.2 Implementation

The language definition of OFML assumes that an OFML program is converted into a processible
1
form by a compiler . This takes place in two phases:

1. The translation o f al definitions to module and class levels. In this step, executable state-
ments and definitions within compound statements are translated only partially or not at
all.
1 Thiscanbe,forexample,bytecode,machinecodeorvectoredgraphs.

18

<!-- Page 21 -->

2. The translation of all executable statements and definitions within compound statements.
Depending on implementation, this step can be delayed for each compound statement until
just before it is first processed.

The purpose of this division is to handle translation units that reference each other through vari-
ables, functions or classes defined by them. Translation units that form a loop based on the
super-classes they reference are not permitted.
Another reason for the division is to partially distribute the time needed to translate the program
to the runtime, which can be achieved through delayed translation of compound statements.

### 3.1.3 Program Structure

An OFML program consists of one or more translation units. Each unit represents a sequence of
characters of the character set (see Section3.2.1), which can exist in the form of a file and string.
Each translation unit is conceptually closed by the EOF (end of file) character. This character is
not a part of the source text, but instead is used only to represent the end of the input stream in
the syntax description.

# 3.2 Lexical Structure

The first pass during processing reads a sequence of input characters and produces as the result a
2
series of lexical symbols (Token) .

### 3.2.1 Character Set

ThecharactersetprocessedbythecompileristhesetofprintableASCIIcharacters,i.e.8-bitchar-
acters with an integer value from 32 to 126 and the control characters mentioned in Section 3.2.1.
Exceptions are permitted only in comments and literal characters and character string constants.
Inthelattercase,theprogrammerisresponsibleforensuringthatthecorrespondingcharactersare
processed correctly by the runtime environment. In the following, non-printable ASCII characters
are represented by hexadecimal numbers in the manner common to C; the grammatical any-chars
symbol denotes any sequence of characters from the entire character set of the implementation.

Alphanumeric Characters

The following productions define letters (alpha), numbers (num) and alphanumeric characters
(alnum). Note that the underscore also belongs to the letters.
2
TheEnglishtermisusedheretoavoidmixupswithOFMLsymbols.

19

<!-- Page 22 -->

alpha:
A | B | C | D | E | F | G | H | I | J | K | L | M
N | O | P | Q | R | S | T | U | V | W | X | Y | Z
a | b | c | d | e | f | g | h | i | j | k | l | m
n | o | p | q | r | s | t | u | v | w | x | y | z

num:
1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 0

alnum:
alpha | num

Spaces

Thefollowingcharacters,assequencesorcombinedwithcomments(seeSection3.2.1)formZwischen-
r”aume (white-space): horizontal tabs (HT), linebreaks (NL), vertical tabs (VT), formfeeds (FF),
carriage returns (CR) and spaces (SP). If an identifier or keyword follows an identifier, a keyword
or a symbol, both have to be separated by a white space. The same applies to integer constants
(excluded character constants) and floating-point constants. Otherwise, white spaces have no
meaning, but are used only to improve program readability.

white-space:
HT | NL | VT | FF | CR | SP | comment

Comments

Commentsbeginwiththe//charactercombinationandendwithalinebreak(NL),carriagereturn
(CR) or a combination of the both.

comment:
// any-chars eol
eol:
CR | NL | CR NL | NL CR

The # sign is different: If it occurs at the start of the first line of a file, the rest of the line is
interpreted as a comment.

20

<!-- Page 23 -->

### 3.2.2 Token

Therearevariousclassesoftoken: keywords,identifiers,literalconstants,operatorsanddelimiters.

### 3.2.3 Identifiers

ident identifiers begin with a letter, which can be followed by any number of alphanumeric char-
acters in sequence.

ident:
alpha alnum-seq
alnum-seq:
alnum alnum-seq
opt

The keywords mentioned in the next section cannot be used as identifiers.

### 3.2.4 Keywords

The following keywords are reserved and cannot be used as identifiers:

abstract break case catch class
continue default do else final
finally for foreach func goto
if import instanceof native operator
package private protected public return
rule self static super switch
throw transient try var while

### 3.2.5 Literal Constants

OFML includes literal constants of the following types (see Section 3.3): integers, floating-point
numbers, character strings and symbols.

constant:
integer-constant
float-constant
string-constant
symbol-constant

21

<!-- Page 24 -->

Integer Constants

Integerconstants(integer-constant)canbespecifiedinthreedifferentnumericalsystems: decimal,
octal and hexadecimal. Because OFML does not distinguish character types, character constants
(character-constant) are also interpreted as integers.

integer-constant:
dec-constant
oct-constant
hex-constant
character-constant

Decimal numbers begin with a digit unequal to 0 , followed by any sequence of digits:

dec-constant:
dec-start dec-rest
opt
dec-start:
1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9
dec-rest:
num dec-rest
opt

Octal numbers begin with the digit 0, followed by any sequence of digits from to 7:
0

oct-constant:
0 oct-rest
opt
oct-rest:
oct-num oct-rest
opt
oct-num:
0 | 1 | 2 | 3 | 4 | 5 | 6 | 7

Hexadecimal numbers begin with the 0x or 0X character string, followed by any sequence of digits
and the letters A to Z and a to z:

hex-constant:
hex-start hex-rest
hex-start:
0X | 0x
hex-rest:
hex-num hex-rest
opt
hex-num:
num | A | B | C | D | E | F | a | b | c | d | e | f

An integer constant must be smaller or equal to the largest representable value in the implemen-
tation. Otherwise, an error is generated during the translation.

22

<!-- Page 25 -->

Character constants consist of a character enclosed in single quotation marks ”‘ ”’:
’

char-constant:
’ char-char ’

The number of characters allowed in character constants is indicated by char-char . The single
quotation mark itself is not allowed in character constants, nor are linebreaks. To represent these
and other special characters, use the escape sequences described in Section 3.2.5.
The value of a character constant is the numerical value of the character in the character set of
the runtime environment.

Floating-point Constants

Floating-point constants begin with an integer part, followed by a decimal point, the broken part
and the exponents. The exponent consists of the E or e character, an optional +/- sign and an
integervalue. Eithertheintegerorbrokenpart,butnotboth,canbeomitted. Furthermore,either
the decimal point or the exponent can be omitted.

float-constant:
dec-rest . dec-rest float-exp
opt
dec-rest . float-exp
opt
. dec-rest float-exp
opt
dec-rest float-exp
float-exp:
exp-char sign dec-rest
opt
exp-char:
|
E e
sign:
|
+ -

Ifanunderflowoccursduringconversionofthefloating-pointconstantsintheInternalrepresenta-
tion, the value of the constants is 0.0. If an overflow occurs, it becomes Float::HUGE_VAL. If the
accuracy of the floating-point constants is greater than supported by the internal representation,
excess positions are ignored.

Constant Strings

Constant strings (string-constant) consist of a sequence of characters enclosed in single quotation
marks (”‘ " ”’). The quotation mark itself is not allowed in character strings. To represent this and
other certain special characters, use the following escape sequences:

23

<!-- Page 26 -->

\a bell character (BEL)
\b backspace (BS)
\t horizontal tab (HT)
\n linebreak (NL)
\v vertical tab (VT)
formfeed (FF)
\f
carriage return (CR)
\r
quotation mark
\"
single quotation mark
\’
backslash
\\
oct-rest octal character code
\
\x hex-rest hexadecimal character code

The number of constant character string allowed is indicated by string-char .
The oct-rest octal character code consists of a sequence of up to three octal digits and ends with
the first not-octal character. The hex-rest hexadecimal character code consists of a sequence of
any number of hexadecimal digits and ends with the first not-hexadecimal character.
If an overflow in a character occurs during translation while converting an octal or hexadecimal
character code, an error is generated.

string-constant:
"string-char-seq
"
opt
string-char-seq:
string-char string-char-seq
opt

Literal Symbols

Literal symbols in OFML always begin with the special character ”‘@”’, directly followed by a
3
character string, which passes the rules for identifiers.

symbol-constant:
@ident

### 3.2.6 Operators

The following tokens are handled by OFML as operators:
3
Byusingthesymbol(...) constructor,itispossibletogeneratesymbolsfromanycharacterstring;seeSection
3.3.3.

24

<!-- Page 27 -->

operator:
. | ( | [ | ++ | -- | ! | !! | ~ | $
* | / | % | + | - | << | >> | >>> | <
<= | >= | > | == | != | ~= | <? | >? | &
^ | | | && | || | => | ? | : | *= | /=
| | | | | | | |
%= += -= &= ^= |= <<= >>= >>>=
| | | |
= , @( :: instanceof

### 3.2.7 Delimiters

The following tokens in OFML represent delimiters:

delimiter:
:: | { | } | ; | ) | ]

# 3.3 Types

OFML is a dynamically typified language, meaning that the type of a variable or expression
generally is not known until runtime.
Apartfromtheclassdefinition, therearenospecialsyntacticalconstructsfortypesOFML.Types
are objects and, as such, are also stored in variables like all other objects. Within the framework
of the operations defined for types, they can be handled like any other object. Mainly this means
that they can be assigned, passed to functions and called.
The two basic kinds of types in OFML are the simple types and the reference types. Simple types
are the numerical types, the symbol type and the Void type. The reference types are predefined
reference types or user-defined classes.

### 3.3.1 Objects and Variables

Anobjectisaninstanceofaclass. Itisgeneratedbythecallingofthecorrespondingclass. Objects
are accessed via references.
A variable is a memory region where the value of a simple type or the reference to an object of a
reference type is stored.
There are two kinds of variables, named and unnamed. Named variables are all the variables that
can be specified by an identifier. Unnamed variables have to be accessed using an operator (such
as the index operator).
[]

25

<!-- Page 28 -->

### 3.3.2 Operations for all Types

All types inherit from the Object root type. This makes the following operations available to all
types:

• The constructor. This is a function (see Section 3.6.3) that requires a type-specific number
of parameters and, for simple types, returns a new value of the type or, for reference types,
a reference to a newly generated object.
• The assignment via the = operator (see Section 3.6). Here, the variables on the left side of
the assignment operator are assigned the value from the result of the expression on the right
side. If the result has a reference type, the reference is assigned, without a new instance of
the referenced object being created.
• Thepassingasargumenttoafunction. Thistakesplaceaccordingtotherulesofassignment
by the = operator, where the argument is assigned the corresponding, formal parameters of
the function.
• The comparison using the == or != operator. For simple types, the values themselves are
compared, while, if not otherwise defined, for reference types, object identity is verified.
• The verification of the type using the instanceof operator.

### 3.3.3 Simple Types

All simple types are defined in the ::cobra::lang package.

The Type
Void

The Void type is always usedif a variable is to have a non-concrete value. The only possible value
for the Void type is NULL.

Integers

4
IntegersarerepresentedbytheInttypeandhaveasizedeterminedbythemachine . Theavailable
value range can be found using the static Int::MIN_VALUE member (the amount being the largest
representable negative value) and Int::MAX_VALUE (largest representable positive value).
The Int() constructor can be called either without arguments (in which case the value of 0 is
returned) or with an argument with one of the following types:

• Int : The value of the argument is copied.
• Float : A conversion from Float to Int is carried out and any fractional part is cut off. If
the available value range is exceeded, the result is undefined.
4
With most currently distributed architectures, these are 32-bit numbers in with complement of two. The
availablevaluerangeis[−2147483648,2147483647].

26

<!-- Page 29 -->

• : A number that is unambiguously assigned to the symbol is returned.
Symbol
• String : An attempt is made to interpret the string as an integer constant. If, in doing so,
the rules specified in Section 3.2.5 are violated, an exception is triggered (see Section 3.5.3).

The following operators (see Section 3.6) can be applied to the Int type.

• The arithmetical operators: the + and - operators in prefix and infix form, the ++ and --
operators in prefix and postfix form and the * , / and % infix operators.
• The relational operators: == , != , < , > , <= , >= , <? and >? .
• The logical operators: ! and !! .
• The bitwise operators: , , , , , and .
& | ^ ~ << >> >>>
• All combined assignments that can be formed using the above operators.

Floating-point Numbers

Floating-point numbers are represented by the Float type and have a size determined by the
5
machine . The available value range can be found using the static Float::MIN_VALUE member
(the amount being the largest representable negative value) and Float::MAX_VALUE (largest rep-
resentable positive value).
Depending on implementation, the static Float::HUGE_VAL member is either infinite positive or
the largest representable positive value. It is used by arithmetical operations on floating-point
values, sometimes with a minus sign, to signalize an overflow.
The Float() constructor can be called either without arguments (in which case the value of 0.0 is
returned) or with an argument with one of the following types:

• Float: The value of the argument is copied.
• Int: A conversion from Int to Float is carried out.
• String: An attempt is made to interpret the string as a floating-point constant. If, in doing
so, the rules specified in Section 3.2.5 are violated, an exception is triggered (see Section
3.5.3).

The following operators (see Section 3.6) can be applied to the type.
Float

• The arithmetical operators: the + and - operators in prefix and infix form, the ++ and --
operators in prefix and postfix form and the *, / and % infix operators.
• The relational operators: == , != , < , > , <= , >= , <? and >? .
• The logical operators: and .
! !!
• All combined assignments that can be formed using the above operators.
5 −308
Withmostcurrentlydistributedarchitectures,theamountofthesmallestrepresentablenumberis±2.2·10 ,
308
thelargestis±1.8·10 andtheaccuracyis15decimalplaces.

27

<!-- Page 30 -->

Arithmetic and Type Conversion

Depending on the types of the operands, arithmetical calculations are carried out either in Int
or Float . Float is used if at least one of the operands is a Float type, except for combined
assignments, in which an Int type value is located on the left side.
Implicit type conversions for numerical types occur under the following conditions:

• Ifoneoftheoperandsisofthe Int typeandthecalculationtakesplacein Float ,theoperand
is converted to Float .
• Ifoneoftheoperandsisofthe Float typeandthecalculationtakesplacein Int ,theoperand
isconvertedto Int . Anyfractionalpartiscutoff. Ifanoverflowoccursduringtheconversion,
the result is undefined.

The following rules apply to calculations in Int :

• The complement of two is used for the internal representation of integer values.
• The result is undefined if it is not representable in a value range of Int. Addition and
subtractionoperationsrepresentexceptions,forwhichtheresultcomesfromthelowest-value
bit of an integer value of sufficient size.
• Division by 0 triggers an exception.

The following rules apply to calculations in Float:

• If the exact result cannot be represented, either the next higher or next lower representable
6
value is applied, depending on implementation .
• The amount of the result is Float::HUGE_VAL if it is not representable in the value range of
Float due to an overflow. The +/- sign corresponds to the +/- sign of the correct value.
• Theresultis0ifitisnolongerrepresentableinthevaluerangeofFloatduetoanunderflow.
Whether the +/- sign is preserved is dependent on implementation.
• Anexceptionistriggerediftheoperandisnotwithintherangeofdefinitionoftheoperation.

Symbols

Symbols represent the dynamic counterpart to numeration constants in statically typified lan-
guages. Internally, they are represented by unique integers, which, using the Int() function, are
also available externally (see Section 3.3.3). With this representation, very fast comparison of
symbols is attainable (in contrast to string comparison).
6
The direction of rounding can differ from operation to operation and is not dependent on the amount of the
differencetothenextlowerornexthigherrepresentablevalue.

28

<!-- Page 31 -->

In various instances of an OFML program, the conversion of the same string to a symbol can
lead to variously applied integers for the internal representation. Due to this, the outcome of
comparisons on symbols that are based on an order is not reproducible in various instances of an
OFML program.
The Symbol() constructor demands an argument with one of the following types:

• Symbol : The value of the argument is copied.
• String : The string (without the leading @ ) is converted to a symbol. The @foo and
Symbol("foo") expressions are thereby equivalent. This method also makes it possible
to convert strings into symbols that do not meet the requirements for identifiers, such as
Symbol("500 Motels") .

The following operators (see Section 3.6) can be applied to the Symbol type.

• The == , != , < , > , <= , >= , <? and >? relational operators.

### 3.3.4 Reference Types

Automatic Garbage Collection

ThelanguagedefinitionofOFMLrequirestheimplementationofanautomaticgarbagecollection.
Objects of reference types are generated implicitly when the constructor is called (see exception
below). Thereisnowayofreleasingobjectsexplicitly. Instead,theycanbereleasedautomatically
bythesystemassoonasnomorereferencestotheobjectexist. However,whenandifobjectsthat
7
are no longer referenced are released is not fixed .
The language definition makes the manner of implementation of the automatic garbage collection
optional.

Operators to Reference Types

The behavior of operators, which can be used within expressions, is firmly defined for the simple
types. If the operand of a unary operator or the left operand of a binary operator delivers a
reference type, an instance-oriented method, specific to the operator, is called for the reference
type. These methods are freely definable for classes. Exceptions are the $ (symbol resolution
operator), ! (logical negation), instanceof (type verification), >? (maximum), <? (minimum),
7 This differs greatly from the algorithm used for automatic garbage collection. When using reference counters,
objectsaregenerallyreleasedassoonastherearenomorereferencestothem. However,agarbagecollectionbased
onlyonreferencecountersdoesnotreleasedatastructureswithcycles. Duetothis,theprogrammerhastobreak
suchcyclesbeforethelastreferencetosuchadatastructureisreleased.
Othermethods, forwhich, basedonaknownnumberofreferencedobjects, allreachable(thusreferenced)objects
aredetermined,delaythereleaseofobjectsthatarenolongerreferencedand,undercertaincircumstances,donot
releaseallobjectsifconservativealgorithmsareused.
Acombinationofbothmethodsisalsoconceivably.

29

<!-- Page 32 -->

(logical AND), (logical OR), (conditional expression), (assignment) and (comma
&& || ?: = ,
operator) operators, whose behaviors either are firmly preset for reference types, are mapped to
other operators or fundamentally cannot be applied to reference types.
The operator methods to be used in class definitions are described in Section 3.6 below their
corresponding operators.

Sequence Types

Sequence types are all of the reference types that can be seen as sequences of objects. For this to
be the case, they have to meet the following conditions:

• The size() method must be defined and return a nonnegative size Int value.
• The operator[](pIdx(Int)) and operator[](pIdx(Int), pValue(Object)) index operators must be
defined for each pIdx integer index within the range of [0,size).
• The sequential access via the index operators, forward or backward, should require constant
time.

Of the predefined types in OFML, String, Vector and List are sequence types.

# 3.4 Predefined Reference Types

The following sections describe the predefined reference types in OFML; user-defined classes are
described in Section 3.8.
All predefined reference types are defined in the ::cobra::lang package.

### 3.4.1 The Metatype

### Type

All types, including the Type type, are instances of the Type type.
Type names OFML are variables having a reference to an instance of Type.
Thefollowingoperators(seeSection3.6)andmethods(seeSection3.8.4)canbeappliedtoinstances
of Type:

operator()(parameters) → Object
The function call operator defined for all types is called a constructor. The constructor
generates an instance of the type for which it is called and calls the initialize() method
for the instance if it exists. The arguments passed to the constructor are forwarded to the
initialization method.
getName() → Symbol
The getName() method returns the simple name of the type as a Symbol .

30

<!-- Page 33 -->

getFullName() → String
The getFullName() method returns the fully qualified name of the type as a string.
subClassOf(pType(Type)) → Int
The subClassOf() method returns 1 if the type for which it was called is either identical to
the type passed as an argument or is derived from this type. Otherwise, the value returned
is 0. If the argument is not of the Type type, an exception is triggered.

### 3.4.2 Functions

Functions are represents in OFML by the Func and CFunc types. Func is the type for functions
defined in OFML, while CFunc is the type for predefined functions. In addition to the operators
that are available to all types (see Section 3.3.2), Func and CFunc implement the ”‘ () ”’ function
call operator.

### 3.4.3 Character Strings

CharacterstringsarerepresentedbytheStringtypeandarerepresentedInternallybyasequence
of 8-bit values, where each value corresponds to one character. Whether the null character (’\0’)
can be a component of a string depends on implementation.
TheString()constructorcanbecalledeitherwithoutarguments(inwhichcasetheemptystring,
"", is returned) or with an argument with one of the following types:

• String: A copy of the string passed as an argument is created.
• Symbol: Anewstringisgenerated,thecontentofwhichisequivalenttothestringrepresented
by the symbol.
• Int,Float: Anewstringisgenerated,whichcontainstheresultoftheconversionofnumbers
in a string.

A string constant in an expression causes an implicit call of the String() constructor, for which
the string is passed as an argument.
The following operators (see Section 3.6) and methods (see Section 3.8.4) can be applied to the
type:
String

operator==(pString(String)) → Int
operator!=(pString(String)) → Int
operator<(pString(String)) → Int
operator<=(pString(String)) → Int
operator>=(pString(String)) → Int
operator>(pString(String)) → Int
The result is 1 if the character-to-character comparison of both strings turns out identi-
cal. Otherwise the result is 0. the character-to-character comparison of strings is described
on page 35 under the compare() function.

31

<!-- Page 34 -->

operator+(pString(String)) → String
The addition operator anticipates a string on the right side. Otherwise, an exception is
+
triggered. Itinturncreatesanewstringconsistingofthelinkedstringsontheleftandright
sides of the operator.
operator+=(pString(String)) → String
The += addition operator anticipates a string on the right side. Otherwise, an exception is
triggered. It in turn appends the string on the right side of the operator onto the string on
the left side. The result is the combined string.
operator[](pIdx(Int)) → Int
operator[](pIdx(Int), pChar(Int))
The index operators anticipate a value of the Int type as the pIdx index. Otherwise, an
exception is triggered. Assume the length of the string is len. If pIdx < 0, pIdx is set to
pIdx+len. If afterwards, pIdx<0∨pIdx≥len, an exception is triggered. Otherwise, the
character at the pIdx position is returned as a positive Int .
If the index operator is used on the left side of the assignment operator (the second form of
the index operator), the expression on the right side of the assignment operator must return
a value of the Int type. Otherwise, an exception is triggered. This value, modulo 2 8 , is
assigned the to the string at the pIdx position.
operator[:](pBegin(Int), pEnd(Int)) → String
operator[:](pBegin(Int), pEnd(Int), pChar(Int))
operator[:](pBegin(Int), pEnd(Int), pString(String))
The [:] range operator anticipates both the pBegin and pEnd indexes of the Int type.
Assume the length of the string is len. If pBegin<0, pBegin is set to pBegin+len. Like-
wise, pEnd is set to pEnd+len if pEnd<0. If, afterwards, pBegin<0∨pBegin>len or
pEnd<0∨pEnd>lenorpBegin>pEnd,anexceptionistriggered. Otherwise,asubstring
is returned, starting with the pBegin position and ending with the pEnd−1 position.
Iftherangeoperatorisusedontheleftsideoftheassignmentoperator(thesecondandthird
form of the range operator), the value of the expression on the right side of the assignment
operator must be either an Int value or a string of any length. Otherwise, an exception
is triggered. The substring specified by the pBegin and pEnd indexes is replaced by the
8
character, modulo 2 , specified by the integer value, or by the string.
operator!!() → Int
The !!test operator returns 1 if the length of the string is not null. Otherwise, it returns 0.
getAt(pIdx(Int)) → Int
If pIdx < 0, pIdx is set to pIdx+size(). If afterwards, pIdx < 0∨pIdx ≥ size(), an
exceptionistriggered. Otherwise,thecharacteratthepIdxpositionisreturnedasapositive
Int .
setAt(pIdx(Int), pChar(Int))
If pIdx < 0, pIdx is set to pIdx + size(). If, afterwards, pIdx < 0 ∨ pIdx ≥ size() or
8
pChar < 0∨pChar ≥ 2 , an exception is triggered. Otherwise, pChar is assigned to the
character at the pIdx position.

32

<!-- Page 35 -->

size() → Int
returns the number of characters in the string.
empty() → Int
returns 1 if the length of the string is null. Otherwise, it returns 0.
resize(pSize(Int), pChar(Int) = ’ ’)
If pChar < 0∨pChar ≥ 2 8 , an exception is triggered. Otherwise, the new length of the
string is set to pSize. If the new value is greater than the old length, the pChar character is
used to fill it in.
append(pString(String), pPos(Int) = 0, pLen(Int) = Int::MAX VALUE)
If pPos < 0∨pPos > pString.size() or pLen < 0, an exception is triggered. Otherwise,
pLen = min(pLen,pString.size()−pPos). The substring of pString with the pLen length
is then, starting at the pPos position appended to the string.
append(pNum(Int), pChar(Int) = ’ ’)
8
If pNum<0 or pChar <0∨pChar ≥2 , an exception is triggered. Otherwise, the pChar
character is appended to the string pNum number of times.
assign(pString(String), pPos(Int) = 0, pLen(Int) = Int::MAX VALUE)
If pPos < 0∨pPos > pString.size() or pLen < 0, an exception is triggered. Otherwise,
pLen=min(pLen,pString.size()−pPos). ThestringisthensettothesubstringofpString,
which begins at the pPos position and has a length of pLen.
assign(pNum(Int), pChar(Int) = ’ ’)
8
If pNum < 0 or pChar < 0∨pChar ≥ 2 , an exception is triggered. Otherwise, the string
is set to a sequence of pLen times the pChar character.
insert(pPos1(Int), pString(String), pPos2(Int) = 0, pLen(Int) = Int::MAX VALUE)
If pPos1 < 0∨pPos1 > size() or pPos2 < 0∨pPos2 > pString.size() or pLen < 0, an
exception is triggered. Otherwise, pLen is set to min(pLen,pString.size()−pPos2). Then,
the substring from pString, beginning at the pPos2 position and having a length of pLen,
is inserted at position pPos1.
insert(pPos(Int), pNum(Int), pChar(Int) = ’ ’)
If pPos < 0∨pPos > size() or pNum < 0 or pChar < 0∨pChar >= 2 8 , an exception is
triggered. Otherwise, the pChar character is inserted at the pPos position pNum number
of times.
remove(pPos(Int) = 0, pLen(Int) = Int::MAX VALUE)
If pPos<0∨pPos>size() or pLen<0, an exception is triggered. Otherwise, pLen is set
to min(pLen,size()−pPos) Then, pLen characters are removed starting at position pPos.
replace(pPos1(Int), pLen1(Int), pString(String), pPos2(Int) = 0, pLen2(Int) = Int::MAX VALUE)

If pPos1 < 0∨pPos1 > size() or pPos2 < 0∨pPos2 > pString.size() or pLen1 < 0 or
pLen2<0,anexceptionistriggered. Otherwise,pLen1issettomin(pLen1,size()−pPos1)
and pLen2 is set to min(pLen2,pString.size()−pPos2). Then, pLen1 characters starting
at position pPos1 are replaced by a substring from pString, which begins at position pPos2
and is pLen2 characters long.

33

<!-- Page 36 -->

replace(pPos(Int), pLen(Int), pNum(Int), pChar(Int) = ’ ’)
If pPos < 0∨pPos > size() or pLen < 0 or pNum < 0 or pChar < 0∨pChar ≥ 2 8 ,
an exception is triggered. Otherwise, pLen is set to min(pLen,size()−pPos) Then, pLen
charactersstartingatpositionpPosarereplacedbypNumnumberofnewpCharcharacters.
swap(pString(String))
swaps the contents of two strings.
find(pString(String), pPos(Int) = 0) → Int
If possible, the smallest res value is returned for which these are valid:
res≥pPos∧res+pString.size()≤size() and
getAt(res+i)=pString.getAt(i) for all i≥0∧i<pString.size()
Otherwise, −1 is returned.
find(pChar(Int), pPos(Int) = 0) → Int
If pChar < 0∨pChar ≥ 2 8 , an exception is triggered. Otherwise, if possible, the smallest
res value is returned for which these are valid:
res≥pPos∧res<size() and getAt(res)=pChar
Otherwise, −1 is returned.
rfind(pString(String), pPos(Int) = Int::MAX VALUE) → Int
If possible, the largest res value is returned for which these are valid:
res≤pPos∧res+pString.size()≤size() and
getAt(res+i)=pString[i] for all i≥0∧i<pString.size()
Otherwise, −1 is returned.
rfind(pChar(Int), pPos(Int) = Int::MAX VALUE) → Int
If pChar <0∨pChar ≥2 8 , an exception is triggered. Otherwise, if possible, the largest res
value is returned for which these are valid:
res≤pPos∧res<size() and getAt(res)=pChar
Otherwise, −1 is returned.
findFirstOf(pString(String), pPos(Int) = 0) → Int
If possible, the smallest res value is returned for which these are valid:
res≥pPos∧res<size() and
getAt(res)=pString.getAt(i) for at least one i≥0∧i<pString.size()
Otherwise, −1 is returned.
findFirstOf(pChar(Int), pPos(Int) = 0) → Int
8
If pChar < 0∨pChar ≥ 2 , an exception is triggered. Otherwise, if possible, the smallest
res value is returned for which these are valid:
res≥pPos∧res<size() and getAt(res)=pChar Otherwise, −1 is returned.
findLastOf(pString(String), pPos(Int) = Int::MAX VALUE) → Int
If possible, the largest res value is returned for which these are valid:
res≤pPos∧pPos<size() and
getAt(res)=pString.getAt(i) for at least one i≥0∧i<pString.size()
Otherwise, −1 is returned.
findLastOf(pChar(Int), pPos(Int) = Int::MAX VALUE) → Int
8
If pChar <0∨pChar ≥2 , an exception is triggered. Otherwise, if possible, the largest res

34

<!-- Page 37 -->

value is returned for which these are valid:
res≤pPos∧pPos<size() and getAt(res)=pChar
Otherwise, −1 is returned.
findFirstNotOf(pString(String), pPos(Int) = 0) → Int
If possible, the smallest res value is returned for which these are valid:
res≥pPos∧res<size() and
getAt(res)=pString.getAt(i) for no i≥0∧i<pString.size()
Otherwise, −1 is returned.
findFirstNotOf(pChar(Int), pPos(Int) = 0) → Int
8
If pChar < 0∨pChar ≥ 2 , an exception is triggered. Otherwise, if possible, the smallest
res value is returned for which these are valid:
res≥pPos∧res<size() and getAt(res)(cid:54)=pChar
Otherwise, −1 is returned.
findLastNotOf(pString(String), pPos(Int) = Int::MAX VALUE) → Int
If possible, the largest res value is returned for which these are valid:
res≤pPos∧pPos<size() and
getAt(res)=pString.getAt(i) for no i≥0∧i<pString.size()
Otherwise, −1 is returned.
findLastOf(pChar(Int), pPos(Int) = Int::MAX VALUE) → Int
8
If pChar <0∨pChar ≥2 , an exception is triggered. Otherwise, if possible, the largest res
value is returned for which these are valid:
res≤pPos∧pPos<size() and getAt(res)(cid:54)=pChar
Otherwise, −1 is returned.
substr(pPos(Int) = 0, pLen(Int) = Int::MAX VALUE) → String
If pPos<0∨pPos>size() or pLen<0, an exception is triggered. Otherwise, pLen is set
to min(pLen,size()−pPos) Then, a new string is created and returned whose contents are
equivalent to the substring beginning at pPos and having a length of pLen.
toUpper(pPos(Int) = 0, pLen(Int) = Int::MAX VALUE)
If pPos<0∨pPos>size() or pLen<0, an exception is triggered. Otherwise, pLen is set
to min(pLen,size()−pPos) Then, if pLen > 0, all lowercase letters from position pPos up
to and including position pPos+pLen−1 are converted to uppercase letters.
toLower(pPos(Int) = 0, pLen(Int) = Int::MAX VALUE)
If pPos<0∨pPos>size() or pLen<0, an exception is triggered. Otherwise, pLen is set
to min(pLen,size()−pPos) Then, if pLen>0, all uppercase letters from position pPos up
to and including position pPos+pLen−1 are converted to lowercase letters.
compare(pPos1(Int), pLen1(Int), pString(String), pPos2(Int) = 0, pLen2(Int) = Int::MAX VALUE) → Int

runsacharacter-to-charactercomparisononthepStr1=substr(pPos1,pLen1)andpStr2=
pString.substr(pPos2,pLen2) strings. The result is −1 if pStr1 is smaller than pStr2. It is
+1 if pStr1 is larger than pStr2. And it is 0 if pStr1 and pStr2 are the same.
When two strings are compared character-to-character, the characters of both strings, start-
ingatposition0,arecomparedtoeachotherinpairs. Thecomparisonisterminatedassoon

35

<!-- Page 38 -->

as a pair of unidentical characters or the end of at least one string is reached. In the first
case,theresultofthecomparisonis−1ifthecodeofthecharacterinthefirst(orleft)string
is less than the code of the character in the second (or right) string. Accordingly, the result
is +1 if the code of the character in the first string is greater than the code of the character
inthesecondstring. Inthesecondcase,theresultis0iftheendsofbothstringsarereached
simultaneously. It is −1 if the end of the first sting was reached and +1 if the end of the
second string was reached.
compare(pString(String), pPos(Int) = 0, pLen(Int) = Int::MAX VALUE) → Int
Corresponds to calling compare(0, Int::MAX_VALUE ,pString,pPos,pLen).
getHashValue() → Int
The getHashValue() method returns a hash value for the string. Like the == operator, it
always returns the same hash value for identical strings, but can also return the same hash
value for unidentical strings.

### 3.4.4 Vectors

The Vector type represents one-dimensional vectors. Multidimensional fields can be formed from
vectors of vectors, whereby the dimensions of the individual vectors do not have to be identical.
Random access to individual vector elements through their indexes requires constant time, as do
insert and delete operations at the ends of vectors. For insert and delete operations at the start or
in the middle of the vector, the required time is proportional to the number of subsequent vector
elements.
Insert operations might require additional time for reallocation of the vector.
Vectors can be created in two ways:

• By calling the Vector constructor. Vector(pSize(Int), ...) creates a vector with pSize ele-
ments, which are initialized with NULL. The entry of a second pSize2 argument of the Int
type initializes the vector with vectors of size pSize2, thus creating a two-dimensional field.
This can be continued recursively by entering three and more arguments of the Int type to
create three and higher multidimensional fields.
• By entering the elements in brackets, separated by commas. For every element there can be
any type of assignment expression, the result of which is to be used to initialize the element.

special-ctor:
[ arg-expr-list ]
opt
arg-expr-list:
assign-expr
arg-expr-list , assign-expr

The following operators (see Section 3.6) and methods (see Section 3.8.4) can be applied to the
Vector type:

36

<!-- Page 39 -->

operator==(pSeq(Object)) → Int
operator!=(pSeq(Object)) → Int
The == and != relational operators with a vec vector on the left side anticipate a pSeq
instanceofasequencetype(seeSection3.3.4)ontherightside. ThevecvectorandthepSeq
sequence are the same if:
• The length of vec is equal to the length of pSeq.
• For every idx integer index in the range of [0,vec.size()), the comparison of vec[idx]
to pSeq[idx] using the == true operator yields ((cid:54)= 0). The first comparison of elements
that triggers an exception or does not yield true terminates the comparison of the vec
vector to the pSeq sequence.
operator[](pIdx(Int)) → Object
operator[](pIdx(Int), pObj(Object))
The [] indexoperatoranticipatesavalueofthe Int typeasindexpIdx. Assumethelengthof
thevectorislen. IfpIdx<0,pIdxissettopIdx+len. Ifafterwards,pIdx<0∨pIdx≥len,
an exception is triggered. Otherwise, the vector element indexed by pIdx is returned.
If the index operator is used on the left side of the assignment operator (the second form of
the index operator), the result of the expression on the right side of the assignment operator
is assigned the vector element indexed by pIdx.
operator[:](pBegin(Int), pEnd(Int)) → Vector
operator[:](pBegin(Int), pEnd(Int), pSeq(Object))
The [:] range operator anticipates both the pBegin and pEnd indexes of the Int type.
Assume the length of the vector is len. If pBegin<0, pBegin is set to pBegin+len. Like-
wise, pEnd is set to pEnd+len if pEnd<0. If, afterwards, pBegin<0∨pBegin>len or
pEnd < 0∨pEnd > len or pBegin > pEnd, an exception is triggered. Otherwise, a vector
is returned that consists of the elements of the original vector that are indexed by pBegin
to pEnd−1.
If the range operator is used on the left side of the assignment operator (the second form of
the range operator), the result of the expression on the right side of the assignment operator
must be a sequence (see Section 3.3.4) of any length. The elements of the vector indexed by
pBegin to pEnd−1 are replaced by all of the elements of the sequence.
operator!!() → Int
The !!test operator returns 1 if the length of the vector is not null. Otherwise, it returns 0.
getAt(pIdx(Int)) → Object
If pIdx < 0, pIdx is set to pIdx+size(). If afterwards, pIdx < 0∨pIdx ≥ size(), an
exception is triggered. Otherwise, the element with index pIdx is returned.
setAt(pIdx(Int), pObject(Object))
If pIdx < 0, pIdx is set to pIdx+size(). If afterwards, pIdx < 0∨pIdx ≥ size(), an
exception is triggered. Otherwise, pObject is assigned the element with the pIdx index.
size() → Int
The number of elements of the vector is returned.

37

<!-- Page 40 -->

empty() → Int
If size()=0, 1 is returned;otherwise 0.
front() → Object
Ifsize()=0,anexceptionistriggered. Otherwise,thefirstelementofthevectorisreturned.
back() → Object
Ifsize()==0,anexceptionistriggered. Otherwise,thelastelementofthevectorisreturned.
pushBack(pObject(Object))
As the last element, pObject is appended to the vector.
popBack() → Object
If size()=0, an exception is triggered. Otherwise, the last element of the vector is removed
from this and returned.
insert(pPos(Int), pNum(Int) = 1, pObj(Object))
If pPos < 0∨pPos > size() or pNum < 0, an exception is triggered. Otherwise, pObj is
insertedpNum number of times at the pPos index.
erase(pBegin(Int), pEnd(Int) = pBegin + 1)
If pBegin < 0∨pBegin > size() or pEnd < 0∨pEnd > size() or pBegin > pEnd, an
exception is triggered. Otherwise, if pBegin < pEnd, the elements indexed by pBegin to
pEnd−1 are deleted from the vector.
swap(pVec(Vector))
If pVec is not an instance of the Vector type, an exception is triggered. Otherwise, the
contents of both vectors are swapped.

### 3.4.5 Lists

The List type represents double-chained lists.
Sequential access to individual elements of a list, both forwards and backwards, as well as insert
and delete operations at any position, require constant time. The most required time for random
access to list elements is proportional to the minimum distance to the start or end of the list.
Lists can be created in two ways:

• By calling the List constructor. This can be called with zero or more arguments. The
arguments form the individual elements of the list.
• By entering the elements in @(), separated by commas. For every element there can be any
type of assignment expression, the result of which is to be used to initialize the element.

special-ctor:
@( arg-expr-list )
opt
arg-expr-list:
assign-expr
arg-expr-list , assign-expr

38

<!-- Page 41 -->

The following operators (see Section 3.6) and methods (see Section 3.8.4) can be applied to the
type:
List

operator==(pSeq(Object)) → Int
operator!=(pSeq(Object)) → Int
The == and != relational operators with a list list on the left side anticipate a pSeq in-
stance of a sequence type (see Section 3.3.4) on the right side. The list list and the pSeq
sequence are the same if:
• The length of list is equal to the length of pSeq.
• For every idx integer index in the range of [0,list.size()), the comparison of list[idx]
to pSeq[idx] using the == true operator yields ((cid:54)= 0). The first comparison of elements
that triggers an exception or does not yield true terminates the comparison of the list
list to the pSeq sequence.
operator[](pIdx(Int)) → Object
operator[](pIdx(Int), pObject(Object))
The [] index operator anticipates a value of the Int type as index pIdx. Assume the length
ofthelistislen. IfpIdx<0,pIdxissettopIdx+len. Ifafterwards,pIdx<0∨pIdx≥len,
an exception is triggered. Otherwise, the list element indexed by pIdx is returned.
If the index operator is used on the left side of the assignment operator (the second form of
the index operator), the result of the expression on the right side of the assignment operator
is assigned the list element indexed by pIdx.
operator[:](pBegin(Int), pEnd(Int)) → List
operator[:](pBegin(Int), pEnd(Int), pSeq(Object))
The [:] range operator anticipates both the pBegin and pEnd indexes of the Int type.
Assume the length of the list is len. If pBegin<0, pBegin is set to pBegin+len. Likewise,
pEnd is set to pEnd+len if pEnd < 0. If, afterwards, pBegin < 0∨pBegin > len or
pEnd < 0∨pEnd > len or pBegin > pEnd, an exception is triggered. Otherwise, a list
is returned that consists of the elements of the original list that are indexed by pBegin to
pEnd−1.
If the range operator is used on the left side of the assignment operator (the second form of
the range operator), the result of the expression on the right side of the assignment operator
must be a sequence (see Section 3.3.4) of any length. The elements of the list indexed by
pBegin to pEnd−1 are replaced by all of the elements of the sequence.
operator!!() → Int
The !!test operator returns 1 if the length of the list is not null. Otherwise, it returns 0.
getAt(pIdx(Int)) → Object
If pIdx < 0, pIdx is set to pIdx+size(). If afterwards, pIdx < 0∨pIdx ≥ size(), an
exception is triggered. Otherwise, the element with index pIdx is returned.
setAt(pIdx(Int), pObject(Object))
If pIdx < 0, pIdx is set to pIdx+size(). If afterwards, pIdx < 0∨pIdx ≥ size(), an
exception is triggered. Otherwise, pObject is assigned the element with the pIdx index.

39

<!-- Page 42 -->

size() → Int
The number of elements of the list is returned.
empty() → Int
If size()=0, 1 is returned;otherwise 0.
front() → Object
If size()=0, an exception is triggered. Otherwise, the first element of the list is returned.
back() → Object
If size()=0 , an exception is triggered. Otherwise, the last element of the list is returned.
pushFront(pObject(Object))
As the first element, pObject is appended to the list.
pushBack(pObject(Object))
As the last element, pObject is appended to the list.
popFront() → Object
If size() = 0, an exception is triggered. Otherwise, the first element of the list is removed
from this and returned.
popBack() → Object
If size() = 0, an exception is triggered. Otherwise, the last element of the list is removed
from this and returned.
insert(pPos(Int), pNum(Int) = 1, pObj(Object))
If pPos < 0∨pPos > size() or pNum < 0, an exception is triggered. Otherwise, pObj is
insertedpNum number of times at the pPos index.
erase(pBegin(Int), pEnd(Int) = pBegin + 1)
If pBegin < 0∨pBegin > size() or pEnd < 0∨pEnd > size() or pBegin > pEnd, an
exception is triggered. Otherwise, if pBegin < pEnd, the elements indexed by pBegin to
pEnd−1 are deleted from the list.
swap(pList(List))
IfpListisnotaninstanceoftheListtype,anexceptionistriggered. Otherwise,thecontents
of both lists are swapped.
splice(pPos(Int), pList(List), pBegin(Int) = 0, pEnd(Int) = pBegin + 1)
If pPos<0∨pPos>size() or pBegin<0∨pBegin>pList.size() or pEnd<0∨pEnd>
pList.size() or pBegin > pEnd, an exception is triggered. Otherwise, if pBegin < pEnd,
the elements from pList that are indexed by pBegin to pEnd−1 are removed from pList
and inserted in the same order starting at pPos.
remove(pObj(Object))
Compares each element of the list, starting with the first and ascending sequentially until
the last, using the operator with pObj, whereby the list element appears on the left and
==
pObj on the right of the relational operator. If an exception is triggered by the comparison,
the function turns back immediately. Otherwise, if the comparison resulted in true ((cid:54)=0), it
removes the current list element from the list.

40

<!-- Page 43 -->

removeIf(pPred(Func))
The pPred argument has to be a function that expects an argument and returns either true
((cid:54)=0) or false (0) (unary predicate).
The removeIf() method calls thepPred function for every element of the list, starting with
the first and ascending sequentially until the last, whereby the list element is passed as an
argumenttothefunction. Ifanexceptionistriggeredbythefunction, removeIf()turnsback
immediately. Ifthereturnvalueofthefunctionisnotan Int type,anexceptionistriggered.
Otherwise,ifthereturnvalueofthefunctionistrue((cid:54)=0),itremovesthecurrentlistelement
from the list.
unique()
Removes from each sequence all identical, consecutive elements except the first one. To do
so, it compares each current element to its directly successive element using the == operator,
wherebythecurrentelementappearsontheleftandthesuccessiveelementontherightofthe
relationaloperator. Ifanexceptionistriggeredbytherelationaloperator,thefunctionturns
back immediately. Otherwise, the successive element is deleted if the comparison results in
true, orthesuccessiveelementismadethecurrentelementifthecomparisonresultsinfalse.
unique(pPred(Func))
ThepPredargumenthastobeafunctionthatexpectstwoargumentsandreturnstrue((cid:54)=0)
if both arguments are the same, or false (0) if they are different (binary predicate). If the
return value is not an Int type, unique() triggers an exception.
The unique() method with pPred as an argument behaves exactly as it does without an
argument except that, instead of the == operator, the pPred function is called, to which the
current element is passed as the first argument and the successive element as the second.
merge(pList(List))
The merge() method merges two lists, sorted in ascending order, into a single sorted list. It
usesthe<operator,totheleftsideofwhichispassedanelementfrompListandtotheright
an element from self. If an exception is triggered by the relational operator, merge() turns
backimmediatelyandthecontentofeachlistisundefined. ThepListargumentlistisempty
after merge() comes back. If elements are equivalent in both lists, the elements from self
are placed before those from pList in the result list. The order of elements in a list remains
unchanged in the result list.
merge(pList(List), pPred(Func))
The second pPred argument has to be a function that expects two arguments and returns
true ((cid:54)= 0) if the first argument is smaller than the second argument or false (0) otherwise
(binary predicate). If the return value is not an Int type, merge() triggers an exception.
Themerge()methodwithtwoargumentsbehavesexactlyasitdoeswithonlyoneargument
except that, instead of the < operator, the pPred function is called.
sort()
Sorts the list using the relational operator, which can be called for any of the elements in
<
a list. If an exception is triggered by sort() either directly or indirectly, the content of the
listisundefined. Theorderofsameelementsintheunsortedlistremainsintactinthesorted
list. The complexity of sort() is approximately size()·log(size()) relational operations.

41

<!-- Page 44 -->

sort(pPred(Func))
The pPred argument has to be a function that expects two arguments and returns true
((cid:54)=0)ifthefirstargumentissmallerthanthesecondargumentorfalse(0)otherwise(binary
predicate). If the return value is not an Int type, sort() triggers an exception.
Thesort()methodwithoneargumentbehavesexactlyasitdoeswithoutanargumentexcept
that, instead of the < relational operator, the pPred function is called.
reverse()
The reverse() method reverses the order of the elements in the list.

### 3.4.6 Hash Tables

The Hash type makes hash tables available. A hash table contains a set of entries in pairs. Each
entryconsistsofakeyandavalue. Thekeyisusedtoaccessthevalueforreadorwriteoperations.
Values of the simple types, Int , Float and Symbol , as well as all reference types that define the
instance-oriented getHashValue() method, can be used as keys. The getHashValue() method
mustreturnavalueofthe Int type,whichisthesamefortwokeysforwhichtheequalityoperator,
==, when applied to them, yields true.
Keys of different types can be used in a hash table. Two keys are considered the same if their
types are identical and the equality operator, ==, when applied to both keys, yields true.
TheHash()constructorcreatesanemptyhashtable. Theinitialsizeofthehashtableisdependent
onimplementation. Itgrowswiththeamountofvaluesstoredinthehashtable, wherebythetime
forhashtableenlargementisdistributedtoconsecutivereadorwriteaccesses,whiletheadditional
time taken for an access is on average independent of the size of the hash table.
The following operators (see Section 3.6) and methods (see Section 3.8.4) can be applied the
Hash
type:

operator[](pKey(Object)) → Object
operator[](pKey(Object), pValue(Object))
The index operator anticipates a key as an index value that meets the key requirements
listed above. If the hash table contains an entry with this key, the value stored for this entry
is returned. Otherwise, an exception is triggered.
If the index operator is used on the left side of the assignment operator, the result of the
expressionontherightsideoftheassignmentoperatorisstoredasavalueunderthespecified
key in the hash table. If no entry yet exists for this key, a new entry is created.
operator!!() → Int
Thetestoperatorreturns1ifthehashtablecontainsatleastoneentry. Otherwise,itreturns
0.
getAt(pKey(Object)) → Object
The getAt() method anticipates as an argument a key that meets the above-mentioned re-
quirements. If no entry exists for this key, an exception is triggered. Otherwise, the value of
the entry is returned.

42

<!-- Page 45 -->

setAt(pKey(Object), pValue(Object))
The setAt() method anticipates as the first argument a key that meets the above-mentioned
requirements and, as the second, an object of any type. If no entry exists for this key, a new
one is created. Then, the value of the second argument is stored in this entry as a value.
size() → Int
The number of entries in the hash table is returned.
empty() → Int
If size()=, 1 is returned, otherwise 0.
hasKey(pKey(Object)) → Int
The hasKey() method anticipates as the argument a key that meets the above-mentioned
requirements. It returns 1 if an entry with this key exists in the hash table; otherwise it
returns 0.
keys() → Vector
The keys() method returns a Vector whose individual elements are the keys of all entries in
the hash table.
values() → Vector
Thevalues()methodreturnsaVectorwhoseindividualelementsarethevaluesofallentries
in the hash table.
swap(pHash(Hash))
If the argument is not of the Hash reference type, an exception is triggered. Otherwise, the
entries of both hash tables are swapped.
remove(pKey(Object))
Theargumentmustbeakeythatmeetstheabove-mentionedrequirements. Ifnoentryexists
for this key, an exception is triggered. Otherwise, the corresponding entry is deleted.

Theidenticalorderofthekeysandvaluesreturnedbythekeys()andvalues()methodscanonly
beguaranteedifnoothermethodsofthehashtable, includingindexoperators, arecalledbetween
the execution of the two methods.

# 3.5 Statements

The translation unit (translation-unit) shapes the entry symbol of the OFML grammar (see Sec-
tion3.1.3). Everytranslationunitconsistsofanoptionalpackagestatement, a(potentiallyempty)
sequence of import statements (import-stmts) and a (potentially empty) sequence of other state-
ments (stmt-list). The syntax and semantics of package and import statements are described in
Section 3.7.

translation-unit:
package-stmt import-stmts stmt-list
opt opt opt
import-stmts:
import-stmts import-stmt
opt
stmt-list:
stmt-list stmt
opt

43

<!-- Page 46 -->

AnOFMLstatementcancontainthefollowing: adefinition(definition-stmt), anexpression(expr-
stmt), a control statement (ctrl-stmt) or a compound statement (compound-stmt).

stmt:
definition-stmt
expr-stmt
ctrl-stmt
compound-stmt

Definitions are handled by the compiler. All other statements are executed in the order in which
they appear textually at runtime.
8
In some cases, either a semicolon or the end of file is expected at the end of a statement .

eox:
; | EOF

### 3.5.1 Definitions

The following elements can be introduced by definitions: variables (var-def), named functions
(named-func-def),classes(class-def),thenameofthepackagetowhichthetranslationunitbelongs
(package-stmt) and the packages imported by the translation unit (import-stmt). Package and
import statements are described in Section 3.7, class definition in Section 3.8.

definition-stmt:
var-def
named-func-def
class-def

Variable Definitions

A variable definition starts with an optional sequence of modifiers and the keyword, followed
var
by one or more initialization expressions (init-expr) separated by commas. The last expression
is ended with a semicolon or the end of file (eox). Every initialization expression consists of an
identifier(ident),optionallyfollowedbyanassignmentoperatorandanexpression(expr)evaluated
in the value context (see Section 3.6.1). The latter is used to set the initial valued of variables. If
neither the assignment operator nor expression (expr, see Section3.6) are present, the variable is
given the NULL value. The identifier becomes valid immediately after the initialization expression
contained within it.
8
Theendoffileisallowedtoterminateastatementsothatthesemicoloncanbedroppedininteractivemode.

44

<!-- Page 47 -->

var-def:
global-modifiers var init-expr-list eox
opt
init-expr-list:
init-expr
init-expr-list , init-expr
init-expr:
ident
ident expr
=

Modifiers are described in Sections 3.7.6 and 3.8.

Named Function Definitions

The definition of a named function begins with an optional sequence of modifiers and the func
keyword, followed by the name of the function that, as such, becomes valid in the current names-
pace (see Section3.7). A pair of parentheses follows, which encloses any existing parameters and
compound statement, which represents the function body.

named-func-def:
global-modifiers func ident ( param-list ) compound-stmt
opt opt
global-modifiers func ident ( param-list , ... ) compound-stmt
opt
native global-modifiers func ident ( ) ;
opt
param-list:
ident
param-list , ident

Modifiers are described in Sections 3.7.6 and 3.8.
Thesecondformofthefunctiondefinition,forwhichanellipse(...),separatedbyitwithacomma,
follows a non-empty parameter list, defines a function with a variable number of arguments. If
the function defined in this manner has n parameters in its parameter list, it is to be called with
at least n−1 arguments. A vector, which receives all further arguments, is created for the nth
parameter.
The third form of the function definition, which is introduced by the native keyword, does not
9
contain any parameter declarations or any function body. Instead, its definition is closed with a
semicolon.
A function that is defined as native is implemented in platform-dependent code. This is usually
another programming language, such as C, C++ or Assembler.
9
Thisdoesnotmeanthatnoargumentscanbepassedtoafunctiondefinedasnative. Theparametersarenot
declared,sinceitisthetaskoftheplatform-dependentcodetoverifythenumberofarguments(andtheirtypes).

45

<!-- Page 48 -->

### 3.5.2 Expressions as Statements

Most statements in OFML consist of an expression (expr, which is evaluated in secondary context
(see Section 3.6.1) and is closed with a semicolon or end of file.

expr-stmt:
expr eox
opt

If the expression is not present, the statement is an empty statement, which can be used in
situations where the syntax requires a statement but no action is desired (for example in the body
of an empty loop).

### 3.5.3 Control Statements

Control statements are used to control the course of a program dynamically and are divided
roughlyintothreecategories: selectionstatements(select-stmt),loopstatements(loop-stmt),jump
statements (jump-stmt) and exception statements exception-stmt). The latter are described in
Section 3.5.3.

ctrl-stmt:
select-stmt
loop-stmt
jump-stmt
exception-stmt

Selection Statements

Selection statements select one or more program sequences.

select-stmt:
expr stmt
if ( )
1
expr stmt stmt
if ( ) else
1 2
label expr switch-stmt-list
switch ( ) { }
opt

For both forms of the if statement, the expr expression is assessed in test context (see Sec-
tion 3.6.1). If the expression yields true, the stmt statement is executed. In the second form,
1
stmt is executed if the expression yields false. The syntactical ambiguity for else is resolved by
2
always assigning an else to the last occurring if without else on the same block nesting level.
The stmt and stmt statements of the if statement cannot be definitions (definition-stmt).
1 2

The switch statementevaluatesthe switch expressionexprinvaluecontextandbranches,depend-
ingontheresult,toalabel(switch-label)withinthesubsequentstatementlist( switch-stmt-list ),

46

<!-- Page 49 -->

which is enclosed in curly brackets. Optionally, it can include a label to which the and
break
statements can refer within the statement list (see Section 3.5.3).
continue switch

switch-stmt-list:
switch-stmt-list switch-stmt
opt
switch-stmt:
expr-stmt
ctrl-stmt
compound-stmt
switch-label
switch-label:
case expr :
default :

Here, the expressions (expr) of the case labels are evaluated in the order in which they occur and
compared for equality to the result of the expression, whereby the result of the
switch switch
expression appears on the left of the relational operator. If the comparison yields true, process-
ing continues with the statement (switch-stmt) that directly follows the label. Otherwise,
case
processing continues at the next label.
case
Ifallcaselabelshavebeenprocessedwithouttheoccurrenceofequality,processingcontinueswith
the statement following a default label if one is present. If none is present, no statement in the
statement list is processed.
No more than one default label may occur within the statement list of a switch statement.
Exceptions that have been triggered by the switch expression, the case expressions or the ==
relational operator, which is applied to the results of both expressions, are not caught.

Loop Statements

Loop statements are used to repeat the execution of statements. Optionally, a loop statement can
include a label to which, within the body of the loop, the breakand continuestatements can refer
(see Section 3.5.3).
The stmt statement that forms the body of the loop cannot be a definition (definition-stmt).

labeled-loop-stmt:
label loop-stmt
opt
label:
ident :
loop-stmt:
while ( expr ) stmt
do stmt while ( expr )
for ( expr ; expr ; expr ) stmt
1opt 2opt 3opt
foreach ( name ; expr ) stmt

47

<!-- Page 50 -->

The expr expressions of the or – statements and the second expr expression of the
while do while
2
statement are evaluated in test context (see Section 3.6.1).
for
Using the while statement, the stmt statement is repeated until the expr expression yields false.
The evaluation of the expression takes place before the first execution of the statement.
The do – while statementissimilartothe while statement,exceptthattheexpressionisevaluated
after the execution of the stmt statement. In this case, the statement is executed at least once no
matter what.
With the for statement, the first expression (expr ) is evaluated first in secondary context. It
1
is used (in general) to initialize the loop. The second expression (expr ) is evaluated before each
2
processing of the loop body. If it yields false, the for loop is terminated. Otherwise, the body of
theloopisprocessedandthenthethirdexpression(expr ),which(ingeneral)isusedtoreinitialize
3
the loop, is processed in secondary context.
All three expressions of the for statement may be omitted. If the second expression (expr ) is not
2
present, this is equivalent to the test result of true.
If the statement does not contain a continue statement, the for statement is equivalent to:
expr ;
1
expr
while ( ) {
2
stmt
expr ;
3
}

The foreach statement is used for iterations through a sequence. In this case, the first expression
must be a (if necessary, qualified) name. The result of the second expression processed in value
contextmustmeettherequirementsforasequencetype(seeSection3.3.4). Otherwise,anexception
is triggered (potentially after one or more iterations).
The implementation must behave as if creating a temporary idx variable that is assigned the Int
value of −1 before the loop is processed and is increased by 1 before each pass of the loop. The
second expression is evaluated once prior to processing the loop and its result is stored in the
temporary seq variable. The loop is terminated if idx, after being increased by 1, is greater than
orequaltothecurrentlengthofthesequencestoredinseq. Otherwise,theelementofthesequence
indexedbyidxisassignedthevaluedeterminedbythefirstexpression. Thenthebodyoftheloop
is completely processed.
10
If the foreach statement does not contain a continue statement, it is equivalent to :
seq = expr;
for (idx = 0; idx < seq.size(); idx++) {
name = seq[idx];
stmt
}
10 Theidentifiersareselectedonlyfordemonstration;inprinciple,OFMLgeneratesinternalvariablesthatcannot
comeintoconflictwithuser-definedvariables.

48

<!-- Page 51 -->

Jump Statements

Jump statements unconditionally continue processing of the program at another position.

jump-stmt:
continue-stmt
break-stmt
return-stmt

The continue statement may occur only within a while , do – while , for or switch statement.
For while and do – while loops, it continues program processing with the evaluation of the test
expression, for the for loop, with the evaluation of the reinitialization expression, and for the
switch statement, by restarting the entire switch statement.

continue-stmt:
continue ;
continue ident ;

A continue statement without identifier passes control to the innermost of the statements listed
above. If such a statement is does not exist, a translation error occurs.
A continue statement with an ident identifier passes control to the innermost of the statements
listed above that has the same identifier as a label. If such a statement is does not exist, a
translation error occurs.
The break statement may occur only within a while, do–while, for or switch statement.

break-stmt:
break ;
break ident ;

A break statement without identifier continues program processing directly after the innermost of
the statements listed above. If such a statement is does not exist, a translation error occurs.
A break statement with an ident identifier continues program processing directly after the inner-
most of the statements listed above that has the same identifier as a label. If such a statement is
does not exist, a translation error occurs.
The identifiers specified for continue and break statements and used as labels before while, do–
while , for and switch statements are located in a separate namespace, in which they can be
applied with any frequency.

The return statement ends the execution of a function. If the statement contains an expression
(optional), it is processed in value context (see Section 3.6.1) and its value is returned as a return
value of the function. If there is no expression or if the end of the function is reached without an
occurrence of the return statement, the function returns the NULL value.

49

<!-- Page 52 -->

A statement outside of a function causes a translation error.
return

return-stmt:
return ;
return expr ;

Exceptions

Exceptionscanbetriggeredeitherbyinternalerrors(suchaserrorswhileloadingtranslationunits
or division by zero) or by the explicit execution by the programmer of the throw statement. They
causeanonlocal 11 passoftheprogramprocessfromthepositionwheretheexceptionwastriggered
to the position at which it is caught. The latter is determined during program runtime.

exception-stmt:
try-stmt
throw-stmt

Thetrystatementallowsexceptionstobehandledinauser-definedmanner. Usingseveraloptional
catchcomponents,itispossibletohandlevarioustypesofexceptionsseparately. Herenameisthe
name of a type and ident is the name of a local variable that contains the value of the exception
and that is valid only within the catch block.

try-stmt:
try compound-stmt catch-stmts
opt
catch-stmts:
catch-stmt catch-stmts
opt
catch-stmt:
catch ( name ident ) compound-stmt

Only reference types are permitted as type names in the catch statement. Other types lead to a
translation error. Using a catch statement, all of the exceptions that are instances of the class
specified by the type names or one of the classes derived from this are caught.
If a statement has several statements, the body of the first matching catchstatement
try catch
is executed even if a subsequent statement of the same statement would yield a more
catch try
exact match between the type of the parameter and the class of the exception.
catch
A try statement without catch statement catches all exceptions. If no match between at least on
type of the catch parameter and the class of the exception can be found in a try statement with
at least one catch statement, the exception is not caught by this try statement.

The statement allows the programmer to trigger exceptions. Here, the value of the expr
throw
expression processed in value context (see Section 3.6.1) is passed as the value of the exception.
11
Nonlocalpassmeansthatthecatchingtrystatementcanbelocatedinadirectorindirectcalleroftheexception-
triggeringfunction.

50

<!-- Page 53 -->

throw-stmt:
throw expr eox

The result of the expression of a throw statement must have a reference type. Otherwise, another
exceptionistriggered. The throw statementpassestheprogramprocessingontothe try statement
that dynamically encloses it and that either contains one matching statement or none. If a
catch
statementofthissortisnotpresent,theexceptionis,dependentonimplementation,handledby
try
theruntimesystem, forexamplebyoutputtinganerrormessageandpossiblyterminatedprogram
execution.

Compound Statements

Compound statements are used to insert sequences of several statements at positions where, syn-
tactically, only one statement is permitted, such as in the body of a loop.

compound-stmt:
{ stmt-list }

Compound statements make a new namespace available where variables defined within the com-
pound statement can be entered. When binding an identifier to a variable, a search is carried out
frominsidetooutside, oneaftertheother, inthenamespacesofthestaticallyenclosingcompound
statements.
Variables with identical identifier cannot be defined more than once in a compound statement.
Compound statements cannot contain any function or class definitions.

# 3.6 Expressions

The following section describes the operators of OFML, sorted by precedence. Precedence, asso-
ciativity and evaluation order of operands are fixed conditions. Unless otherwise stated, operands
are evaluated from left to right, while the evaluation of one operand with all side-effects must
be completed before the evaluation of the next can be begun. This also applies to arguments of
functions and methods. With few exceptions, which are explicitly mentioned, all operands of an
operator are evaluated always.
The behavior of unary operators is oriented to the type of the result of the operand. For binary
operators,itisorientedtothetypeoftheresultoftheleftoperand. Ifthecorrespondingresulthas
a predefined reference type, the exact behavior of each operator, if defined, is described in Section
3.4.

### 3.6.1 Value, Test and Secondary Context

Expressions and subexpressions are processed in three different contexts:

51

<!-- Page 54 -->

Wert–Kontext The expression must supply a value of one of the simple types or a reference
type. If the result of the expression is a logical value, it is converted to the value of 1 if
Int
it is true and to the Int value of 0 if it is false.
Test–Kontext The expression must deliver a logical value, i.e. either true or false. If the result
of the expression is a value of a reference type, the operator!!() operator function is called
up for it and then takes into account its return value. If the result now is not an Int or
Float , an exception is triggered. Otherwise, the result of the expression becomes true, if the
Int or Float does not equal null and, otherwise, false.
Nebenwirkungs–Kontext Theexpressionisevaluatedtoachieveasideeffect. Theresultofthe
expression that presents both a logical value and a value of a simple type or a reference type
is ignored.

If not otherwise stated, operators process their operands in value context.

### 3.6.2 Primary Expressions

Primaryexpressionsareidentifiers(seeSections3.7.2and3.7.5),literalconstants(seeSection3.2.5),
special constructors for vectors (see Section3.4.4) and lists (see Section3.4.5) or bracketed expres-
sions:

primary-expr:
name
constant
special-ctor
( expr )
special-ctor:
[ arg-expr-list ]
opt
@( arg-expr-list )
opt
arg-expr-list:
assign-expr
arg-expr-list , assign-expr

names (name) are described in Section 3.7.2, constants (constant) in Section 3.2.5 and special
constructors(special-ctor)inSections3.4.4and3.4.5. Thevalueofabracketedexpressionisequal
to the value of the expr expression within the brackets.

### 3.6.3 Postfix Expressions

Postfix expressions are left-associative.

52

<!-- Page 55 -->

postfix-expr:
primary-expr
postfix-expr [ expr ]
postfix-expr [ expr : expr ]
1opt 2opt
postfix-expr ( arg-expr-list )
opt
postfix-expr ident
.
postfix-expr
++
postfix-expr
--

The operator for accessing ”‘ . ”’ attributes is described in Section 3.8.

Index Expressions

The postfix-expr in the index expression, postfix-expr [ expr ] , must deliver a reference type.
Otherwise, an exception is triggered.
For reference types, two operator methods can be defined, which are used to request and set an
object in a sequence based on an index:
operator[](idx) iscalledfortheresultofthepostfix-expriftheindexedvalueistoberead. The
resultofexprispassedtotheidxparameter. Thereturnvalueoftheoperatormethodisthevalue
of the index expression.
operator[](idx, value) is called for the result of the postfix-expr if the indexed value is to be
written 12 . The result of expr is then passed to the idx parameter and the value to be written is
passed to the value parameter. Any return value is ignored.

Range Expressions

The postfix-expr in the range expression, postfix-expr expr expr ], must deliver a refer-
[ :
1opt 2opt
ence type. Otherwise, an exception is triggered.
If expr is been specified, the Int value of 0 is passed to the range operator as the start of the
1
range. Similarly, if expr is not specified, the return value of the size() method, applied to the
2
result of the postfix-expr, is passed to the range operator as the end of the range. An exception is
triggered if the size() method does not exist.
For reference types, two operator methods can be defined, which are used to request and set a
range of a sequence based on a start and end index:
operator[:](beginend) is called for the result of the postfix-expr if the range is to be read. The
result of expr is passed to the begin parameter and the result of expr to the end parameter. The
1 2
return value of the operator method is the value of the range expression.
operator[:]( beginendvalue ) iscalledfortheresultofthepostfix-expriftherangeistobewritten.
The result of expr is passed to the begin parameter, the result of expr to the end parameter and
1 2
the write value to the value parameter. Any return value is ignored.
12
This is the case, for example, if the index operator is used on the left side of the assignment operator. The
resultoftheexpressionontherightsideoftheassignmentoperatoristhenpassedasvalueontotheindexoperator.

53

<!-- Page 56 -->

Function Calls

For function calls, the first expression (postfix-expr) has to deliver an object of a reference type
that implements the function call operator ( operator() ), such as the predefined function types,
Func and CFunc . An object of this sort is referred to as a function in the following.
For function calls, the two following cases can be distinguished in regard to the called function:

• The called function is a common function or a class-oriented (static) method.
• The called function is an instance-oriented method.

The difference when calling an instance-oriented method compared to calling a class-oriented
(static) method or a common function is that the object for which the method is called is im-
plicitly passed to an instance-oriented method as a self parameter.
Ifthefunctiontobecalledisaninstance-orientedmethodandtheexpressiondeliveringthemethod
is in the form of postfix-expr . ident, the result of postfix-expr is passed as a self parameter.
2 2
Otherwise, the caller must be an instance-oriented method and the self of the calling method is
passed as the self parameter of the instance-oriented method being called.
An exception is triggered if no object can be passed as self for an instance-oriented method 13 or
if the class of the object passed as self is not equal to the class or or one of its derived classes for
which the called instance-oriented method was defined.
The passing of arguments is analogous to the assignment as value for simple types (call by value)
and as reference for reference types (call by reference). Exactly the same number of arguments as
specifiedinthefunctiondefinitionmustbepassedunlessthefunctionisdefinedasafunctionwith
a variable number of arguments. In this case, the number of passed arguments may be no more
than one less that the number of declared parameters. All further arguments are assigned to the
last parameter in the form of a vector.
Thereturnvalueofafunctioncallisthevaluethatwaspassedinthecalledfunctiontothereturn
statement or NULL (see Section 3.5.3).
The function call operator can be defined for classes as follows:
operator()(parameters) is called for the instance of a class if the instance is the result of the
postfix-expr. The arguments of the function call are passed in the manner described above to the
parameters of the function call operator declared in the place of parameters. The return value of
the function call operator method is the result of the function call.

Postfix Incrementation and Decrementation

Theoperandofapostfixincrement ordecrementoperatormustbeavariable, anindexexpression
or a range expression. Otherwise, a translation error occurs.
The postfix increment and decrement operators, ++ and -- , behave as follows depending on the
type of the operand:
13
Thisisthecaseifthecallingfunctionisacommonfunctionoraclass-oriented(static)method.

54

<!-- Page 57 -->

Ifthe valueofthe operand isasimple type, ithas tobean or . Otherwise, an exception
Int Float
is triggered. Then, the following equivalence applies to the processing of the operator:
expr⊕⊕ ≡ ( tmp = expr , expr = tmp ⊕ 1, tmp ) ,
wheretmpisanunnamedvariablecreateddynamicallyforthelengthofprocessingthissubexpres-
sionandsubexpressionsoftheexprexpressionareonlyprocessedonce. Theadditionorsubtraction
follows the rules listed in Section 3.3.3.
If the value of the operand is a reference type, the value or value
operator++( ) operator--( )
operator method is called for the postfix increment or decrement operator for this reference type.
is passed to the dummy parameter. It is used only to distinguish from the corresponding
NULL
prefix increment or decrement operator. The return value of the operator method is the result of
the operator.

### 3.6.4 Unary Operators

Unary expressions are right-associative.

unary-expr:
postfix-expr
unary-op unary-expr
unary-op:
+ | - | ++ | -- | ~ | ! | !! | $

Unary Plus and Minus Operator

The unary plus and minus operators, + and -, behave as follows depending on the type of the
operand:
Ifthe valueofthe operand isasimple type, ithas tobean Int or Float. Otherwise, an exception
is triggered. In the case of the plus operator, the value of the operand is equal to the result of
the operator. In the case of the minus operator (arithmetical negation operator), the result of the
14
operator is equal to the value of the operand multiplied by −1 .

Ifthevalueoftheoperandisareferencetype,theoperator+(value)oroperator-(value)operator
method is called for the unary plus or minus operator for this reference type. The value of the
operand is passed as a value parameter to this method, the return value of which is the result of
the operator.
14 Due to the use of the complement of two for representing integer numbers, the arithmetical negation of the
greatest-valuedrepresentablenegativevalueisequaltothisvalue.

55

<!-- Page 58 -->

Prefix Incrementation and Decrementation

The operand of a prefix increment or decrement operator must be a variable, an index expression
or a range expression. Otherwise, a translation error occurs.
The prefix increment and decrement operators, ++ and -- , behave as follows depending on the
type of the operand:
Ifthe valueofthe operand isasimple type, ithas tobean Int or Float . Otherwise, an exception
is triggered. Then, the following equivalence applies to the processing of the operator:
⊕⊕expr ≡ ( expr = tmp = expr ⊕ 1, tmp ) ,
wheretmpisanunnamedvariablecreateddynamicallyforthelengthofprocessingthissubexpres-
sionandsubexpressionsoftheexprexpressionareonlyprocessedonce. Theadditionorsubtraction
follows the rules listed in Section 3.3.3.
If the value of the operand is a reference type, the ) or ) operator
operator++() operator--()
methodiscalledfortheprefixincrementordecrementoperatorforthisreferencetype. Anyreturn
valuefromthesemethodsisignored. Thevalueoftheoperandisequaltotheresultoftheoperator.

Bitwise Negation

The bitwise negation operator, ~, behaves as follows depending on the type of the operand:
If the value of the operand is a simple type, it has to be an Int . Otherwise, an exception is
triggered. The result of the operator is then equal to the bitwise negation of the value of the
operand.
If the value of the operand is a reference type, the operator~() operator method is called for
bitwise negation for this reference type. The return value of this method is equal to the result of
the operator.

Logical Negation

The operand of the logical negation operator, !, is evaluated in test context. Its result is true if
the value of the operand is false and false if the value of the operand is true.

The Test Operator

The operand of the test operator, !!, is evaluated in test context. Its result is identical to the
value of the operand.

The Symbol Resolution Operator

The symbol resolution operator, $ , requires an argument of the Symbol type. Otherwise, an
exception is triggered. It cannot be redefined for reference types.
The symbol resolution operator dynamically binds the symbol that its operands deliver to a vari-
able. This takes place according to the rules for binding identifiers, which are specified in Section
3.7.5.

56

<!-- Page 59 -->

### 3.6.5 Multiplicative Operators

Multiplicative expressions are left-associative.

mul-expr:
unary-expr
mul-expr mul-op unary-expr
mul-op:
* | / | %

The multiplicative operators, * , / and % , behave as follows depending on the type of the left
operand:
If the value of the left operand is a simple type, it has to be an Int or Float . The value of the
right operand, then, must also be an Int or Float . If either of these conditions are violated, an
exception is triggered. Otherwise, the operation takes place in Int if both operands are of the Int
type, or in Float if at least one of the operands are of the Float type. In the second case, an
operand of the Int type is converted to Float before the operation.
The * operator multiplies the two operands.
The / operator divides the two operands, where the left operand is the dividend and the right
operand, the divisor. If both operands are integers, the result is rounded towards 0.
The % operator determines the remainder of an implicit division for which the left operand is the
dividend and the right, the divisor.
IftheremainderoperationiscarriedoutinInt,(a/b)∗b+(a%b)=aappliestothevaluecalculated
by the remainder operator. It therefore follows, that the +/- sign of the remainder is the same
as the +/- sign of the dividends. Furthermore, the value of the remainder is always less than the
value of the divisor.
IftheremainderoperationisexecutedinFloat,theresultisthevalueofa−i∗b,wheretheinteger
value of i is selected so that the result carries the same +/- sign as a and the value of the result
is less than the value of b.
The calculations are carried out according to the rules listed in Section 3.3.3.
Ifthevalueoftheleftoperandhasareferencetype,oneofthefollowingoperatormethodsiscalled
for the left operand:
operator*(rhs) (multiplication),
operator/(rhs) (division)
operator%( rhs ) (remainder)
Here,thevalueoftherightoperandispassedasanrhsparameter. Thereturnvalueoftheoperator
method is the result of the operator.

57

<!-- Page 60 -->

### 3.6.6 Additive Operators

Additive expressions are left-associative.

add-expr:
mul-expr
add-expr add-op mul-expr
add-op:
+ | -

The additive operators, + and - , behave as follows depending on the type of the left operand:
If the value of the left operand is a simple type, it has to be an Int or Float . The value of the
right operand, then, must also be an Int or Float . If either of these conditions are violated, an
exception is triggered. Otherwise, the operation takes place in Int if both operands are of the Int
type, or in Float if at least one of the operands are of the Float type. In the second case, an
operand of the Int type is converted to Float before the operation.
The + operator adds the two operands.
The - operatorsubtracts dividesthe twooperands, wherethe left operand isthe minuend andthe
right operand, the subtrahend.

Ifthevalueoftheleftoperandhasareferencetype,oneofthefollowingoperatormethodsiscalled
for the left operand:
operator+(rhs) (addition)
operator-(rhs) (subtraction)
Here,thevalueoftherightoperandispassedasanrhsparameter. Thereturnvalueoftheoperator
method is the result of the operator.

### 3.6.7 Bitwise Shifts

Expressions for bitwise shifts are left-associative.

shift-expr:
add-expr
shift-expr shift-op add-expr
shift-op:
<< | >> | >>>

The shift operators, << (left shift), >> (signed right shift) and >>> (unsigned right shift) behave as
follows depending on the type of the left operand:
If the value of the operand is a simple type, both operands must be of the Int type and the
right operand must be nonnegative. If these conditions are not met, an exception is triggered.

58

<!-- Page 61 -->

Otherwise, the left operand is interpreted as a bit sequence, which is shifted by the number of
positions specified by the right operand either left ( ) or right ( and ). The and
<< >> >>> << >>>
operators fill vacated positions with 0-bits, while the >> operator fills vacated positions with the
value of the highest bit before the operation.

Ifthevalueoftheleftoperandhasareferencetype,oneofthefollowingoperatormethodsiscalled
for the left operand:
operator<<( rhs ) (left shift),
operator>>( rhs ) (signed right shift)
operator>>>( rhs ) (unsigned right shift)
Here,thevalueoftherightoperandispassedasanrhsparameter. Thereturnvalueoftheoperator
method is the result of the operator.

### 3.6.8 Relational Operators

15
Relational expressions are left-associative .

comp-expr:
shift-expr
comp-expr comp-op shift-expr
comp-expr instanceof shift-expr
comp-op:
< | > | <= | >=

The relational operators, < (less than), <= (less than or equal to), >= (greater than or equal to)
and > (greater than), behave as follows depending on the type of the left operand:
If the value of the left operand is a simple type, it has to be an Int, Float or Symbol. The value
of the right operand must be an Int or Float if the left operand is an Int or Float, or it must
be a Symbol if the left operand is a Symbol. If any of these conditions is violated, an exception is
triggered.
If none of the operands is Symbol, the relational operation takes place in Int if both operands are
of the Int type, or in Float if at least one of the operands are of the Float type. In the second
case, an operand of the Int type is converted to Float before the operation.
IftheoperandsareoftheSymboltype,acomparisonoftheinternalrepresentationofbothsymbols
takes place. The result of this comparison can only be guaranteed reproducible in an instance of
an OFML program.
The < operatoryieldstrueifthevalueoftheleftoperandislessthanthevalueoftherightoperand.
The operator yields true if the value of the left operand is less than or equal to the value of the
<=
right operand.
15
Notethatconsecutivelywrittenrelationalexpressionsdonotfollowcommonmathematicalsyntax: 0 < x < 5
isinterpretedas(0 < x) < 5andalwaysreturnsthevalueof1.

59

<!-- Page 62 -->

The operator yields true if the value of the left operand is greater than or equal to the value of
>=
the right operand.
The > operator yields true if the value of the left operand is greater than the value of the right
operand.
If the relational operator does not yield true, it yields false.
Ifthevalueoftheleftoperandhasareferencetype,oneofthefollowingoperatormethodsiscalled
for the left operand:
operator<( rhs ) (less than),
operator<=( rhs ) (less than or equal to),
operator>=( rhs ) (greater than or equal to),
operator>( rhs ) (greater than)
Here, the value of the right operand is passed as an rhs parameter. The return value of the
operator method is interpreted in test context and converted to a logical value as described in
Section 3.6.1 16 .

Type Verification

As the value of the right expressions, the instanceof operator expects a type derived from the
Type type (see Section 3.4.1). Otherwise, an exception is triggered. The result of the instanceof
operator is true if

• theleftexpressionreturnsavalueofasimpletypewhosetypeisidenticaltothetypereturned
by the right expression, or
• the left expression returns a value of a reference type which is either identical to the type
returned by the right expression or has been derived from this.

Otherwise, the result of the operator is false.

### 3.6.9 Equality Comparisons

Equality comparisons are left-associative.

equiv-expr:
comp-expr
equiv-expr equiv-op comp-expr
equiv-op:
| |
== != ~=
16
Subsequently,thereturnvalueshouldthoughisnotrequiredtobeanIntvalue.

60

<!-- Page 63 -->

If the value of the right operand of the relational operators, (equality) and (inequality), is
== !=
, both operands are considered equal if the value of the left operand is also . The
NULL NULL ==
operator returns true in case of equality, otherwise it returns false. The != operator returns false
in case of equality, otherwise true.
Otherwise, the relational operators, , and (pattern match), behave as follows depending
== != ~=
on the type of the left operand:
Ifthevalueoftheleftoperandhasareferencetype,oneofthefollowingoperatormethodsiscalled:
operator==( rhs ) (equality),
operator!=( rhs ) (inequality),
operator =( rhs ) (pattern match)
Here,thevalueoftherightoperandispassedasanrhsparameter. Thereturnvalueoftheoperator
methodisinterpretedintestcontextandconvertedtoalogicalvalueasdescribedinSection3.6.1.
If the value of the left operand has a simple type, an exception is triggered in the case of the ~=
operator. In the case of the != operator, the result is the logical negation of the result of the ==
operator, applied to the same operands. The == operator behaves as follows:
If the value of the left operand is , the result is true if the value of the right operand is also
NULL
NULL, or false if the value of the right operand is not NULL.
If the value of the left operand is of the type, the value of the right operand also has to
Symbol
be of the type. Otherwise, an exception is triggered. The result is true if both symbols
Symbol
embody the same string, otherwise it is, false.
If the value of the left operand is of the Int or Float type, the value of the right operand also
has to be of the Int or Float type. Otherwise, an exception is triggered. The comparison takes
place in Int if both operands are of the Int type, otherwise it takes place in Float. In the second
case, any Int type operand is converted to Float. The result is true if both operands (also after
conversion, if one takes place) have the identical value, otherwise it is false.

### 3.6.10 Minimum and Maximum

Minimum and maximum operators are left-associative.

minmax-expr:
equiv-expr
minmax-expr minmax-op equiv-expr
minmax-op:
<? | >?

Forthe <? (minimum)and >? (maximum)operators,thefollowingequivalenciesapplyforprocess-
ing the minimum and maximum operators:
a <? b ≡ ( tmp = a , tmp = b , tmp < tmp ? tmp : tmp )
1 2 1 2 1 2
a >? b ≡ ( tmp = a , tmp = b , tmp > tmp ? tmp : tmp )
1 2 1 2 1 2
Here, tmp and tmp are unnamed variables created dynamically for the length of processing this
1 2
subexpression.

61

<!-- Page 64 -->

### 3.6.11 Bitwise Links

Expressions for bitwise links are left-associative.

bit-and-expr:
minmax-expr
bit-and-expr & minmax-expr
bit-xor-expr:
bit-and-expr
bit-xor-expr ^ bit-and-expr
bit-or-expr:
bit-xor-expr
bit-or-expr | bit-xor-expr

The bitwise link operators, (bitwise AND), (bitwise exclusive OR) and (bitwise OR), behave
& ^ |
as follows depending on the type of the left operand:
If the value of the operand is a simple type, both operands must be of the Int type. Otherwise,
an exception is triggered. The result is of the Int type.
Ifthevalueoftheleftoperandhasareferencetype,oneofthefollowingoperatormethodsiscalled
for the left operand:
operator&(rhs) (bitwise AND),
operator^(rhs) (bitwise exclusive OR),
operator|(rhs) (bitwise OR)
Here,thevalueoftherightoperandispassedasanrhsparameter. Thereturnvalueoftheoperator
method is the result of the operator.

### 3.6.12 Logical Links

Expressions for logical links are left-associative.

logic-and-expr:
bit-or-expr
logic-and-expr && bit-or-expr
logic-or-expr:
logic-and-expr
logic-or-expr || logic-and-expr

The && (logical AND) and || (logical OR) operators evaluate their left operands in test context.
If the value for the && operator is false, the right operand is not evaluated and the result of the
operator is false. Accordingly, the right operand is not evaluated and the result of the operator is
true for the || , operator if the left operand yields true. Otherwise, both operators evaluate their
right operands in test context and their result is equal to the value of the right operand.
Principally, the right operand is not evaluated if the result of the operator is determined by the
result of the left operand.

62

<!-- Page 65 -->

### 3.6.13 Conditional Expression

Conditional expressions are right-associative.

cond-expr:
logic-or-expr
logic-or-expr ? expr : cond-expr

For the conditional expression, the first operand (logic-or-expr) is evaluated in test context. If the
evaluation yields true, the second operand (expr) is evaluated and the result of the conditional
expression is equal to the value of the second operand. If the evaluation of the first operand yields
false, the third operand ( cond-expr) is evaluated and the result of the conditional expression is
equal to the value of the third operand.
Either the second or the third operand is evaluated, never both.

### 3.6.14 Assignment Operators

All assignment operators are right-associative.

assign-expr:
cond-expr
unary-expr assign-op assign-expr
assign-op:
= | += | -= | *= | /= | %= | <<= | >>= | &= | ^= | |=

The left operand of an assignment must be a variable, an index expression or a range expression.
Otherwise, a translation error occurs.
If the left operand is a variable, the value of the right operand is calculated by the = assignment
operator and the variable is assigned. This value is the result of the assignment operator.
If the left operand is an index or range expression, the value of the right operand is calculated
first by the assignment operator. Then, the subexpressions (sequence, index or indices) of the left
operandarecalculatedandtheindexorrangeoperatoriscalledtosetavaluetothevalueofright
operand as an argument. The value of the right operand is the result of the assignment operator.

Thecombinedassignmentoperators,*=,/=,%=,+=,-=,<<=,>>=,>>>=,&=,^=and|=firstcalculate
the value of the right operand. Then, the value of the left operand is calculated. Depending on its
type, processing continues as follows:
Ifthevalueoftheleftoperandhasasimpletype,thefollowingequivalenceappliestotheprocessing
of the combined assignment operator:
lhs ⊕ = rhs ≡ ( tmp = rhs , lhs = tmp = lhs ⊕ tmp , tmp )
1 2 1 2
Here, tmp and tmp are unnamed variables created dynamically for the length of processing this
1 2
subexpression. Subexpressions of the left operand (a) are calculated only once.

63

<!-- Page 66 -->

Ifthevalueoftheleftoperandhasareferencetype,oneofthefollowingoperatormethodsiscalled
for the left operand:
operator*=( rhs ) ( *= operator),
operator/=( rhs ) ( /= operator),
operator%=( rhs ) ( \%= operator),
operator+=( rhs ) ( += operator),
operator-=( rhs ) ( -= operator),
operator<<=( rhs ) ( <<= operator),
operator>>=( rhs ) ( >>= operator),
rhs ( operator),
operator>>>=( ) >>>=
operator&=( rhs ) ( &= operator),
operator^=( rhs ) ( ^= operator),
operator|=( rhs ) ( |= operator)
Here,thevalueoftherightoperandispassedasanrhsparameter. Thereturnvalueoftheoperator
method is the result of the combined assignment operator.

### 3.6.15 The Comma Operator

The comma operator is left-associative.

expr:
assign-expr
expr , assign-expr

Theleftoperandisevaluatedinsecondarycontext. Then,therightoperandisevaluated. Itsvalue
17
is the result of the comma operator.
Table3.1summarizesoncemoretheprecedenceandassociativityforalloperators. Here,thelowest
number represents highest precedence.

# 3.7 Packages and Namespaces

### 3.7.1 Module

Everytranslationunitformsamodule. Amodulebelongstoapackage,whichisoptionallyspecified
at the beginning of the module with the package statement (see Section 3.7.3).
17 Notethat,basedonthegrammardefinedhere,commaexpressionsincontextsinwhichthecommahasanother
syntactic meaning (such as in argument lists of function calls) must be placed within brackets in order to achieve
thetargetedeffect.

64

<!-- Page 67 -->

Operators Precedence Associativity
:: 1 left
() @() [] . 2 left
! !! ~ ++ -- + - $ 3 right
* / % 4 left
+ - 5 left
<< >> >>> 6 left
< <= > >= instanceof 7 left
== != ~= 8 left
>? <? 9 left
& 10 left
^ 11 left
| 12 left
&& 13 left
|| 14 left
?: 15 right
= *= /= %= += -= <<= >>= >>>= &= ^= |= 16 right
, 17 left

Table 3.1: Operators

A module forms a namespace, which implicitly contains all names defined within its package as
or private to the package (i.e. without or private). In addition to these, other
public public
names from other packages can be implicitly or explicitly imported (see Section 3.7.4), and new
names can be defined within a module.
Qualified access to names in the namespace is not possible.
If an attempt is made to explicitly reimport or redefine an explicitly imported name within a
module, a translation error occurs. Implicitly imported names can be imported implicitly more
than once and imported explicitly or defined no more than once.
An explicitly imported or defined name obscures all implicitly imported names of the same name.
Ifmultipleidenticalnamesareimplicitlyimportedfromdifferentpackages,theseimplicitlyImport
names are no longer visible.

Amoduleisconsideredloadedifithasbeentranslatedtothepointwhereallthedefinitionsonthe
module and class levels in it have been processed and the corresponding names can be referenced
by the compiler while translating other modules. Compound statements do not yet have to have
been translated.

### 3.7.2 Packages and Namespaces

The following namespaces exist In OFML: package (see Section 3.7.3), module (see Section 3.7.1),
class (see Section 3.8) and compound statement (see Section 3.5.3).

65

| Operators | Precedence | Associativity |
| --- | --- | --- |
| ::
() @() [] .
! !! ~ ++ -- + - $
* / %
+ -
<< >> >>>
< <= > >= instanceof
== != ~=
>? <?
&
^
|
&&
||
?:
= *= /= %= += -= <<= >>= >>>= &= ^= |=
, | 1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17 | left
left
right
left
left
left
left
left
left
left
left
left
left
left
right
right
left |

<!-- Page 68 -->

The namespaces of packages and classes from a hierarchy, where the individual components of a
name are separated by double colons . If such a name begins with , the search begins in the
:: ::
root package, otherwise it begins in the package to which the translated module belongs. If the ::
operatorislocatedinthemiddleofaname, theidentifierspecifiedtotherightofitissearchedfor
in the package or class specified to its left. Searching for names if :: is not present is subject to
other rules (see Section 3.7.5). The syntax for names is:

name:
ident
qualified-name
fully-qualified-name
fully-qualified-name:
:: ident
:: qualified-name
qualified-name:
name-qualifier :: ident
name-qualifier:
ident
name-qualifier :: ident

If using a not fully qualified name, the first component must be a class that has been define in the
package to which the translated module belongs or a direct subpackage of this package.
For(qualified)accesstoanamethathasnotyetbeenloaded,anattemptismadetoloaditintothe
corresponding package. For unqualified names, this is the package to which the accessing module
belongs. For qualified names, it is the package that is specified by the qualifier. For loading, the
nameismappedthroughanimplementation-dependentmechanismtothenameofamodule,which
is then loaded.

### 3.7.3 Package Statement

The syntax of a package statement is:

package-stmt:
package fully-qualified-name ;

The module is translated in the specified package. If a package statement is not present, the
module is translated in the root package (or default package).
During the translation of the package statement, all names of the package defined within the
specifiedpackageas public orprivatetothepackage(i.e.without public or private )areimported
implicitly into the translated module. If a package statement is not present, the names of the root
package are imported implicitly.

66

<!-- Page 69 -->

### 3.7.4 Import Statement

The syntax of the import statement is:

import-stmt:
import fully-qualified-name ;
import :: * ;
import fully-qualified-name :: * ;

Thefirstformoftheimportstatementcheckswhetherthespecifiednamehasalreadybeendefined.
If not, the module that defines the name is determined through an implementation-dependent
mechanism. This module is loaded. Then, the name in the namespace of the importing module
is carried over. It is an error to import names whose last components are identical or are defined
within the importing module using this form of the import statement.
The second and third forms of the import statement first check that all modules of the specified
package have been loaded. Then, all of the names of this package defined as public are copied
into the importing module.
Importing a name that belongs to the same package as the importing module is not possible.
Note that the import statement imports the names into the namespace of the module and not
into that of the package to which the module belongs. This is necessary to prevent modules from
influencing each other reciprocally via import statements.

### 3.7.5 Static and Dynamic Bindings

In principle, names (both simple and (fully) qualified) are bound statically.
The point operator (see Sections 3.6 and 3.8.3) can be understood as a binary operator that
anticipates an object on the left and an identifier on the right. The identifier is bound to the
corresponding attribute of the object dynamically during runtime.
ThedefinitionofOFMLallowstheimplementationtogenerateattributesdynamicallyduringrun-
time. To check for undefined names, such attributes must be accessed via self (see Section3.8.3).
Binding a simple (unqualified) name takes place in the following order:

1. Within functions and methods, the name is searched for in the namespace of the innermost
compound statement. If the name is not found there, it is searched for from the inside
outwardsuntilthenamespacethatcontinuesthecompoundstatementthatformsthefunction
body is reached.
Ifthenamecannotbefoundwithinamethod(eitherinstance-orientedorclass-oriented),the
search continues in the namespace of the class to which the method belongs.
If the name cannot be found within a (common) function, the search continues within the
module in which the function was defined.

67

<!-- Page 70 -->

2. Within classes, the name is searched for in the namespace of the class. This contains all of
the names inherited from super-classes. If an instance-oriented method or variable from a
class-oriented method or a class-oriented initializer is found, a translation error is triggered.
Ifthenameisnotfoundwithinthenamespaceoftheclass,thesearchcontinuesinthemodule
in which the class was defined.
3. The search in the module takes place only in the namespace of the module. This contains
all imported names 18 .

### 3.7.6 Visibility and Accessibility

A simple name is visible if it can be bound according to the rules described in Section 3.7.5.
A qualified name is visible if it has not been defined as private or if a simple name consisting
only of the last component of the qualified name refers to the same definition and is visible.
A name to the right of the point operator is visible if it exists in the namespace of the class of the
object on the left side of the point operator and either has not been defined as private or access
takes place from within the same class.
The visibility of a simple name can be limited if it is covered by the same name in another
namespace, where the search is more likely to take place, as is described in Section 3.7.5.
A name is accessible if it is visible and access allows it. For unqualified access, every visible name
is also accessible. For qualified access or for access by means of the point operator, a visible name
may be inaccessible under some circumstances.
Accessibility and visibility are controlled by modifiers at the start of a definition. This section
describes only the modifiers for the definition of variables, functions and classes on the level of
modules. Modifiers for class attributes are described in Section 3.8.

global-modifiers:
global-modifiers global-modifiers
opt
global-modifier:
| |
final public private

The effect of the keyword on variables is that no new values can be assigned to them after
final
the initialization requested within the variable definition. With OFML, however, variables as
well as functions and classes on the level of modules can be redefined by different modules or by
18
Toconservememory,theimplementationdoesnotbyrequirementhavetoadopteverysinglenameatthetime
of translation. It is necessary, however, when removing a name, to search through all imported modules for the
nametoexcludethepossibilityofambiguity. Fornamesforwhichthishasalreadybeendone,anentrycanbemade
inthesymboltableofthemoduletominimizetheamountofprocessingnecessarythenexttimethesamenameis
used.
The same applies to names that belong to the package of the module but which were not defined by the module.
Namesthatweredefinedbythemodulearelocatedinthemodule’ssymboltableanyway.
Thesearchorderforaccesstoanunqualifiednameisasthenasfollows: 1.symboltableofthemodule,2.symbol
tableofthepackage,3.allimportedmodules.

68

<!-- Page 71 -->

retranslatingthe(possiblymodified)samemodule, inwhichcasethevalueofthevariablesdefined
with can also change.
final
Classes defined as final cannot be used as super-classes of other classes.
For function definitions, final cannot be applied.
Variables in which functions and classes are stored are defined implicitly as .
final

Variables, functions and classes defined as public are accessible in all modules, even in those of
other packages.

Variables, functions and classes defined as private are visible and accessible only within their
defining modules.

If a variable, function or class is definedas neither public nor private , it is handled asprivate to
the package. Names defined in this manner are generally visible, but accessible only from modules
19
belonging to the same package .

# 3.8 Classes

### 3.8.1 Class Definitions

Class definitions define new reference types and describe their implementation.

class-def:
global-modifiers class ident super-class class-body
opt opt

### 3.8.2 Super-classes

super-class:
: ident

Optionally,thenameofasuper-classcanbespecifiedinaclassdefinition. Thespecifiedsuper-class
cannot be defined as final. If a super-class is not specified, the class automatically inherits from
the root class (see Section 3.3.2).
Object
If the super-class is defined within the same translation unit, its definition must appear before
the definition of the derived class. Furthermore, the constraint on using super-classes, which is
described in Section 3.1.2, must be observed.
A class inherits all attributes not defined as private from its super-class. These are placed in the
namespace of the subclass and are thus accessible in the subclass. Attributes of the super-class
defined as private are not visible in the subclass.
19
Eventhoughthesenamesarevisibletoimportstatementsforimportingallthenamesofapackage(inasterisk
form),theseimportstatementsdonottrytoaccessthem(importthem).

69

<!-- Page 72 -->

### 3.8.3 Attribute

The body of a class definition consists of a sequence of attribute definitions and class-oriented
initializers.

class-body:
member-def-stmts
{ }
opt
member-def-stmts:
member-def-stmts member-def-stmt
opt
member-def-stmt:
field-def
method-def
static-initializer

### 3.8.4 Data Fields

field-def:
field-modifiers init-expr-list
var ;
opt
field-modifiers:
field-modifiers field-modifiers
opt
field-modifier:
| | | |
public protected private final static

The syntax for defining data fields is the same as the syntax for defining variables (see Section
3.5.1) except that the and modifiers are additionally allowed.
protected static
The initialization of class-oriented data fields takes place immediately after the module that con-
tainstheclassdefinitionisloaded. Theinitializationofinstance-orienteddatafields, includingthe
evaluationoftheinitializationexpression,takesplaceintheorderinwhichtheyoccurimmediately
after a new instance is created and before any method is called.
initialize()
Data fields defined as static describe class-oriented variables that can exist only once per class.
Otherwise, they are instance-oriented variables, which are created new for every instance of the
class.
Datafieldsdefinedasfinalcannotbeassignednewvaluesaftertheinitializationrequestedwithin
the variable definition.
Data fields defined as public are accessible from all modules, even those from other packages.
Datafieldsdefinedas protected aregenerallyvisible,butareaccessibleonlyfrommethods,class-
oriented initializers and initialization expressions from data fields of the same class or from classes
derived from this class.
Datafieldsdefinedas private arevisibleandaccessibleonlyinmethods,class-orientedinitializers
and initialization expressions from data fields of the same class or from classes derived from this
class.

70

<!-- Page 73 -->

Data field defined as private to the package (i.e. without one of the keywords, ,
public protected
or ), are generally visible, but are accessible only from methods, class-oriented initializers
private
and initialization expressions from data fields of the same class or from classes derived from this
class as well as from all modules belonging to the same package.

Methods

method-def:
method-modifiers func method-name ( param-list ) compound-stmt
opt opt
method-modifiers func method-name ( param-list , ... ) compound-stmt
opt
native method-modifiers func method-name ( ) ;
opt
method-modifiers:
method-modifier method-modifiers
opt
method-modifier:
| | | |
public protected private final static
method-name:
ident
method-operator
operator
method-operator:
++ | -- | !! | ~ | * | / | % | + | - | << | >> | >>>
< | <= | >= | > | == | != | ~= | & | ^ | |
*= | /= | %= | += | -= | <<= | >>= | >>>= | &= | ^= | |=

Thesyntaxfordefiningmethodsisthesameasthesyntaxfordefiningnamedfunctions(seeSection
3.5.1) except that modifiers and special names for redefining operators are additionally allowed.
Methods defined as static describe class-oriented methods that cannot access instance-oriented
variables. Class-oriented methods are called in conjunction with the type (see below). Otherwise,
itisaninstance-orientedmethod,whichiscalledinreferencetoaspecificobjectthatisaninstance
of the class or an instance of a class derived from this class.
Methods defined as final cannot be redefined in subclasses.
The modifiers for controlling access have the same meaning as for data fields (see above).

Redefinition of Operators

Most of the operators supported by the OFML grammar can be redefined for reference types. To
doso,instance-orientedmethodshavingnamescombinedfromtheoperatorkeyword,followedby
the operator being redefined, must be defined in the corresponding class definition. The number
of parameters to be declared for operator methods is defined in Section 3.6.
If an operator method is defined as static (class-oriented) or defined with an unallowed number
of parameters, a translation error occurs.

71

<!-- Page 74 -->

Constructors

Constructors are never defined explicitly, but instead are always created automatically. User-
definedoperationsforinitializinginstancescantakeplacewithinthespecial initialize() instance
method, which is passed to the arguments that are passed to the constructor. If an initialize()
method is defined, it is called in the constructor automatically. If an initialize() method is
not defined, no arguments may be passed to the constructor. initialize() methods from super-
classes are not called automatically. Such calls must take place explicitly in the initialize()
methods of their corresponding subclasses!

Class-oriented Initializers

static-initializer:
static compound-stmt

Class-orientedinitializersconsistofthe static keyword,followedbyacompoundstatement. Class-
orientedinitializersareprocessedintheorderinwhichtheyoccurwithinthemoduletogetherwith
otherexecutablestatementsonthemodulelevelandinitializationsofclass-orientedvariablesafter
the module that contains the class definition is loaded.
The following example illustrates this concept:

public class MyInt {
private var value = 0; // instance variable
private static var num; // class variable
public func initialize() { // initialization method
numInts++;
}
public func getValue() { // normal instance method
return (value);
}
public func incr(i) {
value += i;
}
public static func getNum() { // class method
return (num);
}
static { // class-oriented initializer
num = 0;
}
}

Access to Attributes

Within instance methods of the same class, access to attributes is in general direct, meaning it
takes place within the current namespace. Alternatively, instance variables and methods can be

72

<!-- Page 75 -->

accessed using the special keyword and of the ”‘ ”’ access operator. If instance variables are
self .
created dynamically by the implementation, as is the case with child objects in OFML, must
self
be used to access them. Accordingly, in the example above, return (self.value); could have
been written instead of return (value); .
Access to instance methods and variables takes place via the ”‘ . ”’ operator. In this case, the
left operand is any expression, the type of which must be shared by the attribute, and the right
operand is the name of the attribute, e.g. .
i.getValue()
Accesstoclassmethodsandvariablestakesplaceviathe”‘ :: ”’operatoraccordingtotherulesfor
qualifiednames(seeSection3.7.2),wheretheclassnameisusedasaqualifier,e.g. MyInt::getNum() .

# 3.9 Predefined Functions

### 3.9.1 Standard Functions

Standard functions are defined in the ::cobra::lang package.

typeOf(pObject(Object)) → Type
ThetypeOf()functionanticipatesanyvalueofasimpletypeorreferencetypeasanargument
and returns the type of the argument.

### 3.9.2 Numerical Standard Functions

All predefined numerical standard functions are defined in the ::cobra::math package.

Error Handling

Range Errors: If an argument of a numerical standard function is outside the definition range
of the function, an exception is triggered.

Overflow and Underflow Errors: An overflow or underflow error occurs if the result of a
functioncannotberepresentedasFloat. Ifanoverflowoccurs(meaningtheamountoftheresultsis
sogreatthatitcannotberepresentedinaFloat),thefunctionreturnsthevalueFloat::HUGE_VAL
with the same +/- sign as the correct value of the function (except in the case of tan()). In the
case of an underflow, the result is 0.

Argument Conversion

If an Int value is passed to one of the numerical standard functions instead of a Float value, the
Int value is converted implicitly by the function into a Float value.

73

<!-- Page 76 -->

Trigonometrical Functions

acos(x(Float)) → Float
The acos() function computes the arc cosine of x in radians. An exception is triggered if x
is not in the interval [−1,+1]. The result is in the interval [0,π].
asin(x(Float)) → Float
The asin() function computes the arc sine of x in radians. An exception is triggered if x is
not in the interval [−1,+1]. The result is in the interval [−π/2,+π/2].
atan(x(Float)) → Float
The atan() function computes the arc tangent of x in radians. The result is in the interval
(−π/2,+π/2).
atan2(y(Float), x(Float)) → Float
The atan2() function computes the arc tangent of y/x in radians. It uses the sign of both
arguments to compute the quadrants of the return value. If both arguments are 0, an
exception is triggered. The result is in the interval [−π,+π].
cos(x(Float)) → Float
The cos() function computes the cosine of x (specified in radians).
sin(x(Float)) → Float
The sin() function computes the sine of x (specified in radians).
tan(x(Float)) → Float
The tan() function computes the tangent of x (specified in radians).
acosh(x(Float)) → Float
The acosh() function computes the hyperbolic arc cosine of x. If x is not in the interval
[1,∞), an exception is triggered.
asinh(x(Float)) → Float
The asinh() function computes the hyperbolic arc sine of x.
atanh(x(Float)) → Float
The atanh() function computes the hyperbolic tangent of x. If x is not in the interval
(−1,+1), an exception is triggered.
cosh(x(Float)) → Float
The cosh() function computes the hyperbolic cosine of x.
sinh(x(Float)) → Float
The sinh() function computes the hyperbolic sine of x.
tanh(x(Float)) → Float
The tanh() function computes the hyperbolic tangent of x.

74

<!-- Page 77 -->

Exponential Functions and Logarithmic Functions

exp(x(Float)) → Float
x
The exp() function computes the exponential function of x (i.e. e ).
frexp(x(Float)) → [Float, Int ]
The frexp() function breaks a floating-point number into a normalized fractions (frac) and
an integral power of 2 (exp), where x = frac·2 exp . Both values are returned as vector
[frac,exp].
If x is 0, both parts of the result are 0.
ldexp(x(Float), exp(Int)) → Float
The ldexp() function multiplies the floating-point number x by the integral power exp of 2.
log(x(Float)) → Float
The log() function computes the natural logarithm of x. If the argument is negative, an
exception is triggered. If it is 0, the result is −Float::HUGE VAL.
log10(x(Float)) → Float
The log10() function computes the base 10 logarithm of x. If the argument is negative, an
exception is triggered. If it is 0, the result is −Float::HUGE VAL.
modf(x(Float)) → [Float, Float ]
The modf() function breaks the argument into an integer part (int) and a fractional part
(frac),ofwhichbothhavethesamesignastheargument. Bothvaluesarereturnedasvector
[int,frac].

Exponential Functions

pow(x(Float), y(Float)) → Float
The pow() function computes x to the power of y. An exception is triggered if x is negative
and y is not an integer, or x is 0 and y is negative. The result is 1.0 if both x and y are 0.
sqrt(x(Float)) → Float
Thesqrt()functioncomputesthenonnegativesquarerootofx. Ifxisnegative,anexception
is triggered.

Rounding, Absolute Value and Remainder

ceil(x(Float)) → Float
The ceil() function computes the smallest integer not smaller than x.
fabs(x(Float)) → Float
The fabs() function computes the absolute value of x.
floor(x(Float)) → Float
The floor() function computes the largest integer not larger than x.

75

<!-- Page 78 -->

fmod(x(Float), y(Float)) → Float
For y is not equal to 0, the fmod() function computes the value x−i·y so that the result
for an integer i has the same sign as x and a magnitude less than the magnitude of y. If y
is 0, an exception is triggered.

76

<!-- Page 79 -->

# Chapter 4

# Basic Interfaces

The basic interfaces described below implement fundamental concepts on which the actual types
of the OFML standard are based. Such a type implements one or several of these basic interfaces.
Each interface is assigned an interface category (Appendix H). By means of the general method
for determining the category association of a type or an instance described below, it is possible to
determine asanalternativetodeterminingthetypeidentity whetheratypeimplementsaspecific
interface or whether an instance of the type provides the functionality of the interface.

# 4.1 MObject

The MObject interface defines the fundamental interfaces of all OFML types. Consequently, every
OFML type implements at least this interface.

### 4.1.1 Type Identity and Category Association

• getType() → Type
The function provides the direct type of the implicit instance.
• getClass() → String
The function provides the name of the direct type of the implicit instance.

Note: Equivalent to String(getType().getName()).

• isA(pType(Type)) → Int
The function verifies the association to a transferred type pType. isA() furnishes 1 if pType
is the direct type of the implicit instance or a super type of it. Otherwise, the result is 0.

77

<!-- Page 80 -->

• isCat(pCat(Symbol)) → Int
The function furnishes 1 if the implicit instance belongs to the transferred category.

Note: As a rule, a type inherits the association to categories from its direct super type. For this
reason, attention should generally be paid in overwriting the function that the inherited implemen-
tationofthefunctioniscalledforthetransferofacategorythatisnotdefinedbytheconcretetype
itself.

### 4.1.2 Instance Identity and Hierarchy

• final getName() → String
The function returns the absolute name of the implicit instance.
• final getFather() → MObject
The function provides a reference to the father object. If the implicit instance does not have
a father, the result is NULL.
• final getRoot() → MObject
The function furnishes a reference to the root instance of the hierarchy in which the implicit
instance is located.
• final getChildren() → MObject[]
The function returns a list of object references that represent the direct children of the
implicit instance. If no children are available, an empty list is returned.
• final getElements() → MObject[]
The function returns a list of object references that represent those direct children of the
implicitinstancethatarealsoelements. Ifnoelementsareavailable,anemptylistisreturned.
• final add(pType(Type) ...) → MObject
The function creates a child of the implicit instance of type pType and continues to register
it as element. The local name of the child is selected automatically. Should a type require
additional parameter for its instantiation, they must be specified with the add() call after
pType.
The return value of the function is a reference to the created object or NULL.
• final remove(pChild(MObject)) → self
The function removes the specified object, which is a child of the implicit instance, from the
listofchildrenoftheimplicitinstance. Ifitisanelementatthesametime,itisalsoremoved
from the list of elements.

78

<!-- Page 81 -->

# 4.2 Base

AsanextensionoftheMObjectinterface,theBaseinterfacealsorepresentsafundamentalinterface
of the OFML types that is implemented by most of the OFML types.
Every type that implements the Base interface also implements the MObject interface.

### 4.2.1 Instance Variables

• mIsCutable(Int)
The variable specifies the independence of the instance with respect to the cut operation of
the clipboard (setCutable() and isCutable() functions in section 4.2.2).
• [static] eps(Float) = 0.005
The static variable eps must be used for geometric relation operations due to the limited
presentation accuracy of floating point numbers in OFML. Neither this variable nor the
following ones may be redefined. Non-redefinable variables can be designated with final.
π
• [static] sPi4(Float) =
4
π
• [static] sPi2(Float) =
2
• [static] sPi(Float) = π
• [static] s2Pi(Float) = 2π

### 4.2.2 Selectability

• final selectable() → self
The function allows the selection of the implicit instance.
• final notSelectable() → self
The function prohibits the selection of the implicit instance. In the case of an attempted
selection of the implicit instance, the first instance that is selectable within the scope of an
upward traversing is selected.
• final hierSelectable() → self
The function allows the selection of all entities of the subhierarchy whose root object is the
implicit instance. Whether a single instance can actually be selected is determined by the
status that was set via selectable() or notSelectable().
• final notHierSelectable() → self
The function prohibits the selection of all entities of the subhierarchy whose root object is
the implicit instance. The prohibition applies to all entities of the subhierarchy, even if the
selection of an individual instance via selectable() is allowed in principle. Thus, notHierSe-
lectable() in reference to a single instance takes precedence over selectable().

79

<!-- Page 82 -->

• final isSelectable() → Int
The function returns True if the implicit instance can be selected. This is the case if se-
lectable() was called for the instance and was not called for an object in the hierarchy via
notHierSelectable() instance.
Entities can be selected initially.

### 4.2.3 Cuttability

• setCutable(pMode(Int)) → Void
The function determines the independence of the implicit instance with respect to the cut
operationoftheclipboardandsavesthetransferredmodeinthemIsCutableinstancevariable.
Possible values are:
-1 In general, the implicit instance may not be deleted.
0 The implicit instance itself may not be deleted, but it can be deleted within the scope
of a higher-level instance. In the case of an attempted cut operation of the implicit
instance, the operation is applied to the first instance in the course of an upward
traversing for which isCutable() furnishes 1.
1 The implicit instance can be deleted and copied to the clipboard. This is the initial
state.
2 The implicit instance can be deleted, but it may not be copied to the clipboard.

Example: Mode 2 is used for objects such as cornice profiles that are constructed with regard to
a set of base objects and, consequently cannot readily be copied to another spatial or topological
position.

• isCutable() → Int
The function queries the independence of the implicit instance with respect to the cut oper-
ation of the clipboard. It furnishes the value of the mIsCutable instance variable that can be
described using the setCutable() function.
• removeValid() → Int
The function returns True if the implicit instance may be deleted.
Entities can be deleted initially.
IncontrasttotheisCutable()function,whichspecifiesthefundamentalabilityofdeletingan
object and is called by the application prior to a cut operation on the selected object, the
removeValid() function is used for modeling dynamic aspects of the ability of deleting and is
called by father entities within the scope of REMOVE ELEMENT rules.

80

<!-- Page 83 -->

### 4.2.4 Visibility

• final hide() → self
The function hides the implicit instance, including its children and grandchildren. Hiding
entities does not have any influence on collision recognition.
• final show() → self
The function makes the implicit instance visible again if it was hidden.
• final isHidden() → Int
Thefunctionindicatesthroughitsreturnvaluewhethertheimplicitinstanceisvisible(0)or
hidden (1).

### 4.2.5 Resolution

The following functions can be used to set or query the object space resolution of an object. In
general, this applies to the mapping of an analytical or parametric primitive to a piece by piece
linear approximation. The direct conversion is done for geometric elementary types only (Chapter
7). All other types or entities merely pass on the resolution. Imported polygonal data records are
not effected.
Normally, the resolution should only be set directly for the root of an object hierarchy. However,
direct setting of the object space resolution for a non-root object is allowed.
The resolution is indicated by a floating point number r in the range 0.0 ≤ r ≤ 1.0. Where
0.0 represents the minimum resolution and 1.0 the maximum resolution. If the resolution 0.0 is
specified for a parametric primitive, its representation corresponds to the polygonal body that
results from the corresponding connection of the defining vertices. The initial resolution is 0.1.

• final setResolution(pRes(Float)) → self
The function sets the object space resolution for the subtree preset by the implicit instance.
This resolution continues to be inherited in the subtree. If an ancestor already contains an
explicitly assigned object space resolution, the recursive inheritance is ended at this position
and for this path of the subtree.
• final getResolution() → Float
The function returns the valid object space resolution for the implicit instance.

### 4.2.6 Change Status

• final setChanged() → self
The function explicitly marks the implicit instance as changed with respect to the instant
immediately after executing the initialization. An explicit call of setChanged() is necessary
if instance variables are directly written without other changing operations being performed
(e.g.,creationofchildren,move). Thechangestatusisevaluatedtoenableanefficientstoring
of instance hierarchies which is applied to clipboard and persistence operations.

81

<!-- Page 84 -->

• final setUnchanged() → self
The function resets the change status of the implicit instance to the status immediately
after executing the initialization. That is, the instance is now considered as unchanged with
respect to the instant immediately after the initialization.

### 4.2.7 Collision Detection

• final disableCD() → Void
The function deactivates the collision detection for the implicit instance. Afterwards, the
implicit instance, including its children, are ignored by the collision detection.
• final enableCD() → Void
The function (re-)activates the collision detection for the implicit instance.
• final isEnabledCD() → Int
Thefunctionfurnishes0,iftheimplicitinstanceisexcludedfromcollisiondetection,otherwise
it furnishes 1.

### 4.2.8 Dimensioning

• measure(pMode(Symbol)) → Void
Thefunctionactivatesthedimensioningoftheimplicitinstance. Ifnecessary, differenttypes
of dimensioning can be selected using the implementation-dependent value pMode. If only
one type of dimensioning exists, the parameter may be ignored.
The following symbols are predefined for the dimensioning:
– @ISO The dimensioning is done in meter.
– @INCH The dimensioning is done in inch.
• unMeasure() → Void
The function deactivates the dimensioning of the implicit instance.

### 4.2.9 Spatial Modeling

• final setPosition(pPosition(Float[3])) → self
1
The function unconditionally sets the local position of the implicit instance, i.e., no rules
are called and the degrees of translation freedom are ignored to the position pPosition. At
the same time, this position represents the move of the implicit instance compared with the
fatheroftheimplicitinstance. Initially, aninstancedoesnothaveamovewithrespecttoits
father. If no father exists, the world coordinate system serves as reference.
The function is used for the explicit positioning within functions.
1
Actually,thelocalcoordinatesystemismovedtotherespectivepositionrelativetothefather.

82

<!-- Page 85 -->

• final getPosition() → Float[3]
The function furnishes the current move of the implicit instance with respect to its father,
provided that he exists, or with respect to the world coordinate system.
• final translate(pVector(Float[3])) → self
The function conditionally moves the implicit instance by the vector pVector defined in the
worldcoordinatesystem. Theconditionalityofthemoveresultsfromapossiblerasterization
andsnappingfunctionality,providedthatitissupportedbytheOFMLruntimeenvironment,
translational degrees of freedom (setTrAxis()), as well as through the presence of TRANS-
LATE rules of the reason (Chapter 5). If TRANSLATE rules are defined for the implicit
instance, they are directly called after executing the translation.
Thefunctionisusedforinteractivepositioningviadirectmanipulationoruserinterface. The
pVectorvectoristransformedfromtheworldcoordinatesystemtothelocalcoordinatesystem
of the implicit instance under consideration of the current inherited and local modeling of
the implicit instance. This ensures an intuitive modeling via the translate() function.
• final moveTo(pPosition(Float[3])) → self
The function conditionally moves the implicit instance to the pPosition position defined in
the world coordinate system. The semantics of the function completely corresponds to the
call of translate() with the pPosition - getWorldPosition() vector.
• final setTrAxis(pAxis(Int)) → self
The function permits or prohibits the movability of the implicit instance for individual axes
of the local coordinate system. The pAxis parameter results from the addition of allowed
axes, whereby x, y and z-axis are represented by 1, 2 and 4. If pAxis features the value 0,
the object cannot be moved.
• final getTrAxis() → Int
The function furnishes the current movability of the implicit instance.
• final rotate(pAxis(Symbol), pArc(Float)) → self
2
The function conditionally rotates the implicit instance by the pArcangle defined in the
radiant measure with respect to the pAxis local coordinate axis. The conditionality of the
rotation results from a possible rasterization and snapping functionality, provided that it is
supported by the OFML runtime environment, rotational degrees of freedom (setRtAxis()),
aswellasthroughthepresenceofROTATErulesofthereason(Chapter5). IfROTATErules
are defined for the implicit instance, they are directly called after executing the rotation.
pAxis is either @PX, @PY or @PZ as long as a rotation about the (positive) x, y or z-
axis occurs. Alternatively, a rotation about an opposite axis may be carried out. The
respective symbols are @NX, @NY and @NZ. The rotation about random axes is achieved
by corresponding consecutive rotations about the elementary axes.
In contrast to the translation, there is no function for unconditional setting for the rotation.
Thesettingofacertainorientationiscarriedouteitherinitially,i.e.,ifnorotationcompared
to the father has taken place, or through a subtraction of the actual orientation from the
orientation to be set. However, this does not invalidate the conditionality described above.
2
Actually,thelocalcoordinatesystemisrotatedaccordingly.

83

<!-- Page 86 -->

Within the scope of rules, the correction of orientations is carried out through a new appli-
cation of the rotate() function. In this case, the OFML runtime system must ensure that
ROTATE rules are not called again.
A general issue concerning the rotation about cartesian axes consists of the overlay of the
three elementary rotations. For this reason and to ensure the correct functioning of the
rotations, it is recommended to release only one rotational axis at a time (setRtAxis()).
The function is used for the interactive positioning via direct manipulation or user interface
as well as for the explicit positioning within functions.
• final getRotation(pAxis(Symbol)) → Float
The function furnishes the current rotation in the radiant measure by the rotational axis
specified through pAxis.
Attention: Ifaninstancewasrotatedaboutmorethanoneaxis,getRotation()couldfurnish
unexpected results. This is due to the principal problem of overlay of the three elementary
cartesian rotations.
• final setRtAxis(pAxis(Int)) → self
Thefunctionpermitsorprohibitstheabilityofrotationoftheimplicitinstanceforindividual
axesofthelocalcoordinatesystem. ThepAxisparameterresultsfromtheadditionofallowed
axes, whereby x, y and z-axis are represented by 1, 2 and 4. If pAxis features the value 0,
the object cannot be rotated.
It should be possible to rotate entities about a maximum of one rotation axis. However, this
axis may be changed over time.
• final getRtAxis() → Int
The function furnishes the current ability of rotation of the implicit instance.
• final getLocalBounds() → Float[2][3]
The function furnishes the minimum axis-orthogonal delimiting volume of the implicit in-
stance in reference to its local coordinate system. The delimiting volume includes children
and the origin of the local coordinate system.
Thereturnvalueisavectorconsistingoftwoelements. Thefirstelementistheminimumco-
ordinatewithinthelocaldelimitingvolume. Thesecondelementisthemaximumcoordinate
within the local delimiting volume.
The OFML runtime environment must ensure that the local delimiting volume is always in
a consistent state.
• final getLocalGeoBounds() → Float[2][3]
The function furnishes the minimum axis-orthogonal delimiting volume of the implicit in-
stance with reference to its local coordinate system. In contrast to getLocalBounds(), the
delimiting volume does not include the origin of the local coordinate system and children
with empty geometry.
• final getWorldBounds() → Float[2][3]

84

<!-- Page 87 -->

The function furnishes the minimum axis-orthogonal delimiting volume of the implicit in-
stance in reference to the world coordinate system. The delimiting volume includes the
children.
Thereturnvalueisavectorconsistingoftwoelements. Thefirstelementistheminimumco-
ordinatewithintheglobaldelimitingvolume. Thesecondelementisthemaximumcoordinate
within the global delimiting volume.
The OFML runtime environment must ensure that the global delimiting volume is always in
a consistent state.
• final getWorldGeoBounds() → Float[2][3]
The function furnishes the minimum axis-orthogonal delimiting volume of the implicit in-
stance in reference to the world coordinate system. In contrast to getWorldBounds(), the
delimiting volume does not include children with empty geometry.
• final getDistance(pDirection(Symbol)) → Float
The function determines the shortest distance of the implicit instance along one of six di-
rections, starting with the local delimiting volume to another instance in the scene. The
direction indicated by pDirection features one of the following values: @NX, @PX, @NY,
@PY, @NZ, @PZ.
Thereturnvalueisthedistance,providedthatanotherinstancecouldbedetermined,or−1.

### 4.2.10 Rule Call

• final callRules(pReason(Symbol), pArg(Any)) → Int
The function triggers the execution of the rules defined for the reason pReason. pReason is
either a predefined rule (Chapter 5) or a user-defined rule.
The explicit call of a predefined rule reason can be used, for example, to explicitly request
a snapping behavior that is implemented by means of a TRANSLATE rule, following the
initialpositioningoftheinstance. Ifapredefinedrulereasoniscalled,pArgmustcorrespond
to the specification in Chapter 5.
The explicit call of a user-defined rule reason via callRules() is the only possibility to bring
the corresponding rules to be executed. A principal application of user-defined rule reasons
consist of enabling a communication between entities that is more flexible and robust than
the communication via the functions of types. In this case, the necessity for checking type
compatibility is not required; if no rules are defined in a type for a certain reason, no error
will occur. However, calling a function for a type that does not define this function, will
always result in an error.

Example: Spotlightscanbeplannedforasystem, buttheycannormallynotbemoved. However,
as children of a very few types they can be moved in a specific way. In the TRANSLATE rule of
the spotlight, the move is reset so that the spotlight is not moved. This is followed by a call of
thefatherwithcallRules(),wherebytheuser-definedreasonMOVE SPOT,thedesirednewposition
of the spotlight, and the spotlight itself are transferred. If the father permits a movement of the
spotlight,itcancontrolitwithacorrespondingMOVE SPOTrule. Otherwise,thespotlightremains
unchanged.

85

<!-- Page 88 -->

The return value is −1 if a rule of the reason pReason failed. Otherwise, the return value is
0.

### 4.2.11 Dynamic Properties

Featuresofaninstancewhosecurrentcharacteristicsarestoredinacorrespondinginstancevariable
(and that can be assigned or queried using corresponding set and get functions), are referred to
as static features or properties of the instance. In contrast, it is sometimes necessary to assign
dynamic properties and values to an instance for the duration of its existence. For this purpose,
the Base interface manages an internal hash table for each instance, in which such properties can
be set up. A property is defined and addressed via its unique key of the Symbol type. The value
for the key entered in the table can come from a simple type or from the reference types String,
Vector, List, and Hash.

• getDynamicProps() → Hash
The function furnishes the (reference to the) hash table for dynamic properties.

### 4.2.12 2D Representation and ODB

ObjectsthatimplementtheBaseinterfacecanbeequippedwitha2Drepresentation. Itiscreated
by means of the getOdbInfo(), getPictureInfo(), invalidatePicture() methods and the methods for
creating primitive 2D objects, as described in Appendix B.
2DsymbolscreatedviagetOdbInfo()andgetPictureInfo()cannotbeusedsimultaneously. Ifahash
table is returned by getOdbInfo(), a symbol that may be specified by means of getPictureInfo()
will not be represented.

• getOdbInfo() → Hash
The function is called by the core system at random times to query the current ODB infor-
mation that is required for the creation of a 2D symbol or the 3D geometries. The function
returns the ODB information in form of a hash table or NULL if no ODB information is
available for the object. The use of ODB is described in [ODB].
• getPictureInfo() → Vector
The function is called by the core system at random times to query information about the
2D symbol that is to be used for this object. The return value is a vector consisting of three
elements:
– ThefirstelementiseitherNULL,inwhichcasethisobjectdoesnotfeaturea2Dsymbol,
orthefullyqualifiednameofthesymbol. Thenameisusedtosearchforacorresponding
EGM,DMP,orFIGsymbol. Thefirstsymboltobefoundisusedfortherepresentation
in2Dmode. Ifnosymbolcanbefound, asymboliscreatedautomaticallybasedonthe
3D geometries for the object and all its current child objects.

86

<!-- Page 89 -->

– The second element is either @TRAVERSAL STOP or @TRAVERSAL CONT. It de-
termines whether possibly available symbols of child objects should be represented
(@TRAVERSAL CONT) or not (@TRAVERSAL STOP) for the representation in 2D
mode. If a symbol is automatically generated for the object, this value should always
be set to @TRAVERSAL STOP.
– Thethirdelementiseither@SHARE ONor@SHARE OFF.Itdetermineswhethersym-
bols with identical names from different objects should be used jointly (@SHARE ON)
or whether the symbol for each object is loaded and generated again (@SHARE OFF).
In general, @SHARE ON should be specified in this case for symbols that are loaded
from files. For objects whose 2D symbol is automatically generated, @SHARE ON can
bespecifiedifdifferententitieswithidenticalsymbolnamearealwaysequippedwiththe
same3Dgeometry,otherwise@SHARE OFFshouldbeused. Butitshouldbeobserved
thatchildobjects(e.g., accessories)becomepartofthesymbol, sothatforthejointuse
of automatically generated symbols for objects, that may possibly contain additional
children, these children are visible either for all objects or for none.
Bydefault,getPictureInfo()returnsthetypeofclassoftheimplicitinstanceassymbolname,
allows the traversing of child objects with representation in 2D mode, and prevents the joint
utilization of symbols.

Note: A change in the child objects does not automatically cause a matching of an automatically
generated symbol.
If possible, the automatic generation of 2D symbols should be abandoned since it can lead to no-
ticeable delays, especially with repeated application, and the result is usually unsatisfactory for an
effective planning in 2D mode.
• invalidatePicture() → Void
The function must be called after properties of the object that affect the 2D or 3D geometry
have changed. The core system discardsall savedinformation (return values of getOdbInfo()
and getPictureInfo() as well as 2D symbols (ODB, EGM, DMP, FIG, and generated ones)).
If required, this information is queried again and the 2D symbols are generated.
• createOdbObjects(pUpdate(Int)) → Void
ThefunctiongenerateschildobjectsaccordingtothespecificationintheODB.IfthepUpdate
parameter is 0 (false), all currently existing child objects generated by the ODB are deleted
and then recreated. If the pUpdate parameter is 1 (true), a matching of the existing child
objects generated by the ODB is carried out.

Note: InthecurrentOFMLimplementationofEasternGraphicsGmbH,allchildobjectsgenerated
by the ODB are deleted independent of the Parameter pUpdate parameter, and then recreated by
the ODB.

# 4.3 Material

The Material interface defines the functions for processing material properties (surface properties)
on the basis of material categories. All types whose entities can be assigned material properties

87

<!-- Page 90 -->

must implement this interface.
All furniture or furniture components whose materials should be processed similarly due to func-
tional and/or aesthetic viewpoints are combined in a material category. An instance may belong
to one or several material categories. Material categories are designated through symbols.
Predefined material categories are listed in Appendix H.

Example: Typical material categories are corpus, front, base, tabletop. Entities of a cabinet type with
doors and/or drawers would then belong to the categories corpus, front and base while the child entities,
for example, that implement the corpus belong only to the corpus category. The corresponding OFML
material categories could be: @CORPUS, @FRONT, @BASE and @TOP.

Note: The universally valid @ANY material category is predefined (function setCMaterial()) and may
not be used in a different capacity.

Foreachmaterialcategory,alimitedsetofpossiblematerialsisspecifiedthatisalsodesignatedby
symbols (getMatCategories() function). Material designators are unique across all material cate-
gories. Thevisualpropertiesofamaterialarespecifiedinaseparatefilewhoseformatisdescribed
in Appendix D.2. Each material designator must be assigned a material name (getMatName()
function) to be able to read the corresponding material description file during runtime by using
the name.

Example: The materials ”gray laminate” and ”light beech veneer” are intended for the corpus category,
and only the ”light beech veneer” material for the front category. Possible designators for these materials
3
are@LGrayor@VBlight . Correspondingmaterialnameswouldbe”graylaminate”or”lightbeech”and
the corresponding material description files graylaminate.mat or lightbeech.mat .

### 4.3.1 Material Categories

• getMatCategories() → Symbol[]
Itfurnishesthelistofmaterialcategoriesthatarecurrentlydefinedfortheimplicitinstance.
An instance for which no material categories are defined furnishes either an empty list or
Void. In the latter case, the defined material categories for the father instance should be
used for the implicit instance.
The number of material categories defined for the implicit instance can change dynamically
and, therefore, differentiate themselves from the set of all potentially possible material cate-
gories (getAllMatCats() function).
• isMatCat(pCat(Symbol)) → Int
It returns 1 if the transferred material category belongs to the material categories currently
defined for the implicit instance, otherwise 0.
3
Thematerialcodesalreadyinplaceinmanufacturingcompaniesareidealforuseassymbolicmaterialdesigna-
tors.

88

<!-- Page 91 -->

• getAllMatCats() → Symbol[]
It furnishes the list of all material categories that are potentially definable for the implicit
instance (see also getMatCategories() function).
• getCMaterials(pCat(Symbol)) → Symbol[]
Itfurnishesthelistofallmaterialsthatareapplicablewithinthetransferredmaterialcategory
fortheimplicitinstance. ThereturnvalueisoftypeVoidifthetransferredmaterialcategory
does not belong to the material categories currently defined for the implicit instance.

### 4.3.2 Materials

• setCMaterial(pCat(Symbol), pMat(Symbol)) → Int
It assigns the specified material to the implicit instance in the transferred material category.
Theoperationisrecursivelyappliedtoallchildrenandgrandchildren. Thefunctioniswithout
effectifneithertheimplicitinstancenoroneofthechildrenbelongstothetransferredmaterial
category. The return value is 1 if the material could be assigned to the implicit instance or
at least to one of its ancestors (child, grandchild, etc.) 0.
The predefineduniversallyvalid materialcategory @ANY can beused of explicitly assigning
a material withoutconsidering the association ofthe implicit instance to aconcrete material
category.
• getCMaterial(pCat(Symbol)) → Symbol
The function furnishes the material currently assigned to the implicit instance in the trans-
ferredmaterialcategoryoravalueoftheVoidtypeiftheimplicitinstancedoesnotcurrently
belong to the transferred material category.
• getMatName(pMat(Symbol)) → String
The function furnishes the material name to the transferred material or a value of the Void
typefortheimplicitinstanceifthematerialisunknown. Thestandardimplementationcalls
the function of the father of the same name.

# 4.4 Property

Properties are object features that can be changed interactively by the system user with the help
of suitable dialogs (property editors).The Property interface defines the functions for handling
properties. Properties can be associated with features in product databases (Chapter 9).

### 4.4.1 Specifying Properties

• setupProperty(pKey(Symbol), pDef(Any[5]), pPos(Int)) → Void
Thefunctioncreatesapropertywiththespecifiedkey(identifier)andthetransferredspecifi-
cation. Ifapropertywiththespecifiedkeyisalreadyregistered,itsspecificationisoverwritten
by the parameter values.
The definition of a property (pDef parameter) is a vector made up of five values:

89

<!-- Page 92 -->

pName(String) the name of the property (appears in the property editor). This can be a
wildcard that is resolved via an external resource file (Appendix D).
pMin(Any) lower (inclusive) limit of the value range
pMax(Any) upper (inclusive) limit of the value range or maximum length fir String
properties
pFmt(String) desired special input/output format (syntax and meaning according to
Appendix E.1)
pType(String) the type of property:
b boolean value
i integer
f real number
s string
ch choice list (choice list)
The type specification is followed by a space and then by the list
of choice values. Each choice value is either a string ID designated
(language-neutral) by a preceding @ character, or by a pair made
upofstringIDseparatedbyspacesandlanguage-dependentdesig-
nation(AppendixD).Thechoicevaluesareseparatedbyspaces. If
nolanguage-dependentdesignationisspecifiedforavalue,itisread
from language-dependent designation files by means of the string
ID.
chf Choice list via function
The type information is followed by the name of a function which,
when called for the implicit instance, furnishes the list of choice
values in the same form as the explicit information in a property
of type ch.
u Special type (user defined)
The type information is followed by a space and then by the ID
of the required special editor and (after an additional space) addi-
tional information for the special editor, if required.
Note: Itisnotguaranteedthatthespecialeditorisimplementedinthe
OFML runtime environment used at the time.

Besidestheactualpropertydefinition,thedesiredpositioninthepropertylistcanbespecified
inthepPosparameter. Thesamespecificationappliestothesettingofthepositionasofthe
setPropPosOnly() function which can be used to individually set the position for an existing
property.
Thevaluerangelimits,format,andpositionareoptional. Missinginformationaredesignated
by a parameter of type Void.
In the type ofthe implicitinstance, a set anda get methodcan bedefined foreach property:
– set<Key>(pValue(Any)) → Void
The function is called if the value of the <Key> property was changed.

90

<!-- Page 93 -->

Note: Generally,anassignmentofthevaluetoacorrespondinginstancevariableisperformed
inthisfunction. Anyadditionalsemantics,suchastheregenerationofgeometryorcorrespond-
ing collision tests, is reserved for the propsChanged() function.

– get<Key>() → Any
Thefunctionfurnishesthevalueforthe<Key>propertycurrentlystoredintheimplicit
instance.
Note: Generally, the function furnishes the contents of a corresponding instance variable.
AreturnvalueoftypeVoiddesignatesanon-specifiedproperty,e.g.,withoptionalfeatures.

• setPropPosOnly(pKey(Symbol), pPos(Int)) → Int
The function specifies the desired position in the property list for the property with the
specified key. If no property with the specified key is defined for the implicit instance, the
functioniswithouteffectandthereturnvalueisoftypeVoid. Ifapropertywiththespecified
keyisdefinedfortheimplicitinstance,theoldpositioninformationisoverwritten. IfpPosis
anintegergreaterthanorequalto0andthedesiredpositionwasalreadyassignedtoanother
property, then this and all the following properties in the position list are moved back by
one position. If pPos is of type Void or features the value −1, no special position is required
for the property. It is then filed in the property list according to the properties for which a
positionwasexplicitlyrequested. Thenewpositionofthepropertyisthereturnvalueor−1
if no special position is required.
• setExtPropOffset(pOffset(Int)) → Void
This function is used to assign an offset to the implicit instance for positions of externally
defined properties, i.e., of properties that are defined for the implicit instance by another
instancebesidestheimplicitinstance. Theoffsetindicatesthesmallestpositionnumberthat
may be used for externally defined properties.

Example: A typical example of externally defined properties are those that are defined for the
representation of product features from the product database for the implicit instance by a global
product data manager instance (Section 9.1).

• removeProperty(pKey(Symbol)) → Void
The function removes the property specified by the indicated key from the property list. If
nopropertywiththeindicatedkeyisdefinedfortheimplicitinstance,thefunctioniswithout
effect.
• clearProperties() → Void
The function removes all properties from the property list.

### 4.4.2 Querying Properties

• hasProperties() → Int
Thefunctionfurnishes1ifpropertiesaredefinedfortheimplicitinstance,otherwiseitreturns
0.

91

<!-- Page 94 -->

• hasProperty(pKey(Symbol)) → Int
The function furnishes 1 if a property with indicated key is defined for the implicit instance,
otherwise it returns 0.
• getPropertyDef(pKey(Symbol)) → Any[]
The function furnishes the definition of the property with indicated key. The structure of
the returned vector corresponds to the structure of the pDef parameter that was transferred
as property definition to the setupProperty() function. If no property with the indicated key
is defined for the implicit instance, the return value is of type Void.
• getPropertyPos(pKey(Symbol)) → Int
The function furnishes the position of the property with indicated key. If no special position
was requested for the property, the return value is −1. If no property with the indicated key
is defined for the implicit instance, the return value is of type Void.
• getExtPropOffset() → Int
This function is used to furnish the for positions of externally defined properties, i.e., of
properties that are defined for the implicit instance by another instance besides the implicit
instance. The offset indicates the smallest position number that may be used for externally
definedproperties. Thisoffsetshouldbecalledbyanexternalinstancebeforethedefinitionof
apropertyfortheimplicitinstanceandshouldbetakenintoconsiderationfortheassignment
of explicit positions.
If no other value was assigned using setExtPropOffset(), the default return value is equal to
0.
• getPropertyKeys() → Symbol[]
The function furnishes a list of the keys of all properties currently defined for the implicit
instance.
Atthesametime, thepropertiesaresortedinascendingorderaccordingtotheirexplicitpo-
sitions. Thepropertieswithoutexplicitpositionappearattheendofthelistinanundefined
order.
• getProperties() → String
The function furnishes a description of all properties currently defined for the implicit in-
stance. The format of this description is explained in Appendix E.2.
• getPropTitle() → String
Thefunctionfurnishesabriefdescriptionoftheinstanceforuseintheheaderlineofproperty
editors.

Note: Thetwofunctionsdescribedbeforehandareusedbythepropertyeditorstobuildupadialog
window.

92

<!-- Page 95 -->

### 4.4.3 Property Values

• getPropValue(pKey(Symbol)) → Any
The function furnishes the value currently stored in the implicit instance for the property
with the indicated key. If no property with the indicated key is defined for the implicit
instance, the return value is of type Void

Note: The function utilizes the get method of the property (see setupProperty() function). If the
typeoftheimplicitinstancedoesnotfeaturesuchamethod,thevalueisdeterminedfromthehash
table of the dynamic properties (see getDynamicProps() function at the Base interface).

• setPropValue(pKey(Symbol), pValue(Any)) → Int
The function assigns the implicit instance a new value for the property with the indicated
key.
If the property is associated with a feature in a product database, the global product data
manager (Chapter 9) evaluates relationships between properties and property values next
(consequently, other properties or their values may change). Next, the propsChanged() func-
tion (see below) for performing special processings is called. True is transferred for the
pDoChecks parameter. If the value assignment of the product manager or propsChanged()
was rejected, all properties are reset to the state saved at the start of the function and the
propsChanged() function is called again, whereby False is now transferred for the pDoChecks
parameter.
The return value of the function is True if the definition of one or several properties changed
or if properties were added or removed.

Note: The function uses the set method of the property (see setupProperty() function) for the
actualassignmentofthenewvaluetothecorrespondinginstancevariable. Ifthetypeoftheimplicit
instance does not feature such a method, the value under the key of the property is written in the
hash table of the dynamic properties (see getDynamicProps() function at the Base interface).

• propsChanged(pPKeys(Symbol[]), pDoChecks(Int)) → Int
The function performs special processings and checks after property values were changed.
The properties whose values changed are specified by their keys. The pDoChecks parameter
indicates whether checks need to be performed or whether it is only necessary to respond to
the change of property values, e.g., through geometry matching. The return value is 1 if the
new property values are valid, otherwise it is 0.

Note: The function is called at the end of the setPropValue() function. In general, matchings of
the geometry or the material properties of the implicit instance are carried in the function.

• changedPropList() → Symbol[]
The function delivers the reference to the list of properties whose values changed during the
processing of the setPropValue() function. The properties are recorded in the list based on
their keys.

93

<!-- Page 96 -->

Note: In general, the function is used only by product data managers (Chapter 9) during the
evaluation of knowledge on product data relationships within the setPropValue() function.
The list is emptied at the start of each execution of setPropValue().

### 4.4.4 Activation Status

A property can be active or not. For an active property, its value can be changed interactively.
For non-active properties, only their current values are displayed and they cannot be changed
interactively. The initial state following the definition of a property is ”active.”

• setPropState(pKey(Symbol), pState(Int)) → Void
Thefunctionsetstheactivationstatusofthepropertywiththeindicatedkeyfortheimplicit
instance to the transferred value. If no property with the indicated key is defined for the
implicit instance, the function is without effect.
• getPropState(pKey(Symbol)) → Int
The function furnishes 1 if the implicit instance features a property with the indicated key
and if it is active. The function furnishes 0 if the implicit instance features a property with
the indicated key and if it is not active. If no property with the indicated key is defined for
the implicit instance, the return value is -1.

### 4.4.5 Information about Properties and Property Values

• getPropInfo(pKey(Symbol), pPropValue(Any), pInfoType(Symbol)) → Any
The function furnishes the information of the requested type for the specified property value
for the implicit instance. The return value is of type Void if the instance does not feature
the specified property or if no information of the requested type is available.
Default implementations of this function delegate the call to the getPropInfo4Obj() method
of the OiProgInfo instance (if available) responsible for the instance, see Chapter 8.
The following standard information types are predefined:
@Picture
Name of the graphics file that represents the property value (String)
@Text
text description (String, can be text resource)
@HTML
URL of the HTML description (String)

# 4.5 Complex

TheComplexinterfacedescribesthenecessaryfunctionalityofcomplexobjects,i.e.,ofobjectsthat
are composed of one or several accessible subobjects (children). In principle, this applies to all
types whose entities can be combined, expanded or disassembled at runtime.

94

<!-- Page 97 -->

### 4.5.1 Spatial Model

On the one hand, the functions of this group serve the more effective access to the spatial di-
mensions of objects that would otherwise have to be determined by the more time-consuming
getLocalBounds() function of the Base interface. On the other hand, they allow for using dimen-
sions that deviate from the exact geometric dimensions according to getLocalBounds().

• getWidth() → Float
The function furnishes the width of the implicit instance.
• getHeight() → Float
The function furnishes the height of the implicit instance.
• getDepth() → Float
The function furnishes the depth of the implicit instance.

### 4.5.2 Dynamic Creation and Management of Children

• checkAdd((pType(Type), pObj(MObject), pPosRot(Any[2]), pParams(Any)) → Float[3]
Thefunctioncheckswhetheraninstanceoftheindicatedtypecanbeattachedtotheimplicit
instanceaschildand, ifpositive, furnishesavalidpositionforthechildinstance(inthelocal
coordinate system of the implicit instance). If no instance of the indicated type can be
attachedaschildorifnoopenvalidpositioncanbedetermined, thefunctionreturnsavalue
of type Void.
IfthepObjargumentisnotoftypeVoid, itspecifiesanalreadyexistinginstancethatshould
be enlisted to locate a position. If the pPosRot argument is not of type Void, it specifies a
suggested position and rotation with respect to the local coordinate system of the implicit
instance. Thefirstelementoftheparametervectorcontainsthesuggestedposition(Float[3])
and the second element the suggested rotation with respect to the positive Y axis. If the
pParamsargumentisnotoftypeVoid,itcontainsadditionalparametersfortheinitialization
function of the type pType.
Tocheckwhetheraninstanceofthetransferredtypeshouldbeadded,itmaybenecessaryto
generateatemporaryinstanceofthetypeduringtheexecutionofthefunction,e.g.,tobeable
to make statements about the child to be generated by using function calls on this instance.
Thewayinwhichsuchatemporarychildinstanceisgenerated, iscontrolledbytheso-called
Paste Mode which is assigned by means of the setPasteMode() function before checkAdd() is
calledbytheclient. Iftheinstancetobeinsertedrepresentsanarticle(seeArticleinterface),
a simple instantiation of the transferred type may sometimes not be sufficient; instead, the
temporary child instance must also accept the configuration of the article to be inserted.
For this purpose, the desired article specification is transferred by the client by calling the
setTempArticleSpec() function before calling checkAdd() of the implicit instance.
Sofarasthetypetobeinserteddefinesplanningcategories(AppendixH),theycanbetaken
into consideration during the implementation of checkAdd() functions.

95

<!-- Page 98 -->

Note: In general, this function is called by the runtime environment if the user has entered the
command for inserting an object of a selected type in the scene or in a selected object. If the
function furnishes a valid position, the runtime environment generates an instance of the indicated
typeinthenextstepandplacesitatthedeterminedposition. Ifthenewobjectcannotbeinserted
into the selected object, an attempt is made to insert it in its father instance, etc.

• setPasteMode(pMode(Symbol)) → Void
The function sets the Paste mode for inserting temporary child entities into the implicit
instance. The following modes are possible:
The child instance must be re-generated as instance of the type that was transferred to
@CR
the checkAdd() function. This is the default setting.
The child instance should be created as a copy of an already existing object whose rep-
@PA
resentation can be found on the clipboard of the application. In this case, the child in-
stanceisgeneratedbymeansofevaluatingtheclipboardusingtheglobaloiApplPaste()
function.
• getPasteMode() → Symbol
ThefunctionfurnishesthecurrentPastemodeforinsertingtemporarychildentitiesintothe
implicit instance.
• setTempArticleSpec(pArticle(Vector[2])) → Void
Thefunctionassignsthearticlespecificationtotheimplicitinstancewhichmustbeassigned
tothetemporarychildinstanceafteritscreation(seesetXArticleSpec()functionoftheArticle
interface,Section4.6). ThepArticleparametercontainsavectorwhosefirstelementliststhe
base article number, while the second specifies the variant code of the article.
• getTempArticleSpec() → Vector[2]
The function returns the article specification for the temporary child instance that was as-
signed with the setTempArticleSpec() function.
• setMethod(pMethod(String)) → Void
The function sets the method call, including the parameters according to the basic syntax
(Chapter 3), which should be executed after generating and initially positioning a child
instance following an execution of the checkAdd() function for this child instance.
• getMethod() → String
The function provides the code according to the basic syntax (Chapter 3), which should be
executed after generating and initially positioning a child instance following an execution of
the checkAdd() function for this child instance. If no method is to be executed, an empty
string is returned.

Note: The method call to be executed is provided by the checkAdd() function which is executed
beforehand. It contains actions that go beyond the positioning of the child instance, e.g., rotating
the child instance by a required angle.

96

<!-- Page 99 -->

• clearMethod() → Void
After generating a child instance, the function resets a method call to be executed for the
child instance, if necessary. In this case, an empty string is set as method call.
• addPart(pType(Type), pParams(Any)) → MObject
The function adds an instance of the specified type as a child to the implicit instance, if
possible. If the pParams argument is not of type Void, it contains additional parameters for
theinitializationfunctionofthetypepType. Ifnoinstanceofthespecifiedtypecanbeadded
as child, the function returns a value of type Void.

Note: The function utilizes the checkAdd() function for determining a valid position and upon the
returnofsuchapositionaftertheinitialpositioningperformsthecodespecifiedbythegetMethod()
function, if necessary.

• checkElPos(pEl(MObject), pOldPos(Float[3])) → Int
Thefunctionchecksthevalidityofthecurrentlocalpositionofthetransferredchildinstance.
The function furnishes 1 if the current position is allowed, otherwise it furnishes 0.

Note: The function is used primarily for checking the new position of a child instance after a
translation or rotation of the instance. Generally, a collision check is performed. Additional, type-
dependent checks are possible, e.g., monitoring for compliance of a specified grid. If necessary, a
correctionofthepositionmaybeperformedbeforethetransformationusingthepositiontransferred
in the pOldPos parameter, e.g., a setting to the next grid position.

### 4.5.3 Collision Check

• disableChildCD() → Void
The function deactivates the collision detection for children of the implicit instance which is
performed via checkChildColl().
• enableChildCD() → Void
The function (re-)activates the collision detection for children of the implicit instance which
is performed via checkChildColl().
• isEnabledChildCD() → Int
The function furnishes 1, if the collision detection for the implicit instance is activated,
otherwise it furnishes 0.
• isValidForCollCheck(pObj(MObject)) → Int
The function furnishes 1 if the specified (child) instance should be considered during the
collision check, otherwise it furnishes 0.

Note: The function is a hook function which is called by the checkChildColl() function. Standard
implementations of this function always deliver 1.

97

<!-- Page 100 -->

• checkChildColl(pObj(MObject), pExclObj(MObject[])) → MObject
Thefunctioncheckswhetheracollisionof thetransferred(child)instancewithother objects
is present. If the pExclObj argument contains a non-empty set of objects, they are excluded
from the collision check.
The function first checks for collision with the children of the implicit instance. The check
only takes place if the following conditions are met:
– isEnabledChildCD() of the implicit instance delivers True
– isValidForCollCheck() of the implicit instance delivers True for the transferred (child)
instance
– isEnabledCD() of the transferred (child) instance delivers True
The following children are excluded from the collision check:
– children for which the isValidForCollCheck() function of the implicit instance delivers
False
– children whose isEnabledCD() function delivers False
– children that are listed in the pExclObj argument
If isEnabledCD() of the implicit instance delivers True, the function of the father instance of
the same name is called next (if it exists and if its type implements the Complex interface).
The return value is the first located object with which the transferred instance collides or a
value of type Void if no collision was detected or if the collision detection is deactivated.

# 4.6 Article

The Article interface includes a set of functions that provide the necessary information about a
planning object from a commercial point of view.

### 4.6.1 Program Access

• getProgram() → Symbol
The function delivers the ID of the program (Appendix I) to which the implicit instance
belongs.

### 4.6.2 Structure of Order Lists

• setOrderID(pID(Symbol)) → Void
The function assigns a unique ID to the implicit article instance that is used in structures of
order lists for assigning an article item of the order list to the instance that represents the
article in planning.

98

<!-- Page 101 -->

The order ID is assigned to the article instance immediately following its generation and
is not changed as long as the article instance exists. If the position of the article in the
planning hierarchy changes (e.g., in grouping actions), the order ID is transferred from the
destroyedinstancetothenewlygeneratedcloneinstanceinthecut-and-pasteoperationthat
takes place.
• getOrderID() → Symbol
The function delivers the unique order ID of the implicit article instance.

### 4.6.3 Product Data

• getArticleSpec() → String
The function delivers the name of the article (base article number) to which the implicit
instance corresponds or a value of type Void if no article specification is available for the
implicit instance.
If the result of the function is a value of type Void, no entry is generated for the instance in
the order lists.
• getXArticleSpec(pType(Symbol)) → String
The function delivers the specification of the requested type for the article to which the
implicitinstancecorrespondsoravalueoftypeVoidifnoarticlespecificationoftherequired
type is available for the implicit instance.
The following specification types are predefined:
@Base
base article number, designates the model of the article without reference to a concrete
implementation/configuration (corresponds to the return value of getArticleSpec())
@VarCode
variant code, describes the concrete implementation/configuration of the article with
respect to the base article number.
@Final
final article number, designates the model of the article and describes its concrete im-
plementation/configuration

Note: Usually, the final article number consists of the base article number and the variant code.
However, this depends upon the underlying product data system. If it does not allow for such a
strict definition, variant code and final article number are identical.

• setArticleSpec(pSpec(String)) → Void
The function assigns a new base article number to the implicit instance.

Note: The function applies only for types whose entities can represent different article (numbers).
Assigninganewarticlenumbergenerallyleadstoachangeofcertainpropertiesoftheinstanceand,
if necessary, also to a new geometric representation.

99

<!-- Page 102 -->

• setXArticleSpec(pType(Symbol), pSpec(String)) → Void
The function assigns a new article specification of the specified type to the implicit instance.
The possible specification types are described under the getXArticleSpec() function. With a
transfer of an article specification of type @Base, the function behaves like the setArticle-
Spec() function above.

Note: Assigning a new final article number or a new variant code (specification types @Final or
@VarCode) generally leads to a change of certain properties of the instance and, if necessary, to a
new geometric representation.
• getArticleParams() → Any
The function furnishes the parameters of the implicit instance that should be used for de-
termining the article number (see getArticleSpec() function) in addition to the type of the
instance. The return value is a vector with the parameter values or a string that already
contains the parameter values that were converted into the respective storage format. If no
parametersarerequiredfordeterminingthearticlenumber, thefunctionfurnishesavalueof
type Void.
• getArticlePrice(pLanguage(String), ...) → Any[]
The function delivers price information for the implicit instance in the specified language.
If an additional optional parameter is given, it specifies the desired currency. However, the
price information does not have to be furnished in this currency by the function (if, for
example, the underlying product database cannot supply prices in this currency). In this
case,theclientofthefunctionmustperformaconversionintothedesiredcurrencybymeans
of conversion rates.
The return value is a list that contains the individual price components. Every list entry is
a vector consisting of three elements:
1. adescription(String)thatspecifiesthetypeorexistentialreasonofthepricecomponent,
e.g. the reason for a surcharge.
2. the selling price of the price component (Float)
3. the purchase price of the price component (Float)
Thefirstentryrepresentsanexceptionsinceitcontainstheappliedcurrency(String)instead
of the prices. The last entry of the list specifies the (accumulated) final price. The optional
entries in between specify the individual price components (base price, extra charges, dis-
counts, etc.). If such a price component contains the designator "@baseprice", then it is
explicitly designated as base price.

Note: Theexplicitdesignationofthebasepricecomponentcanbeusedbytherespectiveapplication
to treat the base price differently for the presentation of order lists.

ThefunctionfurnishesavalueoftypeVoid,ifnopriceinformationisavailablefortheimplicit
instance.
• getArticleText(pLanguage(String), pForm(Symbol)) → String[]

100

<!-- Page 103 -->

Thefunctionfurnishesatextdescriptionofthedesiredforminthespecifiedlanguageforthe
article that is represented by the implicit instance.
The pForm parameter may take on the following values:
– @ s short description
– @ l long description
The return value is a list of strings that contain the individual lines of the description or a
value of type Void if no article description is available for the implicit instance.

Note: The article description furnished by this function contains (typically in long form) only
information about the fixed features of the article. A description of the concrete current implemen-
tationsofthechangeable/configurablefeaturesofthearticleisfurnishedbythegetArticleFeatures()
function.

• getArticleFeatures(pLanguage(String)) → Any
The function furnishes a description in the specified language for the article represented by
the implicit instance, of the current implementation of the product properties that can be
changed/configured for the article.
The return value is a list of two-digit vectors whose first element (String) labels the feature,
while the second element contains the current value (as character string) of the feature. If
the pLanguage parameter contains a value of type Void, language-independent designators
arefurnishedforfeatureandvalue. ThefunctionfurnishesavalueoftypeVoid, ifnofeature
description is available for the implicit instance.
Calls of the function immediately following each other with different parameters for the
language furnish lists of identical length and contain the features in the same order. If no
language-independent designator is available for a value with a language parameter of type
Void for a feature, the corresponding entry in the return list is not a vector, but a value of
type Void.

Note: The language-independent designators (codes) furnished by the function with a language
parameteroftypeVoidaregenerallyusedbyexportroutinesoftheapplicationtogenerateacomplete
description of an article that can be exported to an external PPS, e.g., for order processing.

### 4.6.4 Consistency Check

• checkConsistency() → Int
The function checks the consistency and completeness of the planning element. If necessary,
corrections or additions are performed or error messages are generated.
If the higher-order instance that initiated the consistency check of the implicit instance,
created an error log, the error messages should be written into this error log; otherwise
they can be issued directly to the user by means of oiOutput(). The error log to be used
must be called using the getErrorLog() function of the global planning instance (OiPlanning
type, Section 8.1). The data structure of the error log specified for checkConsistency() is a

101

<!-- Page 104 -->

hash table, in which the corresponding messages for each article instance are entered as a
code under their order ID (see getOrderID() function). The value for this code is a list of
three-digit vectors:
1. the error message (String)
2. the name of the object that reported the error (String)
3. the name of the method by which the error was detected (String)

Note: If required, detailed reports for error analyses can be generated with the last two entries.

102

<!-- Page 105 -->

# Chapter 5

# Predefined Rule Reasons

This chapter contains a description of predefined rule reasons. The properties of the predefined
rule reasons are:

• They correspond to the fundamental basic interactions in their entirety, such as selecting,
moving, copying, inserting, etc.
• Theyarecalledautomaticallybytheruntimeenvironment,ifacorrespondingactionoccurred
(implicit call).
• They can also be called explicitly.

In addition, there may be user-defined rule reasons. The properties of user-defined rule reasons
are:

• They are always called explicitly.
• The definition of user-defined rule reasons does not violate the compatibility of OFML data.

# 5.1 Element Rules

### CREATE ELEMENT

The rules of the CREATE ELEMENT reason are called for an O object before an E object of T
E
type is generated as element of O. The corresponding interaction is the generation of objects in
general, e.g., byinsertinganobjectfromtheclipboard. TheparameteroftherulesistheT type.
E
Rules of this reason can be used to control the aggregation dynamically and dependent upon the
state of the O object. Reasons for the failure of such rules can be:

• Entities of the T type cannot be aggregated in O.
E
Example: Tabletop lamps cannot be planned in a carcass cabinet.

103

<!-- Page 106 -->

• Entities of the T type can be aggregated only in O if certain (geometric) rules are adhered
E
to, e.g., a linear dependency between the width of O and the width of the instance of T . If
E
such a condition is violated, the rule will necessarily fail.

Example: In general, only shelves with the corresponding width can be planned for a carcass
cabinet of a certain width.
• On principle, entities of the T type can be aggregated in O; however, an insertion would
E
create a conflict with already existing children.

Example: No more shelves can be planned for a carcass cabinet that already contains a shelf at
every grid position.
Inthesecasesfurtherprocessingofthelistofrulesisinterrupted,andnoinstanceofT aselement
E
of O is generated.

### NEW ELEMENT

The rules of the NEW ELEMENT reason are called for an O object before an E child of O is
accepted in the list of elements of O. According to Chapter 2, an element is a special child in
so far as elements from outside are accessible by O, i.e., they can be generated or deleted. The
corresponding interaction is the generation of objects in general, e.g., by inserting an object from
the clipboard. The rules of the NEW ELEMENT reason are called after the rules of the CRE-
ATE ELEMENTreasonhavebeencalled. Thegenerationofaninstancecannotbepreventedbya
NEW ELEMENT rule. Instead, the NEW ELEMENT reason offers expanded possibilities for the
derivation of functionality within the corresponding rules compared to the CREATE ELEMENT
reason. Since an actual instance is transferred as a parameter instead of a type, queries can be
implemented that go beyond comparing types, e.g., the query of type compatibility to abstract
super types, the query of geometric parameters, and other (type-dependent) queries.
The rule parameter is an already existing child of O that is to be incorporated as element of O. If
a rule fails, E is not incorporated.

Example: Theautomaticgenerationofcomponentssuchasmountingrailsthatarerequiredforfastening
add-on parts, can be implemented via NEW ELEMENT or CREATE ELEMENT.

### REMOVE ELEMENT

The rules of the REMOVE ELEMENT reason are called for an O object before an E element is
deleted. The corresponding interaction is the removal of objects in general, e.g., by operations
such as cutting or deleting.
TheruleparameterisareferencetothealreadyexistingelementE ofO thatistobedeleted. The
rule can fail if other elements in O depend upon E. If a rule fails, E is not deleted.

Example: A mattress box as an element of a bed cannot be deleted as long as it contains bed frame,
mattresses, head sections, back panels, etc.

104

<!-- Page 107 -->

# 5.2 Selection Rules

### PICK

TherulesofthePICKreasonarecalledafteranobjectwaschosenorselected. Thecorresponding
interaction is the selection of an object in general, e.g., in a direct-manipulative way (2D/3D
interaction) or via a graphical user interface. The rule parameter is of type Float[3] und indicates
the local coordinates at which the object was selected.
PICKrulescanbedefinedtogenerateaspecialfeedback,e.g.,thechangeinmaterialcharacteristics
or the geometry. Such a feedback is independent from the general feedback which is provided by
the OFML runtime environment. In addition, random actions can be triggered by a PICK rule,
e.g., the display of object properties within the graphical user interface or the change of the global
state.

### UNPICK

TherulesoftheUNPICKreasonarecalledafteranobjectwasdeselected,e.g.,byselectinganother
object. The rule parameter is not defined.
UNPICKrulesaregenerallyareversalofthecorrespondingPICKrules. Forexample,thefeedback
generated by the PICK rule can be reset.

# 5.3 Move Rules

### TRANSLATE

The rules of the TRANSLATE reason are called after an O object was moved. The correspond-
ing interaction is the translatory move of objects via direct or indirect manipulation. The rule
parameter is the local position of O before the move.
The translatory move of an object can be controlled at random through the definition of the
TRANSLATE rules, e.g.:

• homogenous or inhomogenous rasterization,
• limitation to a range,
• initiation of a collision detection with corresponding correction of the position,
• snapping to objects or positions.

The different possibilities can be combined within a single rule, for example, to enable multidi-
mensional moves. In addition, the father can be called within the rule and the rule functionality
can be delegated to it.

105

<!-- Page 108 -->

Moreover,O canadaptitselftothenewpositionatrandom. Thiscanrefertolocalpropertiessuch
as geometry or the properties of children, e.g., the position of a child relative to its O father. The
vector that results from the new and old position can be used to derive directional information
and, if required, applied.

Example: The shelves of a carcass cabinet can be moved in a grid of 32 mm, starting at a height of 80
mm. The maximum fitting height results from the inner height of the carcass cabinet minus 80 mm.

### ROTATE

The rules of the ROTATE reason are called after an O object was rotated. The corresponding
interaction is the rotary move of objects via direct or indirect manipulation. The rule parameter
is the local orientation of O along the employed rotary axis before the rotation.
The rotary move of an object can be controlled at random through the definition of the ROTATE
rules, e.g.:

• homogenous or inhomogenous rasterization,
• limitation to a range,
• initiation of a collision detection and corresponding correction of the orientation,
• snapping to objects or positions.

Thedifferentpossibilitiescanbecombinedwithinasinglerule, forexample, toenablearasterized
rotation within a certain range. In addition, the father can be called within the rule and the rule
functionality can be delegated to it.
Analogous to the TRANSLATE rule, an object can adapt itself at random to the new orientation.

Example: The door of a carcass cabinet can be opened at an angle from 0 to 90 degrees. At angles of
10 degrees or less, a snapping to 0 degrees is performed automatically. At angles of 80 degrees or more,
a snapping to 90 degrees is performed automatically. The snapping behavior can be used to simulate the
latching at the end positions.

### SPATIAL MODELING

The rules of the SPATIAL MODELING reason are called after an O object was moved indirectly,
i.e., shifted or rotated. An indirect move takes place if an ancestor (father, grandfather, etc.) was
panned or rotated. A match of O can take place again. The rule parameter is undefined.

Example: The door handles of a construction kit within a shelf plan are placed dependent upon the
fitting height of the construction kit. At a height of less than 1.40 m, it is placed at the top end of the
door. Otherwise, it is placed at the bottom end. This adjustment can be implemented automatically by
using a SPATIAL MODELING rule.

106

<!-- Page 109 -->

# 5.4 Persistence Rules

The persistence rules serve for the conversion of the instance variables from a representation that
is used at runtime to a persistent representation and vice versa. This includes, above all, the
conversion of object references to values such as String or Int that can be stored and restored.
Furthermore, especially the * EVAL rules can be used for adapting stored scenes by initializing
instance variables accordingly that did not exist so far.
The definition of persistence rules is required only in exceptional cases.
The rule parameter of persistence rules is undefined.

### START DUMP

The rules of the START DUMP reason are called before the generation of a persistent representa-
tion of the O object, e.g., within the scope of scenes/object saving or a clipboard operation (e.g.,
cutting, copying). Afterprocessingtherules, theinstancevariablesmustbeavailableinastorable
representation.

### FINISH DUMP

TherulesoftheFINISH DUMPreasonarecalledafterthegenerationofapersistentrepresentation
oftheOobjectanditschildren. Afterprocessingtherules,theinstancevariablesmustbeavailable
again in the representation that is required for the normal operating mode.

### START EVAL

TherulesoftheSTART EVALreasonarecalledbeforetheprocessingofapersistentrepresentation
of the O object, e.g., within the scope of loading a scenes/object saving or a clipboard operation
(e.g., inserting). The call is performed immediately following the generation of the O object and
before the assignment of attributes, children, etc.

### FINISH EVAL

TherulesoftheFINISH EVALreasonarecalledafterthegenerationofapersistentrepresentation
oftheOobjectanditschildren. Afterprocessingtherules,theinstancevariablesmustbeavailable
in the representation that is required for the normal operating mode.

Example: With a certain roll-container type, the new version can be used to optionally configure an
espagnolette. Consequently, this type defines an additional instance variable in the new version that
describes by means of a symbol whether the espagnolette is desired or not. A FINISH EVAL rule can be
used to ensure that saves of the old version can be post-initialized in this connection.

107

<!-- Page 110 -->

# 5.5 Other Rules

### SENSOR

TherulesoftheSENSORreasonarecalledifanyM objectwasmoveddirectly. Theruleparameter
is a reference to M.
Sensory objects, i.e., objects with at least a SENSOR rule, can autonomously respond to changes
of the environment.

Example: The door of a room opens automatically if an object is located in a circumcircle of 5 m.

### TIMER

TherulesoftheTIMERreasonarecalledifthetimeintervaldefinedintherespectiverulesignature
expired at least once. The number of passed intervals (typically 1 for time intervals that are not
toosmall)ispassedontotherule(s)asparameter. Aninstance(oratype)withatleastaTIMER
rule is time-dependent. By generating and removing time-dependent children, a dynamic indirect
time dependence of an object can be implemented.

Example: An instance of type clock shows the current time. A TIMER rule is used for updating.

### INTERACTOR

The rules of the INTERACTOR reason are called for the father of the interactor if an attempt to
select an interactor is made. They typically serve to activate the interactor (Section F.1).
The selected interactor is transferred as reference as the rule parameter.

Example: Designs can be mounted to an organizational wall at different positions. If interactors are
defined for these positions, the user can interactively select the desired mounting point.

108

<!-- Page 111 -->

# Chapter 6

# Global functions

# 6.1 Formatted Output

Some of the functions described below use special character strings to control the formatting. The
format character string contains two types of components: regular characters that are accepted
in the output without change, and formatting sequences that control the conversion of one of the
followingargumentsineachcase. Everyformattingsequencebeginswiththecharacter%andends
with a formatting character. The following optional characters can be used between the character
% and the conversion character in the sequence indicated here:

• Control characters (in random order) that modify the conversion:
- The converted argument is left-aligned.
+ The number is always indicated with a sign.
space If the first character is not a sign, a space is used as prefix.
0 Numbers are filled with zeros up to the width of the field.
\# Generates an alternative form of the conversion, dependent upon the formatting
character (see below). For o, the first character is a zero. For x or X, 0x or 0X are
prefixed for a result different than zero. For e, E, f, g, and G, the output always
contains a decimal point; for g and G, zeros at the end are not suppressed.
• A number that specifies the minimum field width. The number of characters output is at
least equal to the number of characters indicated, and more if required (i.e., characters will
neverbecutoff). Iftheconvertedargumentisshorter,itisfilleduptothewidthofthefield.
Alignment and fill characters are dependent upon the formatting and control characters.
• A period that separates the field width and the accuracy.
• Anumberwiththefollowingmeaning: For e , E or f thenumberofplacesbehindthedecimal
point. For g or G the number of significant digits. For integer values, the minimum number
of digits to be output. In the remaining cases, the number indicates the maximum number
of characters that are output by a character string.

109

<!-- Page 112 -->

In each case, can be indicated as field width or accuracy, so that the value is determined by the
*
next or the next two arguments that must be of type .
Int
Table 6.1 explains the formatting characters. A character that follows % and is not a formatting
character, represents an error.

Character Argument type Formatting
d , i Int decimal with sign
o Int octal without sign, leading zero optional
x , X Int hexadecimal without sign, 0x , 0X optional, for abcdef
for x or ABCDEF for X
u Int decimal without sign
c Int single character (Section 3.2.1)
s String character string
f Float decimal as [-] mmm.ddd, accuracy determines the number
of d, default: 6, no decimal point for 0
e , E Float decimal as [-] mmm.ddd e ±xx or [-] mmm.ddd E ±xx
accuracy determines the number of d, default: 6,
no decimal point for 0
g , G Float corresponds to %e , %E if exponent is smaller than −4 or not
smaller than accuracy, otherwise %f. zero and decimal point
are not issued at the end.
% - issues %

Table 6.1: Formatting Character

# 6.2 oiApplPaste()

• oiApplPaste(pFather(MObject), pName(Symbol)) → Int
The function evaluates the clipboard of the application and generates a new object as child
of pFather. The local name of the new object is specified by pName. If an object with the
resultingglobalnamealreadyexistsoriftheclipboardoftheapplicationisempty,aruntime
error occurs. If NULL is set for pName, a valid name is automatically selected. The return
value of the function is 1 if an object could be generated, otherwise 0.
The state of the clipboard does not change.

Note: The clipboard of the application is implemented by the runtime environment and does not
have any reference to the global OFML clipboard which can be manipulated or evaluated using the
oiCopy(), oiCut(), and oiPaste() function.

# 6.3 oiClone()

• oiClone(pSrc(MObject), pDest(String)) → MObject

110

| Character | Argument type | Formatting |
| --- | --- | --- |
| d, i
o
x, X
u
c
s
f
e, E
g, G
% | Int
Int
Int
Int
Int
String
Float
Float
Float
- | decimal with sign
octal without sign, leading zero optional
hexadecimal without sign, 0x, 0X optional, for abcdef
for x or ABCDEF for X
decimal without sign
single character (Section 3.2.1)
character string
decimal as [-]mmm.ddd, accuracy determines the number
of d, default: 6, no decimal point for 0
decimal as [-]mmm.ddde±xx or [-]mmm.dddE±xx
accuracy determines the number of d, default: 6,
no decimal point for 0
corresponds to %e, %E if exponent is smaller than −4 or not
smaller than accuracy, otherwise %f. zero and decimal point
are not issued at the end.
issues % |

<!-- Page 113 -->

ThefunctiongeneratesanidenticalcopyofthepSrcobjectundertheglobalnamepDestand
returns the corresponding object reference. If an immediately preceding object under the
name pDest exists, it causes a runtime error.
The state of the OFML clipboard does not change.

# 6.4 oiCollision()

• oiCollision(pObject1(MObject), pObject2(MObject)) → Int
The function checks the collision between two objects pObject1 and pObject2. The polygons
of the geometric basic primitives are the atomic element of the collision check. In the case
of the parametric primitives OiRotation, OiSweep and OiSurface, these polygons result from
the definition coordinates or areas. That is, the actual mapping to a piece by piece linear
approximation is not taken into account.
In the case of a collision, 1 is returned, otherwise 0.
The function always delivers 1 if pObject1 is an ancestor (father, grandfather, etc.) or a
successor (child, grandchild, etc.) of pObject2 and vice versa.

# 6.5 oiCopy()

• oiCopy(pObject(MObject)) → Void
The function writes an adequate description of pObject to the global OFML clipboard.
The existing state of the clipboard is lost.
Since the OFML clipboard is a global data structure, corresponding operations must follow
each other directly. Otherwise, the correctness of the operations cannot be guaranteed.

# 6.6 oiCut()

• oiCut(pObject(MObject)) → Void
The function writes an adequate description of pObject to the global OFML clipboard and
then deletes object pObject.
The existing state of the clipboard is lost.
Since the OFML clipboard is a global data structure, corresponding operations must follow
each other directly. Otherwise, the correctness of the operations cannot be guaranteed.

# 6.7 oiDialog()

• oiDialog(pDialog(Symbol), pIcon(Symbol), pMessage(String)) → Symbol

111

<!-- Page 114 -->

This function causes the reaction of the user to a modal dialog that is generated by the
OFMLruntime environment.
ThepDialogparameterspecifiesthedialogthroughoneofthefollowingsymbols. Thepossible
return values are listed in parentheses.
– @OK - Confirmation (@OK).
– @OK CAN - Confirmation or Cancel (@OK, @CANCEL).
– @ABT IGN - Abort or Ignore (@ABORT, @IGNORE).
– @YES NO CAN - Yes or No or Cancel (@YES, @NO, @CANCEL).
– @YES NO - Yes or No (@YES, @NO).
If no valid value is transferred for pDialog, no dialog is started and the return value is
@INVALID DIALOG.
In addition, the pIcon parameter specifies the visual representation of the dialog. It can be
executed through a corresponding icon and is always binding, independent of the value of
pDialog. The value range of pIcon is specified as follows:

– @NONE - No display of a special character.
– @STOP - Display of a stop character.
– @QUESTION - Display of a question mark.
– @WARNING - Display of an exclamation mark.
– @INFO - Display of an information sign (a small i in a circle).

If no valid value is transferred for pIcon, no dialog is started and the return value is @IN-
VALID ICON.
The pMessage parameter specifies the message to be output. If the first character of the
pMessage string is a @, the string is considered a reference that is triggered by an access to
an external database (Appendix D).
pMessagemustbeeitheravalidstringaccordingtothebasicsyntax(Chapter3)oravector.
In the first case, umlauts are not permitted. Specifying a vector is used for the formatted
output. In this case, the first element is the format character string (Section 6.1), the
remaining elements are the arguments to be formatted. If the first element of the vector
starts with @, the format character string is read from the external database, as indicated
above. If no valid value is transferred for pMessage, an empty character string is output in
the dialog.
The return value is a symbol that describes the selected answer in accordance with the
aforementioned alternatives.

# 6.8 oiDump2String()

• oiDump2String(pObj(MObject)) → String
Thefunctiondeliversthe(implementation-dependent)dumprepresentationofthetransferred
instance.

112

<!-- Page 115 -->

ItcanbeusedtogetherwiththeoiReplace()functiontostoreandrestoreobjectstateswhich
may be used, for example, in problem cases for implementing undo-capable operations.

# 6.9 oiExists()

• oiExists(pName(String)) → Int
The function checks the existence of the object whose absolute name is transferred as string
inthepNameparameter. Iftheobjectexists,thereturnvalueis1,otherwise0. Theexistence
check may be necessary since accessing a non-existing object will cause a runtime error.

# 6.10 oiGetDistance()

• oiGetDistance(pPosition(Float[3]), pDirection(Float[3])) → Float
The function determines the first point of intersection of a beam whose origin lies in the
world coordinate point pPosition and runs alongside the normed vector pDirection, with the
objectsofthescene. Thereturnvalueisthedistancealongthebeamtothefirstintersection
or −1 if no intersection is found.

# 6.11 oiGetNearestObject()

• oiGetNearestObject(pPosition(Float[3]), pDirection(Float[3])) → MObject
The function determines the first encountered object while tracing a beam whose origin lies
in the world coordinate point pPosition and runs alongside the normed vector pDirection.
The return value is a reference to the first encountered object or NULL if no object was
found.

# 6.12 oiGetRoots()

• oiGetRoots() → MObject[]
The function determines the root objects available in the scene.

# 6.13 oiGetStringResource()

• oiGetStringResource(pStr(String), pLanguage(String), ...) → String
The function delivers the text stored in an external resource file for the transferred text
resource in the specified language or the text resource if no text could be found for the
resource or an invalid value was transferred for the language.
If an additional optional parameter is given, it specifies an instance. The text is searched in
the name space of this instance if the text resource is not fully qualified (see Appendix D).

113

<!-- Page 116 -->

# 6.14 oiLink()

• oiLink(pURL(String)) → Void
The function loads the file specified by the string pURL. The current scene can be replaced
by a new scene or another document in the result.

# 6.15 oiOutput()

• oiOutput(pLevel(Symbol), pMessage(String)) → Void
This function causes the output of a text message through the OFML runtime environment.
The output should be implemented through a modal dialog. The pLevel symbol describes
the category of the output as follows:
– @MESSAGE - Output of a message.
– @WARNING - Output of a warning.
– @ERROR - Output of an error message.
– @FATAL - Output of an error message. After quitting the modal dialog, the runtime
environment must terminate.
If the first character of the pMessage string is a @, the string is considered a reference that is
triggered by an access to an external database (Appendix D).
pMessagemustbeeitheravalidstringaccordingtothebasicsyntax(Chapter3)oravector.
In the first case, umlauts are not permitted. Specifying a vector is used for the formatted
output. In this case, the first element is the format character string (Section 6.1), the
remaining elements are the arguments to be formatted. If the first element of the vector
starts with @, the format character string is read from the external database, as indicated
above.
If "::ofml::app::@none" is transferred as the message, the application does not output a
message.

Note: Itcanbeused,forexample,toindicatean”errorcondition”via oiOutput(@ERROR, "::ofml::app::@none")
oftheapplicationforwhichtheOFMLalreadyperformedadialog(oiDialog()function)(e.g.,aCan-
cel dialog during checkAdd(), see Complex interface), and no additional message is desired.

# 6.16 oiPaste()

• oiPaste(pFather(MObject), pName(Symbol)) → MObject
The function evaluates the global OFML clipboard and generates a new object as child of
pFather. The local name of the new object is specified by pName. If an object with the
resulting global name already exists, a runtime error occurs. If NULL is set for pName, a

114

<!-- Page 117 -->

valid name is automatically selected. The return value of the function is a reference to the
created object.
The state of the clipboard does not change.
Since the OFML clipboard is a global data structure, corresponding operations must follow
each other directly. Otherwise, the correctness of the operations cannot be guaranteed.

# 6.17 oiReplace()

• oiReplace(pObj(MObject), pDump(String)) → Void
The function replaces the transferred instance by an object whose dump representation is
contained in the transferred buffer.
An(implementation-dependent)dumprepresentationcanbecreatedwiththeoiDump2String()
function.

# 6.18 oiSetCheckString()

• oiSetCheckString(pString(String) → Void
ThefunctionsetsastringthatmustbeverifiedbytherespectiveOFMLruntimeenvironment.
This string, which is usually set in persistent OFML scene representations, can be used for
checkingtheconsistencyorvalidityofascenerepresentation. Anincorrectstringinthissense
must result in the cancellation of the read operation of the persistent scene representation.

# 6.19 oiTable()

• oiTable(pRequest(Symbol), pArgs(List)) → List
TheoiTablefunctionimplementsthereadaccesstodatafromanexternalrelationaldatabase
(Appendix D).
The desired table operation is specified via pRequest parameter and the corresponding ar-
guments via pArgs. The following listing shows the possible operations and corresponding
arguments:

@openTbl List of TableEntry
@closeTbl List of TableID
@readTE List of TableEntry

A TableEntry is transferred as [tableID, attributeList] vector, where tableID is indi-
cated as string and attributeList as a list of TableAttributen.
ATableAttributeistransferredas [name, isPrimKey, isKey, type, value, format] vec-
tor,wherenameisindicatedasstring,isPrimKeyandisKeyas(boolean)Int,typeassymbol,
value as object according to type and format as string.
The following attribute types and corresponding format strings are defined:

115

<!-- Page 118 -->

Int: type = @i, format = maximum number of places
Float: type = @f, format = total number of places.number of places
behind decimal point
String: type = @s, format = maximum length

A TableID string consists of three components separated by spaces:
– thedesignatorforthetypeofdatabasewhichisalways "FTXT" (textfilewithfixedfield
length) in OFML,
– the localization path for the database to be used, and
– the actual name of the concerned table.
A table must be opened before the first access. The @openTbl operation opens a table for
reading where its structure is defined via the list of attributes. The isPrimKey and isKey
attributes of TableAttribute are evaluated only during the table definition in @openTbl .
The @closeTbl operation requests a list of TableIDs of the tables to be closed as parameter.
All system resources used for the management of these tables are released; afterwards, an
access is no longer possible.
The @readTbl operation is used for reading table rows. The TableEntries transferred in the
listspecifywhichrowsshouldberead. @readTblistheonlyoperationwherethetransferred
TableEntries do not have to feature a complete row description according to the table def-
inition. Rather, only those TableAttributes must be given that should serve as key for the
access. Allrowswhosevaluesinthespecifiedcolumnscorrespondtothespecifiedvaluesinthe
transferred TableAttributes are delivered for a transferred TableEntry. Thus, the @readTbl
operation presents a simple, table-specific search function. Only if the TableEntry contains
a TableAttribute marked as primary key during the table definition can a unique result be
expected. IfseveralTableEntryobjectsaretransferredto@readTbl,thecorrespondingquery
is performed for each object and the results are linked in the returned list.

116

<!-- Page 119 -->

# Chapter 7

# Geometric types

This chapter describes the hierarchy of the geometrically oriented types. A geometric instance
can be viewed directly through its geometry and, if required, through its children. The entities of
geometric types are generally located at the lowest level in hierarchical product models.

# 7.1 OiGeometry

### Description

• TheabstracttypeOiGeometryisthebasetypeforthegeometrically-orientedtypesdescribed
below. OiGeometry may not be instantiated directly. The derivation of application-specific
types of OiGeometry is allowed. An implementation of an application-specific derived type
is carried out here through parameterization and aggregation of one or several OiGeometry-
compatible entities.
The entities of the OiGeometry type can feature a child with the local name geo for the
implementationofthegeometry. Thisnamemaynotbeassignedelsewhere. Inaddition, the
potential existence of geo should be observed with iterations on the list of children.
• Interface(s): Base, material

### Initialization

• OiGeometry(pFather(MObject), pName(Symbol))
The function initializes an indirect instance of OiGeometry type. Initially, the selection
option is deactivated. The initial material category is @ANY. In the normal case, it must be
changed accordingly via setMatCat(). The initial alignment is not defined uniformly and is
determined by the respective primitive.

117

<!-- Page 120 -->

### Methods

• setMatCat(pCat(Symbol)) → Void
Thefunctionoverwritestheinitialmaterialcategory@ANYoracategorypreviouslysetwith
the value of pCat.
• setAlignment(pAlignment(Symbol[3])) → Void
The function allows for the alignment of the geometry with respect to the local axes. The
following symbols for element of pAlignment are supported (in each case with respect to one
of the three axes):
– @C – The origin of the object is located in the middle of the local delimiting volume.
– @I – The origin of the object is located in the minimum of the local delimiting volume.
– @A–Theoriginoftheobjectislocatedinthemaximumofthelocaldelimitingvolume.
A subsequent change of the geometry does not lead to adaptation in accordance with the
specified alignment. Children that may exist can lead to unexpected results when the align-
ment is set.

# 7.2 OiBlock

h

d
y
w
x
z

Figure 7.1: The geometric type OiBlock

### Description

• OiBlock represents an orthogonal quboid that begins in the origin of the local coordinate
system and expands accordingly along the positive axes of the local coordinate system. The
dimensions of the quboid can be changed after its generation.
• Super type: OiGeometry

118

|  |  |  |
| --- | --- | --- |
|  |  |  |

<!-- Page 121 -->

### Initialization

• OiBlock(pFather(MObject), pName(Symbol), pDimensions(Float[3]))
ThefunctioninitializesaninstanceoftheOiBlocktype. Theinitialdimensionsofthequboid
are indicated by a vector of three positive numbers.

### Methods

• setDimensions(pDimensions(Float[3])) → Void
The function sets the dimensions of the quboid. pDimensions must be a vector of three
positive numbers.
If required, an adaptation of the alignment must be performed afterwards (setAlignment()).
• getDimensions() → Float[3]
The function delivers the current dimensions of the quboid.

# 7.3 OiCylinder

l

y
r
x
z

Figure 7.2: The Geometric Type OiCylinder

### Description

• OiCylinder represents a closed homogenous cylinder that begins in the origin of the local
coordinate system and expands centered along the positive y-axis of the local coordinate
system. The dimensions of the cylinder can be changed after its generation.
• Super type: OiGeometry

119

<!-- Page 122 -->

### Initialization

• OiCylinder(pFather(MObject), pName(Symbol), pLength(Float), pRadius(Float))
The function initializes an instance of the OiCylinder type. The initial dimensions of the
cylinder are indicated by the parameters length and radius. Only positive numbers are
allowed.

### Methods

• setLength(pLength(Float)) → Void
The function sets the length of the cylinder. pLength must be a positive number.
If required, an adaptation of the alignment must be performed afterwards (setAlignment()).
• getLength() → Float
The function delivers the current length of the cylinder.
• setRadius(pRadius(Float)) → Void
The function sets the radius of the cylinder. pRadius must be a positive number.
If required, an adaptation of the alignment must be performed afterwards (setAlignment()).
• getRadius() → Float
The function delivers the current radius of the cylinder.

# 7.4 OiEllipsoid

r
y

r
x
r
z
y

x
z

Figure 7.3: Der geometric type OiElliposid

120

<!-- Page 123 -->

### Description

• OiEllipsoidrepresentsahomogenousellipsoidwhosecenterislocatedintheoriginofthelocal
coordinate system and expands accordingly to all six sides of the local coordinate system.
The dimensions of the ellipsoid can be changed after its generation.
• Super type: OiGeometry

### Initialization

• OiEllipsoid(pFather(MObject), pName(Symbol), pDimensions(Float[3]))
The function initializes an instance of the OiEllipsoid type. The initial dimensions of the
ellipsoid are indicated by a vector of three positive numbers.

### Methods

• setDimensions(pDimensions(Float[3])) → Void
The function sets the dimensions of the ellipsoid. pDimensions must be a vector of three
positive numbers.
If required, an adaptation of the alignment must be performed afterwards (setAlignment()).
• getDimensions() → Float[3]
The function delivers the current dimensions of the ellipsoid.

# 7.5 OiFrame

th

h
y
d
w
x
z

Figure 7.4: Der geometric type OiFrame

121

|  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |

<!-- Page 124 -->

### Description

• OiFrame represents a frame that begins in the origin of the local coordinate system and
expands accordingly along the positive axes of the local coordinate system. An orthogonal
volume is subtracted from the body in the local x-y plane. The thickness of the frame in x
and y direction is identical. The following must always apply to the dimensions w, h in x
and y direction and the x/y thickness th: w, h >2∗th. The dimensions of the frame can be
changed after its generation.
• Super type: OiGeometry

### Initialization

• OiFrame(pFather(MObject), pName(Symbol), pDimensions(Float[3]), pThickness(Float))
The function initializes an instance of the OiFrame type. The initial outer dimensions of the
frame are indicated by a vector of three positive numbers. The initial thickness of the frame
in the local x and y direction is indicated by a positive number.

### Methods

• setDimensions(pDimensions(Float[3])) → Void
The function sets the outer dimensions of the frame. pDimensions must be a vector of three
positive numbers.
If required, an adaptation of the alignment must be performed afterwards (setAlignment()).
• getDimensions() → Float[3]
The function delivers the current outer dimensions of the frame.
• setThickness(pThickness(Float)) → Void
The function sets the frame thickness in the local x and y direction. pThickness must be a
positive number.
• getThickness() → Float
The function delivers the actual frame thickness in the local x and y direction.

# 7.6 OiHole

### Description

• OiHole implements circular or rectangular openings in circular or rectangular areas. This
allowsforsimulatingbooleanoperations,especiallythesubtractioninspecialcases. However,
no actual subtraction in the sense of a boolean operation takes place. The real purpose of
OiHole consists of generating the areas for the combination of circular outlines rectangular
hole and rectangular outline circular hole. OiHole does not implement outside areas along

122

<!-- Page 125 -->

Ru¨ckfla¨che (optional)

d < d
h d = d
h
hx
d
h
hy
y
d
x
z
Loch Außenlinie
d = d d < d
@RECTANGLE @RECTANGLE
h h
@CIRCLE @CIRCLE

Figure 7.5: The geometric type OiHole

theoutlineinthelocalzdirection. OiHoleentitiesbeginintheoriginofthelocalcoordinate
system and expand according to the outer dimensions along the positive x-, y- and z-axis.
• Super type: OiGeometry

### Initialization

• OiHole(pFather(MObject),pName(Symbol),pOMode(Symbol),pODim(Float[3]),pBack(Int),
pHMode(Symbol), pHDim(Float[3]), pHOffset(Float[2])
The function initializes an instance of the OiHole type. The following specific parameters
must be supplied:
– ThepOModeparameterindicatesthemodeoftheoutline. Permissibleimplementations
for pOMode are:
∗ @RECTANGLE – The outline corresponds to a rectangle.
∗ @CIRCLE – The outline corresponds to a circle.
– ThepODimparameterdeterminestheouterdimensionsofthebody,consistingofwidth
w, height h and depth d. All dimensions must be positive numbers. In the case of a
circular outline, the width also determines the height.
– The pBack parameter indicates whether the outer back plane is generated (pBack ==
1) or not (pBack == 0).
– The pHMode parameter indicates the mode of the hole. Permissible implementations
for pHMode are:
∗ @RECTANGLE – A rectangular hole is generated.

123

|  |  |  |
| --- | --- | --- |
|  |  |  |

|  |  |  |
| --- | --- | --- |
|  |  |  |

<!-- Page 126 -->

∗ @CIRCLE – A circular hole is generated.
– The pHDim determines the dimensions of the hole consisting of width w , height h
h h
and depth d . All dimensions must be positive numbers. In the case of a circular hole,
h
the width also determines the height. The hole width w must be smaller than total
h
widthw. Theholeheighth mustbesmallerthanthetotalheighth. Theholedepthd
h h
may not be larger than the total depth d. If it is smaller, a hole back area is generated
automatically.
– ThepHOffsetparameterdefinestheoffsetfromthecenteroftheholetothelocalorigin
of the primitive. The hole may not go beyond the area of the outer volume.

# 7.7 OiHPolygon

V V
1 2
H H
3 2

H H
0 1
V V V
0 0 3

Figure 7.6: The geometric type OiHPolygon

### Description

• OiHPolygonrepresentsaone-sided,simple,planarandconvexpolygonfromwhichanumber
of simple, planar and convex polygons can be cut out.
• Super type: OiGeometry

### Initialization

• OiHPolygon(pFather(MObject), pName(Symbol), pMosaic(Int), pOutline(Float[3][]),
pHoles(Float[3][][]))
ThefunctioninitializesaninstanceoftheOiHPolygontype. ThepMosaicparametercontrols
the tessalation of the resulting polygon net. If pMosaic obtains the value 0, it results in a
triangulation. Otherwise, the number of internal polygons is minimized. pOutline describes
theouterpolygoninclockwisedirection. pHolesisanoptionalemptyvectorofpolygonsthat
each describes a cutout. These polygons must be defined in counterclockwise direction.

124

<!-- Page 127 -->

Figure 7.7: The geometric type OiImport

# 7.8 OiImport

### Description

• OiImport imports an external file in a geometric format. Provided that it does not contain
any materials, a material can be set via the Material interface.
OiImportoptionallysupportsexactlyoneheavilyresolution-reducedgeometrynexttotheac-
tualgeometry. Ifitispresent, itcanbeusedforthespeed-optimizedpresentation. However,
its use is dependent upon the respective presentation software.
• Super type: OiGeometry

### Initialization

• OiImport(pFather(MObject), pName(Symbol), pMode(Symbol), pGeometry(String))
The function initializes an instance of the OiImport type. pGeometry describes the name
of a geometry file in form of a simple string without path and extension information, e.g.,
”wheel.” The file type is determined by the pMode parameter. Permissible implementations
for pMode are:
– @OFF – The geometry features the Object File Format.

125

<!-- Page 128 -->

– @G3DS – The geometry features the 3D Studio format.
The optional resolution-reduced geometry file also contains an underscore character at the
beginning of the name, e.g., ” wheel.”
The data record is loaded in accordance with the definitions for external data (Chapter D)
and must be fully qualified.

### Methods

• setScale(pFactor(Float[3])) → Void
The function allows for the scaling of OiImport objects. The elements of the vector pFactor
must be real, positive numbers. The initial scaling is 1.0 in all three dimensions.
If required, an adaptation of the alignment must be performed afterwards (setAlignment()).
• getScale() → Float[3]
The function furnishes the current scaling of the implicit instance.

# 7.9 OiPolygon

V V
3 2

V V
0 1

Figure 7.8: The geometric type OiPolygon

### Description

• OiPolygon represents a one-sided, simple, planar and convex polygon. This primitive should
be used in exceptional cases only since a number of OiPolygonen is extremely inefficient
compared to other polygon sets (e.g., on the basis of OiImport). In addition, a singular
OiPolygon does not describe a body which contradicts the general intention of OFML.
• Super type: OiGeometry

126

<!-- Page 129 -->

### Initialization

• OiPolygon(pFather(MObject), pName(Symbol), pPoints(Float[3][]))
The function initializes an instance of the OiPolygon type. The pPoints parameter defines
a one-sided, simple, planar and convex polygon. The last and first point are automatically
connected. The visibility results by means of the right-hand rule. If the curvature of the
right hand follows the vertex line, the thumb of the right hand indicates the visible side.

# 7.10 OiRotation

a a

V V
0 0

V V
1 1
V V
2 2

V V
3 3
V V
n-1 n-1
y

x
z

Figure 7.9: The geometric type OiRotation

### Description

• OiRotationdescribesasolidbodythatisdefinedbytheplanarrotationofathree-dimensional
planar curve around an axis. The curve must be defined as follows, according to the right-
hand rule: If the thumb of the right hand points towards the direction of rotation, the
remaining fingers of the right hand indicate the orientation. Otherwise, an inversion must
take place.
• Super type OiGeometry

127

<!-- Page 130 -->

### Initialization

• OiRotation(pFather(MObject), pName(Symbol), pMode(Symbol), pAxis(Float[3]),
pPoints(Float[3][]), pArc(Float), pUWMode(Symbol[2]), pCMode(Symbol[2]), pFlip(Int))
The function initializes an instance of the OiRotation type. This requires indicating the
following specific parameters:
– pMode specifies whether the body along the definition curve should be smooth
(@SMOOTH) or not (@LINEAR).
– pAxis defines the rotation axis with respect to the local coordinate system.
– pPoints describes the definition curve. However, points on the rotation axis are not
allowed.
– pArcsetstheangleofrotationofthedefinitioncurve. pArcmustbepositiveandsmaller
than or equal to 2π.
– pUWMode defines the openness (@OPEN) or compactness (@CLOSED) of the body
along two curves. pUWMode[0] specifies whether the body along the rotation axis is
closed. In general, this is the case for bodies with pArg = 2π. pUWMode[1] specifies
whether a compactness of the body results with respect to the definition curve (by
joining the first and last point). In general, this is not the case.
– pCMode defines the openness (@OPEN) or compactness (@CLOSED) of the body with
respect to two areas. pCMode[0] specifies whether possibly resulting interfaces of the
body should be closed. This is only necessary for bodies with pArg = 2π. pCMode[1]
specifies whether the cap areas of the body should be generated or not.
– pFlipforcesaninversionofthesequenceinpPointsifitfeaturesthevalue1. Otherwise,
the value must be 0.

# 7.11 OiSphere

r

y

x
z

Figure 7.10: The geometric type OiSphere

128

<!-- Page 131 -->

### Description

• OiSphere represents a homogenous sphere that is centered about the origin of the local
coordinate system. The radius of the sphere can be changed after its generation.
• Super type OiGeometry

### Initialization

• OiSphere(pFather(MObject), pName(Symbol), pRadius(Float))
The function initializes an instance of the OiSphere type. The initial radius of the sphere is
indicated by the positive number pRadius.

### Methods

• setRadius(pRadius(Float)) → Void
The function sets the radius of the sphere. pRadius must be a positive number.
If required, an adaptation of the alignment must be performed afterwards (setAlignment()).
• getRadius() → Float
The function delivers the current radius of the sphere.

# 7.12 OiSweep

V
1
V
2

V
0
V
3
V
1
V
2
l
V
n-1
V
0
V
3 V
1
V
2

V
n-1
V
0
V
y 3

x
z
V
n-1

Figure 7.11: The geometric type OiSweep

129

<!-- Page 132 -->

### Description

• OiSweep describes a solid body that is defined by the planar move of a three-dimensional
planar curve along an axis. The curve must be defined as follows, according to the right-
handrule: Ifthethumboftherighthandpointstowardsthedirectionofmove,theremaining
fingers of the right hand indicate the orientation. Otherwise, an inversion must take place.
• Super type: OiGeometry

### Initialization

• OiSweep(pFather(MObject),pName(Symbol),pMode(Symbol),pAxis(Float[3]),pLength(Float),
pPoints(Float[3][]), pUMode(Symbol), pCMode(Symbol[2]), pFlip(Int))
ThefunctioninitializesaninstanceoftheOiSweeptype. Thisrequiresindicatingthefollowing
specific parameters:
– pMode specifies whether the body along the definition curve should be smooth
(@SMOOTH) or not (@LINEAR).
– pAxis defines the move axis with respect to the local coordinate system.
– pLength sets the length of the body along the move axis. pLength must be a positive
number.
– pPoints describes the definition curve.
– pUModedefinestheopenness(@OPEN)orcompactness(@CLOSED)ofthebodyalong
the definition curve. If pUMode = @OPEN, end point and start point of pPoints are
connected by a straight line. Otherwise, an appropriate soft connection occurs.
– pCMode defines the openness (@OPEN) or compactness (@CLOSED) of the body with
respect to two areas. pCMode[0] specifies whether the side faces of the body should be
closed or not. pCMode[1] specifies whether the connection of the last point with the
first point should be closed or not.
– pFlipforcesaninversionofthesequenceinpPointsifitfeaturesthevalue1. Otherwise,
the value must be 0.

### Methods

• setLength(pLength(Float)) → Void
The function sets the length of the object along the move axis. pLength must be a positive
number.
If required, an adaptation of the alignment must be performed afterwards (setAlignment()).
• getLength() → Float
The function delivers the current length of the object along the move axis.

130

<!-- Page 133 -->

V
m-1,n-1
V
m-1,1
V
1,n-1
V
V 1,1
m-1,0

y
V V
1,0 0,n-1
V
0,1
x
z V
0,0

Figure 7.12: The geometric type OiSurface

# 7.13 OiSurface

### Description

• OiSurfacedescribesaprimitivethatisdefinedbyatwo-dimensionalnetofthree-dimensional
supporting points. Here, u and w are the dimensions of the net.
• Super type: OiGeometry

### Initialization

• OiSurface(pFather(MObject), pName(Symbol), pUDim(Int), pWDim(Int),
pPoints(Float[3][pUDim(pWDim]), pUWMode(Symbol[2])
ThefunctioninitializesaninstanceoftheOiSurfacetype. Thisrequiresthefollowingspecific
parameters:
– pUDim defines the u dimension of the net.
– pWDim defines the w dimension of the net.
– pPoints describes an array with the definition points. Within a patch, the right-hand
rule indicates the orientation, i.e., if the thumb of the right hand sits on the patch at a
right angle, the remaining fingers of the hand indicate the orientation.
– pUWModedefinestheopenness(@OPEN)orcompactness(@CLOSED)oftheprimitive
along the u and w dimension. If pUWMode[0] = @OPEN, no connection of the net in
the u direction is made. If pUWMode[1] = @OPEN, no connection of the net in the w
direction is made.

131

<!-- Page 134 -->

# Chapter 8

# Global Planning Types

This chapter describes global, higher-level planning base types. These base types are independent
of concrete planning elements (pieces of furniture) and, therefore, also independent of concrete
geometric implementations.
The types described here are based on the conceptual model shown in Figure 8.1.

(cid:79)(cid:105)(cid:80)(cid:108)(cid:69)(cid:108)(cid:101)(cid:109)(cid:101)(cid:110)(cid:116) OiPart (cid:79)(cid:105)(cid:71)(cid:101)(cid:111)(cid:109)(cid:101)(cid:116)(cid:114)(cid:121)

OiPlanning

(cid:79)(cid:105)(cid:80)(cid:114)(cid:111)(cid:103)(cid:73)(cid:110)(cid:102)(cid:111)

Figure 8.1: Conceptual model of the global planning types

# 8.1 OiPlanning

### Description

• An instance of this type functions as root object of a complete planning hierarchy and
implements global planning logics for the elements of the planning (OiPlElement type).
• Additional tasks of the global planning object include:

132

| (cid:79)(cid:105)(cid:80)(cid:108)(cid:69)(cid:108)(cid:101)(cid:109)(cid:101)(cid:110)(cid:116) |
| --- |
|  |

| OiPart |
| --- |
|  |

| (cid:79)(cid:105)(cid:71)(cid:101)(cid:111)(cid:109)(cid:101)(cid:116)(cid:114)(cid:121) |
| --- |
|  |

| OiPlanning |
| --- |
|  |

| (cid:79)(cid:105)(cid:80)(cid:114)(cid:111)(cid:103)(cid:73)(cid:110)(cid:102)(cid:111) |
| --- |
|  |

<!-- Page 135 -->

– The definition of a planning limit that specifies the space within which the planning
elements can be placed.
– Themonitoringandhandlingofthetransformationofplanningelementsforthepurpose
of avoiding collisions and exceeding planning limits.
– The management and utilization of information about characteristics and requirements
of the (furniture) programs to which the elements belong that are represented in the
planning (OiProgInfo type).
– Use of a product data manager for accessing product data (see also Chapter 9).
• Interface(s): Base, Complex, Property, Material

### Initialization

• OiPlanning(pFather(MObject), pName(Symbol))
The function initializes an instance of the OiPlanning type. Initially, the selection option is
deactivated. The initial planning limit is infinite.

### Methods

General Methods

• setLanguage(pLang(String)) → Void
The function specifies the language to be used for subsequent messages and labels. The
pLang parameter describes the national language through a string in accordance with ISO
639 guidelines.

Examples:
– "de" – German
– "en" – English
– "nl" – Dutch

• getLanguage() → String
The function delivers the language that is currently used for messages and labels.
• setRegion(pRegion(String)) → Void
Thefunctionspecifiesthesalesregion,i.e.,generallyacountry,forwhichthecurrentplanning
is created. The pRegion parameter describes the sales region through a string in accordance
with ISO 3166 guidelines (ISO Code 2) or extensions in this connection for the designation
of federal states, etc.

Examples:
– "DE" – Germany

133

<!-- Page 136 -->

– "UK" – United Kingdom
– "NL" – Netherlands

• getRegion() → String
The function delivers the current sales region. If no sales region was specified, the return
value is of type Void.
• setProgram(pProgr(Symbol)) → Void
The function specifies the currently relevant program.

Note: ProgramsaredistinguishedbasedontheirID(identificationsymbol). TheprogramIDmust
be unique across all manufacturers. For this reason, it starts with a two-digit manufacturer code,
followed by the code for the actual program.
TheprogramIDisusedwithcertainoperationsforthedelegationoffunctionalitytoprogram-specific
informationorsimilarobjects. Thecurrentlyrelevantprogramcanbedeterminedexternallythrough
theruntimeenvironment,oreveninternallyoutofthecertaincontext,e.g. outoftheassociationof
the currently processed planning element to a program.

• delegationDone() → Void
Thefunctionsignalstheimplicitplanninginstancethesuccessfulexecutionofafunctionality
delegated to another instance (Delegat).

Note: The function is called by the delegation instance upon successful execution of the delegated
functionality.

Error Log

Complex test algorithms that are executed on an object structure can lead to error messages
concerning various objects of the structure. Instead of issuing an error message from every test
method for the corresponding objects, it is generally desirable to collect these messages and view
themtogetherinadialog. Forthispurpose,theglobalplanninginstancemanagesaso-callederror
log. The instance or method that initiates a global testing process, generates the data structure
to be used for the log of the testing process and passes it on to the setErrorLog() function before
the execution of the test is delegated to another instance or inherited implementations are called.
Implementations of the testing algorithm must first be checked with the getErrorLog() function
whether a higher-level log was created, in which case the generated messages must be entered in
this log and no separate dialog for display may be started. If no higher-level log exists, it must be
created before possible delegations can take place, and a dialog for displaying the messages from
the log must be started at the end of the testing process. The data structure used for the log can
be defined separately for each testing algorithm.

Note: AnapplicationexampleofanerrorlogislocatedintheArticleinterfaceundertheperformanceof
consistency checks.

134

<!-- Page 137 -->

• setErrorLog(pLog(Any)) → Void
The function assigns the implicit planning instance a new data structure for the error log.
• getErrorLog() → Any
Thefunctionreturnsthereferencetothelastdatastructurefortheerrorlogthatwasassigned
by means of the setErrorLog() function.

Instance Hierarchy

• getEnvironment() → MObject
The function delivers the root object of the hierarchy of the planning environment. The
function furnishes a value of the type Void if no planning environment exists.
• getPlElementUp(pObj(MObject)) → MObject
The function traverses the instance hierarchy, beginning with the transferred instance and
upward to the root object and delivers the first instance which is of the OiPlElement type.
If no such instance was located on the traversing path, the function delivers a value of the
type Void.
• getTopPlElement(pObj(MObject)) → MObject
The function traverses the instance hierarchy, beginning with the transferred instance and
upward to the root object and delivers the top instance which is of the OiPlElement type.
If no such instance was located on the traversing path, the function delivers a value of the
type Void.
• getPropObj(pObj(MObject)) → MObject
The function traverses the instance hierarchy, beginning with the transferred instance and
upward to the root object and delivers the first instance that features properties. If no such
instance was located on the traversing path, the function delivers a value of the type Void.

Planning Limit

• setBorder(pBorder(Float[2][3]) → Void
The function assigns the implicit planning instance a new value for the (axis-orthogonal)
planning limit volume.
ThepBorderparameterisavectorconsistingoftwovectorswiththreeFloatvalueseach. The
first Float vector specifies the origin of the acceptable planning volume in world coordinates.
The second Float vector determines the maximum expansion of the acceptable planning
volume along the x-, y- and z-axes. If the spatial location of the planning is not important,
a value of the type Void may also be transferred instead of the first vector.
• getBorder() → Float[2][3]
The function delivers the specification for the planning limit volume that is currently used
in the implicit planning instance. Structure and semantics of the return value correspond to
the parameter for the setBorder() function.

135

<!-- Page 138 -->

• checkBorder() → String
The function checks whether the planning limit is maintained by the planning elements
currently contained in the implicit planning instance.
Inthecaseofalimitviolation, thefunctiondeliversastringthatcontainsthecorresponding
error message. If the limit is maintained, the function delivers a value of the type Void.

Management of Program Information

• addInfoObj(pType(Type), pID(Symbol)) → Void
Thefunctionaddsaninstanceoftheindicatedtypetothesetofprograminformationobjects
and registers them under the indicated program ID. If a program information object with
the indicated program ID already exists, it is removed before the new object is inserted.

Note: The program information objects are inserted into the instance hierarchy of the planning as
non-graphical(thus,notvisible)objects. Afterstoringandreloadingtheplanning,theseinformation
objects are available immediately.

• delInfoObj(pID(Symbol)) → Void
The function removes the program information object with the indicated program ID.
• clearInfoObjs() → Void
The function removes all program information objects.
• getInfoIDs() → Symbol[]
The function delivers the program IDs of all registered program information objects.
• getInfo(pID(Symbol)) → MObject
The function delivers the program information object with the indicated program ID or a
value of the type Void if no program information object is registered under the indicated
program ID.

Materials

• Material::getMatCategories() → Symbol[]
• Material::getCMaterials(pCat(Symbol)) → Symbol[]
• Material::getCMaterial(pCat(Symbol)) → Symbol
• Material::setCMaterial(pCat(Symbol), pMat(Symbol)) → Int
• Material::getMatName(pMat(Symbol)) → String
The standard implementation performs a string conversion of the symbol.

These functions implement the corresponding functions of the Material interface by means of
delegation to the functions of the program information object under the same name (OiProgInfo
type) of the currently relevant program (setProgram() function).

136

<!-- Page 139 -->

Element Management and Collision Detection

• Complex::checkAdd((pType(Type),pObj(MObject),pPos(Float[3]),pParams(Any))→Float[3]

The function checks whether an instance of the indicated type can be inserted as element
into the planning and, if positive, delivers a valid position for the element.
(Formoreinformationaboutthesemanticsofthefunctionoritsparameter,seetheComplex
interface.)
First,thefunctioncallsthefunctionoftheprograminformationobjectunderthesamename
(OiProgInfo type) for the program to which the instance belongs that was transferred in the
pObj parameter. Afterwards, a program-independent check is performed in accordance with
a global planning logic, if required. This requires a call to the doCheckAdd() hook function.
• doCheckAdd(pType(Type), pObj(MObject), pPos(Float[3]), pParams (Any)) → Float[3]
The function checks independent of concrete furniture programs whether an instance of the
indicated type can be inserted as element into the planning and, if positive, delivers a valid
position for the element. The semantics of the parameters corresponds to the checkAdd()
function. Thestandardimplementationachievesanattachingofthenewelementtotheright
of the existing planning.

Note: The function is called by checkAdd() and, in contrast to checkAdd(), can be redefined in
subtypes where the function of the same name of the immediate super type should be called in the
case of non-applicability of the special planning logic that is implemented by the subtype.

• Complex::checkChildColl(pObj(MObject), pExclObj(MObject)) → MObject
Thefunctioncheckswhetheracollisionof thetransferred(child)instancewithother objects
is present. If the pExclObj argument contains a non-empty set of objects, they are excluded
fromthecollisioncheck. Thefunctionfirstchecksforcollisionwiththechildrenoftheimplicit
instance. Objects for which the isValidForCollCheck() hook function delivers the value 0
are excluded from the collision check. Before and after this check, the startCollCheck() or
finishCollCheck() functions of the program information object are called for the program to
which instance belongs that is transferred in the pObj parameter. Afterwards, the function
ofthesamenameoftherootobjectofthehierarchyoftheplanningenvironmentiscalled(if
itexistsanditstypeimplementstheComplexinterface). Thereturnvalueisthefirstlocated
object with which the transferred instance collides or a value of type Void if no collision was
detected or if the collision detection is deactivated.
• Complex::isValidForCollCheck(pObj(MObject)) → Int
This function implements the corresponding function of the Complex interface by means of
delegation to the function of the same name of the program information object (OiProgInfo
type)fortheprogramtowhichtheinstancebelongsthatistransferredinthepObjparameter.
• Complex::checkElPos(pEl(MObject), pOldPos(Float[3])) → Int
The function implements the corresponding function of the Complex interface by means
of collision detection and planning limit monitoring (checkChildColl() and checkBorder()
functions).

137

<!-- Page 140 -->

Element Transformations

• elemTranslation(pEl(MObject), pOldPos(Float[3])) → Void
The function handles an (already performed) translation of the indicated planning element
in the following way.
– First,thegeneralacceptabilityofthetranslationoftheplanningelementischecked(see
also translateValid() function of the OiPlElement type).
– If the translation is acceptable on principle, the translated() function of the transferred
planning element is now called (see also the OiPlElement type).
– If the translated() function returned the value 0, the implicit instance now checks the
validityofthecurrentpositionoftheplanningelement(collisiondetection,adherenceto
planning limit, and others). If necessary, a correction of the current position may occur
before the translation with the aid of the position of the planning element transferred
in the pOldPos parameter.
If the indicated object is not an instance of the OiPlElement type, the function is without
effect.

Note: The function is called from the TRANSLATE rule of the transferred planning element
(OiPlElement type).

• elemRotation(pEl(MObject), pOldRot(Float)) → Void
The function handles the rotation of the indicated planning element in the following way.
– First, the general acceptability of the rotation of the planning element is checked (see
also rotateValid() function of the OiPlElement type).
– If the rotation is acceptable on principle, the rotated() function of the transferred plan-
ning element is now called (see also the OiPlElement type).
– If the rotated() function returned the value 0, the implicit instance now checks the va-
lidityofthecurrentrotaryangleoftheplanningelement(collisiondetection, adherence
to planning limit, and others). If necessary, a correction of the current angle may occur
before the rotation with the aid of the rotary angle of the planning element transferred
in the pOldRot parameter.
If the indicated object is not an instance of the OiPlElement type, the function is without
effect.

Note: ThefunctioniscalledfromtheROTATEruleofthetransferredplanningelement(OiProgInfo
type).

• checkPosition(pEl(MObject), pPos(Float[3]), pAngles(Float[3])) → Float[2][3]
Thefunctioncheckswhethertheindicatedpositionandtheindicatedrotaryangle(peraxis)
are allowed for the transferred planning element.
The return value is a vector consisting of two vectors of three Float values each. The first
vector specifies an acceptable position, the second the rotary angle (per axis). The returned

138

<!-- Page 141 -->

values may deviate from the desired values transferred in the parameters to a certain extent
to prevent collisions and other conflicts. If the planning element cannot be placed at the
desired position on principle (or in its vicinity), the return vector contains a value of the
Void type instead of a position information.

Note: Thefunctioniscalledbytheruntimeenvironmentduringadialogforexplicitpositioningof
a planning element.

Product Data Management

• setPDManager(pType(Type)) → Void
The function generates an instance of the indicated type to be used as global product data
manager (OiPDManager type). If a product data manager instance already exists, it is
removed first.
• getPDManager() → MObject
The function delivers the global product data manager instance or a value of the type Void
if such an instance is not registered.
• article2Class(pArticle(String)) → String
Thefunctiondeliversthenameofthetypethatmodelsthearticlewhichwasspecifiedbased
on its article number, or a value of the type Void if no assignment could be found for the
article. If a global product data manager instance is registered, the query to this instance is
delegated.
• addProductDB(pType(Type), pID(Symbol), pPath(String), pProgList(Symbol[]) → MObject
The function generates an instance of the transferred type (subtype of OiProductDB) and
registers it with the global product data manager under the indicated ID. The file system
path of the directory that contains the files of the product database is transferred in the
pPath parameter (relativeto the root directory ofthe runtime environment). The additional
pProgList parameter specifies the programs (IDs) that are represented in the database. If
a product database is already registered under the indicated ID, the list of programs of the
product database is expanded, if required.
The return value is the reference to the (generated) product database instance.

Note: ThefunctionachievesthesameeffectasthefunctionoftheOiPDManagertypeofthesame
name.

Miscellaneous

• checkConsistency() → Int
Thefunctioncheckstheconsistenceandcompletenessoftheplanning. Ifrequired,corrections
oradditionsareperformedorerrormessagesaregenerated. ThefunctiondeliversTrueifthe
planning is consistent, otherwise False.

139

<!-- Page 142 -->

First,thefunctioncallsthefunctionofthesamenameonallregisteredentitiesofOiProgInfo
andthenonallchildrenoftheOiPlElementtype. TheresultofthecheckisFalseifthecheck
was not successful for at least one instance. The check uses the error log written with the
checkConsistency() function in the Article interface.

Note: The function is usually called by the runtime environment before the creation of an order
list.

• checkObjConsistency(pObj(MObject) → Int
ThefunctionperformsaconsistencecheckonthetransferredinstanceoftheOiPlElementor
OiPart type. Besides the call of the checkConsistency() method on the transferred instance,
the function can perform additional actions, e.g., displaying or removing a visual feedback
with incorrect articles or adding or removing an entry in the global error log.
• doSpecial(pPID(Symbol), pOp(Symbol), pArgs(Any)) → Any
Using the transferred arguments, the function performs the indicated operation concerning
theprogramspecifiedbythetransferredID.Ifaprograminformationobjectisregisteredfor
theprogram,thefunctionisdelegatedtoit(OiProgInfotype). Thereturnvalueisdependent
upon the operation.

Note: Thefunctioncanbeusedforexpandingthefunctionalityofaplanningsystemwithouthaving
to expand the interface between runtime environment and global planning instance.

### Rules

• REMOVE ELEMENT(pValue(Symbol)) → Int
The rule prevents the removal of planning elements whose removeValid() function delivers
the value 0.

# 8.2 OiProgInfo

### Description

• Entities of this type manage information about a (furniture) program (Appendix I) or im-
plement program-specific functions if requested by the global planning instance (OiPlanning
type).
• Interface(s): MObject, Property

### Initialization

• OiProgInfo(pFather(MObject), pName(Symbol), pPID(Symbol))
The function initializes an instance of the OiProgInfo type with the indicated program ID.
The program ID cannot be changed later.

140

<!-- Page 143 -->

### Methods

General Methods

• getID() → Symbol
The function delivers the ID of the program for which the implicit instance responsible is.
• getPlanning() → MObject
The function delivers the root object of the planning hierarchy (t) if this is an instance of
the OiPlanning type, otherwise a value of the type Void.
• checkConsistency() → Int
Thefunctionperformsaprogram-specificconsistencecheck. Itiscalledbytheglobalplanning
instance of the OiPlanning type with a global consistence check before the check on the
planning elements is performed.
• doSpecial(pOp(Symbol), pArgs(Any)) → Any
Using the transferred arguments, the function performs the indicated operation (see also the
function of the same name of the OiPlanning type).

Materials

• getMatCategories() → Symbol[]
• getCMaterials(pCat(Symbol)) → Symbol[]
• setCMaterial(pCat(Symbol), pMat(Symbol)) → Int
• getCMaterial(pCat(Symbol)) → Symbol
• getMatName(pMat(Symbol)) → String
The standard implementation performs a string conversion of the symbol.

These functions represent program-specific versions of the corresponding functions of the Mate-
rial interface and are called by the functions of the same name of the global planning instance
(OiPlanning type).

Element Management and Collision Detection

• Complex::checkAdd((pType(Type),pObj(MObject),pPos(Float[3]),pParams(Any))→Float[3]

Thefunctioncheckswhetheraninstanceoftheindicatedtypecanbeinsertedasneighboring
element of the program element that is transferred in the pObj parameter, into the planning
and, if positive, delivers a valid position for the element.
The semantics of the function or its parameter correspond to the function of the same name
of the global planning instance (OiPlanning type) and is called by it.

141

<!-- Page 144 -->

• isValidForCollCheck(pObj(MObject)) → Int
Thefunctiondelivers1iftheindicatedprogramelementshouldbeconsideredinthecollision
check, otherwise 0. The function is called by the function of the same name of the global
planning instance (OiPlanning type).
• startCollCheck(pObj(MObject)) → Void
The function performs required actions before the indicated program element is checked for
collision with other planning elements.
ItiscalledbythecheckChildObj()functionoftheglobalplanninginstance(OiPlanningtype).
The standard implementation of the function does not perform any actions.
• finishCollCheck(pObj(MObject)) → Void
The function performs required actions after the indicated program element was checked for
collision with other planning elements.
ItiscalledbythecheckChildObj()functionoftheglobalplanninginstance(OiPlanningtype).
The standard implementation of the function does not perform any actions.

# 8.3 OiPlElement

### Description

• Entities of the OiPlElement type represent independent elements of a planning.
• Planningelementscooperateinadefinedwaywiththeglobalplanninginstance(OiPlanning
type).
• Interface(s): Base, Complex, Material, Property, Article

### Initialization

• OiPlElement(pFather(MObject), pName(Symbol))
The function initializes an instance of the OiPlElement type.
The initialization function of concrete subtypes must define the properties of the planning
element. This is accomplished either by means of the setupProperty() function of the Prop-
erty interface or through delegation to the setupProps() function of the global product data
manager (OiPDManager type) if such an instance exists.

### Methods

General Methods

• getPlanning() → MObject
The function delivers the root object of the planning hierarchy (t) if this is an instance of
OiPlanning, otherwise a value of the type Void.

142

<!-- Page 145 -->

• setPlProgram() → Void
The function assigns the inherent program specified through the getProgram() function as
the currently relevant program by means of the setProgram() function (OiPlanning type) to
the global planning instance.

Spatial Model

• setWidth(pWidth(Float)) → Void
The function assigns an explicit value for the width expansion to the implicit instance.
• Complex::getWidth() → Float
The function furnishes the width of the implicit instance. If a value was assigned for the
width during or after the initialization by means of the setWidth() method, it is returned,
otherwise the width of the delimiting volume determined by the getLocalBounds() method
(Base interface).
• setHeight(pHeight(Float)) → Void
The function assigns an explicit value for the height expansion to the implicit instance.
• Complex::getHeight() → Float
The function furnishes the height of the implicit instance. If a value was assigned for the
height during or after the initialization by means of the setHeight() method, it is returned,
otherwise the height of the delimiting volume determined by the getLocalBounds() method
(Base interface).
• setDepth(pDepth(Float)) → Void
The function assigns an explicit value for the depth expansion to the implicit instance.
• Complex::getDepth() → Float
The function furnishes the depth of the implicit instance. If a value was assigned for the
depth during or after the initialization by means of the setDepth() method, it is returned,
otherwise the depth of the delimiting volume determined by the getLocalBounds() method
(Base interface).
• setOrigin(pOrigin(Float[3])) → Void
The function assigns an offset of the reference origin with respect to the minimum of the
local delimiting volume to the implicit instance.
• getOrigin() → Float[3]
The function delivers the offset of the reference origin of the implicit instance with respect
to the minimum of the local delimiting volume. If a value was assigned for the offset during
or after the initialization by means of the setOrigin() method, it is returned, otherwise it is
determined with the help of the getLocalBounds() method of the Base interface.

143

<!-- Page 146 -->

Materials

In each of the following functions, a call of setPlProgram() is performed at the beginning.

• Material::getMatCategories() → Symbol[]
Itdeliversthelistofmaterialcategoriescurrentlydefinedfortheimplicitinstance(fordetailed
specifications see the Material interface). The standard implementation delivers a value of
type Void.
• Material::getAllMatCats() → Symbol[]
It furnishes the list of all material categories that are potentially definable for the implicit
instance. The standard implementation delivers the return value of the getMatCategories()
function.
• Material::getCMaterials(pCat(Symbol)) → Symbol[]
Itdeliversthelistofallmaterialsthatareapplicablewithinthetransferredmaterialcategory
fortheimplicitinstance(fordetailedspecificationsseetheMaterialinterface). Thestandard
implementation delivers the return value of the function of the same name of the global
planning instance if its type is OiPlanning, otherwise a value of type Void.
• Material::getCMaterial(pCat(Symbol)) → Symbol
The function furnishes the material currently assigned to the implicit instance in the trans-
ferredmaterialcategoryoravalueoftheVoidtypeiftheimplicitinstancedoesnotcurrently
belong to the transferred material category. The standard implementation delivers the re-
turn value of the function of the same name of the global planning instance if its type is
OiPlanning, otherwise a value of type Void.

Note: Concretesubclassesmustoverwritethismethodinsuchawaythatthematerialcurrentlyset
in the object for this category is delivered. The standard implementation (call of the father object)
mustbeperformedonlyifamaterialinthiscategoryhasnotbeenassignedwithexplicitassignment
to the object.
• Material::getMatName(pMat(Symbol)) → String
The function furnishes the material name to the transferred material or a value of the Void
type for the implicit instance if the material is unknown. The standard implementation
delivers the return value of the function of the same name of the global planning instance if
its type is OiPlanning, otherwise the return value of the function of the same name of the
father instance if its type implements the Material interface.

Element Generation

• isElemCatValid(pCat(Symbol)) → Int
The function delivers 1 if instances of the indicated category can be added to the implicit
instance as elements, otherwise 0.
The standard implementation delivers 0.

144

<!-- Page 147 -->

Example: TheisElemCatValid()functionofatypeoftableonwhichinstancesofthe@TOP ELEM
category can be placed, must deliver 1 for this category.

Note: After checking for special categories during an overwriting of the function in derived types,
theinheritedfunctionmustbecalledsothat1isalsodeliveredforthecategorieswhichareallowed
by super types.

• Complex::checkAdd((pType(Type),pObj(MObject),pPos(Float[3]),pParams(Any))→Float[3]

The function checks whether an instance of the indicated type can be inserted as element
into the planning and, if positive, delivers a valid position for the element.
The standard implementation implements the placement of elements of the @TOP ELEM
category if the isElemCatValid() function delivers 1 for this category. The getWidth(), getH-
eight(), getDepth(), and getOrigin() functions are used for this purpose.
• getPDistance() → Float
The function delivers the desired initial distance to the previous element.
The standard implementation delivers the minimum x-value of the local delimiting volume.

Note: The function can be used within the checkAdd() function of the father instance.
The value delivered by the function can be queried by the user through a dialog before the new
elementisinserted. Thesubtypesmustmakeacorrespondingsetfunctionavailableforthispurpose.

• getWallOffset() → Float
The function delivers the desired initial distance to a wall element in front of which the
implicit instance should be placed.
Thestandardimplementationdelivers0.01minustheminimumz-valueofthelocaldelimiting
volume.

Note: The function can be used within the checkAdd() function of the father instance.
The value delivered by the function can be queried by the user through a dialog before the new
elementisinserted. Thesubtypesmustmakeacorrespondingsetfunctionavailableforthispurpose.

• onCreate(pRot(Float), pObj(MObject), pParams(Any)) → Void
The function can be called after the generation of the implicit instance and ends the overall
processofinteractivelyinsertingtheinstanceintotheplanning. Therequestedrotationwith
respect to the y-axis in positive direction, the neighboring element to which the implicit
instance was added, and an additional random parameter are transferred. The standard
implementation implements the required rotation with respect to the y-axis in positive di-
rection.

Note: Thefunctionisusedforsettingobjectpropertiesthatcannotbeperformedduringtheobject
generation(intheinitialize()function)forlackofknowledgeoftheplanningcontext. Thefunctionis

145

<!-- Page 148 -->

usuallysettogetherwiththeappropriateargumentsduringthecheckAdd()ofOiPlanningbymeans
of calling setMethod() (Complex interface).

Element Control

• elRemoveValid(pObj(MObject)) → Int
The function returns True if the transferred child instance can be removed. The function is
called in REMOVE ELEMENT rules in addition to the removeValid() function of the Base
interface for the instance that is to be removed.

Example: A cupboard unit subplanning can use this, for example, to remove elements from the
left and right side only.

The standard implementation delivers True.
• isElOrderSubPos(pObj(MObject)) → Int
The function delivers True if the transferred child instance may not appear as a subitem in
an order list.

Example: The function can be used in algorithms for generating order lists to move certain items
to specific positions in the order list.

The standard implementation delivers True.

Product Data

• Article::getArticleSpec() → String
Thestandardimplementationofthefunctiondelegatesthequerytotheclass2Article()func-
tion of the global product data manager (OiPDManager type), if such an instance exists.
• Article::setArticleSpec(pSpec(String)) → Void
The standard implementation does not perform any actions.
• Article::getArticleParams() → Any
The standard implementation delivers a value of type Void.
• Article::getArticlePrice(pLanguage(String)) → Any[]
Thestandardimplementationofthefunctiondelegatesthequerytothefunctionofthesame
name of the global product data manager (OiPDManager type), if such an instance exists.
• Article::getArticleText(pLanguage(String), pForm(Symbol)) → String[]
Thestandardimplementationofthefunctiondelegatesthequerytothefunctionofthesame
name of the global product data manager (OiPDManager type), if such an instance exists.
• Article::getArticleFeatures(pLanguage(String)) → Any
Thestandardimplementationofthefunctiondelegatesthequerytothefunctionofthesame
name of the global product data manager (OiPDManager type), if such an instance exists.

146

<!-- Page 149 -->

Consistence Check

• Article::checkConsistency() → Int
The function checks the consistence and completeness of the planning element and is called
by OiPlanning::checkConsistency(). If required, corrections or additions are performed or
error messages are generated.
The standard implementation delegates to the function of the same name of the global
product data manager (OiPDManager type).

Child Transformations

• elemTranslation(pEl(MObject), pOldPos(Float[3])) → Void
The function handles a (completed) translation of the transferred child instance of the
OiPlElement or OiPart type.
ForinstancesoftheOiPlElementtype,thisisaccomplishedinthesamewayastheOiPlanning
function of the same name. For instances of the OiPart type, the onTranslate() function is
called.

Note: The function is called from the TRANSLATE rule of the transferred child instance.

• elemRotation(pEl(MObject), pOldRot(Float)) → Void
Thefunctionhandlesthe(completed)rotationofthetransferredchildinstanceoftheOiPlEle-
ment or OiPart type.
ForinstancesoftheOiPlElementtype,thisisaccomplishedinthesamewayastheOiPlanning
functionofthesamename. ForinstancesoftheOiParttype,theonRotate()functioniscalled.

Note: The function is called from the ROTATE rule of the transferred child instance.

Translation and Rotation

• translateValid(pOldPos(Float[3])) → Int
Thefunctiondelivers1iftheplanningelementcanbemovedfromthetransferredoldposition
to the new current position, otherwise it delivers 0.
The standard implementation delivers 1.

Note: The function is used within the elemTranslation() function of the global planning instance
(OiPlanning type).
• translated(pOldPos(Float[3])) → Int
The function is called by the elemTranslation() function of the global planning instance to
enable the planning element to individually react to its translation. The return value is 1 if
the function has already checked the validity of the new position, otherwise it is 0.

147

<!-- Page 150 -->

• rotateValid(pOldPos(Float)) → Int
Thefunctiondelivers1iftheplanningelementcanberotatedfromthetransferredoldrotary
angle to the new current rotary angle, otherwise it is 0.
The standard implementation delivers 1.

Note: The function is used within the elemRotation() function of the global planning instance
(OiPlanning type).
• rotated(pOldPos(Float)) → Int
The function is called by the elemRotation() function of the global planning instance to
enable the planning element to individually react to its rotation. The return value is 1 if the
function has already checked the validity of the new rotary angle, otherwise it is 0.

### Rules

• REMOVE ELEMENT(pValue(Symbol)) → Int
The rule prevents the removal of child instances whose removeValid() function delivers False
or for which the elRemoveValid() function delivers False.
• TRANSLATE(pValue(Float[3])) → Int
The rule delegates the handling of the translation to the elemTranslation() function of the
global planning instance (OiPlanning type).
• ROTATE(pValue(Float)) → Int
The rule delegates the handling of the rotation to the elemRotation() function of the global
planning instance (OiPlanning type).

# 8.4 OiPart

### Description

• The OiPart type is the basic type for functional base types that are used as components in
planning elements (OiPlElement class).
• Interface(s): Base, Complex, Material, Property, Article

### Initialization

• OiPart(pFather(MObject), pName(Symbol))
The function initializes an instance of the OiPart type.

148

<!-- Page 151 -->

### Methods

General Methods

• getPlanning() → MObject
The function delivers the root object of the planning hierarchy (t) if this is an instance of
OiPlanning, otherwise a value of the type Void.

Spatial Model

• setWidth(pWidth(Float)) → Void
The function assigns an explicit value for the width expansion to the implicit instance.
• Complex::getWidth() → Float
The function furnishes the width of the implicit instance. If a value was assigned for the
width during or after the initialization by means of the setWidth() method, it is returned,
otherwise the width of the delimiting volume determined by the getLocalBounds() method
(Base interface).
• setHeight(pHeight(Float)) → Void
The function assigns an explicit value for the height expansion to the implicit instance.
• Complex::getHeight() → Float
The function furnishes the height of the implicit instance. If a value was assigned for the
height during or after the initialization by means of the setHeight() method, it is returned,
otherwise the height of the delimiting volume determined by the getLocalBounds() method
(Base interface).
• setDepth(pDepth(Float)) → Void
The function assigns an explicit value for the depth expansion to the implicit instance.
• Complex::getDepth() → Float
The function furnishes the depth of the implicit instance. If a value was assigned for the
depth during or after the initialization by means of the setDepth() method, it is returned,
otherwise the depth of the delimiting volume determined by the getLocalBounds() method
(Base interface).
• setOrigin(pOrigin(Float[3])) → Void
The function assigns an offset of the reference origin with respect to the minimum of the
local delimiting volume to the implicit instance.
• getOrigin() → Float[3]
The function delivers the offset of the reference origin of the implicit instance with respect
to the minimum of the local delimiting volume. If a value was assigned for the offset during
or after the initialization by means of the setOrigin() method, it is returned, otherwise it is
determined with the help of the getLocalBounds() method of the Base interface.

149

<!-- Page 152 -->

Materials

• Material::getMatCategories() → Symbol[]
Itdeliversthelistofmaterialcategoriescurrentlydefinedfortheimplicitinstance(fordetailed
specifications see the Material interface). The standard implementation delivers a value of
type Void.
• Material::getAllMatCats() → Symbol[]
It furnishes the list of all material categories that are potentially definable for the implicit
instance. The standard implementation delivers the return value of the getMatCategories()
function.
• Material::getCMaterials(pCat(Symbol)) → Symbol[]
Itdeliversthelistofallmaterialsthatareapplicablewithinthetransferredmaterialcategory
fortheimplicitinstance(fordetailedspecificationsseetheMaterialinterface). Thestandard
implementation delivers the return value of the function of the same name of the father
instance if its type implements the Material interface, otherwise a value of type Void.
• Material::getCMaterial(pCat(Symbol)) → Symbol
The function furnishes the material currently assigned to the implicit instance in the trans-
ferredmaterialcategoryoravalueoftheVoidtypeiftheimplicitinstancedoesnotcurrently
belongtothetransferredmaterialcategory. Thestandardimplementationdeliversthereturn
value that was delivered by the function of the same name from the father instance.
• Material::getMatName(pMat(Symbol)) → String
The function furnishes the material name to the transferred material or a value of the Void
type for the implicit instance if the material is unknown. The standard implementation
delivers the return value of the function of the same name of the global planning instance if
its type is OiPlanning, otherwise the return value of the function of the same name of the
father instance if its type implements the Material interface.

Element Generation

• isElemCatValid(pCat(Symbol)) → Int
The function delivers 1 if instances of the indicated category can be added to the implicit
instance as elements, otherwise 0.
The standard implementation delivers 0.

Example: TheisElemCatValid()functionofatypeoftableonwhichinstancesofthe@TOP ELEM
category can be placed, must deliver 1 for this category.

Note: After checking for special categories during an overwriting of the function in derived types,
theinheritedfunctionmustbecalledsothat1isalsodeliveredforthecategorieswhichareallowed
by super types.

150

<!-- Page 153 -->

• Complex::checkAdd((pType(Type),pObj(MObject),pPos(Float[3]),pParams(Any))→Float[3]

The function checks whether an instance of the indicated type can be inserted as element
into the planning and, if positive, delivers a valid position for the element.
The standard implementation implements the placement of elements of the @TOP ELEM
category if the isElemCatValid() function delivers 1 for this category. The getWidth(), getH-
eight(), getDepth(), and getOrigin() functions are used for this purpose.

Element Control

• elRemoveValid(pObj(MObject)) → Int
The function returns True if the transferred child instance can be removed. The function is
called in REMOVE ELEMENT rules in addition to the removeValid() function of the Base
interface for the instance that is to be removed.

Example: A cupboard unit subplanning can use this, for example, to remove elements from the
left and right side only.

The standard implementation delivers True.
• isElOrderSubPos(pObj(MObject)) → Int
The function delivers True if the transferred child instance may not appear as a subitem in
an order list.

Example: The function can be used in algorithms for generating order lists to move certain items
to specific positions in the order list.

The standard implementation delivers True.

Product Data

• Article::getArticleSpec() → String
Thestandardimplementationofthefunctiondelegatesthequerytotheclass2Article()func-
tion of the global product data manager (OiPDManager type), if such an instance exists.
• Article::setArticleSpec(pSpec(String)) → Void
The standard implementation does not perform any actions.
• Article::getArticleParams() → Any
The standard implementation delivers a value of type Void.
• Article::getArticlePrice(pLanguage(String)) → Any[]
Thestandardimplementationofthefunctiondelegatesthequerytothefunctionofthesame
name of the global product data manager (OiPDManager type), if such an instance exists.

151

<!-- Page 154 -->

• Article::getArticleText(pLanguage(String), pForm(Symbol)) → String[]
Thestandardimplementationofthefunctiondelegatesthequerytothefunctionofthesame
name of the global product data manager (OiPDManager type), if such an instance exists.
• Article::getArticleFeatures(pLanguage(String)) → Any
Thestandardimplementationofthefunctiondelegatesthequerytothefunctionofthesame
name of the global product data manager (OiPDManager type), if such an instance exists.

Consistence Check

• Article::checkConsistency() → Int
The function checks the consistence and completeness of the planning element and is called
by OiPlanning::checkConsistency(). If required, corrections or additions are performed or
error messages are generated.
The standard implementation delegates to the function of the same name of the global
product data manager (OiPDManager type).

Translation and Rotation

• onTranslate(pOldPos(Float[3])) → Void
The function is called by the translation rule and is used in derived classes to implement a
specific behavior for a move.
• onRotate(pOldRot) → Void
The function is called by the rotation rule and is used in derived classes to implement a
specific behavior for a rotation.

### Rules

• REMOVE ELEMENT(pValue(Symbol)) → Int
The rule prevents the removal of child instances whose removeValid() function delivers False
or for which the elRemoveValid() function delivers False.
• TRANSLATE(pValue(Float[3])) → Int
If the father instance is of OiPlElement type, the handling of the translation is delegated
to its elemTranslation() function, otherwise to the onTranslate() function of the implicit
instance.
• ROTATE(pValue(Float)) → Int
If the father instance is of OiPlElement type, the handling of the rotation is delegated to its
elemRotation() function, otherwise to the onRotate() function of the implicit instance.

152

<!-- Page 155 -->

# 8.5 OiUtility

### Description

• The OiUtility type is the basic type for types that are used for specific tasks, e.g., for the
representation and storage of the global data of a program.
• Interface(s): MObject

### Initialization

• OiUtility(pFather(MObject), pName(Symbol))
The function initializes an instance of the OiUtility type.

# 8.6 OiPropertyObj

### Description

• TheOiPropertyObjtypeisthebasictypefortypesthatareusedforspecifictasksandfeature
properties.
• Super type: OiUtility
• Interface(s): MObject (inherited), Property

### Initialization

• OiPropertyObj(pFather(MObject), pName(Symbol))
The function initializes an instance of the OiPropertyObj type.

### Methods

General Methods

• getPlanning() → MObject
The function delivers the root object of the planning hierarchy (t) if this is an instance of
OiPlanning, otherwise a value of the type Void.
• isCutable() → Int
See the function of the same name of the Base interface.
• removeValid() → Int
See the function of the same name of the Base interface.

153

<!-- Page 156 -->

# 8.7 OiOdbPlElement

### Description

• The OiOdbPlElement type is the basic type for planning elements whose geometries are
generated by the ODB.
• Super type: OiPlElement
• Interface(s): Base, Complex, Material, Property, Article
• The most important function of the OiOdbPlElement class consists of providing the ODB
information in form of a hash table returned by getOdbInfo(). It contains an entry for the
ODB name and an additional entry for each property, where the property key is also used
as key in the hash table. Thus, the values of the properties are available in the ODB for the
parameterization of the geometries.

### Initialization

• OiOdbPlElement(pFather(MObject), pName(Symbol))
The function initializes an instance of the OiOdbPlElement type analogous to OiPlElement.
In addition, the translation in x- and z-direction is enabled and blocked in y-direction.

### Methods

General Methods

• setOdbType(pArticle(String)) → Void (protected)
The function sets the ODB name on the basis of the transferred article. The ODB name is
determined by calling the article2ODBType() method on the PD manager. If this method
does not deliver an ODB name, a name is generated by default. This name consists of the
series of the article and the article designation, where all characters in the article designa-
tion except for letters, numbers and underscore sign are replaced by XX. XX represents the
hexadecimal representation of the code of the respective character. The underscore sign is
replaced by two succeeding underscores.
• setArticleSpec(pArticle(String)) → Void
The function assigns a new base article number to the implicit instance. This causes the
initialization of the ODB information and the subsequent generation of the geometries by
means of calling createOdbChildren(@NEW).
• getArticleSpec() → String
The function delivers the name of the article (base article number) to which the implicit
instance corresponds or a value of type Void if no article specification is available for the
implicit instance.
The name of the article is determined by means of the ODB name.

154

<!-- Page 157 -->

• propsChanged(pPKeys(Symbol[]), pDoChecks(Int)) → Int
If the list of property keys pPKeys is not empty, the createOdbChildren(@INCR) function
is called to regenerate the geometries for this article. In the current implementation, the
pDoChecks parameter is ignored and the return value is always 1.
• setPropValue(pKey(Symbol), pValue(Any)) → Int
First, the setPropValue() method of the OiPlElement top class is called. Next, an iteration
is performed on all direct children of the implicit instance and the setPropValue() method is
called for every child that is either an OiPlElement or an OiPart.
• getOdbInfo() → Hash
The function returns a hash table with the ODB parameters. It contains the ODB name
determined from the base article number and the current property values.
• createOdbChildren(pVal(Symbol)) → Void
The function controls the generation of the child objects via ODB. Dependent upon the
pValparameter,thechildobjectsareeithergeneratedcompletelynew(@NEWand@RULE)
or adapted to the new ODB information (@INCR). Usually, either @NEW or @INCR is
transferred as argument. The @RULE argument is intended for use in the FINISH EVAL
rule.

Note: The current implementation always performs a complete regeneration of the child objects.
Witharegenerationofthechildobjects,thosechildobjectsthatarenotpartofthearticle,suchas
accessories, are deleted and not displayed again. Since the regeneration of child objects can lead to
random changes in the geometry of the article, a general discussion of this problem is not possible.

Translation and Rotation

• translated(pOldPos(Float[3])) → Int
Thefunctioniscalledfollowingeverytranslationandcheckswhethertheobjectatthecurrent
position causes a collision. If this is the case, the function attempts to determine a new
position on the line between old and current position that is as close as possible to the
current position and on which the object does not collide.

155

<!-- Page 158 -->

# Chapter 9

# Types for Product Data

# Management

On principle, OFML allows the complete description of logics and dependencies of types without
external data records. Still, a specification of product properties via external data records could
be desirable for various reasons, e.g., to be able to use an existing data array directly in OFML.
For this purpose, OFML defines a powerful, generic product data management interface. The
concept of a product data management (see also Figure 9.1) conceives that there are a number of
external product databases (possibly in different data formats), but they are managed by a global
product data manager and communicate with this manager via a uniform generic interface. For
each concrete data format (but not for each external product database), a special interface type
must be implemented (subtypes of OiProductDB) that takes over the interpretation of the data
format on the OFML level.

OiPlanning OiPDManager OiProductDB

. . .
ProductDB_A ProductDB_Z

Figure 9.1: Conceptual model of the product data management types

Example: A concrete example is the data format that is generated from a SAP/R3 system while main-
taining the physical basic format. The data is distributed over several tables that are interlinked. The
relational knowledge is stored in expressions of the ABAP/4 language. Using the implementation of a
respectivesubtypeofOiProductDB,thisformatcannowbereadinontheOFMLlevel. Thisincludesthe
implementation of an ABAP/4 parser.

156

<!-- Page 159 -->

# 9.1 OiPDManager

### Description

• An instance of the OiPDManager type manages a set of external product databases (OiPro-
ductDB type) and allows access to the product data stored in these databases.
• Exactly one instance of this type exists for each planning. This instance is referred to as
product data manager. It is generated by means of the setPDManager() function of the
OiPlanning type.
• The product data manager also manages the assignment of types to articles and vice versa.
• Interface(s): MObject

### Initialization

• OiPDManager(pFather(MObject), pName(Symbol))
The function initializes an instance of the OiPDManager type.

### Methods

Management of the Product Databases

• addProductDB(pType(Type), pID(Symbol), pPath(String), pProgList(Symbol[]) → MObject
The function generates an instance of the transferred type (subtype of OiProductDB) and
registersitundertheindicatedID.Thefilesystempathofthedirectorythatcontainsthefiles
of the product database is transferred in the pPath parameter (relative to the root directory
of the runtime environment). The additional pProgList parameter specifies the programs
(IDs) that are represented in the database. If a product database is already registeredunder
the indicated ID, the list of programs of the product database is expanded, if required.
The return value is the reference to the (generated) product database instance.
• delProductDB(pID(Symbol)) → Void
The function deletes and removes the product database with the indicated ID from the set
of registered product databases.
• clearProductDBs() → Void
The function deletes and removes all registered product databases.
• getPDB IDs() → Symbol[]
The function delivers the IDs of all registered product databases.
• getProductDB(pID(Symbol)) → MObject
The function delivers the product database instance that is registered under the indicated
ID or a value of type Void, if such an ID is not available.

157

<!-- Page 160 -->

• getPDBFor(pObj(MObject)) → MObject
The function delivers the product database instance that is responsible for the transferred
planning element or a value of type Void, if such a product database is not found. The
responsibility results from the program association of the planning element.
• getProgPDB(pPID(Symbol)) → MObject
The function delivers the product database instance that is responsible for the program
specified by the transferred ID or a value of type Void, if such a product database is not
found.

Assignment of Types to Articles

• article2Class(pArticle(String)) → String
Thefunctiondeliversthenameofthetypethatmodelsthearticlewhichwasspecifiedbased
on its article number, or a value of the type Void if no assignment could be found.
• article2Params(pArticle(String)) → String
Thefunctiondeliverstheparametervaluesforthetypethatmodelsthearticlespecifiedbyits
article number. The return value is a string that contains the presentation of the parameter
values stored in the product data. The function delivers a value of type Void if no entry for
the article was found in the product data.
• object2Article(pObj(MObject)) → String
The function delivers the name of the article (article number) to which the transferred plan-
ning element corresponds.
Theassignmentiscomposedoftheprogramassociation,theimmediatetype,andtherelevant
parameters (see OiPlElement::getArticleParams() function) of the planning element.
• class2Articles(pObj(MObject)) → String[]
The function delivers the list of article (numbers) that are represented by the class of trans-
ferred planning elements. The return value is a value of type Void if no article assignment
for the class exists.

Properties

• setupProps(pObj(MObject)) → Void
The function defines the initial properties for the indicated planning element based on the
product data for the article that corresponds to the type of the planning element and its
program association. The language currently selected in the global planning instance (see
OiPlanning type) is used for designations (labels, values).
• evalPropValue(pObj(MObject), pPKey(Symbol), pValue(Any), pOldValue(Any), pOldArti-
cle(String)) → Int
The function evaluates the relational knowledge in the product data after the property of
the indicated planning element that was specified by its key was set to the transferred new

158

<!-- Page 161 -->

value. In addition, the old property value and the base article number are transferred before
the value assignment. The evaluation of the value assignment can lead to changes of the
definition (value ranges) or current values of other properties of the planning element. In
this case, the function delivers 0, otherwise 1.

Note: The function is called from the setPropValue() function of the Property interface.

• checkConsistency(pObj(MObject)) → Int
The function checks the correctness of the product data of the article that is represented by
thetransferredinstance. Theglobalerrorlogisusedforerrormessages(seethefunctionofthe
same name of the Article interface). The standard implementation delegates to the function
of the same name of the product database that is responsible for the article (OiProductDB
type).

Article Information

• getXArticleSpec(pObj(MObject), pType(Symbol)) → String
Thefunctiondeliversthespecificationoftherequestedtypeforthearticlethatisrepresented
by the transferred instance or a value of type Void if no article specification of the required
type is available for the implicit instance. Semantics and return value of the function corre-
spond to the function of the same name of the Article interface, where only the @VarCode
and@Finalspecificationtypesareallowed. Thestandardimplementationofthefunctiondel-
egatesthequerywiththe@VarCodespecificationtypetothegetVarCode()functionandwith
the @Final specification type to the getFinalArticleSpec() function of the product database
that is responsible for the article instance (OiProductDB type), if such an instance exists.
Insteadofthearticleinstance,itsbasearticlenumberandalistofitscurrentpropertyvalues
are transferred.
• setXArticleSpec(pObj(MObject), pType(Symbol), pSpec(String)) → Void
Thefunctionassignsanewarticlespecificationofthespecifiedtypetothetransferredarticle
instance. Semantics and return value of the function correspond to the function of the same
name of the Article interface, where only the @VarCode specification type is allowed. The
standardimplementationofthefunctionusesthevarCode2PValues()functionoftheproduct
database that is responsible for the article instance (OiProductDB type) to determine the
product properties that match the transferred variant code. If the obtained values differ
from the current values of the respective properties, they will be reassigned by means of the
setPropValue() function (Property interface) of the transferred article instance.
• getArticlePrice(pObj(MObject), pLanguage(String), ...) → Any[]
The function delivers price information for the transferred planning element in the specified
language. Semanticsandreturnvalueofthefunctioncorrespondtothefunctionofthesame
name of the Article interface. The standard implementation of the function delegates the
query to the function of the same name of the product database that is responsible for the
planning element (OiProductDB type), if such an instance exists. Instead of the planning
element, its base article number and a list of its current property values are transferred.

159

<!-- Page 162 -->

• getArticleText(pObj(MObject), pLanguage(String), pForm(Symbol)) → String[]
The function delivers describing article information for the transferred planning element
in the specified language and in the specified form. Semantics and return value of the
function correspond to the function of the same name of the Article interface. The standard
implementation of the function delegates the query to the function of the same name of the
product database that is responsible for the planning element (OiProductDB type), if such
an instance exists. Instead of the planning element, its base article number is transferred.
• getArticleFeatures(pObj(MObject), pLanguage(String)) → Any
The function delivers a description of the configurable product properties for the transferred
planning element in the specified language. Semantics and return value of the function
correspond to the function of the same name of the Article interface. The standard imple-
mentation of the function delegates the query to the getPropDescription() function of the
product database that is responsible for the planning element (OiProductDB type), if such
an instance exists. Instead of the planning element, its base article number and a list of its
current property values are transferred.

# 9.2 OiProductDB

### Description

• An instance of the OiProductDB type manages exactly one product database and offers
services for access and evaluation of information about articles and their properties.
• Interface(s): MObject

### Initialization

• OiProductDB(pFather(MObject), pName(Symbol), pID(Symbol))
The function initializes an instance of the OiProductDB type with the indicated ID. The ID
cannot be changed later.

### Methods

Article Configuration

Some of the functions described below expect a pPValues parameter that contains the current
article configuration. This parameter is a list that contains a vector made up of the following
elements for each product property:

1. the feature class (String or Void, unless relevant)
2. the (language-independent) designator of the feature (String)

160

<!-- Page 163 -->

3. the value of the feature (Any)
4. the list of the currently possible values (List or Void, unless relevant)
5. the activation state of the property that is assigned to the feature (Int)

General Methods

• getID() → Symbol
The function delivers the ID of the product database.
• setPrograms(pProgList(Symbol[])) → Void
The function assigns the number of programs (IDs) that are represented in the product
database to the implicit instance.
• getPrograms() → Symbol[]
The function delivers the number of programs (IDs) that are represented in the product
database.
• setDataBasePath(pDir(String)) → Void
The function assigns the root directory of the product data to the implicit instance.
• getDataBasePath() → String
The function delivers the root directory of the product data.
• getPDManager() → MObject
The function delivers the reference to the global product data manager.

Features and Relational Knowledge

• hasProductKnowledge() → Int
ThefunctionsdeliversTrueiftheproductdatabasecontainsrelationalknowledgewhichmust
be evaluated with a change of feature values.
• getArticlePropClasses(pArticle(String)) → Any
The function delivers a list with feature classes to which the indicated article (base article
number) is assigned.
• getPropDefs(pArticle(String), pPropOffset(Int), pLanguage(String), pChangedProp(Any[]),
pPValues(Vector[])) → Any
The function delivers the property definitions for all features of the transferred article (base
article number).
The pPropOffset parameter specifies the number at which positions can be assigned for the
properties. The specified language (ISO code) is used for designations (label, values). If no
language is specified (Void), English is used. If the pChangedProp parameter is not a value
of type Void, it specifies a feature whose value was changed so that the function is called.

161

<!-- Page 164 -->

In this case the parameter contains a three-digit vector consisting of (language-independent)
designator of the feature, new and old feature value. The pPValues parameter describes the
currentarticleconfiguration(seeabove)orisavalueoftypeVoidifthefunctioniscalledfor
an article that has not yet been initialized.
The return value is a list of seven-digit vectors. Each vector describes a feature and consists
of the following:
1. Feature class (String or Void, unless relevant).
2. (Language-independent) designation of the feature (String).
3. Specificationoftheassociatedproperty(Any[5])inaccordancewiththesetupProperty()
function of the Property interface.
4. (Initial) value of the feature or Void if no value is (pre)defined.
5. List of all possible values in so far as several values (List or Void are defined for the
feature, unless relevant).
The entries are two-digit vectors that contain the value and the language-independent
description of the value. For optional features, the list must contain the value ”not
selected” which must be specified as [ @ VOID, " @ VOID"] .
6. Position in the property list (Int).
7. Activation status for the property (Int).
• checkConsistency(pArticle(String),pPValues(Vector[]),pLanguage(String),pErrorList(String[]))
→ Int
The function delivers True if the transferred article configuration for the indicated article
(base article number) is correct from a product point of view. Error messages are attached
to the list that is transferred in the pErrorList parameter. Here, the language specified in
the pLanguage parameter is used.

Article Information

• getVarCode(pArticle(String), pPValues(Any[]), ...) → String
The function delivers the variant code for the transferred article (base article number) and
the transferred article configuration. If an additional optional parameter is indicated, it
specifies whether the feature values contained in the article configuration are OFML values
of the associated property (True) or whether they are given in the form used by the product
database (False). Without any information, True is assumed.
• varCode2PValues(pArticle(String), pVarcode(String)) → Any[]
The function delivers the feature values to the transferred variant code for the indicated
article (base article number).
The return value is a list that contains a vector consisting of the following elements for each
product feature:
1. the feature class (String or Void, unless relevant)
2. the (language-independent) designator of the feature (String)

162

<!-- Page 165 -->

3. the value of the feature (Any)
• getFinalArticleSpec(pArticle(String), pPValues(Any[])) → String
Thefunctiondeliversthefinalarticlenumberforthetransferredarticle(basearticlenumber)
and the transferred article configuration.
• getArticlePrice(pArticle(String), pPValues(Any[]), pLanguage(String), ...) → Any[]
The function delivers price information for the transferred article (base article number) and
the transferred article configuration in the specified language. If an additional optional
parameter is given, it specifies the desired currency.
The return value corresponds to the function of the same name of the Article interface.
• getArticleText(pArticle(String), pLanguage(String), pForm(Symbol)) → String[]
The function delivers the article description for the transferred article (base article number)
in the specified language and in the specified form. The pForm parameter may take on the
following values:
– @ short short description
– @long long description
The return value is a list of strings that contain the individual lines of the description or a
value of type Void if no article description is available for the implicit instance.
• getPropDescription(pArticle(String),pPValues(Any[]),pNeedSymbols(Int),pLanguage(String))
→ Any
The function delivers a description of the transferred article configuration for the specified
article (base article number) in the specified language.
The return value is a list of two-digit vectors whose first element (String) labels the feature,
while the second element contains the current value (as character string) of the feature. If
the pLanguage parameter contains a value of type Void, language-independent designators
are furnished for feature and value.
If the pNeedSymbols parameter has the value 1, the list entries consist of four-digit vectors
with the following fields in the indicated order:
1. language-independent symbol of the feature
2. language-independent designation of the feature
3. language-independent symbol of the current value of the feature
4. language-independent designation of the current value of the feature
The function delivers a value of type Void if no descriptions for the features are available.

163

<!-- Page 166 -->

# Chapter 10

# Types of the Planning

# Environment

# 10.1 The Wall Interface

Wall defines the interface of a wall or some of its parts (e.g., sides) for furniture planning.

• getWallParams()) → [Float, Float, Float[3]]
The function delivers the geometric parameter to be able to place furniture at the wall in
the course of the planning process. The return value is a vector with three elements.

1. Width.
2. Rotary angle (in positive orientation about the y-axis).
3. Position (origin of the local coordinate system).

# 10.2 OiLevel

### Description

• OiLevel models one story of a building that can consist of one or several rooms.
• Interface(s): Base, Complex

### Initialization

• OiLevel(pFather(MObject), pName(Symbol))
The function initializes an instance of the OiLevel type.

164

<!-- Page 167 -->

### Methods

• setDefaultHeight(pHeight(Float)) → Void
The function sets a default for the height of walls to be created. This value is effective only
if there are no walls on the story, otherwise the height of the planning wall (see below) is
used as default.
• Complex::getHeight() → Float
The function delivers the maximum wall height within a story or, if no walls exist, the
specified height.
• setPlanningWall(pWall(MObject)) → MObject
Thefunctionselectsawalltowhichfurnitureistobeaddedinthefollowing. pWallmustbe
an object that implements the Wall interface (Section 10.1). NULL is allowed as a special
value for pWall. In this case, a possibly existing setting is deleted. The function delivers the
new planning wall as return value.
• getPlanningWall() → MObject
The function delivers the specified planning wall (see below). If no planning wall was explic-
itly set, the wall generated last is used.
• setPlanningMode(pMode(Int)) → Void
Thefunctionsetstheplanningmode. Asaminimumrequirement,thevalues0(activatesfur-
nitureplanning)and1(switchestothebasemodeoffloorspaceplanning)mustbedetected.
Values >1 are acceptable depending upon the implementation.
• Complex::checkAdd(pType(Type),pObj(MObject),pPos(Float[3]),pParams(Float[]))→Float[3]

The function checks the insertion of a new wall. pType must be a subtype of OiWall. pObj
mustbeinstanceofasubtypeofOiWalltowhichthenewwallshouldbeattached. IfNULL
is transferred for pObj, attaching is performed at the preset planning wall. (Section 10.2).
pPosisignoredandmaybeNULL. pParamsisNULLorcontainsanoptionallistofdefault
parameters. If available, these parameters are interpreted as follows:
1. Width.
2. Attaching angle.
3. Thickness.
Ifthegivenparameterscanbeinserted,theattachingpositionisreturned,otherwiseNULL.
• objInLevel(pObj(MObject)) → Int
The function delivers 1 if the pObj object is located within the story, otherwise 0. Simplified
tests(e.g.,limitationtothesurroundingrectangleorboundingbox)arepossible,andcollision
must not be observed.

165

<!-- Page 168 -->

# 10.3 OiWall

### Description

• OiWallrepresentsawallasacomponentofastory. Thismaybeanoutsidewalloradividing
wall. Windows, doors, etc. can be inserted in a wall as children.
• Interface(s): Base, Complex, Properties, Material, Wall

### Initialization

• OiWall(pFather(MObject), pName(Symbol))
The function initializes an instance of the OiWall type.

# 10.4 OiWallSide

### Description

• Asinglesideofawallatwhichfurniturecanbeplacedinthecourseoftheplanningprocess.
• Interface(s): Base, Properties, Material, Wall

### Initialization

• OiWallSide(pFather(MObject), pName(Symbol))
The function initializes an instance of the OiWallSide type.

166

<!-- Page 169 -->

# Appendix A

# Product Data Model

Thisappendixdescribestheunderlyingdatamodelforthetypesoftheproductdatamanagement
(Chapter 9). Figure A.1 shows a graphic representation of the model which illustrates the major
1
concepts and terms .

Feature
features rel.knowledge
Name

class
Simple Configurable
Article Feature class
feature feature
Name
rel.knowledge rel.knowledge
Article number
values
price condition value
Kind
Feature value
Value default
value

rel.knowledge

Set
order list
Relation
Kind
Coding
Price condition

Figure A.1: Product data model

1
ThenotationalconventionsusedhereisexplainedinAppendixG.

167

| Feature |
| --- |
| Name |

| Article |
| --- |
| Name
Article number
Kind |

| Feature value |
| --- |
| Value |

| Relation |
| --- |
| Kind
Coding |

<!-- Page 170 -->

### Additional remarks and explanations

Each article is assigned to a certain article type that specifies which actions are allowed for the
article or which meaning certain model properties have. The major article types are ”configurable
article,” ”assembly unit” and ”commercial article.”
Features describe the properties of articles and are combined to feature classes. A feature in a
class can be another class. Each article is assigned one or several feature classes.
Price terms contain the definitions for the base price as well as extra charges and discounts for
configurablearticlesviavariantterms. Relationalknowledgemustbeusedtoestablishtherelation
to the corresponding features or feature values.
Relational knowledge is shown by means of five types of relations:

• Conditions
determine whether a feature may be evaluated or whether a feature value may be set.
• Selection criteria
specify that a feature must be evaluated or that a parts list position must be selected.
• Actions and Procedures
serveforderivationoffeaturevaluesandareexecutedifafeaturevalueisselectedorafeature
isevaluated. Forthispurpose, actionshavedeclarativecharacterandareindependentofthe
orderoftheevaluation. Procedures, ontheotherhand, implementmorecomplexalgorithms
and are executed only at certain times.
• Constraints
serve for monitoring the consistence of a configuration and, therefore, can only be bound to
a configurable article via the configuration profile.

168

<!-- Page 171 -->

# Appendix B

# The 2D Interface

# B.1 Introduction

The 2D interface described in this chapter allows for programming of 2D objects. Altogether, the
generation of 2D objects in OFML can be accomplished in the following ways:

• through generation based on a (3D) OFML geometry,
• through description via the OFML database [ODB],
• through import of an external 2D vector data record (Chapter C), and
• through programming.

A specialty of this 2D programming interface is the fact that the generated 2D objects cannot be
stored persistently. Thus, they must be restored in the appropriate rules (Chapter 5), if required.

# B.2 The 2D Object Hierarchy

The2DobjectsaregenerallyarrangedinatreewherethenodesofthetreeareoftheG2DCompound
type and the leaves are consequently of a type derived from G2DPrimitive. The root of the tree
is always bound to an OFML object that supports the MObject interface so that each 2D object
can directly or indirectly be assigned to an MObject object.
From OFML, the 2D objects are referenced via integer ID’s. An MObject object is not assigned
two 2D objects with the same ID, that is, the ID’s below an MObject object are unique. Assigned
ID’s do not grow monotonously, that is, a new object can receive the ID of an old object that was
deleted.
The object with the ID 0 always exists 1 and is of the G2DCompound type.
1
Infact,itisgeneratedifrequired.

169

<!-- Page 172 -->

# B.3 Coordinates

All coordinates are indicated in the rectangular X/Y coordinate system, where the positive X
axis points to the right and the positive Y axis up. In principle, angular dimensions are radiant
measures and mathematically positive (counterclockwise). The zero angle shows in the direction
of the positive X axis.

# B.4 Methods

The manipulation of 2D objects is carried out via the methods listed in the following subsections.

### B.4.1 new2DObj

t.new2DObj( parent id , object type , ...)
All 2D objects are generated with the new2DObj method. Their first argument is the ID of the
father object which must be of the G2DCompound type. The second argument is a symbol which
determines the type of 2D object to be generated. The remaining arguments are dependent upon
the type of the object to be generated. The return value is the ID of the newly generated object.
The exact form of the calls of new2DObj is described in the section B.5 in the respective object-
specific subsections.

### B.4.2 delete2DObj

t.delete2DObj(obj id)
The delete2DObj method removes the object with the indicated ID and, if required, recursively
all existing child objects of this object.

### B.4.3 set2DObjAttr

t.set2DObjAttr(obj id, attr type,
...)
The set2DObjAttr method sets the attributes of existing objects. The first argument is the ID of
the object of which an attribute is to be set. The second argument is a symbol which determines
the type of the attribute to be set. The remaining attributes are dependent upon the attribute
type.
The exact form of the calls of set2DObjAttr is described in the B.6 section in the respective
attribute-specific subsections.

170

<!-- Page 173 -->

### B.4.4 translate2DObj

t.translate2DObj( obj id , [ x , y ])
The translate2DObj method moves the G2DCompound object with the ID obj id relative to the
current position in the coordinate system of the father object by x;y.

### B.4.5

### rotate2DObj

t.rotate2DObj( obj id , angle )
The rotate2DObj methodrotatesthe G2DCompound objectwiththeIDobj idrelativetothecurrent
rotationbytheangleangle. Therotationiscarriedoutaroundtheoriginofthecoordinatesystem
of the father object.

# B.5 Object Types

The following subsections list the available 2D object types with their attributes. Besides the
specified attributes, every type has the Pickable and Snapable attribute.

### B.5.1 G2DCompound

A G2DCompound object differs from all other objects that are derived from G2DPrimitive in that
it

• can have additional 2D objects as children and
• can be translated, rotated and scaled.

A new object is generated with the method
G2DCompound
t.new2DObj(parent id, @COMPOUND)

### B.5.2 G2DPoints

An object of the G2DPoints type consists of a list o f X/Y coordinates that describe the center of
the individual points. In addition, it features the attributes Color, PointSize, and PointSmooth.
A new G2DPoints object with n points is generated with the method
t.new2DObj( parent id , @POINTS, [[ x , y ], ..., [ x , y ]])
0 0 n−1 n−1

171

<!-- Page 174 -->

### B.5.3 G2DLines

Anobjectofthe G2DLines typeconsistsofindividuallinesegmentsthataredefinedintheX/Yco-
ordinatesystembymeansoftheirstartandendpoints. ItfeaturestheattributesColor,LineWidth,
and LineStyle.
A new G2DLines object with n lines is generated with the method
t.new2DObj( parent id , @LINES, [[ x , y ], ..., [ x , y ]])
0 0 2n−1 2n−1
where x ;y specifies the start point and x ;y the end point of a line.
2i 2i 2i+1 2i+1

### B.5.4 G2DLineStrip

An object of the G2DLineStrip type consists of a series of at least two points that are connected
witheachotherbymeansofindividuallinesegmentsinthespecifiedorderwhere, incontrastwith
G2DLineLoop , the last point is not connected with the first point. It features the attributes Color,
LineWidth, and LineStyle.
A new G2DLineStrip object with n points is generated with the method
t.new2DObj(parent id, @LINE STRIP, [[x , y ], ..., [x , y ]])
0 0 n−1 n−1

### B.5.5 G2DLineLoop

An object of the G2DLineLoop type consists of a series of at least two points that are connected
with each other by means of individual line segments in the specified order where, in contrast
with G2DLineStrip, the last point is also connected with the first point. It features the attributes
Color, LineWidth, and LineStyle.
A new G2DLineLoop object with n points is generated with the method
t.new2DObj(parent id, @LINE LOOP, [[x , y ], ..., [x , y ]])
0 0 n−1 n−1

### B.5.6

### G2DConvexPolygon

AnobjectoftheG2DConvexPolygontypeisdescribedbyaseriesofatleastthreepointsthatmust
result in a convex polygon when connected with each other, including the last point with the first
point. It features the attributes Color, PointSize, PointSmooth, LineWidth, LineStyle, FillStyle,
andPolygonMode. DependinguponPolygonMode,onlyonesubsetoftheattributesisusedineach
case.
A new G2DConvexPolygon object with n corner points is generated with the method
t.new2DObj( parent id , @POLYGON, [[ x , y ], ..., [ x , y ]])
0 0 n−1 n−1

172

<!-- Page 175 -->

### B.5.7 G2DRectangle

Anobjectofthe G2DRectangle typeisdescribedbytwocornerpointslyingdiagonallyoppositeeach
other. It features the attributes Color, PointSize, PointSmooth, LineWidth, LineStyle, FillStyle,
andPolygonMode. DependinguponPolygonMode,onlyonesubsetoftheattributesisusedineach
case.
A new G2DRectangle object is generated with the method
t.new2DObj( parent id , @RECTANGLE, [[ x , y ], [ x , y ]])
0 0 1 1
where the rectangle has the four cornerpoints x ;y , x ;y , x ;y and x ;y .
0 0 0 1 1 0 1 1

### B.5.8 G2DText

An object of the G2DText type consists of an ASCII text positioned relative to a reference point.
It features the attributes Color, Text, Position, Height, AspectRatio, and Alignment.
A new G2DText object is generated with the method
t.new2DObj(parent id, @TEXT, [x, y], text)
where x;y is the position and text a character string with the text to be represented.

### B.5.9 G2DArc

AnobjectoftheG2DArctyperepresentsthearcofacirclethatisdescribedbymeansofitscenter,
radius, start and end angle. The circle segment is drawn in mathematically positive direction of
rotation from start to end angle. G2DArc objects feature the attributes Color, LineWidth, and
LineStyle.
A new G2DArc object is generated with the method
t.new2DObj(parent id, @ARC, [x , y ], radius, start, end)
center center
Using the method
t.new2DObj(parent id, @CIRCLE, [x , y ], radius)
center center
generates the special case of an arc of a circle where start=0 and end=2π.

### B.5.10 G2DEllipse

An object of the G2DEllipse type represents an ellipse that is described by means of its center,
radius in x and y direction, and rotary angle about the center.
A new G2DEllipse object is generated with the method
t.new2DObj( parent id , @ELLIPSE, [ x , y ], [ x , y ], angle )
center center radius radius

173

<!-- Page 176 -->

# B.6 Attributes

The following subsections describe the attributes supported for 2D objects.

### B.6.1 Color

Using the call
t.set2DObjAttr( obj id , @COLOR, [ red , green , blue ])
sets the color of the object specified by the ID obj id to the RGB value red; green; blue, where
the three color components must be given as floating point values in the interval [0.0,1.0].

### B.6.2 PointSize

Using the call
t.set2DObjAttr( obj id , @POINT SIZE, point size )
sets the size of a point to the floating point value point size. For the screen display, a value of
1.0 corresponds to a point size of one pixel. For printout, 1.0 should correspond to a size of 1pt
(1/72in).
The standard value of the point size is 1.0

### B.6.3 PointSmooth

Using the call
t.set2DObjAttr(obj id, @POINT SMOOTH, smooth)
specifies for points whose size is not 1.0 whether the point should be represented as a square
(smooth = 0) or as a filled circle with a smooth edge (smooth (cid:54)= 0). This setting is only relevant
for screen display with OpenGL. The screen display with other drivers or the printout can ignore
the PointSmooth flag if the point is always represented as a filled circle.
The standard value for the PointSmooth flag is 0.

### B.6.4 LineWidth

Using the call
obj id line width
t.set2DObjAttr( , @LINE WIDTH, )
setsthelinewidthtoline widthpixels(screendisplay)orpoints(1pt=1/72in)(print). line width
is given as floating point value.
The standard value for the line width is 1.0.

174

<!-- Page 177 -->

### B.6.5 LineStyle

Using the call
t.set2DObjAttr( obj id , @LINE STYLE, factor , pattern )
sets the line style. In this case, pattern is a symbol that can accept the values listed in table B.1.

Sample Description
@DEFAULT The preset line style is used.
@SOLID A continuous line is drawn.
@DASHED A dashed line is drawn. The factor factor determines the length of
the line segments displayed and not displayed.
@DOTTED A dotted line is drawn. The factor factor determines the distance
between the centers of two neighboring points.
Adot-dashlineisdrawn. Thefactor factordeterminesthelengthof
@DASH DOTTED
the displayed line segment and half the length of the non-displayed
line segments.
A dash double-dotted line is drawn. The factor factor determines
@DASH DOUBLE DOTTED
the length of the displayed line segment and one-third the length of
the non-displayed segments.
@DASH TRIPLE DOTTED A dash triple-dotted line is drawn. The factor factor determines the
length of the displayed line segment and on-fourth the length of the
non-displayed segments.

Table B.1: Line styles

The factor factor is given as floating point value. Its unit is one pixel for screen display and a dot
(1pt=1/72in) for the printout.
The standard value for factor is 4.0 and for pattern @DEFAULT.

### B.6.6 FillStyle

Using the call
t.set2DObjAttr(obj id, style)
@FILL STYLE,
sets the fill pattern for polygons. In this case, style is a symbol that can accept the values listed
in table B.2.
Thehorizontaldistancebetweendiagonalorverticallinesinthefillpatternortheverticaldistance
betweenhorizontallinesshouldmeasureeightpixelsforthescreendisplayandeightpoints(1pt=
1/72in) for the printout.
By default, a polygon is shown completely filled.

175

| Sample | Description |
| --- | --- |
| @DEFAULT | The preset line style is used. |
| @SOLID | A continuous line is drawn. |
| @DASHED | A dashed line is drawn. The factor factor determines the length of
the line segments displayed and not displayed. |
| @DOTTED | A dotted line is drawn. The factor factor determines the distance
between the centers of two neighboring points. |
| @DASH DOTTED | Adot-dashlineisdrawn. Thefactor factordeterminesthelengthof
the displayed line segment and half the length of the non-displayed
line segments. |
| @DASH DOUBLE DOTTED | A dash double-dotted line is drawn. The factor factor determines
the length of the displayed line segment and one-third the length of
the non-displayed segments. |
| @DASH TRIPLE DOTTED | A dash triple-dotted line is drawn. The factor factor determines the
length of the displayed line segment and on-fourth the length of the
non-displayed segments. |

<!-- Page 178 -->

Fill pattern Description
@LEFT 30 diagonal lines from top left to bottom right at an angle of 30 degrees
to the horizontal
@RIGHT 30 diagonal lines from bottom left to top right at an angle of 30 degrees
to the horizontal
@CROSS 30 crossingdiagonallinesfromtoplefttobottomrightandfrombottom
left to top right, both at an angle of 30 degrees to the horizontal
diagonal lines from top left to bottom right at an angle of 45 degrees
@LEFT 45
to the horizontal
@RIGHT 45 diagonal lines from bottom left to top right at an angle of 45 degrees
to the horizontal
@CROSS 45 crossingdiagonallinesfromtoplefttobottomrightandfrombottom
left to top right, both at an angle of 45 degrees to the horizontal
@H LINES horizontal lines
@V LINES vertical lines
@CROSS crossing horizontal and vertical lines

Table B.2: Fill pattern

### B.6.7 PolygonMode

Using the call
t.set2DObjAttr(obj id, mode)
@POLYGON MODE,
and the mode parameter specifies for polygons whether the corner points (mode = @POINT), the
boundary lines (mode = @LINE) or the area (mode = @FILL) should be displayed. The attributes
used dependent on PolygonMode are listed in table B.3.

PolygonMode attributes used
@POINT Color, PointSize, PointSmooth
@LINE Color, LineWidth, LineStyle
Color, FillStyle
@FILL
Table B.3: Attributes used dependent on PolygonMode

The standard value for PolygonMode is @FILL.

### B.6.8 Text

Using the call
t.set2DObjAttr( obj id , @TEXT, text )
sets the text text to be displayed for an object of the G2DText type. The text argument must be
a character string whose characters are from the ASCII character set.

176

| Fill pattern | Description |
| --- | --- |
| @LEFT 30 | diagonal lines from top left to bottom right at an angle of 30 degrees
to the horizontal |
| @RIGHT 30 | diagonal lines from bottom left to top right at an angle of 30 degrees
to the horizontal |
| @CROSS 30 | crossingdiagonallinesfromtoplefttobottomrightandfrombottom
left to top right, both at an angle of 30 degrees to the horizontal |
| @LEFT 45 | diagonal lines from top left to bottom right at an angle of 45 degrees
to the horizontal |
| @RIGHT 45 | diagonal lines from bottom left to top right at an angle of 45 degrees
to the horizontal |
| @CROSS 45 | crossingdiagonallinesfromtoplefttobottomrightandfrombottom
left to top right, both at an angle of 45 degrees to the horizontal |
| @H LINES | horizontal lines |
| @V LINES | vertical lines |
| @CROSS | crossing horizontal and vertical lines |

| PolygonMode | attributes used |
| --- | --- |
| @POINT | Color, PointSize, PointSmooth |
| @LINE | Color, LineWidth, LineStyle |
| @FILL | Color, FillStyle |

<!-- Page 179 -->

### B.6.9 Position

Using the call
t.set2DObjAttr( obj id , @POSITION, [ x , y ])
sets the position (the reference point) for an object of the G2DText type.

### B.6.10 Height

Using the call
t.set2DObjAttr( obj id , @HEIGHT, height )
sets the height of a capital letter without descender for an object of the G2DText type.
The standard value for the text height is 0.1.

### B.6.11 AspectRatio

Using the call
t.set2DObjAttr(obj id, @ASPECT RATIO, ratio)
determines the extension or compression in x direction for an object of the G2DText type. The
floating point value of ratio must be greater than 0.0. With the default value of 1.0, the text
appears within normal proportions that are predefined by the font used. With values greater
than 1.0, it is extended in the x direction, with values smaller than 1.0 and greater than 0.0 it is
compressed in the x direction.

### B.6.12 Alignment

Using the call
t.set2DObjAttr(obj id, @ALIGNMENT, align)
determines the alignment of the text relative to the reference point for an object of the G2DText
type.
If width is the width of the text, the move ∆x of the left side of the first letter on the base line
relative to the reference point is determined as follows:
∆x=−(alignment+1.0)×(width/2.0)
The standard value for align is −1.0, which left-aligns the text.

177

<!-- Page 180 -->

### B.6.13 Pickable

Using the call
t.set2DObjAttr( obj id , @PICKABLE, pickable )
can specify for each object whether it should be considered in 2D mode in determining the object
that is to be selected with the mouse. If the integer argument pickable is zero, the corresponding
2D object is not considered; if it is not zero, it is considered.
If the pickable flag of an object of the G2DCompound type is not set, none of the child objects is
taken into account. If it is set, then the pickable flag of the respective child object is decisive.
The standard value for pickable is 1.

### B.6.14 Snapable

Using the call
t.set2DObjAttr( obj id , @SNAPABLE, snapable )
candetermineforeachobjectwhetheritshouldbetakenintoaccountindeterminingatrappoint.
If the integer argument snapable is zero, the corresponding 2D object is not taken into account. If
it is not zero, it is taken into account.
If the snapable flag of an object of the G2DCompound type is not set, none of the child objects is
taken into account. If it is set, then the snapable flag of the respective child object is decisive.
The standard value for snapable is 1.

### B.6.15 Exportable

Using the call
t.set2DObjAttr(obj id, @EXPORTABLE, exportable)
can determine for each object whether it should be exported during the export to a 2D vector
2
format . If the integer argument exportable is zero, the corresponding 2D object is not exported.
If it is not zero, it is exported.
If the exportable flag of an object of the G2DCompound type is not set, none of the child objects is
exported. If it is set, then the exportable flag of the respective child object is decisive.
The standard value for exportable is 1.
2
Since the print command also uses the export to a 2D vector format, the exportable flag also influences the
objectsappearingduringprintout.

178

<!-- Page 181 -->

### B.6.16 Layer

Using the call
t.set2DObjAttr( obj id , @LAYER, layer )
can determine the layer for each object which is used to control its visibility. Here, the layer
argument is a symbol that should solely consist of letters, numbers and underscore sign.
If the layer was set for an object of the type, this layer is used for all direct and
G2DCompound
indirect child objects for which a layer was not explicitly set.

179

<!-- Page 182 -->

# Appendix C

# The 2D vector file format

# C.1 Introduction

The EasternGraphics Metafile (EGM) is an expandable file format for saving graphic and non-
graphic data. Due to its expandability it allows the integration of data in other file formats.
The EGM format is structured in such a way that an EGM parser doesn’t have to be able to
interpret all EGM elements to read until the end of the file. It should be able to generally ignore
unknown elements.
TheEGMformatsupportshierarchicalsavingofdata. Thismakesitpossible,forexample,tosave
graphic 2D symbols on the top level as well as 2D symbols embedded in a scene element within
an EGM. The first case is used when EGM describes only a single 2D symbol for use in the GF.
The second case may become interesting when a whole scene is described in EGM format which,
among other things, also contains user-defined 2D symbols.
EGM is specified in binary as well as text format. Binary format helps to save data efficiently
while text format may be used primarily during the developmental phase.

# C.2 data types

This section describes the data types used in EGM, in particular their representation in EGM
binary and text format.
Both formats – binary and text – are defined to be platform-independent making easy data ex-
change between different computer platforms possible.
All numeric values are saved in binary format so that the byte with the highest value comes first,
followedbyallotherbytesindescendingvalueorder. Thisisalsoknownas”NetworkByteOrder”
or ”Big-Endian.”
The text format character set must be an aggregate of the ASCII character set. This is the case
formost,ifnotall,ISO–8859–xcharactersets. Toenableeasyconversionbetweentextformatand
binary format, the same limitation also applies to the binary format String data type.

180

<!-- Page 183 -->

### C.2.1 Simple Data Types

Byte

A Byte is an integer 8 bit value that can be interpreted either as an unsigned value in the 0 to
2 8 −1 ([0,255]) range or as a two’s complement signed value in the −2 7 to 2 7 −1 ([−128,127])
range. Type Byte values are saved in EGM binary format as a single byte, as shown in figure C.1,
with I being the highest value bit and I the lowest value bit.
7 0

Byte 1 I I
7 0

Figure C.1: Type Byte values

Intextformat,aByte isdisplayedasadecimal,octal,orhexadecimalnumber,whichcanoptionally
be preceded by a minus sign. An octal number is designated by a leading and a hexadecimal
0
number by a leading or , with only digits ranging from to being permitted for octal
0x 0X 0 7
numbers and digits ranging from to , to , and to being permitted for hexadecimal
0 9 A F a f
numbers.
In this EGM specification, the UINT8 identifier is used as a type specification for unsigned Byte
values; for signed Byte values, the INT8 identifier is used.

Word

AWord isaninteger16bitvaluethatiseitherinterpretedasanunsignedvalueinthe0to2 16 −1
([0,65535]) range or as a two’s complement signed value in the −2 15 to 2 15 −1 ([−32768,32767])
range. Type Word values are saved in EGM binary format as two successive bytes as shown in
figure C.2, with I being the highest value bit and I the lowest value bit.
15 0

Byte 1 I I
15 8
Byte 2 I I
7 0

Figure C.2: Type Word values

Intextformat,aWord isdisplayedasadecimal,octalorhexadecimalnumber,whichcanoptionally
be preceded by a minus sign. An octal number is designated by a leading and a hexadecimal
0
number by a leading or 0X, with only digits ranging from to being permitted for octal
0x 0 7
numbers and digits ranging from to , to , and to being permitted for hexadecimal
0 9 A F a f
numbers.
In this EGM specification, the UINT16 identifier is used as a type specification for unsigned Word
values and the INT16 identifier is used for signed Word values.

181

| I I
15 8 |
| --- |
| I I
7 0 |

<!-- Page 184 -->

Double Word

A Double Word is an integer 32 bit value that is interpreted as an unsigned value in the 0 to
32 31 31
2 − 1 ([0,4294967295]) range or as a two’s complement signed value in the −2 to 2 − 1
([−2147483648,2147483647])range. TypeDouble Word valuesaresavedinEGMbinaryformatas
four successive bytes as shown in figure C.3, with I being the highest value bit and I the lowest
31 0
value bit.

Byte 1 I I
31 24
Byte 2 I I
23 16
Byte 3 I I
15 8
Byte 4 I I
7 0

Figure C.3: Type Double Word values

In text format, a Double Word is displayed as a decimal, octal or hexadecimal number that
is optionally preceded by a minus sign. An octal number is designated by a leading 0 and a
hexadecimalnumberbyaleading0xor0X,withonlydigitsrangingfrom0to7beingarepermitted
foroctalnumbersanddigitsrangingfrom0to9,AtoF,andatofbeingpermittedforhexadecimal
numbers.
InthisEGMspecification,theUINT32identifierisusedasatypespecificationforunsignedDouble
Word values and the INT32 identifier is used for signed Double Word values.

Single Precision Floating Point

Type Single Precision Floating Point values are displayed according to the IEEE 754 standard.
−38 38
The absolute value lies in the range between 1.17549435×10 and 3.40282347×10 with a
minimumof6significantdecimalsinthemantissa. InEGMbinaryformat,singleprecisionfloating
point values are saved as four successive bytes as displayed in figure C.4.

Byte 1 S E E
7 1
Byte 2 E F F
0 1 7
Byte 3 F F
8 15
Byte 4 F F
16 23

Figure C.4: Single precision floating point number

The value is 0.0, if the exponent and the mantissa are 0. Otherwise it is calculated according to
(−1) s ×1.f ×2 e−127 . S is the sign bit, f is the mantissa (F ...F with F being the highest
1 23 1
value bit) and e is the exponent (E ...E with E being the highest value bit).
7 0 7
In text format, a single precision floating point number consists of an optional leading minus or
plus sign, an integer decimal quantity, a decimal point, a fractional quantity, and an optional

182

| I I
31 24 |
| --- |
| I I
23 16 |
| I I
15 8 |
| I I
7 0 |

| S | E E
7 1 |
| --- | --- |
| E
0 | F F
1 7 |
| F F
8 15 |  |
| F F
16 23 |  |

<!-- Page 185 -->

exponent. The exponent consists of one of the numbers or , followed by an optional minus
e E
or plus sign which in turn is followed by an integer decimal . The integer or fractional quantity
can be dropped, but both cannot. The decimal point can be dropped, if the fractional quantity is
dropped with an exponent present.
InthisEGMspecification,theFLOAT32identifierisusedasatypespecificationforsingleprecision
floating point values.

Double Precision Floating Point

Type Double Precision Floating Point values are displayed according to the IEEE 754 standard.
−308
Theabsolutevalueliesintherangebetween2.2250738585072014×10 and1.7976931348623157×
308
10 with a minimum of 15 significant decimals in the mantissa. In EGM binary format, double
precision floating point values are saved as eight successive bytes as displayed in figure C.5.

Byte 1 S E E Byte 5 F F
10 4 21 28
Byte 2 E E F F Byte 6 F F
3 0 1 4 29 36
Byte 3 F F Byte 7 F F
5 12 37 44
Byte 4 F F Byte 8 F F
13 20 45 52

Figure C.5: double precision floating point

The value is 0.0, if the exponent and the mantissa are 0. Otherwise it is calculated according to
s e−1023
(−1) ×1.f ×2 . S is the sign bit, f is the mantissa (F ...F with F being the highest
1 52 1
value bit) and e is the exponent (E ...E with E being the highest value bit).
10 0 10
The display of a double precision floating point number in text format corresponds to the display
of a single precision floating point number as described above.
In this EGM specification, the FLOAT64 identifier is used as a type specification for double pre-
cision floating point values.

Symbol

AsymbolisaseriesofcharactersandissavedinEGMbinaryformat, asshowninfigureC.6. The
length (U ...U with U being the highest value bit) that is saved in the first two bytes as an
15 0 15
unsigned value neither includes itself nor the NUL character terminating the symbol.
In text format, a symbol consists of a series of ASCII letters, digits and underscores; the first
character must not be a digit. This symbol is case sensitive.
In this EGM specification, the SYMBOL identifier is used as a type specification for symbols.

String

A string is saved in EGM binary format, as shown in figure C.7. The length (U ...U with U
15 0 15
beingthehighestvaluebit)thatissavedinthefirsttwobytesasanunsignedvalueneitherincludes
itself or the NUL character terminating the string.

183

| S | E E
10 4 |  |
| --- | --- | --- |
| E E
3 0 |  | F F
1 4 |
| F F
5 12 |  |  |
| F F
13 20 |  |  |

| F F
21 28 |
| --- |
| F F
29 36 |
| F F
37 44 |
| F F
45 52 |

<!-- Page 186 -->

Byte 1 U U
15 8
Byte 2 U U
7 0
Byte 3 C C
7 0

Byte 3+n 0 0 0 0 0 0 0 0

Figure C.6: Symbol

Byte 1 U U
15 8
Byte 2 U U
7 0
Byte 3 C C
7 0

Byte 3+n 0 0 0 0 0 0 0 0

Figure C.7: Character string

In EGM text format, character strings are displayed as a result of any number of characters
(includingnone)thataresurroundedbyquotationmarks. Non-printablecharactersarerepresented
by escape sequences that can be used in the applications listed in table C.1. Please note that the
octal coding represented in parentheses can vary between platforms. For example, in MacOS (R)
the coding of \n is \r exchanged.

\a Klingelzeichen (\7) \\ backward slash (\)
\b backspace (\8) \? question mark (?)
\f form feed (\14) \’ apostrophe (’)
\n line separator (\12) \" quotation marks (")
\r carriage return (\15) \ooo octal number
\t tab character (\9) \xhh hexadecimal number
\v vertical tabulation character (\13)

Table C.1: escape sequences for character strings

Intheescapesequence\oooooostandsforaseriesconsistingofonetothreeoctaldigits(0...7)and
in \x hh hh stands for a series consisting of one or more hexadecimal digit (0...9,A...F,a...f).
Youshouldpreferablyusetheformat \ ooo withthreeoctaldigits, sinceonlythenacorrectcoding
of the character can be ensured without any consideration for the subsequent character.
In this EGM specification, the STRING identifier is used as a type specification for character
strings.

184

| U U
15 8 |
| --- |
| U U
7 0 |
| C C
7 0 |

| U U
15 8 |
| --- |
| U U
7 0 |
| C C
7 0 |

<!-- Page 187 -->

### C.2.2 Structured data types

Structured data types consist of a series of simple data types. Each structured data type is
described using a combination consisting of type class and object type. The type class is used for
classifying object types; the object types are used for defining the structure and the meaning of
structureddatatypes. Forexample,atypeclasscancombineallobjecttypesdefinedfordescribing
graphic 2D primitives, with each object type describing the structure of the respective 2D object
within the EGM format.
Inthebinaryformat,everystructureddatatypeconsistsofthestructureheaderandthestructure
body. The structure header is eight bytes long and contains information regarding the type of
structure and its length. The structure body contains the actual data. Within the structure body,
everypieceofdataisorientedtoamultipleofitsownsizerelativetothestructurebeginning,with
the exception of strings that are oriented to a multiple of two.

Byte 1 R R Byte 5 F F
7 0 7 0
Byte 2 C C Byte 6 L L
7 0 23 16
Byte 3 B E S T T Byte 7 L L
12 8 15 8
Byte 4 T T Byte 8 L L
7 0 7 0

Figure C.8: Structure header

Figure C.8 shows the organization of the structure header.
Bits R ...R are reserved for future use and should be set to 0.
7 0
BitsC ...C containthetypeclass,bitsT ...T containtheobjecttype. Theobjecttypesmust
7 0 12 0
be unique within the type class.
The B– and E–bits are used to label the beginning and end of a compound object as described in
section C.2.3.
The S bit indicates whether single precision floating point parameters (S–Bit is set) or double
1
precision floating point parameters (S–Bit is reset) are present . Not every object type that has
floating point parameters must support single and double precision.
Bits F ...F do not have a predefined meaning and, depending on object type, can be used for
7 0
flag bits.
Finally, bits L ...L contain the entire length of the structure.
23 0
The structural header itself is always oriented to a multiple of eight relative to the beginning
of the file and the entire length of the structure also is a multiple of eight. This requires the
end of the structure to be filled with null bytes, if necessary. This ensures that the EGM can
be mapped directly to memory and that no orientation problems arise when individual data are
directly accessed, which could cause a bus error.
1 FortypeattributesthatuseeitherFLOAT32orFLOAT64dependingonS bit,onlyFLOATiswritten.

185

| R R
7 0 |  |  |  |
| --- | --- | --- | --- |
| C C
7 0 |  |  |  |
| B | E | S | T T
12 8 |
| T T
7 0 |  |  |  |

| F F
7 0 |
| --- |
| L L
23 16 |
| L L
15 8 |
| L L
7 0 |

<!-- Page 188 -->

In text format, every structured data type consists of one or more lines, with all but the last line
having to have a backward slash ( ) directly before the line end character(s). These lines are
\
combined into a data record. The backward slashes and the subsequent line end are removed.
Every single line cannot have more than 2047 characters, including the line end character. The
number of characters per line without the line end character should not exceed 2045, since two
characters are used for designating the end of a line on some platforms. Theoretically, the length
of the entire data record is unlimited.
Lines are ended using either \x0A , \x0D , or \x0D\x0A .
The individual single datawithin adata recordare delimited byone ormoreseparators, using the
blank space ( \40 ) and the tab character ( \t ) as separator.
Atthebeginningofthedatarecord,therearetypeclassandobjecttype,delimitedbyoneorseveral
separators and followed by flags F to F indicated as unsigned decimal, octal, or hexadecimal
0 7
number in the range between 0 and 255, with F being the highest value bit. Type class as well as
7
objecttypemaybeindicatedasidentifierthatiscasesensitiveorasdecimal,octal,orhexadecimal
numbers. Thestructuralremainderofthedatarecordisdefinedbytheobjecttypewhoseidentifier
and coding only must be unique within the type class.
An octal number is marked by a leading and a hexadecimal number by a leading or 0X, with
0 0x
only digits ranging from to being permitted for octal numbers and digits ranging form to 9,
0 7 0
to F, and to being permitted for hexadecimal numbers.
A a f

### C.2.3 Compound types

Compound types consist of a series of structured data types that are enclosed by a Begin and a
End object of the same structured data type. These Begin and End objects must always occur in
pairs.
InEGMbinaryformat,theBegin objectismarkedbyasetB bitinthestructureheader; theEnd
object is marked by a set E bit.
In EGM text format, the data record of the Begin object starts with the begin identifier, which
is followed by the type class, delimited by one or several separators. The data record of the End
object starts analogically with the end identifier, followed by one or several separators and the
type class. Instead of begin, there can also be a single plus sign (+), and instead of end, there can
be a single minus sign (-).

# C.3 File header

The EGM binary format starts with the following structure:
major is the main version number and minor is the sub version number. The version described
in this document of EGM is 1.0 (major =1;minor =0).

InEGMtextformat,thefirstlinecontainsthe EGM and version identifiers,with EGM beingdirectly
atthebeginningofthelineand version beingdelimitedfrom EGM byablankspace. Thisisfollowed

186

<!-- Page 189 -->

31 24 16 8 0
0x45 0x47 0x4D 0x00
major minor

Figure C.9: binary EGM header

bythemainversionnumberandthesubversionnumber,delimitedbythe”usual”separators. The
first EGM line in version 1.0 is as follows:
EGM version 1 0

# C.4 General structured data types

Thissectiondescribesgeneralstructureddatatypesthathavenorelationtoconcretetypeclasses.
These types have the type class 1 with the common identifier.

### C.4.1 Comment

Type class: 1 / common
Object type: 1 / comment
Parameter: Offset Type Parameter
8 STRING comment
roundup(11+len,8) End of structure
Comments are ignored during reading.
In a special case, comments can consist of a data record in the text format that starts with a
pound sign (#) followed directly by the actual comment and delimited from the pound sign by one
or more separators, if necessary.

### C.4.2 EGM type

Type class: 1 / common
Object type: 2 / egm_type
Parameter: Offset Type Parameter
8 STRING egmtype
roundup(11+len,8) End of structure
The file header described in section C.3 can be followed directly by a type EGMType object. The
egmtype character string describes the EGM type. Currently, the types listed in table C.2 have
been defined.

187

| 0x45 | 0x47 | 0x4D | 0x00 |
| --- | --- | --- | --- |
| major |  | minor |  |

<!-- Page 190 -->

Identifier Description
x2DSYMBOL TheEGMdescribesa2Dsymbol. Itshouldonlycontainobjectsoftypeclasses
common and gr2dobj . Objects of a different type class are ignored while they
are being read .
Type x2DSYMBOL EGMfilescontainexactlyone2Dobject. Ifthisobjectismade
up of several primitive 2D objects, they must be encapsulated by a Compound
object.

Table C.2: EGM types

# C.5 Graphic 2D objects

The graphic 2D objects are combined into one type class carrying the number 2 and the gr2dobj
identifier .
The 2D objects are described using a x/y-coordinate system, with the x-axis pointing to the right
andthey-axispointingup. Angleinformationisgivenbyradianmeasure,theyaremathematically
positive (counterclockwise) and are relative to the positive x-axis, if not otherwise specified.
All coordinates are given as single or double precision floating point values. The precision used is
specified in each individual 2D object by the S bit of the structure header.

### C.5.1 Compound

Graphic2DobjectsarenestedbytheCompound compoundtype. Thenestingcanalsobeapplied
recursively.
A Compound does not possess a geometric representation. Ordinarily, it includes at least one
object of type class gr2dobj. Other included objects are not permitted.
As an option, the Compound object can contain a geometric transformation that is to be applied
totheenclosedobjects. Thetransformationisspecifiedeitherasarotationoftheenclosedobjects
withsubsequenttranslationorasa3×3transformationmatrixplusoptionalinversetransformation
matrix.

188

| Identifier | Description |
| --- | --- |
| x2DSYMBOL | TheEGMdescribesa2Dsymbol. Itshouldonlycontainobjectsoftypeclasses
common and gr2dobj. Objects of a different type class are ignored while they
are being read .
Typex2DSYMBOLEGMfilescontainexactlyone2Dobject. Ifthisobjectismade
up of several primitive 2D objects, they must be encapsulated by a Compound
object. |

<!-- Page 191 -->

Type class: 2 / gr2dobj
Object type: 1 / compound
Flags: F F =00: no transformation
1 0
F F =01: Rotation and translation
1 0
F F =10: Transformation matrix
1 0
F F =11: Transformation matrix and inverse transformation matrix
1 0
Parameter: Offset (S =1) Offset (S =0) Type Parameter
with F F =01:
1 0
8 8 FLOAT α
12 16 FLOAT x ,y
offs offs
24 32 End of structure
with F F =10:
1 0
8 8 FLOAT mat
2×3
32 56 End of structure
with F F =11:
1 0
8 8 FLOAT mat
2×3
32 56 FLOAT mat −1
2×3
56 104 End of structure
Ifthetransformationisenteredusingrotationandtranslation,thecoordinatesoftheencapsulated
in the coordinate system of the Compound object are calculated as follows:
(cid:48)
x =xcosα−ysinα+x
offs
(cid:48)
y =xsinα+ycosα+y
offs
If the transformation is entered using the transformation matrix, the coordinates of the encapsu-
lated objects in the coordinate system of the Compound object are calculated as follows:
x (cid:48) =m x+m y+m
11 12 13
(cid:48)
y =m x+m y+m
21 22 23
ThetransformationmatricesaswellastheirinversearesavedinEGMformatlinebyline,beginning
with the element in the left upper corner (m ). The third line is not saved, since it always reads
11
0.0,0.0,1.0.
TheinversematrixmaybeincludedintheEGMformatinordertoeliminatetheneedtodetermine
it while reading the EGM .

### C.5.2 Graphic primitives

This section describes all the 2D objects with a graphic representation.
Theobjectdefinitionscontainonlythegeometricinformation,suchaspointcoordinatesandangles.
Attributes, such as color, are saved in a Attribut–Set and are set using special attribute objects
within it. The graphic primitives use the attributes that are relevant to them at the time of their
occurrence in the attribute set. For each individual graphic primitive, these attributes are listed
under ”Attributes:”

189

| 8
16 | FLOAT
FLOAT |
| --- | --- |
| 32 |  |

| 8 | FLOAT |
| --- | --- |
| 56 |  |

| 8
56 | FLOAT
FLOAT |
| --- | --- |

<!-- Page 192 -->

Lines

Type class: 2 / gr2dobj
Object type: 256 / lines
Attributes: Color, LineWidth, LineStyle
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 UINT32 n
12 16 FLOAT x1 ,y1 ,x2 ,y2
0 0 0 0
12+(n−1)×16 16+(n−1)×32 FLOAT x1 ,y1 ,
n−1 n−1
x2 ,y2
n−1 n−1
16+n×16 16+n×32 End of structure
TypeLines objectsrepresentoneorseveralseparatedlinesegments. Thenparameterspecifiesthe
number of line segments. Its value must be greater than or equal to 1. Every single line segment
starts at x1 ,y1 and ends at x2 ,y2 .
i i i i

Polyline

Type class: 2 / gr2dobj
Object type: 257 /
polyline
Attributes: Color, LineWidth, LineStyle
Flags: F =0: open
0
F =1: closed
0
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 UINT32 n
12 16 FLOAT x ,y
0 0
12+(n−1)×8 16+(n−1)×16 FLOAT x ,y
n−1 n−1
16+n×8 16+n×16 End of structure
Depending on flag F , type Polyline objects represent an open or closed line. The n parameter is
0
bigger than the number of line segments by 1. It must be greater than or equal to 2. If flag F is
0
set, the last point (x ,y ) is connected to the first point (x ,y ).
n−1 n−1 0 0

Points

Type class: 2 / gr2dobj
Object type: 258 /
points
Attributes: Color, PointSize, PointType
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 UINT32 n
12 16 FLOAT x ,y
0 0
12+(n−1)×8 16+(n−1)×16 FLOAT x ,y
n−1 n−1
16+n×8 16+n×16 End of structure

190

| 8
16
16+(n−1)×32 | UINT32
FLOAT
FLOAT |
| --- | --- |

| 8
16
16+(n−1)×16 | UINT32
FLOAT
FLOAT |
| --- | --- |

| 8
16
16+(n−1)×16 | UINT32
FLOAT
FLOAT |
| --- | --- |

<!-- Page 193 -->

Type Points objects represent one or several points. The parameter n specifies the number of
points. Its value must be greater than or equal to 1.

Circle

Type class: 2 / gr2dobj
Object type: 259 / circle
Attributes: Color, LineWidth, LineStyle
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 FLOAT x ,y
center center
16 24 FLOAT r
24 32 End of structure
Circletypeobjectsrepresentacirclewitharadiusofr,whosecenterisdeterminedbyx ,y .
center center
The radius r must be greater than 0.0.

Arc
Type class: 2 / gr2dobj
Object type: 260 / arc
Attributes: Color, LineWidth, LineStyle
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 FLOAT x ,y
center center
16 24 FLOAT r
20 32 FLOAT α ,α
start end
24 48 End of structure
Arc typeobjectsrepresentanarcwitharadiusofr,whosecenterisdeterminedbyx ,y .
center center
The arc is drawn from angle α to angle α in mathematically positive direction.
start end

Ellipsis

Type class: 2 / gr2dobj
Object type: 261 / ellipse
Attributes: Color, LineWidth, LineStyle
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 FLOAT x ,y
center center
16 24 FLOAT x ,y
radius radius
24 40 FLOAT α
32 48 End of structure
TypeEllipse objectsrepresentanellipsiswhosecenterisdeterminedbyx ,y . Theradius
center center
of the not rotated ellipsis in the direction of the x-axis is x , the radius in the direction of the
radius
y-axis is y . The rotation angle of the ellipsis around its center is α.
radius

191

| 8
24 | FLOAT
FLOAT |
| --- | --- |

| 8
24
32 | FLOAT
FLOAT
FLOAT |
| --- | --- |

| 8
24
40 | FLOAT
FLOAT
FLOAT |
| --- | --- |

<!-- Page 194 -->

Text

Type class: 2 /
gr2dobj
Object type: 262 / text
Attributes: Color, Font, FontHeight, FontAspectRatio, FontAlignment
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 FLOAT x ,y
origin origin
16 24 FLOAT α
20 32 FLOAT width
20 32 STRING text
roundup(23+len,8) roundup(35+len,8) End of structure
TypeText objectsrepresentthetexttextwhosebaselinegoesthroughthereferencepointx ,y
origin origin
and around which the reference point is rotated by the angle α. The width parameter indicates
the width of the text that was not rotated. The position of the left side of the first letter on the
baseline is determined as described in section C.5.3.
AsystemthatusesthesamefontsasEGRGFcanignorethewidthparameterwhenreading,since
the width of the text is determined by the FontAspectRatio attribute. Other systems must ignore
the FontAspectRatio attribute and must instead modify the text to match the width specified in
the width parameter.

Convex Polygon

Type class: 2 / gr2dobj
Object type: 263 / cvx_polygon
Attributes: Color, FillStyle
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 UINT32 n
12 16 FLOAT x ,y
0 0
12+(n−1)×8 16+(n−1)×16 FLOAT x ,y
n−1 n−1
16+n×8 16+n×16 End of structure
TypeConvex Polygon objectsrepresentaconvexpolygon. Inaconvexpolygon, noedgesintersect
and all interior angles are smaller than or equal to π.
The n parameter containing the number of corner points of the polygon must be greater than 2.

### C.5.3 Attributes

As described in section C.5.2, the graphic 2D primitives contain no attributes, but only pure
geometry information. They use the attributes relevant to them that are specified in the current
attribute set at the time of their occurrence in the EGM format.
Since the EGM permits the hierarchical structuring of data in tree form, it must also support a
hierarchy of attribute sets. This hierarchy is built in tree form when the EGM is read, with all

192

| 8
24
32
32 | FLOAT
FLOAT
FLOAT
STRING |
| --- | --- |

| 8
16
16+(n−1)×16 | UINT32
FLOAT
FLOAT |
| --- | --- |

<!-- Page 195 -->

nodes of the tree that are located on the path from the root to the current leaf existing. This is
implemented by a stack of Attribute sets.
To keep the stack of the attribute sets consistent with the EGM hierarchy, every compound type
End object removes the necessary number of attribute sets from the stack, until the number of
attribute sets on the stack is the same as the number that the corresponding Begin object found
on the stack. Similarly, an error occurs when an attribute set is removed from the stack, so that
the number of attribute sets on the stack becomes smaller than the number of the attribute sets
that the most interior compound type Begin object found on the stack.

Attribute values

The coordinate values given with the graphic 2D primitives generally (i.e. if there was no scaling)
canbeinterpretedasmeters. Thedimensionsofthedisplayonscreen,ontheprinterortheplotter
depend on the scale used.
Comparedwiththis,manyattributevaluesforthegraphic2Dobjectaregivenindependentlyfrom
the scale, since on the one hand this complies with the capabilities of common output devices and
on the other hand scaling is oftentimes not desired. The basic unit in this case is the point. The
following interrelations are valid for the size of one point:
1pt=0.03527cm 1pt=0.3527mm 1pt=0.0138in
1cm=28.346457pt 1mm=2.8346457pt 1in=72pt
This definition of a point is compatible with the definition of a PostScript point, but somewhat
differs from the definition used during letterpress printing. This definition stated 1in = 72.27pt
and 1in=72bp, where bp stands for Big Point.
Whenoutputtingthepointonaprinterorplotter,thesizeofthepointshouldbeobservedexactly.
When outputting on the screen it is acceptable to display a point as a pixel using the customary
resolution of 75 to 100 dpi.

Push Attrib

Type class: 2 / gr2dobj
Object type: 512 / push_attr
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 End of structure
When an PushAttrib object is being read, the current status of the attribute set is put on the
attribute stack.

Pop Attrib

Type class: 2 / gr2dobj
Object type: 513 / pop_attr
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 End of structure

193

<!-- Page 196 -->

When a PopAttrib object is being read, the top attribute set is copied into the current attribute
set and is removed from the stack. An error occurs when the number of the attribute sets on the
stack is subsequently smaller than when the most interior compound type Begin object was read.

Init Attrib

Type class: 2 / gr2dobj
Object type: 514 / init_attr
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 End of structure
When a InitAttrib object is read, the current attribute set is reset to the default values. The
default values are specified with the individual attributes.

Color

Type class: 2 / gr2dobj
Object type: 515 /
color
Default: r/g/b=0/0/0
Parameter: Offset Type Parameter
8 UINT16 red
10 UINT16 green
12 UINT16 blue
16 End of structure
The specification of numbers is accomplished in the RGB system. Here, an unsigned integer value
rangingfrom0to65535isspecifiedforeachcolorcomponent. 0Correspondstominimumintensity
and 65535 corresponds to maximum intensity.

Line Width

Type class: 2 / gr2dobj
Object type: 516 / line_width
Default: 1.0
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 FLOAT linewidth
16 16 End of structure
TypeLineWidth objectssetthelinewidthattributeinthecurrentattributeset. Thelinewidthis
specified in points (pt). The value must be greater than 0.0. Invalid values are interpreted as 1.0.

194

| 8 | FLOAT |
| --- | --- |

<!-- Page 197 -->

Line Style

Type class: 2 /
gr2dobj
Object type: 517 / line_style
Default: -1
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 UINT32 linestyle
12 16 FLOAT factor
16 24 End of structure
Type LineStyle objects set the line type in the current attribute set.
The following values are predefined for the linestyle parameter:

Constant line type
−1 default value
0 solid line
1 dashed line
2 dotted line
3 dash–point line
4 dash–point–point line
5 dash–point–point–point line

Table C.3: Predefined line types

If the LineStyle is −1, the LineStyle set by the parent object will apply.
The parameter is specified in points (pt) and determines how the line is stretched. Depending on
the line type, the parameter affects the display of the line as follows:

Line type meaning of factor factor
dashed length of the displayed and hidden segments
dotted distance between the center points of two neighboring points
dash–point length of the displayed line segment and half length of the hidden
line segments
dash–2–point length of the line segment and a third of the hidden line segments
dash–3–point length of the line segment and a fourth of the hidden line segments

Table C.4: Effects of the factor on the line type

195

| 8
16 | UINT32
FLOAT |
| --- | --- |

| Constant | line type |
| --- | --- |
| −1
0
1
2
3
4
5 | default value
solid line
dashed line
dotted line
dash–point line
dash–point–point line
dash–point–point–point line |

| Line type | meaning of factor factor |
| --- | --- |
| dashed | length of the displayed and hidden segments |
| dotted | distance between the center points of two neighboring points |
| dash–point | length of the displayed line segment and half length of the hidden
line segments |
| dash–2–point | length of the line segment and a third of the hidden line segments |
| dash–3–point | length of the line segment and a fourth of the hidden line segments |

<!-- Page 198 -->

Point Size

Type class: 2 / gr2dobj
Object type: 518 / point_size
Default : 0.1
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 FLOAT pointsize
16 16 End of structure
In the current attribute set, type PointSize objects set the size of a point. The point size is used
only if the set point type is a vector point. In this case, the vertices of the point are calculated as
described in table C.6, with the d variable being the point size set using PointSize.

Point Type

Type class: 2 /
gr2dobj
Object type: 522 / point_style
Default: 0xffffffff
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 UINT32 pointstyle
16 16 End of structure
Pointscanbedifferentiatedintobitmappointsandvectorpoints. Theorientationofbitmappoints
is always the same and they are always the same size irrespective of the scaling and the set point
size. The size and orientation of vector points is determined by the set point size as well as the
transformation of a parent compound object, if necessary.
The specification of points is done using a bit mask so that different bitmap points as well as
different vector points can be combined with each other 2 . Vector points may be combined in any
way; the combination of bitmap points is limited to point types of different classes.
Tables C.5 and C.6 contain the constants for the specification of bitmap and vector points. Table
C.6 contains the provision for calculating the vertices of the points, with the d variable being the
point size set using PointSize.

Font

Currently, different fonts are not supported.
2 i.e.,thatbitmapandvectorpointscannotbecombined.

196

| 8 | FLOAT |
| --- | --- |

| 8 | UINT32 |
| --- | --- |

<!-- Page 199 -->

Constant diameter constant diameter
−1 default value
filled circle: cross:
0x40000001 1 pixel 0x40000008 5 pixels
3 pixels 10 pixels
0x40000002 0x40000010
0x40000003 5 pixels 0x40000018 15 pixels
0x40000004 7 pixels 0x40000020 20 pixels
0x40000005 9 pixels 0x40000028 25 pixels
0x40000006 11 pixels 0x40000030 30 pixels
13 pixels 40 pixels
0x40000007 0x40000038
diagonal cross: circle:
0x40000040 5 pixels 0x40000200 5 pixels
0x40000080 10 pixels 0x40000400 10 pixels
0x400000c0 15 pixels 0x40000600 15 pixels
0x40000100 20 pixels 0x40000800 20 pixels
25 pixels 25 pixels
0x40000140 0x40000a00
0x40000180 30 pixels 0x40000c00 30 pixels
0x400001c0 40 Pixel 0x40000e00 40 Pixel
square:
0x40001000 5 pixels 0x40002000 10 pixel
0x40003000 15 pixels 0x40004000 20 pixel
25 pixels 30 pixel
0x40005000 0x40006000
0x40007000 40 pixels

Table C.5: Bitmap point types and their constants

Font Height

Type class: 2 / gr2dobj
Object type: 519 / font_height
Default: 0.1
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 FLOAT fontheight
16 16 End of structure
Inthecurrentattributeset,typeFontHeight objectssetthefontheight,measuredfromthebaseline
to the upper edge of normal capital letters. Thus, the height specification does not take into
consideration ascenders and descenders.
The font height is not given in points.

197

| Constant | diameter | constant | diameter |
| --- | --- | --- | --- |
| −1 | default value |  |  |
| filled circle: |  | cross: |  |
| 0x40000001 | 1 pixel | 0x40000008 | 5 pixels |
| 0x40000002 | 3 pixels | 0x40000010 | 10 pixels |
| 0x40000003 | 5 pixels | 0x40000018 | 15 pixels |
| 0x40000004 | 7 pixels | 0x40000020 | 20 pixels |
| 0x40000005 | 9 pixels | 0x40000028 | 25 pixels |
| 0x40000006 | 11 pixels | 0x40000030 | 30 pixels |
| 0x40000007 | 13 pixels | 0x40000038 | 40 pixels |
| diagonal cross: |  | circle: |  |
| 0x40000040 | 5 pixels | 0x40000200 | 5 pixels |
| 0x40000080 | 10 pixels | 0x40000400 | 10 pixels |
| 0x400000c0 | 15 pixels | 0x40000600 | 15 pixels |
| 0x40000100 | 20 pixels | 0x40000800 | 20 pixels |
| 0x40000140 | 25 pixels | 0x40000a00 | 25 pixels |
| 0x40000180 | 30 pixels | 0x40000c00 | 30 pixels |
| 0x400001c0 | 40 Pixel | 0x40000e00 | 40 Pixel |
| square: |  |  |  |
| 0x40001000 | 5 pixels | 0x40002000 | 10 pixel |
| 0x40003000 | 15 pixels | 0x40004000 | 20 pixel |
| 0x40005000 | 25 pixels | 0x40006000 | 30 pixel |
| 0x40007000 | 40 pixels |  |  |

| 8 | FLOAT |
| --- | --- |

<!-- Page 200 -->

Constant Type
0x00000001 small cross:
[(−0.5×d,0),(0.5×d,0)],[(0,−0.5×d),(0,0.5×d)]
0x00000002 large cross:
√ √ √ √
[(− 0.5×d,0),( 0.5×d,0)],[(0,− 0.5×d),(0, 0.5×d)]
0x00000004 small cross rotated by 45 ◦ :
√ √ √ √ √
[(− 0.125×d,− 0.125×d),( 0.125×d, 0.125×d)],[(− 0.125×
√ √ √
d, 0.125×d),( 0.125×d,− 0.125×d)]
large cross rotated by 45 ◦ :
0x00000008
[(−0.5×d,−0.5×d),(0.5×d,0.5×d)],[(−0.5×d,0.5×d),(0.5×
d,−0.5×d)]
0x00000010 circle, diameter is d, center is at (0,0)
0x00000020 square:
[(0.5×d,0.5×d),(−0.5×d,0.5×d),(−0.5×d,−0.5×d),(0.5×d,−0.5×
d)]
◦
0x00000040 square rotated by 45 :
[(0.5×d,0),(0,0.5×d),(−0.5×d,0),(0,−0.5×d)]
0x00000080 isosceles triangle, vertex to the right:
(cid:113)
3
c=(0.5− )×d, [(0.5×d,0),(c,0.5×d),(c,−0.5×d)]
4
0x00000100 isosceles triangle, vertex up:
(cid:113)
3
c=(0.5− )×d, [(0,0.5×d),(−0.5×d,c),(0.5×d,c)]
4
0x00000200 isosceles triangle, vertex to the left:
(cid:113)
3
c=(0.5− )×d, [(−0.5×d,0),(c,−0.5×d),(c,0.5×d)]
4
0x00000400 isosceles triangle, vertex down:
(cid:113)
3
c=(0.5− )×d, [(0,−0.5×d),(0.5×d,c),(−0.5×d,c)]
4
Table C.6: Vector point types and their constants

Font Aspect Ratio

Type class: 2 / gr2dobj
Object type: 520 / font_aspect_ratio
Default: 1.0
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 FLOAT aspectratio
16 16 End of structure
In the current attribute, type FontAspectRatio objects set the font aspect ratio. This ratio deter-
mineswhetherthefontshouldappearflattened,(aspectratio<1.0),stretched(aspectratio>1.0),
or normal (aspectratio=1.0).

198

| Constant | Type |
| --- | --- |
| 0x00000001 | small cross:
[(−0.5×d,0),(0.5×d,0)],[(0,−0.5×d),(0,0.5×d)] |
| 0x00000002 | large cross:
√ √ √ √
[(− 0.5×d,0),( 0.5×d,0)],[(0,− 0.5×d),(0, 0.5×d)] |
| 0x00000004 | small cross rotated by 45◦:
√ √ √ √ √
[(− 0.125×d,− 0.125×d),( 0.125×d, 0.125×d)],[(− 0.125×
√ √ √
d, 0.125×d),( 0.125×d,− 0.125×d)] |
| 0x00000008 | large cross rotated by 45◦:
[(−0.5×d,−0.5×d),(0.5×d,0.5×d)],[(−0.5×d,0.5×d),(0.5×
d,−0.5×d)] |
| 0x00000010 | circle, diameter is d, center is at (0,0) |
| 0x00000020 | square:
[(0.5×d,0.5×d),(−0.5×d,0.5×d),(−0.5×d,−0.5×d),(0.5×d,−0.5×
d)] |
| 0x00000040 | square rotated by 45◦:
[(0.5×d,0),(0,0.5×d),(−0.5×d,0),(0,−0.5×d)] |
| 0x00000080 | isosceles triangle, vertex to the right:
(cid:113)
c=(0.5− 3)×d, [(0.5×d,0),(c,0.5×d),(c,−0.5×d)]
4 |
| 0x00000100 | isosceles triangle, vertex up:
(cid:113)
c=(0.5− 3)×d, [(0,0.5×d),(−0.5×d,c),(0.5×d,c)]
4 |
| 0x00000200 | isosceles triangle, vertex to the left:
(cid:113)
c=(0.5− 3)×d, [(−0.5×d,0),(c,−0.5×d),(c,0.5×d)]
4 |
| 0x00000400 | isosceles triangle, vertex down:
(cid:113)
c=(0.5− 3)×d, [(0,−0.5×d),(0.5×d,c),(−0.5×d,c)]
4 |

| 8 | FLOAT |
| --- | --- |

<!-- Page 201 -->

Font Alignment

Type class: 2 /
gr2dobj
Object type: 521 / font_alignment
Default: −1.0
Parameter: Offset (S =1) Offset (S =0) Type Parameter
8 8 FLOAT alignment
16 16 End of structure
In the current attribute set, type FontAlignment objects set the horizontal orientation of the text
in relation to its origin.
If width is the width of the text, the ∆x offset of the left side of the first letter on the baseline in
relation to the reference point is determined as follows:
∆x=−(alignment+1.0)×(width/2.0)

Layer

Type class: 2 / gr2dobj
Object type: 523 / layer
Default: DEFAULT
Parameter Offset (S =1) Offset (S =0) Type Parameter
8 8 SYMBOL layer
roundup(11+len,8) roundup(11+len,8) End of structure
In the current attribute set, type Layer objects set the layer. The name of the layer must be
made up exclusively of ASCII letters, digits, and underscore and must not start with a digit. This
symbol is case sensitive.
The layer is used to control the visibility of objects. Generally it is possible to show and hide all
graphic objects belonging to a layer at the same time. The attributes are not allocated to objects
using the layer.
3
Inahierarchicalstructureofobjects,objectsbelongingtothedefaultlayer inheritthelayerfrom
the parent object which in turn can be the default layer. If this is the case, the respective object
4
is always displayed .

3
thenameofthedefaultlayerisDEFAULT.
4
Thedefaultlayercannotbehidden.

199

| 8 | FLOAT |
| --- | --- |

| 8 | SYMBOL |
| --- | --- |

<!-- Page 202 -->

# Appendix D

# External data formats

OFML defines the external data formats described below. The corresponding files are located in
a library directory or library archive. Global material definitions are located in a global directory
with a relative path of data/material. The predefined fonts are located in a global directory with
a relative path of data/font.
External data have to be qualified completely. For example, the taken text resource, @collision,
must be qualified from the ::ofml::xoi packet as follows when called:
”::ofml::xoi::@collision”
Ifatextresourceisnotqualified,theresourcefileisfirstlookedforinthepackageoftheimmediate
1
type of the instance for which the text resource is to be triggered . If the resource file cannot be
found in this package, the search continues in the supertype packages.

# D.1 Geometries

• Geometry description files define polygon geometries, which can be loaded into OFML di-
rectly.
• Name assignment: The name of the geometric definition file results from the name of the
geometry as it is applied in OiImport but without path or extension. Only ASCII characters
maybeused. However,spacesarenotallowed. Theextensiondependsontheindividualfile.
Allowed extensions are:

– geo – polygonal geometries (OFF format)
In this case, polygons must be defined simple, planar, convex and clockwise.
– ipc – optional polygon colors (OFF format)
If polygon colors are defined, a material can be allocated on the OFML level, but not
visualized.
1
for example, the instance that outputs a message using oiOutput(), or the instance that is sent to the oiGet-
StringResource()function

200

<!-- Page 203 -->

– vnm – optional vertex normals (OFF format)
If no vertex normals are defined, they are generated.
– 3ds – polygonal geometries (3DS format)
Only geometries and materials (including textures) are accepted. If polygon colors are
defined, a material can be allocated on the OFML level, but not visualized.
• Format: The formats correspond to the individual definitions of the 3DS format and the
OFF format.

# D.2 Materials

• Material definition files substitute String identifiers from OFML with a corresponding set of
material parameters.
• Name assignment: The name of a material definition file results from the name of the
material in lower case. Only ASCII characters may be used. If a material name consists of
more than one word, the words are joined together. In doing so, spaces are eliminated. The
file extension is mat.

Example: The ”ashnature.mat” file contains the definition of the material Ash Nature.
• Format: Material definition files are constructed line-by-line and consist of the name of the
material and any number of material parameter specifications. A material parameter speci-
fication overwrites the initial value of the corresponding material parameter. The following
specifications are permitted:
– amb Red(Float) Green(Float) Blue(Float)
The amb key specifies the ambient color of the material. The components are floating-
point numbers in the range of 0 ≤ z ≤ 1. The initial ambient color is white (1.0 1.0
1.0).
– dif Red(Float) Green(Float) Blue(Float)
Thedifkeyspecifiesthediffusecolorofthematerial. Thecomponentsarefloating-point
numbers in the range of 0≤z ≤1. The initial diffuse color is white (1.0 1.0 1.0). The
ambient and diffuse colors are usually the same.
– spe Red(Float) Green(Float) Blue(Float)
The spe key specifies the specular color of the material. The components are floating-
point numbers in the range of 0 ≤ z ≤ 1. The initial specular color is black (0.0 0.0
0.0).
– shi Shininess(Float)
Theshikeyspecifiesthespecularexponentusingapositivefloating-pointnumber. The
higher the exponent is, the lower the spread of the specular highlights. The initial
specular exponent has the value of 30.0.
– tra Transparency(Float)
Thetrakeyspecifiesthetransparencyusinganonnegativefloating-pointnumberthatis
less than or equal to 1. The value of 0.0 stands for complete impermeability; the value
of 1 means complete transparency. The initial transparency is 0.0.

201

<!-- Page 204 -->

– ref Refraction(Float)
The ref key specifies the refraction using a positive floating-point number. The initial
refraction has a value of 1.0 and is equivalent to the refraction in a vacuum.
– tex image Format(String) Name(String)
The tex key specifies an image map texture. Initially, no texture is applied in the scope
of the material being defined. The supported formats are Targa (tga), BMP (bmp),
JPEG (jpg) and SGI RGB (rgb). The Name parameter specifies the name of the image
without path or extension.
– scale X(Float) Y(Float) Z(Float)
If a texture has been defined using the tex key, the scale key specifies the scaling of the
texture. This is done using a positive scalar for each dimension. Each initial value is
1.0, meaning the image, regardless of its resolution, is scaled to a size of 1x1m.
– rotate AngleX(Float) AngleY(Float) AngleZ(Float)
If a texture has been defined using the tex key, the rotate key specifies the rotation of
thetexturebytheanglespecifiedindegreestothecorrespondingaxis. Theinitialvalue
is 0.00.00.0.
– prjx
If an image mapping has been defined using the tex key, the prjx key specifies the
projection of the image on the x-axis.
– prjy
If an image mapping has been defined using the tex key, the prjy key specifies the
projection of the image on the y-axis.
– prjz
If an image mapping has been defined using the tex key, the prjz key specifies the
projection of the image on the z-axis.
– prj X(Float) Y(FLoat) Z(Float)
If an image mapping has been defined using the tex key, the prj key specifies the pro-
jection of the image on the axis specified by X, Y and Z.
– circ R(Float)
If an image mapping has been defined using the tex key, the circ key specifies the
mapping of the image on a circle with the radius of R
– sph R(Float)
Ifanimagemappinghasbeendefinedusingthetexkey,thesphkeyspecifiesthemapping
of the image on a sphere with the radius of R
– cyl R(Float) H(Float)
Ifanimagemappinghasbeendefinedusingthetexkey,thecylkeyspecifiesthemapping
of the image on a cylinder with the radius of R and height of H.
– cone R1(Float) R2(Float) H(Float)
If an image mapping has been defined using the tex key, the cone key specifies the
mapping of the image on a cone with radii of R1 and R2 and height of H.

202

<!-- Page 205 -->

– quadX1(Float)Y1(Float)Z1(Float)X2(Float)Y2(Float)Z2(Float)X3(Float)Y3(Float)
Z3(Float) X4(Float) Y4(Float) Z4(Float)
If an image mapping has been defined using the tex key, the quad key specifies the
mappingoftheimageonacommonquadrilateralsurfacewithcorrespondingcoefficients.
– interp Mode(Int)
Ifanimagemappinghasbeendefinedusingthetexkey,theinterpkeyspecifieswhether
interpolation takes place (1) or not (0). The initial value is 1.
– once Mode(Int)
If an image mapping has been defined using the tex key, the once key specifies whether
a repeated mapping of the image takes place (1) or not (0). The initial value is 1.

The use of the material parameter depends on the applied display method. As long as objects
already define their own colors and materials, possibly concerning OiImport, the materials defined
here are not accepted.
In special cases, materials can be specified alternatively without external files. In such cases, the
parameter specifications can be entered directly in place of the material name. A material defined
in this manner must begin with a ’$’ sign. Furthermore, semicolons are used in place of the line
ends. Using the mat key is not permitted in this case.

Example: The ”$ amb 1.0 0.0 0.0; dif 1.0 0.0 0.0” string sets the color of red as a material without the
use of an external material definition file.

# D.3 Fonts

• The fonts supported in OFML are based on the fonts created by Dr. A. V. Hershey (U.S.
National Bureau of Standards). These are vector fonts, which describe continuous lines.
The following fonts are to be prepared by an OFML-conforming runtime environment:

– default
– cyrillic
– cursive
– timesg
– timesi
– timesib
– timesr
– timesrb

• Name assignment: The name of a font results from an identifier (the name of the font),
in which all letters are lower case. The font name does not have an extension.
• Format: The format corresponds to the definition of the Hershey font format.

203

<!-- Page 206 -->

# D.4 External Tables

• External tables, such as product databases, are saved in a simple text format. Data records
are separated by line breaks. The individual fields of a data record have fixed lengths; there
are no field separators. Fields that are shorter than their corresponding lengths are filled in
to achieve their fixed lengths.
This generic table format can be read within OFML using the global oiTable() function
(Chapter 6).
• Name assignment: The name of a product database can be chosen freely.
• Format: The following field types are understood:
– Character strings. These are left-justified and, as necessary, filled with spaces, except
the last field in a data record. In the later case, the character string is closed with the
line end.
If the last field is the empty string, it can be omitted completely. In this case, the field
before the last is handled according to the rules above. If the field before the last is
empty as well, the rules can be applied again.
– Integers are right-justified and are filled with zeros.
– Fixed point numbers are right-justified and are filled with zeros; the decimal point is
left out.
– Fields that serve as the first key for access must be sorted in ascending order.

# D.5 Text Resources

• Text resources substitute a symbol identifier from OFML with a corresponding text from
an external file. This might find use, for example, for property names, description texts or
output texts.
• Name assignment: The name of a resource file is made up a link of the library names and
the corresponding ISO country abbreviation, separated by an underscore. The file extension
is sr. All letters are lower case.

Example: The ”room de.sr” file contains the German text resources for the Room library.
• Format: The relevant lines are formatted as follows:

@SYMBOL=<Text>

Here, the left expression is the assignment of a valid symbol as understood in OFML. The
right expression is a text in any 8-bit character format. For Western Europe, the ISO-Latin
1 (ISO 8859-1) character set is applied. Another valid character format, for example, is
UTF 8. For use with formatted output, the text can be a format character string (Section
6.1). All other lines are ignored and can be used for structuring and comments. Based on
convention, a single pound sign indicates a comment. Two pound signs leads to structuring
of the resource file. By convention, the following structurings are established:

204

<!-- Page 207 -->

– ## messages: – Character strings that follow stand for messages, warnings etc.
– ## properties: – Character strings that follow stand for property titles.

# D.6 Archives

• Archives represent containers, each of which usually contains all of the files belonging to a
library. The archive structure corresponds to the format used by the UNIX SVR4 ar utility
program.
• Name assignment: The name of an archive is lower case. The extension is alb. No other
standards apply.
• Format: All archives begin with the string, !<arch>\n . The rest of the archive is made up
of objects, each of which consists of a header and the actual content of the file.
The header consists of six, fixed-length fields of ASCII characters. With two exceptions (see
below, these fields contain the file names (16 characters), the most recent time the file was
modified (12 characters), the user and group numbers of the file owner (6 characters each),
the access mode (8 characters) and the size of the file in bytes. All numerical fields are
decimal, except the access mode, which is specified in octal. The header is closed with the
‘\n string.
File names that are longer than 16 characters are treated differently. If at least one such
file exists in the archive, the first object in the archive is not a file, but a table named //,
which contains the long file names. In place of the file name in the header of each file is the
character, /, followed by a number that indicates the offset of the file name in regard to the
table.
A line break is appended to files having an uneven number of bytes, which, however, has
no effect on the size specified in the header. This ensures that every object starts on an
even-numbered address.
¿From the OFML runtime environment, each archive becomes a special file called __attrib,
which contains the attributes of the archive. Each attribute claims one line and contains a
key and value pair, the elements of which are separated by a space. The following attributes
are standardized:

version The version of the archive, consisting of two numbers
separated by a period.
valid_span The validity range of the archive, consisting of
two date entries separated by an underscore.
pwdcheck A password for checking encryption.
md5sum The MD5 checksum of the archive.

All attributes are optional. Any number of attributes can be added.

205

<!-- Page 208 -->

# Appendix E

# Format Specifications

# E.1 Format Specifications for Properties

This section describes syntax and meaning of format specifications for properties. Format spec-
ifications can be entered during the setting of properties in the setupProperty() function of the
Property interface (Section 4.4).
The format specification has one of the following forms:

property-format:
"@L"
"@A"
"%[-][width][.prec]type"

The first two formats can be used with properties of the "f" base type and indicate that the
property value is a length or angle measurement and that the unit of measure set by the user
should be used for the presentation of entry of the value. The property editor must then perform
a conversion between the user-defined unit of measure and the unit of measure used in OFML for
length and angle measurements (m or rad).
The third form is used if an OFML object intends to force a special format for the presentation or
entryofpropertyvalues. Theformatcharacterstringofthisformbeginswitha%sign. Afterwards,
the following specifiers in the respective sequence are allowed:

• an optional left-align indicator – " [-] "
• an optional width specifier – [width]
• an optional precision specifier – [.prec]
• a required type specifier – type
The following discrete value range is predefined for the type specifier:

206

<!-- Page 209 -->

– Decimal number (Int) – d
The argument must be an Int value. The value is converted to a character string that
contains the decimal places. If the format specification contains a precision specifier,
the specifier indicates that the resulting character string contains at least the specified
number of places. If the value features fewer places, it is filled with zeros dependent
upon the optional left-align indicator. If the left-align indicator is given, zeros are filled
in on the right side. Otherwise, zeros are filled in on the left side.
If the width specifier is used, it indicates the maximum number of places that the
resulting character string may possess. If width and precision specifier are used, then
the following applies: width ≥ prec.
– Floating point number (Float) – f
The argument must be a floating point number. The value is converted to a character
stringoftheform " -ddd.ddd... " . Theresultingcharacterstringstartswithaminussign
if the number is negative. The number of places after the decimal point is indicated by
the precision specifier. If no precision specifier is given, 2 is assumed as the number of
decimal places after the period.
Ifawidthspecifierisused,itindicatestheexactwidthoftheresultingcharacterstring.
Here, the minus sign is counted, but the decimal point is not. If the value has fewer
digits, zeros are filled in on the left side. The left-align indicator is ignored, if present.
If the value has more digits, the leading places are suppressed.
– Character string (String) – s
Theargumentmustbeacharacterstring. Itisinsertedinsteadoftheformatspecifier. If
the precision specifier is indicated, it defines the maximum length of the resulting char-
acter string. If the length of the argument exceeds the maximum length, the character
string is cut off accordingly.
Iftheformatspecificationcontainsawidthspecifier,thespecifierindicatestheminimum
number of characters of the resulting character string. If the character string features
fewer characters, the resulting character string is filled with spaces on the left side
(without set left-align indicator) or on the right side (with set left-align indicator).

# E.2 Definition Format for Properties

This section describes the format of a property definition description that describes all properties
ofaninstanceandisdeliveredastheresultofthegetProperties()functioninthePropertyinterface
(Section 4.4).
The following rules apply to the format of the definition of properties:

• The description of all properties consists of the descriptions for each individual property
separated from each other by semicolons.
• EachpropertydefinitionreflectsthedatathataretransferredtotheProperty::setupProperty()
function and consists of a set of required and optional specifications that are separated by
semicolons.

207

<!-- Page 210 -->

• A semicolon can be followed by a random number of spaces.
• The first specification of a property definition is the key specifier:
– k <str> – key of the specified property.
• The last specifier of a property specification is the type specifier. It must have one of the
following values:
– b – a boolean type (0 or 1).
– i – a decimal type.
– f – a floating point number type.
– s – a character string type.
– ch<str>*n–aselectionlistwithn,n>0characterstringsforusewithcharacterstring
entry.
– chf <str> – a selection list whose possible character strings are delivered by the listed
function.
– u – a user-defined type with a given editor identification.
• Additional optional specifiers between key and type specifier are:
– n <str>*n – the name of the property.
– d <str>*n – the initial value of the property.
– mn <str> – minimum value of a decimal or floating point number or minimum number
of characters in a character string property.
– mx <str>–maximumvalueofadecimalorfloatingpointnumberormaximumnumber
of characters in a character string property.
– fmt <str> – C-type format specifier (Section E.1)

208

<!-- Page 211 -->

# Appendix F

# Additional Types

ThefollowingdefinedtypesarenotadirectcomponentofOFML,buttheycanbeusedinOFML-
conform libraries. The Base interface is implemented, but with a few specific limitations in each
case.

# F.1 Interactor

### Description

• Interactor implements the base class for interactors.
• Interface(s): Base with limitations:
ThefunctionsisCat(),hide(),show(),isHidden(),selectable(),notSelectable(),isSelectable(),
setCutable(), isCutable(), enableCD(), disableCD(), isEnabledCD(), measure(), and unMea-
sure() are not available. The instance variable mIsCutable is not available.

### Initialization

• Interactor(pFather(MObject), pName(Symbol))
The function initializes an instance of the Interactor type.

### Methods

• final makeVisible(pType(Type) ...) → Void
The function generates an instance of the indicated type as element which represents the
geometry of the interactor. After the type argument, additional constructor arguments may
follow. If the interactor is already visible, the function is without effect. The transfer of
ZERO makes the interactor visible.

209

<!-- Page 212 -->

• final isVisible() → Int
The function delivers 1 if the interactor is visible, otherwise 0.
• final getState() → Symbol
The function delivers the state of the interactor which is described by one of the symbols
@ENABLED, @DISABLED or @ACTIVE.
• final enable() → Int
It sets the interactor in the state ”free” (@ENABLED) and always delivers 1 (success).
• final disable() → Int
It sets the interactor in the state ”blocked” (@DISABLED) and always delivers 1 (success).
• final activate() → Int
It sets the interactor in the state ”active” (@ACTIVE) where it must already be in the state
@ENABLED. It delivers 1 with success and 0 if the interactor was blocked.

# F.2 Light

### Description

• Light is a globally acting active light source that is, however, integrated in an instance
hierarchy. The following procedure applies for converting the light source in a local lighting
model: Ifthelightsourcefeatureschildren, itisadirectionalpointlightsource. Itislocated
in the local origin and lights along the local negative y-axis. The aperture of the cone of
light results from the arcus tangent of the relationship of the maximum z-value of the local
delimiting volume of the light source to the negative minimum y-coordinate of the local
delimiting volume.
If the light source does not have any children or the minimum y-coordinate of the local
delimiting volume is equal to 0.0, it is a nondirectional point light source.
In a global lighting model, this explicit differentiation is unnecessary.
• The Light type may not be derived.
• Interface(s): Base with limitations:
The functions getType(), isCat(), setCutable(), isCutable(), enableCD(), disableCD(), isEn-
abledCD(), measure(), and unMeasure() are not available. The instance variable mIsCutable
is not available.

### Initialization

• Light(pFather(MObject), pName(Symbol))
The function initializes an instance of the Light type.

210

<!-- Page 213 -->

### Methods

• final setColor(pColor(Float[3])) → self
The function sets the color of the light source. The elements of the pColor vector must be
real numbers in the interval from 0.0 to 1.0 where the interval boundaries are acceptable
values. Thevectorelementsareinterpretedasamplitudesofthewavelengthsred,green, and
blue. Their linear combination results in the actual color. The initial light color is white.
• final getColor() → Float[3]
The function furnishes the current light color of the implicit instance.
• final on() → self
The function activates the light source.
• final off() → self
The function deactivates the light source.
• final isOn() → Int
The function signals the status of the light source via its return value: activated (1) or
deactivated (0).

# F.3 MLine

### Description

• MLine implements an automatic dimensioning primitive that automatically dimensions the
higher-order object in the hierarchy.
The line thickness measures 1 in the smallest representation unit of the image space in each
case, e.g., 1 pixel.
• The MLine type may not be derived.
• Interface(s): Base with limitations:
The functions getType(), isCat(), hide(), show(), isHidden(), selectable(), notSelectable(),
isSelectable(),setCutable(),isCutable(),enableCD(),disableCD(),isEnabledCD(),measure(),
and unMeasure() are not available. The instance variable mIsCutable is not available.

### Initialization

• MLine(pFather(MObject), pName(Symbol), pDirection(Symbol))
The function initializes an instance of the MLine type. The pDirection parameter defines
howthetopologicallyhigher-orderprimitiveisdimensioned. Eitherthewidth, theheight, or
thedepthofthelocaldelimitingvolumeofthefatherisdimensioned. Thefollowingsymbols
are allowed:

211

<!-- Page 214 -->

@NX The width is dimensioned at the bottom rear. The dimensioning lies in the local x-y-
plane of the father and can be read from the front.
@NXG The width is dimensioned at the bottom rear. The dimensioning lies in the local x-z-
plane of the father and can be read from the front and the top.
@NXT The width is dimensioned at the bottom rear. The dimensioning lies in the local x-z-
plane of the father and can be read from the rear and the top.
@PX The width is dimensioned at the top rear. The dimensioning lies in the local x-y-plane
of the father and can be read from the front.
@PXT The width is dimensioned at the bottom front. The dimensioning lies in the local
x-z-plane of the father and can be read from the front and the top.
@NY Theheightisdimensionedfromtheleftrear. Thedimensioningliesinthelocalx-y-plane
of the father, can be read from the front, and is aligned from bottom to top.
@PY The height is dimensioned from the right rear. The dimensioning lies in the local x-y-
plane of the father, can be read from the front, and is aligned from bottom to top.
@NZ The depth is dimensioned from the bottom left. The dimensioning lies in the local
y-z-plane of the father and can be read from the left.
@NZT The depth is dimensioned from the bottom left. The dimensioning lies in the local
x-z-plane of the father and can be read from the left and the top.
@PZ The depth is dimensioned from the bottom right. The dimensioning lies in the local
y-z-plane of the father and can be read from the right.
@PZT The depth is dimensioned from the bottom right. The dimensioning lies in the local
x-z-plane of the father and can be read from the right and the top.

### Methods

• final setMaterial(pMaterial(String)) → self
The specified material is assigned. The ambient component of the material is assigned as
color during the display. The presentation should be done without considering the lighting
and tint.
• final getMaterial() → String
The function delivers the currently valid material of the implicit instance.
• final setOffset(pOffset(Float)) → self
Thisfunctionsetstheoffsetofthedimensionlinewithrespecttotheedgetobedimensioned.
The initial offset measures 0.1.
• final getOffset() → Float
The function furnishes the current offset of the implicit instance.
• final setText(pText(String)) → self
Initially, entities of MLine automatically dimension the respective edge of the delimiting
volume of the father object and automatically adjust to the dimensional changes. However,
byusingthisfunctionthetextcanbesetexplicitly. Inthiscase,thepTextparameterpresents
the text to be displayed by means of an ASCII character string.

212

<!-- Page 215 -->

• final getText() → String
The function delivers the currently displayed text.

# F.4 MSymbol

### Description

• MSymbol implements a polymorphic dimensioning primitive. All variants are generated in
the local x-y-plane. The z-coordinate is always 0. Coordinates with respect to this plane are
represented by a vector with 2 elements (x- and y-value, in this order).
The line thickness measures 1 in the smallest representation unit of the image space in each
case, e.g., 1 pixel.
• The MSymbol type may not be derived.
• Interface(s): Base with limitations:
The functions getType(), isCat(), hide(), show(), isHidden(), selectable(), notSelectable(),
isSelectable(),setCutable(),isCutable(),enableCD(),disableCD(),isEnabledCD(),measure(),
and unMeasure() are not available. The instance variable mIsCutable is not available.

### Initialization

• MSymbol(pFather(MObject), pName(Symbol), pMode(Symbol), pValues(Float[][2]))
The function initializes an instance of the MSymbol type. In this context, the pMode param-
eter together with the variable pValues parameter specifies the implementation of MSymbol.
TheevaluationofpValuesisdependentupontheassignmentofpMode. Thefollowingsymbols
may be used for pMode:
@ARCLINE Nocontourofasegmentofacircleisgenerated. Theoriginofthecorrespondingcircleis
indicated by pValues[0]. pValues[1][0] defines the radius of the circle through a positive
number. pValues[1][1] defines the length of the line in the radian measure through a
non-negative number. If the length is positive, the line starts at
(pValues[0][0], pValues[0][1]+pValues[1][0])
in clockwise direction. If it is negative, it starts at the same point, but runs in counter-
clockwise direction.
@CIRCLE A filled circle is generated in the local origin. pValues[0][0] defines the radius of the
circle through a positive number.
@POLYLINE A continuous line is generated that connects the given points in the respective order.
The last and first point are not connected. The orientation is not taken into account.
@RECTANGLE A filled rectangle is generated. pValues[0] describes the lower left corner. pValues[1]
describes the upper right corner.
@X CIRCLE A circle is generated. pValues[0] defines the origin of the circle with respect to the
localcoordinatesystem. pValues[1][0]definestheradiusofthecirclethroughapositive
number. IfpValues[1][1]equals0.0,onlythecontourisshown. Otherwise,afilledcircle
is drawn.

213

<!-- Page 216 -->

### Methods

• final setMaterial(pMaterial(String)) → self
The specified material is assigned. The ambient component of the material is assigned as
color during the display. The presentation should be done without considering the lighting
and tint.
• final getMaterial() → String
The function delivers the currently valid material of the implicit instance.

# F.5 MText

### Description

• MText implements a vector-text-primitive.
The line thickness measures 1 in the smallest representation unit of the image space in each
case, e.g., 1 pixel.
• The MText type may not be derived.
• Interface(s): Base with limitations:
The functions getType(), isCat(), hide(), show(), isHidden(), selectable(), notSelectable(),
isSelectable(),setCutable(),isCutable(),enableCD(),disableCD(),isEnabledCD(),measure(),
and unMeasure() are not available. The instance variable mIsCutable is not available.

### Initialization

• MText(pFather(MObject), pName(Symbol), pText(String))
The function initializes an instance of the MText type. The pText parameter specifies the
text to be displayed in form of an ASCII character string.

### Methods

• final setMaterial(pMaterial(String)) → self
The specified material is assigned. The ambient component of the material is assigned as
color during the display. The presentation should be done without considering the lighting
and tint.
• final getMaterial() → String
The function delivers the currently valid material of the implicit instance.
• final setFont(pFont(String)) → self
The specified font is assigned. pFont specifies the font through a corresponding font name
without path or extension information in accordance with Chapter D.

214

<!-- Page 217 -->

• final getFont() → String
The function furnishes the current font of the implicit instance.
• final setText(pText(String)) → self
The test to be displayed is set anew through the ASCII character string pText.
• final getText() → String
The function furnishes the current text of the implicit instance.
• final setScale(pScale(Float)) → self
The positive pScale parameter sets the scaling of the text. The initial scaling measures 0.05.
• final getScale() → Float
The function furnishes the current scaling of the implicit instance.
• final setAlignment(pAlignment(Symbol)) → self
The pAlignment parameter determines the horizontal alignment of the text. The following
symbols can be used here:
@LEFT The text is left-aligned with respect to the local reference point.
@CENTER The text is centered with respect to the local reference point.
@RIGHT The text is right-aligned with respect to the local reference point.
The initial alignment is @CENTER.
• final getAlignment() → Symbol
The function furnishes the current alignment of the implicit instance.
• final setMode(pMode(Symbol)) → self
The pMode parameter sets the presentation mode of the text. The following symbols are
allowed here:
@NORMAL The text is shown in normal mode.
@UNDERLINE The text is highlighted through underlining.
@BOX The text is highlighted by a box.
The initial display mode is @NORMAL.
• final getMode() → Symbol
The function furnishes the current display mode of the implicit instance.

215

<!-- Page 218 -->

# Appendix G

# Applied Notation

# G.1 Class Diagrams based on Rumbaugh

The notation used in this document for class diagrams is a modified form of the notation by
Rumbaugh [Rumb91].

cardinality: 1
abstract class
specific
Association class1
Attribute
AbstractMethod
Aggregation specific
class2

cardinality: 1 or more
specific specific
cardinality: 0 or more
subclass1 subclass2
Attribute Attribute
implementation
Method Method
in pseudo code

Figure G.1: Modified Rumbaugh Notation for Class Diagrams

In object-oriented software engineering, class diagrams are used to visualize the properties (at-
tributes, methods) of classes and relationships between classes. Principally, there are three types
of relationship:

• Vererbung (Inheritance).
A subclass inherits the properties of its super-class(es).

216

| abstract class |
| --- |
| Attribute |
| AbstractMethod |

| specific
subclass1 |
| --- |
| Attribute |
| Method |

| specific
subclass2 |
| --- |
| Attribute |
| Method |

| implementation
in pseudo code |  |
| --- | --- |

<!-- Page 219 -->

• Aggregation (Consists Of).
An instance of a class (an object) contains (consists of) one or more object(s) of another
class.
• Assoziation bzw. Bekanntschaft (Acquaintance).
An object of a class ”knows”’ an object of another class or is associated with it.

In abstract models, the attribute and/or method part of a class can be omitted.

217

<!-- Page 220 -->

# Appendix H

# Categories

Thecategoriesoutlinedbelowarepredefinedaccordingtothedefinition. Theuseofthesecategories
is optional; the applicability and readability of data acquired in OFML increases accordingly if
these categories are used.

# H.1 Interface Categories

For each OFML interface, a predefined corresponding category exists whose symbolic designator
1
isformedbytheprefix”‘IF ”’ andthenameoftheinterface, e.g., @IF Article. Inthisway, every
instance of an OFML type can be queried using the isCat() function whether it implements a
special interface.

# H.2 Material Categories

The following categories are predefined to designate the assignment of a geometric object or a
complex object to a certain material category:

• @FRONT – The object belongs to the front of a complex object or represents it.
• @GRIFF – The object belongs to the handle of a complex object or represents it.
• @KORPUS – The object belongs to the corpus of a complex object or represents it.
• @KRANZ – The object belongs to the border of a complex object or represents it.
• @RUECK – The object belongs to the back of a complex object or represents it.
• @SOCKEL – The object belongs to the base of a complex object or represents it.
1 acronymforinterface

218

<!-- Page 221 -->

• @S FUSS – The object belongs to the foot of a chair or represents it.
• @S LEHNE – The object belongs to the back rest of a chair or represents it.
• @S SITZ – The object belongs to the seat of a chair or represents it.
• @T FUSS – The object belongs to the foot of a table or represents it.
• @T GESTELL – The object belongs to the stand of a table or represents it.
• @T GEST ABDECK – The object belongs to a lateral stand cover or represents it.
• @T KANTE – The object belongs to the edge of a table top or represents it.
• @T PLATTE – The object belongs to a table top or represents it.

# H.3 Planning Categories

The following categories are predefined to designate the ability of adding sections of an object:

• @CEILING ELEM – The object (e.g., a ceiling lamp) can be planned below an object.
• @TOP ELEM – The object (e.g., a desk lamp) can be planned on the surface of an object.
• @WALL ELEM – The object (e.g., an electrical outlet) can be planned at the surface of an
object.

219

<!-- Page 222 -->

# Appendix I

# Terms

• Bounding box
– A bounding box is a rectangular volume that minimally encloses a body.
– The definition of bounding boxes makes reference to the local coordinate system of an
object or to the common coordinate system of all objects (world or global coordinate
system).
• Category
– Acategoryisaclassificationof→typesor→entitiesthatresultsfromacertainviewing
perspective.
– Categories represent an expansion of the concept of types.
• Clipboard
– A clipboard is a buffer storage in which objects can be placed. Objects can be written
to the clipboard using operations such as Cut and Copy. They can be read out again
from the clipboard using the Paste operation.
• Coordinate system
– A coordinate system is an orthogonal space defined by three axes (x, y, z) to which
position and direction information are referenced.
– Inaspecificcase,thez-andx-axisspanaplaneonwhichthey-axisislocatedataright
angle.
• Father object
– A father object is an → object from which properties are inherited, e.g., a name space,
the spatial modeling, the material, etc.

220

<!-- Page 223 -->

• Identity
– The identity of an → instance results from a → name in the hierarchical name space
that exists only once and uniquely describes the position in an instance hierarchy.
• Instance
– An instance is a concrete implementation of a → type. It differs from other entities
through a local copy of → attributes, especially through a unique → identity.
– Synonyms for instance are → object and entity.
• Interface
– An interface is the collection of a number of methods and member variables that a →
type must define or implement for interface compatibility.
• Lighting model
– Alightingmodelusesgreatsimplificationtosimulatethelightingofbodies(3Dobjects).
– For a local lighting model, only the lighted object and the light source (distance, ma-
terials, etc.) are viewed.
– For a global lighting model, other objects of the → scene that cause shadows or reflec-
tions are also included.
• Name
– The(absolute)nameofan→instanceuniquelydescribesthetopologicalpositionofthe
instance. Alternatively,aninstancecanalsobereferencedthrougha→symbolrelating
to the respective context or through a variable.
• Object
– From a programmer’s view, an object is a synonym for the → instance of a → type.
From a user’s view, an object represents a certain unit that can be generated, selected,
modified, and deleted as a whole.
• Program
– A set of products combined by a manufacturer for functional and/or aesthetic points of
view.
– Synonyms: collection, product line
• Property (Feature)
– Apropertyisafeatureofaninstance,e.g.,ageometricmeasurementorthedesignation
of an execution that may be changed interactively by the system user with the help of
appropriate dialogs (property editors).

221

<!-- Page 224 -->

• Symbol
– Asymbolisastring-likevaluethatisusedprimarilytodesignateconstantsandinstance
→ names.
• Root object
– A root object is an → object that is located at the root of an object hierarchy. Conse-
quently, a root object has no → father object. All objects that are directly located in a
→ scene are root objects.
• Scene
– A scene is the collection of a number of 3D objects, in the context of OFML also called
→ entities.
• Type
– Atypecombinesanumberofhomogenous→entitiesanddefinesstructureandbehavior
for them.
– A type implements one or several → interfaces.
– A type features no more than one direct super type; its characteristics are inherited
from the super type.
– Class is a synonym for type.
• Units
– If no other specific definition exists, units of length implicitly feature the unit meter.
– If no other specific definition exists, units of angle implicitly feature the unit radiant.

222

<!-- Page 225 -->

# Index

Change Status, 81 callRules()
Spatial Modeling, 82 Base, 85
Spatial model, 95 Category, 16
2D Representation, 86 changedPropList()
2D interface, 169 Property, 93
3DS file, 125, 201 Check String, 115
checkAdd()
ABAP/4, 156
Complex, 95
Action, 168
OiLevel, 165
Activation Status of a Property, 94
OiPart, 151
add()
OiPlanning, 137
MObject, 78
OiPlElement, 145
addInfoObj()
OiProgInfo, 141
OiPlanning, 136
checkBorder()
addPart()
OiPlanning, 136
Complex, 97
checkChildColl()
addProductDB()
Complex, 98
OiPDManager, 157
OiPlanning, 137
OiPlanning, 139
checkConsistency()
Archive, 205
Article, 101
Article
OiPart, 152
Article, 98
OiPDManager, 159
Information, 99, 100, 158, 162
OiPlanning, 139
information, 14
OiPlElement, 147
Information, general, 99
OiProductDB, 162
article2Class()
OiProgInfo, 141
OiPDManager, 158
checkElPos()
OiPlanning, 139
Complex, 97
article2Params()
OiPlanning, 137
OiPDManager, 158
checkObjConsistency()
OiPlanning, 140
Base, 79
checkPosition()
Basic interfaces, 77
OiPlanning, 138
Block, 118
Child, 12, 78
Bounding Box
and instance variable, 12
global, 84
Creation and management, 95
global, geometric, 85
Transformation, 147
local, 84
Class, 10
local, geometric, 84

223

<!-- Page 226 -->

class2Articles() Element, 12, 78
OiPDManager, 158 Transformation, 138
clearInfoObjs() elemRotation()
OiPlanning, 136 OiPlanning, 138
clearMethod() OiPlElement, 147
Complex, 97 elemTranslation()
clearProductDBs() OiPlanning, 138
OiPDManager, 157 OiPlElement, 147
Clipboard, 80, 96, 110, 114 Ellipsoid, 120
Collision Detection, 82 elRemoveValid()
Collision detection, 111, 141 OiPart, 151
for children, 97 OiPlElement, 146
Complex, 94 enableCD()
Condition, 168 Base, 82
Consistency check, 101 enableChildCD()
Constraint, 168 Complex, 97
CREATE ELEMENT, 103 Environment, 135
createOdbChildren() Epsilon, eps, 79
OiOdbPlElement, 155 Error log, 134
createOdbObjects() evalPropValue()
Base, 87 OiPDManager, 158
Cylinder, 119 Existence check, 113
Cuttability, 80 external data, 200
external geometry (ODB)
Database, 115
2D, 180
delegationDone()
Extrusion body, 129
OiPlanning, 134
delInfoObj() Father, 12
OiPlanning, 136 Father-child-relation, 12
delProductDB() Feature, 89
OiPDManager, 157 FINISH DUMP, 107
Diagram, 216 FINISH EVAL, 107
Dimensioning, 82 finishCollCheck()
disableCD() OiProgInfo, 142
Base, 82 Font, 203
disableChildCD() Format specifications, 206
Complex, 97 Frame, 121
Dissolving text resources, 113
Generating a dump representation, 112
Distance measurement, 113
geometric object, 117
doCheckAdd()
Geometry, 117, 200
OiPlanning, 137
getAllMatCats()
doSpecial()
Material, 89
OiPlanning, 140
OiPart, 150
OiProgInfo, 141
OiPlElement, 144
Dynamic Properties, 86
getArticleFeatures()
EasternGraphics Metafile, 180 Article, 101
EGM, 180 OiPart, 152

224

<!-- Page 227 -->

OiPDManager, 160 getDistance()
OiPlElement, 146 Base, 85
getArticleParams() getDynamicProps()
Article, 100 Base, 86
OiPart, 151 getElements()
OiPlElement, 146 MObject, 78
getArticlePrice() getEnvironment()
Article, 100 OiPlanning, 135
OiPart, 151 getErrorLog()
OiPDManager, 159 OiPlanning, 135
OiPlElement, 146 getExtPropOffset()
OiProductDB, 163 Property, 92
getArticleSpec() getFather()
Article, 99 MObject, 78
OiOdbPlElement, 154 getFinalArticleSpec()
OiPart, 151 OiProductDB, 163
OiPlElement, 146 getHeight()
getArticleText() Complex, 95
Article, 100 OiLevel, 165
OiPart, 152 OiPart, 149
OiPDManager, 160 OiPlElement, 143
OiPlElement, 146 getID()
OiProductDB, 163 OiProductDB, 161
getBorder() OiProgInfo, 141
OiPlanning, 135 getInfo()
getChildren() OiPlanning, 136
MObject, 78 getInfoIDs()
getClass() OiPlanning, 136
MObject, 77 getLanguage()
getCMaterial() OiPlanning, 133
Material, 89 getLocalBounds()
OiPart, 150 Base, 84
OiPlanning, 136 getLocalGeoBounds()
OiPlElement, 144 Base, 84
OiProgInfo, 141 getMatCategories()
getCMaterials() Material, 88
Material, 89 OiPart, 150
OiPart, 150 OiPlanning, 136
OiPlanning, 136 OiPlElement, 144
OiPlElement, 144 OiProgInfo, 141
OiProgInfo, 141 getMatName()
getDataBasePath() Material, 89
OiProductDB, 161 OiPart, 150
getDepth() OiPlanning, 136
Complex, 95 OiPlElement, 144
OiPart, 149 OiProgInfo, 141
OiPlElement, 143 getMethod()

225

<!-- Page 228 -->

Complex, 96 getPropDescription()
getName() OiProductDB, 163
MObject, 78 getProperties()
getOdbInfo() Property, 92
Base, 86 getPropertyDef()
OiOdbPlElement, 155 Property, 92
getOrderID() getPropertyKeys()
Article, 99 Property, 92
getOrigin() getPropertyPos()
OiPart, 149 Property, 92
OiPlElement, 143 getPropInfo()
getPasteMode() Property, 94
Complex, 96 getPropObj()
getPDB IDs() OiPlanning, 135
OiPDManager, 157 getPropState()
getPDBFor() Property, 94
OiPDManager, 158 getPropTitle()
getPDistance() Property, 92
OiPlElement, 145 getPropValue()
getPDManager() Property, 93
OiPlanning, 139 getRegion()
OiProductDB, 161 OiPlanning, 134
getPictureInfo() getResolution()
Base, 86 Base, 81
getPlanning() getRoot()
OiPart, 149 MObject, 78
OiPlElement, 142 getRotation()
OiProgInfo, 141 Base, 84
OiPropertyObj, 153 getRtAxis()
getPlanningMode() Base, 84
OiLevel, 165 getTempArticleSpec()
getPlanningWall() Complex, 96
OiLevel, 165 getTopPlElement()
getPlElementUp() OiPlanning, 135
OiPlanning, 135 getTrAxis()
getPosition() Base, 83
Base, 83 getType()
getProductDB() MObject, 77
OiPDManager, 157 getVarCode()
getProgPDB() OiProductDB, 162
OiPDManager, 158 getWallOffset()
getProgram() OiPlElement, 145
Article, 98 getWallParams()
getPrograms() Wall, 164
OiProductDB, 161 getWidth()
getPropDefs() Complex, 95
OiProductDB, 161 OiPart, 149

226

<!-- Page 229 -->

OiPlElement, 143 OiPropertyObj, 153
getWorldBounds() isElemCatValid()
Base, 84 OiPart, 150
getWorldGeoBounds() OiPlElement, 144
Base, 85 isElOrderSubPos()
getXArticleSpec() OiPart, 151
Article, 99 OiPlElement, 146
OiPDManager, 159 isEnabledCD()
Global planning object, 132 Base, 82
GO types, 8 isEnabledChildCD()
Complex, 97
hasProductKnowledge()
isHidden()
OiProductDB, 161
Base, 81
hasProperties()
isMatCat()
Property, 91
Material, 88
hasProperty()
isSelectable()
Property, 92
Base, 80
hide()
isValidForCollCheck()
Base, 81
Complex, 97
hierSelectable()
OiPlanning, 137
Base, 79
OiProgInfo, 142
Hole, 122
Hyperlink, 114 Language Selection, 133
Light, 210
Import of Geometries, 125
Light source, 210
Information object, 136
Link, 114
Inheritance of features, 12
Initialization, 16
Material, 87
Instance, 10–12
-definition, 201
Identity, 13
Categories, 88, 218
identity, 78
measure()
Initialization, 16
Base, 82
name, 13
Measurement line, 211
variable, 11, 14
Measurement symbol, 213
INTERACTOR, 108
Measurement text, 214
Interactor, 17, 209
Metafile, 180
Interface, 11, 14
Method, 10, 14
Interfaces
Difference compared to rule, 15
Basic interfaces, 77
MLine, 211
Categories, 218
MObject, 77
invalidatePicture()
Modal dialog, 111
Base, 87 Module, 10
isA() moveTo()
MObject, 77 Base, 83
isCat() MSymbol, 213
MObject, 78 MText, 214
isCutable()
Name space
Base, 80

227

<!-- Page 230 -->

hierarchical, 13 OiHole, 122
Names OiHPolygon, 124
for entities, 13 OiImport, 125
of methods, 15 OiLevel, 164
predefined, 13 oiLink(), 114
reserved, 13 OiOdbPlElement, 154
NEW ELEMENT, 104 oiOutput(), 114
Notation, 216 OiPart, 148
notHierSelectable() oiPaste(), 114
Base, 79 OiPDManager, 157
notSelectable() OiPlanning, 132
Base, 79 OiPlElement, 142
OiPolygon, 126
OAM, 8
OiProductDB, 160
OAS, 8
OiProgInfo, 140
Object, 11
OiPropertyObj, 153
Object model, 8
oiReplace(), 115
object2Article()
OiRotation, 127
OiPDManager, 158
oiSetCheckString(), 115
objInLevel()
OiSphere, 128
OiLevel, 165
OiSurface, 131
OCD, 8
OiSweep, 129
ODB, 8
oiTable(), 115
2D Representation and ODB, 86
OiUtility, 153
OEX, 8
OiWall, 166
OFF file, 200
OiWallSide, 166
OFML
onCreate()
Concepts, 10
OiPlElement, 145
Features, 7
onRotate()
Overview, 8
OiPart, 152
OFML database, 8
onTranslate()
oiApplPaste(), 110
OiPart, 152
OiBlock, 118
Open-form areas, 131
oiClone(), 110
oiCollision(), 111 Pi, 79
oiCopy(), 111 PICK, 105
oiCut(), 111 Planning check, 101
OiCylinder, 119 Planning element, 142
oiDialog(), 111 Planning environment, 135, 164
oiDump2String(), 112 Planning hierarchy, 132
OiEllipsoid, 120 Planning limit, 133, 135
oiExists(), 113 Planning mode, 165
OiFrame, 121 Polygon, 124, 126
oiGetDistance(), 113 Price, 100
oiGetNearestObject(), 113 Primitive, 117
oiGetRoots(), 113 Procedure, 168
oiGetStringResource(), 113 Product Data, 99

228

<!-- Page 231 -->

Product Data Management, 156 Difference compared to method, 15
Product data management, 139 explicit call, 85
Product data model, 167 predefined, 103
Product database, 204 user-defined, 103
Program Access, 98
Sales region, 133
Program Information, 140
SAP/R3, 156
Program information, 136
Scaling of geometries, 126
Property, 14, 89
Scene, 12
Definition format, 207
Selectability, 79
Property Information, 94
selectable()
propsChanged()
Base, 79
OiOdbPlElement, 155
Selection criterion, 168
Property, 93
SENSOR, 108
Quboid, 118 setAlignment()
OiGeometry, 118
Reference Types, predefined
setArticleSpec()
CFunc, 31
Article, 99
Func, 31
OiOdbPlElement, 154
Hash, 42
OiPart, 151
List, 38
OiPlElement, 146
String, 31
setBorder()
Type, 30
OiPlanning, 135
Vector, 36
setChanged()
Relational database, 115
Base, 81
remove()
setCMaterial()
MObject, 78
Material, 89
REMOVE ELEMENT, 104
OiPlanning, 136
removeProperty()
OiProgInfo, 141
Property, 91
setCutable()
removeValid()
Base, 80
Base, 80
setDataBasePath()
OiPropertyObj, 153
OiProductDB, 161
Resolution, 81
setDefaultHeight()
Resource, 204
OiLevel, 165
Restoring an instance from a dump representa-
setDepth()
tion, 115
OiPart, 149
Root object, 113
OiPlElement, 143
ROTATE, 106
setErrorLog()
rotate()
OiPlanning, 135
Base, 83
setExtPropOffset()
rotated()
Property, 91
OiPlElement, 148
setHeight()
rotateValid()
OiPart, 149
OiPlElement, 148
OiPlElement, 143
Rotation, 83
setLanguage()
Rotational body, 127
OiPlanning, 133
Rule, 10, 15, 85, 103

229

<!-- Page 232 -->

setMatCat() OiPDManager, 158
OiGeometry, 118 setWidth()
setMethod() OiPart, 149
Complex, 96 OiPlElement, 143
setOdbType() setXArticleSpec()
OiOdbPlElement, 154 Article, 100
setOrderID() OiPDManager, 159
Article, 98 show()
setOrigin() Base, 81
OiPart, 149 SPATIAL MODELING, 106
OiPlElement, 143 Sphere, 128
setPasteMode() START DUMP, 107
Complex, 96 START EVAL, 107
setPDManager() startCollCheck()
OiPlanning, 139 OiProgInfo, 142
setPlanningWall() Structure of Order Lists, 98
OiLevel, 165
Table, external, 204
setPlProgram()
Text output, 114
OiPlElement, 143
Text resource, 204
setPosition()
TIMER, 108
Base, 82
Topology
setProgram()
Name space, 13
OiPlanning, 134
Scene, 12
setPrograms()
topological independence, 11
OiProductDB, 161
TRANSLATE, 105
setPropPosOnly()
translate()
Property, 91
Base, 83
setPropState()
translated()
Property, 94
OiOdbPlElement, 155
setPropValue()
OiPlElement, 147
OiOdbPlElement, 155
translateValid()
Property, 93
OiPlElement, 147
setRegion()
Translation, 83
OiPlanning, 133
Type, 10
setResolution()
abstract, 10
Base, 81
Uniqueness, 10
setRtAxis()
Type identity, 77
Base, 84
setTempArticleSpec()
unMeasure()
Complex, 96
Base, 82
setTrAxis()
UNPICK, 105
Base, 83
setUnchanged()
varCode2PValues()
Base, 82
OiProductDB, 162
setupProperty()
Visibility, 81
Property, 89
setupProps()
Wall, 164

230