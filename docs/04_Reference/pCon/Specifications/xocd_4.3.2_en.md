Specification
XOCD
Extended   OFML   Commercial   Data
Version   4.3
2nd   revised   version
Status:   Final
Ekkehard   Beier
Stefan   Sachs
2026-03-27

XOCD   -   Extended   OFML   Commercial   Data
Version   4.3.2
Copyright   ©   2004-2026   EasternGraphics.   All   rights   reserved.

Contents
1
Introduction
2
2
The   additional   tables
4
2.1
The   series   tables
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
4
2.2
The   price   list   table   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
5
2.3
The   text   category   table
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
5
3
The   extended   tables
6
3.1
The   article   table
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
6
3.2
The   property   class   table   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
7
3.3
The   property   table   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
8
3.4
The   article   base   table
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
9
3.5
The   property   value   table   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
9
3.6
Property   groups
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
10
3.7
The   relational   object   table   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
11
3.8
The   relational   knowledge   table
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
11
3.9
Value   combination   tables
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
11
3.10   The   price   table   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
12
3.11   The   rounding   rule   table   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
13
3.12   The   taxation   scheme   tables   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
14
3.13   The   code   scheme   table   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
15
3.14   The   packaging   table   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
16
3.15   The   classification   table   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
17
3.16   The   description   tables   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
18
3.17   The   version   information   table   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
18
Modification   history
19
1

1
Introduction
XOCD   is   an   extension   format   based   on   OCD.   This   extended   format   has   got   following   additional
features   compared   to   OCD:
•   Support   of   several   series,
•   Support   of   several   price   lists,
•   Support   of   several   text   categories   as   well   as
•   Support   of   data   filtering   for   different   markets
Presently,   XOCD   is   not   a   format   to   be   used   in   planning   and   configuration   tools.   Its   application   is
reserved   for   the   processes   of   the   product   data   collection   and   conversion.
The physical exchange format corresponds to the OCD format with the following differences.   Only
the tables and fields described in this document are supported.   Furthermore, the prefix of the data
table   file   names   is   “ xocd_ ”.
All   extended   tables   are   preceded   by   the   key   Program   which   defines   to   which   series   they   belong.
This key corresponds to the value of the same name of the series registration according to the DSR
description.
Alternatively,   a   wildcard   ( * )   can   be   indicated   as   serial   key   in   the   following   tables:
•   CodeScheme ,
•   Property ,
•   PropertyValue ,
•   PropertyGroup ,
•   RelationObj ,
•   Relation ,
•   Price ,
•   Rounding ,
•   TaxScheme ,
•   Packaging   as   well   as
•   in   all   description   tables.
Then   these   entries   will   be   applied   for   all   series.   The   serial   related   entries   have   priority   over   the
comprehensive   entries.
The   price   table   is   furthermore   extended   by   one   field   to   indicate   a   price   list   reference.
The   text   tables   are   additionally   extended   by   one   field   to   store   a   text   category.
Furthermore,   XOCD   defines   three   new   tables:
•   the   table   of   the   series,
•   the   table   of   the   price   lists   as   well   as
•   the   table   of   the   text   categories.
2

The following tables contain a separate field to enter information to support market specific filtering
of   the   entries.
•   Programs ,
•   Article ,
•   ArtBase ,
•   PropertyValue
A   character   string   can   be   entered   into   this   field.   Its   definite   structure   can   be   defined   freely   in
projects   and   in   dependence   on   the   target   application.
Further   determinations   concerning   the   data   sets,   their   data   types   and   field   lengths   can   be   found
in   the   OCD   specification   4.3.
3

2
The   additional   tables
2.1
The   series   tables
Table   name:   Programs
Obligatory   table:   yes
File   name:   xocd_programs.csv
Nr.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
X
Serial   key
2.
Program_ID
Char
X
Sales   productline   key
3.
Label
Char
X
Series   designation
4.
TransferFilterTag
Char
Tag   for   export   filter   evaluation
Remarks:
•   Serial   Key
–   The   serial   key   ( Program )   defines   the   OFML   package   in   which   the   data   is   distributed.
–   The   value   must   only   consist   of   alphanumeric   characters. 1   The   first   character   has   to   be
a   letter:   [a-z][a-z0-9]*
–   Reserved   keywords   of   the   OFML   programming   language   are   not   allowed:
abstract
break
case
catch
class
continue
default
do
else
final
finally
for
foreach
func
goto
if
import
instanceof
native
operator
package
private
protected
public
return
rule
self
static
super
switch
throw
transient
try
var
while
–   Reserved   keywords   of   the   Windows   files   systems   are   not   allowed:
con
prn
aux
nul
com1
com2
com3
com4
com5
com6
com7
com8
com9
lpt1
lpt2
lpt3
lpt4
lpt5
lpt6
lpt7
lpt8
lpt9
•   Sales   productline   key
–   This key is used for logical identification of the sales product line of articles in all OFML
packages   of   a   manufacturer.
–   The value should only consist of upper-case letters, digits and underscores:   [A-Z0-9_]+
Other   special   characters   should   not   be   used.
–   The   sales   productline   key   ( Program_ID )   in   the   series   table   is   only   used   as   a   default
value   for   articles   in   the   OFML   package.   Nevertheless,   the   explicit   com.   serial   keys   are
assigned   to   articles   in   the   Article   table   (3.1).
•   An   optional   designation   of   the   key   is   intended   in   this   and   the   two   following   tables.   This   is
done   by   a   direct   text   in   a   chosen   language.   Thus,   no   multilingualism   is   intended   here.
•   The   values   in   field   Label   have   to   be   unique.
1 For   reasons   of   compatibility   with   existing   data,   the   serial   key   ( Program )   may   contain   upper-case   letters   and
underscores.   Anyway   it   is   highly   recommended   to   use   only   lower-case   letters   and   digits.
4

2.2
The   price   list   table
Table   name:   PriceLists
Obligatory   table:   yes
File   name:   xocd_pricelists.csv
Nr.
Name
Key
Type
Length
Required
Description
1.
PriceList
X
Char
X
Price   list   key
2.
Label
Char
X
Price   list   designation
Remarks:
•   The   values   in   field   Label   have   to   be   unique.
2.3
The   text   category   table
Table   name:   TextCategories
Obligatory   table:   yes
File   name:   xocd_textcategories.csv
Nr.
Name
Key
Type
Length
Required
Description
1.
TextCategory
X
Char
X
Text   category   key
2.
Label
Char
X
Designation   of   the   text   category
Remarks:
•   The   values   in   field   Label   have   to   be   unique.
5

3
The   extended   tables
3.1
The   article   table
Table   name:   Article
Obligatory   table:   yes
File   name:   xocd_article.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
TransferFilterTag
Char
Tag   for   export   filter   evaluation
3.
ArticleID
X
Char
80
X
Base   article   number
1.
4.
ArticleType
Char
1
X
Article   type:
P   -   plain
(not   configurable)
C   -   configurable
2.
5.
ManufacturerID
Char
16
X
Sales   manufacturer   key
3.
6.
SeriesID
Char
16
X
Sales   productline   key
4.
7.
ShortTextID
Char
80
X
Short   text   number
5.
8.
LongTextID
Char
80
Long   text   number
6.
9.
RelObjID
Num
X
Relational   object   number
(0   =   no   relational   object)
7.
10.
Discountable
Bool
1
X
Purchase   prices   discountable?
9.
11.
OrderUnit
Char
3
Order   Unit:
C62
-   Piece
MTR   -   Meter
MTK   -   Square   meter
(UN/ECE   Recommendation   20)
10.
12.
SchemeID
Char
30
Identifier   of   the   codification
scheme   of   final   article   number
11.
Remarks:
•   Sales   manufacturer   key
–   The  ManufacturerID  identifies the manufacturer of the articles in OFML environments.
–   The unique values are centrally registered.   Please get in touch with your contact person
at   EasternGraphics   GmbH,   if   you   do   not   know   the   sales   ManufacturerID ,   yet.
•   Sales   productline   key
–   This   key   is   used   for   logical   identification   of   the   sales   product   line   of   the   article   in
all   OFML   packages   of   a   manufacturer.   Alternatively,   it   can   be   interpreted   as   a   sales
product   group.
–   The value should only consist of upper-case letters, digits and underscores:   [A-Z0-9_]+
Other   special   characters   should   not   be   used.
–   Reserved   keywords   of   the   OFML   programming   language   are   not   allowed
(see   series   table   2.1).
–   Reserved   keywords   of   the   Windows   files   systems   are   not   allowed   (see   series   table   2.1).
6

3.2
The   property   class   table
Table   name:   PropertyClass
Obligatory   table:   yes 3
File   name:   xocd_propertyclass.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
ArticleID
X
Char
80
X
Base   article   number
1.
3.
Position
Num
X
Position   of   the   property   class
2.
4.
Name
X
Char
50
X
Identifier   of   the   property   class
3.
5.
TextID
Char
50
Text   number
4.
6.
RelObjID
Num
X
Relational   object   number
(0   =   no   relational   object)
5.
3 This   table   can   be   omitted,   if   the   data   contains   only   plain   not   configurable   articles.
7

3.3
The   property   table
Table   name:   Property
Obligatory   table:   yes 5
File   name:   xocd_property.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
PropertyClass
X
Char
50
X
Identifier   of   the   property
class
1.
3.
PropertyName
X
Char
50
X
Identifier   of   the   property
2.
4.
Position
Num
X
Position   of   the   property
3.
5.
TextID
Char
80
Text   number
4.
6.
RelObjID
Num
X
Relational   object   number
(0   =   no   relational   object))
5.
7.
Type
Char
1
X
Data   type   of   values:
C   -   Char
N   -   Num
L   -   Length   (m)
T   -   Text   (multiline   input)
6.
8.
Digits
Num
X
Number   of   digits   (total)
7.
9.
DecDigits
Num
X
Number   of   decimal   digits
8.
10.
Obligatory
Bool
1
X
Entry   obligatory?
9.
11.
AddValues
Bool
1
X
Entry   of   additional   values
allowed?
10.
12.
Restrictable
Bool
1
X
Value   range   restrictable
using   constraints?
11.
13.
MultiOption
Bool
1
X
Multiple   values   selectable?
12.
14.
Scope
Char
2
X
Scope:
C
-   configurable
RV   -   visible/not   editable
RG   -   internal
(graphic   relevant)
R
-   internal
13.
15.
TxtControl
Num
X
Text   control   code
14.
16.
HintTextID
Char
80
Number   of   hint   text
15.
5 This   table   can   be   omitted,   if   the   data   contains   only   plain   not   configurable   articles.
8

3.4
The   article   base   table
Table   name:   Artbase
Obligatory   table:   no
File   name:   xocd_artbase.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
TransferFilterTag
Char
Tag   for   export   filter   evaluation
3.
ArticleID
X
Char
80
X
Base   article   number
1.
4.
PropertyClass
X
Char
50
X
Identifier   of   the   property   class
2.
5.
PropertyName
X
Char
50
X
Identifier   of   the   property
3.
6.
PropertyValue
X
Char
30
X
Property   value
4.
3.5
The   property   value   table
Table   name:   PropertyValue
Obligatory   table:   yes 7
File   name:   xocd_propertyvalue.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
TransferFilterTag
Char
Tag   for   export   filter   evaluation
3.
PropertyClass
X
Char
50
X
Identifier   of   the   property   class
1.
4.
PropertyName
X
Char
50
X
Identifier   of   the   property
2.
5.
Position
Num
X
Position   of   the   property   value
3.
6.
TextID
Char
80
Text   number
4.
7.
RelObjID
Num
X
Relational   object   number
(0   =   no   relational   object)
5.
8.
IsDefault
Bool
1
X
Proposal   value?
6.
9.
SuppressText
Bool
1
X
Suppress   printing   the   text?
7.
10.
OpFrom
X
Char
2
X
Operator   from
8.
11.
ValueFrom
X
Char
30
X
Property   value   from
9.
12.
OpTo
X
Char
2
Operator   to)
10.
13.
ValueTo
X
Char
30
Property   value   to
11.
14.
Raster
X
Char
30
Step   range   of   an   interval
12.
15.
DateFrom
Date
8
Valid   from
13.
16.
DateTo
Date
8
Valid   to
14.
7 This   table   can   be   omitted,   if   the   data   contains   only   plain   not   configurable   articles.
9

3.6
Property   groups
Table   name:   Article2PropGroup
Obligatory   table:   no
File   name:   xocd_article2propgroup.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
ArticleID
X
Char
80
X
Base   article   code
1.
3.
Position
Int
X
Position   of   the   property   group
2.
4.
PropGroupID
X
Char
50
X
Id   of   the   property   group   in   table
PropertyGroup
3.
5.
TextID
Char
80
Label/Title   of   the   property
group.   Text   number   in
description   table
PropGroupText   (3.16))
4.
Remarks:
•   In   this   table   one   or   more   property   groups   can   be   assigned   to   articles.
•   The   field   Program   must   contain   a   serial   key.   The   wildcard   value   *   is   not   allowed   in   table
Article2PropGroup .
Table   name:   PropertyGroup
Obligatory   table:   no
File   name:   xocd_propertygroup.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
PropGroupID
X
Char
50
X
Id   of   the   property   group
1.
3.
Position
Int
X
Position   of   the   property   in   the
group
2.
4.
PropertyClass
X
Char
50
X
Identifier   of   the   property   class
(3.3)
3.
5.
PropertyName
X
Char
50
X
Identifier   of   the   property   (3.3)
4.
Remarks:
•   This   table   defines   the   properties   of   the   property   groups.
•   In   field   Program   the   wildcard   value   *   defines   a   product   line   independent   property   group.
•   In field  PropertyClass  the wildcard value  *  can be used instead of the identifier of an existing
property   class.   In   this   case   a   visible   property   from   any   of   the   article’s   property   classes   with
the   name   from   field   PropertyName   is   shown.   Please   note:   The   names   of   all   properties   must
be   unique   over   all   the   article’s   property   classes. 8
8 see   Further   remarks   of   the   Property   table   in   OCD   specification.
10

3.7
The   relational   object   table
Table   name:   RelationObj
Obligatory   table:   yes 10
File   name:   xocd_relationobj.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
RelObjID
X
Num
X
Relational   object   number   ( >  0 )
1.
3.
Position
Num
X
Position   of   the   relation
2.
4.
RelName
X
Char
80
X
Identifier   of   the   relation
3.
5.
Type
X
Char
1
X
Type   of   the   relation:
1   -   Pre-condition
2   -   Selection   condition
3   -   Action
4   -   Constraint
5   -   Reaction
6   -   Post-Reaction
4.
6.
Domain
X
Char
4
X
Domain:
C
-   Configuration
P
-   Price   relation
PCKG   -   Packaging   relation
TAX
-   Taxation
5.
3.8
The   relational   knowledge   table
Table   name:   Relation
Obligatory   table:   yes 12
File   name:   xocd_relation.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
RelationName
X
Char
80
X
Identifier   of   the   relation
1.
3.
BlockNr
X
Num
X
Code   block   number/line   number
2.
4.
CodeBlock
Char
255
X
Code   block
3.
3.9
Value   combination   tables
The   value   combination   tables   are   taken   over   from   OCD   without   any   modification.   However,   the
file   name   must   be   preceded   with   the   respective   series   in   the   form   of   <Program>_ .
Globally usable tables are preceded with the sign  $  instead of the wildcard  * , because the wildcard
character   *   is   not   allowed   in   file   names.
10 This   table   can   be   omitted,   if   the   data   does   not   contain   any   logic   or   relational   knowledge.
12 This   table   can   be   omitted,   if   the   data   does   not   contain   any   logic   or   relational   knowledge.
11

3.10
The   price   table
Table   name:   Price
Obligatory   table:   yes 14
File   name:   xocd_price.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
PriceList
X
Char
32
X
Price   list   key
3.
ArticleID
X
Char
80
X
Base   article   number
1.
4.
Variantcondition
X
Char
80
Variant   condition
2.
5.
Type
X
Char
1
X
Price   type:
S   -   Sales   price
P   -   Purchase   price
3.
6.
Level
Char
1
X
Price   level:
B   -   Base   price
X   -   eXtra   charge   price
D   -   Discount
4.
7.
Rule
Char
1
Calculation   rule
5.
8.
TextID
Char
80
Text   number
6.
9.
PriceValue
Num
X
Price   /   amount
7.
10.
FixValue
Bool
1
X
Fix   amount   (vs.   percentage)?
8.
11.
Currency
X
Char
3
(X)
Currency   of   fix   amount
(ISO-4217)
9.
12.
DateFrom
X
Date
8
X
Valid   from
10.
13.
DateTo
X
Date
8
X
Valid   to
11.
14.
RoundingID
Char
50
Identifier   of   a   rounding   rule
13.
Remarks:
•   Using   the   wildcard   ( * )   for   field   ArticleID   indicates   an   eXtra   charge   price   or   discount   as
article   independent.   These   prices   are   used   by   all   articles   in   an   OFML   package.   A   variant
condition   has   to   be   specified   for   article   independent   prices.   An   empty   string   is   not   allowed
as   variant   condition   in   this   case.
•   An   article   independent   price   can   also   be   defined   as   program   independent   by   applying   a
wildcard   ( * )   as   serial   key.
•   Base   prices   can   neither   be   article   nor   program   independent.
14 This   table   can   be   omitted,   if   the   data   is   provided   without   any   prices.
12

3.11
The   rounding   rule   table
Table   name:   Rounding
Obligatory   table:   no
File   name:   xocd_rounding.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
RoundingID
X
Char
50
X
Identifier   of   the   rounding   rule
1.
3.
Number
X
Num
X
Position   of   the   rounding
2.
4.
Minimum
Num
Least   value   to   be   rounded
3.
5.
Maximum
Num
Greatest   value   to   be   rounded
4.
6.
Type
Char
4
X
Rounding   method:
DOWN   -   round   down
UP
-   round   up
COM
-   commercial   rounding
ECOM   -   round   to   even
(banker’s   rounding)
5.
7.
Precision
Num
X
Rounding   precision
6.
8.
AddBefore
Num
X
Value   added   before   rounding
7.
9.
AddAfter
Num
X
Value   added   after   rounding
8.
13

3.12
The   taxation   scheme   tables
Table   name:   ArticleTaxes
Obligatory   table:   no
File   name:   xocd_articletaxes.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
ArticleID
X
Char
80
X
Base   article   number
1.
3.
TaxID
X
Char
50
X
Identifier   of   the   taxation   scheme
2.
4.
DateFrom
Date
8
Valid   from
3.
5.
DateTo
Date
8
Valid   to
4.
Table   name:   TaxScheme
Obligatory   table:   no
File   name:   xocd_taxscheme.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
TaxID
X
Char
50
X
Identifier   of   the   tax   scheme
1.
3.
Country
X
Char
2
X
Country   code   (ISO-3166-1)
2.
4.
Region
X
Char
3
Region   code   (ISO-3166-2)
3.
5.
Number
Num
X
Position   in   evaluation
sequence
4.
6.
TaxType
X
Char
8
X
Identifier   of   the   tax   type
5.
7.
TaxCategory
Char
24
X
Identifier   of   the   tax   category
6.
Remarks:
•   Valid   tax   type   and   tax   categories   are   documented   in   OCD   Specification   4.3   Appendix   H   -
Tax   Types   and   Tax   Categories
14

3.13
The   code   scheme   table
Table   name:   CodeScheme
Obligatory   table:   no
File   name:   xocd_codescheme.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
SchemeID
X
Char
30
X
Identifier   of   the   scheme
1.
3.
Scheme
Char
Description   of   the   scheme
2.
4.
VarCodeSep
Char
12
Character   string   to   separate   base
article   number   and   variant   code
3.
5.
ValueSep
Char
12
Character   string   to   separate
property   values
4.
6.
Visibility
Char
1
Visibility   of   properties   in   variant
code
0   -   only   currently   valid   and   visible
1   -   any   configurable
5.
7.
InVisibleChar
Char
1
Replacement   character   for   invalid
or   invisible   properties
6.
8.
UnselectChar
Char
1
Replacement   character   for
unselected   optional   or   restrictable
properties
7.
9.
Trim
Bool
1
X
Trim   property   values?
8.
10.
MO_Sep
Char
12
Character   string   to   separate   values
of   multivalued   properties
9.
11.
MO_Bracket
Char
24
Characters   for   brackets   around
multivalued   properties   ( 2  ∗ N )
10.
15

3.14
The   packaging   table
Table   name:   Packaging
Obligatory   table:   no
File   name:   xocd_packaging.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
ArticleID
X
Char
80
X
Base   article   number
1.
3.
Variantcondition
X
Char
80
Variant   condition
2.
4.
Width
Num
Width   of   the   packaging   unit
3.
5.
Height
Num
Height   of   the   packaging   unit
4.
6.
Depth
Num
Depth   of   the   packaging   unit
5.
7.
MeasureUnit
Char
3
(X)
Unit   of   measurement   of
dimensions   4   to   6
6.
8.
Volume
Num
Volume   of   the   packaging   unit
7.
9.
VolumeUnit
Char
3
(X)
Unit   of   measurement   of   the
volume
8.
10.
TaraWeight
Num
Weight   of   the   packaging   unit
9.
11.
NetWeight
Num
Weight   of   the   individual
article
10.
12.
WeightUnit
Char
3
(X)
Unit   of   measurement   of   the
weights   10   bis   11
11.
13.
ItemsPerUnit
Num
Number   of   articles   per
packaging   unit
12.
14.
PackUnits
Num
Number   of   packaging   units,
which   are   used   for   the   article
13.
Remarks:
•   Article   independent   packaging   data   records   can   be   defined   using   the   wildcard   ( * )   as   article
number.   Article   independent   packaging   data   is   used   by   all   articles   in   an   OFML   package.
A   variant   condition   has   to   be   specified   for   article   independent   packaging   data.   An   empty
string   is   not   allowed   as   variant   condition   in   this   case.
•   Article independent packaging data can also be defined as program independent by applying
a   wildcard   ( * )   as   serial   key.
•   The   valid   values   to   define   units   of   measurements   of   dimensions,   volume   and   weights   are
defined   in   OCD   specification.   These   values   correspond   to   the   Common   Code   of   UN/ECE
Recommendation   20. 15 .
•   Unit   of   measurements   have   to   be   specified   in   a   record,   if   it   contains   the   according   measured
values.
15 www.unece.org/cefact/rec/rec20en.htm
16

3.15
The   classification   table
Table   name:   Classification
Obligatory   table:   no
File   name:   xocd_classification.csv
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
ArticleID
X
Char
80
X
Base   article   number
1.
3.
System
X
Char
32
X
Name   of   the   classification
system
2.
4.
ClassID
Char
64
X
ID   of   the   class   of   the   article
3.
Remarks:
•   Each   article   can   by   classified   using   multiple   different   classifications   systems.
•   Currently   the   following   classification   systems   are   allowed:
System
Explanation
ECLASS- x.y
Classification according to the eClass Model with indication of the version.
The   suffix   x.y   has   to   be   replaced   by   the   used   eClass   Major.Minor   version:
e.g.   ECLASS-12.0
UNSPSC
Classification   according   to   the   standard   UN/SPSC
17

3.16
The   description   tables
All   text   tables   (see   OCD   description)   have   the   same   structure:
No.
Name
Key
Type
Length
Required
Description
1.
Program
X
Char
32
X
Serial   key
2.
TextCat
X
Char
1
X
Text   category   key
3.
TextID
X
Char
80
X
Text   number
1.
4.
Language
X
Char
2
X
Language   (ISO   639-1)
2.
5.
LineNr
X
Num
X
Line   number
3.
6.
TextLine
Char
80
X
Text   line
5.
Following   description   tables   are   supported:
•   Article   short   texts:   xocd_artshorttext.csv
•   Article   long   texts:   xocd_artlongtext.csv
•   Property   class   names:   xocd_propclasstext.csv
•   Property   names:   xocd_propertytext.csv
•   Property   value   names:   xocd_propvaluetext.csv
•   Property   group   names:   xocd_propgrouptext.csv
•   Price   texts:   xocd_pricetext.csv
•   User   messages:   xocd_usermessage.csv
3.17
The   version   information   table
Table   name:   Version
Obligatory   table:   no
File   name:   xocd_version.csv
The   version   information   table   corresponds   exactly   to   the   OCD   table   of   the   same   name.
18

Modification   history
Version   4.3.2
•   Clarification:   Section description tables includes a list of supported tables / filenames (3.16).
•   Clarification:   Section   series   table   describes   the   restrictions   in   OFML   for   valid   productline
keys   in   more   detail   (2.1).
•   Clarification:   Section article table describes the restrictions in OFML for valid manufacturer
and   productline   keys   in   more   detail   (3.1).
Version   4.3.1
•   New:   Includes   the   classification   table   xocd_classification.csv   (3.15).
Version   4.3
•   New   features   introduced   with   OCD   4.3
–   New:   New   optional   Property   Groups   can   be   used   to   define   a   new   view   /   order   of
properties   for   each   article   (3.6).
–   New:   Relations of the relation object domain  TAX  can calculate a tax category depending
on   the   specific   article   variants   (3.7).
–   Changed:   Language   definition   value   SAP_LOVC   replaces   former   values   SAP_3_1   and
SAP_4_6   in   version   information   table   (3.17).
•   Max.   length   of   property   class   names   increased   from   30   to   max.   50   characters   (3.3,   3.2,   3.4,
3.5).
Version   4.2
•   New Fields  DateFrom ,  DateTo  in property value table to define an optional period of validity.
Version   4.1
•   General:   Update   according   new   features   introduced   with   OCD   4.1
•   Relation   object   table:   New   relation   type   Post-Reaction
•   Property   table:   New   property   type   “ T ”   allowing   users   to   enter   multiline   text
•   Packaging   table:   Supports   article   and   OFML   package   independent   packaging   data
•   Packaging   table:   More   precise   specification   regarding   the   variant   condition   and   units   of
measurements
•   Price   table:   More   precise   specification   regarding   the   variant   condition
•   Taxation   scheme   table:   A   reference   to   OCD   specification   where   tax   types   and   categories
added
19

Version   4.0.2
•   New   table:   Packaging
•   New   relation   domain:   PCKG
•   Refinements   of   tables:   file   names,   obligation
•   Subsections   reorder   to   keep   logical   coherent   tables   together.
Version   4.0.1
•   Refinement:   Maximum   lengths   of   fields.
•   Refinement:   The   column   Key   represents   the   Primary   Key   of   a   data   table.
Version   4.0
•   General:   Update   according   new   features   introduced   with   OCD   4.0
•   General:   Support for information for market specific filtering of product lines,   articles,   prop-
erty   values   and   article   base
•   New   Tables:   Rounding ,   ArticleTaxes   und   TaxScheme
•   Table   CodeScheme :   new   fields   MO_Sep ,   MO_Bracket
•   Table   RelationObj :   new   fields   Position
•   Table   PropertyValue :   new   fields   TransferFilterTag ,   Raster
•   Table   ArtBase :   new   fields   TransferFilterTag
•   Table   Property :   new   fields   MultiOption ,   HintText
•   Table   Article :   new   fields   TransferFilterTag ,   Discountable
•   Table   Article :   field   FastSupply   removed
•   Table   Programs :   new   field   TransferFilterTag
•   Tables   removed:   Identification ,   Classification ,   ClassificationData ,   Packaging   and
Set
Version   3.0.1
•   Table   Price :   Wildcard   entries   ( * )   for   field   Program   and   ArticleID   refined.
Version   3.0
Formal   update   according   to   OCD   3.0
20

Version   2.1.2
Incompatible   extension
•   Table   Programs :   renaming   of   the   obligatory   field   CProgram   to   Program_ID .
•   General:   precision   of   the   applicability   of   the   wildcard   entries
Version   2.1.1
Incompatible   extension
•   Table   Programs :   new   obligatory   field.
•   Wildcard   entries   ( * )   for   field   Program   in   the   corresponding   tables   possible.
Version   2.1(.0)
Initial   release
21
