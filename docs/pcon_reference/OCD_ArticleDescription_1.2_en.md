# OCD_ArticleDescription_1.2_en

> Auto-generated from OCD_ArticleDescription_1.2_en.pdf for AI consumption.

---


<!-- Page 1 -->

# Uniform customer-oriented article descriptions

### Recommendation of the standardization committee of the

*

### Industrieverband Bu¨ro und Arbeitswelt e.V. (IBA)

Document version 1.2

Editor: Thomas Gerth, EasternGraphics GmbH

October 13th, 2020

*
InteriorBusinessAssociation)(IBA)

<!-- Page 2 -->

# Contents

1 Introduction 1

2 General recommendation(s) 1

3 Structure of the article descriptions 2
3.1 Manufacturer and series name . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2
3.2 Article short or long text . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2
3.3 Variant text . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
3.4 Text for custom-made product . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3

# 1 Introduction

OCD (OFML Part IV) is used for the creation of product data required in the business processes of the
furniture trade. This includes processes on the manufacturer side as well as on the sales side (retail-
ers). From the sales point of view (customer orientation), there are two basic requirements for article
descriptions, which consist of text modules that are stored in the product data:
(cid:136)
The descriptions must be understandable for the customer.
(cid:136)
Since offers and similar business forms can contain articles from multiple manufactures, the form
of article descriptions should be consistent across manufactures.

The rules presented in this document provide a guideline for the creation of uniform customer-oriented
articledescriptions. However,astheultimatedesignauthoritylieswiththemanufacturers,theguidelines
only can have the character of recommendations.
Some of the guidelines not only influence the creation and design of the text modules in the product
data itself, but also their processing by the layout modules of the various sales software systems. This is
indicated at the appropriate places in the following sections.
In drawing up the guidelines, the standardization committee has made use of the preparatory and sup-
plementary work of the following working groups and individuals:
(cid:136)
Bundesverband Bu¨rowirtschaft
(cid:136)
Working group of wegscheider office solution gmbh, Dauphin HumanDesign Group and Vitra Holding
GmbH
(cid:136)
Mr. K¨oppchen, Kirsch & L utjohann ¨ GmbH & Co. KG
(cid:136)
Survey on measurements via the pCon information distribution list
(cid:136)
Working Group of the IT Committee of the IBA, October 7th, 2020

# 2 General recommendation(s)

(cid:136)
Since the end user (customer) usually is not a furniture specialist, the descriptions and texts must
be understandable even for non-experts.
For the internal sales team at the manufacturers, it is conceivable and useful to have shorter texts.
However, since normally no separate texts for the back office and the sales department are created
in the master data, the customer-friendliness of the texts should be given priority.

1

<!-- Page 3 -->

# 3 Structure of the article descriptions

An article description basically consists of the following sections:

1. Manufacturer and series name (can be switched off)
2. Article short or long text (incl. dimensions)
3. Variant text (description of configurable properties)
4. Text for custom-made product (optional)

No blank lines should be inserted between the individual sections, not even by the layout modules of the
applications.
The following subsections contain notes and guidelines for the individual sections.

### 3.1 Manufacturer and series name

(cid:136)
The application obtains the manufacturer and series name from the higher-level data registration
files. (Currently, proprietary formats are used for this.)
(cid:136)
Both names are written into one line by the layout module of the application separated by a space.
If both names together (including the space) do not fit into one line, a break occurs at the 1st
character of the series name.
(cid:136)
For the design of manufacturer-neutral offers the user (retailer) should have the possibility to sup-
press the display of manufacturer and series names. This has to be supported by the application.

### 3.2 Article short or long text

(cid:136)
The application gets the article short and long text from OCD tables ArtShortText resp. Art-
LongText.
(cid:136)
The article short text usually is displayed in overviews of all articles of a project (for example in
the article tree)
In article lists and forms, usually the article long text is printed. (The short text is used there only
in exceptional cases.)
(cid:136)
Thearticleshorttextshouldcontainashortdescriptionofthebasicarticleandshouldconsistonly
of one line (50 characters).
(cid:136)
The article long text must be understandable independently of the short text and should describe
all essential characteristics of the article that cannot be configured by the customer. This includes
information about the fixed dimensions (see below).
(cid:136)
The individual lines of the long text in the OCD table are considered as paragraphs, i.e. each line
can be wrapped as required by the layout module of the application (continuous text). Each new
1
line forces a line break by the application .
(cid:136)
If necessary, the fixed dimensions of the article should be described in the last line of the article
long text.
TherecommendedunitofmeasurementforGermanyismillimeter(mm),otherwisecentimeter(cm)
2
can/should be used . In the USA, inches can be used instead.
The dimensions are specified in the following order: width, depth, height.
Example: 800 x 430 x 720 mm (WxDxH)
1
Long texts that already have been created may have to be revised in order to optimally support the continuous text
display.
2 Thisresultsfromthemajorityratiosdeterminedbythesurveymentionedintheintroduction.

2

<!-- Page 4 -->

If a dimension is configurable by the customer, it is omitted in the dimension description within
the article long text (and is described instead in the following variant text).
Example with configurable table height: 1600 x 800 mm (WxD)

### 3.3 Variant text

(cid:136)
The variant text complements the article long text and describes the properties of the article that
can be configured by the customer (variants).
The application gets the text modules for this from OCD tables PropertyText (propertie names)
and PropValueText (value descriptions).
(cid:136)
In the standard case (OCD property text control code 0 ), the description of a variant is composed
of the property name and the value description, separated by the layout module using a colon and
a space character (taking into account a colon which may already be present at the end of the
property name).
(cid:136)
The individual lines of the variant text created according to the OCD property text control are
considered as paragraphs, i.e., each line can be wrapped as required by the layout module of the
application (continuous text). Each new line forces a line break by the applications.
(cid:136)
Thevarianttextshouldnotcontaincodes(abbreviations)forpropertiesand/orvalues, atleastnot
exclusively.
The applications can optionally enable the user to also display the codes.

### 3.4 Text for custom-made product

The content for this text is entered by the retailer himself.

3