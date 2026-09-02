# AppNote_OAP_DataCreation_EN

> Auto-generated from AppNote_OAP_DataCreation_EN.pdf for AI consumption.

---


<!-- Page 1 -->

# Application Note

## (2025-05-21)

# Notes on OAP Data creation and Planning groups

# Contents

1 General ............................................................................................................................................................ 3
1.1 Extensions in table structures / EBase ................................................................................................... 3
1.2 Separate series for OAP data ................................................................................................................. 3
1.3 Name conventions for identifiers .......................................................................................................... 3
2 Conditions/Expressions ................................................................................................................................... 4
2.1 OAP expressions vs. OCD expressions ................................................................................................... 4
2.2 Using standard methods ........................................................................................................................ 4
2.3 Article at top planning level? ................................................................................................................. 5
2.4 Numerical metaproperties .................................................................................................................... 5
2.5 Special Symbols ..................................................................................................................................... 5
2.6 Expressions with integers ...................................................................................................................... 6
3 Interactors ....................................................................................................................................................... 7
3.1 Recommendations for using the 3 abstract symbol sizes ..................................................................... 7
3.2 Interactor for planning group or group elements? ............................................................................... 7
3.3 Dynamic interactors .............................................................................................................................. 8
3.4 3D interactor symbols ......................................................................................................................... 11
3.5 Correct configuration context?............................................................................................................ 13
4 Actions........................................................................................................................................................... 14
4.1 Creating articles via xOiCreateArticle() resp. xOiCloneArticle() ........................................................... 14
4.2 Change direction in DimChange actions .............................................................................................. 14
4.3 Nesting of method calls ....................................................................................................................... 15
4.4 Notes on DeleteObj.............................................................................................................................. 15
4.5 RG properties ....................................................................................................................................... 16
4.6 Action type NoAction ........................................................................................................................... 16
5 Planning groups ............................................................................................................................................. 17
5.1 Using object category MethodCall ...................................................................................................... 17
5.2 Changing dimensions of group elements ............................................................................................ 18
5.3 Dimension change based on na-Metaproperties ................................................................................ 21
5.4 Group-specific entries in the control data table .................................................................................. 22
5.5 Changing articles via replaceElement() ................................................................................................ 22
5.6 Non-Layout articles with xOiJointPlGroup ........................................................................................... 22
5.7 Additional start elements .................................................................................................................... 23
5.8 Removability of group elements ......................................................................................................... 23
5.9 Common properties / Group properties ............................................................................................. 24
5.10 Persistency ........................................................................................................................................... 28
5.11 Overriding methods of XOI base classes.............................................................................................. 30
5.12 Managing the property state of group elements ................................................................................ 31
5.13 Reaction to property changes of elements ......................................................................................... 32
5.14 Collision detection ............................................................................................................................... 34
6 Base class xOiCustomModule ........................................................................................................................ 35
6.1 Module initialization ............................................................................................................................ 36

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 1/52

<!-- Page 2 -->

6.2 Properties ............................................................................................................................................ 37
6.3 Managing elements (parts).................................................................................................................. 39
7 OFML-Debugging ........................................................................................................................................... 41
7.1 Debugging the xOiOAPManager .......................................................................................................... 41
7.2 Debugging CreateObj ........................................................................................................................... 41
7.3 Usage of xOiOAPManager::setDBMode() ............................................................................................ 42
8 Miscellaneous ............................................................................................................................................... 43
8.1 EBase for control data tables ............................................................................................................... 43
8.2 Metatype-Type-Mapping ..................................................................................................................... 43
8.3 Auxiliary objects with OAP interactors ................................................................................................ 44
8.4 Use of event @RecreationModeFinished ............................................................................................ 44
Appendix ............................................................................................................................................................... 46
A. Specification and Usage of xOiCreateArticle/2() and xOiCloneArticle() ................................................... 46
B. Document history .................................................................................................................................... 50

## References

[an0601] Application Note on Control Data Tables (AN-2006-01). EasternGraphics GmbH
[article] The OFML Interfaces Article und CompositeArticle (Specification). EasternGraphics GmbH
[methods] Useful OFML methods for OAP data. EasternGraphics GmbH
[oap] OAP – OFML Aided Planning (Specification). EasternGraphics GmbH
[ocd] OCD – OFML Commercial Data (Specification).
Industrieverband Büro- und Arbeitswelt e.V. (IBA)
[ofml] OFML – Standardized Data Description Format of the Office Furniture Industry.
Version 2.0, 3rd revised edition.
Industrieverband Büro- und Arbeitswelt e.V. (IBA)
[property] The OFML Interface Property (Specification). EasternGraphics GmbH
[xoi] XOI – Library extending the basic OFML implementation library OI (Documentation).
EasternGraphics GmbH

Except [xoi], the specifications are available via the pCon Download Center
https://download-center.pcon-solutions.com
in the category OFML Specifications.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 2/52

<!-- Page 3 -->

# 1 General

## 1.1 Extensions in table structures / EBase

In the course of the further development of OAP , it occasionally comes to extensions (changes) of already used
tables resp. to the definition of new tables. This necessarily causes the release of a new format version (minor or
major) 1 . In order to ensure correct processing of the OAP data, the used format version has to be stored in table
Version.
With each new major resp. minor version of OAP also a corresponding new EBase table description file
oap_<major>_<minor>.inp_descr is provided.

## 1.2 Separate series for OAP data

By means of key in the registration file of an series, another series can be referenced in
oap_program OFML
which the data for the articles of the series are located.
OAP OFML
In the following situations it is necessary or advisable to create the data in a separate series:
OAP
• The OAP data refers to articles from several OFML series.
• Planning groups are used in the OAP project.
The easiest way to integrate a planning group into the catalog is to create an own (pseudo) article in the
OCD data 2 . (In any case, an own article for the planning group is required if OAP interactors are bound
to it.) In most cases, it does not make sense to include the article for the planning group(s) together
with the actual articles in a single OCD database unless there is such a close coupling between OCD
data and OAP data that also a simultaneous distribution is indicated.
• The data changes more frequently 3 or in a different rhythm than the data, and the manu-
OAP OFML
facturer's distribution processes allow for a separate distribution of the data.
OAP
4
• OFML data and OAP data are created or maintained (in parallel) by different persons .

## 1.3 Name conventions for identifiers

In most tables, identifiers (field type ID) are used as access keys. As long as there is no application for OAP data
creation, these keys must be manually defined. For a quicker orientation in the tables 5 it is recommended to
mark the purpose of an identifier with a standardized prefix. The "OAP style guide" contains corresponding rec-
ommendations.

1 Conversely, a new minor version can also contain only enhancements that do not require any changes in the table structures
(e.g., new interactor symbols).
2 usually without price and properties, but possibly with an article short text
3 which is probably true for the early stages of most projects
OAP
4 in the case of OAP e.g. by an external partner
5 both for the person creating the data, but also for support staff

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 3/52

<!-- Page 4 -->

# 2 Conditions/Expressions

## 2.1 OAP expressions vs. OCD expressions

The syntax of expressions in OAP differs from the syntax in OCD expressions [ocd]. Those who have only created
OCD data so far have to retrain a bit in this regard. (However, programmers who have already used the OFML
programming language should not have any major difficulties since the syntax is very similar.)
OAP expressions are described in detail in appendix A of the OAP specification. For the start, focus on section
A.4. For a quicker switch from OCD to OAP , here is an overview of the operators used in conditions (logical
expressions):

Operator OCD OAP
OR ||
OR relation
AND &&
AND relation
<
Is lower than < ( LT )
<= LE <=
Is lower equal ( )
==
Is equal = (EQ)
<> (NE) !=
Is not equal
>=
Is greater equal => (GE)
>
Is greater than > (GT)

It should also be noted that expressions in OCD operate with OCD characteristics, whereas expressions in OAP
C
operate with OFML properties. This particularly affects OCD characteristics with data type (Char): if a list of
values is associated with these characteristics, the values of the OFML properties generated for these character-
istics are symbols (rather than character strings). For comparison, here two conditions in OCD and OAP identical
in content:

OCD : Legs = 'ALU'
OAP : Legs == @ALU

Another significant difference is the representation of string literals (constants): in , these are enclosed in
OCD
single quotation marks (see example above), in , however, in double quotation marks ( "ALU" ).
OAP

## 2.2 Using standard methods

In expressions (to determine the position of interactor symbols or to formulate conditions for interactors or
actions), the use of project-specific implemented methods should be avoided as far as possible, using property
values and/or standard methods instead.
The accompanying document „Useful OFML methods for OAP data“ [methods] describes useful standard
methods.
Following section provides an example of the usage of standard methods.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 4/52

| Operator | OCD | OAP |
| --- | --- | --- |
| OR relation | OR | || |
| AND relation | AND | && |
| Is lower than | < (LT) | < |
| Is lower equal | <= (LE) | <= |
| Is equal | = (EQ) | == |
| Is not equal | <> (NE) | != |
| Is greater equal | => (GE) | >= |
| Is greater than | > (GT) | > |

<!-- Page 5 -->

## 2.3 Article at top planning level?

In OAP data creation, there is often a requirement that certain interactors are not valid (should not be displayed)
6
if the article in question is at the top planning level, i.e., if it is not a sub-article of a composite article .
Instead of programming a special method in the (specific) class of the article that checks this condition, standard
methods getFather() and getRoot() 7 should be used.

oap_methodcall.csv:
MC_GET_FATHER;Instance;@IF_Base;getFather;
MC_GET_ROOT ;Instance;@IF_Base;getRoot ;

With corresponding actions (table Action) the condition in table Interactor can be formulated as follows:

methodCall("AC_call_GET_FATHER") != methodCall("AC_call_GET_ROOT")

or if it is to be linked to a condition for the case that the article is a sub-article of a composite article:

methodCall("AC_call_GET_FATHER") == methodCall("AC_call_GET_ROOT") ? 0 : <condition>

## 2.4 Numerical metaproperties

Properties for selecting a value from a list of integers or floating-point numbers created in the metadata (table
go_types ), using formats chi and chf respectively, for historical/technical reasons return the character string
representation of the current value via the Property interface, e.g., instead of the number 1200 the string
"1200" .
Thus, these properties cannot be used directly in in expressions for comparison with numeric values or for
OAP
determining a coordinate for the position of interactor symbols! Instead, functions int() and float() have to be
used to convert the string value into an integer or a floating-point number.

## 2.5 Special Symbols

Occasionally, in expressions Symbols have to be specified that cannot be represented as a Symbol literal in nor-
mal form. The alternative known from OFML of using the constructor Symbol() is not applicable in OAP !
Instead, the conversion function symbol() or the alternative form to represent a Symbol literal (see appendix
A.3.2 in the OAP specification) have to be used.

An example for a PropChange action:

PC_SET_OPT_WITHOUT;Value;OPT;symbol("---")

or

PC_SET_OPT_WITHOUT;Value;OPT;@"---"

6 e.g., of a planning group (see section 5)
7 For the meaning of these both methods see [methods] or [ofml].

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 5/52

<!-- Page 6 -->

## 2.6 Expressions with integers

The behavior described in appendix A.4.10 of the OAP specification regarding binary arithmetic operators has a
small "pitfall" when using integer operands (type Int), especially in division:
"If both operands have a numeric type and at least one operand has type Float, the other operand,
if necessary, is converted to Float and the calculation is performed in Float. The result then also
has type Float. Otherwise, the result has the same type like both operands."

In other words: If both operands have type Int, the result also has type Int. As a consequence in division, the
possibly occurring non-integer remainder of the division is omitted!

This is particularly important in expressions for positions of interactor symbols (table NumTripel) using properties
of type "i"!

Example:
The active object has a property DEPTH of type "i", which indicates the current depth of the object in millimeters.
The interactor symbol has to be placed centered in depth. Since the corresponding Z coordinate has to be given
in meters, possibly the following expression would be specified:

DEPTH / 2000

At a current depth of e.g. 650 mm, the expression returns 0 instead of the desired 0.325!
Therefore, the expression must be written as follows:

DEPTH / 2000.0

Or the expression is transformed into a multiplication:

DEPTH * 0.0005

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 6/52

<!-- Page 7 -->

# 3 Interactors

## 3.1 Recommendations for using the 3 abstract symbol sizes

large Interactors for planning groups

medium Actions, referring to top-level objects or elements of planning groups

small Actions, referring to child objects (sub-articles)

## 3.2 Interactor for planning group or group elements?

If a planning group (section 5) is used in the project, certain actions can be triggered both via an interactor
OAP
at the group instance and via interactors at the elements.

A typical example is adding and removing elements. Usually this is allowed only at certain places
(elements) of the layout. The interactors with the corresponding actions could be displayed for
the elements where the action is possible. However, it would also be possible for the group in-
stance itself to place the interactors at the allowed locations (elements).

When making a decision, aspects of user guidance as well as the respective efforts have to be considered and
weighed against each other (if necessary, in consultation with the client). Here are some considerations for
decision-making.
From the user's point of view, interactors bound to group elements are problematic because they are visible
only when the user has selected the element in question. However, the inexperienced user often is not even
aware that he must first select elements in order to be able to perform certain actions. Furthermore, in the
scenario of adding a new element (see above), the user often wants to continue adding to the new element and
must first select it again.
On the other hand, many interactors bound to the group can lead to oversaturation and, when the viewer is
further away, to unsightly overlapping effects. In order to avoid or reduce the oversaturation of the group, a
compromise could be that interactors, which would only be visible/valid for certain elements (see example
above), are bound to the group. In contrast, interactors that are valid for (almost) all elements are bound directly
to them.
Element-related interactors (actions) bound to the group usually imply more effort, since the positions for the
interactor symbols have to be determined based on the position (and rotation) of the respective element within
the group (for which appropriate methods have to be implemented in the project-specific class for the planning
group). Further effort arises if the group instance itself does not have the required functionality (property,
method) to perform the desired action. In this case, methods have to be implemented in the project-specific
class, that use (call up) the corresponding functionality of the concerned element.
In the case of interactors bound the elements, on the other hand, there may be an effort involved in creating the
8
validity condition if the interactor has to be visible only for certain elements . Here, however, often existing

8 This corresponds to the above-mentioned recommendation from the user's point of view to rather bind these interactors
to the group

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 7/52

| large | Interactors for planning groups |
| --- | --- |
| medium | Actions, referring to top-level objects or elements of planning groups |
| small | Actions, referring to child objects (sub-articles) |

<!-- Page 8 -->

standard methods can be used, i.e., the creation of these conditions may not require any project-specific pro-
gramming.
If the decision has been made to perform certain element-related actions via interactors bound to the group, but
the number of possible interactors and the positions of the interactor symbols are difficult to predict/manage,
the use of dynamic interactors can/should be considered.

Tip:
According to the recommendation from the previous section, interactors of the planning group that refer to
individual elements should have a smaller symbol size than the interactors that actually refer to the group as a
whole.

## 3.3 Dynamic interactors

They are realized by implementing the (parameter less) method getDynamicOAPInteractors() in the class of the
relevant article instance (planning group) 9 . The method is called by the application when the instance is selected
and after processing the actions of an activated interactor 10 . The interactors supplied by the method then are
displayed in addition to the currently valid static interactors.

The return value of the method must be of OFML type List, whose elements are of type Vector (each) containing
the following 2 elements:
1. Interactor ID (String)
2. Interactor information (Vector)
The ID for a dynamic interactor can be defined freely, but it must be unique and must not match the ID of a static
interactor!
The Interactor information in the second element contains the following elements:
1. NeedsPlanMode (Int)
2. Action IDs (String[])
3. SymbolType (Symbol)
4. SymbolSize (Symbol)
5. SymbolDisplay information (Vector)
Elements 1-4 correspond to the according fields in OAP table Interactor.

The elements in the SymbolDisplay information (element 5) again are of type Vector each defining a symbol using
the following elements (which correspond to the according fields in table SymbolDisplay):
OAP
1. HiddenMode (Int)
2. Offset (Float[3])
3. Direction axis (Float[3] | Void)
4. ViewAngle (Float | Void)
5. Orientation X (Float[3] | Void)

9 i.e., theoretically also are possible with "normal" articles
10 see also method xOiOAPManager::getInteractors(), section 6.1

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 8/52

<!-- Page 9 -->

Notes:
• Since there is no element for a validity condition, the method must/may supply only those interactors
that are valid at the time the method is called.
• The data for the specified actions has to be provided/contained in the OAP database. For further notes
on this point see below.
• SymbolType and SymbolSize must be specified as a Symbol, whose value corresponds to the identifier
of the desired symbol type resp. the desired symbol size grade according to the specification.
OAP
•
Elements NeedsPlanMode and HiddenMode must not contain expressions, but have to be specified as
0 1
an explicit Boolean value ( or ).
• Float values must be specified explicitly, i.e. no expressions are allowed (and the ID of an entry in the
table NumTripel cannot be used either).
As noted in the 2nd point above, the actions of the dynamic interactor have to be specified in the OAP data. If
an action is semantically identical for all relevant planning elements, placeholder $INTERACTOR can be used.
Otherwise, a separate action would have to be created for each relevant planning element with the appropriate
target object (object category MethodCall) or an appropriate object as argument of a MethodCall action. With
an arbitrary or unknown number of relevant elements this is practically impossible.
The basic idea of using the placeholder $INTERACTOR is to build up the ID of a dynamic interactor defined for a
given element in such a way that the relevant element can be retrieved from it. This can be done, e.g. 11 , by
encoding the local object name of the element within the group into the ID of the interactor. For this purpose
methods localObjName() and localName2Obj() are available in the base class xOiPlGroup for all types of planning
groups, see example.
The example shows the implementation of dynamic interactors in a planning group class derived from
type xOiJointPlGroup), which should allow to change the length of each layout element by means of a PropEdit
action:

oap_object.csv:
OB_self;Self;;;
OB_dynID;MethodCall;AC_call_getElemByDynIID;;

oap_action.csv:
AC_PE_Length;;PropEdit;PE_Length;OB_dynID
AC_call_getElemByDynIID;;MethodCall;MC_getElemByDynIID;OB_self

oap_methodcall.csv:
MC_getElemByDynIID;Instance;::foo::bar::barPlGroup;getElemByDynIID;$INTERACTOR

11 Another possibility would be to encode the index of the element in the list of layout elements into the ID of the interactor.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 9/52

<!-- Page 10 -->

barplgroup.cls:

static var sIA_PE_Length_ID_Prefix = "IA_PE_Length_";
public func getDynamicOAPInteractors()
{
var tRet = @();

var tEl;
foreach(tEl; self.getElOrder()) {
var tIID = sIA_PE_Length_ID_Prefix + self.localObjName(tEl);
var tPos = self.getEditInteractorPos(tEl);
var tDisplayInfo = [0, tPos, NULL, NULL, NULL];
var tData = [tIID, [0, ["AC_PE_Length"], @Edit, @small, [tDisplayInfo]]];
tRet.pushBack(tData);
}

return(tRet);
}
private func getEditInteractorPos(pEl)
{
// position above the element in the middle of x dimension
var tOffset = 0.05;
var tLBB = pEl.getLocalBounds();

var tX = tLBB[0][0] + (tLBB[1][0]-tLBB[0][0])/2;
var tY = tOffset;
var tZ = 0.0;

return(xOiTransformObjCoords(pEl, [tX, tY, tZ], self));
}
public func getElemByDynIID(pIID)
{
var tName = pIID.substr(sIA_PE_Length_ID_Prefix.size());
return(self.localName2Obj(tName));
}

Note:
Currently, object category MethodCall is not permitted for the target object of an action whose ID is used as the
argument of a call to function methodCall() (see [oap]).
Therefore, the object ID OB_dynID defined in the example above cannot be used for target objects of actions
that are used as arguments of methodCall() expressions in conditions!

Assume that in the example above, in addition to the PropEdit action, an ActionChoice action with a selection of
objects to be added is to be applied, where the selection depends on the currently selected group element.
Method canAddObject(pType) of the class of the group element is to be used to determine whether a specific
object from the possible selection list can be added to the selected group element.
The condition for an option in table ActionList would then be formulated as follows:
methodCall("AC_call_canAddObj_<type>")

As object category MethodCall cannot be used for the target object of these actions, the method call must not
be made directly on the group element. Instead, a method (of the same name) of the planning group class must
be called, which in turn calls the method on the relevant group element. In doing so, placeholder $INTERACTOR
and method getElemByDynIID() described above are used:

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 10/52

<!-- Page 11 -->

oap_action.csv:
AC_call_canAddObj_<type>;;MethodCall;MC_canAddObj_<type>;OB_SELF

oap_methodcall.csv:
MC_canAddObj_<type>;Instance;::foo::bar::barPlGroup;canAddObject;$INTERACTOR,<type>

barplgroup.cls:

public func canAddObject(pIID, pType)
{
var tRet = 0;
var tEl = getElemByDynIID(pIID);
if (tEl != NULL)
tRet = tEl.canAddObject(pType);
return tRet;
}

## 3.4 3D interactor symbols

In the case of interactor symbols which illustrate the effective direction of the action associated with the interac-
tor by means of an arrow, the implementation as a 3D symbol should be considered.
Example:
On the right side of an object there is an interactor with symbol type ChangeDim2Right, linked to an action which
increases the width of the object.
A "normal" 2D symbol, which always is displayed parallel to the screen plane, would always point to the right.
This would illustrate the correct direction of the action to the user (in the case of a non-rotated object) only when
viewed from front or from above.
Since for 3D symbols the plane has to be specified in which the (flat) symbol icon is to be located for 3D, one has
to decide on a view that is most suitable to deal with the object:
• For objects with a low height, the top view is usually the most suitable, i.e., the symbol icon then has to
lie in the X-Z plane of the object.
• In the case of objects with a shallow depth, the front or rear view is usually the most suitable, i.e., the
symbol icon then has to lie in the X-Y plane of the object.

A 3D symbol intended for the top view would be defined as follows 12 :

oap_numtripel.csv:
NT_RightSide;LENGTH * 0.001;0.0;0.0
NT_POS_X_AXIS; 1.0; 0.0;0.0
NT_POS_Y_AXIS; 0.0; 1.0;0.0
NT_NEG_Y_AXIS; 0.0;-1.0;0.0

oap_symboldisplay.csv
IA_RESIZE;0;Tripel;NT_RightSide;NT_POS_Y_AXIS;360;NT_POS_X_AXIS

12 see also figure 2 in section 4.6 of the OAP specification

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 11/52

<!-- Page 12 -->

Explanation:
The direction vector of the visibility range ( , field 5) runs along the positive Y axis (top view).
NT_RightSide
Thus, the 3D symbol lies in the X-Z plane of the object and, due to the entry in field 7, always is oriented along
the positive X axis of the local coordinate system of the object.

Notes on the opening angle in field 6
Without specifying an opening angle (empty field 6), no visibility area is defined, which means that the possibly
existing entry in field 5 does not take effect for the direction vector. The result would be a normal 2D symbol! If
the visibility range actually is not to be restricted, an opening angle of 360 degrees must be specified, as in the
example above. However, since the 3D symbol is becoming "flatter" and therefore less recognizable the closer
the viewing angle approaches the X-Z plane of the object, a restriction of the visibility range is recommended for
3D symbols, e.g.:

IA_RESIZE;0;Tripel;NT_RightSide;NT_POS_Y_AXIS;150;NT_POS_X_AXIS
IA_RESIZE;0;Tripel;NT_RightSide;NT_NEG_Y_AXIS;150;NT_POS_X_AXIS

Then, the interactor would have 2 symbols with mutually exclusive visibility ranges, which would not be visible
at a viewing angle of less than 15 degrees to the X-Z plane of the object. (The second entry can be omitted if the
interactor should be visible only when the user looks at the object from above.)

Analogous, a 3D symbol intended for the front and rear view (in the example with symbol type ChangeDim2Right)
would be defined as follows:

oap_numtripel.csv:
NT_RightSide;LENGTH * 0.001;0.0;0.0
NT_POS_X_AXIS; 1.0; 0.0; 0.0
NT_POS_Z_AXIS; 0.0; 0.0; 1.0
NT_NEG_Z_AXIS; 0.0; 0.0;-1.0

oap_symboldisplay.csv
IA_RESIZE;0;Tripel;NT_RightSide;NT_POS_Z_AXIS;150;NT_POS_X_AXIS
IA_RESIZE;0;Tripel;NT_RightSide;NT_NEG_Z_AXIS;150;NT_POS_X_AXIS

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 12/52

<!-- Page 13 -->

## 3.5 Correct configuration context?

The validity condition in OAP table Interactor can resp. must be used to ensure that the interactor is only dis-
played if the current configuration context allows it.
A common requirement is that an interactor should only be displayed if the article in question is a sub-article of
a composite article, i.e., if it is not at the top planning level. This applies, for example, to the following cases:
• An Add interactor for attaching a neighbor element in the context of a planning group.
(see also section 3.2)
• All Delete interactors!
(see also section 4.4)
A typical resp. recommended solution for this requirement is described in section 2.3.

Furthermore, it must be considered that some applications have the function "Split up article" 13 , during the ex-
ecution of which a composite article is split up into its components, i.e., individual articles at top planning level.
If the composite article is the special case of a Meta type instance, it will no longer exist after executing the
function "Split up article"!
One consequence of this is that meta properties can no longer be accessed after splitting up. Accordingly, in-
teractors with PropEdit or PropChange actions that use meta properties then must no longer be displayed! If an
OAP type exclusively has such interactors, this can be achieved in a simple way by assigning the OAP type (ex-
clusively) to one (or more) meta types (ID) via mapping table Metatype2Type 14 .

13 or similar, e.g., "Break up article"
14 i.e., there should/must not be an assignment to articles (mapping table Article2Type)

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 13/52

<!-- Page 14 -->

# 4 Actions

## 4.1 Creating articles via xOiCreateArticle() resp. xOiCloneArticle()

Actions of type CreateObj are used to add articles to the configuration as required by the user. If further pro-
cessing is required before and/or after article creation, it may be advisable to program all this in a method (and
call it via an action of type MethodCall). The global functions xOiCreateArticle() resp. xOiCreateArticle2() 15
can/should be used for article creation 16 .
In default mode @extended , the functions simulate the standard process of article creation in the applications
of EasternGraphics , where the so-called checkAdd() mechanism 17 is used to determine position and rotation of
the new article instance (including the creation of a temporary article instance).
If position and rotation of the new article instance are defined during the programmed article creation itself, the
functions should be used in mode @lite , as this offers a better performance. Then, after calling the function
position and rotation have to be assigned to the article instance returned by the function 18 .
As of the application releases in fall 2024, a third mode @att_pts is supported, which expands mode @lite :
Position and rotation of the new article instance are determined using the OFML interface AttachPts 19 . This mode
can be used to avoid a problem related to collision detection, which is covered in section 5.14.
Global function xOiCloneArticle() can be used to realize the attachment of an exact and deep copy 20 of the active
object to it (via an interactor with symbol type Duplicate 21 ).
The mentioned functions are described in detail in appendix A.
Like actions of type CreateObj, functions xOiCreateArticle() and xOiCreateArticle2() require the specification of a
parent article (father object) and, thus, are not suitable for insertion at the top planning level.

## 4.2 Change direction in DimChange actions

As of OAP 1.2, in field Dimension in table DimChange can be specified in which axis direction a change is permit-
ted. Previously, only a change in the positive direction of the respective dimension axis was possible (imple-
mented). To ensure downward compatibility, for OAP data that is created in accordance with an older OAP
X, Y Z PX, PY PZ
version, values and are treated in the same way as or in accordance with OAP 1.2.
With dimensions X and Z, in most cases it makes sense to allow a change in both directions (i.e., to specify values
X resp. Z as of OAP 1.2) in order to offer the user an optimal change behavior regardless of the rotation of the
object or the camera perspective. If necessary, existing data should be ported to OAP 1.2 22 .

15 as of the application releases in fall 2023
16 These functions are contained in the base library .
OFML XOI
17 see OFML interface Complex (section 4.5.2) in [ofml]
18 using methods of interface Base, see section 4.2.9 in [ofml]
OFML
19 This assumes that both the classes of the reference object and those of the added object implement the interface AttachPts.
20 incl. property values and possible sub-articles
21 as of the application releases in fall 2024
22 considering new fields Separate and ThirdDim in table DimChange

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 14/52

<!-- Page 15 -->

## 4.3 Nesting of method calls

Since the arguments for a method call (table MethodCall) can be specified as expressions, it is possible to realize
nested method calls by means of the expression methodCall().

Example:
MC_METHOD_1;Instance;::foo::bar::aClass;method_1;methodCall("AC_call_METHOD_2")

## 4.4 Notes on DeleteObj

Of the currently supported object categories, only Self and MethodCall can be used for the target object of a
DeleteObj action 23 .
MethodCall is useful in the context of interactors, which are bound to planning groups (see section 5). Then the
method call can be used to determine the element of the planning group that is to be removed.
When using Self, after the DeleteObj action no further actions may follow, which again need a target object or
an object definition as a parameter, because after the action the original active object no longer exists!
(This applies not only to DeleteObj actions, but generally to all actions that lead to the removal of the active
object.)
This is problematic if, after removing the object, further actions have to be executed that perform certain checks
and, if necessary, subsequent treatments 24 . Such a task typically exists in the context of planning groups. If, after
all, the DeleteObj action cannot be executed in the context of an interactor bound to the planning group 25 , there
is no alternative but to replace the DeleteObj action with a MethodCall action for the planning group instance
(object category ParentArticle) that deletes the element and performs the subsequent examinations and treat-
ments. The element to be deleted is passed in a parameter using the placeholder $SELF :

public func delElem(pObj)
{
self.remove(pObj);
// do further checks and act accordingly
...
}

Note:
If the checks to be performed relate to the neighborhood relationships of the layout elements of the planning
group, an OAP data creator might think of calling certain methods for manipulating the internal layout structure
of the planning group instance prior to the DeleteObj action in order to obtain desired results in the neighborship
tests (exclusion of the element to be deleted). However, this is error-prone, since this requires exact knowledge
of the processes in the base classes. Since a method for performing the checks has to be created in the (derived)
class of the planning group anyway, it then can/should better be extended as described above.

23 ParentArticle and TopArticle are not possible because the active object cannot delete a superior article instance.
24 and these actions cannot be performed before the DeleteObj action
25 and, then, object category MethodCall is used to determine the element to be removed

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 15/52

<!-- Page 16 -->

## 4.5 RG properties

OFML properties generated for OCD properties with scope RG can only be changed using actions of
1
types PropChange and PropEdit if value is specified for option @NeedValuesForRGProps in control data table
epdfproductdb 26 .
Caution:
An assignment of a value to an RG property made possible via @NeedValuesForRGProps should not lead to a
value change of a configurable property that follows the RG property in the list of properties (due to dependen-
cies in OCD product relationships)! Otherwise, problems ("freezing") can occur when the article instance is re-
created (e.g., as part of an update) 27 .

## 4.6 Action type NoAction

An interactor is not displayed if it currently has no valid action. This may be a handicap in an early phase of project
development, when, initially, only the interactor symbols are to be created and positioned. In this case, special
dummy action type NoAction can be used, which does not require any further data to be specified.

Example:
AC_DUMMY;;NoAction;;

26
With this, the value choice list of the generated property contains all the values that are stored for the RG property in the
OCD value table. Without the option (or with value 0 ) the value list contains only the current value, so the property is practi-
cally read-only.
27 as RG properties are not encoded in the variant code

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 16/52

<!-- Page 17 -->

# 5 Planning groups

The explanations in this section refer to the classes from the OFML base library XOI used in OAP projects to
28
implement planning groups .
Useful methods of these classes that can be used directly in OAP via MethodCall actions are described in the
document [methods]. This document also contains a brief introduction to the purpose and application of the
planning classes.
Control data tables customplgroup , jointplgroup , layoutgroup resp. tabularplgroup can be used to
control some aspects of the behavior of planning groups. The possible options are described in Application Note
AN-2006-01 [an0601].
Note on the use of xOiJointPlGroup vs. xOiLayoutGroup:
29
In principle, a pure left-right-oriented joint planning can be realized by means of xOiLayoutGroup . However, in
most cases the use of xOiJointPlGroup is the more "light weight" solution for such planning groups and thus
preferable. Certain requirements, which go beyond a pure left-right-oriented joint planning, within limits also
can be implemented based on xOiJointPlGroup, see sections 5.6 and 5.7.

## 5.1 Using object category MethodCall

In particular, in connection with planning group classes, there are some useful applications for object category
MethodCall. A common scenario is, for example, that a certain property has to be set on a group element created
via a CreateObj action. In this case, the target object for the according PropChange action cannot be determined
by means of object category Self (since this refers to the object to which the interactor is bound whose actions
currently are being executed). However, if the group element has been added to the last layout element of the
group, in the case of class xOiJointPlGroup, e.g., method lastObj() can be used for that purpose. In the classes
xOiLayoutGroup and xOiCustomPlGroup there are equivalent methods 30 .

For the example above, the PropChange action could be implemented as follows:

oap_object.csv:
OB_PARENT;ParentArticle;;;
OB_LAST_GROUP_OBJ;MethodCall;AC_call_LAST_OBJ;;

oap_action.csv:
AC_PC_CHANGE_A_PROPERTY;;PropChange;PC_CHANGE_A_PROPERTY;OB_LAST_GROUP_OBJ
...
AC_call_LAST_OBJ;;MethodCall;MC_LAST_OBJ;OB_PARENT

oap_methodcall.csv:
MC_LAST_OBJ;Instance;::ofml::xoi::xOiJointPlGroup;lastObj;

28 These are currently the classes xOiCustomPlGroup, xOiJointPlGroup, xOiLayoutGroup and xOiTabularPlGroup. They are
described in detail in the XOI documentation [xoi] in section "Planning Groups".
29 In this case, the group would consist of only a single branch.
30 see document [methods]

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 17/52

<!-- Page 18 -->

Note:
A method that is used in object category MethodCall has to return an instance that represents an article 31 . This
requirement may not be met for special auxiliary objects within planning groups. Then, the solution is not to
execute the action directly on this auxiliary object, but to call a method on the group instance (action type
32
MethodCall), passing the auxiliary object as an argument to this method by means of a methodCall() expression
(see section 4.3).

## 5.2 Changing dimensions of group elements

5.2.1 General

Classes xOiCustomPlGroup, xOiJointPlGroup and xOiLayoutGroup support the modification of the dimension
(width/depth) of topological 33 elements of the planning group: connected elements (to the right side 34 ) are
moved away resp. closer (to re-connect).
For that, the so-called InsertMode 35 has to be set to 1 (or greater) 36 .
This is done via an entry
@InsertMode;;1
in the corresponding control data table.

Furthermore, in the article classes of the planning group elements, the handling of a dimension change by the
planning group has to be triggered by calling method dimensionChanged() on the planning group instance 37 .
Typically, a dimension change occurs when the value for certain properties is changed. Accordingly, these prop-
erties have to be handled separately in the method propsChanged() [property].
In the case of an article class derived from GoMetaType, assuming that a change of property @WidthProp results
in a change in width, a prototypical implementation of this method using the planning group class
xOiJointPlGroup would look like this:

31
The technical background for this restriction is that the clients of online apps perform some actions themselves (i.e., do not
delegate them to the server), but in turn only "know" articles (no OFML instances).
32
The same MethodCall action is used here that would also be used for object category MethodCall.
33 elements, defining the layout of the group
34
In the case of xOiLayoutGroup and xOiCustomPlGroup, the side of the changed element to be adjusted is defined by a
parameter of method dimensionChanged().
35
defined in the base class xOiPlGroup
36 For xOiCustomPlGroup, this requires (default) value 1 for option @StoreNeighborship.
37 For details (parameters) see [xoi]. In case of xOiJointPlGroup method dimensionChanged() is implemented and documented
In base class xOiLRPlGroup.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 18/52

<!-- Page 19 -->

public func propsChanged(pProps, pCheck)
{
var tRet = GoMetaType::propsChanged(pProps, pCheck);

if (!tRet) return (tRet);
// Do nothing during meta type initialization!
// (This would cause syntax errors due to the lack of some properties.)
// Skip this, if the class is not derived from GoMetaType!
if (!isMetaInitialized() || sInSetAddStateCode)
return tRet;
var tFather = self.getFather();

if (pCheck && tFather.isA(xOiJointPlGroup) &&
pProps.find(@WidthProp) >= 0 &&
!tFather.dimensionChanged(self))
tRet = 0;

return(tRet);
}
For Meta properties that raise a native property of the encapsulated article instance to the level of the Meta
type instance (so-called na-properties), this does not work because a change of such a Meta property is delegated
from the Meta type instance to the encapsulated article instance. Thus, in this case, method propsChanged()
would have to be overwritten accordingly in the class of the encapsulated article instance. Since in standard
OFML data creation normally the standard type OiOdbPlElement is used, it would therefore be necessary to
derive a specific class from it and assign it to the corresponding articles in the OAM data. Section 5.3 describes
a different approach that allows to avoid overwriting propsChanged() in the class of the encapsulated article
instance by means of an extended Meta data creation.

5.2.2 Considering changes in the bounding volume

The algorithm for handling a dimension change is based – amongst others – on a comparison of current and
stored minimum axis-orthogonal bounding volume of the changed element relative to its local coordinate sys-
tem 38 . The bounding volume is stored by the planning group instance after an element has been inserted and
whenever the above-mentioned methods are called. If a change of the bounding volume takes place without
calling any of the methods mentioned above, this will lead to incorrect handling in subsequent calls of the meth-
ods, because the planning group instance has not noticed anything about the interim change of the bounding
volume!

This has to be considered in situations where the bounding volume changes, but the actual dimension of the
element does not change and, thus, actually no neighbors need to be moved. An example would be creating a
frame foot as a child of a table placed midway under the left neighbor table and the modified table. In order to
avoid the problem above, the methods for handling a dimension change should be called anyway, even if this
means a small overhead. However, if such a change takes place exclusively during the insertion of an element
into the planning group, the call can be omitted. (In the example above, this would be the case, if the foot is
generated in the course of the execution of the actions of an Add interactor by means of a PropChange action
that is executed after a CreateObj action that actually performs the element's creation.) But then, the planning
group instance has to be assisted by other method calls, where different methods must be used for the two
above-mentioned classes:

38 according to method getLocalGeoBounds() of OFML interface Base [ofml]

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 19/52

<!-- Page 20 -->

• xOiJointPlGroup:
39
Call of elementCreated() after the relevant PropChange action
• xOiCustomPlGroup and xOiLayoutGroup:
Call of delayHandleNewElement() before the CreateObj action and handleNewElement2() after the rel-
evant PropChange action
For details on these methods, see XOI documentation [xoi].
While methods elementCreated() and delayHandleNewElement() have a simple signature and thus can be inte-
grated directly without special programming by means of a MethodCall action 40 , in the case of
handleNewElement2() the encapsulation by a specially programmed method probably is the preferred way.

5.2.3 Notes on the algorithm in xOiJointPlGroup

In cases were the origin of the local coordinate system (also) has changed, method dimensionChanged(), when
indicated, also performs a re-positioning of the changed element before (possible) re-positioning of relevant
neighbor elements. An example would be attaching a mounting plate on the left side of a table. Re-positioning
of the changed element is also performed if the coordinates of the relevant attach point change accordingly.
In the example with the left mounting plate, therefore, it is assumed that the attach point on the left side of the
modified table “migrates” to the left in accordance with the width of the mounting plate.
Another scenario would be the example already mentioned above (in section 5.2.2) of creating a frame foot
centered below two adjacent tables. If dimensionChanged() is called in this case 41 , the coordinates of the attach
point on the left side of the table to which the foot is added must not change. Otherwise, there would be an
undesirable shift of the changed table!
The re-positioning of the changed element ideally takes place on the basis of the attach point that was used
when the changed element was attached to (the right of) its left neighbor. In the case where the left neighbor
of the changed element was added to (the left of) the changed element, this attach point is not known (with the
standard implementation in xOiJointPlGroup/xOiLRPlGroup). As a fallback, the changed element then is trans-
lated by the amount of the change in the local origin.
Especially with angled or curved elements, the latter can lead to an undesired repositioning of the changed ele-
ment if dimensionChanged() is called as a result of a change in the orientation of the element (in order to accom-
plish the repositioning of the neighboring elements). This can be prevented by delivering the relevant attach
42
point via overwriting method getUsedAttPt() . In the ideal case, where the elements of the planning group are
attached to each other with the help of an attach point each on the left and right side and these attach points
are named the same for all elements, the overwritten implementation would look something like this:

39 inherited from base class xOiLRPlGroup
40 In the case of elementCreated(), the argument itself also is determined by calling a method (lastObj()) via function
methodCall(), see section 4.3.
41 see alternative, described in section 5.2.2
42 The method is defined and documented in the base class xOiLRPlGroup.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 20/52

<!-- Page 21 -->

protected func getUsedAttPt(pRefObj, pNeighbor)
{
var tRet = xOiJointPlGroup::getUsedAttPt(pRefObj, pNeighbor);
if (tRet == NULL) {
if (pNeighbor == self.neighbor(pRefObj, @R))
tRet = @AP_R;
else
if (pNeighbor == self.neighbor(pRefObj, @L))
tRet = @AP_L;
}
return(tRet);
}

## 5.3 Dimension change based on na-Metaproperties

This section describes a Meta data approach that can be used to avoid overwriting method propsChanged() in
the class of the encapsulated article instance, as described in section 5.2.1, in the case of a dimension change
that is based on a change to a na-Metaproperty.
Suppose there is a na-Metaproperty GWidth , which specifies the width of the article in centimeters:
1.
In table go_types, create an invisible utility property of type (format) "ch" controlling sub-items (mode 24):
MT_SE_Name;GWidth;na;60;1;
MT_SE_Name;GWidth2;ch;_60;24;

2.
The implementation of propsChanged() in the class of the Meta type instance (see section 5.2) uses property key
@GWidth2 (instead of @GWidth ).

3.
In table go_childprops, specify a parameter set for the possible values of the utility property:
CHP_SE_GWidth2;GWidth2;_60;
CHP_SE_GWidth2;GWidth2;_70;
...

(Before, the parameter set, here CHP_SE_GWidth2, was assigned to the articles of Meta type in
MT_SE_Name
table go_articles. Alternatively, an already assigned parameter set can be used.)
Tip:
It is enough to specify just one value (e.g. the start value). This is particularly helpful when there are many
possible values.

4.
In file go_context.ofml , implement a function converting a value of property @GWidth into a value of property
@GWidth2 :

func gwidth2gwidth2(pVal)
{
return(Symbol("_"+String(pVal)));
}

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 21/52

<!-- Page 22 -->

5.
In table go_actions, add an according action:

MT_SE_Name;GWidth;;CON;;SET_PROP;GWidth2;gwidth2gwidth2(GWidth);

## 5.4 Group-specific entries in the control data table

If several group classes derived from an XOI base class exist in a series and different specifications have to be
made for these in the respective control data table, the second field (argument) of the table entries can be
used for differentiation, provided that (different) articles have been created for the different planning group
types.

Example:
@StartElement;[@Article,["SINGLE_WP"]];[@foo_bar,"ARTICLE1",@VarCode,"",[]]
@StartElement;[@Article,["DOUBLE_WP"]];[@foo_bar,"ARTICLE2",@VarCode,"",[]]

Details see Application Note AN-2006-01.

## 5.5 Changing articles via replaceElement()

Edit interactors are often used to change the article of the object. Ideally, a corresponding property is directly
addressed by means of a PropEdit action. Sometimes, however, there is no suitable property available. In this
case, one can use method replaceElement() implemented in the classes xOiJointPlGroup and xOiLayoutGroup
resp. method replaceField() in class xOiTabularPlGroup, calling it by means of a MethodCall action.
For details about using these methods see document [methods].
Notes:
• If the interactor is bound to a group element (not to the planning group instance), after the MethodCall
action with the call of replaceElement() no further actions may follow, which again need a target object
or an object definition as a parameter, because after the action the original active object no longer
exists! (See also notes on DeleteObj in section 4.4.)
•
The implementation of xOiLayoutGroup::replaceElement() currently does not work if a neighbor of the
element to be replaced belongs to a different branch.

## 5.6 Non-Layout articles with xOiJointPlGroup

Occasionally elements have to be inserted in an instance of xOiJointPlGroup (or any derived class) that are not
part of the topological list, e.g. frames, service tables etc.
Regarding such elements a few hints:
• For elements of the planning group that should not be part of the topological list 43 , hook method
isValidForLRPlanning() 44 has to return value 0. Accordingly, this method has to be overwritten specific
to the project.
It should be noted that this method is called immediately after element creation, i.e. at a time when the
article is not initialized yet. As a consequence, the article number or properties of the instance cannot

43 This corresponds roughly to the distinction between layout elements and other elements in xOiLayoutGroup.
44 This method is defined in base class xOiLRPlGroup.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 22/52

<!-- Page 23 -->

be used in the method to decide whether or not the given element should be part of the topological list.
All that remains is the ability to test for a type using isA() or for a category using isCat() 45 .
1
• If these elements are to be treated as sub-articles, value has to be specified for option
@AllElements4SubArticle in control data table jointplgroup .
• If these elements are placed by means of attach points, by calling method xOiJointPlGroup::isBusyAttPt()
in validity conditions of interactors it is possible to determine whether an element from the topological
list has a neighbor element at the relevant attach point 46 .
(For details about using this method see document [methods].)

• When changing the dimensions of elements from the topological list (see section 5.2), elements that are
not contained in this list are not moved! Therefore, these elements either have to be re-created or class
xOiLayoutGroup has to be used.

## 5.7 Additional start elements

Typically, options @StartElement or @StartLayout in the control data tables are used to initially create one or
several start (layout) elements. Occasionally, it may be necessary to initially create also some non-layout ele-
ments.
Because this initialization occurs when an article number is assigned to the planning group instance during
method setArticleSpec(), this method has to be overridden accordingly in derived classes in order to create addi-
tional start elements. In the overridden method, first the inherited implementation has to be called. After that
global function xOiCreateArticle() (see section 4.1) can be used to create further r elements. If required, the
reference objects for the additional elements to be created can be determined using the methods for accessing
the topological list (xOiJointPlGroup 47 ) resp. for accessing the layout structure (xOiLayoutGroup and
xOiCustomPlGroup).

Pay attention also to the notes in section 5.10.3 and, in the case of a class derived from xOiJointPlGroup, the
notes in previous section on creating elements that should not be part of the topological list!

## 5.8 Removability of group elements

Since the removal of an element from a planning group often is accompanied by further actions (see section 4.4),
usually they should be able to be removed only via OAP interactors (symbol type Delete), but not via the Delete
command of the application. Previously, this explicitly had to be done by directly or indirectly calling the method
setCutable() ( OFML interface Base [ofml]) with the value -1 . This is no longer necessary: The desired state can
be specified for all planning group classes, separately for layout elements and other elements (see 4.7), in the
respective control data table using options @CutableState4Layout and @CutableState4Other.

45 If for some reason this is not possible or not sufficient, class xOiLayoutGroup has to be used.
46 The methods for determining neighbor elements in the topological list do not work here.
47 via base class xOiLRPlGroup

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 23/52

<!-- Page 24 -->

## 5.9 Common properties / Group properties

With all group types, option @CommonProps in the respective control data table can be used to specify the
properties of the elements, which can be edited together at the level of the planning group. Then, a change at
group level is delegated to all group elements that own the changed property.
There are a number of accompanying options that affect the processing of common properties. These are de-
scribed in section 6.1 of Application Note AN-2006-01 [an0601]. Some of these are also discussed in the following
(sub) sections.
Beyond that – if necessary, in addition to the properties generated via @CommonProps – in derived, project-
specific classes group properties also can be programmed using OFML interface Property [property], see section
5.9.4.

5.9.1 Creation and update of common properties

For which of the properties, specified in option @CommonProps, a group property is actually created depends
on the group elements used for generating the group properties and on their current configuration. This can be
controlled or influenced by the following options:
@AllObjs4CommonProps
@NonLayout4CommonProps,
@Meta4CommonProps
@CommonPropsDepth
@NonVisibleProps4Common
@ROPropsEditable4Common

The initial creation of the common properties is done during the initialization of the group instance after the
creation of the initial layout elements 48 .

An automatic update (re-creation) takes place in case of the following events:

1. When a common property is changed and this has affected at least one group element 49 .
This reacts to possible dependencies between the common properties.
2. When opening resp. updating the property editor for an OFML instance – via method updateProperties()
of OFML interface Property 50 – if the language to be used for product data of the series has changed
since the last opening resp. updated. This reacts to a changed language setting on the part of the user.
As of XOI 1.60 (with the releases in fall 2023), the update is generally also performed during the first call
of updateProperties() after calling setAddStateCode() 51 . This reacts to possible changes in the product
data, e.g., changed choice lists in the relevant properties

48 usually in method setArticleSpec()
49 via method fixPropsChanged()
50 In the overridden implementation in base class xOiPlGroup
51 in the course of restoring an article instance on the basis of a saved basket representation

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 24/52

<!-- Page 25 -->

3. If option @AllObjs4CommonProps has value 1 :
When creating a group element using a CreateObj action or using global function xOiCreateArticle() in
52
@extended mode (see section 4.1) and when removing a group element .
This covers properties that are relevant only for the new element or the element to be deleted.

In certain situations that are not covered by the standard events mentioned above, the update must be triggered
from the OFML resp. OAP data. For this purpose, method updateCommonProperties() is implemented in the
XOI classes for all group types (see document [methods]). Typical use cases are:
• A property has been changed that affects the visibility or the state of common properties, where the
changed property itself is not included in the set of common properties.
• A group element is created or removed 53 that has properties listed in the common properties, but the
creation or removal is not covered by the standard situation 3 described above.
The method can and should be called directly in the data by means of a corresponding MethodCall action
OAP
after the relevant actions. (Thus, no special programming is required for this.) However, if an element is removed
by an action triggered by an interactor of the element itself, this is not possible (see section 4.4). In this case,
consider using an interactor of the parent article to remove the element.

5.9.2 Common properties for a new element

When a new element is inserted into the group the element gets the configuration defined by the respective
action (as long as there is no Metadata-driven inheritance of property values). This configuration can differ from
the current settings of the common properties of the planning group. If the current settings of the common
54
properties of the planning group are to be adopted for the new element, method assignCommonPropValues()
has to be called on the planning group instance in an additional action after the action that creates the element.
(Whether actually the current settings of the common properties are to be adopted for the new element, or
rather a Metadata-controlled inheritance of property values of the reference object has to be carried out, is to
55
be determined on a project-specific or situation-specific basis .)
Method assignCommonPropValues() expects as an argument the element to which the procedure is to be ap-
plied. In the considered scenario this is the element which was created by means of the CreateObj action. The
best way to specify this element is to apply object category MethodCall, using the appropriate methods to access
the neighbor element of the reference object defined by the CreateObj action (see also section 5.1).
For example, if the CreateObj action is executed in the context of an Add interactor bound to the selected group
element (active object), and if the active object also is the reference object of the CreateObj action, methods
neighbor() (xOiJointPlGroup) resp. getNeighbor() (xOiLayoutGroup and xOiCustomPlGroup) could be used, where
in the first argument the active object is passed by means of placeholder $SELF , and the second argument spec-
ifies the attach direction (xOiJointPlGroup) resp. the attach point used in the CreateObj action (xOiLayoutGroup
and xOiCustomPlGroup).

52 via events of types @ArticleInserted resp. @ElementRemoval
53 e.g., as a result of a property change
54 The method is equally defined and implemented in all classes. It is described in the document [methods] (as well as the
both methods mentioned below).
55 Property values of the reference object can deviate from the common properties if the properties of the reference object
were changed again after the last change of the common properties.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 25/52

<!-- Page 26 -->

5.9.3 Property groups

By default, when generating the common properties (option @CommonProps), the property classes are not
adopted from the elements and no specific class is assigned either. Thus, in the property editor, the generated
common properties appear in the standard group, i.e., “Article” or “Other”, if additional programmed properties
(see next sub section) are assigned to their own class.
In most projects this behavior is sufficient. However, in the following situations, a class assignment for the gen-
erated common properties can be useful or even necessary:
1. With a large number of common properties, classes/groups can be used to increase the clarity for the
user.
2. If the common properties are drawn from different object types and these each have disjoint sets of
relevant properties:
56
a. it makes sense to make this visible to the user as well
b. separate property groups are necessary if (different) properties of the different object types
57
have the same language-specific name

1
In the simplest case, the class assignment for the generated common properties is done by setting value for
58
option @Classes4CommonProps . Currently, the classes are adopted from the group elements for all generated
common properties. If this is not desired, or if specific classes are to be assigned in connection with additional
programmed properties (see next sub section), this must be done in derived classes using method setPropClass()
of OFML interface Property [property].
In both cases, language-specific text resources (.sr files) that correspond to the names of the property classes
also should or must be created in the series of the planning group article.

5.9.4 Programmed group properties

In many projects, users should be able to control some general planning features of the group, e.g. the maximum
permitted dimensions. For this purpose, corresponding properties have to be programmed in the project-specific
derived group class. Usually this is done in addition to the automatically generated common properties (option
@CommonProps).
Occasionally, properties also have to be programmed in the project-specific class because the properties of the
group elements do not provide enough functionality or they cannot be adopted one-to-one for the group 59 .
Here are some hints and tips for programming group properties:

1. Since the list of keys of the programmed properties is needed in several places of the implementation
of the group class, it is recommended to define a corresponding static class variable, e.g.:
static var sMyPropKeys = @(@Foo, @Bar);

2. As already described in Application Note AN-2006-01 for option @CommonProps, also the programmed
properties should be specified in table non_pd_properties for better performance.

56 It is then easier for the user to see resp. understand that the change of a property from a given property group only affects
certain elements of the planning group.
57 and, thus, cannot be distinguished by the users
58 The prerequisite for this is, of course, that suitable property classes are assigned in the OFML data of the group elements.
59 This is often the case when the OAP project is built on top of existing OFML data. In projects where the OFML data and the
OAP data are built together, care should be taken from the outset that the properties of the group elements are created in
the OFML data already in such a way that specific programming of properties in the group class is avoided

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 26/52

<!-- Page 27 -->

3. Base class xOiPlGroup for all planning group types implements some standard handlings (e.g. regarding
persistence) for the properties of a group instance, the keys of which are supplied by hook method
getFixProperties(). Thus, as a rule, this method should be overridden in the project-specific group class
and supply the keys of the programmed properties, if necessary, in addition to the keys of the generated
common properties supplied by the inherited implementation.
Example see section 5.10.1.

4. If the programmed properties are created in addition to the automatically generated common proper-
ties (@CommonProps), it must be decided whether the programmed properties should be displayed in
the property editor before or after the generated common properties. By default, the generated com-
60
mon properties are created in the property list starting from position 1 .
• If the programmed properties are to follow afterwards, they must be assigned a correspondingly
high position number.
• In the other case, option @FirstPos4CommonProps has to be used to specify a position number
high enough for the first generated common property.
However, with the help of option @CommonPropsPos 61 , a mixed order can also be realized!

5. The initial definition of the programmed properties is done in the overridden method setArticleSpec()
after calling the inherited implementation and, if necessary, after generating additional start elements
(see section 5.7).

public func setArticleSpec(pSpec)
{
<BaseClass>::setArticleSpec(pSpec);
initMyProps();
}

To avoid overhead (performance) and side effects, the initial values are not assigned using
setPropValue(), but by setting the value in the table of dynamic properties (method getDynamicProps()
from OFML interface Base [ofml]) or by calling the corresponding set methods.

6. The handling of a change of a programmed property by the user is done in the overridden
method fixPropsChanged(), if necessary, after calling the inherited implementation, which performs the
standard handling for generated common properties (see also section 5.9.1):
protected func fixPropsChanged(pProps, pDoChecks)
{
var tRet = <BaseClass>::fixPropsChanged(pProps, pDoChecks);

var tP;
foreach(tP; pProps) {
if (sMyPropKeys.find(tP) < 0) continue; // not my cup of tea

// handle change of my property tP
...
}
return(tRet);
}

60 in the order according to option @CommonProps
61 As of XOI 1.60 (fall 2023)

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 27/52

<!-- Page 28 -->

7. If the user changes the language setting in the application at runtime and the group instance is selected
at this point (open property editor), the language-specific names of the programmed properties includ-
ing their values and classes have to be changed 62 .
This is done by overriding method updateOtherFixProperties2() 63 . This hook method is called by the
standard implementation of method updateProperties() in base class xOiPlGroup if the language to be
used for the product data of the series has changed since the last call (see also section 5.9.1, point 2).
At this time, the names for the generated common properties have already been changed by the base
64
class. So, these do not have to be handled in updateOtherFixProperties2() .
If the programmed properties are created using method setupProperty2() of the Property interface, a
call of setPropName() and, if necessary, a call of setPropChoiceList() (if no text resources are used for
the values) is sufficient to adapt the texts.
8. If the choice lists and, if necessary, other attributes of properties of group elements are used in the
definition of programmed properties, it is necessary to react to possible changes in the product data.
65
This is also done by overwriting method updateOtherFixProperties2() . This hook method is called, in
addition to the situations described in point 7, by the standard implementation of updateProperties() in
base class xOiPlGroup, if it is the first call after the call of setAddStateCode() (see also point 2 in section
66
5.9.1). At this time the common properties have already been re-created by the base class .
In contrast to the situation from point 7 - method updateOtherFixProperties2() has parameters, by which
the triggering situation can be recognized - here the simplest and safest solution probably is to com-
pletely redefine the concerned programmed properties.

## 5.10 Persistency

The XOI planning group classes store all the information that is necessary to reconfigure the planning group.
Essentially, this is done in the methods getAddStateCode() and setAddStateCode() of the OFML interface Article
[article]. When implementing derived classes, the following aspects must be taken into account so that the in-
herited behavior continues to function or to avoid overwriting the two mentioned methods.

5.10.1 Properties

If own properties are programmed in the derived class, the keys of these properties must be supplied via over-
ridden method getFixProperties(). If these properties are defined in addition to the properties that are generated
by the base class according to option @CommonProps, this must be taken into account accordingly:

protected func getFixProperties()
{
var tMyProps = @(@Foo, @Bar);
var tRet = xOiCopyAggr(<BaseClass>::getFixProperties(), NULL, 0);
xOiCopyAggr(tMyProps, tRet, 0);
return(tRet);
}

62 This also applies if a saved group instance will be opened for reconfiguration and a different language is set in the applica-
tion than at the time of saving.
63 As of XOI 1.60 (fall 2023). Before that, hook method the updateOtherFixProperties() was used. This is still supported due to
backward compatibility, but is considered obsolete.
64 Hence the "Other" in the method name.
65 As of XOI 1.60 (fall 2023)
66 So, these do not have to be handled in updateOtherFixProperties2().

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 28/52

<!-- Page 29 -->

5.10.2 Member variables

If information is stored in member variables that is required for a re-configuration, and if this information cannot
be restored in any other way, the values of these member variables have to be encoded in the so-called
AddStateCode (getAddStateCode()), and parsed from the AddStateCode and assigned again during restoration
(setAddStateCode()).
To avoid the rather complex overwriting of the two methods, all XOI planning group classes offer a mechanism
that is based on method getAddStateMembers(): For all member variables whose names (String) are supplied
by the method (return value is of type Vector), the XOI base class takes the encoding in the AddStateCode and
the restoration from it.

Regardless of whether the encoding is done via getAddStateMembers() or not, it should be noted that the mem-
ber variables to be encoded must not contain any object references!
There are two approaches to circumvent this limitation:
1. The two methods mentioned above are overwritten: in getAddStateCode(), the object references are
converted into storable information (e.g. object name, see below) before calling the inherited imple-
mentation, and in setAddStateCode() the object references accordingly are restored after calling the
inherited implementation.
2. No object references are stored in the relevant member variables, but rather an information from which
the respective object reference can be determined if necessary (e.g. object name, see below).
Caution: When using object names, the complete (hierarchical) object name must not be used, only the local
name within the planning group instance!
Methods localObjName() and localName2Obj() are available in all planning group classes to implement these
approaches. The methods are specified and implemented in the base class xOiPlGroup.

As an alternative to the (local) object name, the index of the instance can be saved under which the instance is
managed in the list of elements of the planning group instance (see method getElements() of OFML interface
MObject [ofml]).
If a list of object references has to be saved, global XOI functions xOiElRefs2ElIdcs() and xOiElIdcs2ElRefs() can be
used 67 . For an example how to use these methods see below.

Object references in member variables (currently) also have to be observed and handled in the OFML
persistence rules 68 !
Assuming there is a member variable mMyEL which contains a list of object references, the persistence rules
could be implemented as follows:

rule START_DUMP(pArg)
{
mMyEL = xOiElRefs2ElIdcs(self, mMyEL);
return(0);
}

67 see section "xOiFuncs", sub-section "DUMP and EVAL rule supporting functions" in the XOI documentation [xoi]
68 The basket implementation (OBK) used in the applications (for optimization reasons) writes a dump of the article instance
to the cut buffer when an article is deleted or copied and possibly during other operations.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 29/52

<!-- Page 30 -->

rule FINISH_DUMP(pArg)
{
mMyEL = xOiElIdcs2ElRefs(self, mMyEL);
return(0);
}
rule FINISH_EVAL(pArg)
{
mMyEL = xOiElIdcs2ElRefs(self, mMyEL);
return(0);
}

5.10.3 Additional start elements

According to section 5.7, overridden implementations of method setArticleSpec() can create further elements in
addition to the start elements that are created in the inherited implementation according to options
@StartElement resp. @StartLayout.
In order for the restoration to work using method setAddStateCode() of the base class, the following has to be
taken account of:
• If deriving from xOiJointPlGroup and xOiLayoutGroup, it must be ensured that overridden method
elRemoveValid() does not prevent the removal of elements created in setArticleSpec().

• If deriving from xOiTabularPlGroup and xOiCustomPlGroup, no additional elements may be created in
setArticleSpec() if the method is called in the course of the restoration of the planning group for re-
configuration. The distinction is made using method xOiBasePlanning::getCreationMode() 69 :

public func setArticleSpec(pArtNo)
{
xOiTabularPlGroupVert::setArticleSpec(pArtNo);
if (oiGetPlanning().getCreationMode() == 0) {
// add some further elements:
...
}
// else: nothing to do during re-creation
}

## 5.11 Overriding methods of XOI base classes

Occasionally, before or after a method of the planning group instance is called via an action of
OAP
type MethodCall, further treatments must be carried out. Ideally, this should be done via additional preceding
resp. succeeding OAP actions 70 . If this is not possible for certain reasons, or if it is more efficient to do all in one
method call, the method in question should not be overwritten directly in the derived class (in order to imple-
ment there the additional treatments), as this can hinder the further development of the used XOI base class 71 .
Instead, an own method should be defined and implemented in which the relevant method of the XOI base class
is called at a suitable point!

69 For details see documentation [xoi], section „Main Planning Classes“
XOI
70 according to the principle of avoiding OFML programming
71 e.g. the introduction of additional optional parameters

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 30/52

<!-- Page 31 -->

public func myXoiMethod(...)
{
// do something special
...

xoiMethod(...);
// do something other
...
}

## 5.12 Managing the property state of group elements

Often the task is that certain, normally editable properties of an article instance should not be editable (or not
visible at all) if the article instance is an element of a planning group. For example, it may be required that a
material property, e.g., @Color, which is raised to the planning group level using option @CommonProps (see
section 5.9), should not be editable for individual elements of the planning group in order to guarantee a uniform
look of the planning group.
Note:
If a property of the group elements is made not editable or not visible with the approaches described in this
section, but should be visible and editable as part of the @CommonProps on the level of the planning group,
option @ROPropsEditable4Common resp. option @NonVisibleProps4Common has to be used!

One approach to this involves the following steps:
• For the start elements of the planning group, also the state of the relevant properties is specified in
option @StartLayout (or @StartElement), e.g.:
@StartLayout;;[\
[NULL, @man_series,"0815",@VarCode,"",[],[[@Color,1]]],\
[@AP_R,@man_series,"0815",@VarCode,"",[],[[@Color,1]]]]
Here, the property state hast to be specified in accordance with method setPropState2() of OFML inter-
face Property [property]. There, value 1 specifies a visible but not editable property.
• For elements subsequently inserted into the planning group via an interactor, after the CreateObj
OAP
action in the action list of the interactor (or the relevant entries of an ActionChoice) an additional
PropChange action is specified (see also section 5.1), e.g.:
PC_DisableColor;Editability;Color;0

Note that this approach does not require any additional OFML programming. Unfortunately, this approach does
not work if the property in question is an original, commercial property of the article and the article is encapsu-
lated by a meta type instance: after a property change triggered by the planning group instance, the property
gets its original state again (editable).
Then, the approach described above has to be modified and expanded as follows:
• The commercial property in question is raised to the level of the meta type instance as a so-
called na-property. (The name of the property by default then changes to @GColor and must be
changed accordingly in the places mentioned above.)

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 31/52

<!-- Page 32 -->

• For the start elements, method setArticleSpec() must be overwritten in a specifically derived planning
group class according to the following pattern (for xOiJointPlGroup):
public func setArticleSpec(pSpec)
{
xOiJointPlGroup::setArticleSpec(pSpec);

var tEl;
foreach(tEl; self.getElOrder())
tEl.updateNAPropState(@GColor, 0);
}
• For elements subsequently inserted into the planning group via an OAP interactor, in the relevant action
list after the CreateObj action and the PropChange action described above an additional MethodCall
action must be specified according to the following pattern:

MC_Disable_GColor;Instance;::ofml::go::GoMetaTyppe;updateNAPropState;@GColor,0
Remark:
Method GoMetaType::updateNAPropState() guarantees a permanent state change of a na-property.
There, the status has to be specified according to method setPropState() of old OFML interface Property,
0
i.e., a property that is visible but cannot be edited here is specified by the value .

In the case of meta-type-based articles, the following approach may be more suitable, especially if the state of
72
several (many) properties has to be modified . This is often the case with meta types, since, in addition to the
above example with the material property, properties for an article exchange often are not useful in the context
of the planning group and must be deactivated:
• An auxiliary (invisible) property is created in the meta type, e.g. In_PGroup, with possible values 0 (no)
and 1 (yes), where 0 is the initial value.
go_actions, 73
• In table the relevant properties are deactivated via a CON_PROP action if the condition
In_PGroup == 1 is met.
• In OAP, property In_PGroup is set to 1. (For the start elements this is done in the corresponding option
in the control data table. For additional elements inserted via an interactor this is done via a PropChange
action after the CreateObj action in the relevant action list.)

## 5.13 Reaction to property changes of elements

Often the group instance has to react to changes of certain properties of group elements. In principle, this can
be realized with the following two approaches:
1. In the relevant classes of the group elements, method setPropValue() or propsChanged() is overridden
and the change of a relevant property is delegated to a corresponding method of the parent group
instance.

72 Option @StartLayout and the action lists then would become very long and confusing with the first approach.
73 For that, commercial properties such as @Color also have to be created as na-properties, as in the first approach.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 32/52

<!-- Page 33 -->

2. The group instance registers with the global change manager (type OiChangeManager) for change
events of type @PropertyChange, triggered by elements of the group, and reacts to them in method
receivePropertyChange() (example see below) 74 .
(For commercial properties that are raised to the level of an encapsulating meta type instance as so-
75
called na-properties, event type @MetaMainChildPropChange must be used if necessary .)
In most cases, the 2nd approach is preferable, as it does not require any implementations in project-specific
76
element classes !
In addition, the second approach facilitates the solution to the following problem:
If the group contains Meta type instances as elements, during the (re)creation of the group for reconfiguration
property changes are triggered by base class GoMetaType when processing the saved variant code. These
changes are irrelevant for the group instance, since the group has the correct, saved state when the (re)creation
process has finished. Alone for reasons of performance, the group instance should not react to these changes.
Even more, in certain cases there may be misbehavior or evaluation errors if the group reacts to them, since at
this point not all (other) group elements have been completely restored yet!

The following is the implementation pattern based on the 2nd approach:

public func initialize(pFather, pName)
{
<BaseClass>::initialize(pFather, pName);

var tChMgr = oiGetChangeManager();
if (tChMgr != NULL)
// consider property changes in (grand) children
tChMgr.register(self, @(@PropertyChange), [@(self), 0]);
}
public func receivePropertyChange(pPublisher, pKeys)
{
// Do nothing during Meta type initialization of pPublisher!
if (pPublisher.isA(GoMetaType) &&
(!pPublisher.isMetaInitialized() || pPublisher.sInSetAddStateCode))
return;

// process pKeys and check for possible re-action:
...
}

74 The concept of the global change manager and the currently supported event types are described in the XOI documentation
[xoi] in section "ChangeManager Event Types".
75 With these properties, the property change is delegated to the so-called main child of the meta type instance. Method
setPropValue() for the main child (also) reports an event of type @PropertyChange, but at that time no (possibly required
and relevant) adjustments in the meta type instance itself took place yet.
76 which might also have to be first derived from the standard classes just for this purpose

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 33/52

<!-- Page 34 -->

## 5.14 Collision detection

77
If a new element is added to a defined attach point of an element already in the group by means of a CreateObj
action or function xOiCreateArticle() (resp. xOiCreateArticle2()) in mode @extended , a standard check is per-
78
formed to determine whether the new element collides with other elements in the group . If a collision is de-
tected, the insertion of the new element is rejected.
In the case of inaccurate geometry data resp. inaccurately defined attachment points, collision detection for the
79
group elements is often switched off completely or temporarily (during the insertion process) in the OFML data .
This has the following consequences:
1. In the case of groups planned “around the corner”, the new element can collide with other group ele-
ments.
2. It is not possible to insert the new element between two other group elements (insert mode 2)!

In order to avoid these problems, the geometry data and attach points should be defined as precisely as possible
from the outset so that the collision detection need not be switched off!

If the deactivation of the collision detection cannot be prevented, e.g. with upholstered furniture, at least the
second problem can be avoided when using xOiCreateArticle() resp. xOiCreateArticle2() by applying mode
@att_pts 80 (instead of @extended)!.

If it is not possible to use mode @att_pts for any reason, the second problem can be circumvented in the fol-
lowing way. The basic idea is to use methods isBusyAttPt() 81 resp. isFreeAttPt() 82 to check whether the attach
point of the reference object is already occupied, and, in this case, to temporarily activate the collision detection:

// Used in OAP via a MethodCall action
public func myAddElement(pRefObj, pAttPt, pPID, pModel)
{
var tEl, tDisableCD = @(); // elements to be disabled again after xOiCreateArticle()
if (!isFreeAttPt(pRefObj, pAttpt)) {
// enforce re-positioning of previous neighbors (insert mode 2)
foreach(tEl; getElements()) {
if (!tEl.isEnabledCD()) {
tDisableCD.pushBack(tEl);
tEl.enableCD();
}
}
}
var tNewEl = xOiCreateArticle(self, pRefObj, pAttpt, pPID, tModel, "", @VarCode);
// tNewEl. disableCD(); // ?
foreach(tEl; tDisableCD) tEl.disableCD();
...
}

77 Concerns the group types xOiCustomPlGroup, xOiJointPlGroup and xOiLayoutGroup.
78 via method checkChildColl() of interface Complex [ofml]
OFML
79 via method disableCD() of OFML interface Base [ofml]
80 This mode is supported from the application releases in fall 2024.
81 class xOiJointPlGroup
82 class xOiLayoutGroup and xOiCustomPlGroup,

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 34/52

<!-- Page 35 -->

# 6 Base class xOiCustomModule

84
The base class xOiCustomModule from the OFML base library XOI 83 can be used to implement custom modules .
A module is a composite article ( OFML interface CompositeArticle [article]) that consists of a fixed or variable
number of sub-articles. As a rule, a module represents a pseudo-article (see category @PseudoArticle in the
specification of OFML interface Article [article]).
An instance of this class does not have its own geometry, but its geometry is made up of the geometries of its
sub-elements and their position resp. rotation in the local coordinate system of the module instance.
The class provides a more performant variant for the implementation of such modules compared to the use of
Meta types. A Meta type should only be used if the module has a dedicated main article and article polymorphism
must be implemented.
The class supports the following general concepts (some of which are already known from the classes for plan-
ning groups):
• Controlling aspects of the behavior by means of options in a control data table.
In particular, this refers to the generation of common properties.
The possible options in the control data table custommodule are described in the Application Note
AN-2006-01 [an0601].
•
Generic implementation of methods getAddStateCode() and setAddStateCode() ( OFML interface
Article).
The names of the member variables of derived classes that are to be encoded just have to be specified
in the List of Strings returned by hook method getAddStateMembers().
Note: The member variables to be encoded must not contain any object references!
• Generic implementation of OFML interface CompositeArticle.
• Generic implementation of interface AttachPts.
OFML
This implementation is based on information in the data tables addattptdefs and
oppositeattpts,
which are described in the appendix of Application Note AN-2006-01 [an0601].
• A distinction can be made between 2 types of module elements (parts):
o Intrinsic elements of the module:
They are only created resp. removed by the module instance. The user may be able to change
their properties but can only create and remove them indirectly by changing properties of the
module instance. For instance, changing property Height of a rack module will add resp. remove
some shelve objects (which are intrinsic parts of the module).
o Additional elements (add-ons):
They are created resp. removed interactively by the user by changing properties of the module
instance 85 or using OAP interactors.
•
Some or all intrinsic parts can be created automatically during module initialization by specifying the
required data in a special table (see section 6.1 below).

83 The class is specified in the XOI documentation [xoi] in section „Main Planning Elements“.
84 as of the application releases in fall 2024
85 similar to the child-creation properties of Meta types

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 35/52

<!-- Page 36 -->

## 6.1 Module initialization

The initialization of a module instance is executed in the method setArticleSpec() ( OFML interface Article). The
implementation in the base class xOiCustomModule performs the following actions:
custommodule
1. Reads the control data table (if any).
2. If value @Slot1 is specified for option @ApplyOCDProps:
Sets up OFML properties for properties defined in OCD for the article represented by the module in-
stance.
3. Calls hook method initializeModule() (see below).
4. If value @Slot2 is specified for option @ApplyOCDProps:
Sets up properties for properties defined in for the article represented by the module in-
OFML OCD
stance.
5. Only, if the call takes places during the initial creation of the module instance (i.e., not during the re-
creation of the module instance from its basket representation):
1. Creates intrinsic parts based on data table cmoduleparts (if any).
cmoduleparts
The data table is described in the appendix of Application Note AN-2006-01
[an0601].
2. Calls hook method onModuleCreation() (see below).
3. Generates the common properties (according to options in the control data table).

Method setArticleSpec() should not be overwritten in subclasses! Instead, use the mentioned hook methods to
create sub-elements and to program properties (in addition to the generated common properties).

initializeModule () → Symbol[]
Hook method provided for derived classes to initialize the module instance.
Typically, this method is used in derived classes to set up the so-called fixed properties (see section 6.2).
This method must not be used to create sub-items (parts) or to define non-fixed properties! Use hook
method onModuleCreation() (see below) for this purpose!
Return value is a List of the keys (Symbol) of the fixed properties, that were setup during the method.

onModuleCreation () → Void
Hook method provided for derived classes to create (intrinsic) sub-items and to set up non-fixed properties.
This method is called only during the initial creation of a module instance, not during the re-creation of a
module instance from its basket representation.
The method is called after (some) intrinsic parts have been created based on data table cmoduleparts (if
any). In this case, derived classes can use this method to create additional sub-items (intrinsic or other).

Below is an example of a module initialization of a typical shelf system realized by a planning group on the top
level. The elements of the group are shelf modules consisting of ladders (left and right) and boards, where the
class of the modules is derived from xOiCustomModule. In the example, the ladders are created automatically
based on data table cmoduleparts, while the initial boards are created in hook method onModuleCreation().

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 36/52

<!-- Page 37 -->

protected func initializeModule()
{
var tFixedProps = self.setupMyFixedProperties();
return(tFixedProps);
}
protected func onModuleCreation()
{
self.setupMySmartProperties();

var tPG = self.getFather();
var tFH = tPG.getFolderHeight();
var tH;
for (tH = 0; tH <= tFH; tH++) {
var tBoard = self.createBoard(tH);
if (tBoard != NULL)
self.addIntrinsicElement(tBoard, 1);
}
}
Notes:
• The boards are created using global function xOiCreateArticle() (see appendix A).
• Inherited method addIntrinsicElement() (see section 6.3) is used to add the board instances to the list
of intrinsic elements and to specify some mode values to be assigned to the instance.

## 6.2 Properties

A module instance can have three types of properties:
• Common properties, that are automatically generated based on options @CommonProps & Co. in con-
trol data table custommodule.
•
Properties, that are set up for properties defined in OCD for the article represented by the module
instance. (See option @ApplyOCDProps in the Application Note AN-2006-01 [an0601].)
• Properties programmed in derived classes.
These are divided into:
• So-called fixed properties:
The attributes of fixed properties do not change during the "life" of the module, i.e., do not
depend on the current configuration of the module resp. on other properties.
They are defined/created in hook method initializeModule(), which is called both during the
initial creation of the module instance and during the re-creation of the module instance from
its basket representation.
•
All other properties may change their choice lists resp. value ranges as well as their state, de-
pending on the current configuration of the module resp. on other properties.
They are defined/created in hook method onModuleCreation(), which is called only during the
initial creation of the module.
The values of programmed properties are expected to be stored in the hash table for dynamic properties
(see method getDynamicProps() of OFML interface Base).

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 37/52

<!-- Page 38 -->

Note on properties:
OCD
Even if a module usually represents a pseudo-article (without real commercial characteristics), using (artificial)
properties the programming of properties in derived classes can be avoided. Especially with more complex
OCD
dependencies between properties, data creation via is often more elegant, e.g., due to the possibility of
OCD
using value combination tables.
(See also notes on the use of scope RG in section 4.5.)

All generated common properties as well as the programmed properties specified via hook method
getProgrammedPropKeys() (see below) are (automatically) encoded in the AddStateCode, where for the fixed
properties only their current value is encoded.
A fixed property requires significantly less space in the AddStateCode. However, it must be carefully considered
at the start of the project whether a programmed property can be declared as a fixed property, as a later con-
version to a non-fixed property is problematic: Although the definition of the property can be moved from
method initializeModule() to onModuleCreation(), however, when a module instance is restored from a saved
basket representation, the property value saved there would not be adopted (i.e., the instance would then have
the initial value defined in onModuleCreation()).

Methods related to programmed properties:

getProgrammedPropKeys () → Symbol[]
Returns a List of the keys of properties that have been set up in derived classes.

programmedPropsChanged (pProps, pDoChecks) → Int
Handles the change of the specified properties programmed in derived classes.
Hook method called from the implementation of method propsChanged() ( OFML interface Property) in the
base class xOiCustomModule.
This method has same specification and semantics as propsChanged() (see [property]) and has to be over-
ridden in derived classes for programmed properties (according to getProgrammedPropKeys() above).

updateProgrammedProperties (pAfterAddStateCode, pChangedLanguage, ...) → Void
Updates the definitions of properties programmed in derived classes.
Hook method called from the implementation of method updateProperties() of OFML interface Property
[property] in the base class xOiCustomModule.
Parameter pAfterAddStateCode (Int) specifies whether this is the first call after setAddStateCode() in the
course of the re-creation of the module instance from its basket representation.
If the parameter has the value 1 (yes/true), this method can be used to adapt programmed non-fixed prop-
erties to possible changes in the product data (compared to the time, when the basket representation was
saved). This can be necessary if the definition of a programmed non-fixed property depends on the choice
lists or other attributes of properties of sub-article instances.
Parameter pChangedLanguage (Int) specifies whether the product data language has changed since last call
of updateProperties() or if it is different from the language specified in the code passed to the immediate
preceding call of setAddStateCode().
If the parameter has the value 1 (yes/true), this method can be used to adapt the names of programmed
properties resp. of choice list values to a change language setting in the used application. This is necessary
if no text resources are used for property resp. value names.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 38/52

<!-- Page 39 -->

Methods related to common properties:

assignCommonPropValues (pEl) → Void
Assigns the current values of the common (module) properties to the specified module element (insofar it
possesses these properties).

This method is mainly intended for new elements inserted into a module configuration.
Instead of a single module element a List or Vector of elements may be passed.
custommodule 0
If option @CommonPropsDepth in the control data table has a value greater than , sub-
articles of given element(s) at according hierarchy levels will be affected, too.

updateCommonProperties () → Void
Updates the common properties of the module instance.
To be called by clients if a property has been changed which affects the visibility or the state of common
module properties, where the changed property itself is not included in the set of the common module
properties.
See also the notes in section 5.9.1.

## 6.3 Managing elements (parts)

The following methods can be used to manage and access the lists of intrinsic and additional module elements.

addIntrinsicElement (pObj, pSelectable, ...) → Void
Adds given instance to the list of intrinsic module elements/parts.
Parameter pSelectable (Int) specifies, whether the element is selectable by the user (1) or not (0).
If first optional parameter is given, it specifies the state according to method setCutable() ( interface
OFML
Base) to be assigned to the element.
The default state is 0, i.e., the element cannot be deleted by the user via the Cut or Delete operation of the
application.
If a second and a third optional parameter are given, they specify the degrees of freedom for translation
resp. rotation of the element according to methods setTrAxis() resp. setRtAxis() ( OFML interface Base).
The default degrees of freedom are 0 (for both translation and rotation).
If the given instance is not an element of the module instance, the method has no effect.

getIntrinsicElements () → MObject[]
Returns the list of current intrinsic module elements/parts.
The order of the elements in the list corresponds to the order of insertion.

getIntrinsicElCount () → Int
Returns the current number of elements in the list of intrinsic elements/parts.

isIntrinsicElement (pObj) → Int
Returns True (1) if given instance is contained in the list of current intrinsic module elements/parts.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 39/52

<!-- Page 40 -->

addAdditionalElement (pObj, pSelectable, ...) → Void
Adds given instance to the list of additional elements (add-ons).
Parameter pSelectable (Int) specifies, whether the element is selectable by the user ( 1 ) or not ( 0 ).

If first optional parameter is given, it specifies the state according to method setCutable() ( OFML interface
Base) to be assigned to the element.
0
The default state is , i.e., the element cannot be deleted by the user via the Cut or Delete operation of the
application.
If a second and a third optional parameter are given, they specify the degrees of freedom for translation
resp. rotation of the element according to methods setTrAxis() resp. setRtAxis() ( OFML interface Base).
The default degrees of freedom are 0 (for both translation and rotation).
If the given instance is not an element of the module instance, the method has no effect.

getAdditionalElements () → MObject[]
Returns the current list of additional elements (add-ons).
The order of the elements in the list corresponds to the order of insertion.

hasAdditionalElements () → Int
Returns True (1) if the module contains additional elements (add-ons).

isAdditionalElement (pObj) → Int
Returns True (1) if given instance is contained in the current list of additional elements (add-ons).

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 40/52

<!-- Page 41 -->

# 7 OFML-Debugging

The remarks in this section refer to the OFML debugging in the pCon.planner using the OFML Console provided
with the plugin X3G-OFC .

## 7.1 Debugging the xOiOAPManager

The OAP Manager is the interface between the OAP data and the applications. For that, at runtime there is
exactly one instance of the class xOiOAPManager. In case of problems during processing the OAP data, an OFML
debug log for this class can be helpful 86 . Essentially 3 top-level methods are relevant here:
• When selecting an article the application calls methods getArticleData() and getInteractors() (in this
order).
•
When an interactor is activated the application calls method getActionData() for each action of the in-
87
teractor .
88
(The detailed specification of these methods can be found in the XOI documentation [xoi] .)
Calls of getArticleData()/getInteractors() occur again - with unchanged selection - if the mouse pointer enters
another view of the Planner (because for each view the interactor symbols have to be determined and displayed).
In order to avoid unnecessary output in the log file, it is recommended to debug in 1-view mode.

Errors in the OAP tables can be found relatively easily and quickly by looking for the following output in the log
file ( debug.out ):
W: OAP database access error: ...
For this purpose, at least the debug modes Warn(ing) , Func and Func2 must be set and the function trace
level should be set to at least 5 (if ActionChoice actions are involved, at least to 7).

## 7.2 Debugging CreateObj

If a CreateObj action with a given attach point (or a MethodCall action using global functions xOiCreateArticle()
and xOiCreateArticle2() in mode ) does not produce the desired result (object is not created), the
@extended
cause often is not immediately obvious.
Here are 2 troubleshooting tips:

1.
One reason could be that a collision of the new object with already existing objects would occur at the position
of the selected attach point (either due to incorrectly positioned attach point or due to "inaccurate" geometries).
Whether this is the case can be seen quite quickly with the debug setting Collision. The log file then contains
entries like this

c.e1 (myPlGroup) detected collision: c.e1.ch (myClass) >|< c.e1.e1 (myClass) ...

86 The already provides a suitable debug profile for this purpose.
OFML Console OAP
87 If an error occurs while accessing the OAP data of an action, the processing of the actions is terminated.
88 Class xOiOAPManager is contained in section "Utility Classes".

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 41/52

<!-- Page 42 -->

2.
If 1. does not apply, (unfortunately) one must dive a little deeper into the process of object creation. It is im-
portant to know that the above actions are based on the so-called checkAdd() mechanism. For details about this
see the OFML specification. For the moment it is enough to know the following:
Method checkAdd() is called on the parent object to determine the position and rotation for the new object.
Before this, the attach point specified in the action is activated at the reference object (neighbor) using method
setActiveAttPt() (interface AttachPts [xoi]).
Thus, in general, in case of problems with CreateObj, the class of the parent object (and possibly relevant base
89
classes ) has to be specified in the debug settings. In the log file then you have to look for clues in the outputs
for method checkAdd().
However, in a first step it is recommended to specify only the class OiGlobal and to search in the log for the global
function oiGetPosRot4AttachPts(). This function is used by all standard implementations of checkAdd() in the
base classes of OI and XOI for the actual determination of position and rotation for the new object..
One cause for a failure of checkAdd() could be, e.g., that there is no definition for the given attach point. Then
you would see this relatively quickly based on the output for the mentioned function:

1> OiGlobal::oiGetPosRot4AttachPts(object: c.e1.e1 (GoMetaType), [object: c.e1.ch
(GoMetaType), NULL, 1, 1, 1])
I: is child?: 0
I: list of att pts: @(...)
I: active attach point: @ApOb_12R
W: missing or wrong attach point definition for active attach point @ApOb_12R
1< OiGlobal::oiGetPosRot4AttachPts: NULL.

If this is not the case, the cause of the error could be that there is no suitable opposite for the active attach point.
This can be seen in the log by adding the class OiFuncs. Then, the output for function oiCalcCheckAttPt() in the
log (1 level below oiGetPosRot4AttachPts()) shows the following:

no opposite attach point(s) for @ApOb_12R ...

In case of attach points defined in meta data table go_attpt.csv , the cause could be that they are not defined
as opposites in table go_action.csv .

## 7.3 Usage of xOiOAPManager::setDBMode()

Normally, the currently accessed OAP database will be kept open until access to the OAP database for another
OFML program. This is somewhat inconvenient for the OAP data creator, as he/she cannot test "live" changes
in the OAP data of the OFML program currently being edited.
The class xOiOAPManager provides the method setDBMode() to change this default behavior (mode
@KeepOpen): With mode @CloseOpen OAP databases will be closed and opened at each time an object is se-
lected or after an action was performed.If you enter the command
/t.getOAPManager().setDBMode(@CloseOpen)
in the command line of the OFML Console , then you can immediately test changes in the OAP data 90 .

89
e.g., in the case of xOiJointPlGroup the base classes xOiLRPlGroup and xOiPlGroup
90 However, the oap.ebase must be rebuilt in the process.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 42/52

<!-- Page 43 -->

# 8 Miscellaneous

## 8.1 EBase for control data tables

If a control data table used by planning group class (see section 5) has to be transferred to the ofml.ebase
and an EBase version older than 1.2.3 91 is used, the following problem has to be considered:

If an empty variant code is specified in a table entry for option @StartElement or @StartLayout, like in

@StartElement;;[@foo_bar,"ArticleNr",@VarCode,"",[]]

the field must be enclosed in double quotation marks (") and double quotation marks in the field contents have
to be replaced by 2 consecutive double quotation marks:

@StartElement;;"[@foo_bar,""ArticleNr"",@VarCode,"""",[]]"

Such a transformation is also required if the article number or the variant code contains a semicolon 92 .

Advice:
The elements in the vector after the article number are optional. If these are not relevant, as in the example
above, they should be omitted, which makes a transformation superfluous:

@StartElement;;[@foo_bar,"ArticleNr"]

## 8.2 Metatype-Type-Mapping

The specification contains no statement which series to specify in field 2 of the Metatype2Type table.
It is currently implemented in such a way that the series of the article is expected in this field, not the series in
which the Meta type is created!

A consequence of this is that in the case where an OAP database is created for several commercial series, and
there are articles from the various series that use one Meta type (ID) (no matter in which series this is created)
for this Meta type multiple entries have to be created in the mapping table, for example:

man;foo;MTID;;OAP_TYPE
man;bar;MTID;;OAP_TYPE

(There may be other/better regulations in the future. In any case, a future change in the OAP core of the applications will
contain a downward-compatible fallback, so that OAP data created according to the current state still will be processed cor-
rectly.)

91 contained in version 1.4.0 of the OFML-Binaries
92 This corresponds to the regulations known from the specifications of OCD and OAP for the representation of a table field.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 43/52

<!-- Page 44 -->

## 8.3 Auxiliary objects with OAP interactors

In more complex projects, in a planning group or generally within a composite configuration, auxiliary objects
that have OAP interactors may be required to facilitate planning by the user. For example, this often applies to
placeholders in a planning group with a tabular layout (xOiTabularPlGroup).
For that, the auxiliary object must be an article instance. However, as a rule, the object will represent an article
that does not actually exist. Then, the instances in any case should belong to the category @PseudoArticle (see
appendix in [article]). As these instances (presumably) should also not be contained in offer forms and order
documents, the categories @NonOfferArticle and @NonOrderArticle must also be set.
Data creators/manufacturers may be inclined to keep the auxiliary articles also out of technical article lists. This
can be achieved, for example, with a planning group using hook method getInvalidSubArticleSpecs() specified in
the base class xOiPlGroup or with placeholders in an xOiTabularPlGroup using the value 0 for the option
@FieldPlaceholder4SubArticle.
In this case, however, the object categories ParentArticle and TopArticle do not apply to the auxiliary objects!
This means that methods of the higher-level instance (e.g., the planning group) cannot be called directly
in actions of interactors bound to the auxiliary object.
Then, extra methods must be implemented in the class of the auxiliary objects, which delegate the request to
the relevant method of the higher-level instance.
In the case of auxiliary objects in a planning group, the following alternative approach can be taken:
•
The auxiliary objects can be hidden by the user via a (programmed) property (e.g. “planning aid”) (using
method hide() of OFML interface Base).
• The above-mentioned hook method getInvalidSubArticleSpecs() is overwritten and returns the article
number of the auxiliary objects in the “hidden” state.
In the “hidden” state, the auxiliary articles do not appear in the technical article list. Then, object categories
ParentArticle and TopArticle do not take effect, but this does not matter in this state, as the interactors of the
auxiliary objects are not visible/active anyway.
With this approach, it is therefore up to the user to decide whether the auxiliary articles are included in the
technical article list.

## 8.4 Use of event @RecreationModeFinished

From spring releases 2025, an event of type @RecreationModeFinished is reported to the global Change
Manager 93 when the process of restoring an article instance 94 from a saved basket representation has been com-
pleted 95 .
Especially for composite articles (e.g. planning groups) it may be useful or necessary to register for events of this
type.

93 The concept of the global change manager and the currently supported event types are described in the XOI documentation
[xoi] in section "ChangeManager Event Types".
94 at the highest hierarchy level
95 for more details/background see appendix E in the specification of interface Article [article]

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 44/52

<!-- Page 45 -->

For example, one use case are auxiliary objects that themselves are not sub-articles of the composite article, but
which can only be created correctly when all sub-articles have been completely restored. (Then, the auxiliary
object cannot be created at the end of method setAddStateCode() overwritten in the class of the composite
article).

Note, that the argument list of events of this type contains only instances at top hierarchy level. If a composite
instance, which itself is a sub-article instance, has registered for events of this type this hat to be taken into
account accordingly in the implementation of the receive-method:

public func receiveRecreationModeFinished(pPublisher, pArgs)
{
if (pArgs.find(self.getFather()) >= 0)
self.createMyAuxiliaryObj();

}

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 45/52

<!-- Page 46 -->

# Appendix

## A. Specification and Usage of xOiCreateArticle/2() and xOiCloneArticle()

xOiCreateArticle (pFather, pRefObj, pAttPt, pPID, pArticle, pVarCode, pCodeType, ...) → MObject|Void
Creates an instance representing the article specified by program ID, base article number and variant code
as a child of given father object.
The required parameters are:
• pFather: father object (MObject)
•
pRefObj: reference object (MObject or Void) to be used for positioning
• pAttPt: key (Symbol or Void) of attach point of reference object to be used for positioning
• pPID: OFML program ID (Symbol)
• pArticle: base article number (String)
• pVarCode: variant code (String)
• pCodeType: type of variant code (Symbol: @VarCode , @OFMLVarCode , @Final )

If first optional parameter is specified, it is used to modify/specify the extent of this function. Currently, the
following two modes/values (of type Symbol) are supported:
@extended (default)
Simulates the standardized article creation process of an OFML application based on method checkAdd()
of interface Complex (including the creation of a temporary object) in order to determine position and
rotation for the new article instance.
If a reference object and an attach point of this object are given (parameters pRefObj and pAttPt are not
NULL ) they will be used for positioning.
At the end of the creation process, an event of type @ArticleInserted is issued.
@lite
Determines the type (class) for given article, creates an instance of this class using method add() of
OFML interface Complex and then assigns given article number and variant code.
Parameters pRefObj and pAttPt have no impact (will be ignored).
Position and rotation for the new article instance have to be determined and assigned by the client after
the call of this method.
(In this mode, no event of type @ArticleInserted is issued at the end of the creation procedure.)

@att_pts
This mode expands mode @lite :
• Position and rotation for new article instance are determined using interface AttachPts (and
OFML
are assigned by this function).
In this mode, parameters pRefObj and pAttPt must not be and the classes of the reference
NULL
object as well of the added object must implement the OFML interface AttachPts. (Otherwise, the
function has no effect.)
• If the class of the father object is a subclass of xOiPlGroup and the class allows to check whether a
given attach point of a group element already is busy (occupied), i.e., is used to connect to another
existing other group element, the function executes the following actions:

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 46/52

<!-- Page 47 -->

If the attach point pAttPt of pRefObj is busy, method handleInsertion() is called on the father object
to handle a possible insertion of the new object between two existing elements (moving some of
the existing elements away). If method handleInsertion() returns an error (i.e., insertion is not pos-
sible/allowed), the new object that has already been created is removed (i.e., the function has no
effect).
• Finally, before calling beAnElement() on the new object (triggering rule NEW_ELEMENT on the fa-
ther object), method prepare4NewElement(pInfo) is called on the father object, if its class imple-
ments this method.
The parameter is a Vector providing information which could be useful/necessary for updating the
internal data structures of the father object. Currently, the following information is passed (in the
specified order):
1. the reference object (MObject)
2. the local bounding box of the new object (according to method getLocalGeoBounds(), OFML
interface Base)
3. the used attach point of the reference object (Symbol)
4. the used attach point of the new object (Symbol)

If a second optional parameter (of type Symbol) is given, it specifies the key of the attach point of the new
child to be passed to checkAdd() called on the father instance.
The current implementation passes this parameter only if the father is an instance of class xOiPlGroup (the
base class for all planning group types).

Returns the reference to the created article instance or NULL in case of errors during creation.

xOiCreateArticle2 (pFather, pRefObj, pAttPt, pPID, pArticle, pVarCode, pCodeType, pMode, pChAttPt, pName, ...)
→ MObject|Void
Creates an instance representing the article specified by program ID, base article number and variant code
as a child of given father object.
This version extends the functionality of xOiCreateArticle() (see above).
The first 7 parameters have the same meaning as for xOiCreateArticle() where parameters pMode and
pChAttPt correspond to the first resp. second optional parameter of xOiCreateArticle().
Note:
In contrast to xOiCreateArticle(), here an event of type is issued at the end of the cre-
@ArticleInserted
ation procedure also in modes and !
@lite @att_pts

Parameter pName specifies the local name (String) of the child instance to be created. If there is already a
NULL).
child instance with this name, no new child instance will be created (and the function returns
NULL,
If the parameter pName is the local name is determined automatically by the OFML runtime environ-
ment (what is the fix behavior in function xOiCreateArticle()).

If first optional parameter is given, it specifies, whether the article instance has to be created as a Meta type
(if the data is provided for that). Default is 1 (true/yes). Value 0 ignores possibly existing meta data.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 47/52

<!-- Page 48 -->

If a second optional parameter is given (and it is not NULL ), it specifies a Vector of property settings.
Each element in the Vector is itself a Vector of 2 elements:
1. property key (Symbol)
2. property value (Any)
The assignment of the property values takes place after the actual article creation procedure.

If a third optional parameter is given, it specifies, whether a possibly existing child instance with the same
local name, as given in parameter pName, should be removed before creating the new instance (with the
same name).
0
Default is (no/false), in which case the behavior is as described above.
If the parameter has value 1 , but removal of existing child instance fails, no new child instance will be created
(and the function returns NULL ).
Note: The removal fails, if method removeValid() ( OFML interface Base) of the existing child instance returns
0 (false) or if method elRemoveValid() of the father instance, called for the existing child instance, returns 0
(false).

xOiCloneArticle (pFather, pSource, pRefObj, pAttPt, ...) → MObject|Void
Creates a clone of specified article instance (pSource) as a child of given father object (pFather).

Parameters pRefObj and pAttPt are used to determine position and rotation of the new instance (clone):
NULL
• If pRefObj is not and given instance is an immediate child of pFather and the classes of pSource
and pRefObj implement the OFML interface AttachPts, the clone will be positioned beside pRefObj
using attach points with mode @Sibling .
In this case, pAttPt, if not NULL, defines the key (Symbol) of the attach point of the reference object
to be used for positioning.
• If pRefObj is NULL or is not an immediate child of pFather or its class does not implement the
OFML
interface AttachPts, and if both the classes of pSource and pFather implement the OFML interface
AttachPts, the clone will be positioned using attach points of pFather with mode @Child .
• In all other cases the clone gets no specific position and rotation.
Notes:
• pSource and pRefObj may refer to the same instance!
• There is no collision check when determining position and rotation.

If first optional parameter is given, it specifies the local name (String) for the clone. If the parameter is not
NULL
given or if it is and if pSource is an element instance, the name of the clone will be determined auto-
matically.
Note: If pSource is not an element (but a simple child), a name for the clone has to be given, otherwise the
method has no effect!

If a second optional parameter is given, it specifies the key (Symbol) of the attach point of the clone which
has to be used during positioning (see above).

NULL
Returns the reference to the created article instance or in case of errors during cloning.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 48/52

<!-- Page 49 -->

As a rule, further actions are required in the method that calls the function xOiCloneArticle(). In the case of
modules that are layout elements of a planning group of type xOiLayoutGroup, an attached clone typically
should also be a layout element of the planning group. This can be achieved in the following way 96 :

public func cloneModule(pAttPt)
{
var tPG = self.getFather();
tPG.delayHandleNewElement(@DuringCloneOp);

var tClone = xOiCloneArticle(tPG, self, self, pAttPt);
if (tClone != NULL)
tPG.handleNewElement2(tClone, @Layout, self,
oiGetAttPt4LastPosRot2(self), NULL, NULL);
else
tPG.delayHandleNewElement(NULL);
}

The integration of the method in the OAP data then typically looks like this:
oap_interactor.csv:
IA_CloneModule;;;AC_CloneModule,…;Duplicate;medium
oap_action.csv:
AC_CloneModule;;MethodCall;MC_cloneModule;OB_SELF
oap_methodcall.csv:
MC_cloneModule;Instance;::foo::bar::MyModule;cloneModule;@AP_R

96 Without these arrangements, the clone instance would be included in the list of other (additional) elements.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 49/52

<!-- Page 50 -->

## B. Document history

2025-05-21:
• Additions in section 6 regarding properties that are set up for properties defined for the module article
in OCD.
•
New section 8.4 on the use of events of type @RecreationModeFinished.

2024-11-18:
• Section 4.1 now also refers to the global function xOiCloneArticle().
• Reworked section 5.14, now describing a solution using (new) mode of global functions
@att_pts
xOiCreateArticle() and xOiCreateArticle2().
• New section 6 with notes on the implementation of custom modules.
• New section 7.3 with notes on the use of xOiOAPManager::setDBMode().
•
New section 8.3 with notes on the implementation of auxiliary objects with OAP interactors.
• New appendix (A) with the specifications of global functions xOiCreateArticle(), xOiCreateArticle2() and
xOiCloneArticle().
•
Various minor changes.

2023-11-07:
• Various minor corrections and improvements.
• Additional notes in section 3.3 (dynamic interactors) related to the target object of an action whose ID
is used as the argument of a methodCall() expression in conditions.
• New section 3.5 on considering the configuration context for interactor visibility.
• In section 4.1 now the new global function xOiCreateArticle2() is mentioned.
• Section 5 now considers new class xOiCustomPlGroup.
• Added note regarding extended behavior of xOiPlGroup::updateProperties() in section 5.9.1.
•
More precise description regarding usage of method getPDLangauage() in section 5.9.4.
• New note in section 5.9.4 regarding usage of new option @CommonPropsPos.
• New note in section 5.9.4 on reacting to possible changes in the product data when definitions of pro-
grammed properties are derived from attributes (e.g., choice lists) of properties of group elements.
•
New hint on event type @MetaMainChildPropChange in section 5.13.
• Additional notes on collision detection in section 5.14.
• New section 6.3.

2022-01-03:
• New section 5.14 with notes on collision detection.
• Correction and addition regarding the debug settings in section 6.1.

2021-11-17:
• First version containing this history.
• Obsolete section 3.2 “Visibility of interactor symbols” has been replaced by a section that addresses the
question of when it is better to bind an interactor to the planning group or to the group element.
•
Sections 3.3 and 3.4 have been swapped.
• Update of section 3.3 on dynamic interactors, including notes on the use of placeholder $INTERACTOR .
• Additional note in section 4.4 on actions that remove the active object.
• New section 4.6 on the use of the dummy action type NoAction.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 50/52

<!-- Page 51 -->

• Class xOiTabularPlGroup now is treated in section 5 "on an equal footing" with the older classes for
planning groups.
• Additional note in section 5.1 on the use of object category MethodCall.
• Additional note in section 5.5 on method xOiLayoutGroup::replaceElement().
•
Extensive expansion and restructuring of section 5.9 with many new information and tips on creating
and using of group properties (common properties).
• Renaming of section 5.11 (better description of the content) and addition of an example.
• Additional note in section 5.12 on the use of options @ROPropsEditable4Common and
@NonVisibleProps4Common.
• New section 5.13 with notes on the realization of reactions to property changes of elements on the part
of a group instance.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 51/52

<!-- Page 52 -->

Legal remarks

© 2025 EasternGraphics GmbH | Albert-Einstein-Straße 1 | 98693 Ilmenau | GERMANY

This work (whether as text, file, book or in other form) is copyright. All rights are reserved by
EasternGraphics GmbH. Translation, reproduction or distribution of the whole or parts thereof is permitted only
with the prior agreement in writing of EasternGraphics GmbH.

EasternGraphics GmbH accepts no liability for the completeness, freedom from errors, topicality or continuity of
this work or for its suitability to the intended purposes of the user. All liability except in the case of malicious
intent, gross negligence or harm to life and limb is excluded.

All names or descriptions contained in this work may be the trademarks of the relevant copyright owner and as
such legally protected. The fact that such trademarks appear in this work entitles no-one to assume that they are
for the free use of all and sundry.

© 2025 EasternGraphics GmbH Notes on OAP data creation and Planning groups 52/52