# Application Notes (2025-11-25)

> AN-2014-04: Supported OCD Features
> This Application Note provides an overview of the supported OCD features in the last 5 releases of the main
> applications of EasternGraphics (section 1) and provides a more detailed look back at the history of the exten-
> sions resp. changes from the releases in spring 2012 (section 2).
> This application note refers to the so-called native OCD implementation, which is realized in module EAI. In the
> series registry files this corresponds to the class ::ofml::xoi:: xOiNativeOCDProductDB* for key productdb.
> In this document, the following abbreviations are used for the applications:
> P-PL pCon.planner
> P-CF pCon.configurator (last version 5.9.4, Nov. 2023)
> P-BK pCon.basket
> EAIWS EAI Web Service (base for online apps)
> The individual online apps are not mentioned separately. For these apps usually applies the information on the
> previous releases of the offline applications resp. on the used version of the EAIWS.
> Legal remarks
> © 2025 EasternGraphics GmbH | Albert-Einstein-Straße 1 | 98693 Ilmenau | GERMANY
> This work (whether as text, file, book or in other form) is copyright. All rights are reserved by
> EasternGraphics GmbH. Translation, reproduction or distribution of the whole or parts thereof is permitted only
> with the prior agreement in writing of EasternGraphics GmbH.
> EasternGraphics GmbH accepts no liability for the completeness, freedom from errors, topicality or continuity of
> this work or for its suitability to the intended purposes of the user. All liability except in the case of malicious
> intent, gross negligence or harm to life and limb is excluded.
> All names or descriptions contained in this work may be the trademarks of the relevant copyright owner and as
> such legally protected. The fact that such trademarks appear in this work entitles no-one to assume that they are
> for the free use of all and sundry.
> © 2025 EasternGraphics GmbH AN-2014-04: Supported OCD-Features 1/5

# 1 Tabular overview

The plus or minus sign in the line of the format version specifies whether the format version is generally supported in the corresponding release or not. In the lines below, the OCD features from the format version are listed that are not yet sup- ported 1 . There, a plus sign means that the feature is supported as of the corresponding release. (A number in parentheses denotes a conditional support, for details see below the table.)

|  |  |  | P-CF 5.9.4 P-PL 8.9 P-BK 1.13.10 EAIWS 4.14 (EAI 1.32) Nov. 2023 |  |  | P-PL 8.10 P-BK 1.14.0 EAIWS 4.15 (EAI 1.33) June 2024 |  |  | P-PL 8.11 P-BK 1.14.1 EAIWS 4.16 (EAI 1.33.2) Nov. 2024 |  |  | P-PL 8.12 P-BK 1.14.2 EAIWS 4.17 (EAI 1.34.1) May 2025 |  | P-PL 8.13 P-BK 1.14.3 EAIWS 4.18 (EAI 1.34.1) Nov. 2025 |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  | OCD 2.1 |  |  | + |  |  | + |  |  | + |  |  | + |  | + |  |
| identification tables |  |  | - |  |  | - |  |  | - |  |  | - |  | - |  |  |
| classification tables |  |  | + |  |  | + |  |  | + |  |  | + |  | + |  |  |
| packaging table |  |  | (1) |  |  | (1) |  |  | (1) |  |  | (1) |  | (1) |  |  |
| alternative text tables |  |  | - |  |  | - |  |  | - |  |  | - |  | - |  |  |
| fast supply counter |  |  | - |  |  | - |  |  | - |  |  | - |  | - |  |  |
|  | OCD 3.0 |  |  | - |  |  | - |  |  | - |  |  | - |  | - |  |
| scale prices |  |  | - |  |  | - |  |  | - |  |  | - |  | - |  |  |
| multivalued properties |  |  | (4) |  |  | (4) |  |  | (4) |  |  | (4) |  | (4) |  |  |
| composite articles |  |  | - |  |  | - |  |  | - |  |  | - |  | - |  |  |
|  | OCD 4.0 |  |  | + |  |  | + |  |  | + |  |  | + |  | + |  |
| controlling the discountability |  |  | (3) |  |  | (3) |  |  | (3) |  |  | (3) |  | (3) |  |  |
| hints for properties |  |  | - |  |  | - |  |  | - |  |  | - |  | - |  |  |
| several valid interval values for a property at the same time |  |  | (2) |  |  | (2) |  |  | (2) |  |  | (2) |  | (2) |  |  |
| text formatting codes |  |  | - |  |  | - |  |  | - |  |  | - |  | - |  |  |
|  | OCD 4.1 |  |  | + |  |  | + |  |  | + |  |  | + |  | + |  |
|  | OCD 4.2 |  |  | + |  |  | + |  |  | + |  |  | + |  | + |  |
|  | OCD 4.3 |  |  | + |  |  | + |  |  | + |  |  | + |  | + |  |
|  | OCD 5.0 |  |  | - |  |  | - |  |  | - |  |  | - |  | - |  |

(1) The packaging table is supported/used only in P-BK as part of the calculation of EcoTax -France (deter- mination of weight). (2) Due to the limitations of the property editors, several simultaneously valid interval values for a property are combined into an overall interval. (3) Non-discountable articles (field Discountable in the article table) are supported in P-BK if a purchase price is provided. (4) Only properties of scope R and only in format version 4.3. 1 The features are filed under that OCD format version, in which they were introduced. However, the statement about the support of a feature is true also for higher format versions, in which the feature (still) is contained/specified. © 2025 EasternGraphics GmbH AN-2014-04: Supported OCD-Features 2/5

# 2 History of added or changed features

P-PL 8.13, P-BK 1.14.3, EAIWS 4.18 (EAI 1.34.1), November 2025 :

- No enhancements/changes with respect to OCD processing. P-PL 8.12, P-BK 1.14.2, EAIWS 4.17 (EAI 1.34.1), May 2025 :

- No enhancements/changes with respect to OCD processing. P-PL 8.11, P-BK 1.14.1, EAIWS 4.16 (EAI 1.33.2), November 2024 : The new flag with value 8 for option @RelEvalOptimization now can be used to specify that after a property change only the restrictable properties should be reset that follow the changed property. P-PL 8.10, P-BK 1.14.0, EAIWS 4.15 (EAI 1.33), June 2024 :

- No enhancements/changes with respect to OCD processing. P- CF 5.9.4, P-PL 8.9, P-BK 1.13.10, EAIWS 4.14 (EAI 1.32), November 2023 :

- Option @UnfixPreselectedChoiceList in control data table epdfproductdb.csv now can be used to specify whether the set of values shown to the user should be "frozen" during automatic value pre- assignment of restrictable properties (for more details see Application Note AN-2006-01). P- CF 5.9.3, P-PL 8.8.1, P-BK 1.13.9, EAIWS 4.13 (EAI 1.31.2), May 2023 : Improved handling of violated constraints during the pre-selection of restrictable properties. P- CF 5.9.2, P-PL 8.8, P-BK 1.13.8, EAIWS 4.12 (EAI 1.31), November 2022 :

- Classification data is now supported. The data is not used in the applications themselves, but it is stored in the basket (OBX) and can thus be evaluated in third-party systems. P- CF 5.9.1, P-PL 8.7, P-BK 1.13.7, EAIWS 4.11 (EAI 1.30.4), April 2022 :

- No enhancements/changes with respect to OCD processing. P- CF 5.9, P-PL 8.6, P-BK 1.13.6, EAIWS 4.10 (EAI 1.30), November 2021 : Using option @UnlockBackwardRestriction in control data table epdfproductdb.csv , the behavior when evaluating relationships with backward dependencies now can be modified (for more details and information see Application Note AN-2006-01). P-PL/CF 5.8.14, P-PL 8.5, P-BK 1.13.5, EAIWS 4.9.1 (EAI 1.29), May 2021 :

- In format version 4.3 multivalued properties of scope R now are supported. P-PL/CF 5.8.13, P-PL 8.4, P-BK 1.13.4, EAIWS 4.8 (EAI 1.28), November 2020 :

- The new format version 4.3 now is supported. P-PL/CF 5.8.12, P-PL 8.3, P-BK 1.13.3 (EAI 1.27), April 2020 :

- No enhancements/changes with respect to OCD processing. P-PL/CF 5.8.11u1, P-PL 8.2u1, P-BK 1.13 (EAI 1.26.4), November 2019 :

- Changed behavior when handling the SAP language construct set_default , which is not officially sup- ported by the OCD specification. (For details see Application Note AN-2019-01). © 2025 EasternGraphics GmbH AN-2014-04: Supported OCD-Features 3/5

- Unofficially (i.e. in addition to the OCD specification), now are supported post reactions of articles and the Boolean constant TRUE. P-PL/CF 5.8.10, P-PL 8, P-BK 1.12.1 (EAI 1.24), November 2018 :

- The new format version 4.2 now is supported. P-PL/CF 5.8.9p1, P-PL 7.7p2 (EAI 1.23.3), June 2018 ( P-BK 1.12.1 , Nov. 2018) :

- In relations of type Action , Reaction and Post-Reaction now proprietary, i.e. not (yet) standardized func- tion SET_CHECK_RELEVANCE(<property>, <logical expression>) can be used: If the logical expression yields true , the specified property is marked as check-relevant , i.e., the property has to be checked by the recipient of an order confirmation 2 , even if the property is not visible to the user of an OFML appli- cation via function SET_VISIBILITY() . The mark can be retrieved via the ECOM interface from the P-BK using function GetAllArticleFeatures() (and thus be written to the corresponding element of the order confirmation document). P-PL/CF 5.8.8, P-PL 7.6, P-BK 1.12 (EAI 1.22), October 2017 :

- No enhancements/changes with respect to OCD processing. P-PL/CF 5.8.7, P-PL 7.5, P-BK 1.11.2 (EAI 1.21.4), April 2017 :

- No enhancements/changes with respect to OCD processing. P-PL/CF 5.8.6, P-PL 7.4, P-BK 1.11.1 (EAI 1.21), December 2016 :

- Function SET_VISIBILITY(), specified in OCD 5.0, already is implemented and can be used in currently supported older format versions, too.

- With the option @AllowConsecValsInTrimmedCode in control data table epdfproductdb.csv , a special method can be activated for processing end article numbers with a user defined coding scheme including successive properties (without separator) where the trimming flag is set. (With the standard procedure, an article configuration cannot be completely restored by means of such end article num- bers.) P-PL/CF 5.8.5, P-PL 7.3, P-BK 1.11 (EAI 1.20), June/July 2016 :

- Non-discountable articles (field Discountable in table Article ) now are supported in P-BK if a purchase price is provided. P-PL/CF 5.8.4, P-PL 7.2, P-BK 1.10.4 (EAI 1.19), Oct./Nov. 2015 :

- No enhancements/changes with respect to OCD processing. P-PL/CF 5.8.3, P-PL 7.1, P-BK 1.10.3 (EAI 1.18), April/May 2015 :

- No enhancements/changes with respect to OCD processing. P-PL/CF 5.8.2, P-PL 7.0, P-BK 1.10.2 (EAI 1.17), November 2014 :

- In SAP language sets now operator || for string concatenation is supported. P-PL/CF 5.8.1, P-PL 6.8, P-BK 1.10.1 (EAI 1.16), March 2014 :

- The new format version 4.1 now is supported. 2 See document type ORDRSP in OFML standard for Business Data Exchange (OEX). © 2025 EasternGraphics GmbH AN-2014-04: Supported OCD-Features 4/5

P-PL/CF 5.8, P-PL 6.7, P-BK 1.10 (EAI 1.15), October 2013 :

- The packaging table now is supported; however, on the side of the application only in pCon.basket dur- ing calculation of EcoTax-France (determining the weight).

- Several simultaneously valid interval values for a property now are supported, but combined into an overall interval due to limitations in the property editors.

- The behavior with respect to properties, which are declared as optional and for which there are values specified in the article base table, now can be controlled using the option @OptPropsWithBaseValues in the control data table epdfproductdb.csv (see Application Note on control data tables) 3 . P-PL/CF 5.7.4, P-PL 6.6, P-BK 1.9 (EAI 1.14), April 2013 :

- The behavior with respect to SAP language construct set_default , which officially is not supported in OCD, now can be controlled using the option @SetDefaultMode in the control data table epdfproductdb.csv (see Application Note on control data tables). P-PL/CF 5.7.2, P-PL 6.4.1, P-BK 1.8.2 (EAI 1.12), April 2012 :

- The special variable $BAN referring to the base article number now is supported as actual parameter in table calls. 3 The OCD specification contains no clear instructions how to handle this situation. © 2025 EasternGraphics GmbH AN-2014-04: Supported OCD-Features 5/5