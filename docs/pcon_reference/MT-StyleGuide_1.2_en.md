# MT-StyleGuide_1.2_en

> Auto-generated from MT-StyleGuide_1.2_en.pdf for AI consumption.

---


<!-- Page 1 -->

# Style Guide

Title Style Guide for Metatypes
1
Author Ekkehard Beier , Annett Wiegand (EasternGraphics)
Reference Title: Metatypes Coding Style Guide
Version: 1.2
Release Date: 2012-02-06
History At the end of the document
State Release to EGR, sales partners and customers.
Subject to change
Feedback metatypes@easterngraphics.com

### go_types.csv

The name of the Metatype starts with MT_ followed by the series identifier SE_ and the name. The
name consists of upper and lower cases; each single word must start with an upper case.
The GType entry should be the same as the Metatype name but without the leading MT_.
MT_[SE_]StandardDesk;GType;;[SE_]StandardDesk;0;
Property Names start with G followed by the Series identifier and an underscore. Composite words are
specified without separators. The first letter of each word must be an upper case. The rest of the name
is arbitrary.
StandardDesk; Line;ch; Compact;3;
MT_[SE_] G[SE_] [SE_]

### go_articles.csv

In order to guarantee an unique naming of articles (qv. MT Spec go_articles, prm_set) it must be built
in the following way:
1. Metatype ID plus underscore
2. Article Number
3. optional underscore plus extension
If multiple property sets should be defined for one and the same article then add a number for
distinction
MT_[SE_] Table;HEX;SE;VP2003; MT_[SE_] Table_VP2003;
MT_[SE_] Table;HEX;SE;VP2004; MT_[SE_] Table_VP2004_1;
MT_[SE_] Table;HEX;SE;VP2004; MT_[SE_] Table_VP2004_2;
Keys of child-oriented properts should have the following structure:
1. CHP_
2. SE_
3. an arbitrary number of alphanumeric characters; each word shouls start with an upper case
MT_[SE_]Table;HEX;SE; VP2003;MT_[SE_]Table_VP2003;CHP_[SE_]Legs

### go_properties.csv

Dimensions should be given in the measurement unit that is used also in the paper pricelist. The
internal name is arbitrary as long as it follows the rules defined for go_types.

### go_childprops.csv

Children, created by property start with:
1. Series ID SE_ followed by a
2. name consisting of upper and lower cases in arbitrary sequence
CHP_[SE_]Table;G[SE_]OrgBridge;[SE_]Yes;[SE_]OrgBridge

1
Initial draft by Annett Wiegand, Andrea Schramm (EasternGraphics)

Version 1.2 page 1 of 2

|  | Title |  | Style Guide for Metatypes |
| --- | --- | --- | --- |
|  | Author |  | Ekkehard Beier1, Annett Wiegand (EasternGraphics) |
| Reference | Reference |  | Title: Metatypes Coding Style Guide
Version: 1.2
Release Date: 2012-02-06 |
|  | History |  | At the end of the document |
| State | State |  | Release to EGR, sales partners and customers.
Subject to change |
|  | Feedback |  | metatypes@easterngraphics.com |

<!-- Page 2 -->

# Style Guide

### go_attpt.csv

Attachment points should be named this way:
1. Ap (Attach Point)
2. Series ID SE_
3. In case of a child attach point: an additional CH_
4. The name, starting with an upper case followed by further upper and lower cases.
MT_[SE_]Table;Ap[SE_]CH_AddOn;CH;;G[SE_]Width*0.05;0.1;0.0;0.0
MT_[SE_]Table;Ap[SE_]TableL;L;;0.0;0.72;0.0;0.0

### go_propclasses

Property Classes hav to be named the following way:
1. starting with PC_
2. Series ID SE_
3. an arbitrary sequence of upper and lower cases
MT_[SE_]Table;G[SE_]Width;PC_[SE_]Measures

### go_actions

Messages displayed via go_actions, must start with
1. msg
2. Series ID SE_
3. an arbitrary sequence of upper and lower cases
MT_[SE_] Table; G[SE_] Width;;CON;;SET_PROP; G[SE_] AddOn; [SE_] No; msg[SE_] notPossi
ble

# HHHHiiiissssttttoooorrrryyyy

MT-Styleguide 1.2
- improved syntax highlighting
MT-Styleguide 1.1
- style for property classes added (go_propclasses)
- style for messages added (go_actions)
MT-Styleguide 1.0

Version 1.2 page 2 of 2