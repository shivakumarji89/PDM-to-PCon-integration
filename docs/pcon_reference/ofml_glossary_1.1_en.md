# ofml_glossary_1.1_en

> Auto-generated from ofml_glossary_1.1_en.pdf for AI consumption.

---


<!-- Page 1 -->

# Libraries, Series & Co. — fundamental OFML terms

### Document version 1.1

### Thomas Gerth, EasternGraphics GmbH

### February 25, 2022

<!-- Page 2 -->

# Contents

1 Introduction 1

2 Glossary 1

A Alphabetical index of terms 5

B Conceptual Model 6

C Change history 7
C.1 Version 1.1 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
(2021-12-25)

# References

[oam] OAM – OFML Article Mappings (OFML Part VI). Specification Version 1.0.
Industrieverband Bu¨ro und Arbeitswelt e. V. (IBA)
[oas] OAS – OFML Article Selection (OFML Part V). Specification Version 2.0.
Industrieverband Bu¨ro und Arbeitswelt e. V. (IBA)
[ocd] OCD – OFML Commercial Data (OFML Part IV). Specification Version 4.3.
Industrieverband Bu¨ro und Arbeitswelt e. V. (IBA)
[ofml] OFML – Standardized Data Description Format of the Office Furniture Industry.
Version 2.0, 3rd revised edition.
Industrieverband Bu¨ro und Arbeitswelt e. V. (IBA)
[xcf] XCF – Extensible Catalog Format. Specification Version 2.10.
EasternGraphics GmbH

Legal Notice

Copyright ' 2022 EasternGraphics GmbH. All rights reserved.
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

# 1 Introduction

In this document fundamental terms are defined and explained, which are essential for the creation of
OFMLdata. TheyformtheuniformterminologicalbasisforcommunicationbothwithinEasternGraphics
and with customers and partners.
In section 2 the terms are prepared in form of a glossary. In doing so, the terms are not arranged
in an alphabetical order, but in a logically developed order. Synonyms are given where appropriate.
Furthermore, where necessary, in addition to the general explanation of terms, reference is made to
special usage conditions resp. special specifications for OFML applications.
Appendix A contains an alphabetical index of terms (including synonyms).
Appendix B provides a graphical representation of the terms and their most important relationships.

# 2 Glossary

(cid:136) sales system
– Software system, which supports the dealer with sales procedures.
– The terms explained below relate specifically to OFML-based sales systems.
– Synonym: marketing system

product
(cid:136)
– A commodity (or service) that can be produced resp. is produced and/or offered for sale by a
manufacturer or supplier.
– Products differ from each other by their constructive, material and other characteristics.
– Synonym: article

configurable product
(cid:136)
– → Product, for which some of the characteristics can be specified by the buyer resp. the user
of the sales system.

article number
(cid:136)
– Alphanumeric code, which unambiguously identifies a → product of a manufacturer or a sup-
plier within the leading production and planning system (PPS).
– Occasionally, the article number is unambiguous only within a single → commercial series of
the manufacturer (not among all series).
– In certain process chains concerning a product, beyond that also other codes can be applied,
e.g. the code in accordance with the EAN.UCC system.
– The article number, which identifies a → configurable product, is called also the basic article
number, contrary to a possibly additionally specified extended final article number, which
identifies the product as configured by the buyer resp. user. The final article number contains
the so-called variant code, which encodes the values of the configurable characteristics.

(cid:136) product classification
– Organization of → products into groups (classes) according to defined differentiation criteria
resp. from certain points of view, for example:
* functional characteristics
* design, aesthetics
* price group allocation
* statistics, disposition, ...

1

<!-- Page 4 -->

– A product can be assigned to more than one product class, if several, independent differentia-
tion criteria are applicable and required by the manufacturer or supplier.
– The assignment of a product to various product classes can change in the course of its ”‘life
cycle”’.
– There are manufacturer-independent, standardized classification systems, e.g. the eClass
model or the UN/SPSC standard. Beyond that, each manufacturer or supplier can define
and use one or more own classification systems, e.g. for the definition of → product groups,
product hierarchies etc..
– Aclassificationsystemcanhavemulti-levelstructure,i.e. leadtothedefinitionofsuperclasses
and subclasses.

product group
(cid:136)
– A group of → products, specified according to a manufacturer–specific system for → product
classification.
– While the term is used manufacturer-spreading, the criteria and aspects for the definition of a
material group differ from manufacturer to manufacturer. Material groups are often used for
rebates.
– Synonyms: commodity group, class of goods

(cid:136) commercial series
– A group of → products, that is specified according to a manufacturer-specific system for
→ product classification, that governs the distribution of the products.
– ForanOFML-basedsalessystemthedeterminationofoneorseveralcommercialseriesforthe
products of a manufacturer is obligatory. However, according to which classification system
1
this takes place, is the decision of the manufacturer . E.g., the applied classification system
could be identical to that, which is used for the definition of → product groups.
– Within a commercial series, other independent classification systems can be applied.
– A commercial series is unambiguously identified by an ID (code) within the manufacturer.
– The assignment of an article to a commercial series may not change in the course of its ”‘life
cycle”’!
– Synonyms: collection, product line

(cid:136) product data
– In the broader sense, all data, which are needed and used in order a to be able to present,
configure and order a → product in a sales system, as well as other data, which are needed for
production and supply of the product.
– In a sales system only the → commercial data and the → graphical data of a product are
relevant.
– Occasionally, the term product data in the narrower sense is also used as a synonym for com-
mercial data (e.g., compare with → product database).

1 In extreme cases, if the manufacturer cannot determine a classification system relevant for selling, all products of the
manufacturercanbeassignedtoasingle(imaginary)commercialseries.

2

<!-- Page 5 -->

commercial data
(cid:136)
– All data, which describe a → product of a commercial, i.e. of a sales point of view.
– More exactly said, all non–graphical data, which are needed and used during the selling of a
product. This covers the following main aspects:
* presentation:
short and long description (text) of the article
* configuration (relevant only for → configurable products):
descriptionoftheconfigurablecharacteristicsincludingtherelations(conditions)between
these
* pricing:
base price and (for configurable products, if necessary) extra charges
– The format for creating commercial data is standardized in OFML Part IV (OCD) [ocd].
However, the generic product data management interface specified in OFML Part III also
allows the connection of external → product databases that use other formats to describe
commercial data, insofar as these can be mapped to the data model for commercial data
2
specified in OFML Part III .

(cid:136) graphical data
– All data, that is used for the graphical visualization of a → product in a sales system.
– In the simplest case this are digital image files. For the representation in 2D and 3D views of
an OFML-based sales system the methods and formats are to be used, which are specified by
the OFML standard (OFML parts I-III).

(cid:136) catalog
– Instrument for the presentation of all or a part of the available → products of a manufacturer
or an supplier to a potential buyer.
– Acatalogcanbepresentinprintedformorinelectronicformasacomponentofasalessystem.
In latter case the catalog data must be present in a format, which can be processed by the
catalog module of the used system. In the systems of EasternGraphics up-to-date only the
proprietary format XCF is supported [xcf] 3 .
– Additionally to the pure presentation function, electronic catalogs offer the function to insert
a selected article into the planning resp. into the article list.
– The products of a manufacturer can be presented in one or more catalog, where the same
product can be registered in several catalogs. The composition of a catalog is not necessarily
bound to a system for → product classification. Thus, e.g., a catalog can cover articles from
several commercial series.

mapping data
(cid:136)
– Describe the connections between → commercial, → graphical and → catalog data.
– Are needed and used by an OFML-based sales system in order to find the suitable graphi-
cal representation for an article selected from the catalog and in order to link the graphical
representation of the article with its commercial data.
– SinceSeptember2004,thedataformatformappingsisstandardizedinOFMLpartVI(OAM)
4
[oam] .

2
Inthepast,thiswasused,e.g.,toconnectEPLdatabasesfromcompanyhi-cadGmbH.
3 TheformatforcreatingcatalogdatastandardizedinOFMLPartV(OAS)[oas]iscurrentlynotusedinpractice.
4 Untilthen,thesystemsofEasternGraphicsusedproprietarymappingformats.

3

<!-- Page 6 -->

OFML library
(cid:136)
– There are 3 different forms of OFML libraries:
→ OFML base library
→ OFML product library
→ OFML catalog library
– An OFML library is identifed by an unambiguous ID, the so-called program ID.
– Synonym: OFML program

(cid:136) OFML base library
– ContainsOFMLclassesandotherdatainaccordancewithOFMLstandard(partIII)without
reference to a concrete commercial series of a manufacturer.
– Base libraries form the developing basis for → OFML product libraries.

(cid:136) OFML product library
– Aggregation of the → commercial, → graphical, → mapping and, if necessary, → catalog data
of one or several commercial series of a manufacturer.
– A commercial series should be completely contained in the product library, i.e. including
all articles of the series. If this is not possible for certain reasons (e.g. in consequence of a
graphics-centered OFML data creation), then the following two conditions must be fulfilled:
1. article numbers are unambiguous among all commercial series of the manufacturer
2. the articles are listed in the catalog data of the respective product library
Otherwise, the OFML-based sales system cannot unambiguously determine the associated
OFMLproductlibraryforagiventriplecomposedofmanufacturerID,(commercial)seriesID
and article number. As a consequence, certain application scenarios can fail.
– The catalog data for a commercial series can be omitted, if the articles of the series are refer-
enced in another product library or in a separate → OFML catalog library.
The other way round, the catalog data of the product library can reference articles of com-
mercial series, which are not contained in the product library.
– Synonym: OFML series

OFML catalog library
(cid:136)
– Contains only → catalog data, which references articles in other → OFML product libraries.

OFML package
(cid:136)
– An actual distribution and installation unit of an → OFML library for a defined sales region,
tagged with a unique version number.
– Is not a package as a hierarchical name space in accordance with OFML part III.

product database
(cid:136)
– Database, which contains the → commercial data of one or several → commercial series of a
manufacturer.
– Fromalogicalpointofviewan→OFMLproductlibraryalwayscontainsa(dedicated)product
database for the articles resp. commercial series contained in the product library. However,
theunderlyingphysicalproductdatabasecancontainthedataforseveralproductlibraries(in
particular when using an external, non-OFML-based system).

4

<!-- Page 7 -->

# A Alphabetical index of terms

article ... 1
article number ... 1
catalog ... 3
class of goods ... 2
collection ... 2
commercial data ... 3
commercial series ... 2
commodity group ... 2
graphical data ... 3
marketing system ... 1
mapping data ... 3
OFML library ... 4
OFML library, base ... 4
OFML library, catalog ... 4
OFML library, product ... 4
OFML package ... 4
OFML program ... 4
OFML series ... 4
product ... 1
product, configurable ... 1
product classification ... 1
product data ... 2
product database ... 4
product group ... 2
product line ... 2
program ID ... 4
sales system ... 1
variant code ... 1

5

<!-- Page 8 -->

# B Conceptual Model

Illustration 1 shows a diagram of the terms and their most important relationships. A notation similar
to UML is used, where the terms/concepts are represented as classes.
The following types of relationships are pictured:
Triangles refer to a superordinate concept/term (inheritance).
(cid:136)
Diamonds refer to contained entities (aggregation).
(cid:136)
Other associations. Can be specified more precisely using <<type>> .
(cid:136)

<<belongsTo>>
n n
n Product
Product Class
1 n
article number

n
Commercial
Configurable
Material Group
Series
Product
variant code

1
n
Catalog Product Data

1
<<uses>>
Electronic Commercial Graphical
Print Catalog
Catalog 1 Data Data 0..1

1
Catalog Data
<<delivered as>>
1 0..1
Mapping Data
<<connects>>
OFML Package OFML Library
1
sales region program ID
version nr.

<<uses>> <<refersTo>>
n
Product Catalog
Base Library
Library Library
<<refersTo>>
1 1 1 1

Figure 1: Concept overview

6

| Product |
| --- |
| article number |

| Configurable
Product |
| --- |
| variant code |

| OFML Package |
| --- |
| sales region
version nr. |

| OFML Library |
| --- |
| program ID |

<!-- Page 9 -->

# C Change history

### C.1 Version 1.1

(2021-12-25)
(cid:136) Updates regarding the formats of commercial and catalog data (OCD, OAM).
(cid:136) New: Appendix with an alphabetical index of terms.
(cid:136) The conceptual model diagram has been moved to an appendix.
(cid:136) Various minor corrections and embellishments.

7