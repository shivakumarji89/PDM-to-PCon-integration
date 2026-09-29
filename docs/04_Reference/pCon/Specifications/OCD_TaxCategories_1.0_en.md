# OCD_TaxCategories_1.0_en

> Auto-generated from OCD_TaxCategories_1.0_en.pdf for AI consumption.

---


<!-- Page 1 -->

# OCD – Tax Types and Tax Categories

Document version 1.0

Editor: Thomas Gerth, EasternGraphics GmbH

### December 22, 2025

This document defines the tax types and associated tax categories standardized
within OCD (OFML Commercial Data) 1 .
It replaces the corresponding appendix in the OCD specifications from format
version 4.0 onwards.

### Contents

1 Value added tax 1

2 Eco-tax France 2
2.1 General furniture types . . . . . . . . . . . . . . . . . . . . . . . . . 2
2.2 Decoration . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
2.3 Floorings . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
2.4 Specific product types . . . . . . . . . . . . . . . . . . . . . . . . . . 4

A Alphabetical index of categories for the Eco-tax France 5

B Modification history 6

1 Copyright'2003–2025IndustrieverbandBu¨roundArbeitswelte.V.(IBA).
RequeststorecordothertaxtypesandtaxcategoriesshouldbemadetotheOFMLStandardisationCommittee.

<!-- Page 2 -->

# 1 Value added tax

Tax type identifier: VAT

The following tax categories are defined for this tax type:

standard_rate standard rate
reduced_rate reduced rate
severely reduced rate
super_reduced_rate
parking_rate parking rate
services services
zero_rate zero rate
exemption tax-exempt

1

<!-- Page 3 -->

# 2 Eco-tax France

Tax type identifier: ECO_FR

Actually,theeco-taxisnotatax,butratheravisiblefeethatservestofinancethedisposalandrecycling
of products.
The eco-tax is subject to value added tax and is not discountable.
The non-profit company Valdelia 2 is authorized by the French government to implement the legal provi-
sions relating to the Eco-tax in the B2B trade of professional object and office furniture 3 . The purpose
of the fee in this industry is to involve buyers in the disposal and recycling of bulky waste furniture.
The tax depends on the net weight 4 of the product and its tax (fee) category, which is associated with
a price factor. The net weight multiplied by this price factor produces the amount of the fee. The price
factorsvaryannuallyandareusuallypublished/updatedbyValdeliainOctoberinthedocument”Bar`eme
eco-contribution” 5 .
Thetaxcategorieslistedbelowarederivedfromthecategoriesdescribedintheabove-mentioneddocument
dated October 2025.
Apart from the special category none for products that are not subject to the fee, a tax (fee) category
refers to a defined product type (scope of use) and may be combined with a material category.
In the latter case, the identifier of a tax category is the concatenation of the identifiers for the product
type and the material category, separated by an underscore (_).
Theassignmenttoamaterialcategoryisbasedontheweightpercentage. Forexample,ifplasticmaterials
accountformorethan50percentofaproduct’sweight,itisassignedtothematerialcategoryplastics. If
no material type accounts for the majority of the weight, the product has to be assigned to the category
other.
The following subsections describe the different product types with the possible material categories.
AppendixAcontainsacomplete(alphabetical)indexofallpossibletaxcategoriesfortheEco-taxFrance.

### 2.1 General furniture types

The following general furniture types are defined:

seat furniture used for sitting
storage cabinets, rolling containers, side tables, etc.
workplace tables, desk components, and other furniture such as whiteboards
other other furniture 6

2
www.valdelia.org
3
Fortherecyclingoffurnitureintendedforprivatecustomers(B2Ctrade),organization´eco-mobilierisresponsible. Their
taxmodelisnot(yet)subjectofOFMLstandardization.
4
moreprecisely: themass
5
Thefeewasfirstimposedin2013.
6 thatdoesnotbelongtotheproductfamilieschangingrooms,pollingboothsandpartitionwalls,andthatalsodoesnot
belongtothespecificproducttypesdefinedinsection2.4

2

<!-- Page 4 -->

The following material categories are defined for these types of furniture:

metal mostly consisting of metal
7
metal95 consisting of more than 95% metal
plastics mostly consisting of plastics
wood mostly consisting of wood
other other materials or no predominant material

Example:
Tax category seat_metal is used for a seat that is mostly made of metal.

Note:
For tambour door cabinets that consist of at least 75% (but less than 95%) metal, there is a specific
product type, see section 2.4. (Therefore, the tax category storage_metal does not apply to these.)

### 2.2 Decoration

Decorative elements 8 are assigned to the product type .
decoration

The following material categories are defined for this product type:

metal mostly consisting of metal
metal95 consisting of more than 95% metal
mostly consisting of plastics, except for PVC
plastics
pvc mostly consisting of PVC
wood mostly consisting of wood
textile mostly consisting of textiles
other other materials or no predominant material

Example:
Tax category decoration_textile is used for fabric curtains.

### 2.3 Floorings

Floorings are assigned to the product type floor.

Currently, only 2 material categories are defined for this product type.

mostly consisting of PVC
pvc
other other materials except PVC

7 appliesexclusivelytofunctionalunits,nottocomponents
8 exceptforfloorings,seesection2.3

3

<!-- Page 5 -->

### 2.4 Specific product types

The following specific product types are defined:

mattress mattresses
bed_base bed bases
metal_tambour_cabinet cabinet with roller shutter door, consisting of at least 75% metal
school_furniture desks and chairs for classrooms
acoustic (soundproof) booths
acoustic_booth
cut2size_panel cut-to-size decorative panels

No material categories are defined for these product types.

4

<!-- Page 6 -->

# A Alphabetical index of categories for the Eco-tax France

Preliminary remarks:
(cid:136)
The list refers exclusively to the categories defined by Valdelia for the Eco-tax in the B2B trade of
professional object and office furniture.
(cid:136)
The new categories, which have not yet been defined in the OCD specifications, are marked with
(n) .

acoustic_booth (n)
bed_base (n)
cut2size_panel (n)
decoration_metal (n)
decoration_metal95 (n)
decoration_other (n)
decoration_plastics (n)
decoration_pvc (n)
decoration_textile (n)
decoration_wood (n)
floor_other (n)
floor_pvc (n)
mattress (n)
metal_tambour_cabinet (n)
none
other_metal
other_metal95
other_other
other_plastics
other_wood
school_furniture (n)
seat_metal
seat_metal95
seat_other
seat_plastics
seat_wood
storage_metal
storage_metal95
storage_other
storage_plastics
storage_wood
workplace_metal
workplace_metal95
workplace_other
workplace_plastics
workplace_wood

5

<!-- Page 7 -->

# B Modification history

Version 1.0 :
(2025-12-22)
(cid:136)
Initial version.

6