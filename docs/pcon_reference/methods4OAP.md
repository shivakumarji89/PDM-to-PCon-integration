# methods4OAP

> Auto-generated from methods4OAP.pdf for AI consumption.

---


<!-- Page 1 -->

# Useful OFML methods for OAP data

### Version 1.13

### Thomas Gerth, EasternGraphics GmbH

May 10, 2025

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

2 Interface Base (incl. MObject) 3
2.1 Class and Category . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
2.2 Object hierarchy . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
2.3 Spatial model . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4

3 Interface Complex 5

4 Interface Property 6

5 Interface Article 7

6 Class GoMetaType 7

7 Planning group classes 7
7.1 General Notes . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8
7.2 Element categories . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8
7.3 Methods related to common properties . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9
7.4 Other common functions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10

8 Class xOiJointPlGroup 11
8.1 Accessing topological order list . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
8.2 Other methods . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 12

9 Class xOiLayoutGroup 13
9.1 Layout elements . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14
9.2 Fork elements . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 16
9.3 Branches. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 17
9.4 Other methods . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19
9.5 Additional elements . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 23

10 Class xOiTabularPlGroup 23
10.1 General settings and information . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 25
10.2 Information on fields and layout structure . . . . . . . . . . . . . . . . . . . . . . . . . . . 26
10.3 Manipulating the layout structure . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 28

11 Class xOiCustomPlGroup 34
11.1 Layout elements . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34
11.2 Additional elements . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 36
11.3 Free attach points . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 36
11.4 Neighbors . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 37

1

<!-- Page 4 -->

12 Class xOiCustomModule 37

A Alphabetic index of methods 38

B Methods mapped to object types 42
B.1 All article types . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 42
B.2 GoMetaType . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 42
B.3 All planning group classes . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 42
B.4 xOiJointPlGroup . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 43
B.5 xOiLayoutGroup . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 43
B.6 xOiTabularPlGroup . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 44
B.7 xOiCustomPlGroup . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 45

C Document history 47

# References

[an0601] Application Note on Control Data Tables (AN-2006-01). EasternGraphics GmbH
[an oap] Application Note on OAP Data Creation. EasternGraphics GmbH
[article] The OFML Interfaces Article and CompositeArticle (Specification). EasternGraphics GmbH
[oap] OAP – OFML Aided Planning. Version 1.5. EasternGraphics GmbH
[ofml] OFML – Standardized Data Description Format of the Office Furniture Industry.
Version 2.0, 3rd revised edition.
Industrieverband Bu¨ro und Arbeitswelt e. V. (IBA)
[property] The OFML Interface Property (Specification). EasternGraphics GmbH

The specifications are available via the pCon Download Center in the category OFML Specications:
https://download-center.pcon-solutions.com

2

<!-- Page 5 -->

# 1 Introduction

Calls to OFML methods are used in OAP data creation for three purposes:

1. Realization of product logics as an action, which is bound to an interactor
2. Obtaining information about objects within expressions using syntax construct methodCall(), e.g.
for
(cid:136) validity conditions of interactors and actions
(cid:136) determining the position of interactor symbols
(cid:136) determining arguments for a MethodCall action
3. Specifying (target) objects via object category MethodCall

While in some cases specially programmed methods from project-specific classes have to be used, in
other cases methods can be used which are implemented in OFML base classes (i.e., requiring no special
programming).
This document lists and describes some useful methods of base classes that would otherwise have to be
gathered from multiple specifications or documents. In addition to the specification of each method,
there also is given an example of an application in OAP table MethodCall.
Notes:
InterfacesBase, Complex, Property[property]andArticle[article]allareimplementedinbaseclass
(cid:136)
OiPlElement. Asthisisthebaseclassforallclassesusedtorepresentarticles,allmethodsdescribed
for these interfaces can be used with/for all article instances (see also appendix B).
This document describes only the methods of the mentioned interfaces and classes that are usefull
(cid:136)
for MethodCall actions in OAP. For a full documentaion see the according specifications.

This document version reflects the state of OFML base packages OI version 1.45.0, XOI version 1.63.0
and GO version 1.18.5 contained in the application releases of Spring 2025.

# 2 Interface Base (incl. MObject)

### 2.1 Class and Category

getClass() → String
(cid:136)
The function returns the name of the direct type of the implicit instance.

MC_GET_CLASS;Instance;@IF_Base;getClass;

isCat(pCat(Symbol)) → Int
(cid:136)
The function returns 1 if the implicit instance belongs to the specified category.

MC_IS_CAT_FOOBAR;Instance;@IF_Base;isCat;@FooBar

hasMember(pName(Symbol)) → Int
(cid:136)
The function returns 1 if the class of the implicit instance has the specified member (variable or
method).
This is useful if neither getClass() nor isCat() can be used to determine whether a certain method
can be called on the target object.

MC_HAS_GET_MTID;Instance;@IF_Base;hasMember;@getMTID
(For method getMTID() see section 6.)

3

<!-- Page 6 -->

### 2.2 Object hierarchy

(cid:136) getFather() → MObject
Thefunctionreturnsareferencetothefatherobject. Iftheimplicitinstancedoesnothaveafather,
1
the result is NULL .

MC_GET_FATHER;Instance;@IF_Base;getFather;

(cid:136) getRoot() → MObject
Thefunctionreturnsareferencetotherootinstanceofthehierarchyinwhichtheimplicitinstance
is located.

MC_GET_ROOT;Instance;@IF_Base;getRoot;

Note:
As object references of OFML instances cannot be used in OAP, these methods can be employed only
for comparison with NULL (in the case of getFather()) or for comparing the results of both methods or in
combination with object category MethodCall.

E.g., a recurring requirement in OAP data creation is, that an interactor should not be displayed,
if the article instance is on the top planning level (i.e. if it is not an element of a planning group).
With the 2 methods above the corresponding condition is:

methodCall("AC_call_GET_FATHER") != methodCall("AC_call_GET_ROOT")

Or,iftheconditionshouldbelinkedwithaspecificconditioninthecase,thatthearticleinstanceis
an element of a planning group (see also section 8):

methodCall("AC_call_GET_FATHER") == methodCall("AC_call_GET_ROOT") ? 0 : <group condition>

### 2.3 Spatial model

getTrAxis() → Int
(cid:136)
The function returns the current degrees of freedom of translation of the implicit instance with
respect to the 3 individual axes of local coordinate system.
The return value results from the addition of allowed axes, where x, y and z-axis are represented
by 1, 2 resp. 4. (I.e., if return value is 0, the object cannot be moved.)

MC_GET_TRANSLATION_AXIS;Instance;@IF_Base;getTrAxis;

(cid:136) getRtAxis() → Int
Thefunctionreturnsthecurrentdegreesoffreedomofrotationoftheimplicitinstancewithrespect
to the 3 individual axes of local coordinate system.
The return value results from the addition of allowed axes, where x, y and z-axis are represented
by 1, 2 resp. 4. (I.e., if return value is 0, the object cannot be rotated.)

MC_GET_ROTATION_AXIS;Instance;@IF_Base;getRtAxis;
1
Thismaybetrueonlyiftheimpliciteinstanceistherootinstanceofanobjecthierarchy.

4

<!-- Page 7 -->

# 3 Interface Complex

getWidth() → Float
(cid:136)
The function returns the (nominal) width of the implicit instance.

MC_GET_WIDTH;Instance;@IF_Complex;getWidth;

(cid:136) getHeight() → Float
The function returns the (nominal) height of the implicit instance.

MC_GET_HEIGHT;Instance;@IF_Complex;getHeight;

getDepth() → Float
(cid:136)
The function returns the (nominal) depth of the implicit instance.

MC_GET_DEPTH;Instance;@IF_Complex;getDepth;

Typically, the objects possess some properties related to dimensions. Instead of calling the methods
above, these properties can – and should be – used!
Thisavoidspossiblepitfallsduetotheactualimplementationofthesemethodsintheclassoftheimplicit
instance. Consider the following notes on this regard:

(cid:136) It depends on the individual class of the implicit instance whether these methods return the exact
dimension according to the geometry of the object, or some other values (e.g. nominal values
according to the price list).
(cid:136) The default implementations in the base class OiPlElement behave as follows:
If a value was assigned for the width/height/depth via the according set-method, this value will
be returned. If no value was assigned via the set-method, the dimension is determinded based
on method getLocalBounds() of interface Base [ofml] and this dimension will be returned until
2
(a possible) succeeding call of the set-method .
This means, if no value was assigned until the first call of the get-method the according dimension
willbedeterminedatthattimebasedongetLocalBounds()andafterwardsallcallsoftheget-method
will return this value (unless the dimension will be explicitely changed via the set-method)!
So, these implementations cannot be used if, e.g., the dimension may be changed by the user via
an according property and the new dimension is not be assigned via the set-method!
(cid:136) The implementations in the base class GoMetaType delegate to the main child (if any), otherwise
use the inherited implementation as described above (class OiPlElement).
So, these implementations can be used, if the main child defines the according dimension of the
metatype instance and the dimension may be changed by the user only via a metatype property
causing a change of the main child due to a changed basic article number 3 .
The implementions in the base class for all planning groups xOiPlGroup determine the according
(cid:136)
dimensionbasedonmethodgetLocalBounds(),i.e.,theycannotbechangedviatheset-method,but
reflect the dimensions of the current group elements.
Thus,inthemostcasestheseimplementationscanbesafelyusedtodeterminethedimensionsofthe
group. This is important, because the group instances typically do not have dimension properties
which could be used otherwise.
2
Actually, according to the specification in [ofml], the methods should return a value determinded based on
getLocalBounds()only,ifnovaluewasassignedviatheset-method.
3 According to the described behaviour of the default implementations in OiPlElement, the first call of the get-method
afterthearticlechangethenreturnstherightdimensionvalue.

5

<!-- Page 8 -->

# 4 Interface Property

hasProperties() → Int
(cid:136)
The function returns 1, if properties are defined for the implicit instance, otherwise it returns 0.

MC_HAS_PROPERTIES;Instance;@IF_Property;hasProperties;

(cid:136) hasProperty(pKey(Symbol)) → Int
Thefunctionreturns1ifapropertywithindicatedkeyisdefinedfortheimplicitinstance,otherwise
0.

MC_HAS_PROP_FOOBAR;Instance;@IF_Property;hasProperty;@FooBar

getPropState(pKey(Symbol)) → Int
(cid:136)
The function returns the current activation state of the property of the implicit instance with the
specified key according to the old interface.
The possible state values are:
-1 non-active and non-visible
0 non-active but visible
1 active
If no property with the specified key is defined for the implicit instance, the return value is −1.

MC_GET_PROPSTATE_FOOBAR;Instance;@IF_Property;getPropState;@FooBar

(cid:136) getPropState2(pKey(Symbol)) → Int
The function returns the current activation state of the property of the implicit instance with the
specified key according to the new interface.
The possible state values are:
0 not visible (and not editable)
1 visible, but not editable
3 visible and editable
If no property with the specified key is defined for the implicit instance, the return value is 0.

MC_GET_PROPSTATE2_FOOBAR;Instance;@IF_Property;getPropState2;@FooBar

(cid:136) checkPropValue(pKey(Symbol), pValue(Any), ...) → Int
Themethodcheckswhetherthegivenvaluecanbeassignedtothepropertyoftheimplicitinstance
with the specified key.
The return value is 1 if the implicit instance has the specified property and if all checks have been
successfully completed, otherwise 0 .
If an additional optional parameter is passed, it specifies whether the passed value, if proven valid,
should be compared to the current value of the property ( 1 ) or not ( 0 , default).
If comparison is enabled, the method returns 0 if the passed value is equal to the current value of
the property.
See the interface specification [property] for a list of checks performed by the standard implemen-
tation.

MC_CHECK_PROPVALUE_FOOBAR_VAL1;Instance;@IF_Property;checkPropValue;@FooBar,@Val1

6

<!-- Page 9 -->

# 5 Interface Article

getArticleSpec() → String | Void
(cid:136)
Thefunctionreturnsthebasearticlenumberoftheimpliciteinstance, or NULL ,iftheinstancedoes
not represent an article.
Note:
Thefunction isnot applicable ifthe actualarticle instanceis encapsulatedby ametatype instance!

MC_GET_ARTICLE;Instance;@IF_Article;getArticleSpec;

# 6 Class GoMetaType

(cid:136) getMTID() → String
Returns the ID of the metatype represented by the implicite instance.

MC_GET_MT_ID;Instance;::ofml::go::GoMetaType;getMTID;
Ifitisunproved,thattheclassofthetargetobjectis::ofml::go::GoMetaType(oraderivedclass)
method hasMember() (see section 2.1) should be used to check this, as shown in the following
condition sample:
methodCall("AC_call_HAS_GET_MT_ID") && methodCall("AC_call_GET_MT_ID") == "FOO_BAR"

(cid:136) getChID() → Symbol | Void
Returns the child ID under which the implicite Meta type instance is registered in a father Meta
type instance (if any).
IftheimpliciteMetatypeinstanceisnotachildofanotherMetatypeinstance,returnvalueisNULL.
This refers to colum 1 (child key) in table go children.

MC_GET_CHILD_ID;Instance;::ofml::go::GoMetaType;getChID;
Thiscanbeused,e.g.,todisplayaninteractoronaMetatypeinstanceonlyifitwascreatedas
a child of a parent Meta type instance, as shown in the following interactor condition sample:
methodCall("AC_call_GET_CHILD_ID") != NULL
Or the interactor should only be displayed if the Meta type instance was created at a certain
position in the geometry of the parent Meta type instance:
methodCall("AC_call_GET_CHILD_ID") == @FB_Left_Sreen

# 7 Planning group classes

The XOI base library provides 4 types of planning groups, implemented in according classes:

(cid:136) xOiJointPlGroup realizes a joint planning, i.e. new elements will be added either to the right or to
the left of the already existing group elements.
(cid:136) xOiLayouGroup realizes a group with a free but continuous (2-dimensional) layout consisting of
branches.
(cid:136) xOiTabularPlGroup realizes a group with a tabular layout.
(cid:136) xOiCustomPlGroup supports the realization of groups with specific (custom) planning logics.

7

<!-- Page 10 -->

The subsequent sections describe the concept and the specific methods of these classes. However, all
planning group classes also provide some common functions, which are covered here in this section in
according subsections:

Elements of a planning group may be assigned to self-defined categories (see 7.2).
(cid:136)
Controlledbyoptionsinthecontroldatatable[an0601],propertiesmaybepulledfromtheelement
(cid:136)
level to the planning group level. The according properties on planning group level are called
common properties. Subsection 7.3 covers methods related to common properties.

Note: The examples in these subsections use class xOiLayoutGroup. If necessary, this has to be replaced
by the class actually used.

### 7.1 General Notes

(cid:136) If the interactor is bound to the planning group itself, the target object for the action, performing
a call of one of the methods described in the following sections, has to belong to category Self.
Otherwise,iftheinteractorisboundtoagroupelement,thetargetobjecthastobelongtocategory
ParentArticle (see section ”Object definitions” in [oap]).
(cid:136) Some methods require a group element as a parameter.
Iftheinteractorisboundtoagroupelement,placeholder$SELFcanbeusedforsuchaparameter.
Alternativly, or if the interactor is bound to the planning group, the element has to be specified
via expression methodCall() using methods accessing specific group elements (and not requiring a
group element as a parameter).
$SELF,
The examples in the following sections use placeholder i.e., it is assumed, that the corre-
sponding interactor is bound to a group element.
(cid:136) Some methods return object references.
As references to OFML instances cannot be used in OAP, these methods can be employed only for
comparison with NULL or in combination with object category MethodCall!
E.g., assuming a MethodCall action with identifier calling a method which
AC call NEIGHBOR R
returns the neighbor to the right (or NULL if there is no neighbor at that side), this action can
be used to write the condition
methodCall("AC_call_NEIGHBOR_R") == NULL
This condition is satisfied, if the active object has no neighbor to the right side.

### 7.2 Element categories

(cid:136) assignElementCat(pObj(MObject), pCat(Symbol)) → Void
Assigns given group element to specified category.
Insteadofangroupelement,alsoaninstancecanbepassedthatrepresentsanimmediatesubarticle
of one of the group elements. (Below, these instances are also called grand subarticles.)
If a selectability state was/is specified for the category (see method setSelectability4ElemCat()
below), this state will be applied to the given object.
Note:
If the object is up to be removed, the internal data structure containing the information regarding
the assigned element categories will be updated automatically, i.e. it is not necessary to call
removeElementCat() (see below) before the removal.

MC_ASSIGN_CAT_SEAT;Instance;::ofml::xoi::xOiLayoutGroup;assignElementCat;$SELF,@Seat

8

<!-- Page 11 -->

removeElementCat(pObj(MObject), pCat(Symbol |Void)) → Void
(cid:136)
Removes given group element from specified category.
Insteadofangroupelement,alsoaninstancecanbepassedthatrepresentsanimmediatesub-article
of one of the group elements.
If parameter pCat is NULL, the element will be removed from all assigned categories.
Note:
Ifaselectabilitystatewasspecifiedforthe/acategory(seemethodsetSelectability4ElemCat()below)
and applied accordingly to the given object, its state will not be changed at this moment!
(If necessary, this has to be done by the client.)
MC_REMOVE_CAT_SEAT;Instance;::ofml::xoi::xOiLayoutGroup;removeElementCat;$SELF,@Seat

(cid:136) clearElementCat(pCat(Symbol)) → Void
Clears specified category.
MC_CLEAR_CAT_SEAT;Instance;::ofml::xoi::xOiLayoutGroup;clearElementCat;@Seat

isElementCat(pObj(MObject), pCat(Symbol)) → Int
(cid:136)
ReturnsTrue(1)ifgiveninstanceisagroupelementoragrandsub-articleinstanceandifitbelongs
to specified element category.
MC_IS_CAT_SEAT;Instance;::ofml::xoi::xOiLayoutGroup;isElementCat;$SELF,@Seat

(cid:136) setSelectability4ElemCat(pCat(Symbol), pState(Int)) → Void
Setstheselectabilitystateforallgroupelementsorgrandsub-articleinstancesbelongingtospecified
category.
Parameter pState may have the following values:
0 the objects cannot be selected
1 the objects can be selected
If an additional optional parameter is given, it specifies whether the state should be applied hier-
archically to child objects of the affected category objects (1) or not (0, default) 4 .
(For a given category the same optional parameter should be used for both states.)
MC_CAT_SEAT_SELECTABLE;Instance;::ofml::xoi::xOiLayoutGroup;setSelectability4ElemCat;\
@Seat,1

### 7.3 Methods related to common properties

(cid:136) assignCommonPropValues(pEl(MObject)) → Void
Assigns current values of common group properties to given layout element (insofar it possesses
these properties).
MC_ASSIGN_COMMON_PROPS;Instance;::ofml::xoi::xOiLayoutGroup;assignCommonPropValues;\
$SELF

updateCommonProperties() → Void
(cid:136)
The function updates the common properties.
To be called by clients if a property has been changed which affects the visibility or the state
of common properties, where the changed property itself is not included in the set of common
properties.
MC_UPDATE_COMMON_PROPS;Instance;::ofml::xoi::xOiLayoutGroup;updateCommonProperties;\
$SELF
4 In case of value 1, methods hierSelectable() resp. notHierSelectable() (OFML interface Base) will be used (instead of
selectable()resp. notSelectable())toapplythepassedstate.

9

<!-- Page 12 -->

### 7.4 Other common functions

(cid:136) isGrandSubArticle(pObj(MObject), ...) → Any
5
Checks whether given instance is a sub-article of one of the group elements .
Additional optional parameter can be used to control the type of return value:
– If it is 0 (default), the return value is 0 (false) or 1 (true).
– If it is 1, return value is NULL, if given instance is not a grand sub-article, otherwise a Vector
containing the following information:
1. the group element being the superior article
2. the sub-article ID of the grand sub-article
Note:
In the context of OAP method calls only the default behavior is useful.

MC_IS_GRAND_SUBARTICLE;Instance;::ofml::xoi::xOiLayoutGroup;isGrandSubArticle;$SELF
This example assumes object category TopArticle for the target object.

(cid:136) checkElDistance(pOp(Symbol), pCheckVal(Float), pObj(MObject), pAttPt(Symbol |Any), ...) → Int
Compares the distance from given attach point of specified group element to other objects in the
scene with a specified value.
ParameterpAttPteitheristhekeyofanattachpointofthegiveninstanceoraspecificattachpoint
definition related to the given instance.
If an attach point definition is given, the 4th element (mode) can be omitted. Mode @Sibling is
then assumed.
If an additional optional parameter is given, it specifies a Vector of 3 Float values, defining the
offset to be applied to the coordinates (x, y, z) of the attach point position.
This may be useful/necessary in order to modify the position of a given attach point to get the
desired result 6 .
The distance is determined based on global OFML function oiGetDistance() ([ofml], section 6.10):
Thestartingpointofthesearchrayisthe(possiblymodified)positionoftheattachpointtranslated
into world coordinates. The direction of the search ray is determined based on the global PY-
rotation of the given instance and the PY-rotation to be applied to a sibling element according to
the attach point definition.
Ifnointersectionofthesearchraywithanobjectinthescenewasfound, thedistanceisundefined.
Otherwise, it is defined as the distance along the search ray from the starting point to the first
point of intersection.
Note: The (possibly modified) position of the attach point should not be inside of the geometry of
thegiveninstance. Otherwise,thesearchraymayintersectwithoneoftheinstance’sowngeometry
objects!
The following comparison operations (parameter pOp) may be applied 7 :
@GE The comparison is successful if no intersection was found or if the distance is greater than or
equal to the check value.
@GT The comparison is successful if no intersection was found or if the distance is greater than the
check value.
@LE The comparison is successful if an intersection was found and if the distance is lower than or
equal to the check value.
The comparison is successful if an intersection was found and if the distance is lower than the
@LT
check value.
5
Onlythosegroupelementswillbecheckedforsub-articleswhichrepresentarticlesthemselves.
6
AtypicalusagescenarioistoadapttheY-coordinate, asthethestandardvalue0.0maynotresultinanintersection
ofthesearchraywithasceneobject.
7 Thecomparisonsapplyanepsilonof0.0001.

10

<!-- Page 13 -->

In case of errors related to the parameters or if the comparison is not successful, the return value
is False (0), otherwise True (1).

MC_CHECK_DISTANCE_ADD_B2;Instance;::ofml::xoi::xOiLayoutGroup;checkElDistance;\
@GT,1.995,$SELF,@AP_Add_B2,[0.0, 0.4, 0.0]

# 8 Class xOiJointPlGroup

Instances of xOiJointPlGroup realize a joint planning, i.e., new elements/articles will be added either to
8
the right or to the left of the already existing elements .
If the insertion mode (see option @InsertMode in [an0601]) has the (default) value 0, elements may not
beinsertedbetweentwoexistinggroupelementsresp. maynotberemovedfromthemiddleofthegroup.
In this case, interactors for adding resp. removing elements have to be equipped with according validity
conditions.
For that purpose, methods of class xOiJointPlGroup can be used which concern the so-called topological
order list of the group, i.e. the order of the group elements from the left-most to the right-most element
(see 8.1).
Some aspects of the behaviour may be controlled by specifying according options in control data table
jointplgroup [an0601].

### 8.1 Accessing topological order list

(cid:136) getElCount() → Int
Returns the number of elements in the topological order list.

MC_ELEM_COUNT;Instance;::ofml::xoi::xOiJointPlGroup;getElCount;

isEmpty() → Int
(cid:136)
Returns True (1), if the topological order list is empty.

MC_IS_EMPTY;Instance;::ofml::xoi::xOiJointPlGroup;isEmpty;

(cid:136) isNotEmpty() → Int
Returns True (1), if the topological order list is not empty.

MC_IS_NOT_EMPTY;Instance;::ofml::xoi::xOiJointPlGroup;isNotEmpty;

(cid:136) getElPos(pObj(MObject)) → Int | Void
Returns the position of given element in the topological order list.
Returnvalueisanintegerspecifyingthepositionstartingwith0(fortheleft-mostelement)or NULL
if the object ist not contained in the topological order list.

MC_GET_EL_POS;Instance;::ofml::xoi::xOiJointPlGroup;getElPos;$SELF

firstObj() → MObject | Void
(cid:136)
Returns the left-most group element (or NULL if group is empty).
(Useful in combination with object category MethodCall.)

MC_FIRST_OBJ;Instance;::ofml::xoi::xOiJointPlGroup;firstObj;

8 Infact,xOiJointPlGroupitselfisderivedfrombaseclassxOiLRPlGroupandmanyofthemethodsdescribedbeloware
inheritedfromthatclass.

11

<!-- Page 14 -->

lastObj() → MObject | Void
(cid:136)
Returns the right-most group element (or NULL if group is empty).
(Useful in combination with object category MethodCall.)

MC_LAST_OBJ;Instance;::ofml::xoi::xOiJointPlGroup;lastObj;

(cid:136) isFirstObj(pObj(MObject)) → Int
Returns True (1), if given element is the left-most group element.

MC_IS_FIRST_OBJ;Instance;::ofml::xoi::xOiJointPlGroup;isFirstObj;$SELF

(cid:136) isLastObj(pObj(MObject)) → Int
Returns True (1), if given element is the right-most group element.

MC_IS_LAST_OBJ;Instance;::ofml::xoi::xOiJointPlGroup;isLastObj;$SELF

neighbor(pObj(MObject), pDir(Symbol)) → MObject | Void
(cid:136)
Returns the neighbor of given group element in given direction ( @L – left, @R – right).
Returns NULL if group is empty or if there is no neighbor in given direction.

MC_NEIGHBOR_R;Instance;::ofml::xoi::xOiJointPlGroup;neighbor;$SELF,@R

### 8.2 Other methods

replaceElement(pEl(MObject), pPID(Symbol), pArticle(String), pOptions(Any)) → MObject | Void
(cid:136)
Replaces given group element by an instance of specified article 9 .
If parameter pEl is and the group contains only a single topological element, this element will
NULL
be replaced.
Parameter pPID specifies the OFML program ID.
Parameter pArticle specifies the base article number.
Parameter pOptions either is NULL or a Vector of additional options for article creation:
1. Varcode type (Symbol: @VarCode, @OFMLVarCode, @Final)
2. Varcode (String)
3. PropValues (Vector of [key, value] pairs)
4. PropStates (Vector of [key, state] pairs)
All elements in this Vector may be NULL. Elements 3 and 4 may be omitted.
The new element gets the same position and rotation as the replaced element.
Returns NULL if the new element could not be created, otherwise the reference to the new article
instance. (The new instance gets the same object name as the replaced instance.)

MC_CREATE_XY;Instance;::ofml::xoi::xOiJointPlGroup;replaceElement;\
$SELF,@foo_bar,"XY",NULL

Notes:
– If the new element has another width than the replaced one, neighbors of the element should
be moved according to the changed width and/or the element itself should be re-positioned.
This re-positioning procedure has to be enabled by specifying an according value for option
@InsertMode in the control data table [an0601].
9 ThismethodcanbeusedinsituationswherethereisnosuitablepropertyforanactionoftypePropEdit(orPropChange)
inordertochangethearticleoftheactiveobject.

12

<!-- Page 15 -->

– If the interactor with the MethodCall action is bound to a group element (not to the planning
group instance), after the action no further actions may follow, which again need a target
object or an object definition as a parameter, because after the action the original active
object no longer exists!

(cid:136) replaceElement2(pEl(MObject), pPID(Symbol), pArticle(String), pOptions(Any), pAttPt(Symbol),
...) → MObject | Void
Replaces given group element by an instance of specified article.
ThebehaviorisalmostidenticalwithreplaceElement()(seeabove)exceptforthepositioningofthe
new element:
It will be positioned using a given attach point of left or right neighbor. The key of the attach
pointisspecifiedinparameterpAttPt. Perdefault,theleftneighborisusedasthereferenceobject.
However, the reference object may be explicitely specified in additional optional parameter passing
the according direction (Symbol: @L or @R ).

MC_CREATE_XY_2;Instance;::ofml::xoi::xOiJointPlGroup;replaceElement2;\
$SELF,@foo_bar,"XY",NULL,@AP_LF

(cid:136) isBusyAttPt(pEl(MObject), pAttPt(Symbol)) → Int
Returns True (1) if given group element possesses an OFML attach point with specified key and if
there is a sibling or child element at this attach point.
MC_IS_ATTPT_R_BUSY;Instance;::ofml::xoi::xOiJointPlGroup;isBusyAttPt;$SELF,@ATTPT_R

# 9 Class xOiLayoutGroup

Instances of xOiLayoutGroup realize a planning group with a free but continuous (2-dimensional) layout
consisting of branches.
In contrast to xOiJointPlGroup (see previous section) this class supports arbitrary types of connec-
tions, e.g. ”T” and ”X” connections. For that purpose, the notion of the topological order list in
xOiJointPlGroup here is replaced by the notion of the layout.
There are two types of group elements:
(cid:136) Elements defining the layout of the group.
These elements have neighbor-relationships. They are attached to other layout elements by means
of OFML attach points. Two layout elements are called neighbors if they were connected (placed
10
next to each other) using a pair of attach points .
Methods regarding layout elements are described in 9.1.
Additional (non-layout) elements.
(cid:136)
Typically,theyarecreatedbasedonthecurrentlayout(definedbythelayoutelements),e.g. frames
for sofa arrangements, links between layout elements and alike.
Methods regarding additional elements are described in 9.5.

There are special layout elements called fork elements: They either are elements where the layout forks
(i.e. elements with more then two neighbors, such as ”T” or ”X” connections) or are elements otherwise
playingaspecialroleinthelayout. Forkelementsaredeterminedautomaticallywhenalayoutelementis
added or removed 11 . Alternatively, layout elements may be marked or unmarked as fork elements using
methods markAsForkElement() resp. unMarkAsForkElement() (see9.2).
Methods regarding fork elements are described in 9.2.
10
Note: two layout elements may be located next to each other but be no neighbors because they were not placed next
toeachotherusingapairofattachpoints.
11 Aslongasalayoutelementhasmorethan2neighborsitisdefinedtobeaforkelement.

13

<!-- Page 16 -->

By default, layout elements may be added only to layout elements with a free attach point. Accordingly
they may be removed only if they have only one attached neighbor. However, if the insertion mode is 2
(see option @InsertMode in the control data table [an0601]) insertion and removal is allowed anywhere
(implying a possible repositioning of neighbors).
Bydefault,itisnotallowed/supportedtochangethedimensionsofindividuallayoutelements. However,
iftheinsertionmodeisgreaterthan0,itisallowedtochangethedimensionofalayoutelement(implying
a possible repositioning of neighbors).
The layout consists of one or more branches: It starts with the so-called root branch. It grows when a
successor element is attached to the last branch element or a predecessor element is attached to the first
branch element.
When a new layout element is attached to an element of the root branch, which already has 2 neighbors
(forkelement),anewchild branchiscreated. Anewbranchalsoisstarted,ifthenewelementisattached
to a first or last element of the branch and if that element is marked as a fork element. Alternatively,
by calling method startNewBranch() (see section 9.4) right before adding a new layout element, a new
branch explicitly can be started, even if the predecessor does not have 2 neighbors (or more).
Elements of a branch where a child branch sets off are called nodes. A node element always also is a fork
element, but, vice versa, a fork element does not necessarily have to be a node element.
Therootbranchcangrowinbothdirections. Whetherotherbranchesalsomaygrowinbothdirectionsor
onlyinonedirectionisspecifiedbyoption@ChildBranchGrowthModeincontroldatatable layoutgroup
[an0601].
12
Branches are identified by numbers in the order of creation starting with 1 .
Methods regarding branches are described in 9.3.
Some aspects of the behaviour may be controlled by specifying according options in control data table
layoutgroup [an0601].

### 9.1 Layout elements

Note:
Theorderoftheelementsinthelistoflayoutelementsreflectstheorderofinsertionresp. removalofthe
elements!

(cid:136) isLayoutEmpty() → Int
Returns True (1) if the group does not contain any layout element.

MC_IS_LAYOUT_EMPTY;Instance;::ofml::xoi::xOiLayoutGroup;isLayoutEmpty;

isLayoutElement(pObj(MObject)) → Int
(cid:136)
Returns True (1) if given instance is a layout element.

MC_IS_LAYOUT_EL;Instance;::ofml::xoi::xOiLayoutGroup;isLayoutElement;$SELF

(cid:136) firstLayoutElement() → MObject | Void
Returns the first entry from the list of current layout elements (or NULL if the list currently is
empty).

MC_FIRST_LAYOUT_EL;Instance;::ofml::xoi::xOiLayoutGroup;firstLayoutElement;

12 Aschildbranchescandisappearduringtheprocessoflayoutcreation,theorderofthebranchnumberscanbediscon-
tinuous.

14

<!-- Page 17 -->

isFirstLayoutElement(pObj(MObject)) → Int
(cid:136)
Returns True (1) if given instance is the first element in the list of current layout elements.
MC_IS_FIRST_LAYOUT_EL;Instance;::ofml::xoi::xOiLayoutGroup;isFirstLayoutElement;$SELF

(cid:136) lastLayoutElement() → MObject | Void
Returns the last created element layout element (or NULL if the list of layout elements currently is
empty).
MC_LAST_LAYOUT_EL;Instance;::ofml::xoi::xOiLayoutGroup;lastLayoutElement;

(cid:136) isLastLayoutElement(pObj(MObject)) → Int
Returns True (1) if given instance is the last element in the list of current layout elements.
MC_IS_LAST_LAYOUT_EL;Instance;::ofml::xoi::xOiLayoutGroup;isLastLayoutElement;$SELF

(cid:136) getNeighbor(pObj(MObject), pAttPt(Symbol)) → MObject | Void
Returns the neighbor of given layout element at given attach point.
Returns NULL if given instance is not a layout element or if there is no neighbor at given attach
point.
See also method getAdjacentElement() below.
MC_NEIGHBOR_R;Instance;::ofml::xoi::xOiLayoutGroup;getNeighbor;$SELF,@ATTPT_R

(cid:136) getNeighborCount(pObj(MObject), ...) → Int
Returns the number of all current (immediate) neighbors of specified layout element.
If the given instance is not a layout element, the return value is 0.
Currently, no specific optional parameters are defined 13 .

MC_NEIGHBOR_COUNT;Instance;::ofml::xoi::xOiLayoutGroup;getNeighborCount;$SELF

hasNeighbors(pObj(MObject)) → Int
(cid:136)
Returns True (1) if given instance is a layout element and if it currently has neighbors.

MC_HAS_NEIGHBORS;Instance;::ofml::xoi::xOiLayoutGroup;hasNeighbors;$SELF

getAdjacentElement(pObj(MObject), pAttPt(Symbol)) → MObject | Void
(cid:136)
Returns the group element which occupies the specified attach point of given layout element.
In contrast to getNeighbor() (see above) this method also considers elements not being a neighbor
of given layout element, i.e. which are not explicitely connected to it but are just located beside it
occupying the specified attach point geometrically.
Returns ifgiveninstanceisnotalayoutelementorifthereisnoattachpointcurrentlydefined
NULL
with given key or if there is no group element occupying the specified attach point.
Note:
The returned group element does not necessarily have to be a layout element.

MC_ADJACENT_R;Instance;::ofml::xoi::xOiLayoutGroup;getAdjacentElement;$SELF,@ATTPT_R

canBeRemovedFromLayout(pObj(MObject)) → Int
(cid:136)
Returns True (1) if given instance is a layout element and if it can be deleted (removed from the
layout structure).
A layout element can be removed (by the definition of this implementation) if the insert mode is 2
(see option @InsertMode) or if it has only one neighbor.
13 Reservedforpossibleextensionsinthefuture.

15

<!-- Page 18 -->

MC_CAN_REMOVE;Instance;::ofml::xoi::xOiLayoutGroup;canBeRemovedFromLayout;$SELF

hasFreeAttPts2(pObj(MObject), pCheckAll(Int)) → Int
(cid:136)
Returns True (1) if given instance is a layout element and if it has at least one free OFML attach
point, otherwise False (0).
An attach point is free, if it was not used to connect with a neighbor layout element and if there is
no (other) sibling or child element occupying this attach point geometrically.
Parameter pCheckAll specifies whether all attach points of given instance have to be checked (1) or
only the additional attach points (0, i.e. ignoring the standard attach points).

MC_HAS_FREE_ATTPTS;Instance;::ofml::xoi::xOiLayoutGroup;hasFreeAttPts2;$SELF,0

isFreeAttPt(pObj(MObject), pAttPt(Symbol)) → Int
(cid:136)
Returns True (1) if given instance is a layout element and if specified OFML attach point (key)
currently is defined for the given instance and if it is free.
Otherwise returns False (0).

MC_IS_ATTPT_R_FREE;Instance;::ofml::xoi::xOiLayoutGroup;isFreeAttPt;$SELF,@ATTPT_R

### 9.2 Fork elements

hasForkElements() → Int
(cid:136)
Returns True (1) if the group contains fork elements.

MC_HAS_FORKS;Instance;::ofml::xoi::xOiLayoutGroup;hasForkElements;

(cid:136) isForkElement(pObj(MObject)) → Int
Returns True (1) if given instance is a fork element.

MC_IS_FORK;Instance;::ofml::xoi::xOiLayoutGroup;isForkElement;$SELF

markAsForkElement(pObj(MObject)) → Int
(cid:136)
Marks given layout element as a fork element.
Has no effect, if given instance is not a layout element of the group or if it already is deter-
mined/marked as a fork element. In this case, return value is 0, otherwise 1.

MC_MARK_AS_FORK;Instance;::ofml::xoi::xOiLayoutGroup;markAsForkElement;$SELF

unMarkAsForkElement(pObj(MObject)) → Int
(cid:136)
Unmarks given layout element as a fork element.
Has no effect, if given instance is not a fork element or if it is a node element. In this case, return
value is 0, otherwise 1.

MC_UNMARK_AS_FORK;Instance;::ofml::xoi::xOiLayoutGroup;unMarkAsForkElement;$SELF

16

<!-- Page 19 -->

### 9.3 Branches

(cid:136) getLatestBranch() → Int
Returns the number of the branch created most recently.

MC_GET_LAST_BRANCH;Instance;::ofml::xoi::xOiLayoutGroup;getLatestBranch;

(cid:136) isLatestBranch(pBranch(Int)) → Int
ReturnsTrue(1)ifthereisabranchwithgivennumberandifthisbranchwascreatedmostrecently.
MC_IS_ROOT_BRANCH_LAST;Instance;::ofml::xoi::xOiLayoutGroup;isLatestBranch;1

(cid:136) getBranch(pObj(MObject)) → Int
Returns the number of the branch the given layout element belongs to.
If given object is not a layout element return value is 0.

MC_GET_BRANCH;Instance;::ofml::xoi::xOiLayoutGroup;getBranch;$SELF

(cid:136) isBranchElement(pBranch(Int), pObj(MObject)) → Int
Returns True (1) if given layout element belongs to the specified branch.
MC_IS_ROOT_BRANCH_EL;Instance;::ofml::xoi::xOiLayoutGroup;isBranchElement;1,$SELF

(cid:136) isNodeElement(pObj(MObject)) → Int
Returns True (1) if given object is a layout element and if it is a node element of the branch it
belongs to.
MC_IS_ROOT_BRANCH_NODE;Instance;::ofml::xoi::xOiLayoutGroup;isNodeElement;1,$SELF

(cid:136) getFirstBranchElem(pBranch(Int)) → MObject | Void
Returns the first element from the topological order list of given branch.
Returns NULL if there is no branch with given number.
MC_FIRST_EL_IN_ROOT_BRANCH;Instance;::ofml::xoi::xOiLayoutGroup;getFirstBranchElem;1

(cid:136) isFirstBranchElem(pBranch(Int), pObj(MObject)) → Int
ReturnsTrue(1)ifgivenlayoutelementbelongstothespecifiedbranchandifitisthefirstelement
in the topological order list of that branch.
MC_IS_FIRST_EL_IN_ROOT_BRANCH;Instance;::ofml::xoi::xOiLayoutGroup;isFirstBranchElem;\
1,$SELF

getLastBranchElem(pBranch(Int)) → MObject | Void
(cid:136)
Returns the last element from the topological order list of given branch.
Returns NULL if there is no branch with given number.

MC_LAST_EL_IN_ROOT_BRANCH;Instance;::ofml::xoi::xOiLayoutGroup;getLastBranchElem;1

isLastBranchElem(pBranch(Int), pObj(MObject)) → Int
(cid:136)
ReturnsTrue(1)ifgivenlayoutelementbelongstothespecifiedbranchandifitisthelastelement
in the topological order list of that branch.

MC_IS_LAST_EL_IN_ROOT_BRANCH;Instance;::ofml::xoi::xOiLayoutGroup;isLastBranchElem;\
1,$SELF

17

<!-- Page 20 -->

isFirstOrLastBranchElem(pBranch(Int), pObj(MObject)) → Int
(cid:136)
Returns True (1) if given layout element belongs to the specified branch and if it is the first or the
last element in the topological order list of that branch.

MC_IS_END_EL_IN_ROOT_BRANCH;Instance;::ofml::xoi::xOiLayoutGroup;isFirstOrLastBranchElem;\
1,$SELF

(cid:136) getBranchPredecessor(pObj(MObject)) → MObject | Void
Returns the topological predecessor branch element of given layout element.
Returns NULL if given object is not a layout element or if it has no predecessor branch element.

MC_PREDECESSOR;Instance;::ofml::xoi::xOiLayoutGroup;getBranchPredecessor;$SELF

getBranchSuccessor(pObj(MObject)) → MObject | Void
(cid:136)
Returns the topological successor branch element of given layout element.
Returns NULL if given object is not a layout element or if it has no successor branch element.

MC_SUCCESSOR;Instance;::ofml::xoi::xOiLayoutGroup;getBranchSuccessor;$SELF

(cid:136) getForkPredecessor(pObj(MObject)) → MObject | Void
Returns the topological predecessor fork element in the branch of given layout element.
Returns NULL if given object is not a layout element or if it has no predecessor fork element in the
branch.

MC_PREDECESSOR_FORK;Instance;::ofml::xoi::xOiLayoutGroup;getForkPredecessor;$SELF

getForkSuccessor(pObj(MObject)) → MObject | Void
(cid:136)
Returns the topological successor fork element in the branch of given layout element.
Returns NULL if given object is not a layout element or if it has no successor fork element in the
branch.

MC_SUCCESSOR_FORK;Instance;::ofml::xoi::xOiLayoutGroup;getForkSuccessor;$SELF

getFirstForkElem(pBranch(Int)) → MObject | Void
(cid:136)
Returns the first fork element from the topolopical element list of given branch.
ReturnsNULLifthereisnobranchwithgivennumberorifthebranchdoesnotcontainforkelements.

MC_FIRST_FORK_IN_ROOT_BRANCH;Instance;::ofml::xoi::xOiLayoutGroup;getFirstForkElem;1

(cid:136) getLastForkElem(pBranch(Int)) → MObject | Void
Returns the last fork element from the topolopical element list of given branch.
Returns NULL ifthereisnobranchwithgivennumberorifthebranchdoesnotcontainforkelements.

MC_LAST_FORK_IN_ROOT_BRANCH;Instance;::ofml::xoi::xOiLayoutGroup;getLastForkElem;1

getFirstCatElem(pBranch(Int), pCat(Symbol)) → MObject | Void
(cid:136)
Returns the first element from the topolopical element list of given branch belonging to specified
element category.
Returns NULL if there is no branch with given number or if the branch does not contain elements
belonging to specified category.

MC_FIRST_SEAT_IN_ROOT_BRANCH;Instance;::ofml::xoi::xOiLayoutGroup;getFirstCatElem;1,@Seat

18

<!-- Page 21 -->

getLastCatElem(pBranch(Int), pCat(Symbol)) → MObject | Void
(cid:136)
Returns the last element from the topolopical element list of given branch belonging to specified
element category.
Returns NULL if there is no branch with given number or if the branch does not contain elements
belonging to specified category.

MC_LAST_SEAT_IN_ROOT_BRANCH;Instance;::ofml::xoi::xOiLayoutGroup;getLastCatElem;1,@Seat

### 9.4 Other methods

startNewBranch() → Void
(cid:136)
Forces the creation of a new branch when the next layout element is added.
Then, if the predecessor of the new layout element only has one neighbor it will not be marked as
a fork element.

MC_START_NEW_BRANCH;Instance;::ofml::xoi::xOiLayoutGroup;startNewBranch;

replaceElement(pEl(MObject), pPID(Symbol), pArticle(String), pOptions(Any),
(cid:136)
pPredecessorAttPt(Symbol), pElAttPt(Symbol), pSuccessorAttPt(Symbol)) → MObject | Void
14
Replaces given group element by an instance of specified article .
If parameter pEl is NULL and the group contains only a single topological element, this element will
be replaced.
If the given element is a a fork element or if it is connected to a parent branch, the method has no
effect!
Parameter pPID specifies the OFML program ID.
Parameter pArticle specifies the base article number.
Parameter pOptions either is or a Vector of additional options for article creation:
NULL
1. Varcode type (Symbol: @VarCode, @OFMLVarCode, @Final)
2. Varcode (String)
3. PropValues (Vector of [key, value] pairs)
4. PropStates (Vector of [key, state] pairs)
All elements in this Vector may be NULL. Elements 3 and 4 may be omitted.
Parameter pPredecessorAttPt specifies the attach point of the predecessor element to be used to
position the new element.
Parameter pElAttPt specifies the attach point of the new element to be used to connect with the
successor element.
ParameterpSuccessorAttPtspecifiestheattachpointofthesuccessorelementtobeusedtoconnect
with the new element.
Returns NULL if the replacement was not successful, otherwise the reference to the new article
instance.

MC_CREATE_XY;Instance;::ofml::xoi::xOiLayoutGroup;replaceElement;\
$SELF,@foo_bar,"XY",NULL,@AP_R,@AP_R,@AP_L

14 ThismethodcanbeusedinsituationswherethereisnosuitablepropertyforanactionoftypePropEdit(orPropChange)
inordertochangethearticleoftheactiveobject.

19

<!-- Page 22 -->

Notes:
– Itistheresponsibilityoftheclienttospecifyareplacementarticlethathasthesamedimensions
15
as the replaced element!
– Theoperationcannotbeperformedifeitherthepredecessororthesuccessor(ifany)currently
is/are flipped (see method flipElement() below)!
– If the interactor with the MethodCall action is bound to a group element (not to the planning
group instance), after the action no further actions may follow, which again need a target
object or an object definition as a parameter, because after the action the original active
object no longer exists!

(cid:136) replaceElement2(pEl(MObject), pPID(Symbol), pArticle(String), pOptions(Any),
pRefObjAtAttPt(Symbol)) → MObject | Void
16
Replaces given group element by an instance of specified article .
In contrast to replaceElement() this method allows to replace an element marked as a fork element
resp. anelementthatisconnectedtoaparentbranch. Thismethodonlyrequiresthatthespecified
layout element has no more than two neighbors. However, it is assumed that the replaced element
will/can be re-connected with its neighbors using the same attach points as before.
Parameter pPID specifies the OFML program ID.
Parameter pArticle specifies the base article number.
Parameter pOptions either is NULL or a Vector of additional options for article creation:
1. Varcode type (Symbol: @VarCode, @OFMLVarCode, @Final)
2. Varcode (String)
3. PropValues (Vector of [key, value] pairs)
4. PropStates (Vector of [key, state] pairs)
All elements in this Vector may be NULL. Elements 3 and 4 may be omitted.
Parameter pRefObjAtAttPt specifiesthe attachpoint ofpEl usedto connectwith the neighborthat
should be used as the reference object for positioning of the new element.
Returns if the replacement was not successful, otherwise the reference to the new article
NULL
instance. (In contrast to replaceElement() here the new element gets the same hierarchical name
as the replaced one.)

MC_CREATE_XY;Instance;::ofml::xoi::xOiLayoutGroup;replaceElement2;\
$SELF,@foo_bar,"XY",NULL,@AP_L
Notes:
– Itistheresponsibilityoftheclienttospecifyareplacementarticlethathasthesamedimensions
17
as the replaced element!
– Theoperationcannotbeperformedifaneighborcurrentlyisflipped(seemethodflipElement()
below)!
– If the interactor with the MethodCall action is bound to a group element (not to the planning
group instance), after the action no further actions may follow, which again need a target
object or an object definition as a parameter, because after the action the original active
18
object no longer exists !

15 I.e., in contrast to xOiJointPlGroup no elements will be re-positioned if the new element has another width than the
replacedone,evenifdimensionchangeoflayoutelementsisenabledaccordingtooption@InsertModeinthecontroldata
table[an0601].
16
ThismethodcanbeusedinsituationswherethereisnosuitablepropertyforanactionoftypePropEdit(orPropChange)
inordertochangethearticleoftheactiveobject.
17 I.e., in contrast to xOiJointPlGroup no elements will be re-positioned if the new element has another width than the
replacedone,evenifdimensionchangeoflayoutelementsisenabledaccordingtooption@InsertModeinthecontroldata
table[an0601].
18 evenifthenewelementgetsthesamehierarchicalname

20

<!-- Page 23 -->

flipElement(pEl(MObject), pPredecessorCon(Any), pSuccessorCon(Any)) → Int
(cid:136)
Switches the front/back orientation of given layout element.
The operation is not allowed/possible if given element has more than two neighbors!
ParameterspPredecessorConandpSuccessorConcanbeusedtospecifytheattachpointstobeused
to connect the flipped element with its predecessor resp. successor element if the element is flipped
from its original orientation: The parameters either are NULL or a Vector
1. attach point of predecessor (Symbol)
2. attach point of element (Symbol)
resp.
1. attach point of element (Symbol)
2. attach point of successor (Symbol)
where the Vector elements may be .
NULL
If a connection information is missing ( NULL ), it is be determined as follows:
– The attach points of predecessor and successor elements used to connect with the flipped
element stay the same.
– The attach points of the flipped element used to connect to its predecessor resp. successor
elements will be switched.
Note:
If the flipped element has no predecessor, pSuccessorCon must not be NULL and has to specify
an attach point in its first element!
Vice versa, if the flipped element has no successor, pPredecessorCon must not be NULL and
has to specify an attach point in its second element!
If the element is flipped back to its original orientation, parameters pPredecessorCon and
pSuccessorCon will be ignored and the original attach point connections will be restored.
If given layout element is the first branch element and the branch of the element is not the root
branch and if the element is a neighbor of the element of the parent branch where the element
branch sets off, that element of the parent branch is used as the predecessor.
If given layout element is the last branch element and if it is a node where a child branch sets off,
the neighbor element of that branch is used as the successor.
Returns 1 (true) if the operation was successful, otherwise 0 (false).
Important note:
If a new neighbor is up to be added to a flipped element as successor or predeccessor (i.e., if the
flippedelementcurrentlyhasonlyapredeccessorresp. onlyasuccessor),inordertogetthecorrect
originalorientationforthenewelement,theflippedelementtemporarilyhastobeswitchedbackto
itsoriginalorientation,andtobeflippedagainafterthenewneighborelementwasadded. (Whether
an element is flipped can be determined by method isFlippedElement(), see below.)
MC_FLIP_ME;Instance;::ofml::xoi::xOiLayoutGroup;flipElement;$SELF,NULL,NULL

isFlippedElement(pEl(MObject)) → Int
(cid:136)
Returns 1 (true) if given layout element currently is flipped with respect to its original front/back
orientation.
This refers to the flip operation performed by method flipElement() (see above).

MC_AM_I_FLIPPED;Instance;::ofml::xoi::xOiLayoutGroup;isFlippedElement;$SELF

(cid:136) swapNeighbors(pEl1(MObject), pEl2(MObject), ...) → Int
Swaps the given two neighbor elements (belonging to the same branch).
The elements change their geometric position as well as their position in the topological element
list of the branch (incl. adaptation of connection information of the affected elements).

21

<!-- Page 24 -->

The method has no effect in the following situations:
– One of the elements is not a layout element.
– One of the elements has more than two neighbors.
– The elements do not belong to the same branch.
– The elements aren’t neighbors.
– One of the elements or the predecessor of the first element (if any) or the successor of the
second element (if any) currently is flipped.
(Consider to temporarily switch affected element back to its original orientation, and to flip it
again after the swap operation.)
Returns 1 (true) if the operation was successful, otherwise 0 (false).
Note:
Current implementation expects, that the given elements as well as predecessor and successor (if
any) use the same pairs of attach points to connect to each other. If this is not the case, correct
functioning cannot be guaranteed. (Additional parameters may be added in the future, to handle
other cases, too.)

MC_SWAP_ME_AND_NEIGHBOR_R;Instance;::ofml::xoi::xOiLayoutGroup;swapNeighbors;\
$SELF,methodCall("AC_call_NEIGHBOR_R")

(cid:136) canSwapNeighbors(pEl1(MObject), pEl2(MObject), ...) → Int
Returns 1 (true) if given two neighbor elements can be swapped.
Checks the conditions mentioned above for method swapNeighbors().

MC_CAN_SWAP_ME_AND_R;Instance;::ofml::xoi::xOiLayoutGroup;canSwapNeighbors;\
$SELF,methodCall("AC_call_NEIGHBOR_R")

(cid:136) setAdjustSide4Insertion(pAdjustSide(Symbol |MObject), ...) → Void
Specifies the neighbors of the reference object which have to be moved due to upcoming insertion
of a new element between the reference object and its current neighbor.
The parameter either specifies the attach point of the reference object to which the relevant imme-
diate neighbor is attached, or specifies the immediate neighbor itself.
If this method is not called before the upcoming insertion, the current active attach point of the
reference object is used (if any) to determine the neighbors to be adjusted (if there is a neighbor
attached to that attach point).
If an additional optional parameter is given it specifies the attach point (Symbol) of the upcoming
new neighbor to be used for re-positioning the neighbors at pAdjustSide. If the parameter is not
givenorisnotaSymbol,thesameattachpointisusedthatdeterminestheneighborstobeadjusted
(see above), if the upcoming new neighbor has such an attach point.

MC_SET_ADJUST_SIDE_4_INSERT;Instance;::ofml::xoi::xOiLayoutGroup;\
setAdjustSide4Insertion;@AP_R

(cid:136) setAdjustSide4Removal2(pAdjustSide(Symbol |MObject), ...) → Void
Specifies the neighbors which have to be moved due to upcoming removal of a layout element
between two neigbors.
The parameter either specifies the attach point of the element up to be removed to which the
relevant immediate neighbor is attached, or specifies the immediate neighbor itself.
Note: Removal of an inner element is allowed/possible only if it has exactly two neighbors!
TheneighborattheothersideaspAdjustSidewillbeusedasthereferenceobjectforre-positioning
the neighbors at pAdjustSide.
If an additional optional parameter is given it specifies the attach point (Symbol) of the reference
object to be used for re-positioning the neighbors at pAdjustSide. If the parameter is not given or

22

<!-- Page 25 -->

is not a Symbol, the attach point of reference object is used that was used to connect it with the
element up to be removed.
Note:
If the neighbor elements or the element up to be removed currently are flipped (see method
flipElement() above) the affected elements temporarily should be switched back to their origi-
nal orientation, and be flipped again after the removal 19 . (Whether an element is flipped can be
determined by method isFlippedElement(), see above.)

MC_SET_ADJUST_SIDE_4_REMOVE;Instance;::ofml::xoi::xOiLayoutGroup;\
setAdjustSide4Removal2;@AP_R

### 9.5 Additional elements

(cid:136) hasAdditionalElements() → Int
Returns True (1) if the group contains additional elements.

MC_HAS_OTHER_ELEMS;Instance;::ofml::xoi::xOiLayoutGroup;hasAdditionalElements;

(cid:136) isAdditionalElement(pObj(MObject)) → Int
Returns True (1) if given instance is contained in the list of additional elements.

MC_IS_ADDITIONAL_EL;Instance;::ofml::xoi::xOiLayoutGroup;isAdditionalElement;$SELF

# 10 Class xOiTabularPlGroup

Base class for planning groups with a tabular layout.
Instances may have an horizontal orientation (XZ plane) or a vertical orientation (XY plane).
ElementsalignedparalleltoXaxisformrows,elementsalignedparalleltoYorZaxesarecalledcolumns
(or lines with an horizontal layout). The crossing of a row and a column forms a field.
Fields have an address consisting of the index of the corresponding column and the index of the corre-
spondingrow,wheretheindexnumberingstartswithzero. Twofields,wheretheabsoluteindexdifference
in both directions is 0 or 1, are called neighbor fields. Two neighbor fields, having the same index in one
direction, are called straight neighbor fields.
Each column has a defined width and each row has a defined depth with the horizontal orientation resp.
a defined height with the vertical orientation, but the group may be configured so that all columns have
the same (uniform) width and all rows have the same depth resp. height.
Project specific subclasses must not be derived from xOiTabularPlGroup but have to be derived from
dedicated subclasses according to required orientation and row count direction:
xOiTabularPlGroupVert
Realizes a tabular planning group with a vertical orientation.
xOiTabularPlGroupHForth
Realizes a tabular planning group with a horizontal orientation where rows are added in positive Z
direction, i.e., forwards (back to front).
xOiTabularPlGroupHBack
Realizes a tabular planning group with a horizontal orientation where rows are added in negative Z
direction, i.e., backwards (front to back).

19 incaseoftheneighbors

23

<!-- Page 26 -->

There are two supported types of group elements:
Elements defining the layout of the group, also called field elements.
(cid:136)
(cid:136) Additional, other (non-layout) elements.
Typically,theyarecreatedbasedonthecurrentlayout(definedbythelayoutelements),e.g. frames
for sofa arrangements, links between field elements and alike.
Creating such elements requires special OFML programming, i.e., this cannot be done in OAP data
alone. Therefore, methods related to non-layout elements are not covered in this document.

Afieldelementmayoccupymorethanonefield,inwhichcaseitiscalledamulti-field element. Thefield,
that defines the position of a multi-field element is called its root field.
Note: Some operations (methods) manipulating the tabular structure are not allowed/possible if multi-
field elements would be affected. This will be stated below for each affected method. Methods
hasMultiFieldElements() and isStraightLine() (see subsection 10.2 below) can be used for according pre-
checks.
Two single-field elements are called neighbors if they are located in neighbor fields (see definition above).
The neighbors of a multi-field element are determined as follows:
For all fields occupied by the element, the first field in the requested search direction is determined,
which is not occupied by the multi-field element. If this field is occupied by another field element (or
placeholder), that element (or placeholder) is a neighbor in the requested search direction.
The neighbor relative to the root field of a multi-field element is called its main neighbor.
Thewidthandthedepthresp. heightofafieldelementcanbesmallerthanthewidthresp. depth/height
defined for the according column resp. row of the field. Accordingly, various alignment strategies are
supported.
A field may be empty. Then, it can be filled with a placeholder (not being a field element).
Some aspects of the behaviour, e.g. related to the creation of the initial (start) layout or to place-
holdercreation,maybecontrolledbyspecifyingaccordingoptionsincontroldatatabletabularplgroup
[an0601].
Thefollowingoperations(methods)involvecloningofexistingfieldelementsusingglobalOFMLfunction
oiClone() [ofml] (mainly due to performance considerations):
1. Creation of the initial field elements according to option @StartLayout with mode @Uniform (see
[an0601])
2. Adding new columns and rows using methods addColumn2() resp. addRow3() with article creation
modes @Default and @Unique (see subsection 10.3 below)
3. Replacingafield(element)byacloneoftheelementinspecifiedsourcefield,usingmethodreplace-
Field() (see subsection 10.3 below)
In the first and second scenarios, the first element from the set of the elements to be created, is created
according to the standard procedure for the creation and initialization of an article instance, as specified
in [article]. All other elements are created as clones of the first element.
Note:
Cloning triggers the DUMP rules for the source element and the EVAL rules for the clone (see [ofml]).
This has to be considered, if the affected class has member variables containing object refernces! Some
hintsregardingthisissuecanbefindin[an oap]inthesectioncoveringthepersistencyofplanninggroups.
When a field element is deleted, by default, empty head and back columns resp. rows after the removal
of the element will be removed from the internal data structures. This can be avoided by using method
deleteFieldElement2() with value 1 (true) for parameter pKeepFields (see subsection 10.3 below).

24

<!-- Page 27 -->

### 10.1 General settings and information

(cid:136) setMaxColumns(pCount(Int)) → Void
Assigns new maximum allowed count of columns. (See also option @MaxColumns in [an0601].)
Value 0 denotes no restriction.
The assignment of the given count (greater than 0) is rejected if it is lower than the current count
of columns.

MC_SET_MAX_COLUMNS_6;Instance;::ofml::xoi::xOiTabularPlGroup;setMaxColumns;6

(cid:136) getMaxColumns() → Int
Returns currently defined maximum allowed count of columns.
(Value 0 denotes no restriction.)

MC_GET_MAX_COLUMNS;Instance;::ofml::xoi::xOiTabularPlGroup;getMaxColumns;

setMaxRows(pCount(Int)) → Void
(cid:136)
Assigns new maximum allowed count of rows. (See also option @MaxRows in [an0601].)
Value 0 denotes no restriction.
The assignment of the given count (greater than 0) is rejected if it is lower than the current count
of rows.

MC_SET_MAX_COLUMNS_5;Instance;::ofml::xoi::xOiTabularPlGroup;setMaxRows;5

(cid:136) getMaxRows() → Int
Returns currently defined maximum allowed count of rows.
(Value 0 denotes no restriction.)

MC_GET_MAX_COLUMNS;Instance;::ofml::xoi::xOiTabularPlGroup;getMaxRows;

(cid:136) setUniformFieldSize(pColumnWidth(Float |Void), pRowSize(Float |Void)) → Void
Assigns new dimension(s) for uniformly sized fields.
Parameter pColumnWidth either is NULL or specifies the new column width. The parameter will
be ignored, if columns do not have a uniform width, according to option @UniformColumnWidth.
(See also option @ColumnWidth.)
Parameter pRowSize either is NULL or specifies the new row height resp. depth. The
parameter will be ignored, if rows do not have a uniform size, according to options
@UniformRowSize/Height/Depth. (See also options @RowSize/Height/Depth.)
Note: if a size change becomes effective, field elements will be re-positioned accordingly.

MC_SET_UNIFORM_FIELD_SIZE;Instance;::ofml::xoi::xOiTabularPlGroup;\
setUniformFieldSize;NULL,2.4

(cid:136) getUniformColumnWidth() → Float |Void
Returns the current width for uniformly sized fields.
Return value is NULL if uniform column width is not enabled according to option
@UniformColumnWidth.

MC_GET_UNIFORM_COLUMN_WIDTH;Instance;::ofml::xoi::xOiTabularPlGroup;\
getUniformColumnWidth;

25

<!-- Page 28 -->

getUniformRowSize() → Float |Void
(cid:136)
Returns the current height resp. depth for uniformly sized fields.
Return value is NULL if uniform row size is not enabled according to options
@UniformRowSize/Height/Depth.

MC_GET_UNIFORM_ROW_SIZE;Instance;::ofml::xoi::xOiTabularPlGroup;getUniformRowSize;

(cid:136) getColumnWidth(pIdx(Int)) → Float |Void
Returns the width of the column with specified index.
Return value is , if there is no column with specified index.
NULL
MC_GET_COLUMN_2_WIDTH;Instance;::ofml::xoi::xOiTabularPlGroup;getColumnWidth;2

(cid:136) getRowSize(pIdx(Int)) → Float |Void
Returns the height resp. depth of the row with specified index.
Return value is NULL , if there is no row with specified index.
MC_GET_ROW_3_HEIGHT;Instance;::ofml::xoi::xOiTabularPlGroup;getRowSize;3

setPlaceholderCreationOn(pValue(Int)) → Void
(cid:136)
Specifieswhetheremptyfieldsshouldbefilledbytransparentandselectableplaceholderobjects(1)
or not (0).
Can be used to dynamically change the value for option @EmptyFieldsPlaceholder. (See also infor-
mation on accompanying options.)

MC_SET_PLACEHOLDER_CREATION_ON;Instance;::ofml::xoi::xOiTabularPlGroup;\
setPlaceholderCreationOn;1

getPlaceholderCreationOn()) → Int
(cid:136)
Returns the current value of option @EmptyFieldsPlaceholder.

MC_IS_PLACEHOLDER_CREATION_ON;Instance;::ofml::xoi::xOiTabularPlGroup;\
getPlaceholderCreationOn;

### 10.2 Information on fields and layout structure

(cid:136) getColumnCount()) → Int
Returns current count of columns.
MC_COLUMN_COUNT;Instance;::ofml::xoi::xOiTabularPlGroup;getColumnCount;

getRowCount()) → Int
(cid:136)
Returns current count of rows.

MC_ROW_COUNT;Instance;::ofml::xoi::xOiTabularPlGroup;getRowCount;

(cid:136) isLayoutEmpty()) → Int
Returns 1 (true) if the group does not contain any field element.

MC_IS_GROUP_EMPTY;Instance;::ofml::xoi::xOiTabularPlGroup;isLayoutEmpty;

(cid:136) firstFieldElement()) → MObject |Void
Returns the first entry from the list of current field elements (or an instance of Void if the list
currently is empty).

26

<!-- Page 29 -->

MC_FIRST_FIELD_EL;Instance;::ofml::xoi::xOiTabularPlGroup;firstFieldElement;

lastFieldElement()) → MObject |Void
(cid:136)
Returns the last entry from the list of current field elements (or an instance of Void if the list
currently is empty).

MC_LAST_FIELD_EL;Instance;::ofml::xoi::xOiTabularPlGroup;lastFieldElement;

(cid:136) isFieldElement(pObj(MObject)) → Int
Returns 1 (true) if given instance is a field element.
MC_AM_A_FIELD_EL;Instance;::ofml::xoi::xOiTabularPlGroup;isFieldElement;$SELF

(cid:136) isMultiFieldElement(pObj(MObject)) → Int
Returns 1 (true) if given instance is a field element and occupies multiple fields.

MC_AM_A_MULTI_FIELD_EL;Instance;::ofml::xoi::xOiTabularPlGroup;isMultiFieldElement;\
$SELF

(cid:136) getFieldOf(pObj(MObject)) → Int[2] |Void
Returns the field address of given field element or placeholder.
Returns NULL if given object is not a field element and no placeholder, otherwise the root field, i.e.
the field that was used for the position of the element resp. placeholder.

MC_MY_FIELD_ADDRESS;Instance;::ofml::xoi::xOiTabularPlGroup;getFieldOf;$SELF

getColumnOf(pObj(MObject)) → Int |Void
(cid:136)
Returns the index of the column of given field element or placeholder.
Returns NULL if given object is not a field element and no placeholder, otherwise the column of the
root field, i.e. the field that was used for the position of the element resp. placeholder.

MC_MY_COLUMN_IDX;Instance;::ofml::xoi::xOiTabularPlGroup;getColumnOf;$SELF

getRowOf(pObj(MObject)) → Int |Void
(cid:136)
Returns the index of the column of given field element or placeholder.
Returns if given object is not a field element and no placeholder, otherwise the column of the
NULL
root field, i.e. the field that was used for the position of the element resp. placeholder.

MC_MY_ROW_IDX;Instance;::ofml::xoi::xOiTabularPlGroup;getRowOf;$SELF

(cid:136) hasMultiFieldElements(pObjs(MObject |Void)) → Int
Returns 1 (true) if there is at least one field element occupying multiple fields.
IfparameterpObjsisnot NULL butspecifiesaListorVectoroffieldelements(orplaceholders),only
those elements will be checked.

MC_HAS_MULTIFIELD_ELEMENTS;Instance;::ofml::xoi::xOiTabularPlGroup;\
hasMultiFieldElements;NULL

(cid:136) isStraightLine(pLineType(Symbol), pLineIdx(Int)) → Int
Returns 1 (true) if none of the elements in given line occupies fields of another line (i.e., if they
form a straight line).
Possible types in parameter pLineType are and @Row.
@Column

27

<!-- Page 30 -->

MC_IS_COLUMN_1_STRAIGHT;Instance;::ofml::xoi::xOiTabularPlGroup;\
isStraightLine;@Column,1

(cid:136) getNeighbor(pObj(MObject | Int[2]), pDir(Symbol), ...) → MObject |Void
Returns the neighbor element of given field element in given direction.
In parameter pObj, instead of a field element, the address of a field may be passed.
The possible direction values (parameter pDir) are:
@N (or @North , @Up and @Back )
@E (or @East , @R and @Right )
@S (or @South , @Down and @Forth )
@W (or @West , @L and @Left )
and the diagonal directions: @NE , @SE , @SW , @NW .
Additional optional parameter of type Int specifies whether placeholders in empty fields have to be
considered (1) or not (0, default).
Returns NULL if given direction is not valid or if given instance is not a field element (resp. a
placeholder) or if there is no neighbor element (resp. placeholder) in given given direction.
If the given element occupies more than one field, the neighbor relativ to the root field will be
returned.

MC_NEIGHBOR_R;Instance;::ofml::xoi::xOiTabularPlGroup;getNeighbor;$SELF,@R

### 10.3 Manipulating the layout structure

addNeighbor(pRefField(MObject | Int[2]), pDir(Symbol), pArticle(Any), pAlignment(Any)) →
(cid:136)
MObject |Void
Creates a new field next to specified reference field in given direction (if it does not exist yet) and
fills it with specified article.
The reference field either is specified by its address or by the according field element. If an element
is given it must not occupy more than one field.
For possible direction values (parameter pDir) see method getNeighbor() above.
ParameterpArticleeitherisaspecificationaccordingtooption@DefaultArticleorisNULL,inwhich
case an article is created as specified in option @DefaultArticle.
Parameter pAlignment is not supported yet. (New element is aligned according to corresponding
options.)
The method has no effect if the maximum allowed count of columns or rows (see options
@MaxColumns and @MaxRows) has already been reached.
If the direction denotes a new element before first column resp. row, the indices of all existing
columns resp. rows will be incremented and new column resp. row (for the new element) gets
index 0. The position of the new element gets a negative coordinate in the according dimension.
This scenario is not allowed/possible if the group contains at least one element occupying more
than one field.
Also note: do not use this scenario if the fields do not have the same size.
Returns NULL if the operation is not allowed (see above) or in case of invalid parameters or if the
neighborfieldviolatesthemaximumallowedcountofcolumnsorrowsorifthearticlecouldnotbe
created. Otherwise returns the reference to the new element.

MC_ADD_NEIGHBOR_R;Instance;::ofml::xoi::xOiTabularPlGroup;addNeighbor;\
$SELF,@R,NULL,NULL

28

<!-- Page 31 -->

addColumn2(pArtSpecType(Symbol), pArticle(Any), pDir(Symbol), pAlignment(Any),
(cid:136)
pWidth(Float), ...) → Void
Creates a new column and fills it with specified article(s).
Parameter pArtSpecType specifies the type of article creation for the new fields and defines the
expected type of parameter pArticle:
@Default
All fields will be filled by articles according to option @DefaultArticle.
Parameter pArticle is ignored (should be NULL ).
@Unique
All fields will be filled by identical articles.
Parameter pArticle is a specification according to option @DefaultArticle.
@Individual
The fields will be filled individually.
Parameter pArticle is a Vector whose elements either are NULL , if the according field should be
empty, or are a specification according to option @DefaultArticle.
@Empty
All fields are empty (possibly filled with placeholders assording to option
@EmptyFieldsPlaceholder).
Parameter pArticle specifies the number (Int) of fields to be created in the column.
Parameter pDir specifies the direction (side) where the new column is added:
@Last
new column is added to the right of current last column
@First
new column is added to the left of current first column

ParameterpAlignmentisnotsupportedyet. (Newelementsarealignedaccordingtocorresponding
options.)
Parameter pWidth specifies the width of new column:
If all columns have the same width (see option @UniformColumnWidth), the parameter is ignored.
Otherwise, if necessary, it is used to extend the Vector of widths for non-uniformly sized columns
(see option @ColumnWidths):
– In case of direction @First, the parameter value will be appended to the Vector as the new
first elememt.
– In case of direction @Last, the parameter value will be appended to the Vector as the new
last elememt if the current Vector size does not contain an element for the new column to be
added.

In case of direction @First the indices of all existing columns will be incremented and the new
column gets index 0. The position of the elements in the new column get a negative coordinate in
X dimension.
The method has no effect if the maximum allowed count of columns (see option @MaxColumns)
has already been reached.

MC_ADD_COLUMN_R;Instance;::ofml::xoi::xOiTabularPlGroup;addColumn2;\
@Default,NULL,@Last,NULL,NULL

(cid:136) addRow3(pArtSpecType(Symbol), pArticle(Any), pDir(Symbol), pAlignment(Any), pSize(Float),
...) → Void
Creates a new row and fills it with specified article(s).
Parameter pArtSpecType specifies the type of article creation for the new fields and defines the
expected type of parameter pArticle. For the possible values see same parameter of method
addColumn2() above.

29

<!-- Page 32 -->

Parameter pDir specifies the direction (side) where the new row is added:
@Last
new row is added after current last row
@First
new row is added before current first row
ParameterpAlignmentisnotsupportedyet. (Newelementsarealignedaccordingtocorresponding
options.)
Parameter pSize specifies the width of new row:
If all rows have the same size (see option @UniformRowSize), the parameter is ignored. Other-
wise, if necessary, it is used to extend the Vector of sizes for non-uniformly sized rows (see option
@RowSizes):
– In case of direction @First , the parameter value will be appended to the Vector as the new
first elememt.
– Incaseofdirection @Last , theparametervaluewillbeappendedtotheVectorasthenewlast
elememt if the current Vector size does not contain an element for the new row to be added.

In case of direction @First the indices of all existing rows will be incremented and the new row
gets index 0. The position of the elements in the new row get a negative coordinate in according
dimension.
Themethodhasnoeffectifthemaximumallowedcountofrows(seeoption@MaxRows)hasalready
been reached.

MC_ADD_EMPTY_ROW_F_SIZE3;Instance;::ofml::xoi::xOiTabularPlGroup;addRow3;\
@Empty,3,@First,NULL,NULL

(cid:136) deleteFieldElement2(pField(MObject | Int[2]), pKeepFields(Int), ...) → Void
Deletes the element from given field.
The field either is specified by its address or by the according field element.
Parameter pKeepFields specifies whether any fields have to be kept (1) or not (0). If not, empty
head and back columns resp. rows after the removal of the element will be removed from the
internal data structures.
Note:
IftheinteractorwiththeMethodCallactionisboundtoagroupelement(nottotheplanninggroup
instance), after the action no further actions may follow, which again need a target object or an
objectdefinitionasaparameter,becauseaftertheactiontheoriginalactiveobjectnolongerexists!

MC_DELETE_ME;Instance;::ofml::xoi::xOiTabularPlGroup;deleteFieldElement2;$SELF,0

(cid:136) deleteColumn(pColumn(Int), pKeepFields(Int)) → Void
Deletes all elements from the column specified by given index.
If NULL is passed for parameter pColumn the last column will be deleted.
Parameter pKeepFields specifies whether the fields have to be kept (1) or not (0). If not, the
complete column will be removed, i.e. the columns with higher indexes will be moved (shifted) to
fill the place of the removed column (including repositioning of the contained elements).
Theoperationisnotallowed/possibleifthespecifiedcolumncontainsatleastoneelementoccupying
fieldsofanothercolumn. (ThiscanbecheckedinadvanceusingmethodisStraightLine(),seeabove
in section 10.2.)
ConsiderusageofmethoddeleteLine()(seebelow)providingmoreoptionstocontrolthebehaviour.

MC_DELETE_LAST_COLUMN;Instance;::ofml::xoi::xOiTabularPlGroup;deleteColumn;NULL,0

30

<!-- Page 33 -->

deleteRow(pRow(Int), pKeepFields(Int)) → Void
(cid:136)
Deletes all elements from the row specified by given index.
If NULL is passed for parameter pRow the last row will be deleted.
Parameter pKeepFields specifies whether the fields have to be kept (1) or not (0). If not, the
complete row will be removed, i.e. the rows with higher indexes will be moved (shifted) to fill the
place of the removed row (including repositioning of the contained elements).
The operation is not allowed/possible if the specified row contains at least one element occupying
fields of another row. (This can be checked in advance using method isStraightLine(), see above in
section 10.2.)
ConsiderusageofmethoddeleteLine()(seebelow)providingmoreoptionstocontrolthebehaviour.

MC_DELETE_FIRST_ROW;Instance;::ofml::xoi::xOiTabularPlGroup;deleteRow;0,0

(cid:136) deleteLine(pType(Symbol), pIdx(Int), pKeepFields(Int), pShiftDir(Symbol), ...) → Void
Deletes all elements from the line specified by given type and index.
Parameter pType either is @Row or @Column .
If NULL is passed for parameter pIdx the last row resp. column will be deleted.
Parameter pKeepFields specifies whether the fields have to be kept (1) or not (0). If not, the
complete row resp. column will be removed, i.e. the other rows resp. columns will be moved
(shifted) to fill the place of the removed line.
The shift direction is controlled by parameter pShiftDir:
@Left
lines with higher indices will be shifted (by 1) to line with lower index
@Right
lines with lower indices will be shifted (by 1) to line with higher index
The operation is not allowed/possible if the specified line contains at least one element occupying
fields of another line. (This can be checked in advance using method isStraightLine(), see above in
section 10.2.)

MC_DELETE_LAST_COLUMN_SHIFT_R;Instance;::ofml::xoi::xOiTabularPlGroup;\
deleteLine;@Column,NULL,0,@Right

resize(pColumns(Int), pRows(Int), pArticle(Any), pAlignment(Any)) → Void
(cid:136)
Resizes the group according to given numbers for the new count of columns resp. rows.
If one of the counts is greater than the current count new fields will be created filling it with the
specified article:
ParameterpArticleeitherisaspecificationaccordingtooption@DefaultArticleorisNULL,inwhich
case articles are created as specified in option @DefaultArticle.
If there is specified a maximum allowed count of columns resp. rows (see options @MaxColumns
resp. @MaxRows),thesecountswillbeusedforresizingifthevaluespassedinparameterspColumns
or pRows are greater.
Note:
This method supports a resize operation only in positive (index count) direction (both for columns
and rows).
ParameterpAlignmentisnotsupportedyet. (Newelementsarealignedaccordingtocorresponding
options.)
The operation is not allowed/possible, if the group contains at least one element occupying more
than one field. (This can be checked in advance using method hasMultiFieldElements(), see above
in section 10.2.)

31

<!-- Page 34 -->

MC_RESIZE_4X4;Instance;::ofml::xoi::xOiTabularPlGroup;resize;4,4,NULL,NULL

rePositionAllFieldElements(pRecreatePHs(Int)) → Void
(cid:136)
Repositions all field elements.
Parameter pRecreatePHs specifies, whether placeholder instances have to be re-created (1) or not
(0). This has an effect only if option @EmptyFieldsPlaceholder has value 1.

MC_REPOS_ALL;Instance;::ofml::xoi::xOiTabularPlGroup;rePositionAllFieldElements;1

(cid:136) shiftColumns(pDir(Symbol), pCircular(Any)) → Void
Shifts all columns by one column in specified direction.
The possible direction values (parameter pDir) are:
@Left
shifting towards columns with lower indexes
@Right
shifting towards columns with higher indexes
Parameter pCircular currently is unused. The method performs a circular shift, i.e. the column
shifted out replaces the (empty) column on the other side.
The operation is not allowed/possible if the group contains at least one element occupying fields of
multiple columns!
Furthermore,incaseofnon-uniformlysizedcolumnsitisrequiredthatthecountofassignedcolumn
sizes (see option @ColumnWidths) is equal to the current count of columns! (The elements in that
Vector will be shifted accordingly.)

MC_SHIFT_COLUMNS_R;Instance;::ofml::xoi::xOiTabularPlGroup;shiftColumns;@Right,NULL

(cid:136) shiftRows(pDir(Symbol), pCircular(Any)) → Void
Shifts all rows by one row in specified direction.
The possible direction values (parameter pDir) are:
@Down
shifting towards rows with lower indexes
@Up
shifting towards rows with higher indexes
ParameterpCircularcurrentlyisunused. Themethodperformsacircularshift, i.e. therowshifted
out replaces the (empty) row on the other side.
The operation is not allowed/possible if the group contains at least one element occupying fields of
multiple rows!
Furthermore, in case of non-uniformly sized rows it is required that the count of assigned row sizes
(see option @RowSizes) is equal to the current count of rows! (The elements in that Vector will be
shifted accordingly.)

MC_SHIFT_ROWS_UP;Instance;::ofml::xoi::xOiTabularPlGroup;shiftRows;@Up,NULL

replaceField(pRepl(MObject |Int[2]), pArticle(Any), pAlignment(Any)) → MObject |Void
(cid:136)
Replaces given field (element) by an instance of specified article.
In parameter pRepl, instead of a field element, the address of a field or a placeholder instance may
be passed.

32

<!-- Page 35 -->

The replacement article can be specified in parameter pArticle in the following ways:
– NULL :
Creates article according to option @DefaultArticle.
– Field address (Int[2]):
20
Clones article from specified field .
– Explicit article (Any[]):
Parameter pArticle is a specification according to option @DefaultArticle.
Parameter pAlignment is not supported yet. (New element is aligned according to corresponding
options.)
In case of invalid parameters, the method has no effect, i.e. the element specified by parameter
pRepl (if any) will not be removed.
It is the responsibility of the client to specify a replacement article that fits into the field resp., in
case of a multi-field element, that relevant neighbor fields are empty.
If a new element (successfully) has been created, it gets the name of the replaced field element (if
any) and return value is the reference to this new instance, otherwise return value is NULL .
Note:
IftheinteractorwiththeMethodCallactionisboundtoagroupelement(nottotheplanninggroup
instance), after the action no further actions may follow, which again need a target object or an
object definition as a parameter, because after the (successful) action the original active object no
longer exists!

MC_REPLACE_ME_BY_DEFAULT;Instance;::ofml::xoi::xOiTabularPlGroup;replaceField;\
$SELF,NULL,NULL

moveFieldElement(pFieldEl(MObject), pDestType(Symbol), pDestination(Any), ...) → Int[2] |Void
(cid:136)
Moves given field element to a new destination (field).
Currently, this operation can be performed only if all columns have the same width (see
option @UniformColumnWidth) and if all rows have the same depth resp. height (see option
@UniformRowSize).
Thedestination(parameterpDestination)maybegivenintwoways. Whichwayisusedisspecified
in parameter pDestType:
@Address
The destination is determined by a field address (Int[2]).
@DirNumber
The destination is determined by the direction of movement and a number of fields by which
to move the element in that direction.
The according value in parameter pDestination is a Vector of
1. direction (Symbol), for possible values see method getNeighbor()
2. number of fields (Int)
The operation will be rejected if the element at the new destination would occupy fields which are
already occupied by other field elements.
If an additional optional parameter is given, it specifies whether the element may occupy non-
existing fields at the new destination. If this parameter has value 1 (yes/true) and the element
would occupy non-existing fields at the new destination, according rows resp. columns will be
added to the table structure.
Default is 0 (no/false), i.e., the operation will be rejected if the element would occupy non-existing
fields at the new destination.
If the operation is rejected, return value is NULL, otherwise the new address of the element.

20 IfthatfieldisemptythefieldspecifiedbypReplbecomesempty,too.

33

<!-- Page 36 -->

Destination type @DirNumber can be used to implement an action bound to an interactor with
symbol types Pos2Left and the like:

MC_MOVE_ME_LEFT;Instance;::ofml::xoi::xOiTabularPlGroup;moveFieldElement;\
$SELF,@DirNumber,[@L,1],1

# 11 Class xOiCustomPlGroup

This base class supports the realization of groups with specific (custom) planning logics.
In contrast to the other planning group classes described in the previous sections, this class does not
implement specific planning logics, but supports general concepts known from those classes.
Specific (custom) logics have to be implemented in derived classes.
The following general concepts are supported:
(cid:136) Controlling aspects of the behavior by means of options in a control data table, here
customplgroup.csv . In particular, this refers to the generation of common properties. For all
options see Application Note [an0601].
(cid:136) Elements of the group may be assigned to self-defined categories, see section 7.2.
(cid:136) A distinction can be made between 2 types of group elements:
– Elements defining the actual layout of the group.
Methods regarding layout elements are described in 11.1.
– Additional, other (non-layout) elements.
Typically, they are created based on the current layout (defined by the layout elements), e.g.
frames for sofa arrangements, links between layout elements and alike.
Methods regarding additional elements are described in 11.2.
(cid:136) Generic implementation of methods getAddStateCode() and setAddStateCode() (interface Article).
Member variables of derived classes that are to be encoded are just specified using hook method
getAddStateMembers().
(cid:136) Generic implementation of interface CompositeArticle.
(cid:136) Checking for free attach points (see section 11.3).
(cid:136) Recordingneighbor-relationshipsbetweenlayoutelementsbasedonOFMLattach points(optional).
Two layout elements are called neighbors if they were placed next to each other using a pair of
21
attach points .
This functionality is enabled with (default) value 1 of option @StoreNeighborship (see [an0601].
Then, the class behaves like a reduced xOiLayoutGroup without handling for branches and fork
elements. Thisincludesrepositioningoflayoutelementsafteradimensionchangeorafterinsertion
between two existing elements if option @InsertMode has the value 1 resp. 2.
Methods regarding neighbor-relationships are described in 11.4.

### 11.1 Layout elements

Note:
Theorderoftheelementsinthelistoflayoutelementsreflectstheorderofinsertionresp. removalofthe
elements!

(cid:136) getLayoutElCount() → Int
Returns the current number of elements in the list of layout elements.
21 Note: Twolayoutelementsmaybelocatednexttoeachotherbutbenoneighborsbecausetheywerenotplacednext
toeachotherusingapairofattachpoints.

34

<!-- Page 37 -->

MC_LAYOUT_ELCOUNT;Instance;::ofml::xoi::xOiCustomPlGroup;getLayoutElCount;

(cid:136) isLayoutEmpty() → Int
Returns True (1) if the group does not contain any layout element.
MC_IS_LAYOUT_EMPTY;Instance;::ofml::xoi::xOiCustomPlGroup;isLayoutEmpty;

isLayoutElement(pObj(MObject)) → Int
(cid:136)
Returns True (1) if given instance is a layout element.
MC_IS_LAYOUT_EL;Instance;::ofml::xoi::xOiCustomPlGroup;isLayoutElement;$SELF

(cid:136) firstLayoutElement() → MObject | Void
Returns the first entry from the list of current layout elements (or NULL if the list currently is
empty).
MC_FIRST_LAYOUT_EL;Instance;::ofml::xoi::xOiCustomPlGroup;firstLayoutElement;

isFirstLayoutElement(pObj(MObject)) → Int
(cid:136)
Returns True (1) if given instance is the first element in the list of current layout elements.
MC_IS_FIRST_LAYOUT_EL;Instance;::ofml::xoi::xOiCustomPlGroup;isFirstLayoutElement;$SELF

(cid:136) lastLayoutElement() → MObject | Void
Returns the last created element layout element (or NULL if the list of layout elements currently is
empty).
MC_LAST_LAYOUT_EL;Instance;::ofml::xoi::xOiCustomPlGroup;lastLayoutElement;

isLastLayoutElement(pObj(MObject)) → Int
(cid:136)
Returns True (1) if given instance is the last element in the list of current layout elements.
MC_IS_LAST_LAYOUT_EL;Instance;::ofml::xoi::xOiCustomPlGroup;isLastLayoutElement;$SELF

(cid:136) canBeRemovedFromLayout(pObj(MObject)) → Int
Returns True (1) if given layout element can be deleted (and removed from the neighbor data
structure).
A layout element can be removed (by the definition of this implementation) if option
@StoreNeighborship has the value 0 or if one of the following conditions is met:
– it has no neighbors but is not the single layout element left
– it has only 1 neighbor
– it has 2 neighbors and the insert mode is 2 (see option @InsertMode)
MC_CAN_REMOVE;Instance;::ofml::xoi::xOiCustomPlGroup;canBeRemovedFromLayout;$SELF

setAdjustSide4Insertion(pAdjustSide(Symbol |MObject), ...) → Void
(cid:136)
Specifies the neighbors of the reference object which have to be moved due to upcoming insertion
of a new element between the reference object and its current neighbor.
The parameter either specifies the attach point of the reference object to which the relevant imme-
diate neighbor is attached, or specifies the immediate neighbor itself.
If this method is not called before the upcoming insertion, the current active attach point of the
reference object is used (if any) to determine the neighbors to be adjusted (if there is a neighbor
attached to that attach point).
If an additional optional parameter is given it specifies the attach point (Symbol) of the upcoming
new neighbor to be used for re-positioning the neighbors at pAdjustSide. If the parameter is not
givenorisnotaSymbol,thesameattachpointisusedthatdeterminestheneighborstobeadjusted
(see above), if the upcoming new neighbor has such an attach point.

35

<!-- Page 38 -->

MC_SET_ADJUST_SIDE_4_INSERT;Instance;::ofml::xoi::xOiCustomPlGroup;\
setAdjustSide4Insertion;@AP_R

(cid:136) setAdjustSide4Removal(pAdjustSide(Symbol |MObject), ...) → Void
Specifies the neighbors which have to be moved due to upcoming removal of a layout element
between two neigbors.
The parameter either specifies the attach point of the element up to be removed to which the
relevant immediate neighbor is attached, or specifies the immediate neighbor itself.
Note: Removal of an inner element is allowed/possible only if it has exactly two neighbors!
TheneighborattheothersideaspAdjustSidewillbeusedasthereferenceobjectforre-positioning
the neighbors at pAdjustSide.
If an additional optional parameter is given it specifies the attach point (Symbol) of the reference
object to be used for re-positioning the neighbors at pAdjustSide. If the parameter is not given or
is not a Symbol, the attach point of reference object is used that was used to connect it with the
element up to be removed.

MC_SET_ADJUST_SIDE_4_REMOVE;Instance;::ofml::xoi::xOiCustomPlGroup;\
setAdjustSide4Removal;@AP_R

### 11.2 Additional elements

(cid:136) hasAdditionalElements() → Int
Returns True (1) if the group contains additional elements.

MC_HAS_OTHER_ELEMS;Instance;::ofml::xoi::xOiCustomPlGroup;hasAdditionalElements;

isAdditionalElement(pObj(MObject)) → Int
(cid:136)
Returns True (1) if given instance is contained in the list of additional elements.

MC_IS_ADDITIONAL_EL;Instance;::ofml::xoi::xOiCustomPlGroup;isAdditionalElement;$SELF

### 11.3 Free attach points

An attach point is free, if it was not used to connect with a neighbor layout element and if there is no
(other) sibling or child element occupying this attach point geometrically.
The first condition applies only to layout elements and requires (default) value 1 for option
@StoreNeighborship.

hasFreeAttPts2(pObj(MObject), pCheckAll(Int)) → Int
(cid:136)
Returns True (1) if given instance has at least one free OFML attach point, otherwise False (0).
Parameter pCheckAll specifies whether all attach points of given instance have to be checked (1) or
only the additional attach points (0, i.e. ignoring the standard attach points).

MC_HAS_FREE_ATTPTS;Instance;::ofml::xoi::xOiCustomPlGroup;hasFreeAttPts2;$SELF,0

(cid:136) isFreeAttPt(pObj(MObject), pAttPt(Symbol)) → Int
Returns True (1) if the specified OFML attach point (key) currently is defined for the given group
element and if it is free.
Otherwise returns False (0).

MC_IS_ATTPT_R_FREE;Instance;::ofml::xoi::xOiCustomPlGroup;isFreeAttPt;$SELF,@ATTPT_R

36

<!-- Page 39 -->

### 11.4 Neighbors

Note:
Neighbor-relationships between layout elements are stored in an internal data structure (only) if option
@StoreNeighborship has the (default) value 1.

(cid:136) getNeighbor(pObj(MObject), pAttPt(Symbol)) → MObject | Void
Returns the neighbor of given layout element at given attach point.
Returns NULL if given instance is not registered in the neighbor map or if there is no neighbor at
given attach point.
MC_NEIGHBOR_R;Instance;::ofml::xoi::xOiCustomPlGroup;getNeighbor;$SELF,@ATTPT_R

See also method getAdjacentElement() below.
getNeighborCount(pObj(MObject)) → Int
(cid:136)
Returns the number of all current (immediate) neighbors of specified layout element.
If the given instance is not registered in the neighbor map, the return value is 0.

MC_NEIGHBOR_COUNT;Instance;::ofml::xoi::xOiCustomPlGroup;getNeighborCount;$SELF

(cid:136) hasNeighbors(pObj(MObject)) → Int
Returns True (1) if given instance is a layout element and if it currently has registered neighbors.

MC_HAS_NEIGHBORS;Instance;::ofml::xoi::xOiCustomPlGroup;hasNeighbors;$SELF

(cid:136) getAdjacentElement(pObj(MObject), pAttPt(Symbol)) → MObject | Void
Returns the group element which occupies the specified attach point of given layout element.
IncontrasttogetNeighbor()(seeabove)thismethodalsoconsiderselementsnotbeinga(registered)
neighbor of given layout element, i.e. which are not explicitely connected to it but are just located
beside it occupying the specified attach point geometrically.
Returns if there is no attach point currently defined with given key or if there is no group
NULL
element occupying the specified attach point.

MC_ADJACENT_R;Instance;::ofml::xoi::xOiCustomPlGroup;getAdjacentElement;$SELF,@ATTPT_R

# 12 Class xOiCustomModule

This base class can be used to implement custom modules.
Amoduleisacompositearticle(OFMLinterfaceCompositeArticle[article])thatconsistsofafixedorvari-
ablenumberofsub-articles. Asarule,amodulerepresentsapseudo-article(seecategory@PseudoArticle
in the specification of OFML interface Article [article]).
Aninstanceofthisclassdoesnothaveitsowngeometry,butitsgeometryismadeupofthegeometriesof
its sub-elements and their position resp. rotation in the local coordinate system of the module instance.
The application note [an oap] contains a detailed description of the class, which is why it is not included
here.
Methods of the class that are suitable for use in MethodCall actions are
assignCommonPropValues() and updateCommonProperties() 22 , which have the same specification
(cid:136)
and semantics as the methods described in section 7.3 for planning groups, and
all methods from the subsection ”Managing elements (parts)” in [an oap].
(cid:136)

22 subsection”Properties”in[an oap]

37

<!-- Page 40 -->

# A Alphabetic index of methods

addColumn2() ... 28
addNeighbor() ... 28
addRow3() ... 29
assignCommonPropValues() ... 9
assignElementCat() ... 8
canBeRemovedFromLayout() ... 15, 35
canSwapNeighbors() ... 22
checkElDistance() ... 10
checkPropValue() ... 6
clearElementCat() ... 9
deleteColumn() ... 30
deleteFieldElement2() ... 30
deleteLine() ... 31
deleteRow() ... 30
flipElement() ... 20
firstFieldElement() ... 26
firstLayoutElement() ... 14, 35
firstObj() ... 11
getAdjacentElement() ... 15, 37
getArticleSpec() ... 7
getBranch() ... 17
getBranchPredecessor() ... 18
getBranchSuccessor() ... 18
getChID() ... 7
getClass() ... 3
getColumnCount() ... 26
getColumnOf() ... 27
getColumnWidth() ... 26
getDepth() ... 5
getElCount() ... 11
getElPos() ... 11
getFather() ... 4
getFieldOf() ... 27
getFirstBranchElem() ... 17
getFirstCatElem() ... 18
getFirstForkElem() ... 18

38

<!-- Page 41 -->

getForkPredecessor() ... 18
getForkSuccessor() ... 18
getHeight() ... 5
getLastBranchElem() ... 17
getLastCatElem() ... 18
getLastForkElem() ... 18
getLatestBranch() ... 17
getLayoutElCount() ... 34
getMaxColumns() ... 25
getMaxRows() ... 25
getMTID() ... 7
getNeighbor() ... 15, 28, 37
getNeighborCount() ... 15, 37
getPlaceholderCreationOn() ... 26
getPropState() ... 6
getPropState2() ... 6
getRoot() ... 4
getRowCount() ... 26
getRowOf() ... 27
getRowSize() ... 26
getRtAxis() ... 4
getTrAxis() ... 4
getUniformColumnWidth() ... 25
getUniformRowSize() ... 25
getWidth() ... 5
hasAdditionalElements() ... 23, 36
hasForkElements() ... 16
hasFreeAttPts2() ... 16, 36
hasMember() ... 3
hasMultiFieldElements() ... 27
hasNeighbors() ... 15, 37
hasProperties() ... 6
hasProperty() ... 6
isAdditionalElement() ... 23, 36
isBranchElement() ... 17
isBusyAttPt() ... 13
isCat() ... 3
isElementCat() ... 9

39

<!-- Page 42 -->

isEmpty() ... 11
isFlippedElement() ... 21
isFieldElement() ... 27
isFirstBranchElem() ... 17
isFirstLayoutElement() ... 15, 35
isFirstObj() ... 12
isFirstOrLastBranchElem() ... 17
isForkElement() ... 16
isFreeAttPt() ... 16, 36
isGrandSubArticle() ... 10
isLastBranchElem() ... 17
isLastLayoutElement() ... 15, 35
isLastObj() ... 12
isLatestBranch() ... 17
isLayoutElement() ... 14, 35
isLayoutEmpty() ... 14, 26, 35
isMultiFieldElement() ... 27
isNodeElement() ... 17
isNotEmpty() ... 11
isStraightLine() ... 27
lastFieldElement() ... 27
lastLayoutElement() ... 15, 35
lastObj() ... 11
markAsForkElement() ... 16
moveFieldElement() ... 33
neighbor() ... 12
removeElementCat() ... 8
replaceElement() ... 12, 19
replaceElement2() ... 13, 20
replaceField() ... 32
rePositionAllFieldElements() ... 32
resize() ... 31
setAdjustSide4Insertion() ... 22, 35
setAdjustSide4Removal() ... 36
setAdjustSide4Removal2() ... 22
setMaxColumns() ... 25
setMaxRows() ... 25
setPlaceholderCreationOn() ... 26

40

<!-- Page 43 -->

setSelectability4ElemCat() ... 9
setUniformFieldSize() ... 25
shiftColumns() ... 32
shiftRows() ... 32
startNewBranch() ... 19
swapNeighbors() ... 21
unMarkAsForkElement() ... 16
updateCommonProperties() ... 9

41

<!-- Page 44 -->

# B Methods mapped to object types

### B.1 All article types

Note:
Includes interfaces Base, Complex, Property and Article.

checkPropValue() ... 6
getArticleSpec() ... 7
getClass() ... 3
getDepth() ... 5
getFather() ... 4
getHeight() ... 5
getPropState() ... 6
getPropState2() ... 6
getRoot() ... 4
getRtAxis() ... 4
getTrAxis() ... 4
getWidth() ... 5
hasMember() ... 3
hasProperties() ... 6
hasProperty() ... 6
isCat() ... 3

### B.2 GoMetaType

getChID() ... 7
getMTID() ... 7

### B.3 All planning group classes

assignCommonPropValues() ... 9
assignElementCat() ... 8
checkElDistance() ... 10
clearElementCat() ... 9
isElementCat() ... 9
isGrandSubArticle() ... 10
removeElementCat() ... 8
setSelectability4ElemCat() ... 9
updateCommonProperties() ... 9

42

<!-- Page 45 -->

### B.4 xOiJointPlGroup

firstObj() ... 11
getElCount() ... 11
getElPos() ... 11
isBusyAttPt() ... 13
isEmpty() ... 11
isFirstObj() ... 12
isLastObj() ... 12
isNotEmpty() ... 11
lastObj() ... 11
neighbor() ... 12
replaceElement() ... 12
replaceElement2() ... 13

### B.5 xOiLayoutGroup

canBeRemovedFromLayout() ... 15
canSwapNeighbors() ... 22
firstLayoutElement() ... 14
flipElement() ... 20
getAdjacentElement() ... 15
getBranch() ... 17
getBranchPredecessor() ... 18
getBranchSuccessor() ... 18
getFirstBranchElem() ... 17
getFirstCatElem() ... 18
getFirstForkElem() ... 18
getForkPredecessor() ... 18
getForkSuccessor() ... 18
getLastBranchElem() ... 17
getLastCatElem() ... 18
getLastForkElem() ... 18
getLatestBranch() ... 17
getNeighbor() ... 15
getNeighborCount() ... 15
hasAdditionalElements() ... 23
hasForkElements() ... 16
hasFreeAttPts2() ... 16

43

<!-- Page 46 -->

hasNeighbors() ... 15
hasProperty() ... 6
isAdditionalElement() ... 23
isBranchElement() ... 17
isFlippedElement() ... 21
isFirstBranchElem() ... 17
isFirstLayoutElement() ... 15
isFirstOrLastBranchElem() ... 17
isForkElement() ... 16
isFreeAttPt() ... 16
isLastBranchElem() ... 17
isLastLayoutElement() ... 15
isLatestBranch() ... 17
isLayoutElement() ... 14
isLayoutEmpty() ... 14
isNodeElement() ... 17
lastLayoutElement() ... 15
markAsForkElement() ... 16
replaceElement() ... 19
replaceElement2() ... 20
setAdjustSide4Insertion() ... 22
setAdjustSide4Removal2() ... 22
startNewBranch() ... 19
swapNeighbors() ... 21
unMarkAsForkElement() ... 16

### B.6 xOiTabularPlGroup

addColumn2() ... 28
addNeighbor() ... 28
addRow3() ... 29
deleteColumn() ... 30
deleteFieldElement2() ... 30
deleteLine() ... 31
deleteRow() ... 30
firstFieldElement() ... 26
getColumnCount() ... 26
getColumnOf() ... 27

44

<!-- Page 47 -->

getColumnWidth() ... 26
getFieldOf() ... 27
getPlaceholderCreationOn() ... 26
getMaxColumns() ... 25
getMaxRows() ... 25
getNeighbor() ... 28
getRowCount() ... 26
getRowOf() ... 27
getRowSize() ... 26
getUniformColumnWidth() ... 25
getUniformRowSize() ... 25
hasMultiFieldElements() ... 27
isFieldElement() ... 27
isLayoutEmpty() ... 26
isMultiFieldElement() ... 27
isStraightLine() ... 27
lastFieldElement() ... 27
moveFieldElement() ... 33
replaceField() ... 32
rePositionAllFieldElements() ... 32
resize() ... 31
setMaxColumns() ... 25
setMaxRows() ... 25
setPlaceholderCreationOn() ... 26
setUniformFieldSize() ... 25
shiftColumns() ... 32
shiftRows() ... 32

### B.7 xOiCustomPlGroup

canBeRemovedFromLayout() ... 35
firstLayoutElement() ... 35
getAdjacentElement() ... 37
getNeighbor() ... 37
getNeighborCount() ... 37
getLayoutElCount() ... 34
hasAdditionalElements() ... 36
hasFreeAttPts2() ... 36

45

<!-- Page 48 -->

hasNeighbors() ... 37
isAdditionalElement() ... 36
isFirstLayoutElement() ... 35
isFreeAttPt() ... 36
isLastLayoutElement() ... 35
isLayoutElement() ... 35
isLayoutEmpty() ... 35
lastLayoutElement() ... 35
setAdjustSide4Insertion() ... 35
setAdjustSide4Removal() ... 36

46

<!-- Page 49 -->

# C Document history

Version 1.13 (May 10, 2025)
(cid:136) Added description of methods isFirstLayoutElement() and isLastLayoutElement() for class
xOiLayoutGroup (section 9.1).
Added description of method getNeighborCount() for class xOiLayoutGroup (section 9.1) and class
(cid:136)
xOiCustomPlGroup (section 11.4).

Version 1.12 (November 19, 2024)
(cid:136) Added description of method replaceElement2() for class xOiLayoutGroup (section 9.4).
Added some notes regarding the cloning of field elements of instances of class xOiTabularPlGroup
(cid:136)
occuring in certain scenarios (section 10).
Added description of rePositionAllFieldElements() for class xOiTabularPlGroup (section 10.3).
(cid:136)
Corrections in the specification of methods deleteColumn(), deleteRow() and deleteLine() of class
(cid:136)
xOiTabularPlGroup (section 10.3).
New section 12 introducing class xOiCustomModule.
(cid:136)

Version 1.11 (November 6, 2023)
More details on some methods regarding element categories implemented in all planning group
(cid:136)
classes (section 7.2).
AddeddescriptionofmethodsetSelectability4ElemCat(()implementedinallplanninggroupclasses
(cid:136)
(section 7.2).
(cid:136) Addedsection7.4describingothermethodsthatcanbeusedforallplanninggroupclasses,namely
isGrandSubArticle() and checkElDistance().
(cid:136) Added section covering methods regarding additional elements of class xOiLayoutGroup
(section 9.5).
(cid:136) UpdateddescriptionofclassxOiTabularPlGroupwithrespecttoneighborshipandhandlingofempty
head and back columns resp. rows (section 10).
(cid:136) Added description of methods isFieldElement() and isMultiFieldElement() for class
xOiTabularPlGroup (section 10.2).
(cid:136) Added section for class xOiCustomPlGroup (section 11).

Version 1.10 (December 2, 2022)
(cid:136) UpdateddescriptionofmethodcanBeRemovedFromLayout()forclassxOiLayoutGroup(section9.1).

Version 1.9 (October 24, 2022)
(cid:136) More details on the various implementations of getWidth(), getHeight() and getDepth(), possibly
hindering the usage in OAP projects (section 3).
(cid:136) Added description of methods getPropState2() and checkPropValue() in interface Property
(section 4).
(cid:136) Added description of method getAdjacentElement() for class xOiLayoutGroup (section 9.1).
Removed description of method swapFields() for class xOiTabularPlGroup (since it is not really
(cid:136)
directly usable in MethodCall actions in OAP).
Added description of method moveFieldElement() for class xOiTabularPlGroup (section 10.3).
(cid:136)

Version 1.8 (December 6, 2021)
Added description of method getChID() for class GoMetaType (section 6).
(cid:136)

47

<!-- Page 50 -->

Version 1.7 (October 19, 2021)
Reorganization of document structure.
(cid:136)
(cid:136) Added description of method hasProperties() in interface Property (section 4).
(cid:136) Added section covering functionality common for all planning group classes (section 7).
(cid:136) Added description of method updateCommonProps() implemented in all planning group classes
(section 7.3).
(cid:136) More precise description of method replaceElement() and added description of method
replaceElement2() for class xOiJointPlGroup (section 8.2).
(cid:136) Added description of methods flipElement(), isFlippedElement(), swapNeighbors(),
canSwapNeighbors(), setAdjustSide4Insertion() and setAdjustSide4Removal() for class
xOiLayoutGroup (section 9.4).
(cid:136) Added section for class xOiTabularPlGroup (section 10).
(cid:136) Added appendix listing the methods per object type (appendix B).
(cid:136) Added this history appendix.

48