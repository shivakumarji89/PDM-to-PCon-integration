# oap_1.6.1-en

> Auto-generated from oap_1.6.1-en.pdf for AI consumption.

---


<!-- Page 1 -->

# OAP

# OFML Aided Planning

# Version 1.6

### 1st revised version

Thomas Gerth, EasternGraphics GmbH (Editor)

August 19, 2025

<!-- Page 2 -->

Legal Notice

Copyright ' 2025 EasternGraphics GmbH. All rights reserved.
This work is copyright. All rights are reserved by EasternGraphics GmbH. Translation, reproduction
or distribution of the whole or parts thereof is permitted only with the prior agreement in writing of
EasternGraphics GmbH.
EasternGraphics GmbH accepts no liability for the completeness, freedom from errors, topicality or
continuity of this work or for its suitability to the intended purposes of the user. All liability except in
the case of malicious intent, gross negligence or harm to life and limb is excluded.
All names or descriptions contained in this work may be the trademarks of the relevant copyright owner
and as such legally protected. The fact that such trademarks appear in this work entitles no-one to
assume that they are for the free use of all and sundry.

<!-- Page 3 -->

# Contents

1 Introduction 4

2 Basics 4
2.1 Technology . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
2.2 Terms . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
2.3 Other issues . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6

3 General rules and definitions 7
3.1 Regulations regarding the format . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
3.2 Table descriptions and field types . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
3.3 Language-specific data elements . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
3.4 Regulations regarding storage . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
3.5 Regulations regarding persistency of articles . . . . . . . . . . . . . . . . . . . . . . . . . . 11

4 The Tables 12
4.1 OAP types . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 13
4.1.1 The Type table . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 13
4.1.2 The Mapping tables . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 13
4.1.3 Determination of the appropriate mapping entry . . . . . . . . . . . . . . . . . . . 14
4.2 The NumTripel table . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15
4.3 General information . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15
4.4 Attach areas . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15
4.5 Matching attach areas . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15
4.6 Interactors. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 16
4.7 Actions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 20
4.8 The Tables for the action parameters . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 22
4.8.1 Action Choice. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 22
4.8.2 PropChange . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 23
4.8.3 PropEdit2 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 24
4.8.4 DimChange . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 26
4.8.5 CreateObj . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 27
4.8.6 MethodCall . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 28
4.8.7 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 29
Message
4.8.8 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 29
ExtMedia
4.9 Object definitions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 30
4.10 Texts. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 31
4.11 Images . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 31
4.12 Version information . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 32

1

<!-- Page 4 -->

A OAP expressions 33
A.1 General definitions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 33
A.2 Supported data types . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 33
A.2.1 Error . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 33
A.2.2 Null . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 33
A.2.3 Int . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 33
A.2.4 Float. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34
A.2.5 Symbol . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34
A.2.6 String . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34
A.2.7 Sequence . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34
A.2.8 Name . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34
A.2.9 Numeric types . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34
A.2.10 Boolean types . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34
A.3 Lexical structure . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34
A.3.1 Operators . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 35
A.3.2 Literals . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 35
A.4 Syntax of expressions. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 36
A.4.1 Precedence and associativity of operators . . . . . . . . . . . . . . . . . . . . . . . 36
A.4.2 Expressions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 37
A.4.3 Conditional evaluation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 37
A.4.4 Logical OR operator . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 38
A.4.5 Logical AND operator . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 38
A.4.6 Bitwise combinations. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 38
A.4.7 Operators to test for equality . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 38
A.4.8 Relational operators . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 39
A.4.9 Shift operators . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 39
A.4.10 Binary arithmetic operators . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 40
A.4.11 Unary arithmetic operators . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 40
A.4.12 Operators for bitwise and logical negation . . . . . . . . . . . . . . . . . . . . . . . 40
A.4.13 Primary expressions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 41
A.4.14 Funktion call . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 41
A.4.15 Execution of MethodCall actions . . . . . . . . . . . . . . . . . . . . . . . . . . . . 41
A.4.16 Access to property values . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 42
A.4.17 Placeholder . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 43
A.4.18 Literals . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 43
A.4.19 Identifier . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 43

2

<!-- Page 5 -->

B Functions 44
B.1 Mathematical functions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 44
B.2 Type conversion functions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 46
B.2.1 Conversion to Int . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 46
B.2.2 Conversion to Float . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 46
B.2.3 Conversion to Symbol . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 47
B.2.4 Conversion to String . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 47

C Modification history 49

# References

[article] The OFML Interfaces Article and CompositeArticle (Specification).
EasternGraphics GmbH
[dsr] Data Structure and Registration (DSR) Specification. EasternGraphics GmbH
[mt] OFML Metatypes (MT) Specification. EasternGraphics GmbH
[ofml] OFML – Standardized Data Description Format of the Office Furniture Industry.
Version 2.0, 3rd revised edition. Industrieverband Bu¨ro und Arbeitswelt e. V. (IBA)
[property] The OFML Interface Property (Specification). EasternGraphics GmbH

The specifications are available via the pCon Download Center in the category OFML Specications:
https://download-center.pcon-solutions.com

3

<!-- Page 6 -->

# 1 Introduction

OFML Aided Planning describes concepts, techniques and corresponding data tables, which should enable
a largely uniform data creation and implementation of planning techniques (inter–product rules) both in
online and offline applications.
OAPrepresentsanadditionallayerontopoftheconventionalOFMLdata[ofml]. Amongotherthings,you
can refer to the properties of article instances. With this, OAP data creation can be linked to metadata
creation [mt], for example.
Certainconceptsthatwerepreviouslyusedtoimplementplanningtechniquesinofflineapplications,such
as OLAYER–based snapping methods, will be replaced by OAP in the future.
Note:
A feature described in this specification which is not yet supported in the current applications of East-
ernGraphics is highlighted in gray.

# 2 Basics

### 2.1 Technology

OAP integrates the following techniques:

Interactors
(cid:136)
Interactorsaretwo-dimensionalgraphicalsymbolsthataredrawnbytheapplicationoveranobject 1
and which are linked to one ore more → actions to be performed when the interactor is selected by
2
the user , allowing the user to modify the planning or to get some information.
Interactors are object-specific. When an object is selected, the interactors are displayed which are
defined for the object and which are valid in the current planning context.
The size of the interactor symbols does not change depending on the distance of the camera to the
object.
It can be specified in the OAP data whether an interactor may be hidden by other objects or not.
In addition, visibility areas can be defined for the interactor symbols so that they are visible only
from certain (reasonable) angles.
There is a distinction between 2D and 3D interactor symbols:
– Independent of the camera perspective, 2D symbols always are parallel to the image plane, so
they are not subject to any perspective distortion.
– 3D symbols have a defined orientation in space, thus, depending on the camera perspective,
this results in a perspective distortion.
3D symbols can and should be used in situations where, when using a 2D symbol, the meaning
of the interactor would not be clearly recognizable in every camera perspective, e.g. arrows to
illustrate a direction of movement.
Note:
(Application)InteractorswerealreadysupportedinpCon.planner8beforeOAP,withtheinteractors
to be defined directly in the OFML data, see Application Note AN-2013-001. In the context of
OAP, however, the interactor concept described in the mentioned Application Note is adapted and
significantly expanded 3 .

1 graphicalrepresentationofaproduct,moreonthetermobjectseenextsection
2
Theselectionisdonebyclickingontheinteractorsymbolandiscalledalsotheactivationofthatinteractor.
3
Perspectively,theinteractorsdescribedintheApplicationNotebecomeobsolete.

4

<!-- Page 7 -->

Actions
(cid:136)
For certain events, e.g. the activation of an → application interactor by the user, actions can be
defined. An action specifies the functionality to be performed when the event occurs.
In conjunction with → attach areas, it is also possible to implement inter-product rules, which
4
currently are realized based on metadata .
(cid:136) Smart attach areas
Smart attach areas extend the concept of conventional OFML attach points:
Inadditiontopoints,alsolinesandareascanbespecified,optionallywitharaster. Furthermore,
the area can be linked with actions (see below) to be executed if the attach area was used to
connect two objects or if this connection is broken up again.
With smart attach areas, in the future snapping methods can/will be supported, which
currently are implemented in pCon.planner on the basis of OLAYERs D2SNAP resp.
ATTACH & ORIGIN .

### 2.2 Terms

The following terms of fundamental relevance are used in this document:

(cid:136) Article vs. article variant
An article (synonym: product) is a commodity that can be produced or is produced by a manufac-
turer or supplier and/or is offered for sale.
If some of the properties of an article can be specified by the buyer or the user of the OFML
application, this is referred to as a configurable article. The specific values of an article with
regard to its configurable properties then is referred to as an article variant (synonym: article
configuration).
Within a manufacturer/supplier, an article uniquely is identified by an alphanumeric code, the
article number. The values of the configurable properties are coded in the variant code, where
different schemes can be applied.
Since most articles are configurable, this document normally uses only the term article for the sake
of simplicity, even though, in the case of a configurable article, actually the term article variant is
meant. Only when a distinction is mandatory, the term article variant is used explicitly.
(cid:136) Article representation vs. OFML instance
An article representation (synonyms: planning element, object) is the object that graphically rep-
resents an article in a planning system or a configuration system.
The configuration of a (configurable) → article is carried out based on OFML properties. For this
purpose, an OFML article instance (short OFML instance) has to be created. OFML instances also
are required to determine various article information (texts, prices, etc.).
An OFML instance also includes a graphical representation of the article. However, for technical
reasons,OFMLinstancesnormallyarenotusedas→articlerepresentationsintheplanningsystem.
In this case, in order to configure an article or to determine article information, an OFML instance
(not visible to the user) has to be created temporarily.
In the online applications (based on the EAIWS), an article has two representations: a graphical
one in the client (planning element) and a commercial one in the basket, which is managed by the
server. For this reason, in difference to the planning element, the representation in the basket of
the server is called the basket instance. Also, the server is responsible for creating a (temporary)
OFML instance for a basket instance, if this is necessary to fulfill a request from the client.
(cid:136) Active vs. passive planning element
When inserting a new element into the planning or when removing a planning element or when
moving a planning element, 2 roles can distinguished that planning elements play: The element
4 Articlepolymorphismandintra-productrulescanandshouldcontinuetobeimplementedusingmetadata.

5

<!-- Page 8 -->

thatisinserted, deletedormovedplaystheactiveroleandaccordinglyiscalledtheactive planning
element. The other elements play a passive role and accordingly are referred to as passive planning
elements.
In particular, this distinction is relevant with respect to the attach areas: some of the attach areas
of a planning element only can/should be used if the element plays the active role, others only if it
plays a passive role. Respectively, the attach areas also are referred to as active and passive, where
there may be attach areas that can be used in both roles.

### 2.3 Other issues

(cid:136) Proximity
A proximity relationship (synonym: connection) between two planning elements exists if there
is (at least) one pair of attach areas of the two elements which match one another logically and
geometrically.

(cid:136) Dependancy on variants
5
DependenciesintheOAPdataonanarticlevariantarerepresentedonthebasisofOFMLproperties .
For this purpose, the so-called Property variant code (abbreviated PropVarCode) is introduced,
which encodes the current values of the OFML properties of an article variant (for details see field
type PVC in section 3.2):

<Property>=<Value>;<Property>=<Value>;...

In the OAP tables (section 4), fields are provided in which can be specified either a (partially
determined) PropVarCode or an expression that operates with OFML properties.
One consequence is that, in order to evaluate the OAP data for a given article variant, its Prop-
VarCode must be known. The PropVarCode has to be retrieved from the OFML instance of the
6
article .
In order to ensure a good performance, it is the responsibility of the applications to minimize the
number of OFML instance creations by using suitable caching resp. persistence techniques.
(cid:136) OAP types
An OAP type comprises the set of all articles resp. article variants which, in the context of
OAP, have the same features and should be treated equally. OAP types are defined in table Type
(see section 4.1.1).
Correspondingmappingtablesareusedtoassignspecificarticlesresp. articlevariantsorevenmeta
types to a specific OAP type.

5
Thus,OAPdatamaybesetupontopof,e.g.,metatyp-baseddataorspeciallyprogrammedOFMLdata.
6
ThisisdonebymeansofnewmethodgetPropVarCode(pState(Int))ofbaseclassOiPlElement,wherevalue0istobe
used for the status parameter, so that the invisible (and in part graphics-relevant) properties also are represented in the
code.

6

<!-- Page 9 -->

# 3 General rules and definitions

### 3.1 Regulations regarding the format

CSV tables (comma separated values) are used as the physical exchange format between OFML conform
applications. The following regulations apply for this:

1. Eachofthetablesdescribedbelowisincludedinexactlyonefile. Thefilenameismadeoftheprefix
oap_ , the specified table name and the suffix .csv where the table name is written completely in
small letters.
7
2. UTF-8 is used as the character set . Optionally, the byte order mark can be specified at the
beginning of the file.
8
3. Each line of the file represents a data record .
Blank lines, i.e. lines consisting of zero or several blank characters (U+0020) or tabulators
(U+0009), are ignored.
Lines starting with a number sign (’ # ’=U+0023) are interpreted as a comment and are ignored,
too.
4. The representations of the individual fields of a data record are separated from each other by a
semicolon (’ ’=U+003B).
;
5. ThevalueofafieldconsistsofzeroormoreUnicodecharacterswithavalidUTF-8encoding,except
for the control characters U+0000..U+001F as well as U+007F..U+009F.
6. The representation of a field is derived from the value of the field replacing each quotation mark
(’"’=U+0022)bytwoquotationmarksandenclosingtheresultingstringinquotationmarks. Ifthe
valueofafielddoesnotstartwithaquotationmarkanddoesnotcontainasemicolon(’;’=U+003B),
the value itself (i.e. without any modifications) can be used as the field representation.

### 3.2 Table descriptions and field types

In the table descriptions, a field of a data record is specified by the following attributes:

(cid:136) Number
(cid:136) Name
9
(cid:136) Mark, whether the field belongs to the primary key of the table
(cid:136) Field type (see below)
10
(cid:136) Maximum length of the field (number of characters)
(cid:136) Mark, whether the field has to be filled (obligatory field)

11
In key fields of a table, there must not be two values that differ only in spelling .

7
ThenormalformshouldbeNFC(NormalizationFormCanonicalComposition).
8
AlineisterminatedeitherbyanLFcharacter(U+000A)orbyasequenceofCR(U+000D)andLF.
9 Foragivenprimarykeytheremaybeonlyonerecordinthetable.
10
WhileinprincipletherearenorestrictionsinCSVdatarecordsconcerningindividualfieldlengths,forcertainfieldsof
datatypeCharmaximumpossibleresp. reasonablelengthsresultingfromtheintendedpurposearespecifiedhere. Moreover,
indatacreationfurtherrestrictionsthatareimposedbytheprogramusedinthedatacreationprocessshouldbeobserved.
11 withrespecttoupperandlowercase

7

<!-- Page 10 -->

The following field types are defined:

Text Text
All characters according to regulation 5 above are allowed. except the non-breaking spcae
(U+00A0) and the soft hyphen (U+00AD).
Char Character string
All characters according from the ASCII character set are allowed.
PVC Property variant code
In a property variant code, properties and their values are represented in the form
<property_key>=<property_value>
with individual property representations being separated by a semicolon (’ ; ’=U+003B).
Property keys are specified without a preceding ’ @ ’ character (U+0040).
Values are represented according to the rules for literal OFML constants.
ApropertyvariantcodedoesnotnecessarilyhavetoincludeallthepropertiesofagivenOFML
instance, but, on the other hand, may contain non-visible properties.
Lang Language code
The code consists of the two-digit language code according to ISO 639-1 and the two-digit
country resp. region code according to ISO 3166-1 (ALPHA-2), separated by a hyphen
12
(U+002D) .
The specification of the region code is optional (see section 3.3).

Examples:
f”ur amerikanisches English
en-US
f”ur britisches English
en-GB
If a data element can be used for any language, then the corresponding field must be empty.
Symbol Symbol
All alphanumeric characters from the ASCII character set (’0’..’9’=0x30..0x39,
’A’..’Z’=0x41..0x5A, ’a’..’z’=0x61..0x7A) are allowed as well as the underscore (’_’=0x5F),
but the first character must not be numeric.

ID Identifier
All alphanumeric characters from the ASCII character set (’0’..’9’=0x30..0x39,
’A’..’Z’=0x41..0x5A, ’a’..’z’=0x61..0x7A) are allowed as well as the minus sign (’-’=U+002D)
and the underscore (’_’=U+005F).
13
An identifier everywhere must be used in the same spelling .
OID Objekt identifier
An object identifier references a specific object or set of objects.
An object identifier either is a simple identifier that corresponds to field type ID or a hierar-
chical name in which the individual hierarchy levels represent a simple identifier and where
the levels are separated by a period (’ . ’=U+002E).
Hierarchical object names can be used if there are articles in the planning that are related
to each other in a parent-child relationship. The front name segments identify the higher
levels. If the parent-level identifier references a set of objects, the child-level identifier is
applied to all the objects in that set (product quantity).

12
This definition is based on the specification of the IETF for language tags. Lower case of the language code and
capitalizationofthecountrycodemustbeobserved!.
13 withrespecttoupperandlowercase

8

<!-- Page 11 -->

ID List comma-separated list of identifiers (field type ID)
OID List A comma-separated list of object identifiers (field type OID)

OFML A name according to OFML standard (part III) [ofml]
Possible names:
(cid:136) OFML package
(cid:136) OFML interface
(cid:136) fully qualified OFML type (class)

Int Non-negative integer
All numeric characters from the ASCII character set (U+0030..U+0039) are allowed.
Num Numerical value
AllnumericcharactersfromtheASCIIcharacterset(U+0030..U+0039)areallowedaswellas
the decimal point (’ - ’=U+002E), where the decimal point only may occur once. Optionally,
a minus sign (’ ’=U+002E) can be used at the first position.
-
Bool Boolean value
’1’ – true, ’0’ – false
NumExpr Numerical expression
Itisexpectedthattheresultoftheevaluationoftheexpressionisanumericalvalueaccording
to field type Num.
More on expressions see below.

BoolExpr Boolean expression
It is expected that the result of the evaluation of the expression is a boolean value:
(cid:136) Theresultoftheevaluationoftheexpressionisconsidered(unambiguously)trueifeither
ithasanumerictypeandthevalueisnonzero,oritisastringanditsvalueisanon-empty
string.
(cid:136) Theresultoftheevaluationoftheexpressionisconsidered(unambiguously)falseifeither
it has a numeric type and the value is equal to zero, or it is a string and its value is an
empty string.
(cid:136) In all other cases the result is undefined.
More on expressions see below.

Lexical structure and syntax of OAP expressions (field types NumExpr and BoolExpr) are described in
detail in appendix A 14 . To a large extent, OAP expressions correspond to the expressions specified in
part III of the OFML standard. In addition, OAP expressions (among others) offer the following special
features:

Thenames(keys)oftheOFMLpropertiesoftheactiveplanningelement(andpossiblyotherobjects)
(cid:136)
can be used as variables.

Function
(cid:136)
methodCall(<Action-ID>)
15
can be used in order to call OFML methods. The argument of the function is the ID of an action
of type MethodCall, which specifies the method call. (For details see A.4.15.)
14
Thedatatypesdescribedtherearenotidenticaltothefieldtypesdescribedhere.
15
oranexpressionyieldinganID

9

<!-- Page 12 -->

If errors occur when evaluating expressions (for example, syntax errors or references to non-existent
properties), the following rules apply:

For field type NumExpr value 0.0 is assumed.
(cid:136)
For field type BoolExpr, the result is undefined (not unambiguously true or false).
(cid:136)
Foreachfieldofthistype,thespecificationoftherespectivetablesexplicitlydeterminesthebehavior
in the case of an undefined expression.

### 3.3 Language-specific data elements

16
The following provisions apply to the use of language and region codes in fields of type Lang :

(cid:136) Foreachtableentrywitha(non-empty)codeinthefieldoftypeLang,containingboththelanguage
code and the region code, there should also exist a table entry with a code containing only the
language code in question. This entry serves as fallback for applications that do not support the
region specific code.
(cid:136) Whichlanguage(region)isusedforthefallbackentrylieswithinthediscretionofthemanufacturer
resp. data creator.
(cid:136) If the contents of both table entries are identical, the entry with the region specific code can (and
should) be omitted.

Example:
IfatextresourceiscreatedforbothAmericanandBritishEnglish,andthefallbackfor en isthetext
17
inBritishEnglish ,thelanguagecode en-US isspecifiedinthelanguagefieldofthetableentrywith
thetextinAmericanEnglish,whileforthetableentrywiththetextinBritishEnglishthelanguage
code is given only as en .

When selecting a table entry from the entries that match a given search key (text ID resp. image ID),
the application then proceeds as follows:

1. An application in which language and region are set uses the entry with the appropriate code in
the language field that contains the language and the region code.
2. If there is no matching entry with the region specific code, or if only the language but not the
region is set in the application, then the entry will be used whose language field contains only the
respective language code.
3. If there also is no matching entry with the simple code in the language field (only consisting of the
language code), the entry with empty language field is used (if available) 18 .

### 3.4 Regulations regarding storage

By default, the tables are stored region specific in the relevant OFML series:
<data>/($manufacturer)/($program)/($region)/($version)/oap
The tables have to be compiled into an EBase database named oap.ebase .
If cross-serial, manufacturer-wide logics have to be realized, the OAP data has be created and stored in
a specific series of the manufacturer (e.g. global). Then, in the registration files of the relevant product
series this series has to be referenced by means of key oap_program 19 .
16
currentlythisconcernstablesExtMedia,TextandImage,fieldLanguage
17
assumingthattheOFMLdataismainlyusedinEurope
18
Fortexts,alanguagealwaysshouldbespecified,forimagesandvideos,however,thelanguagefieldusuallyisempty.
19 Thesyntaxofthiskeycorrespondstothesyntaxforthekeycatalogs,i.e. ::($manufacturer)::($program)::

10

<!-- Page 13 -->

### 3.5 Regulations regarding persistency of articles

In order to be able to process the articles in the online applications and for high-performance processing
inpCon.planner,value STATECODES hastobespecifiedintheregistrationdataforkey persistency_form .
Accordingly,thestateofallobjects(articles)hastobecompletelydescribedbythestatecodesdefinedin
20
OFMLinterfaceArticle. Thisalsoappliestoanypartialplannings(planninggroups)thatmaybeused .

20 Thus,ifapartialplanningdoesnotrepresentarealarticles,ithastobecreatedasaso-calledpseudo article.

11

<!-- Page 14 -->

# 4 The Tables

Version
FormatVersion
Action
DimChange
Action
Condition
Article2Type
ID
Type
Dimension
Parameter
ManufacturerID ActionChoice Condition
Objects
SeriesID Separate
ID ThirdDim
ArticleID
VarType Title Property
Variant ViewType Multiplier
Argument Precision
TypeID
ListID
PropChange
Metatype2−
ActionList
Type
PropEdit− ID
ID Type
Props
Manufacturer
Property
Position
Series
Value
Condition ID
MetatypeID
Actions Property
VarType
TextID
Condition
Variant
ImageID StateRestr PropEdit2
TypeID
ID
PropEdit−
Title
Type Image Classes
Properties
Classes
TypeID ID ID
GeneralInfo PropClass
Language
PropChange− DPR Condition
Actions
File StateRestr ExtMedia
ActiveAttAreas
PassiveAttAreas ID
Interactors Type
Media
Text
ID
Interactor Language CreateObj
Text
Interactor
ID
Condition
Parent
NeedsPlanMode
ArtSpecMode
Actions Object
Package
SymbolType
Article
SymbolSize ID VarCode
Category PosRotMode
Argument1 PosRotArg1
Argument2 PosRotArg2
Symbol− Argument3 PosRotArg3
NumTripel
Display
ID
X
Interactor MethodCall
HiddenMode Y
Z
OffsetType Message ID
Type
Offset
Direction ID Context
Method
ViewAngle ArgType
Arguments
OrientationX Argument

Figure 1: Table Overview

Primarykeyfieldsarehighlightedinbold. Fieldswhicharenotmandatoryareindicatedinitalics.

12

| Version |
| --- |
| FormatVersion |

| Action |
| --- |
| Action
Condition
Type
Parameter
Objects |

| DimChange |
| --- |
| ID
Dimension
Condition
Separate
ThirdDim
Property
Multiplier
Precision |

| Article2Type |
| --- |
| ManufacturerID
SeriesID
ArticleID
VarType
Variant
TypeID |

| ActionChoice |
| --- |
| ID
Title
ViewType
Argument
ListID |

| PropChange |
| --- |
| ID
Type
Property
Value |

| Metatype2−
Type |
| --- |
| Manufacturer
Series
MetatypeID
VarType
Variant
TypeID |

| ActionList |
| --- |
| ID
Position
Condition
Actions
TextID
ImageID |

| PropEdit−
Props |
| --- |
| ID
Property
Condition
StateRestr |

| PropEdit2 |
| --- |
| ID
Title
Properties
Classes |

| PropEdit−
Classes |
| --- |
| ID
PropClass
Condition
StateRestr |

| Type |
| --- |
| TypeID
GeneralInfo
PropChange−
Actions
ActiveAttAreas
PassiveAttAreas
Interactors |

| Image |
| --- |
| ID
Language
DPR
File |

| ExtMedia |
| --- |
| ID
Type
Media |

| Text |
| --- |
| ID
Language
Text |

| Interactor |
| --- |
| Interactor
Condition
NeedsPlanMode
Actions
SymbolType
SymbolSize |

| CreateObj |
| --- |
| ID
Parent
ArtSpecMode
Package
Article
VarCode
PosRotMode
PosRotArg1
PosRotArg2
PosRotArg3 |

| Object |
| --- |
| ID
Category
Argument1
Argument2
Argument3 |

| Symbol−
Display |
| --- |
| Interactor
HiddenMode
OffsetType
Offset
Direction
ViewAngle
OrientationX |

| NumTripel |
| --- |
| ID
X
Y
Z |

| MethodCall |
| --- |
| ID
Type
Context
Method
Arguments |

| Message |
| --- |
| ID
ArgType
Argument |

<!-- Page 15 -->

### 4.1 OAP types

4.1.1 The Type table

Table name: Type
Obligatory table: yes

No. Name Key Type Length Oblig. Explanation
1. TypeID X ID X ID of the OAP type
2. GeneralInfo ID General information
3. PropChangeActions ID List Property change actions
4. ActiveAttAreas ID List Active attach areas
5. PassiveAttAreas ID List Passive attach areas
6. Interactors ID List Interactors

Remarks:

(cid:136) The ID in field 2 refers to table GeneralInfo .
(cid:136) The identifiers in field 3 refer to table Action .
The PropChangeActions are executed after a property of the article has been changed in the
property editor of the application. They are not executed if a property change took place as
part of an action of types PropValue and PropEdit2.
The actions are executed in the order of the identifiers!
(cid:136) The identifiers in fields 4 and 5 refer to table AttachArea.
Theactiveattachareasareusediftheplanningelementrepresentingthearticleplaystheactive
role. Accordingly, the passive attach areas are used in case of a passive role. (Correspondingly,
an attach area that is relevant in both roles has to be referenced in both fields.)
If no active attach areas are specified, the article can only be placed freely, i.e., the snapping
mechanism of the application does not take effect. If no passive attach areas are specified,
it is not possible to attach other articles to the article using the snapping mechanism of the
application.

(cid:136) The identifiers in field 6 refer to table Interactor.

4.1.2 The Mapping tables

Table name: Article2Type
Obligatory table: no

No. Name Key Type Length Oblig. Explanation
1. ManufacturerID X Char 16 X Commercial manufacturer ID
2. SeriesID X Char 16 X Commercial series ID
3. ArticleID X Char X Base article number
4. VarType X Symbol X Type of variant specification
5. Variant X Char Variant specification
6. TypeID ID X ID of assigned OAP type

13

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | TypeID | X | ID |  | X | ID of the OAP type |
| 2. | GeneralInfo |  | ID |  |  | General information |
| 3. | PropChangeActions |  | ID List |  |  | Property change actions |
| 4. | ActiveAttAreas |  | ID List |  |  | Active attach areas |
| 5. | PassiveAttAreas |  | ID List |  |  | Passive attach areas |
| 6. | Interactors |  | ID List |  |  | Interactors |

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ManufacturerID | X | Char | 16 | X | Commercial manufacturer ID |
| 2. | SeriesID | X | Char | 16 | X | Commercial series ID |
| 3. | ArticleID | X | Char |  | X | Base article number |
| 4. | VarType | X | Symbol |  | X | Type of variant specification |
| 5. | Variant | X | Char |  |  | Variant specification |
| 6. | TypeID |  | ID |  | X | ID of assigned OAP type |

<!-- Page 16 -->

Table name: Metatype2Type
Obligatory table: no

No. Name Key Type Length Oblig. Explanation
1. Manufacturer X Char X OFML manufacturer ID
2. Series X Char X OFML series ID
3. MetatypeID X Char X Metatype ID
4. VarType X Symbol X Type of variant specification
5. Variant X Char Variant specification
6. TypeID ID X ID of assigned OAP type

In both mapping tables, field 5 can be used to assign OAP types to specific article variants. The type of
variant specification is defined in field 4. Currently the following 3 types are supported:

None The entry is valid for all article variants.
Field 5 is empty in this case (or any existing content is ignored).
21
Expr The variant is defined by a Boolean expression (which uses certain properties) .
22
PVC The variant is defined by a PropVarCode .
Usually, it is sufficient to specify a partially determined PropVarCode, which only encodes the
properties that are necessary to distinguish the article variants.
The mapping entries for a given article or metatype may use only either Expr or PVC to specify article
variants, and may include only one entry with value None in field 4!
The procedures for selecting the appropriate mapping entry are described in the following section.

4.1.3 Determination of the appropriate mapping entry

Thefirststepistodeterminethesetofalltableentrieswheremanufacturer,seriesandthearticlenumber
or the metatype ID match.
Table access fails if no matching table entry is found, or if the entries in the resulting set use different
types of variant specification (Expr and PVC), or if the resulting set contains more than one entry with
value None in field 4.
Variant specification via Boolean expression
From the entries determined in step 1, all entries with a variant specification are removed for which the
evaluation of the expression in field 5 does not yield definitely true.
Table access fails if the resulting set is empty or if it contains more than one entry with a variant
specification.
If the resulting set contains an entry with a variant specification and one without (None in field 4), the
entry with the article variant is used.

Variant specification via PropVarCodes
The (partially determined) PropVarCodes (field 5) of each of the entries with a variant specification
determined in step 1 will be compared with the PropVarCode of the currently treated article instance.
For each property, which is contained in both Codes, the corresponding values are compared with each
other.

21 Field5thenistreatedasafieldoftypeBoolExpr.
22 Field5thenistreatedasafieldoftypePVC.

14

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | Manufacturer | X | Char |  | X | OFML manufacturer ID |
| 2. | Series | X | Char |  | X | OFML series ID |
| 3. | MetatypeID | X | Char |  | X | Metatype ID |
| 4. | VarType | X | Symbol |  | X | Type of variant specification |
| 5. | Variant | X | Char |  |  | Variant specification |
| 6. | TypeID |  | ID |  | X | ID of assigned OAP type |

<!-- Page 17 -->

Two property values are considered equal if
both values are symbol literals and have the same symbolic value
(cid:136)
both values are string literals and both string literals represent the same character string
(cid:136)
(cid:136) both values are NULL
23
(cid:136) both values are numeric literals (integer or floating-point), have a valid value , and represent the
24
same numeric value
(See appendix A.3.2 for details on literals.)
If not all compared property values are equal, the table entry is removed from the set of entries to be
25
considered further .
Finally, the set is reduced to the table entries with the most matching property valuest 26 .
Table access fails if the resulting set does not contain exactly one entry.

### 4.2 The NumTripel table

A triple is used to indicate the coordinates of a position, rotation axes, translation vectors and other
three-dimensional parameters.
Triples are referenced from various tables of this specification.
Table name: NumTripel
Obligatory table: no

No. Name Key Type Length Oblig. Explanation
1. ID X ID X ID of the triple
2. X NumExpr (X) X value
3. Y NumExpr (X) Y value
4. Z NumExpr (X) Z value

### 4.3 General information

Not yet supported.

### 4.4 Attach areas

Not yet supported.

### 4.5 Matching attach areas

Not yet supported.
23
SeeappendixAfordetailsonthevalidrangesofnumericliterals.
A consequence of the regulation is that the results of the comparison is false if both values are invalid, even if they are
representedbythesamecharacterstring.
24 Theonlylimitationofthecurrentimplementationwhencomparingdecimalintegersandfloating-pointnumbersisthat
theamountofanyexponentmaynotbegreaterthan9999(inwhichcasethevalueisconsideredinvalid). Apartfromthat,
theexactdecimalvalueisalwayscomparedwithoutrestrictionofprecision.
25 Since no values can be compared for table entries without a variant specification (None in field 4), these entries are
includedinthesetoftableentriestobeconsideredfurther.
26
IfthesamepropertyoccursseveraltimesinaPropVarCode,thepropertyiscountedonlyonce.

15

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | ID of the triple |
| 2. | X |  | NumExpr |  | (X) | X value |
| 3. | Y |  | NumExpr |  | (X) | Y value |
| 4. | Z |  | NumExpr |  | (X) | Z value |

<!-- Page 18 -->

### 4.6 Interactors

Table name: Interactor
Obligatory table: no

No. Name Key Type Length Oblig. Explanation
1. Interactor X ID X ID of the interactor
2. Condition BoolExpr Validity condition
3. NeedsPlanMode BoolExpr <deprecated/obsolete>
4. Actions ID List X Actions
5. SymbolType Symbol X Type of interactor symbol
6. SymbolSize Symbol X Size of interactor symbol

Remarks:
The interactor is valid if field 2 is empty or if the evaluation of the expression specified in the field
(cid:136)
definitely yields true.
The identifiers in field 4 refer to table Action .
(cid:136)
The actions are executed in the order of the identifiers when the interactor is activated.
In doing so, an action is skipped if its execution condition is currently not met, or if it is otherwise
27
invalid . (Thecontextforevaluatingtheexecutioncondition(s)oftheactionsisupdatedafterthe
execution of each single action.)
28
An interactor is only displayed if (currently) there is at least one valid action .
If an error occurs when accessing the action parameters in the OAP database, or if the execution
of an action fails, the processing of the action list is aborted!
The processing of the action list is also aborted after an action of type SelectObj (see section 4.7).
(cid:136) The symbol of an interactor is a pictogram that illustrates the (main) effect of the interactor. In
the interest of a uniform design of the GUI of the applications, there is no provision in the OAP
to directly specify an image file for the symbol. Instead, an abstract, predefined symbol type is
specified (field 5). The application then uses an image matching the type to represent the symbol.
The position and, if necessary, the orientation and visibility range of the symbol is defined in the
table SymbolDisplay described below.
Certain actions (such as DimChange, see section 4.7) are executed in a special application mode in
which application-specific interactors (not defined in OAP) are used. The OAP interactors are not
visible during these modes.
Symbol types for interactors whose first action has to be an action that activates an application
mode, are marked with App in the following list.
Symboltypesforinteractorswhosefirstactioncanbeanactionthatactivatesanapplicationmode,
are marked with (App).
The following symbol types are defined:
Add Adding planning elements
Attention Output of important information (using an action of type Message)
(App)
ChangeDimHorizontal Changing horizontal dimension
(possibly using an action of the type Dimchange)
ChangeDim2Left (App) Decreasing horizontal dimension
(possibly using an action of the type Dimchange)
ChangeDim2Right (App) Increasing horizontal dimension
(possibly using an action of the type Dimchange)
27
e.g.,unsupportedactiontypeorfalseormissingactionparameters
28
Inearlyphasesofprojectdevelopment,dummyactiontypeNoActionmayneedtobeused.

16

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | Interactor | X | ID |  | X | ID of the interactor |
| 2. | Condition |  | BoolExpr |  |  | Validity condition |
| 3. | NeedsPlanMode |  | BoolExpr |  |  | <deprecated/obsolete> |
| 4. | Actions |  | ID List |  | X | Actions |
| 5. | SymbolType |  | Symbol |  | X | Type of interactor symbol |
| 6. | SymbolSize |  | Symbol |  | X | Size of interactor symbol |

<!-- Page 19 -->

ChangeDimVertical (App) Changing vertical dimension
(possibly using an action of the type Dimchange)
(App)
ChangeDimDown Decreasing vertical dimension
(possibly using an action of the type Dimchange)
(App)
ChangeDimUp Increasing vertical dimension
(possibly using an action of the type Dimchange)
Delete Removing planning elements
Duplicate Adding a copy of the active object
Edit Changing properties/settings, general
(see also Electrification, Lighting and Material)
Electrification Changing properties/settings related to electrification 29
FinishMode Finish a (temporary) mode programmed in the OFML data that was
activated by a previously used interactor
Flip Switching the front/back orientation of a planning element
(rotation about vertical axis by 180 degrees)
30
Lighting Changing properties/settings related to lighting/illumination
Material Changing material characteristics
OnOff Switching a functionality on/off 31
PosHorizontal Changing horizontal position
Pos2Left Moving to the left
Pos2Right Moving to the right
PosVertical Changing vertical position
PosDown Moving downwards
PosUp Moving upwards
RotateNY Rotation about negative Y axis (vertical axis, counterclockwise)
RotateNY90 Rotation by 90 degrees about negative Y axis
RotatePY Rotation about positive Y axis (vertical axis, clockwise)
RotatePY90 Rotation by 90 degrees about positive Y axis
App
StartDimChange Start an action of type DimChange
Video Playing a video
VisibilityOff Hide specific elements of the active object (e.g. doors) so that the
users can manipulate elements behind them
VisibilityOn Show elements of the active object that were previously hidden (see
symbol type VisibilityOff)
(cid:136) Field 6 specifies the desired abstract size of the interactor symbol. The exact dimensions of the
symbols (pictograms) for each abstract size grade are determined by the applications.
The following size grades are defined:
– small
– medium
– large
For a given symbol type, it is not necessary to have a pictogram in all sizes. The application then
uses the pictogram in the next larger or next smaller version.
29 e.g. settingsthatdeterminewhetherandatwhichpositionsockets,cableguides,supplylines,connectinglinesetc. are
tobeplanned
30
e.g. settingsthatdeterminewhetherandatwhichpositionluminaires/lampsofwhichtypearetobeplanned
31 Asthecurrentstate(on/off)cannotbeseenfromthesymbolitself,itshouldonlybeusediftheusercanseefromthe
graphicoftheconcernedobjectwhetherthefunctionalityisswitchedonornot(e.g. lighton/off,screenon/off).

17

<!-- Page 20 -->

Table name: SymbolDisplay
Obligatory table: no

No. Name Key Type Length Oblig. Explanation
1. Interactor X ID X ID of the interactor
2. HiddenMode X BoolExpr X Hidden mode
3. OffsetType X Symbol X Type of offset specification
4. Offset X Char X Offset of the symbol
5. Direction ID Orientation of the symbol
6. ViewAngle NumExpr Opening angle of the visibility range
7. OrientationX ID Orientation of X axis for 3D symbols

Remarks:
(cid:136) This table specifies the position, orientation and visibility range of the symbols of an Interactor.
(cid:136) The table can contain several entries for an interactor ID to represent different positions with
separate visibility ranges, e.g. to realize different representations for the front and rear view of an
object.
It is the responsibility of the data creator to ensure that in this case the visibility ranges do not
overlap, sothat, dependingonthecameraperspective, nottwo(ormore)symbolswillbedisplayed
for the interactor.
(cid:136) The mode in field 2 specifies whether the interactor symbol should be hidden by objects lying
32
between the position of the symbol and the camera position (user/observer) :
If the evaluation of the expression specified in the field definitely yields true, the symbol will be
hidden, otherwise it will not 33 .
Thepositionofthesymbolisdeterminedbyanoffsetrelativetothepositionoftheplanningelement
(cid:136)
to which the interactor is bound.
The specification of the offset can be done in two ways. The way used is indicated in field 3:
Tripel The 3 coordinates (x, y, z) are specified in an entry in table NumTripel (see section 4.2).
The ID of this entry has to be specified in field 4.
IfnoentrywiththeIDspecifiedinfield3isfoundintableNumTripel,thesymbolisplaced
at the position of the planning element.
Expr The offset is specified by an expression stored in field 4, which yields a Sequence of 3 Float
34
values . The expression may include method calls (function methodCall(), see A.4.15).
Iftheexpressioninfield4doesnotyieldasequenceof3Floatvalues,thesymbolisplaced
at the position of the planning element.
(cid:136) If at least one of the fields 5 and 6 is empty, the symbol is visible regardless of the camera perspec-
35
tive .
In order to avoid overloaded and confusing views, especially if an object has a lot of interactors, it
is recommended to restrict the visibility range of the symbols. In most cases, for example, it makes
sense that a symbol is only visible if the side of the object to which the symbol is attached also is
visible. The visibility range of a symbol is determined by a direction vector (field 5) starting from
the position of the interactor (field 4) and the opening angle relative to the direction vector (field
6): If the inside of the cone defined by the position of the symbol, direction vector and opening
angle,completelyorpartially,iscapturedbythecamerawiththecurrentcamerasettings,thenthe
36
symbol is visible .
32
Thisincludestheobjecttowhichtheinteractorisbound.
33
If the field is empty, the behavior is the same as before the field was introduced: If no visibility range is specified
(fields5and6),thesymbolishiddenbyobjectsinfront,otherwisenot.
34 forthedatatypeswhichcanbeusedinexpressions,seeappendixA.2
35
However, it is obscured by objects that lie between the position of the symbol and the camera position if the hidden
modeinfield2hasvaluetrue.
36 ifthehiddenmodeinfield2hasvaluefalseorifitisnotobscuredbyobjectsthatliebetweenthepositionofthesymbol
andthecameraposition

18

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | Interactor | X | ID |  | X | ID of the interactor |
| 2. | HiddenMode | X | BoolExpr |  | X | Hidden mode |
| 3. | OffsetType | X | Symbol |  | X | Type of offset specification |
| 4. | Offset | X | Char |  | X | Offset of the symbol |
| 5. | Direction |  | ID |  |  | Orientation of the symbol |
| 6. | ViewAngle |  | NumExpr |  |  | Opening angle of the visibility range |
| 7. | OrientationX |  | ID |  |  | Orientation of X axis for 3D symbols |

<!-- Page 21 -->

In order to specify a direction vector, an entry has to be created in table NumTripel and the ID
(cid:136)
of this entry has to be stored in field 5. The coordinates of the vector are relative to the local
coordinate system of the object to which the interactor is bound.

Forasymbolonthefrontofanobject,e.g.,thetriple [0.0, 0.0, 1.0] wouldindicatethatthe
symbol is oriented in the direction of the positive Z axis (forward-facing).
If no entry with the ID specified in field 5 is found in table NumTripel , the behavior is as in the
case that the field is empty, i.e., the symbol always is visible.
(cid:136) The angle in field 6 has to be givem in degrees in the range of 0 to 360.

For a symbol on the front of an object, e.g., with a forward-faced direction vector (field 5, see
example above), opening angle 180 would cause the symbol to be visible only if the front of the
object is also visible 37 .

(cid:136) If fields 5-7 are not empty and if an entry is found in table NumTripel for the ID specified in
field 7, the symbol is treated as a three-dimensional object (3D symbol). In all other cases, the
symbolistreatedasatwo-dimensionalobject,whichalwaysisdisplayedparalleltotheimageplane
(2D symbol).
38
The vector specified by the entry in table NumTripel referenced in field 7 defines the X axis of
thelocalcoordinatesystemofthe3Dsymbolwhoseoriginisatthesymbol’sposition(field4). The
39
Z axis of this coordinate system is determined by the direction vector (field 5) and the Y axis
40
results from the cross product of Z and X axis .
The image/pictogram associated with the type of the symbol (see field SymbolType in table
Interactor above) then is placed and oriented in such a way that it resides in the X-Y plane
of the 3D symbol, the origin (center) of the image matches the position of the symbol, and the X
axis of the image coincides with the X axis of the coordinate system of the symbol, see figure 2.

Y X = [0.0, 1.0, 0.0]

# + =

X Y

N = Z = [0.0, 0.0, 1.0]
Z (viewer)

a) Icon b) Pos./Orientation of interactor symbol c) Mapped symbol icon

Figure 2: Mapping of pictograms (icons) for 3D symbols

The image of a 2D symbol is placed and oriented in such a way that it resides in a plane parallel
to the image plane (projection plane), the origin (center) of the image matches the position of the
symbol, and the X axis of the image is pointing horizontally to the right.
The length of the vectors referenced in fields 5 and 7 must be greater than zero, otherwise an error
(cid:136)
is triggered and the behaviour of the application is undefined.

37
Rather,inpracticeanglesoflessthan180degreesmakesense.
38
Thecoordinatesarerelativetothelocalcoordinatesystemoftheobjecttowhichtheinteractorisbound.
39 Inthecaseofa3Dsymbol,thedirectionvectorisalsoreferredtoasthenormal,sinceitalsodefinestheplaneinwhich
thetwo-dimensionalimageofthepictogramlies.
40
If the vector for the X axis is not orthogonal to the normal, the application will normalize the vector. The vector for
theXaxismustnotbeparalleltothenormal. Ifthisisthecase,anerroristriggeredandthebehavioroftheapplication
isundefined.

19

<!-- Page 22 -->

### 4.7 Actions

Table name: Action
Obligatory table: no

No. Name Key Type Length Oblig. Explanation
1. Action X ID X Identifier of the action
2. Condition BoolExpr Execution condition
3. Type Symbol X Type of the action
4. Parameter ID (X) Parameter for the action
5. Objects OID List (X) Target objects

Remarks:
Theactionisexecuted(i.e. isvalid)iffield2isemptyoriftheevaluationoftheexpressionspecified
(cid:136)
in field 2 definitely yields true.
Furthermore, certain action types may have additional conditions that must be fulfilled for the
action to be considered valid.
These conditions, if any, are mentioned below for each action type.
(cid:136) Supported types (field 3) are:
ActionChoice
This is not an action in the true sense, but rather a list of options from which the user can
choose one. Selecting an option then causes the execution of one or more actions.
The ID in field 4 refers to table ActionChoice.
Thistableinturnrefersto table ActionList, wherethelistofselectableoptionsisspecified.
There, an option may have conditions that must be fulfilled for it to be considered valid.
AnactionoftypeActionChoiceisonlyvalid,apartfromtheconditioninfield2,if(currently)
there is at least one valid option.

CreateObj
The action creates an object.
The ID in field 4 refers to table CreateObj.
DeleteObj
The action removes the objects specified in field 5.
(Field 4 has no meaning for this action type.)
DimChange
The action allows for an interactive change of one or more dimensions of the active object.
The ID in field 4 refers to table DimChange.

Message
The action issues a message to the user.
The ID in field 4 refers to table Message .
An action of this type is only allowed for interactors with symbol type Attention!
MethodCall
The action calls an OFML method.
The ID in field 4 refers to table MethodCall .
If the method is an instance method, it is called on the objects specified in field 5. For class
methods, field 5 has no meaning.

20

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | Action | X | ID |  | X | Identifier of the action |
| 2. | Condition |  | BoolExpr |  |  | Execution condition |
| 3. | Type |  | Symbol |  | X | Type of the action |
| 4. | Parameter |  | ID |  | (X) | Parameter for the action |
| 5. | Objects |  | OID List |  | (X) | Target objects |

<!-- Page 23 -->

NoAction
Thistypedefinesadummyactionwhichdoesnotrequireanyfurtherdatatobespecifiedand
which is always valid.
Since these actions have no real effect, they should not be used in delivered OFML data, but
they can be useful in early stages of project development when, initially, only the interactor
symbols are to be created and positioned.
PropChange
The action assigns a (new) value or status to a property.
The ID in field 4 refers to table .
PropChange
PropEdit2
The action executes a dialog for entering or selecting property values.
The ID in field 4 refers to table PropEdit2 .
The set of objects resulting from field 5 may contain only one object, otherwise the action
has no effect.
SelectObj
The action selects the object specified in field 5.
(Field 4 has no meaning for this action type.)
The set of objects resulting from field 5 may contain only one object, otherwise the action
has no effect.
Attention:
The action results in a change of the active object (see object category Self, section 4.9).
Therefore, the processing of the action list of an interactor (see 4.6) is aborted after this
action! therefore, actions of this type should always be the last action in the action list of an
interactor.
ShowMedia
The action displayes an (external) media content to the user.
The ID in field 4 refers to table ExtMedia.
(cid:136) In fields of type ID List specifying a list of action identifiers, there has to be only one action of a
41
type involving an interaction with the user .
Furthermore, the following regulations also apply to these actions:

– Actions of types DimChange, Message and ShowMedia have to be the single action in the list
and may only be used in action lists of interactors. (These actions always are executed, i.e.
any specified execution condition will be ignored.)
– Actions of type PropEdit2 have to be the last action in the list.
– ForactionsoftypesActionChoice,iftheinteractionisabortedbytheuser(withoutaselection),
possible subsequent actions are not executed.

Field 5 specifies the objects for which the action is to be performed.
(cid:136)
For action types ActionChoice, CreateObj, DimChange, Message and ShowMedia field 5 has no
42
meaning . The following applies to the other action types:
If an OID is a simple identifier (see field type OID), the identifier is used to access table Object in
order to determine the relevant set of objects.
For hierarchical names, the total set of the affected objects results from the product of the sets
at the individual hierarchy levels.
The action is executed for each of the specified objects in the specified order of the OIDs. If an
OID references more than one object, the order of execution within that set is undefined.
41 concerns: ActionChoice,DimChange,Message,PropEdit2andShowMedia
42 ThepossibleparentobjectsforactionsoftypeCreateObjarespecifiedintheparametertableCreateObj.

21

<!-- Page 24 -->

### 4.8 The Tables for the action parameters

4.8.1 Action Choice

Two tables are required to specify action choices: Table ActionChoice describes the general attributes
of an action choice (e.g. the appearance). Furthermore, this table refers to the list of selectable op-
43
tions, which is specified in table ActionList . In this table, names and/or images are assigned to the
actions/options.

Table name:
ActionChoice
Obligatory table: no

No. Name Key Type Length Oblig. Explanation
1. ID X ID X ID of the parameter set
2. Title ID Text ID for dialog title
3. ViewType Symbol X Type of view (appearance)
4. Argument (Char) (X) (conditional) parameter for the view type
5. ListID ID X ID of the action list

The ID in field 2 refers to table Text .
If the field is empty or no text can be determined for the ID, the choice dialog is displayed without a
title.
Currently, 2 view types (field 3) are supported:
List The selection options are shown in a list below each other, with each option represented by an
(optional) small image on the left and a text (name) on the right.
The size of the images should be geared to the size for the material images in property editors (see
[dsr]), i.e. 50 x 18 image points (width x height). But that is not mandatory. Ideally, however, the
images should be the same size for a given action choice.
If there is a image for at least one option, then the area reserved for the image remains empty for
options without an assigned image, i.e. the texts of all options are left-aligned.
In this representation form, there should always be a text for an option, since the images alone
usually are not meaningful due to the small size.
Field 3 is not relevant for this view type.
Tile The selection options are displayed in tiles of the same size next to and/or below each other. This
view type is intended for displaying options with larger images.
A tile consists of the image and an (optional) text below or right beside it.
Thedesiredtilesizeisspecifiedinfield4. (Thisrefersonlytothesizeoftheimage. Withtext, the
actual displayed tile correspondingly is larger.)
Currently, the following tile sizes are supported (image points, width x height):
small 50 x 50
medium 100 x 100
large 200 x 200
The image files for normal resolution displays are expected to be in exactly the size (in pixels)
determined by the tile size specified in field 4.

The above mentioned image dimensions are information in (logical) image points. For a good represen-
tation on high-resolution displays, image files with a correspondingly larger resolution (pixels) are to be
provided. For details see table Image (section 4.11).
43
ThetablebettershouldbenamedChoiceList. However,forasimplermigrationthepreviousnameisused,whichwas
introducedwhenonlyoneactioncouldbelinkedtoanoption.

22

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | ID of the parameter set |
| 2. | Title |  | ID |  |  | Text ID for dialog title |
| 3. | ViewType |  | Symbol |  | X | Type of view (appearance) |
| 4. | Argument |  | (Char) |  | (X) | (conditional) parameter for the view type |
| 5. | ListID |  | ID |  | X | ID of the action list |

<!-- Page 25 -->

An option without image and text is not displayed.
The ID in field 5 refers to the following table.

Table name: ActionList
Obligatory table: conditional (yes, if table ActionChoice exists)

No. Name Key Type Length Oblig. Explanation
1. ID X ID X ID of the action list
2. Position X Int X Position of the action in the list
3. Condition BoolExpr Validity condition
4. Actions ID List X Actions
5. TextID ID ID of the text
6. ImageID ID ID of the image

Remarks:
(cid:136) The list entry (option) is valid if field 3 is empty or if the evaluation of the expression specified in
the field definitely yields true.
(cid:136) The identifiers in field 3 refer to table Action .
The referenced actions themselves may be of type ActionChoice, i.e. a nesting of actions of type
44
ActionChoice is supported .
Besides that, no actions should be used which themselves include a user dialog.
To the execution of the actions apply the same regulations as to the actions of an interactor,
specifically:
The actions are executed in the order of the identifiers. In doing so, an action is skipped if its
execution condition is currently not met, or if it is otherwise invalid.
The option is only valid if (currently) there is at least one valid action.
If an error occurs when accessing the parameters of the referenced actions in the OAP database,
or if the execution of a referenced action fails, the processing of the action list is aborted and the
enclosing ActionChoice action fails!
The ID in field 5 refers to table (section 4.10). In this table, language-specific texts (names)
(cid:136) Text
for the action/option can be specified.
TheIDinfield6referstotableImage((section4.11). Inthistable, animage(icon)illustratingthe
(cid:136)
action/option can be specified 45 .
If required, also language-specific image files can be referenced in table Image.

4.8.2
PropChange

No. Name Key Type Length Oblig. Explanation
1. ID X ID X ID of the parameter set
2. Type Symbol X Type of change
3. Property Symbol X Property key
4. Value Char X Expression for value of change

44
Theconcreteimplementationintheuserinterfacecanvaryfromapplicationtoapplication.
45 whereseveralimagefileswithcorrespondingresolutionsfordisplayswithdifferentresolutionhavetobereferencedfor
oneimage(fordetailsseetableImage)

23

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | ID of the action list |
| 2. | Position | X | Int |  | X | Position of the action in the list |
| 3. | Condition |  | BoolExpr |  |  | Validity condition |
| 4. | Actions |  | ID List |  | X | Actions |
| 5. | TextID |  | ID |  |  | ID of the text |
| 6. | ImageID |  | ID |  |  | ID of the image |

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | ID of the parameter set |
| 2. | Type |  | Symbol |  | X | Type of change |
| 3. | Property |  | Symbol |  | X | Property key |
| 4. | Value |  | Char |  | X | Expression for value of change |

<!-- Page 26 -->

Remarks:

Following change types are defined:
(cid:136)
Value A (new) value is assigned to the property.
Theexpression 46 infield4mustyieldavaluethatmatchesthedatatypeoftheproperty.
Visibility The visibility of the property is changed.
The expression in field 4 must yield a boolean value (see field type Bool).
The value determines whether the property should be visible or not.
Editability The editability of the property is changed.
The expression in field 4 must yield a boolean value (see field type Bool).
The value determines whether the property should be editable or not.
(cid:136) Field 3 specifies the key of the property to be changed (without the preceding @ character).
The change is made for all objects affected by the action that possess this property.

4.8.3 PropEdit2

Table name: PropEdit2
Obligatory table: no

No. Name Key Type Length Oblig. Explanation
1. ID X ID X ID of the parameter set
2. Title ID Text ID for editor title
3. Properties ID (X) ID for PropEditProps
4. Classes ID (X) ID for PropEditClasses

Remarks:

(cid:136) The ID in field 2 refers to table Text.
If the field is empty or no text can be determined for the ID, the editor dialog is displayed without
47
a title .
(cid:136) ThepropertiestobeeditedarespecifiedintablePropEditProps(seebelow). TheIDfortheaccess
to this table is given in field 3.
If all properties of one or more property classes are to be edited, these classes are specified in table
PropEditClasses (see below). The ID for the access to this table is given in field 4.
Only one of the fields 3 or 4 may be empty.
Properties from classes that are referenced via table should not be specified in
(cid:136) PropEditClasses
table PropEditProps.

Table name: PropEditProps
Obligatory table: conditional (yes, if table PropEdit2 exists and contains references in field Properties)

No. Name Key Type Length Oblig. Explanation
1. ID X ID X ID of the parameter set
2. Property X Symbol X Key of the property
3. Condition BoolExpr Validity condition
4. StateRestr Symbol X Restriction regarding property state

Property keys (field 2) are to be specified without the preceding @ character.
46 onexpressionseeappendixA
47 Inthiscase,theapplicationshouldnotusethenameofthepropertyasafallback(ifonlyonepropertyisinvolved).

24

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | ID of the parameter set |
| 2. | Title |  | ID |  |  | Text ID for editor title |
| 3. | Properties |  | ID |  | (X) | ID for PropEditProps |
| 4. | Classes |  | ID |  | (X) | ID for PropEditClasses |

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | ID of the parameter set |
| 2. | Property | X | Symbol |  | X | Key of the property |
| 3. | Condition |  | BoolExpr |  |  | Validity condition |
| 4. | StateRestr |  | Symbol |  | X | Restriction regarding property state |

<!-- Page 27 -->

For fields 3 and 4 see below.

Table name: PropEditClasses
Obligatory table: conditional (yes, if table PropEdit2 exists and contains references in field Classes)

No. Name Key Type Length Oblig. Explanation
1. ID X ID X ID of the parameter set
2. PropClass X Char X Name of the class
3. Condition BoolExpr Validity condition
4. StateRestr Symbol X Restriction regarding property state

A property resp. class is used in the dialog only if field 3 (Condition) is empty or if the evaluation of the
expression specified in the field definitely yields true.
Note:
Since the conditions are not (re)evaluated during the dialog after a property change, they must not refer
to properties whose values can change themselves during the dialog!
In order to handle the dependency of the visibility of a property on other properties in general and in
particular on properties that are used in the dialog itself, an according value (not equal to None ) should
be specified in the following field 4.
Field 4 (StateRestr) indicates whether the property resp. the properties of the class should be displayed
in the dialog depending on the current property status. (The field is evaluated only for properties resp.
classes that are valid according to field 3.)
Currently, the following values are defined for field StateRestr:

None No restriction, i.e., the property resp. the properties of the class should be displayed
regardless of the current status.
Visible The property resp. the properties of the class should be displayed only if they are
48
currently visible .
VisibleEditable The property resp. the properties of the class should be displayed only if they are
currently visible and editable.
If, due to the validity conditions, only one property is suitable for use in the dialog, field StateRestr has
49
no meaning for this property, i.e., the property is displayed and can be changed by the user regardless
of its current status.
If, taking into account the conditions and the property status, only one property is to be displayed, only
theinputfieldortheselection(choice)listofthispropertyisdisplayedintheeditordialog. (Theproperty
name is not displayed.) The dialog ends as soon as the user has selected a value or confirmed the entry.
However, this dialog variant is not used if, taking into account the conditions, several properties are
possible in principle and if there are no restrictions regarding the property status for at least two of
50
them .
Ifseveralpropertiesareedited,theapplicationoffersasuitableGUItechnologyallowingtheuserexplicitly
to close the dialog. However, the graphical representation of the relevant object is updated with every
property change, i.e. not only at the end of the dialog.
Foranoptimalappearanceofthedialog,thematerialimagesforthepropertyvaluesshouldalsobegiven
in the large variant (see [dsr], section 6.4.2).
48
Thisrestrictionisusefulornecessaryifthespecifiedpropertieshaveinterdependencies.
49
evenifitisactuallynoteditable
50 Thisistopreventswitchingbetweendialogvariantsif,duetodependenciesbetweenproperties,thenumberofproperties
tobeeditedchangesbetween1andNduringtheconfigurationdialog.

25

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | ID of the parameter set |
| 2. | PropClass | X | Char |  | X | Name of the class |
| 3. | Condition |  | BoolExpr |  |  | Validity condition |
| 4. | StateRestr |  | Symbol |  | X | Restriction regarding property state |

<!-- Page 28 -->

4.8.4 DimChange

No. Name Key Type Length Oblig. Explanation
1. ID X ID X ID of the parameter set
2. Dimension X Symbol X Affected dimension
3. Condition BoolExpr Validity condition
4. Separate BoolExpr X To be changed only separately?
5. ThirdDim BoolExpr X Use as the third dimension?
6. Property Symbol X Property to use
7. Multiplier NumExpr X Factor for conversion in m
8. Precision NumExpr X Precision in m

Remarks:
As already stated in section 4.7, actions of type DimChange have to be the single action in the list
(cid:136)
of actions of an interactor. The symbol type of the interactor has to be StartDimChange or a type
51
whose identifier begins with ChangeDim .
(cid:136) Currently, actions of type DimChange are supported only for objects on top planning level.
In field 2, the axis of the concerned dimension is specified.
(cid:136)
The possible values are X, Y, Z, PX, PY, PZ as well as NX, NY and NZ:
– With X, Y and Z, the change may be made on both sides of the object.
– WithPX,PYaswellasPZthechangemayonlybemadeonthesideinpositivedirectionofthe
axis and with NX, NY as well as NZ only on the side in negative direction of the axis.
– A change on the side in negative direction of the axis causes a corresponding repositioning of
the object.
– Only one of the 3 variants (possible change directions) may be used per dimension, or the
conditioninfield3(seebelow)hastobeusedtoensurethatonlyoneofthe3variantsisvalid
at the time of the evaluation. (Otherwise, the concerned dimension does not apply.)
(cid:136) The dimension specified in field 2 is applied if field 3 is empty or if the evaluation of the expression
specified in field 3 definitely yields true.
If, after evaluating the conditions of all entries for the action (field 1), more than one dimension
is affected, it is up to the application whether and how it realizes the interaction. (This may
be dependent on the current view of the user.) However, the behavior of the application in this
situation also can be influenced to a certain extent by the content in fields 4 and 5.
If 2 (or 3) dimensions should be changed simultaneously, the value sets and value ranges of the
(cid:136)
concerned properties must not be dependent on one another! (Otherwise, there can occur an
unexpected or confusing feedback experience for the user.)
If this requirement is not met, the evaluation of the expression given in field 4 for the concerned
dimensions has to yield true. Then, once a dimension has been changed 52 , the applications recall
the value sets and value ranges of the concerned properties in order to react to possible changes
due to the dependencies.
(cid:136) Not all applications resp. application modes allow the simultaneous change of all three dimensions.
If a simultaneous change is possible on the part of the data (see field Separate), field 5 (ThirdDim)
should indicate which of the three dimensions should be changed separately if necessary. For that,
the evaluation of the expression given in the field has to yield true.
If not exactly one dimension is declared as the third dimension, the behavior of the application is
undefined.
Field 6 specifies the property to be used to implement the change of the affected dimension.
(cid:136)
The property key is to be specified without the preceding @ character.
51 OthertypesareignoredandwillbereplacedbyStartDimChange.
52 andiftheactionhasnotyetbeencompleted

26

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | ID of the parameter set |
| 2. | Dimension | X | Symbol |  | X | Affected dimension |
| 3. | Condition |  | BoolExpr |  |  | Validity condition |
| 4. | Separate |  | BoolExpr |  | X | To be changed only separately? |
| 5. | ThirdDim |  | BoolExpr |  | X | Use as the third dimension? |
| 6. | Property |  | Symbol |  | X | Property to use |
| 7. | Multiplier |  | NumExpr |  | X | Factor for conversion in m |
| 8. | Precision |  | NumExpr |  | X | Precision in m |

<!-- Page 29 -->

The property has to meet the following conditions 53 :
– The data type of the property has to be numeric ( N ) or a symbolic choice list ( Y , YS ), see
[property].
In the case of a symbolic choice list, the class of the OFML instance must implement the
following method:
symbolicPropValue2Float(pPKey(Symbol), pPValue(Symbol)) → Float
The method returns the numeric value in Meter, which corresponds to the given
(symbolic) value of the specified property of the implicit instance.
The statements below refer to the native values in the case of a numeric property resp. to the
numericvaluesdeterminedviasymbolicPropValue2Float()inthecaseofasymbolicchoicelist.
– The property values have to be positive.
– The property either has to define a (single) closed value range (in the case of a numeric
property) or a choice list of single values (value set).
Ifbotharedefined,onlythosevaluesfromthechoicelistareusedinthedialogthatarewithin
the value range.

(cid:136) In field 7, the factor is specified which has to be used to convert property values to Meter.
54
In the case of a symbolic choice list, factor 1.0 is assumed .
(cid:136) Field 8 specifies the precision of the property values (in Meter).

Thus, before assigning a (new) value determined by the dialog for the affected dimension to the property
specified in field 6, the application performs the following calculations (in this order):
1. Rounding of the value to the precision specified in field 8.
2. Division of the (rounded) value determined in the first step by the factor given in field 7.
3. Roundingofthevaluedeterminedinthesecondsteptotheprecisionofthepropertyvaluesaccording
55
to the property definition .
(Thisstepisrequiredifthefactorinfield7isnotapoweroften, e.g. inthecaseofpropertyvalues
in inches.)
In the case of a symbolic choice list, the symbolic value corresponding to the numeric value determined
in this way is assigned to the property.

4.8.5 CreateObj

No. Name Key Type Length Oblig. Explanation
1. ID X ID X ID of the parameter set
2. Parent OID X Superior article
3. ArtSpecMode Symbol X Type of indication of the article
to be created
4. Package OFML (X) OFML package
5. ArticleID Char (X) (Base) article number
6. VarCode Char OFML variant code
7. PosRotMode Symbol X Type of indication of
position/rotation
8. PosRotArg1 (Char) (X) Argument 1 for position/rotation
9. PosRotArg2 (Char) (X) Argument 2 for position/rotation
10. PosRotArg3 (Char) (X) Argument 3 for position/rotation

53
Ifoneofthemisnotfulfilled,theactionfails.
54 sincemethodsymbolicPropValue2Float()returnsthenumericvaluesinMeter
55 Inthecaseofasymbolicchoicelist,3decimalplacesareassumed

27

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | ID of the parameter set |
| 2. | Parent |  | OID |  | X | Superior article |
| 3. | ArtSpecMode |  | Symbol |  | X | Type of indication of the article
to be created |
| 4. | Package |  | OFML |  | (X) | OFML package |
| 5. | ArticleID |  | Char |  | (X) | (Base) article number |
| 6. | VarCode |  | Char |  |  | OFML variant code |
| 7. | PosRotMode |  | Symbol |  | X | Type of indication of
position/rotation |
| 8. | PosRotArg1 |  | (Char) |  | (X) | Argument 1 for position/rotation |
| 9. | PosRotArg2 |  | (Char) |  | (X) | Argument 2 for position/rotation |
| 10. | PosRotArg3 |  | (Char) |  | (X) | Argument 3 for position/rotation |

<!-- Page 30 -->

Remarks:

(cid:136) TheobjectIDinfield2mayreferenceonlyasingleobject,otherwisenoarticlecreationtakesplace.
The mode in field 3 specifies how the article to be created is indicated. The following modes are
(cid:136)
supported:
Explicit The details are given explicitly in fields 4-6. If a specific variant is to be created, the
(possibly partially determined) OFML variant code hast to be specified in field 6.
Self Anarticleiscreatedwiththesamearticlenumberandconfiguration(OFMLvariantcode)
as the object to which the interactor is bound for which the action was triggered 56 .
The mode in field 7 specifies how position and rotation for the new object are indicated. The
(cid:136)
following modes are supported:
DataDefined
Position and rotation are determined by the OFML data.
The application determines position and rotation for the new article by calling method
checkAdd() (OFML interface Complex) on the OFML instance of the superior article.
In field 8, a reference object to be passed to method checkAdd() can be specified by means of
an object ID. (The reference object must be an immediate sub-article of the superior article
specified in field 2.)
Inaddition,infield9thekeyofanOFMLattachmentpoint(withoutthepreceding@character)
57
can be specified, which preferentially should be used for placement .

4.8.6 MethodCall

No. Name Key Type Length Oblig. Explanation
1. ID X ID X ID of the parameter set
2. Type Symbol 8 X Type of call
3. Context OFML X Call context
4. Method Char X Name of method
5. Arguments Char Arguments

Two types of method calls are supported. The used type must be specified in field 2:
Instance The method is called on an OFML instance (object).
For this purpose, field 3 must specify the fully qualified identifier of the OFML type or of the
OFMLinterfacewhichdefinesthemethod. Thenameofthemethodhastobespecifiedinfield
4.
The method is called on each target object of the action (see field Objects in table Action ,
section 4.7) whose class is derived from the type specified in field 3 or implements the interface
58
specified there .
Class A (static) class method is called.
Forthispurpose,infield3thefullyqualifiedidentifieroftheclass(OFMLtype)mustbespecified
and in field 4 the name of the method.
In field 5, optional arguments for the method call can be specified. Several arguments must be separated
by a comma. Each argument is specified as an OAP expression (see appendix A). Amongst others, it is
possible to use placeholders in these expressions (see A.4.17).
56 I.e., the information stored in the fields 4-6 with mode Explicit here are queried by the application from the active
object.
57
ThisreferstomethodsetActiveAttPt()ofOFMLinterfaceAttachPts
58 If the articles are not already represented in the application by an OFML instance, the application must create a
correspondingtemporaryOFMLinstanceforthispurpose.

28

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | ID of the parameter set |
| 2. | Type |  | Symbol | 8 | X | Type of call |
| 3. | Context |  | OFML |  | X | Call context |
| 4. | Method |  | Char |  | X | Name of method |
| 5. | Arguments |  | Char |  |  | Arguments |

<!-- Page 31 -->

4.8.7 Message

No. Name Key Type Length Oblig. Explanation
1. ID X ID X ID of the parameter set
2. ArgType Symbol X Type of argument
3. Argument ID X Argument

Remarks:
(cid:136) The text for the message either can be stored in the text table or provided via a method call.
(The latter is useful if the text has to be composed of boilerplates depending on the situation.)
Field 2 indicates which of the two variants is used:
Text The ID in field 3 refers to table Text (section 4.10).
Method The ID in field 3 refers to table Action (section 4.7).
ThereferencedactionmustbeoftypeMethodCallandtheresultofthemethodcallmust
be of OFML type String.
If this is not the case, the ID itself is output as the message.
The method is expected to return the text in the language that is currently to be used
for product data texts of the OFML series of the active object and/or the target object
(see function getPDLanguage() of OFML interface Article in [article]).
The String returned by the method must either be read from a string resource file or be
encoded in US-ASCII.
The following options are available for formatting:
(cid:136)
– The character string causes a line break.
\n
The dialog is terminated when the user ”clicks”next to the dialog window or on the OK button.
(cid:136)

4.8.8 ExtMedia

No. Name Key Typ Length Oblig. Explanation
1. ID X ID X ID of the parameter set
2. Language X Lang 5 Language key
3. Type Symbol X Media type
4. Media String X Media ID

Remarks:
For using and evaluating the language key (field 2) see 3.3.
(cid:136)
Ingeneral,externalmediacontentisnotaccesseddirectlybyspecifyinganURL.Instead,identifiers
(cid:136)
referencing the content are used (field 3).
The following media types (field 2) are defined:
(cid:136)
59
PIM content provided by the PIM
In field 3, the ID has to be specified, by means of which the media content can be
accessed via the PIM interface.
(This type currently is not supported yet.)
YouTube a video hosted by YouTube
In field 3, the YouTube video ID has to be specified.
This ID can be taken from the URL of the video. (For example, in case of URL
the video ID is .)
https://www.youtube.com/watch?v=k-W5A-mvphg k-W5A-mvphg
(cid:136) It is up to the applications whether the media content is displayed in a separate window (dialog)
of the application itself or via an external app (e.g. browser).
59 ProductInformationManagement

29

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | ID of the parameter set |
| 2. | ArgType |  | Symbol |  | X | Type of argument |
| 3. | Argument |  | ID |  | X | Argument |

| No. | Name | Key | Typ | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | ID of the parameter set |
| 2. | Language | X | Lang | 5 |  | Language key |
| 3. | Type |  | Symbol |  | X | Media type |
| 4. | Media |  | String |  | X | Media ID |

<!-- Page 32 -->

### 4.9 Object definitions

An entry in this table references a specific object or set of objects. Referencing is done primarily by
specifying an object category that describes a defined set of objects. For some categories describing a set
of more than one object, the set can be restricted by category-specific arguments.

Table name: Object
Obligatory table: no

No. Name Key Typ Length Oblig. Explanation
1. ID X ID X Object ID
2. Category Symbol X Object category
3. Argumen1 Char Argument 1
4. Argumen2 Char Argument 2
5. Argumen3 Char Argument 3

Remarks:

(cid:136) The ID in field 1 is (possibly the only) part of a hierarchical object identifier (field type OID).
Object identifiers (OIDs) specify the target objects of actions (see field Objects in table Action ,
section 4.7) or arguments of specific action types.
(cid:136) Following object categories (field 2) are defined:
Self ReferstotheactiveobjectincaseofanAttachActionoraDetachActionofamatching
attach area pair (see table AttAreaMatch,section 4.5), or the object to which the
interactor is bound for which the action was triggered.
The argument fields 3-5 have no meaning.
ParentArticle
Refers to the parent article of Self.
The resulting set of objects is empty if Self is not a subarticle.
The argument fields 3-5 have no meaning.
TopArticle Refers to the superior article of Self at the top level of the hierarchy.
The resulting set of objects is empty if Self is not a subarticle.
The argument fields 3-5 have no meaning.
MethodCall The objects are determined by means of a method call.
This object category is not allowed for the target object of an action whose ID is used
as the argument of a call to function methodCall() (see A.4.15) !
In field 3, the ID of an action of type MethodCall has to be specified.
Inthecaseofaninstancemethod,onlyoneobjectdefinitionwithoneofthecategories
Self, ParentArticle or TopArticle is permitted for determining the target object of this
action.
The method is expected to yield either a reference to an OFML instance or a (non-
empty) sequence (Vector, List) of references to OFML instances, where each OFML
instance has to represent an article 60 .
The method must not have any side effects, which would require an update of the
information about OFML instances, stored in different parts of the application 61 .

60 forthetermsseealsosection2.2
61 seealsoremarksregardingfunctionmethodCall()inA.4.15

30

| No. | Name | Key | Typ | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | Object ID |
| 2. | Category |  | Symbol |  | X | Object category |
| 3. | Argumen1 |  | Char |  |  | Argument 1 |
| 4. | Argumen2 |  | Char |  |  | Argument 2 |
| 5. | Argumen3 |  | Char |  |  | Argument 3 |

<!-- Page 33 -->

The argument fields 4 and 5 have no meaning.
Theexecutionoftheactioninwhichtheobjectdefinitionisusedfailsinthefollowing
cases:
– The action specified in field 3 does not have type MethodCall.
– The action specified in field 3 specifies an instance method, but there is more
than one target object specified or the object definition for the target object
does not use one of the object categories Self, ParentArticle or TopArticle.
– ThemethodreturnsnoOFMLinstanceormorethanoneOFMLinstancewhere
exactly one object is expected.

### 4.10 Texts

In this table, language-specific texts are stored, which are required for actions of types ActionChoice,
Message and PropEdit2.

Table name: Text
Obligatory table: no

No. Name Key Type Length Oblig. Explanation
1. ID X ID X Text ID
2. Language X Lang 5 Language key
3. Text Text X Text content

For using and evaluating the language key (field 2) see 3.3.
If the table does not exist, the behavior of the application is undefined. Usually the affected action will
fail.
If the table exists, but no text can be determined for an ID, the ID itself is used as text.
Unless otherwise specified for the above actions, the escape sequences for special characters known from
OFML are not permitted in the text!

### 4.11 Images

Table name: Image
Obligatory table: no

No. Name Key Type Length Oblig. Explanation
1. ID X ID X Image ID
2. Language X Lang 5 Language key
3. DPR X Int X Device-Pixel-Ratio
4. File Char X Filename/path

Remarks:

For using and evaluating the language key (field 2) see 3.3.
(cid:136)
If no image can be determined for an ID, the behavior of the application is undefined. Usually the
affected action will fail.
TheDevice-Pixel-Ratio(field3)isatermfromthewebdesign: itspecifieshowmanyphysicalpixels
(cid:136)
of the output device – per dimension – are used to represent a (logical) image point (of the web
page). With a DPR of 2, e.g., 4 pixels are used to represent one image point. Normal resolution
displays have a DPR of 1, high-resolution displays of smartphones and tablets have a DPR of 2
(and more).

31

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | Text ID |
| 2. | Language | X | Lang | 5 |  | Language key |
| 3. | Text |  | Text |  | X | Text content |

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | ID | X | ID |  | X | Image ID |
| 2. | Language | X | Lang | 5 |  | Language key |
| 3. | DPR | X | Int |  | X | Device-Pixel-Ratio |
| 4. | File |  | Char |  | X | Filename/path |

<!-- Page 34 -->

In order to display an image with 100x100 image points (e. g. a tile of size medium with actions of
type ActionChoice and view type Tile) a high-resolution display with DPR 2 expects an image file
of the size 200x200 pixels 62 . If instead an image file with only 100x100 pixels would be provided,
the image would be scaled up to 200x200 pixels 63 , which would lead to quality losses.
Therefore, in OAP it is required that in addition to the image file for normal resolution (DPR 1) at
64
least another image file for DPR 2 is provided . (If this file is not provided, the behavior of the
application is undefined.)
By default, the image files referenced in field 4 are stored in the same directory as the OAP data.
(cid:136)
If necessary, however, they can also be stored in a subdirectory of it. In this case, the filename
must be preceded by a relative path, using the slash (’ / ’=U+002F) as the separator between the
individual path components.
(cid:136) The image format of the file specified in field 5 must be JPEG, PNG or SVG.
ImagesinJPEGformathavetocomplywiththespecificationoftheJPEG File Interchange Format
65
(JFIF) and
– have to be sequentially structured (not interlaced/progressive)
– have to use Huffman coding (not arithmetic coding)
– have to use the YCbCr color model (no black/white)
– have to use 8 bit color channel (no more).
Images in PNG format have to comply with the PNG (Portable Network Graphics) Specification,
66
Version 2.2 and
– have to be sequentially structured (not interlaced/progressive)
– have to use the RGB color model
– have to use 8 bit color channel (no more, no black/white)
– optionally an 8 bit alpha channel can be used for transparent images.
Images in SBG format have to comply with the specification Scalable Vector Graphics (SVG) 1.1
67
(Second Edition) where animations and interactions are not allowed.
(cid:136) TheimagefilesforagivenimageIDmayuseseveralimageformatsfordifferentDPR’s(field3). For
example, it is conceivable resp. wise to use a raster graphic (JPEG, PNG) for the normal resolution
representation, but SVG for higher resolutions.

### 4.12 Version information

Table name:
Version
Obligatory table: yes

No. Name Key Type Length Oblig. Explanation
1. FormatVersion Char X Number of the used format version

Remarks:
(cid:136) The table serves to give information concerning the used format.
The table may contain only one entry.
The format version (field 1) has to be indicated in the form MajorNumber.MinorNumber according
(cid:136)
to the OAP specification.

62 which,correspondingly,cancontainmoreimagedetails
63 Iftheimagefileislargerthan200x200pixels,theimagewillbescaleddownaccordingly.
64
sincethiscorrespondstotheDPRofcurrentlypopularsmartphonesandtablets
65
http://www.jpeg.org/public/jfif.pdf
66 http://libpng.org/pub/png/spec/1.2/png-1.2-pdg.html
67 https://www.w3.org/TR/SVG11/

32

| No. | Name | Key | Type | Length | Oblig. | Explanation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. | FormatVersion |  | Char |  | X | Number of the used format version |

<!-- Page 35 -->

# A OAP expressions

### A.1 General definitions

For boolean and numeric expressions the same syntax and semantics are used.
ThevaluesofalldatatypessupportedbyOAP(seeA.2)canbeformattedaccording tothe OFMLScript
Object Notation (OSON). This is utilized, amongst others, when passing arguments to OFML methods
called in the course of actions of type MethodCall.
Theotherwayround, most, ifnotall, valuerepresentationsformattedaccordingtoOSONcanbeparsed
and stored using one of the data types supported by OAP. This is used, among other things, for values
returned from OFML methods called via function methodCall() (see A.4.15).
Each OAP expression is evaluated in a defined context. When evaluating the validity condition of an
interactor, e.g., the active planning element and the ID of the interactor are known (and relevant). For
this purpose, the application core module that executes the evaluation of OAP expressions is provided
with a so-called evaluation context. This context contains an object table, in which the reference to the
relevant object 68 is stored for defined scopes, and a value table, which stores the values for defined keys
(for example, identifiers of placeholders, see A.4.17).

### A.2 Supported data types

Each expression or subexpression returns a value that has one of the types described in the following
subsections.
69
For each type an information is given on OSON formatting resp. how to parse an OSON input .

A.2.1 Error

70
Values of type Error are returned if an error occurred during the evaluation of a (sub) expression . The
value consists of an error code and an error message.
OSON formatting: NULL
OSON parsing: not applicable

A.2.2 Null

Type Null has the only value NULL.
Itisusuallyusedwhenthereisnovalueavailableinagivencontext,as,e.g.,inthecaseofanon-existent
property during property value access (see A.4.16).
OSON formatting and parsing: NULL

A.2.3 Int

A value of type Int is an integer in the range from −2 31 to 2 31 −1 (inclusive).
Arithmetic operations with an integer result, that can not be represented as an integer in the specified
range, return an error.
OSON formatting: decimal integer literal
OSON parsing: decimal, octal oder hexadecimal integer literal
68 internalterm: articleinstanceidentifier(AIID)
69
TheliteralsmentionedthereinrefertotheliteralsspecifiedinpartIIIoftheOFMLstandard,nottotheOAPliterals
specifiedinA.3.2.
70 Errorsarereturnedasspecificallytypedvaluesinordertobeable,withinstantaneousevaluationduringthesyntactic
analysis,toeasierignoreerrorsoccuringinnon-relevantoperandsofoperatorswithconditionalevaluation.

33

<!-- Page 36 -->

A.2.4 Float

A value of type Float is a 64-bit floating-point number according to IEEE 754.
Infinity and NaN are not supported. Operations with an corresponding result return an error.
OSON formatting und -Parsen: floating-point literal

A.2.5 Symbol

A value of type Symbol is character string from a restricted range of values.
OSONformatting: Ifpossibleassymbolliteral,otherwiseassymbolconstructor( Symbol() )withastring
literal as argument
OSON parsing: symbol literal or symbol constructor

A.2.6 String

A value of type String consists of a possibly empty string of characters.
OSON formatting and parsing: string literal

A.2.7 Sequence

A value of type Sequence contains an ordered, possibly empty sequence of values.
OSON formatting: Vector
OSON parsing: Vector or List

A.2.8 Name

AvalueoftypeNamerepresentsasimplenamesuchast,anhierarchicalnamesuchasc.e1ora(partially
resp. fully) qualified name such as ::ofml::oi::OiPlElement.
OSON formatting and parsing: simple name, hierarchical name, qualified name

A.2.9 Numeric types

The two types Int and Float are called numeric types.

A.2.10 Boolean types

Numeric types as well as type String are called boolean types.
If an operator expects an operand of Boolean type, the value of the operand is considered to be true if
it is either a numeric type and the value is not equal to zero, or if it is of type String and the value is a
non-empty string. All other values of boolean types will be considered to be false.

### A.3 Lexical structure

71
An expression consists of a nonempty sequence of token .
Spaces are allowed before the first, after the last and between tokens.
Tokens are divided into operators (A.3.1), literals 72 and identifier (A.4.19).
Duringlexicalanalysis, startingfromthecurrentposition, thenexttokenisdeterminedtobethelongest
possible string that yields a valid token. The lexical analysis fails if no such token can be determined.
71 smallestunitswithadistinctivemeaning
72 Literalsaredefinedstringsforthedirectrepresentationofthevaluesofbasetypes.

34

<!-- Page 37 -->

A.3.1 Operators

The following operators are defined:

? : :: || | && & ^ == !=
! < <= << > >= >> >>> + -
* / % ~ ( ) $ ,

A.3.2 Literals

NULL literal
The NULL literal consists of the four consecutive letters NULL . It represents the only value of type Null.

Symbol literals
There are two forms of symbol literals 73 :
The normal form starts with character @ (U+0040) immediately followed by a letter or underscore
(cid:136)
(’ _ ’=U+005F),followedbyzeroormoreletters,digitsand/orunderscore,withonlyASCIIcharacters
allowed 74 .
The second form consists of character @ immediately followed by a string literal (see below). It can
(cid:136)
and should solely be used to represent symbols that can not be represented using the normal form.

String literals
A string literalconsistsof a possibly empty string of charactersenclosed indoublequotes(’"’=U+0022).
The double quote itself is not allowed in the string. To represent this and certain special characters, the
following escape sequences, starting with a backslash (’\’=U+005C), have to be used:
\a U+0007 bell character (BEL)
\b U+0008 backspace (BS)
\t U+0009 horizontal tab (HT)
\n U+000A newline (NL)
\v U+000B vertical tab (VT)
\f U+000B form feed (FF)
\r U+000D carriage return (CR)
\" U+0022 double quote
\’ U+0027 single quote
\\ U+005C backslash
\[0-7] octal escape sequence
\x[0-9A-Fa-f] hexadecimal escape sequence
An octal escape sequence consists of the backslash followed by up to three octal digits
(’ 0 ’..’ 7 ’=U+0030..U+0037), which is converted to an integer value.
A hexadecimal escape sequence consists of the character \x , followed by one or more hexadecimal digits
(’ 0 ’..’ 9 ’=U+0030..U+0039,’ A ’..’ F ’=U+0041..U+0046,’ a ’..’ f ’=U+0061..U+0066),withthelongestpossi-
ble digit sequence being consumed and converted to an integer value.
Thevaluedeterminedbyoctalandhexadecimalescapesequencesmodulo256isthecodeoftherepresented
character.
If the backslash is not followed by any of the characters listed above, or if \x is not followed by a
hexadecimal digit, the backslash is ignored and the character following it is taken unchanged.

73 Thecharacter@isnotpartofthevalueofthesymbol.
74 seealsofieldtypeSymbolinsection3.2

35

<!-- Page 38 -->

Integer literals
Integer literals are divided into decimal, octal and hexadecimal ones:

Decimale integer literals consist of a sequence of decimal digits (’ ’..’ ’=U+0030..U+0039), where
(cid:136) 0 9
the first digit can not be null unless it is the only digit.
Octal integer literals consist of a leading null (’ ’=U+0030), followed by one or more octal digits
(cid:136) 0
(’ ’..’ ’=U+0030..U+0037).
0 7
Hexadecimal integer literals consist of a leading null (’ 0 ’=U+0030), followed by ’ x ’ (U+0078)
(cid:136)
or ’ X ’ (U+0058), followed by one or more hexadecimal digits (’ 0 ’..’ 9 ’=U+0030..U+0039,
’ A ’..’ F ’=U+0041..U+0046, ’ a ’..’ f ’=U+0061..U+0066).

The unsigned number U represented by an integer literal must not be greater than 2 32 −1. The signed
value of the literal I is equal to U if 0≤U <−2 31 , otherwise I =U −2 32 is valid.

Floiting-point literals
Floating-point literals consist of the mantissa and an optional exponent.
The mantissa consists of a non-empty sequence of decimal digits (’ 0 ’..’ 9 ’=U+0030..U+0039) and a max-
imum of one decimal point (’ . ’=U+002E) at any position 75 .
The exponent consists of the letter ’e’ (U+0065) or ’E’ (U+0045), followed by an optional sign ’+’
(U+002B) or ’-’ (U+002D), followed by a nonempty sequence of decimal digits (see above).
Mantissa and exponent are generally interpreted as decimal numbers.
Decimal point or exponent can be missing, but not both.
A floating-point literal whose absolute value after convertion to the internal binary representation and
1024
rounding to 53 (binary) digits is greater than or equal to 2 , leads to an error.

### A.4 Syntax of expressions

A.4.1 Precedence and associativity of operators

The precedence (priority, rank) of operators controls the order in which the corresponding operations in
expressions are executed, unless a different order has been explicitly given by bracketing.
For operators of equal precedence, associativity controls the order of evaluation of the operations. Most
operators are left-associative, so A op B op C is evaluated as (A op B) op C.
The following table gives an overview of precedence and associativity of operators in OAP 76 .
75
includingthefirstorthelastdigit
76
Thetableisforinformationonly. Thebindingdefinitionofprecedenceandassociativityisgivenbythesyntaxrulesin
thefollowingsections.

36

<!-- Page 39 -->

Precedence Operator Description Associativity
1 :: scope for access to property values
$ placeholder
() funktion call
2 + - unary Plus and Minus right
~ ! bitwise and logical negation
3 * / % multiplication, division and modulo left
4 + - addition and subtraction links
5 << >> >>> shift operations left
6 relational operations left
< > <= >=
7 == != comparisons left
8 & bitwise AND left
9 ^ bitwise exclusive OR left
10 | bitwise OR left
11 && logical AND left
12 logical OR left
||
13 ? : conditional evaluation right
14 , separator of expressions in argument lists links

77
Subexpressions are generally evaluated from left to right .

A.4.2 Expressions

Expression:
UnaryExpression
ConditionalExpression

The evaluation of an expression or subexpression yields a value of one of types described in section A.2.
If one or more subexpressions of an expression return an error, unless otherwise specified, the error that
first occurred in the evaluation order is returned. Whether further subexpressions are evaluated or not
after the occurrence of an error in a subexpression is not specified.
If it is required in the following sections that a condition must be met, and the condition is not satisfied,
then the corresponding expression returns an error.

A.4.3 Conditional evaluation

ConditionalExpression:
LogicalOrExpression
LogicalOrExpression Expression ConditionalExpression
? :

The left expression must yield a boolean value. If the value is true, the result of the middle expression is
returned, otherwise the result of the right expression.
The implementation behaves as if the respectively other expression would not be evaluated 78 .
77
Withthefunctionalitycurrentlysupported,theorderofevaluationisoflesserimportance,sincealloperatorshaveno
visiblesideeffects,andOFMLfunctionscalledviamethodCall()arealsorequiredtohavenosideeffect(seeA.4.15).
78 Implementationsmayspeculativelyevaluatetheothersubexpressionaslongasitisensuredthatanyerrorsthatmay
occur are ignored and no side effects occur, or any side effects that may occur will be withdrawn if the evaluation of the
othersubexpressionturnsouttobeunnecessarytodeterminetheresultoftheexpression

37

<!-- Page 40 -->

A.4.4 Logical OR operator

LogicalOrExpression:
LogicalAndExpression
LogicalOrExpression || LogicalAndExpression

The left expression must yield a boolean value. If the value is true, the result is . Otherwise, the right
1
expression is evaluated and must also yield a boolean value. If this is true, the result is 1 , otherwise 0 .
In case the left expression yields true, the implementation behaves as if the right expression would not
be evaluated 79 .

A.4.5 Logical AND operator

LogicalAndExpression:
BitwiseOrExpression
LogicalAndExpression && BitwiseOrExpression

The left expression must yield a boolean value. If the value is false, the result is 0 . Otherwise, the right
expression is evaluated and must also yield a boolean value. If this is false, the result is 0 , otherwise 1 .
In case the left expression yields false, it is unspecified, whether the right expression is evaluated. If it is
evaluated and an error occurs during the evaluation, then the error is ignored.
In case the left expression yields false, the implementation behaves as if the right expression would not
80
be evaluated .

A.4.6 Bitwise combinations

BitwiseOrExpression:
BitwiseExclusiveOrExpression
BitwiseOrExpression BitwiseExclusiveOrExpression
|
BitwiseExclusiveOrExpression:
BitwiseAndExpression
BitwiseExclusiveOrExpression BitwiseAndExpression
^
BitwiseAndExpression:
EqualityExpression
BitwiseAndExpression & EqualityExpression

The left and right operands must be of type Int. Both operands are combined bitwise with each other
according to the operator. The result again is of type Int.

A.4.7 Operators to test for equality

EqualityExpression:
RelationalExpression
EqualityExpression == RelationalExpression
EqualityExpression != RelationalExpression

When testing for equality, the following rules are applied in the given order:

(cid:136) If one of the two operands is of type Null, both operands are considered equal if both operands are
of type Null. Otherwise they are not equal.
79 seefootnoteaboveforconditionalevaluation
80 seefootnoteaboveforconditionalevaluation

38

<!-- Page 41 -->

If both operands are of type String, Symbol or Name, then they are considered equal if their values
(cid:136)
match characters for characters.
If both operands have a numeric type, they are considered equal if both have the same numeric
(cid:136)
value.
IfbothoperandsareofthetypeSequence,thecomparisonreturnsanerrorifoneofthetwosequences
(cid:136)
contains a value of type Error. Otherwise, the sequences are considered not equal if their length
does not match. Otherwise, a pairwise comparison of the elements of both sequences occurs. If an
error occurs, the comparison of the two sequences also yields an error. Otherwise, the sequences
are considered equal if all elements are equal in pairs.
(cid:136) Otherwise, the comparison returns an error.

The result of the operator == is 1 if both operands are equal, and 0 if they are not equal.
The result of the operator is if both operands are not equal, and if they are equal.
!= 1 0

A.4.8 Relational operators

RelationalExpression:
ShiftExpression
RelationalExpression < ShiftExpression
RelationalExpression <= ShiftExpression
RelationalExpression >= ShiftExpression
RelationalExpression > ShiftExpression

Relative comparison of two values applies the following rules in the given order:

(cid:136) If both operands are of type String, then both strings are compared character by character until a
difference is found or the end of the shorter string is reached. In the case of a difference, the result
of the comparison of the character strings is equal to the result of the comparison of the different
characters, the character with the smaller character code being considered smaller. Otherwise, the
shorter string is considered smaller.
(cid:136) Ifbothoperandshaveanumerictype, theoperandissmaller, whichhasthesmallernumericvalue.
(cid:136) Otherwise, the comparison returns an error.

The result of operator < is 1 if the left operand is smaller than the right operand.
The result of operator <= is 1 if the left operand is less than or equal to the right operand.
The result of operator is if the left operand is greater than or equal to the right operand.
>= 1
The result of operator > is 1 if the left operand is greater than the right operand.
Otherwise, the result of the operators is 0 .

A.4.9 Shift operators

ShiftExpression:
AdditiveExpression
ShiftExpression << AdditiveExpression
ShiftExpression >> AdditiveExpression
ShiftExpression >>> AdditiveExpression

The left and right operands must be of type Int. The least significant 5 bits of the right operand are
considered as an unsigned integer and provide the number of bits, hereafter n, by which the left operand
should be shifted.

39

<!-- Page 42 -->

Operator << shiftstheleftoperandnbitstotheleft,discardingthemostsignificantnbitsoftheoperand
and setting the least significant n bits of the result to 0 .
Operator shifts the left operand n bits to the right, copying the most significant bit of the operand
>>
into the most significant n bits of the result and discarding the least significant n bits of the operand.
Operator >>> shifts the left operand n bits to the right, discarding the least significant n bits of the
operand and setting most significant n bits of the result to 0 .

A.4.10 Binary arithmetic operators

AdditiveExpression:
MultiplicativeExpression
AdditiveExpression + MultiplicativeExpression
AdditiveExpression - MultiplicativeExpression
MultiplicativeExpression:
UnaryExpression
MultiplicativeExpression * UnaryExpression
MultiplicativeExpression / UnaryExpression
MultiplicativeExpression % UnaryExpression
Bothoperandsmusthaveanumerictype. Operator + alsocanbeusedwithtwooperandsoftypeString.
If both operands have a numeric type and at least one operand has type Float, the other operand, if
necessary, is converted to Float and the calculation is performed in Float. The result then also has type
Float. Otherwise, the result has the same type like both operands.
Ifoperator+isappliedtooperandsoftypeString, theresultistheconcatenationoftheleftoperandand
the right operand, in this order.
The result of dividing by zero or modulo zero is always an error even if the left side of the operator is
zero.
The operation a % b calculates the result of a−n∗b, where n is the result of a/b rounded in direction
31
to zero. The result of −2 %−1 is 0.

A.4.11 Unary arithmetic operators

UnaryExpression:
+ UnaryExpression
- UnaryExpression
If the operand of the unary operators + and - does not have a numeric type, then these operators return
an error. Otherwise, the result has the same type and the same absolute value as the operand. In the
case of operator +, the result has the same sign as the operand. In the case of operator -, the result has
81
the opposite sign of the operand .

A.4.12 Operators for bitwise and logical negation

UnaryExpression:
UnaryExpression
~
UnaryExpression
!
The result of both operators has type Int.
In the case of operator ~ , the operand must be of type Int. The result is the bitwise negation of the
operand.
In the case of operator !, the operand must have a boolean type. The result is 1 if the operand is
considered true, otherwise 0.
81 The only exception is the negation of 0, since there is no distinction between and in the two’s complement
+0 -0
representation.

40

<!-- Page 43 -->

A.4.13 Primary expressions

UnaryExpression:
PrimaryExpression
PrimaryExpression:
( Expression )
FunctionCall
PropertyReference
Placeholder
Literal
[ ExpressionList ]
opt
ExpressionList:
Expression
ExpressionList , Expression

A.4.14 Funktion call

FunctionCall:
Identifier ( ExpressionList )
opt

Afunctioncallconsistsofthenameofapredefinedfunctionfollowedbyapossiblyemptylistofarguments
enclosed in parentheses, where arguments are separated by commas.
Function calls can be nested, that is, the argument list on its part also can contain calls of arbitrary
functions.
If an error occurred while evaluating the arguments of a function 82 or if there is no function with the
specified identifier, the function call fails.
Currently predefined functions are the functions described in appendix B and the function methodCall()
described in the next section.

A.4.15 Execution of MethodCall actions

Function methodCall(actionId) can be used in order to perform function calls defined by MethodCall
actions. The argument actionId is any expression which must yield a string interpreted as the ID of the
corresponding MethodCall action.
The function returns an error if any of the following conditions is satisfied:

The function does not have exactly one argument of type String.
(cid:136)
The maximum number 83 of nested calls of MethodCall actions has been reached 84 . When counting
(cid:136)
the depth of nesting, the name of the action does not matter.
(cid:136) In the evaluation context of the expression that contains the call of methodCall(), object SELF is
not defined.
(cid:136) An error occurred while querying the data of the MethodCall action, the type of action is not
MethodCall, or the action’s data is incorrect.
(cid:136) The evaluation of the execution condition of the action (if specified) definitely yields true.

82
i.e.,oneoftheargumentshastypeError
83 Inthecurrentimplementation(October2017)thevalueissetto10.
84 NestedMethodCallactionsmayoccuriftheexecutionconditionofaMethodCallactionitselfusesfunctionmethodCall().

41

<!-- Page 44 -->

In case of an instance method:
(cid:136)
– An error occured during the evaluation of an object definition or during the generation of the
corresponding OFML instance.
– After evaluating all object definitions, not exactly one object was determined.
– The verification of the context (class, interface) defined for the MethodCall action failed for
the determined object.
(cid:136) An error occurred while evaluating the arguments defined by the MethodCall action using the
current evaluation context.
(cid:136) The call of the OFML method failed.
(cid:136) The result returned by the OFML method could not be converted to an OAP data type.

OFMLmethodswhicharecalledviafunctionmethodCall()mustnothaveanyvisiblesideeffects,because
85
for performance reasons it is not possible to update the information about OFML instances , stored in
different parts of the application, after every call of methodCall().

A.4.16 Access to property values

PropertyReference:
PropertyName
Scope :: PropertyName
PropertyName:
Identifier
Scope:
Identifier

ApropertyvalueaccesswithoutspecifiedscopecorrespondstoanaccesswithscopeSELF(seealsobelow).
Duringapropertyvalueaccess,theidentifierforthescopeislookedupintheobjecttableoftheevaluation
context (see A.1) to determine the corresponding article instance identifier (AIID). This then is used to
86
query the application for the value of the specified property of the referenced article instance .
If no entry is found in the object table for the specified scope, or if the referenced object has no property
with the specified name, or if the value of the property can not be converted to an OAP value, the result
ofthepropertyvalueaccessisNULL.SupportedtypesofpropertyvaluesareSymbol, String, Null, Intand
Float.

Currently, the following scopes are defined:

SELF References the active object (corresponds to object category Self, see 4.9).
PARENT References the immediate parent article of the active object (corresponds to object category
ParentArticle, see 4.9).
TOP References the parent article of the active object that is highest in the hierarchy (corresponds
to object category TopArticle, see 4.9).
85
suchasarticlenumbers,variantcodes,articleandvarianttexts
86
Infact,inthecurrentimplementation(October2017),theentirePropVarCodeisqueriedbytheapplicationandstored
intheevaluationcontextforpossiblereuse,oraPropVarCodestoredthereisuseddirectly. Thepropertyvalueisextracted
fromthePropVarCode.

42

<!-- Page 45 -->

A.4.17 Placeholder

Placeholder:
$ Identifier

In placeholder substitution, the identifier specified as a placeholder is looked up in the value table of the
evaluation context (see A.1). If an entry is found, the corresponding value is returned.
Otherwise, the identifier specified as a placeholder is looked up in the object table of the evaluation
context. If no entry is found there, the result of the placeholder substitution is NULL . Otherwise, for the
article instance identifier (AIID) that was found in the object table, the corresponding OFML instance
is determined or recreated (if it currently does not exist). The placeholder substitution result then is a
value of type Name representing the name of the OFML instance.

Currently, the following placeholder are defined:

INTERACTOR
This placeholder is replaced by the identifier of the interactor for which currently information
is being determined or to which the currently executed action is bound.
SELF This placeholder is replaced by the name of the OFML instance of the active object (see also
scope SELF in A.4.16).

A.4.18 Literals

Literal:
SymbolLiteral
StringLiteral
IntegerLiteral
FloatingPointLiteral
NullLiteral

The syntax of literals is described in A.3.2.

A.4.19 Identifier

An identifier consists of a non-empty sequence of letters, numbers and/or underscore, where the first
87
character may not be a number and only ASCII characters may be used .

87 correspondstofieldtypeSymbolintheOAPtables(see3.2)

43

<!-- Page 46 -->

# B Functions

### B.1 Mathematical functions

All arguments must have a numeric type (see A.2.9). Arguments of type Int are converted to type float
88
beforethefunctioniscalculated. Thevalueoftheargumentsmustbeinthespecifiedrange . Ifnoerror
is returned, the return value of all functions has type Float.

Trigonometric functions

acos(x) Calculates the inverse cosine of x for −1≤x≤1.
acosh(x) Calculates the inverse hyperbolic cosine of x for 1≤x<+∞.
asin(x) Calculates the inverse sine of x for −1≤x≤1.
asinh(x) Calculates the inverse hyperbolic sine of x for −∞<x<+∞.
atan(x) Calculates the inverse tangent of x for −∞ < x < +∞. The result is in the range
[−π/2,+π/2].
atan2(y,x) Calculates the inverse tangent of y/x for −∞<x<+∞ and −∞<y <+∞ using the
signs of both arguments to determine the quadrant of the return value. The result is in
the range [−π,+π].
In general, the result has the sign of y.
For positive x the absolute value of the result is less than π/2.
For negative x the absolute value of the result is greater than π/2.
If x is zero, the following rules apply:
If y is not equal to zero, then the result is ±π.
(cid:136)
If x is +0.0 and y is ±0.0, then the result is ±0.0.
(cid:136)
If x is -0.0 and y is ±0.0, then the result is ±π.
(cid:136)
atanh(x) Calculates the inverse hyperbolic tangent of x for −1<x<1.
cos(x) Calculates the cosine of x for −∞<x<+∞.
cosh(x) Calculates the hyperbolic cosine of x for −∞<x<+∞.
sin(x) Calculates the sine of x for −∞<x<+∞.
sinh(x) Calculates the hyperbolic sine of x for −∞<x<+∞.
tan(x) Calculates the tangent of x for −∞<x<+∞ 89 .
tanh(x) Calculates the hyperbolic tangent of x for −∞<x<+∞.

88
Evenifallargumentsareinthespecifiedrange,anerrorcanbereturnediftheresultexceedsthevaluerangeoftype
Float. Underrunsofthevaluerange(valueswithverysmallamount)donotleadtoanerror. Instead,zeroisreturned.
89 Theoretically,thetangentfunctionisnotdefinedforπ/2+n∗πwithintegern. However,sinceπcannotbeaccurately
represented,thatshouldnotbeaprobleminpractice. Forexample,theresultoftan(atan2(1,0))is1.63312393531954e+16.

44

<!-- Page 47 -->

Power, exponential and logarithmic functions

x
exp(x) Calculates the value of exponential function e for −∞<x<+∞.
log(x) Calculates the natural logarithm of x for 0<x<+∞.
log10(x) Calculates the common logarithm of x for 0<x<+∞.
logb(x) Calculates the binary logarithm of x for ∞ < x < +∞ rounded towards negative infin-
90
ity .
y
pow(x,y) Calculates the value of x for −∞<x<+∞ and −∞<y <+∞.
If x is negative, y must be an integer value.
If x is 0 , y must not be negative.
The result is if both x and y are equal to .
1.0 0
scalb(x,y) Calculates x∗2 n , where n is y rounded towards zero, for −∞<x<+∞ and −∞<y <
+∞.
sqrt(x) Calculates the square root of x for 0≤x<+∞.

Rounding, absolute value and remainder

ceil(x) For −∞<x<+∞ calculates the smallest integer value that is not less than x.
fabs(x) Calculates the absolute value of x for −∞<x<+∞.
floor(x) For −∞<x<+∞ calculates the largest integer value that is not greater than x.
fmod(x,y) Calculates the remainder of the floating-point division x/y for −∞ < x < +∞ and
−∞<y <+∞ with y (cid:54)=0.0.
Thiscorrespondstotheoperationx%y withthedifferencethattheresultalwayshastype
Float.
remainder(x,y) Calculates the remainder of the division x/y for −∞ < x < +∞ and
−∞<y <+∞ with y (cid:54)=0.0.
The result is x−n∗y, where n is the result of x/y rounded toward the next integer. If
the absolute value of x−n∗y is 0.5 then n is chosen to be even.

90 Theresultisequaltothevalueoftheexponentoftheinternalfloatingpointrepresentation,convertedtoFloat.

45

<!-- Page 48 -->

### B.2 Type conversion functions

All conversion functions exist in two variants.
The first variant has an argument specifying the value to be converted.
This variant returns an error (a value of type Error) if the conversion was not successful.
Thesecondvarianthastwoarguments. Thefirstargumentspecifiesthevaluetobeconverted,thesecond
a default value, which is used as the return value of the conversion function if the conversion was not
successful. The type of the default value is not restricted.
It is not defined whether the expression in the argument for the default value is evaluated or not.

B.2.1 Conversion to Int

int(value)
int(value, default)

The function converts the value of the expression passed in argument value into a value of type Int.
The following conversions are supported:
from Int to Int:
(cid:136)
The return value of the conversion function is equal to the value of argument value.
This conversion always is successful.
from Float to Int:
(cid:136)
In the first step of the conversion, the fractional part of the value of argument value is truncated
(rounding toward zero).
The conversion function returns the value determined in step 1 as Int if it can be represented as
such (−2 31 ≤I <2 31 ). Otherwise, the conversion is not successful.
from String to Int:
(cid:136)
The value of argument value has to be a string composed of the following components: optional
leading spaces, an optional negative sign (’-’=U+002D), an integer literal as described in ap-
pendix A.3.2, optional trailing spaces. Otherwise, the conversion is not successful.
Withoutsign,thereturnvalueoftheconversionfunctionisequaltothevalueoftheliteral,otherwise
equal to the negated value of the literal (see A.4.11).

B.2.2 Conversion to Float

float(value)
float(value, default)

The function converts the value of the expression passed in argument value into a value of type Float.
The following conversions are supported:
from Int to Float:
(cid:136)
The return value of the conversion function is a floating-point number with the same value as
argument value.
This conversion always is successful.
from Float to Float:
(cid:136)
The return value of the conversion function is equal to the value of argument value.
This conversion always is successful.

46

<!-- Page 49 -->

from String to Float:
(cid:136)
The value of argument value has to be a string composed of the following components: optional
leading spaces, an optional negative sign (’ - ’=U+002D), a floating-point literal as described in
appendix A.3.2, optional trailing spaces. Otherwise, the conversion is not successful.
Withoutsign,thereturnvalueoftheconversionfunctionisequaltothevalueoftheliteral,otherwise
equal to the negated value of the literal (see A.4.11).

B.2.3 Conversion to Symbol

symbol(value)
symbol(value, default)

The function converts the value of the expression passed in argument value into a value of type Symbol.
The following conversions are supported:
(cid:136) from Symbol to Symbol:
The return value of the conversion function is equal to the value of argument value.
This conversion always is successful.
(cid:136) from String to Symbol:
The conversion function returns a value of type Symbol, representing the same string as the string
to be converted.
This conversion always is successful.
Note:
There is no special handling for the character ’@’ (U+0040) at the beginning of
the string. Therefore, expression returns a symbol yielding string
symbol("@FOO")
after formatting according to the OFML Script Object Notation
"Symbol(\"@FOO\")"
(OSON) (instead of "@FOO").

B.2.4 Conversion to String

string(value)
string(value, default)

The function converts the value of the expression passed in argument value into a value of type String.
The following conversions are supported:
from Int to String:
(cid:136)
Thereturnvalueoftheconversionfunctionisastringthatconformstotherulesfordecimalinteger
literals (see appendix A.3.2) and represents the same value as the argument value.
This conversion always is successful.
(cid:136) from Float to String:
The return value of the conversion function is a string that conforms to the rules for floating-point
literals (see appendix A.3.2) and Though, the exact representation is unspecified apart from the
following exceptions:
– The string contains a decimal point or an exponent, or both.
– The conversion is done with an precision of at least fifteen decimal digits in the mantissa.
– The conversion does not produce any significant zeros after the first decimal digit of the
mantissa.
This conversion always is successful.

47

<!-- Page 50 -->

Note:
The conversion is not exact. It is not guaranteed that the expression
float(string(x)) == x is true.

from Symbol to String:
(cid:136)
The conversion function returns a value of type String, representing the same string as the symbol
to be converted.
This conversion always is successful.

Note:
The value of the expression string(@FOO) is "FOO" (not "@FOO" ).

(cid:136) from String to String:
The return value of the conversion function is equal to the value of argument value.
This conversion always is successful.

48

<!-- Page 51 -->

# C Modification history

OAP 1.6, 1st revised version:
Clarification on the use of the dialog variants for actions of type PropEdit2 (section 4.8.3).
(cid:136)

OAP 1.6:
New interactor symbol types Duplicate, FinishMode, VisibilityOff and VisibilityOn (section 4.6).
(cid:136)
Now, for interactors with an action of type Dimchange, symbol types whose identifier begins with
(cid:136)
ChangeDimarealsopermittedinadditiontosymboltypeStartDimChange(sections4.6and4.8.4).
Clarification on the use of actions of types Dimchange, Message and ShowMedia (section 4.7).
(cid:136)
Table ExtMedia now contains a new field to specify a language key (section 4.8.8).
(cid:136)
Note: If this feature is to be applied to existing sf OAP data, it has to be converted to the format
of the new version 1.6 91 !

OAP 1.5, 1st revised version:
Additions and clarifications regarding visibility of interactors (section 4.6) as well as validity of ac-
(cid:136)
tionsincl. descriptionof(alreadysupported)dummyactiontypeNoAction(sections4.7and4.8.1).

OAP 1.5:
New interactor symbol types Electrification, Lighting, RotateNY and RotatePY (section 4.6).
(cid:136)
ActionsoftypeDimChangenowcanalsousesymbolicpropertiesoftypeYSwhosevalueshavetype
(cid:136)
String (section 4.8.4).
Removed all references to action type PropEdit marked as deprecated in version 1.2.
(cid:136)

OAP 1.4, 1st revised version:
Correction and clarification regarding the usage of object category MethodCall (section 4.9).
(cid:136)

OAP 1.4:
New interactor symbol type Attention (section 4.6).
(cid:136)
New action type Message (section 4.7).
(cid:136)
Clarification on the use of conditions for properties and classes with actions of type PropEdit2
(cid:136)
(section 4.8.3).
Actions of type DimChange now can also use properties representing a symbolic choice list if the
(cid:136)
mapping method symbolicPropValue2Float() is implemented (section 4.8.4).
New section describing the parameter table for new action type Message (section 4.8.7).
(cid:136)
Clarification on the usage of escape sequences in texts (section 4.10).
(cid:136)

OAP 1.3:
Correction regarding possible follow-up actions after actions of type PropEdit2 (section 4.7).
(cid:136)
Clarification on the handling of the status in the case of an action of type PropEdit2 with only one
(cid:136)
valid property (section 4.8.3).
Scopes PARENT and TOP now are supported for property value access (appendix A.4.16).
(cid:136)
Placeholder $INTERACTOR now is generally supported 92 (appendix A.4.17).
(cid:136)

91 includingthecorrespondingstatementintableVersion
92 notonlyinvalidityconditionsofinteractors

49

<!-- Page 52 -->

OAP 1.2:
The descriptions of tables and features that are not yet supported have been removed or grayed
(cid:136)
out.
(cid:136) Corrections and more detailed definition regarding the interactor concept (section 2.1).
(cid:136) Field NeedsPlanMode in table Interactor is marked as deprecated (section 4.6).
(cid:136) New interactor symbol types StartDimChange and Video (section 4.6).
(cid:136) ActiontypePropEditisdeprecated. Instead,newactiontypePropEdit2shouldbeused(section4.7).
(cid:136) New section describing the parameter tables for new action type PropEdit2 (section 4.8.3).
(cid:136) More detailed definition regarding material images for property values in PropEdit2 dialogs
(section 4.8.3).
(cid:136) In field Dimension in table DimChange (section 4.8.4) now it is possible to specify the change
direction for a given dimension.
Furthermore, table DimChange now gets additional fields Separate and ThirdDim.
Note: If an existing project is ported to OAP 1.2, any existing table DimChange must be adapted!
(cid:136) In table CreateObj PosRotMode AttachAreas was removed (section 4.8.5).
(cid:136) New section describing parameter table ExtMedia (section 4.8.8).

OAP 1.1:
(cid:136) New interactor symbol type OnOff (section 4.6).

50