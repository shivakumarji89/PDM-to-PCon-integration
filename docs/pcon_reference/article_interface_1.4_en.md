# article_interface_1.4_en

> Auto-generated from article_interface_1.4_en.pdf for AI consumption.

---


<!-- Page 1 -->

# The OFML Interfaces Article and CompositeArticle

### Document version 1.4

### Thomas Gerth, EasternGraphics GmbH (Editor)

May 12, 2025

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

1 Introduction 3

2 Interface Article 4
2.1 OFML program . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
2.2 Initialization and article codes. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
2.3 Other State . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6
2.4 Product data . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9
2.5 Features and variant text . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 13
2.6 Persistence and update . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 16
2.7 Consistency check and price date . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19
2.8 Others . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 20

3 Interface CompositeArticle 23
3.1 Synchronization with the basket structure . . . . . . . . . . . . . . . . . . . . . . . . . . . 23

A Alphabetical index of functions 24

B Standard categories 25

C OFML variant code 27

D Update state 28

E Initialization of article instances 29

F Document history 31

1

<!-- Page 4 -->

# References

[oam] OAM – OFML Article Mappings (Specification).
Industrieverband Bu¨ro und Arbeitswelt e. V. (IBA)
[ocd] OCD – OFML Commercial Data (Specification).
Industrieverband Bu¨ro und Arbeitswelt e. V. (IBA)
[oex] OEX – OFML Business Data Exchange (Specification).
Industrieverband Bu¨ro und Arbeitswelt e. V. (IBA)
[ofml] OFML – Standardized Data Description Format of the Office Furniture Industry.
Industrieverband Bu¨ro und Arbeitswelt e. V. (IBA)
[property] The OFML Interface Property (Specification). EasternGraphics GmbH
[rec20] Code List Recommendation 20 – Codes for Units of Measure Used in International Trade.
Revision 17 (Annexes I to III), 2021.
The United Nations Economic Commission for Europe (UNECE)
(https://unece.org/trade/uncefact/cl-recommendations)
[xcf] XCF – Extensible Catalog Format (Specification). EasternGraphics GmbH

The documents (except [rec20]) are available at the Download Center of EasternGraphics
https://download-center.pcon-solutions.com
in the category OFML Specifications.

2

<!-- Page 5 -->

# 1 Introduction

The interface Article defines all functions that must be implemented by a type whose instances represent
a commercial article.
(In the following, instances representing an article are also referred to as article instances.)
The specifications in this document replace resp. update the interface specification in [ofml]!
A composite article consists of a fixed or variable number of sub-articles. A sub-article of a composite
1
article can also be a composite article itself .
TheinterfaceCompositeArticledefinesthefunctionsthatmustbeimplementedbyatypewhoseinstances
represent a composite article. It extends the interface Article, i.e. the corresponding type must also
implement all the functions of interface Article!
Functions that are related in content are combined into a method group and specified in corresponding
subsections of sections 2 (interface Article) and 3 (interface CompositeArticle).
Appendix A contains an alphabetical index of the functions.

Base type OiPlElement has a default implementation for all functions of interface Article. (Where nec-
essary/helpful, the behavior of the default implementation is explicitly described.)
However, base type OiPlElement cannot be used directly for an article instance because it does not pro-
vide a generic geometry creation. For this, see e.g. base type OiOdbPlElement derived directly from
OiPlElement.
Base type OiPart is conceptually not intended for article instances. Since types derived from it have
nethertheless been used for this purpose in the past, OiPart also has a default implementation for all
functions.
The implementation of function isCat() (interface MObject) in the base types OiPlElement and OiPart
returns value 1 (true) for the interface category @IF_Article.
However, in derived classes isCat() may be overwritten and then return value 0 for the category
@IF_Article, i.e. this instance is then not to be considered an article instance. For clients this means
that in this case no methods of this interface may be called on this instance 2 .
Appendix B contains specifications of predefined standard categories for article instances.

1
TheunderlyingsoftwaredesignpatternisComposite.
2 Ifmethodsarecallednevertheless,inthesimplercasethisonlyleadstoapoorerperformance,butinthemoresevere
casethiscanalsoleadtoanincorrectbehavior.

3

<!-- Page 6 -->

# 2 Interface Article

Functions that have not (yet) been described in the interface specification in [ofml] are marked with
.
**new**
Functions whose specification has been modified compared to [ofml] are marked with .
**mod**
Some functions have a parameter pLanguage of type String which can be used to specify the desired
language for textual components of the return value. The language must be specified as a two-character
abbreviation according to ISO 639-1, e.g.: (German) and (English).
de en

### 2.1 OFML program

(cid:136) getProgram() → Symbol
The function returns the ID of the OFML program to which the implicit instance belongs.
The program defines, among other things, which instance of OiProgInfo registered in the global
planning instance (base type OiPlanning) is used to perform general program-related tasks.
Furthermore, the program defines which product database (instance of OiProductDB) registered in
the global product data manager (base type OiPDManager) contains the commercial data for the
article represented by the implicit instance.
3
Conceptually, this function belongs to the interface Base . However, due to its use when deter-
miningtherelevantproductdatabase(seeabove), theprogramIDhasaspecialmeaningforarticle
instances.
The default implementation of interface Base delegates the request to the next planning element
(instance of OiPlElement) higher up in the object hierarchy.
The default implementation in OiPlElement is based on a member variable which is initialized
during the creation and initialization of the article instance (see also appendix E).

### 2.2 Initialization and article codes

(cid:136) setArticleSpec(pSpec(String)) → Void
**mod**
The function assigns an article number to the implicit instance.
The article number is an alphanumeric code that uniquely identifies a manufacturer’s product
(article) within the leading production and planning system (PPS). If it is a configurable article,
the article number is also referred to as the basic article number, in contrast to a (possibly) addi-
tionally specified extended final article number which identifies the fully configured product (see
setXArticleSpec() below).
Asaresultofthefunction,theinstanceshouldhavethecharacteristics(properties)thataredefined
in the relevant product database 4 for the initial (basic) configuration of the article.
Whether the corresponding geometric representation is also available in the result of the function
dependsontheimplementationinthespecifictypeused. Forreasonsofperformance,thegeneration
ofthegeometricrepresentationcanbedelayeduntilthesubsequentcalloffunctionsetXArticleSpec()
(see below), which assigns a (possibly empty) variant code to the implicit instance.

For example, the implementation in the base type OiOdbPlElement generates only the ini-
tial properties using the method setupProps() of the global product data manager (base type
OiPDManager).

Thefunctionhasnoeffectifitiscalledbetweenthepersistencerules START_EVAL and FINISH_EVAL
for the global planning instance.

3 andwillbedescribedtherewhentheOFMLspecificationin[ofml]isrevised
4 TherelevantproductdatabaseisdeterminedbasedontheprogramIDoftheimplicitinstance,see2.1.

4

<!-- Page 7 -->

getArticleSpec() → String |Void
(cid:136) **mod**
The function returns the (base) article number of the article represented by the implicit instance
or a value of type Void if there is no article specification for the implicit instance.
IftheresultofthefunctionisavalueoftypeVoid,noentryiscreatedfortheinstanceinthebasket
structure of the application.
The default implementation delegates the request to the method object2Article() of the global
product data manager (base type OiPDManager), passing the implicit instance as the argument.
For reasons of performance, concrete types whose instances represent an article should overwrite
this implementation and return the value of a corresponding member variable to which the article
number is assigned that was passed to function setArticleSpec() (see above). This principle is used,
for example, in the implementation in base type OiOdbPlElement.

getArticleParams() → Any
(cid:136) **mod**
The function returns the parameters of the implicit instance, which are to be used in addition to
the type of the instance in order to determine the article number.
The function is relevant only for types that do not have their own implementation of method
getArticleSpec()usingacorrespondingmembervariable(seeabove),andwhoseinstancescanrepre-
sent different articles. Function getArticleParams() is then called from method object2Article() of
the global product data manager (base type OiPDManager).
ReturnvalueisaVectorwiththeparametervaluesoraStringthatalreadycontainstheparameter
values converted into the respective persistence format. If no parameters are required to determine
the article number, the function returns a value of type Void.
The default implementation returns a value of type Void.
The implementation in base type OiPlElement delegates to the equal named method of the global
product data manager (base type OiPDManager), passing the implicit instance as the argument.
The global product data manager then uses external mapping tables to determine the parameters.
The mapping tables are standardized in OFML Part VI (OAM) [oam].

setXArticleSpec(pType(Symbol), pSpec(String)) → Void
(cid:136) **mod**
The function assigns an article specification of the specified type to the implicit instance.
The following specification types are defined:
@Base
Basicarticlenumber: uniqueidentifierofthemanufacturerforthearticlewithoutreferenceto
a specific design/configuration.
@VarCode
Manufacturer-specific variant code: describes the specific design/configuration of the article.
@OFMLVarCode
Manufacturer-independent variant code, also called the OFML variant code: describes the
specific design/configuration of the article.
The OFML variant code should be used by OFML applications to restore saved article confi-
gurations (see section. 2.6). Its structure is described in appendix C.
@Final
Manufacturer-specific final article number: identifies the article and describes its specific
design/configuration.
Normally, the final article number is composed of the basic article number and the variant
code. However, this depends on the underlying product database.
Ifanarticlespecificationoftype@Baseispassed,thefunctionbehaveslikefunctionsetArticleSpec(),
see above.

5

<!-- Page 8 -->

The commercial initialization of an article instance is done by immediately successiv calls to
setArticleSpec() (or setXArticleSpec() with specification type @Base ) and setXArticleSpec() with
specification type @VarCode .
The passed variant code can be an empty string. The article instance will then keep the initial
(basic) configuration created during setArticleSpec().
The passed variant code can be partially determined, i.e. it can only code the properties that are
to be evaluated differently from the basic configuration.
If a variant code or a final article number is passed that does not match the article represented by
the implicit instance, the instance retains the configuration generated up to that point or only part
of the properies coded in the passed specification are re-evaluated.
When assigning a variant code or a final article number, the implicit instance in the result of the
function also has the geometric representation corresponding to the created article configuration.

(cid:136) getXArticleSpec(pType(Symbol)) → String |Void
**mod**
Thefunctionreturnsthespecificationoftherequiredtypeforthearticlerepresentedbytheimplicit
instance.
Ifthereisnoarticlespecificationoftherequiredtypefortheimplicitinstance, thefunctionreturns
a value of type Void.
The possible specification types are described with function setXArticleSpec() (see above).
If an article specification of type @Base is passed, the return value corresponds to that of function
getArticleSpec() (see above).
ThestandardimplementationdelegatestherequesttomethodgetArticleSpec()forspecificationtype
@Baseandtoequalnamedmethodoftheglobalproductdatamanager(basetypeOiPDManager)for
all other specification types, passing the implicit instance and the specification type as arguments.
The standard implementation for the specification type @OFMLVarCode must not be overwritten!

### 2.3 Other State

getObjState(pStateType(Symbol)) → Any
(cid:136)
**new**
The function returns the current value of the implicit instance regarding the state of the specified
type.
ThisfunctionisalreadydefinedforthebasicinterfaceBase. Thedefaultimplementationofinterface
Article overrides the implementation inherited from interface Base as follows:
It handles the state types and (see below) and calls the
@OI_UpdateState @OI_ConsistencyState
inherited implementation for all other state types 5 .
Thestatetype@OI_UpdateStatereferstotheupdatestatethatdefinestheusabilityofthecurrently
installed product database.
Thepossiblevalues(oftypeSymbol)fortheupdatestateandthefunctions usedduringtheupdate
of article instances are specified in section 2.6.
The state type @OI_ConsistencyState refers to the consistency state containing the result of the
last call of method checkConsistency(), see section 2.7.
Immediatelyaftercreatingthearticleinstance,theconsistencystateisundefined,whichisexpressed
with a value of type Void.
Theconsistencystateisstoredinamembervariableofthearticleinstanceandisusedastheresult
of checkConsistency() (instead of actually performing the check) if the article instance has not yet
been updated resp. could not be updated (see state type @OI_UpdateState above) after loading
from a dump representation (see section 2.6).

5 ThedefaultimplementationofinterfaceBasehandlesstatetypesrelatedtoflagsthataremanagedintheOFMLruntime
environmentforeachobject.

6

<!-- Page 9 -->

isUp2Date() → Int
(cid:136) **new**
The function returns the value 1 (true) if the currently installed product database may be to be
used to change the configuration of the implicit article instance.
The result is the current update status according to function getObjState() (see above) for state
type @OI_UpdateState : The return value is 1 if the current update status is @Up2Date , otherwise
0.

setObjState(pStateType(Symbol), pValue(Any)) → Void
(cid:136)
**new**
The function assigns a new value to the implicit instance regarding the state of the specified type.
This function is already defined for the basic interface Base. The default implementation of inter-
face Article overrides the implementation inherited from interface Base as follows:
It handles the state types and (see function
@OI_UpdateState @OI_ConsistencyState
getObjState() above) and calls the inherited implementation for all other state types.
Inthecaseofachangedvalueforstatetype @OI_UpdateState ,thedefaultimplementationperforms
the following actions in addition to assigning the value to a member variable:
– Ifthenewstateis @Migratable or @Invalid (seeappendixD),allcurrentlyeditableproperties
aredeactivated(seemethodinvalidateProperties()intheinterfaceProperty). Thus,thearticle
instance can not (anymore) be configured in these states.
– Ifthenewstateis@Up2Date(seeappendixD),aneventoftype@ArticleUpdatedissenttothe
global ChangeManager (instance of base type OiChangeManager), with the implicit instance
as the publisher and the old state as the event argument.

getAddStateCode(pDomain(Void | Symbol)) → String |Vector
(cid:136) **new**
Thefunctionreturnsacodethatdescribesthestateoftheinternalvariablesoftheimplicitinstance,
whichdifferfromthestateimmediatelyafterthecreationandcommercialinitializationofthearticle
instance 6 .
This code is primarily required and retrieved by OFML applications that store the state of article
instances in a persistent basket structure, see section 2.6.
The code returned by this function should not contain any representation of the current article
configuration, as this is already returned by function getXArticleSpec() (see section 2.2).
If the parameter pDomain is a value of type Void, the complete additional state code has to be
supplied. The code is then split into separate sections for different domains and the return value is
a vector of vector pairs, each describing the state of a specific domain:
1. domain (Symbol)
2. code (String)

sample: [[@Domain1, "Code1"],[@Domain2, "Code2"], ...]

OFML applications use this variant of the function call when creating a persistent basket represen-
tation of the article instance.
Ifaclienthasknowledgeaboutspecificdomainsandwantstogettheadditionalstatecodeonlyfor
a specific domain, this can be specified in parameter pDomain. In this case, the return value is a
7
string containing only the code for the requested domain , or an empty string if the domain is not
supported by the type of the implicit instance.
The default implementation returns an empty vector if the parameter pDomain is a value of type
Void, otherwise an empty string.

6 Therefore,thiscodeiscalledtheadditionalstatecode.
7 e.g. "Code1"fordomain@Domain1

7

<!-- Page 10 -->

When this function is overridden in a derived class (together with associated function
setAddStateCode(), see below), the following rules should be observed:
– IftheparameterpDomainisavalueoftypeVoid,theinheritedimplementationmustbecalled
first. Then the own domain section has to be added (if any).
– If the parameter pDomain is not a value of type Void, the corresponding code is returned if
the domain is supported by the class. Otherwise, the result of the inherited implementation
has to be returned.
– To avoid naming conflicts with domain identifiers, it is recommended to use the name of the
class itself for the section that the class inserts into the code.
The domain @ChildProps is reserved for Meta types.
If necessary, a class/implementation can define multiple domains.

(cid:136) setAddStateCode(pDomain(Void | Symbol), pCode(Vector | String)) → Void
**new**
The function assigns the specified additional state code to the implicit instance.
Thiscodedescribesthestateoftheinternalvariablesoftheimplicitinstance, whichdifferfromthe
state immediately after the creation and commercial initialization of the article instance.
If the parameter pDomain is a value of type Void, the complete additional state code is passed in
the form of a vector containing information about all relevant domains. For the structure of this
vector see specification of function getAddStateCode() above.
IftheparameterpDomainisnotavalueoftypeVoid,onlythecode(String)relevanttothisdomain
is passed.
The client is expected to use the same value for parameter pDomain as it did when calling
getAddStateCode() to get the passed code.
OFMLapplicationsusethefunctionwithavalueoftypeVoidforparameterpDomainwhenrestoring
an article instance from a saved basket representation. In doing so, the call is made after the saved
8
commercial configuration was restored by calling setupConfiguration() (see section 2.6) .
The default implementation is empty, i.e. no actions are performed.
When this function is overridden in a derived class (together with associated function
getAddStateCode(), see above), the following rules should be observed:
– If the parameter pDomain is a value of type Void, the section to be handled by the class must
first be extracted from the passed code. Then the inherited implementation must be called
passingthe(possibly)truncatedvector. Finally,thecodefortheown(extracted)domainmust
be processed (if any).
– If the parameter pDomain is not a value of type Void, the passed code will be processed if the
domain is supported by the class. Otherwise, the inherited implementation must be called.

8 Therefore, analogous to the definition for function getAddStateCode() above, the passed code should not contain any
representationofconfigurablepropertiesofthearticle.

8

<!-- Page 11 -->

### 2.4 Product data

Preliminary remark:
Conceptually, the product data also includes feature descriptions and variant texts. Since numerous
functions are available for retrieving this information, these are dealt with in a separate section (2.5).

Different article instances can represent the same configuration of an article. Conceptually, the functions
describedinthisandthefollowingsectionshoulddeliverthesameresultsforthesamearticleconfiguration
(taking into account any language parameters that may be present).
Two article instances represent the same configuration if the following information match:
(cid:136) the OFML program ID, see function getProgram() (section 2.1)
(cid:136) the (basic) article number, see function getArticleSpec() (section 2.2)
(cid:136) the OFML variant code, see function getXArticleSpec() (section 2.2)

Applications can use this information to generate a key for product data caches in order to minimize the
numberofmethodcallsandthusimproveperformance. Ifsuchacacheisalsousedforpriceinformation,
the key must additionally encode the price date, see function getPriceDate() (section 2.7).

(cid:136) getArticlePrice(pLanguage(String), ...) → Any[] |Void
**mod**
The function returns price information for the implicit article instance.
ParameterpLanguagespecifiesthelanguagetobeusedfortextualelementsofthepriceinformation.
If an additional, optional parameter of type String is specified, it specifies the desired currency
(according to ISO 4217). However, the function does not have to provide the price information in
this currency (e.g. if the relevant product database cannot provide prices in this currency).
9
If no explicit currency is requested, the price is returned in any available currency .
If the function does not provide the price in the desired currency, the client must convert it himself
using exchange rates.
If no price information is available for the article in the product data, the function returns a value
of the type Void.
OtherwisethereturnvalueisaListcontainingtheindividualprice componentsresp. thefinalprice.
Each entry in the return list is a Vector of 3, optionally 5 elements:
1. adescription(String)specifyingthetypeorthereasonfortheexistenceofthepricecomponent,
e.g. the reason for a surcharge
2. the sales price of the price component (Float)
3. the purchase price of the price component (float)
4. (optional) the identifier of the variant condition of the price component (Void | String)
5. (optional) the factor applied to the amount from the price database when calculating the
amount of the price component (Void | Float)
Thefirstentryrepresentsanexceptionsinceitcontainstheappliedcurrency(String)insteadofthe
prices: the second element specifies the currency of the sales price and the third element specifies
the currency of the purchase price. (The other elements in this entry have no meaning.)
The last entry in the list specifies the (accumulated) final price. The optional entries in between
specify the individual price components (base price, surcharges, discounts, etc.). If such a price
component contains the description "@baseprice" in the first element, it is explicitly marked as a
base price.
Elements4and5areonlyincludedinthereturnstructureiftheseaspectsarerelevantduringprice
10
determination in the relevant product database .
9 Asarule,however,thecurrencyshouldbeexplicitlyrequestedthattheuserhassetintheapplication.
10
TherelevantproductdatabaseisdeterminedbasedontheprogramIDoftheimplicitinstance,see2.1.

9

<!-- Page 12 -->

Elements 4 and 5 in the entry for the final price are relevant only if no other price components are
included in the return list and if the final price is equal to the base price.
If the final price amount for a price type (sales price vs. purchase price) is 0.0 and if an empty
stringforthecorrespondingcurrencyisspecifiedinthefirstlistentryforthispricetype,thismeans
that there is no information on this price type for the article in the product data.
If the relevant product database supports validity periods for price components when determining
the price, the date is used that is returned by method getPriceDate() for the implicit instance (see
section 2.7).
If no price information for the article is available in the product data on this date, the function
returns the following value:

@(["@invalid_date", NULL, NULL], ["invalid price date", NULL, NULL])

The resource @invalid_date in the first list entry may be qualified with a concrete package iden-
tifier. The description of the state in the second list entry should be specified in the language
requested via parameter pLanguage.
In this case, the OFML runtime environment (additionally) has to ensure that function
checkConsistency()(seesection2.7)returnsacorrespondinginconsistencyfortheimplicitinstance.
Thedefaultimplementationdelegatestotheequalnamedmethodoftheglobalproductdatamana-
ger (base type OiPDManager), passing as arguments the implicit instance, the requested language
and the desired currency (if any).

(cid:136) getArticleText(pLanguage(String), pForm(Symbol)) → String[] |Void
**mod**
The function returns a textual description of the requested form in the specified language for the
article represented by the implicit instance.
Possible values for parameter pForm are:
@l Long description (article long text)
The article long text should describe all essential fixed (non-configurable) features of the
article 11 .
The article long text usually consists of multiple lines.

@s Short description (article short text)
The (rather technically oriented) article short text is often an abbreviated version of the long
text.
The article short text should contain only a single line.
@pn Product name
The (rather marketing-driven) product name can be used in user-oriented product views
(instead of the article short text).
The product name usually consists of a single line.
The return value is a List of strings containing the individual lines of the description or a value of
type Void if no description of the requested form is available in the specified language.
The default implementation delegates to the equal named method of the global product data ma-
nager (base type OiPDManager), passing the implicit instance, the required language and the
requested form as arguments 12 .

11
A description of the current values of the changeable/configurable properties of the article is provided by function
getArticleFeatures()(seesection2.5).
12 The default implementation in OiPDManager in turn delegates to the equal named method of the relevant product
database(basetypeOiProductDB).

10

<!-- Page 13 -->

getArticleClassifications(pLanguages(String[] |Void)) → Any |Void
(cid:136) **new**
The function returns information about the classification of the article represented by the implicit
instance.
Paramter pLanguages can be used to specify the languages (codes according to ISO 639-1 Alpha 2)
for which language-specific descriptions of the classes are to be supplied. If the parameter has a
value of type Void, no language-specific descriptions are supplied. If the parameter contains an
empty sequence (List or Vector), all language-specific descriptions stored in the product database
are supplied.
Ifnoclassificationinformationisavailableforthearticle,avalueoftypeVoidisreturned,otherwisea
(non-empty)Vectorofclassificationinformationitems. Oneclassificationinformationitemdescribes
a classification according to a specific classification system.
A classification information item is a Vector consisting of the following elements:
1. Name/identifier of the classification system, without version information or the like (String).
The following identifiers are currently predefined for cross-industry and cross-company stan-
dards:
ECLASS Classification according to standard ECLASS 13
UNSPSC Classification according to standard UNSPSC 14
Identifiers for other classification systems start with the character @. Identifiers for
manufacturer-specific classification systems consist of the character @ followed by the com-
mercial manufacturer ID.
2. Qualifier of the system, e.g. the version (String).
The string can be empty if no special qualifier is stored in the product data.
Semantics and syntax of the qualifier depend on the data format of the relevant product
database. For example, for the format version 4.3 of OCD [ocd] the following applies:
– With standard ECLASS, the qualifier is the version number in the format x.y.
– With a manufacturer-specific system, the qualifier is the part from the OCD system iden-
tifier after the manufacturer ID and the underscore.

3. Identifier of the class (String).
4. Language-specific descriptions of the class (Any[]|Void).
If parameter pLanguages has a value of type Void, then this element also has a value of type
Void. Otherwise, the element is a language–text mapping consisting of a sequence (Vector or
List) of zero or more elements, where each element again is a Vector of two elements:
1. language code according to ISO 639-1 Alpha 2 (String)
2. Text/description in the corresponding language (String)
The language code must consist of two lowercase letters. Combinations of letters that do not
correspond to any officially registered code are not explicitly permitted, but should not lead
to errors when processed by the client.
A language–text mapping must not contain two entries with the same language code!
If parameter pLanguages is an empty sequence, the language–text mapping contains all
language-specific descriptions stored in the product database.
Otherwise,themappingcontainsthelanguage-specificdescriptionsforthelanguagesrequested
in the parameter. (If no description is stored for the class for a requested language, the ID of
the class itself is used.)
13 www.eclass.eu
14 www.unspsc.org

11

<!-- Page 14 -->

The default implementation delegates to the equal named method of the global product data ma-
nager (base type OiPDManager), passing the implicit instance and the required languages as argu-
ments 15 .

getPDInfo(pLanguage(String)) → Any[] |Void
(cid:136) **new**
The function returns additional product information about the article represented by the implicit
instance.
Parameter pLanguage specifies the language to be used for textual information.
ReturnvalueisaVectorofinformationitemsoravalueoftypeVoidifthereisnoadditionalproduct
data information.
The content and the order of the information items depends on the relevant product database 16 .
The default implementation delegates to the equal named method of the global product data ma-
nager (base type OiPDManager), passing the implicit instance and the required language as argu-
ments 17 .
Product databases based on the commercial data format standardized in OFML Part IV (OCD)
[ocd] must provide at least the following two information items:
1. commercial manufacturer ID (String)
2. commercial series ID (String)

getOrderUnit(pLanguage(String |Void)) → String
(cid:136)
**new**
The function returns the order unit for the article represented by the implicit instance.
IfparameterpLanguageisavalueoftypeVoid,thelanguage-independentcodeaccordingtoUNECE
Recommendation 20 is returned [rec20], e.g. C62 – piece, MTR – meter and MTK – square meter.
If parameter pLanguage is a language code (type String), the unit name will be supplied in the
required language.
If the product data does not contain information about the order unit of the article, the standard
unit resp. ”piece”will be assumed and returned.
C62
Thedefaultimplementationdelegates(first)totheequalnamedmethodoftheglobalproductdata
manager (base type OiPDManager), passing the implicit instance as an argument.
If parameter pLanguage is not a value of type Void, then the name in the required language is
determined for the most common units using a text resource for the language-independent code 18 .
(If no text resource is available, the language-independent code itself is returned.)

(cid:136) getArticleAttribute(pAttr(Symbol)) → Any
**new**
Thefunctionreturnsthevaluefortherequestedattributeforthearticlerepresentedbytheimplicit
instance.
Currently the following attributes are defined:
@Discountable
The attribute of type Int specifies whether discounts can be applied to the possibly speci-
fied purchase price of the article or not. Value 0 (no) means that no discounts from the
purchasepricearepermittedforthisarticle, deviatingfromthegeneralconditioningofthe
manufacturer.
15 The default implementation in OiPDManager in turn delegates to the equal named method of the relevant product
database(basetypeOiProductDB).
16
TherelevantproductdatabaseisdeterminedbasedontheprogramIDoftheimplicitinstance,see2.1.
17 The default implementation in OiPDManager in turn delegates to the equal named method of the relevant product
database(basetypeOiProductDB).
18
seeglobalfunctionoiGetOrderUnitDescr()

12

<!-- Page 15 -->

If an undefined attribute is requested or if the product data for the article does not contain infor-
mation about the attribute, a value of type Void is returned.
The default implementation delegates to the equal named method of the global product data ma-
nager (base type OiPDManager), passing as the first argument the object supplied by method
getArticleObj() (see above) of the implicit instance, and as the second argument the requested
attribute.

Notes on the functions getPDInfo(), getOrderUnit() and getArticleAttribute():

These functions were introduced in this order with time intervals and all serve to retrieve specific
(cid:136)
informationaboutanarticle. Fromaconceptualpointofview,auniform,generalfunctionwouldbe
desirable,sothatanewfunctiondoesnothavetobeintroducedwitheverynewrelevantinformation.
This was addressed with the introduction of function getArticleAttribute(). However, for reasons of
downward compatibility, the other two functions were retained.
For performance reasons, it is often desirable for clients to be able to retrieve several pieces of
(cid:136)
information of different types with one function call. However, since the needs of different clients
differwithregardtothescopeoftheinformationtoberetrieved, suchafunctioncannotbedefined
generally in the context of the interface Article. Therefore, this must be done in specific OFML
libraries if required.

### 2.5 Features and variant text

(cid:136) getArticleFeatures(pLanguage(String |Void) → Any
**mod**
The function returns a description of the currently defined configurable properties (features) of the
article represented by the implicit instance.
The function either returns a value of type Void if there is no feature description for the implicit
instance, or a list of Vectors:
1. property (String)
2. current property value (String |Void)
The content of the vector elements depends on the parameter pLanguage:
– If the parameter has a value of type Void, language-independent identifiers for properties and
19
values are returned. (Numeric values are converted into type String for this purpose ).
This form of function call can be used by OFML applications to generate a description of
the article configuration that can be exported to an external production and planning system
(PPS) for order processing.
– If the parameter contains a language code (type String), the names of properties and values
are supplied in the required language. The value element can be a value of type Void, see
below.
This form of function call is used by OFML applications to generate the so-called variant text.
The following rules apply to this:
* Each vector in the return list creates one line of the variant text.
(Therefore,thestringsintheelementsforpropertyandvaluethemselvesmustnotcontain
20
any characters for a line break .)
* If the value element is of type Void, the property element contains the complete line for
the variant text.
This can be used for multi-line descriptions of features (which are then realized by imme-
diately consecutive entries in the return list).
19 seeconstructorsoftypeString
20 Iftheydo,theyarereplacedbytheapplicationswithaspacecharacter.

13

<!-- Page 16 -->

If both vector elements contain a string, the line of the variant text results from the
*
concatenation of both strings, separated by the string ” : ”.
In both forms, the return list contains only currently visible/valid configurable properties with a
defined value. An exception are not selected valid optional properties with a special description
for the unselected state: these are included in the return list if parameter pLanguage contains a
language code.
On the other hand, certain defined and visible configurable properties can be omitted in the return
list for the variant text. This can be the case if the feature is indirectly described by dependent
features, see e.g. the text control code in the OCD property table [ocd].
The default implementation delegates to the equal named method of the global product data ma-
nager (base type OiPDManager), passing the implicit instance and the desired language as argu-
21
ments .

getArticleFeatures2(pLanguage(String) → Any
(cid:136) **new**
The function returns an alternative description of the currently defined configurable properties
(features) of the article represented by the implicit instance.
The function either returns a value of type Void if there is no feature description for the implicit
instance, or a list of Vectors, each describing one property:
1. language-independent identifier of the property (String)
2. language-specific name of the property (String)
22
3. current property value (String |Void)
4. language-specific description of the value (String)
The language-specific elements are returned in the language specified by parameter pLanguage.
The return list contains only currently visible/valid configurable properties with a defined value.
Anexceptionarenotselectedvalidoptionalpropertieswithaspecialdescriptionfortheunselected
state: these are included in the return list with a value of type Void in the 3rd element.
IncontrasttofunctiongetArticleFeatures()(seeabove),forpropertyvalueswithamulti-linedescrip-
tion (variant text) only the first line is used/returned in the 4th element (see also the text control
code in the OCD property table [ocd]).
Thedefaultimplementationdelegatestotheequalnamedmethodoftheglobalproductdatamana-
ger(basetypeOiPDManager),passingtheimplicitinstanceandthedesiredlanguageasarguments.

(cid:136) getAllArticleFeatures(pLanguage(String) → Any
**new**
The function returns a description of all current property assignments (features) of the article
represented by the implicite instance.
IncontrasttofunctionsgetArticleFeatures()andgetArticleFeatures2()(seeabove), thiscaninclude
internal properties that are not visible/configurable for the user.
The function either returns a value of type Void if there is no feature description for the implicit
instance, or a list of Vectors, each describing one property:
1. language-independent identifier of the property (String)
2. language-specific name of the property (String)
23
3. current property value (String |Void)
4. language-specific description of the value (String)
5. Flag (Int) indicating whether the property is visible/configurable (1) or not (0).
21
ThedefaultimplementationinOiPDManagerinturndelegatestomethodgetPropDescription()oftherelevantproduct
database(basetypeOiProductDB).
22
NumericvaluesareconvertedintotypeString.
23
NumericvaluesareconvertedintotypeString.

14

<!-- Page 17 -->

The language-specific elements are returned in the language specified by parameter pLanguage.
The transmission of internal properties is optional, i.e. it depends on the implementation and the
data format of the relevant product database 24 .
If there is no language-specific name or no language-specific description for the value of an internal
(non-visible) property in the product data, the 2nd element contains an empty character string
resp. the 4th element is identical to the 3rd element.
The return list contains only properties that currently have a defined value. An exception are
not selected valid optional properties with a special description for the unselected state: these are
included in the return list with a value of type Void in the 3rd element.
Thedefaultimplementationdelegatestotheequalnamedmethodoftheglobalproductdatamana-
ger(basetypeOiPDManager),passingtheimplicitinstanceandthedesiredlanguageasarguments.

getArticleFeaturesDescr(pType(Symbol), pLanguage(String) → Any
(cid:136) **new**
The function returns a description of the properties (features) of the article represented by the
implicit instance.
The desired form of the description is specified in the parameter pType.
The language-specific elements are returned in the language specified by parameter pLanguage.
Currently, the following description types are defined:
@Text
The description corresponds to the result of the function call
getArticleFeatures(pLanguage)
@AllIDs
The description corresponds to the result of the function call
getAllArticleFeatures(pLanguage)
@ID_Text
The function either returns a value of type Void if there is no feature description for the
implicit instance, or a list of Vectors, each describing a currently defined configurable
property:
1. language-independent identifier of the property (String)
2. current property value (String |Void) 25
3. List of String pairs (type Vector), each specifying one line of the language-specific
description of the feature
The first string is intended for the language-specific name of the property and the
second for the language-specific description of the value. For the creation of the cor-
responding line of the feature description on part of the client the regulations apply
which are mentioned with function getArticleFeatures() (see above) for the creation of
the variant text.
The return list contains only currently visible/valid configurable properties with a defined
value. Anexceptionarenotselectedvalidoptionalpropertieswithaspecialdescriptionfor
the unselected state: these are included in the return list with a value of type Void in the
2nd element.
On the other hand, certain defined and visible configurable properties can be omitted in
the return list. See also the correspondig comment for function getArticleFeatures() (see
above).
ThedefaultimplementationcallsfunctiongetArticleFeatures()fordescriptiontype @Text andfunc-
tiongetAllArticleFeatures()fordescriptiontype @AllIDs . Forallotherdescriptiontypes,delegation
ismadetotheequalnamedmethodoftheglobalproductdatamanager(basetypeOiPDManager),
passing the implicit instance, the required description type and the desired language as arguments.
24
TherelevantproductdatabaseisdeterminedbasedontheprogramIDoftheimplicitinstance,see2.1.
25
NumericvaluesareconvertedintotypeString.

15

<!-- Page 18 -->

### 2.6 Persistence and update

Inprinciple,thefollowingtwoformsofapersistentrepresentationofanarticlecanandmustbeconsidered:
Dump representation
In this form, the complete internal state (member variables) of the OFML instance itself, which
represents an article, is serialized.
ApplicationscanusethisformtosaveacompleteOFMLsceneortowritethestateoftheOFML
instance to the clipboard resp. to restore the instance from the state saved in the clipboard.
When saving and loading a dump, the persistence rules specified in [ofml] are applied.
The dump format is not standardized 26 .
Basket representation
In this form, all relevant information about the article is saved, which is necessary to be able to
(further) process it in order transactions. This also includes information needed to recreate the
OFML instance, e.g. if the article is to be reconfigured.
ThefollowinginformationisrequiredtorecreatetheOFMLinstancefromabasketrepresentation:
the OFML program ID, see function getProgram() (section 2.1)
(cid:136)
the (basic) article number, see function getArticleSpec() (section 2.2)
(cid:136)
the OFML variant code, see function getXArticleSpec() (section 2.2)
(cid:136)
the so-called AddStateCode, see function getAddStateCode() (section 2.3)
(cid:136)
The basket format is not standardized 27 .

The functions specified below in this section are used to implement a general concept for the handling of
savedarticlesinrelationtothecurrentlyinstalledproductdata. Thesemaydifferfromtheproductdata
with which the article was last created resp. reconfigured and saved.

The basic regulations of this concept are:
(cid:136) Immediately after loading a saved planng or a saved basket, the articles contained in it have all the
characteristics (configuration, texts, price) as at the time of saving.
Initially, the state of the articles in relation to the currently installed product data is
unknown/undefined(Undefined),becauseusuallytheversionoftheproductdatausedwhensaving
is not known and it must be assumed that the product data has changed in the meantime.
If the used basket format provides for saving the version of the used product data, after comparing
the saved version with the version of the currently installed product data, where appropriate, the
28
application also can setthe state of the concernedarticles to up-to-date/updated (Up2Date) . This
optiondoesnotexistforsavedOFMLscenes(dumpformat),becausetheinterfaceArticle(currently)
does not provide for assigning the product data version to an article instance.
(cid:136) In order to be able to edit (reconfigure) the article or to use texts and prices from the currently
installed product data, the article has to be updated.
After the update, the article is in the state up-to-date/updated ( Up2Date ).
As long as an article is not in this state, it cannot/may not be changed (offer commitment)!
Before an article is updated, it must be determined whether the article can be updated at all. To
(cid:136)
this end, it must meet the following conditions:
1. The article is contained in the currently installed product data in the same commercial series.
2. The saved configuration of the article can be restored with the currently installed product
data, i.e., all properties that can be changed (configured) by the user according to the saved
26 ApplicationsofEasternGraphicsusetheFMLformat.
27
ApplicationsofEasternGraphicsusetheOBXformat.
28
TheOBXformatusedinapplicationsofEasternGraphicscurrentlydoesnotprovidethisoption.

16

<!-- Page 19 -->

configuration can also be configured with the current product data and the saved values of
these properties are also valid with the current product data 29 .
The manufacturer-independent OFML variant code is recommended as the basis for checking the
updatability, see section 2.2 and appendix C.
After the updatability check, the article can be in 3 states:
– Invalid , if condition 1 is not met
– Updatable , if both conditions are met
– Migratable , if condition 1 is met but not condition 2
30
The updatability check is conceptually a separate step, independent of the actual update . From
the user’s point of view, however, the applications usually combine both steps into one action.
(cid:136) Migrationisaspecialformofupdatingthatacceptsthatthesavedconfigurationcannotberestored
exactlythesame. Duringthemigration,anattemptismadetoadoptasmanyofthesavedproperty
values as possible.
It is up to the OFML applications whether they support the migration, and if so, whether and in
what form the user is involved.

Appendix D contains a graphical representation of the possible states and their relationships.

The basic principles described above are supplemented by the following specific provisions:
(cid:136) Composite articles may only be updated in their entirety, i.e., as soon as one of the articles in the
compound cannot be updated, all other articles in the composition may not be updated either.
(cid:136) Anarticleinstancethatwasinsertedviacopy/cut and pasteadoptsthe updatestateoftheoriginal
instance.

The following functions are used to implement the concept described above:

setupConfiguration(pBaseArticle(String), pArticleCode(String), pCodeType(Symbol),
(cid:136)
pMigration(Int)) → Int
**new**
The function assigns the passed basic article number to the implicit instance and then tries to
create/restore the configuration described by the passed article code on the basis of the currently
installed product data.
The product database to be used is determined based on the program ID of the implicit instance,
see 2.1.
Parameter pCodeType is used to specify the type of the passed article code. Currently the types
@VarCodeand@OFMLVarCodearepermitted,seefunctionsetXArticleSpec()insection2.2. According
to the recommendation in the concept described above, it is preferable to use the manufacturer-
31
independent OFML variant code .
This function is primarily intended for restoring an article instance from a saved basket represen-
tation.
If no product database is installed for the OFML program of the implicit instance or if it does not
contain an article with the specified basic article number, the configuration of the implicit instance
32
remains unchanged , its update state is set to @Invalid and the return value is 0.
If the configuration can be completely restored, the update state of the implicit instance is set to
@Up2Date and the return value is 1.
29
Therefore,thisconditionisnotmetifaconfigurablepropertyisnot(nolonger)containedinthecurrentproductdata
or is not (no longer) configurable, or if a stored value of a configurable property is not (no longer) valid in the current
productdata. Ontheotherhand,aconfigurablepropertyaddedinthecurrentproductdatadoesnotviolatethecondition.
30
Thisisreflectedinthefunctionsspecifiedinthissection.
31 whichappliestotheapplicationsofEasternGraphics.
32 Then,thepassedbasicarticlenumberisnotadoptedeither.

17

<!-- Page 20 -->

If the configuration cannot be completely restored and if parameter pMigration has the value 0
(false), the configuration of the implicit instance remains unchanged 33 , its update state is set to
@Migratable and the return value is 0.
If the configuration cannot be completely restored and if parameter pMigration has the value 1
(true), the article instance adopts the partially restored configuration, its update state is set to
@Up2Date and the return value is 0.
In the case of an update or migration, the basic article number and the variant code are assigned
by means of immediately successive calls of methods setArticleSpec() and setXArticleSpec() on the
implicit instance (see section 2.2).
The default implementation delegates to the equal named method of the global product data ma-
nager (base type OiPDManager).

updateConfiguration() → Void
(cid:136)
**new**
The function updates resp. migrates the configuration of the implicit article instance based on the
currently installed product data.
The product database to be used is determined based on the program ID of the implicit instance,
see 2.1.
This function is primarily intended for updating or migrating an article instance loaded from a
dump representation.
If the implicit instance is part of a composite article, the default implementation delegates the
request to the composite article instance at the highest level in the object hierarchy above the
implicit instance.
Otherwise, the default implementation behaves as follows:
1. The function has no effect if the update state is or @Invalid.
@Up2Date
2. Ifthecurrentupdatestateis@Undefined,firstthemethodcheckObjUpdatability()oftheglobal
product data manager (base type OiPDManager) is called, passing the implicit instance and
@OFMLVarCode as the code type. The update state returned by this method is then assigned
to the implicit instance, see function setObjState() (section 2.3).
3. If the current update state of the implicit instance is now @Invalid or if the update state is
@Migratable and the user does not want to perform a migration, the function will terminate.
4. Now the commercial update (@Updatable) resp. migration (@Migratable) is done by delega-
tiontotheequalnamedmethodoftheglobalproductdatamanager(basetypeOiPDManager),
passing the implicit instance as the argument.
5. Now method updateGeometry() (see below) is called on the implicit instance in order to make
adjustments to the geometry, if necessary.
6. Finally,theupdatestateoftheimplicitinstanceissetto@Up2Date,seefunctionsetObjState()
(section 2.3).

checkUpdatability(pCodeType(Symbol)) → Symbol
(cid:136)
**new**
The function checks whether the article with the base article number of the implicit instance is
containedinthecurrentlyinstalledproductdataandwhethertheconfigurationcodedinthearticle
code of the implicit instance can be completely restored with this product data.
The product database to be used is determined based on the program ID of the implicit instance,
see 2.1.
Parameter pCodeType specifies the type of article code to be used. Currently, types @VarCode and
@OFMLVarCode are permitted, see function setXArticleSpec() (section 2.2).
The return value is @Invalid if no product database is installed for the OFML program of the
implicit instance or if it does not contain an article with the basic article number of the implicit
instance.
33 Then,thepassedbasicarticlenumberisnotadoptedeither.

18

<!-- Page 21 -->

The return value is @Migratable if the product database contains the article with the basic article
number of the implicit instance, but the configuration described by the article code of the specified
type cannot be completely restored.
The return value is @Updatable if the product database contains the article with the base article
number of the implicit instance and the configuration described by the article code of the specified
type can be completely restored.
The method call does not change the update state of the implicit instance itself.
The default implementation delegates to method checkObjUpdatability() of the global product data
manager (base type OiPDManager), passing the implicit instance and the specified code type.

updateGeometry() → Void
(cid:136) **new**
The function updates the geometry of the implicit instance according to its current article configu-
ration.
ThefunctioniscalledbythedefaultimplementationoffunctionupdateConfiguration()(seeabove).
The default implementation is empty.
TheimplementationinthebasetypeOiOdbPlElementupdatestheODBobjecthierarchyaccording
to the current state of the Hash table of ODB parameters (which may have changed after the
previous commercial update resp. migration).

### 2.7 Consistency check and price date

(cid:136) checkConsistency() → Int |Void
**mod**
The function checks the consistency and completeness of the implicit instance.
If necessary, corrections or additions are made or error messages are generated.
If the consistency and completeness of the instance cannot be determined unambiguously, a value
of type Void is returned. Otherwise, the return value is 1 (ok) if the instance is consistent and
complete, and 0 if not.
If an error log has been created by the higher-level instance that initiated the consistency check of
theimplicitinstance, theerrormessagesshouldbewrittentothislog, otherwisetheycanbeissued
directly to the user by means of global function oiOutput().
The error log to be used must be retrieved from the global planning instance (type OiPlanning)
using method getErrorLog().
The data structure of the error log specified for checkConsistency() is a Hash table in which the
relevant messages are entered for each article instance. The key for the Hash table is either the
order ID of the article instance (see function getOrderID() in section 2.8 below) or its absolute
hierarchical object name (see function getName() of interface MObject).
The value for this key is a list of vectors containg these three elements:
1. the error message (String)
2. the absolute hierarchical object name of the instance that reported the error (String)
3. the name of the method in which the error was detected (String)

The behavior of the default implementation is as follows:
– If a hash table for the error log is set up in the global planning instance (type OiPlanning)
according to the method getErrorLog(), inconsistency messages are stored in this table, other-
wise the messages are issued to the user by means of global function oiOutput().
– If the update state of the implicit instance is not @Up2Date (see section 2.6 and appendix D),
the result is the return value of method getObjState() of the implicit instance for the state
type @OI_ConsistencyState (see section 2.3) and the function terminates.

19

<!-- Page 22 -->

– The commercial consistency check is done by delegation to the equal named method of the
global product data manager (base type OiPDManager), passing the implicit instance as the
argument.
The scope of the commercial consistency check depends on the implementation and the data
format of the relevant product database 34
If the relevant product database supports validity periods for price components when deter-
mining prices, it is required to check whether price information is available in the (currently
installed) product data for the price date of the implicit instance (see method getPriceDate()
below).
– Afterthecommercialconsistencycheck,adelegationismadetomethodcheckObjConsistency()
of the instance of OiProgInfo, which is registered in the global planning instance (base type
OiPlanning) for the OFML program of the implicit instance. In doing so, the implicit instance
is passed as an argument.
This can be used to perform additional program-specific checks on the implicit instance.
– The result of the consistency check is stored in the implicit instance by calling method
setObjState() for state type @OI_ConsistencyState (see section 2.3).

(cid:136) setPriceDate(pDate(String)) → Void
**new**
The function assigns the date to be used during price determination to the implicit instance.
ThedatemustbegivenintheformatYYYYMMDD.Ifthedateisnotpassedinthisformat,thefunction
has no effect.
If the implicit instance belongs to the interface category @IF_Article, the default implementation
delegatestotheequalnamedmethodoftheinstance, whichisreturnedbyfunctiongetArticleObj()
(see section 2.4). Otherwise, the default implementation assigns the passed date (if valid) to a
member variable of the implicit instance.

getPriceDate() → String |Void
(cid:136) **new**
The function returns the date to be used during price determination for the implicit instance.
If no (valid) date has been assigned to the implicit instance using method setPriceDate() (see
above), a value of type Void will be returned. Otherwise, the return value is a string in the format
YYYYMMDD.
If the implicit instance belongs to the interface category @IF_Article, the default implementation
delegatestotheequalnamedmethodoftheinstance, whichisreturnedbyfunctiongetArticleObj()
(see section 2.4). Otherwise, the default implementation returns the date that was assigned by a
previous call of method setPriceDate() resp. a value of type Void if no (valid) date was assigned
before.

### 2.8 Others

(cid:136) getArticleObj() → MObject
**new**
ThefunctionreturnstheobjectwhosemethodsofinterfaceArticlemustbeusedtogetinformation
(text, price) about the article represented by the implicit instance.
The default implementation returns the implicit instance itself.
The function can resp. must be overridden in Meta types in order to delegate to a special (encap-
sulated) child object. The type of this object must implement the interface Article!
Clientsmustcallthisfunctionandcallthefunctionsdescribedfurtherinthissectiononthereturned
object to get the article information for the implicit instance!

34 TherelevantproductdatabaseisdeterminedbasedontheprogramIDoftheimplicitinstance,see2.1.

20

<!-- Page 23 -->

getPDLanguage() → String
(cid:136) **new**
The method returns the language to be used for product data texts and property-related texts for
the implicite instance.
The default implementation 35 is based on a member variable that is initialized resp. updated at
the following times by calling method getPDLanguage() on the global planning instance (base type
36
OiPlanning) (passing the implicit instance as an argument):
– on creation of the instance
– on each change of the OFML program of the implicit instance (see section 2.1) by calling
method setProgram() (only for instances of type OiPlElement)
– on each call of method updateProperties() of interface Property [property] for the implicite
instance if the update state of the instance is @Up2Date (see section 2.6)

(cid:136) setOrderID(pID(Symbol)) → Void
The function assigns a unique order ID to the implicit instance.
The order ID can be used to synchronize a basket structure managed by the application with the
article instances in the planning hierarchy (OFML scene). The order ID is then used to assign an
article position in the basket to the instance that represents the article in the planning.
The order ID is assigned to the article instance by the global planning instance (base type
OiPlanning) immediately after its creation and is not changed for the duration of the instance’s
existence.
Ifthepositionofthearticleinstanceintheplanninghierarchychangesduetoacut/pasteoperation,
the order ID from the destroyed instance is transferred to the newly created clone instance.
The default implementation stores the passed ID in a corresponding member variable.

getOrderID() → Symbol |Void
(cid:136)
The function returns the unique order ID of the implicit instance.
IfnoorderIDhasbeenassignedtotheimplicitinstance(seefunctionsetOrderID()above), avalue
of type Void is returned. (This applies to applications that do not manage a OFML scene.)
The default implementation returns the current value of the member variable to which the ID is
assigned during setOrderID().

setCatalogInfo(pInfo(Any[])) → Void
(cid:136)
**new**
The function assigns to the implicit instance information about the entry in the catalog of the
application that was used when inserting/creating the article instance.
The information is passed as a List of vectors with two elements:
1. type of information (Symbol)
2. information (Any)
The following information types are defined:
@CatID ID of the OFML program that contains the catalog data (Symbol).
This ID can be different from the program ID of the implicit instance if the OFML
program of the article instance does not contain catalog data.
TheversionoftheOFMLpackageoftheOFMLprogramwiththecatalogdata(String).
@CatV
35 inbasetypeOiPartasofOIversion1.42.0fromfall2022
36
whoseimplementationisbasedontheapplicationcallback::ofml::app::getPDLanguage()

21

<!-- Page 24 -->

@ArtNr The basic article number (String) specified in the catalog entry.
This may differ from the basic article number of the implicit instance 37 if an article
exchange took place as a result of the assignment of the variant code from the catalog
entry (see below).
The variant code specified in the catalog entry for assigning property values different
@VarCode
from the initial (basic) configuration of the article (String).

WhichofthesepossibleinformationitemsarepassedinparameterpInfoandtheorderoftheitems
depends on the applications.
The assignment takes place immediately after the commercial initialization of the article instance
(see also appendix E).

The default implementation stores the passed information in a corresponding member variable.

(cid:136) getCatalogInfo() → Any[] |Void
**new**
The function returns information about the entry in the catalog of the application that was used
when inserting/creating the article instance.
If no information has been assigned to the implicit instance (see function setCatalogInfo() above),
a value of type Void is returned. Otherwise the return value is as specificied for parameter pInfo of
function setCatalogInfo().
The information can be used by the application to identify the catalog entry that was used when
38
inserting/creating the article instance .
The default implementation returns the current value of the member variable to which the infor-
mation is assigned during setCatalogInfo().

37 accordingtofunctiongetArticleSpec()insection2.2)
38 e.g. togetimagesthatarestoredinthecatalogforthearticle

22

<!-- Page 25 -->

# 3 Interface CompositeArticle

### 3.1 Synchronization with the basket structure

(cid:136) getSubArticleIDs() → String[]
The function returns a List or Vector containing the IDs for those child objects of the implicit
instance that have to be represented in the basket structure, i.e. which represent sub-articles.
The IDs are created and managed by the composite instance. An ID must uniquely identify a
sub-article in the context of the composite instance.
The ID of a sub-article must not change during the processing of a change of a property of the
composite article!
Possible methods for generating the IDs are:
– using the OFML type and/or the geometrical position of the child instance
– using the local name of the child instance
– using the property setting of the composite instance, that has caused the creation of the child
39
instance

(cid:136) getSubArticle(pID(String)) → MObject |Void
Thefunctionreturnsthereferencetothechildinstanceoftheimplicitinstance, thatrepresentsthe
sub-article with the specified ID.
The passed ID is expected to come from a previous call of method getSubArticleIDs() (see above)
of the implicit instance.
If there is no child instance with the passed ID, a value of the type Void is returned.

Whencreatingthe(persistent)basketrepresentation,forallsub-articlesofthecompositearticletherewill
be created a corresponding sub item (position) in the basket structure. For the sub items, the respective
ID (from getSubArticleIDs()) is saved.
Usingthis,thecompositearticleinstancecanbecompletelyrecreatedfromthebasketrepresentation(see
also appendix E).

39 butconsidersituations,whereacertainpropertysettingmayleadtothecreationofmorethanonechildinstance

23

<!-- Page 26 -->

# A Alphabetical index of functions

checkConsistency() ... 19
checkUpdatability() ... 18
getAddStateCode() ... 7
getAllArticleFeatures() ... 14
getArticleAttribute() ... 12
getArticleClassifications() ... 11
getArticleFeatures() ... 13
getArticleFeatures2() ... 14
getArticleFeaturesDescr() ... 15
getArticleObj() ... 20
getArticleParams() ... 5
getArticlePrice() ... 9
getArticleSpec() ... 5
getArticleText() ... 10
getCatalogInfo() ... 22
getObjState() ... 6
getOrderID() ... 21
getOrderUnit() ... 12
getPDInfo() ... 12
getPDLanguage() ... 21
getPriceDate() ... 20
getProgram() ... 4
getSubArticle() ... 23
getSubArticleIDs() ... 23
getXArticleSpec() ... 6
isUp2Date() ... 7
setAddStateCode() ... 8
setArticleSpec() ... 4
setCatalogInfo() ... 21
setObjState() ... 7
setOrderID() ... 21
setPriceDate() ... 20
setupConfiguration() ... 17
setXArticleSpec() ... 5
updateConfiguration() ... 18
updateGeometry() ... 19

24

<!-- Page 27 -->

# B Standard categories

The following categories are predefined for article instances:

@PseudoArticle
Theinstancerepresentsapseudo-article,i.e. itisanobjectthatdoesnotrepresentaphysical/real
article,butmerelyimplementstheinterfaceArticlefortechnical(andpossiblyhistorical)reasons.
Therefore, such instances must be handled in a special way during order processing.
If an article instance belongs to this category, a corresponding indicator is set in the persistent
basketrepresentationofthearticleandthisistransferredtotheorderprocessingviatherelevant
interfaces and data formats.
Typical use cases for this category are:
(cid:136) Planning groups and other composite articles that combine other articles from a planning
or other point of view.
(cid:136) Instances intended for planning and other auxiliary purposes (placeholder, dummies).
Typically, the article number of a pseudo article is not available/known in the manufacturer’s
ERP system, but is created artificially as part of the OFML data creation. In this case, the
manufacturer must/should be asked whether the category must be set.
If the article number is known in the manufacturer’s ERP system, it possibly is used there
also only for auxiliary purposes, e.g. for managing of typicals. Here, the manufacturer has to
determine whether the category must be set for proper order processing.
Instances that belong to category @PseudoArticle have the following requirements:
1. The instance must also belong to the interface category @IF Article.
2. Method getArticlePrice() (section 2.4) must not return a price, i.e. the return value must
be of type Void. (If this requirement is not met, the category is ignored for a given article
instance.)
OFML applications do not display a price or article number for instances of this category, but
40
may display the article short text . Furthermore, articles of this category are excluded from
commercial calculation.
See also the following categories @NonOrderArticle and @NonOfferArticle.

@NonOrderArticle
The instance represents a pseudo-article that is not relevant for order processing.
If an article instance belongs to this category, a corresponding indicator is set in the persistent
basket representation of the article. Articles with this indicator will not be included in printed
orders as well as in documents for electronic order data exchange (e.g. OEX document type
41
ORDERS [oex]) .
Article instances of this category are assumed to (also) belong to category @PseudoArticle. (If
this requirement is not met, the category is ignored for a given article instance.)
The determination of this category for a given article must be made in consultation with the
manufacturer.
If the category is set for a composite article, its sub-articles will be raised in the order document
to the level of the composite article.

40 ifavailable
41 Thecategorythereforehasnoinfluenceonbasketviews(articlelists),thatarenotexplicitlytypifiedasanorder.

25

<!-- Page 28 -->

@NonOfferArticle
The instance represents a pseudo-article that should not be shown in customer offers.
If an article instance belongs to this category, a corresponding indicator is set in the persistent
basket representation of the article. Articles with this indicator will not be included in printed
offers as well as in documents for electronic offer data exchange (e.g. OEX document type
QUOTES [oex]) 42 .
Article instances of this category are assumed to (also) belong to category @PseudoArticle. (If
this requirement is not met, the category is ignored for a given article instance.)
The determination of this category for a given article must be made in consultation with the
manufacturer.
If the category is set for a composite article, its sub-articles will be raised in the offer document
to the level of the composite article.

@SALESONLY_ARTICLE
The instance represents an article without a specific geometry.
Possible special treatments for article instances of this category are:
(cid:136) Hide when generating the image for parent article instance (if any)
43
(cid:136) No dynamic generation of an article image

42 Thecategorythereforehasnoinfluenceonbasketviews(articlelists),thatarenotexplicitlytypifiedasanoffer.
43 insteaduseofanimagestoredinthecatalogdata(ifavailable)

26

<!-- Page 29 -->

# C OFML variant code

For the structure of the OFML variant code, the provisions apply that are specified for the variant code
of the predefined OCD coding scheme KeyValueList [ocd], namely:

Every currently valid/visible configurable property is presented in order according to the OCD property
table as follows:
< class > . < property > = < value >
The semicolon is used as the separator character between the properties.
Forcurrentlynon-valuedoptionalandrestrictablecharacteristicsthevalueidentifier” VOID ”isused. When
coding the values of evaluated properties, there is no padding with blanks according to the specification
in the length field of the property table, i.e. only the significant characters are displayed.

If the manufacturer-independent OFML variant code, as recommended in section 2.6, is used to update
44
saved article configurations, the following issue can occur :
IftheOCDdataisexportedfromanERPresp. PPSsystemthatdoesnotknowtheconceptofaproperty
class, and where arbitrary property classes are generated by the export routine, the update could fail
because the properties may not be ”recognized”due to a changed property class.
Therefore, OFML applications have to offer and support an alternative updatability check, that ignores
property classes in the variant code.

44 Theproblemalsooccurswithmanufacturer-specificvariantcodes,whicharegeneratedwiththepredefinedOCDcoding
schemeKeyValueList.

27

<!-- Page 30 -->

# D Update state

Re−Creation Insertion

Undefined Up2Date

Updatability Test

Invalid Updatable Migratable

Update Migration

28

<!-- Page 31 -->

# E Initialization of article instances

When inserting an article from the catalog of an OFML application, the following process is
expected/assumed regarding the initialization of the article instance:

1. Definition of the program context.
The OFML program ID is read from the catalog data by the application. The type for the program
info object (base type OiProgInfo) and the type of the product database (base type OiProductDB)
are determined from the registration data for the installed OFML package with the program ID.
With this information the program context is defined by appropriate method calls on the global
planning instance, see the functions setProgram(), addInfo() and addProductDB() of base type
OiPlanning in [ofml].
2. Creation of the article instance.
The type to be used is determined based on the basic article number read from the catalog data
by calling method article2Class() on the global planning instance (see base type OiPlanning in
[ofml]) 45 .
This step also includes calling the initialization function initialize() for the created instance.
3. Commercial initialization.
Thisisdonebyassigningthebasicarticlenumberandthe(possiblyemptyorpartiallydetermined)
manufacturer-specificvariantcodeusingcallsofmethodssetArticleSpec()andsetXArticleSpec()on
the article instance (see section 2.2).
The basic article number and the variant code are taken from the catalog data.
4. Other initialization.
1. If the used catalog data format allows the specification of (pure) graphical variants and this is
46
supported by the application, the corresponding parameters now are assigned here .
2. Using the OFML interface Property, specific property settings can be made for the article
instance, e.g. based on user profiles.
3. Method setCatalogInfo() (see section 2.8) is used to assign information about the the catalog
entry that was used when inserting the article.
4. Method articleInserted() is called for the created article instance on the global planning in-
stance (base type OiPlanning).
47
Here, an event, e.g. @ArticleInserted, can be reported to the global ChangeManger by
the specific subclass of OiPlanning used in the respective OFML application.

When restoring an article instance based on a saved basket representation, the following process is
expected/assumed regarding the initialization of the article instance:

1. Definition of the program context.
As above, but the OFML program ID is taken from the basket representation.
2. Creation of the article instance.
As above, but the basic article number is taken from the basket representation.
45
MappingtablesstandardizedinOFMLPartVI(OAM)areusedforthis.
46 IntheapplicationsofEasternGraphicsthisconcernsresourcesoftypeOPinthecatalogformatXCF[xcf]. Theparameters
specifiedthereinareassignedtoinstancesofOiOdbPlElementusingmethodsetXArticleSpec()withthespecialspecification
type @OdbParams .
47
instanceofbasetypeOiChangeManager

29

<!-- Page 32 -->

3. Commercial initialization.
Thisisdonebyassigningthebasicarticlenumberandthemanufacturer-independentOFMLvariant
code using a call of method setupConfiguration() on the article instance (see section 2.6).
The basic article number and the variant code are taken from the basket representation.
If the article instance does not have the update status @Up2Date after the method call (see
section 2.6), the restoration has failed (and the process will be aborted).
4. Other initialization.
Here, the additional state code stored in the basket representation is assigned by calling method
setAddStateCode() on the article instance (see section 2.3).
Furthermore,methodsetCatalogInfo()(seesection2.8)isusedheretoassigninformationaboutthe
the catalog entry that was used when inserting the article. (This assumes that this information is
stored in the basket representation.)
5. Initialization of sub-articles.
In the case of a composite article, for each sub-item (position) in the basket, the SubArticleID
stored there is read and the instance representing the sub-article with this ID is determined by
calling method getSubArticle() on the composite article instance (see section 3.1).
Steps3to5arerepeatedforeachsub-articleinstance, wherethecallofsetCatalogInfo()(instep4)
is omitted for it.

Attheendofstep1(inbothscenarios),theapplicationinformstherootinstanceoftheplanninghierarchy
(basetypeOiPlanning)bycallingmethodsetCreationMode(pMode(Int))whichofthescenariosispresent.
The corresponding values for the parameter are:
0 inserting an article from the catalog
1 restoring an article instance based on a saved basket representation
After scenario 1 has ended, the mode is reset to (the default value) 0. At this point, an event of type
48
@RecreationModeFinished will be reported to the global ChangeManager . In doing so, the global
planning instance is passed as the publisher and the List of re-created top article instances as the event
49
argument .

WhenimplementingfunctionsoftheinterfacesArticleandCompositeArticle,thismodecanbetakeninto
accountifrequired. ThemodecanbedeterminedbycallingthecorrespondingmethodgetCreationMode()
50
on the global planning instance .
The mode is particularly relevant for the creation and initialization of sub-article instances of composite
articles:
0 In this scenario, the complete creation and initialization of initial sub-article instances takes place
during the methods setArticleSpec() resp. setXArticleSpec() of the composite article instance, i.e.,
steps 1 to 4 of the scenario are executed by the composite article instance for the initial sub-articles.
1 Since in this scenario steps 3 and 4 for all sub-articles of a composite article are triggered by the
application (step 5) after the composite article instance has been created and initialized, for perfor-
mance reasons no sub-article instances should be created and initialized during setArticleSpec() resp.
51
setXArticleSpec() .
Step 2 – creation of the sub-article instance including positioning – takes place during method
setAddStateCode() of the composite article instance 52 . For that purpose, the corresponding infor-
mation 53 for all (current) sub-article instances 54 have to be saved in the AddStateCode (see method
getAddStateCode(), section 2.3).
48
instanceofbasetypeOiChangeManager
49 Normally,thelistcontainsonlyasinglearticleinstance.
50 TheglobalplanninginstancecanbedeterminedusingtheglobalfunctionoiGetPlanning().
51
viasetupConfiguration()
52
Accordingly,sub-articleinstancescreatedneverthelessduringsetupConfiguration()areremovedhere!
53 atleast: SubArticleID,programID,basicarticlenumber,position,rotation
54 i.e.,alsoforsub-articleinstancesthatwereaddedorchangedinteractivelybytheuser

30

<!-- Page 33 -->

# F Document history

Version 1.4
(2025-05-12)
Clarification in section 2.2 regarding the standard implementation of function getXArticleSpec().
(cid:136)
More precise description regarding the currency specification in function getArticlePrice()
(cid:136)
(section 2.4).
Clarification in appendix E regarding the possible assignment of parameters for (pure) graphical
(cid:136)
variants.
Addition in appendix E regarding the event of type @RecreationModeFinished .
(cid:136)

Version 1.3
(2024-10-21)
Clarifications and minor stylistic improvements in the introduction (section 1).
(cid:136)
AdditionsinappendixE,especiallyregardingthecreationandinitializationofsub-articleinstances.
(cid:136)

Version 1.2
(2024-01-11)
Moved function getArticleObj() from section 2.4 to section 2.8.
(cid:136)
Description of the possibility of using product data caches for identical article configurations
(cid:136)
(section 2.4).
New function getArticleClassifications() in section 2.4.
(cid:136)
New appendix B contains specifications of standard categories.
(cid:136)

Version 1.1
(2022-05-02)
New function getPDLanguage() in section 2.8.
(cid:136)

31