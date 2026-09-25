# AN-2017-01_PriceLists_DataCreation-EN

> Auto-generated from AN-2017-01_PriceLists_DataCreation-EN.pdf for AI consumption.

---


<!-- Page 1 -->

# Application Notes

# (2025-04-24)

# AN-2017-01: Notes on Data Creation Regarding Multiple Price Lists

# Contents

1 Introduction .................................................................................................................................................... 2
2 (Possible) Changes in the OFML dataset ......................................................................................................... 3
2.1 An article no longer is available (valid) in the new price list ................................................................. 3
2.2 The new version of the dataset introduces a new article ..................................................................... 4
2.3 An older price list no longer is included in the dataset ......................................................................... 4
2.4 An (existing) article variant now is price-relevant with the new PL (extra charge) ............................... 4
2.5 An article variant no longer is price-relevant with the new price list .................................................... 4
2.6 An article variant no longer is valid in the new price list ....................................................................... 4
2.7 A new (price-relevant) article variant is introduced with new price list ............................................... 5
2.8 Conversion from article-specific to global price components for extra charges ................................... 5

Legal remarks

© 2017-2025 EasternGraphics GmbH | Albert-Einstein-Straße 1 | 98693 Ilmenau | GERMANY

This work (whether as text, file, book or in other form) is copyright. All rights are reserved by
EasternGraphics GmbH. Translation, reproduction or distribution of the whole or parts thereof is permitted only
with the prior agreement in writing of EasternGraphics GmbH.

EasternGraphics GmbH accepts no liability for the completeness, freedom from errors, topicality or continuity of
this work or for its suitability to the intended purposes of the user. All liability except in the case of malicious
intent, gross negligence or harm to life and limb is excluded.

All names or descriptions contained in this work may be the trademarks of the relevant copyright owner and as
such legally protected. The fact that such trademarks appear in this work entitles no-one to assume that they
are for the free use of all and sundry.

© 2025 EasternGraphics GmbH AN-2017-01: Data Creation Regarding Multiple Price Lists 1/6

<!-- Page 2 -->

# 1 Introduction

Starting with July 2016 the pCon applications support multiple price lists in a single OFML dataset based on the
price date:
In the OCD price table, multiple price lists are implemented by creating several table entries with different validity
periods for a given price component. At run time of the OFML application, during price calculation then the table
entry for the price component is used whose validity period corresponds to the price date specified by the user
1
for the given article (or the project) . If no suitable price list is found for the price date, the article has no price
2
and is marked as inconsistent ("invalid price date") . (For details on the price calculation, refer to the correspond-
ing section in the OCD specification.)
3
The document "Multiple Price Lists in the pCon World" describes the behavior in the applications from the user
perspective. This application note is addressed to data providers who want (have) to support multiple price lists
in a single dataset: it provides information on what must be observed in the case of changes in successive versions
of the OFML dataset with regard to multiple price lists.
The following scenario is considered (assumed): A newly provided version of the OFML dataset comes with a new
price list (PL). In addition, the dataset also contains the PL from the previous version (referred to as "old PL" in
this document). With this, a dealer can do the following:
1. If the new version is provided before the first validity date of the new PL, (s)he already can create and
process orders with reference to the new PL.
2. Orders which have not yet been completed can be processed further on the basis of the old PL (validity
of quote) 4 .
While it can be assumed that the new PL is consistent with the new data, certain changes in the data can lead to
conflicts when using the old PL. For this purpose, the types of changes most relevant in this respect are examined
in more detail below.
Regardless of this, the following shall apply in order to ensure validity of quotes: If an older PL is taken over into
the new dataset, no changes should be made to the relevant entries in the price table. There is an exception to
this rule: If the end date of the formerly current PL was not known when the old data was created and therefore
a date far in the future was specified, now it can or should be corrected 5 . For certain change scenarios (e.g. 2.1),
this even is required to avoid problems.
Due to the sensitive subject matter, it is assumed that the data creator, who is charged with the implementation
of Multiple price lists, is familiar with the pricing policy of the respective manufacturer, including the basic agree-
ments with his dealers.

1 or has the latest start date, in case there are multiple suitable table entries
2 The user then may (must) abolish this state by selecting another price list (i.e., setting another price date).
3 see http://help.pcon-planner.com/en/help/ under "Documents"
4 Depending on the manufacturer's basic agreements with its dealers and on the frequency of the publication of new price
lists, it may be necessary to include more than one old PL in the new data version in order to ensure validity of quotes.
5 Typically, the end date of the old PL will be set to the date before the first day of the validity period of the new PL.

© 2025 EasternGraphics GmbH AN-2017-01: Data Creation Regarding Multiple Price Lists 2/6

<!-- Page 3 -->

# 2 (Possible) Changes in the OFML dataset

## 2.1 An article no longer is available (valid) in the new price list

If multiple price lists would not have to be supported, one would simply remove the article completely from the
dataset. The article then could no longer be created (and ordered), and after loading a saved project created
with the predecessor version of the dataset the article could no longer be reconfigured and no change to another
(older) PL would be possible 6 .
If multiple price lists have to be supported, an article that is no longer valid in the new PL cannot be removed
from the dataset as long as the basic agreements permit dealers to order this article. The solution in this case
simply is to create no table entries for the article in the new PL. In addition, the end date of the table entries for
the old PL have to be corrected if necessary (see Introduction).
The article then can be reconfigured after loading (and updating) a stored older project based on the old price
list assigned at the time of storage, and the article can be inserted into a new project and easily used with the
old PL. However, when using the new PL the article is marked as inconsistent ("invalid price date")! This is an
indication for the user to change the price list if necessary.
This solution can be combined with the following changes in the catalog data and thus be modified:
1. The article is removed from the catalog structure table: Then, the article can no longer be inserted di-
rectly from the catalog view into a new project, only by means of article search or article number input.
2. The article is completely removed from the catalog data: Then, the article can no longer be inserted into
a new project, but a reconfiguration after loading a stored, older project still is possible.
Caution when using the OAS module in pCon.creator :
The dialog catalog entries has a function for synchronizing the catalog entries of type Article. This function has an
option that allows you to import articles from the OCD data into the article list of the catalog. This function imports
from selected commercial series all articles missing in the catalog. In this case, the articles which have already been
removed beforehand because they are invalid in the new PL are imported again!

Caution when using global, article-independent price components 7 :
If an extra charge for a particular variant of the no longer valid article is implemented via a global price compo-
nent, and if this price component is used in the new PL for still valid articles, this has the following effect if the
article is used with the new PL: though the approach described above ensures that no article-specific price com-
ponent will be found, however, the global surcharge is included in the price calculation, i.e., the article gets a
(incorrect) price! This can be avoided in either of the following two ways:
1. The global price component from the old PL is copied and created as an article-specific price component
for the no longer valid article, where a new identifier is used for the variant condition. In the relevant
OCD price relationship of the article, the name of the variant condition is changed accordingly 8 .
2. In the new PL the relevant price component no longer is created globally, but specifically for the rele-
vant, still valid articles.

6 The article is "frozen" with the price of the older PL allocated at the time of storage.
7 Article-independent price components are created by specifying the wildcard "*" in the article column.
8 If the price relationship is also used for other articles for which the change is not valid, an own price relationship may have
to be created for the article.

© 2025 EasternGraphics GmbH AN-2017-01: Data Creation Regarding Multiple Price Lists 3/6

<!-- Page 4 -->

## 2.2 The new version of the dataset introduces a new article

This is the opposite situation compared to 2.1. The implementation is uncomplicated: In the new PL supplied
with the new dataset corresponding table entries are included for the article, but not in the old PL still delivered
with the new dataset. The article can be inserted into a project and used with the new PL, but if used with an old
PL it is marked as inconsistent ("invalid price date")! This is an indication for the user to change the price list.

## 2.3 An older price list no longer is included in the dataset

After loading a saved, older project, articles saved with this older PL still have the stored price. If, however, they
are updated with the aim of reconfiguration while retaining the stored price date, they are marked as incon-
sistent ("invalid price date"), i.e., a change of the project based on the old PL is no longer possible!
Similar to 2.1, an older PL may not be removed as long as the basic agreements permit dealers to order articles
on the basis of this PL!

## 2.4 An (existing) article variant now is price-relevant with the new PL (extra charge)

This change is implemented by setting a corresponding variant condition for the variant in the OCD price rela-
tionships of the new dataset and creating a corresponding table entry for this variant condition in the new PL,
but not in older price lists that still are delivered with the new dataset.
When using an old PL, even though the (new) variant condition is also assigned if the given article variant is
present, no extra charge is added due to the missing table entry for this variant condition in the old PL. This is
the desired behavior in terms of the validity of quotes.

## 2.5 An article variant no longer is price-relevant with the new price list

This is the opposite situation compared to 2.4. Without taking into account multiple price lists, one would no
longer set a variant condition for the variant in the OCD price relationships of the new dataset, and, accordingly,
would not create a table entry in the new PL. However, with regard to the possible use of an old PL, which still is
delivered with the new dataset, this implementation is problematic: the (valid) price component still contained
in this PL will not be considered during calculation of the article price since the corresponding variant condition
no longer is set! This is particularly tricky since the lack of the extra charge probably is not noticed by the user
and then leads to a faulty offer!
Therefore, the solution considering multiple price lists is to leave the price logic with respect to the article variant
unchanged, and simply to not create a table entry for the variant condition in the new PL, as long as basic agree-
ments still require the support of older price lists in which this variant was price-relevant! In addition, the end
date of the table entry for the old PL has to be corrected if necessary (see Introduction).
If the surcharge has been implemented via a global price component, and if it is still required for other articles in
the new PL, further adjustments are required in the data, see section 2.1!

## 2.6 An article variant no longer is valid in the new price list

Without taking into account multiple price lists, one would implement this by removing the respective property
value or the relevant property from the OCD data. (If this was a price-relevant variant, the price logic for setting
the corresponding variant condition would be removed, too, and no table entry would be created for the variant
condition in the new PL).

© 2025 EasternGraphics GmbH AN-2017-01: Data Creation Regarding Multiple Price Lists 4/6

<!-- Page 5 -->

The consequences would be:

• The article variant in question no longer can be created (and ordered)!
• If a property has been removed, the article cannot be reconfigured after loading a saved project (is
"frozen") and it is not possible to switch to the new PL!
• If a value has been removed, the stored article configuration cannot be restored after loading. The arti-
cle either is "frozen" or a migration can be made (after what a price list change would be possible).

Similar to 2.1 and 2.3, such a change is not allowed, as long as the basic agreements permit the dealers to order
this article variant!
However, it is recommended to provide a corresponding hint in the text of the relevant property resp. property
value after the actual text, e.g. in the form "(obsolete)", "(till ...)" or the like.
If a property value is no longer valid, a validity period can be specified as of OCD 4.2 9 . Thus, the scenario consid-
ered here can be better covered by setting the To date of the value to one day before the start date of the new
price list.

## 2.7 A new (price-relevant) article variant is introduced with new price list

This change is implemented, beside of introducing the new property or the new property value, by setting a
corresponding variant condition for the new variant in the OCD price relationships of the new dataset and creat-
ing a corresponding table entry for this variant condition in the new PL, but not in older price lists that still are
delivered with the new dataset.
In terms of price determination, however, this is identical to case 2.4, where an already existing variant becomes
price-relevant with the new PL. Thus, the OCD implementation cannot distinguish these two cases without fur-
ther information! Current OCD implementation assumes case 2.4, i.e., when using an old PL, the (new) variant
condition is also assigned if the given article variant is present, but no extra charge is added due to the missing
table entry for this variant condition in the old PL. In case 2.4 this is the desired behavior due to the validity of
quotes, but not in the case considered here!
As of OCD 4.2 10 , there is a solution to this problem: a validity period can be specified for property values. Thus,
in the scenario considered here, the start date of the new property value or – in in the case of a new property –
of all price-relevant values of the new property have to be set to the start date of the new PL!

## 2.8 Conversion from article-specific to global price components for extra charges

For the sake of simplification of the data, in the new dataset surcharges no longer will be implemented by means
of article-specific price components, but by means of article-independent (global) price components.
Such a change is not possible with the OCD implementation in the current applications, taking into account
pCon
multiple price lists!
The reason for this is that the OCD implementation strictly keeps with the following regulation from the OCD
specification: “However, this article-independent table entry is taken into account only if there is no own, specific
11
entry with the same variant condition for the processed article.”

9 supported by the applications from November 2018
pCon
10 supported by the pCon applications from November 2018
11 This regulation applies up to and including OCD format version 4.3. The specification of format version 5.0, which is not yet
supported in the pCon applications, contains more sophisticated regulations regarding the processing of article-specific and
global price components, which allow such changes in the data.

© 2025 EasternGraphics GmbH AN-2017-01: Data Creation Regarding Multiple Price Lists 5/6

<!-- Page 6 -->

This regulation does not take into account multiple price lists. When using the new PL for an article with an extra
charge implemented via a global price component, this has the following effect: As there exists an article-specific
table entry in the old PL for the variant condition of the affected article variant, the article-independent table
entry is not considered, but the table entry for the old PL neither is applied due to the validity period. Hence, no
extra charge is determined for the affected article variant!

© 2025 EasternGraphics GmbH AN-2017-01: Data Creation Regarding Multiple Price Lists 6/6