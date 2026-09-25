# dsr-3.7_en

> Auto-generated from dsr-3.7_en.pdf for AI consumption.

---


<!-- Page 1 -->

# OFML Data Structure and Registration (DSR)

### Specificationversion3.7

### Editors: BerndHeinemann,StefanBleuel,ThomasGerth

### Copyright©1999-2024EasternGraphicsGmbH

### September12,2024

<!-- Page 2 -->

## Legaldisclaimer

## Copyright © 1999-2024 EasternGraphics GmbH. All rights reserved. This work is protected by copyright law.

## All rights are reserved to EasternGraphics. The translation, reproduction, or dissemination, fully or in part, is

## onlypermitteduponthepriorwrittenconsentofEasternGraphics. EasternGraphicsassumesnoguaranteefor

## the completeness, accuracy, currentness, continuity, and fitness of this work for the purpose intended by the

## user. A liability of EasternGraphics is excluded, except in cases of intent or gross negligence and personal

## injury. Allnamesorlabelscontainedinthisworkmaybetrademarksoftherespectiveholderofrightsandmay

## betrademark-protected. Thefactthatatrademarkismentionedinthisworkshouldnotleadtotheassumption

## thatitisfreeandeverybodyisallowedtomakeuseofit.

<!-- Page 3 -->

CONTENTS

# Contents

1 Preliminarynotes 3

2 Directorystructure 4

2.1 StructureofOFMLproductandcatalogdata . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4

2.2 Examplestructure . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5

3 DataandCatalogprofiles 6

3.1 Directorystructureofdataregistration . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6

3.1.1 Registrationofdataprofilesviaapp.gf.data.profile . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6

3.1.2 Registrationofcatalogprofilesviaapp.gf.data.catalogs . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7

3.1.3 Storageofcatalogprofileresources . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8

3.2 Dataprofiles . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8

3.2.1 Settingsandpaths. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8

3.2.2 Descriptions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9

3.2.3 Packagesofagroup. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9

3.2.4 Exampleforadataprofile:standard_DE_1.cfg . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9

3.3 Catalogprofiles . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10

3.3.1 Structure . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10

3.3.2 Settings . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10

3.3.3 Descriptions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 12

3.3.4 Datapackages. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 12

4 Registrationofmanufacturersandconcerns 14

4.1 Centralregistrationdatabase . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14

4.2 Manufacturerregistration . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14

4.2.1 Manufacturerregistrationformat . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14

4.2.2 Manufacturerregistrationkeys . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15

4.2.3 Storageofmanufacturerresources . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 17

4.3 Concernregistration . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 17

4.3.1 Concernregistrationformat . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 18

4.3.2 Concernregistrationkeys . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 18

4.3.3 StorageofConcernresources . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 18

5 RegistrationofOFMLpackages 19

5.1 Packageregistrationformat . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19

5.2 Registration . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19

5.3 Packageregistrationkeys . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19

5.4 Languagedependentkeys . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 28

5.5 Example . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 30

DSR3.7 1

<!-- Page 4 -->

REFERENCES

6 Datatypesandfiletypes 31

6.1 OFMLandpicturedata . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 31

6.2 OFMLproductdata . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 31

6.3 XCFcatalog . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 31

6.4 Specificresources . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 32

6.4.1 Catalogimages . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 32

6.4.2 Materialimages . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 32

6.4.3 HTMLfiles . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34

6.4.4 Configurationsandgeometries . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34

6.4.5 Articlespecificviewsetup . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34

6.5 Imageformatconventions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34

6.6 Priceprofiles . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 35

7 History 36

# References

[asv] ArticleSpecificViewsetup(Specification).EasternGraphicsGmbH
[gln] GLNhttp://en.wikipedia.org/wiki/Global_Location_Number
[glos] Libraries,Series&Co.–fundamentalOFMLterms.EasternGraphicsGmbH
[gtin] GTINhttp://en.wikipedia.org/wiki/Global_Trade_Item_Number
[iso639-1] ISO639-1http://en.wikipedia.org/wiki/ISO_639
[iso3166] ISO3166http://en.wikipedia.org/wiki/ISO_3166
[iso8601] ISO3166http://en.wikipedia.org/wiki/ISO_8601
[oap] OAP-OFMLAidedPlanning(Specification).EasternGraphicsGmbH
[ocd] OCD-OFMLCommercialData(Specification).EasternGraphicsGmbH
[ofml] OFML–Standardizeddatadescriptionformatoftheofficefurnitureindustry.
IndustrieverbandBüroundArbeitswelte.V.(IBA)
[omats] OFMLcompatibleMaterials(Specification).EasternGraphicsGmbH
[ppr] PreisprofileinHerstellerdatenzurVerarbeitungmitpCon-Produkten(Specification).EasternGraphicsGmbH
[utc] UTChttp://en.wikipedia.org/wiki/Coordinated_Universal_Time
[xcf] XCF–ExtensibleCatalogFormat(Specification).EasternGraphicsGmbH

1
Except[asv]und[ppr] thespecificationsofEasternGraphicsGmbHaswellas[ofml]areavailableviathepConDownloadCenter

https://download-center.pcon-solutions.com

inthecategoryOFMLSpecifications.

1
Ifrequired,thespecifications[asv]and[ppr]canberequestedfromtherelevantprojectmanageratEasternGraphics.

DSR3.7 2

<!-- Page 5 -->

1 PRELIMINARYNOTES

# 1 Preliminary notes

## Regarding file names pay attention to case sensitivity corresponding to their formation rule. The file name

## has to be written exactly as the stored keys in the registration file. This convention is urgent to guarantee

## the operativeness of the OFML data (see [ofml]) platform independent. In principle the use of small letters is

## recommended.

## For all path definitions the slash character (’/’) will be used throughout this specification. Alternatively the

## backslash’\’maybeused.

## Keyandkeyvaluedefinedinthisspecificationhavetobeusedexactlyinthespellingdefinedhere.

## Thefollowingstyleswillbeusedfortheidentificationofdifferentelements:

## Example

## File respectively path name

## Keydefination

## Key reference

## Theidentifierbehindthekeynamespecifies:

## [M] mandatorykey

## [M/O] conditionalkey

## [O] optionalkey

## In many places of this specification the values of specific keys are used to define file or path names. In that

## casethespecifiedkeyismarkedwithprefix’$’andthereferenceisputinparentheses. Thedatarootdirectory

## whichisusedinpathdefinitionshasthesymbolicname<data>.

DSR3.7 3

<!-- Page 6 -->

2 DIRECTORYSTRUCTURE

# 2 Directory structure

# 2.1 Structure of OFML product and catalog data

## The illustration below shows the general idea of the commonly used directory structure in pCon applications.

## Inthefollowingsectionseachdirectoryanditscontentwillbeexplainedindetail.

## <data>/

## catalogs/

## images/...............................................................................[3.1.3]

## profiles/.............................................................................[3.1.2]

## registry/....................................................................................[5.2]

## ($manufacturer)/

## ($program)/

## ($version)/.........................................................................[6.1]

## ($distribution_region)/

## ($version)/

## cat/........................................................................[6.3]

## db/.........................................................................[6.2]

## etc/.....................................................................[6.4.4]

## html/....................................................................[6.4.3]

## de/

## en/

## fr/

## ...

## image/...................................................................[6.4.1]

## mat/.....................................................................[6.4.2]

## l/

## m/

## s/

## meta/

## oam/

## oap/

## priceprofiles/..........................................................................[6.6]

## ($ppr_version)/

## Someelementsinthestructurecanbestoredasa ZIParchive :

## <data>/

## ($manufacturer)/

## ($program)/

## ($distribution_region)/

## ($version)/

## cat/xcf.zip

## image/image.zip

## mat/mat.zip

## NotesfortheuseofZIParchives:

## The ZIP archive contains the files exactly as they would be in the directory (i.e., no additional sub

## folders). Anexceptionisthemat.zip,see6.4.2. Ifafileexistsinsidethearchiveandinthedirectory

## too,thefilefromthedirectorywillbeused.

DSR3.7 4

<!-- Page 7 -->

2 DIRECTORYSTRUCTURE

# 2.2 Example structure

### <data>/

### catalogs/

### images/

### man_de-2011.0.jpg

### man_de-2012.0.jpg

### man_fr-2011.0.jpg

### man_fr-2012.1.jpg

### ...

### profiles/

### man.cfg

### man_de-2011.0.cpr

### man_de-2012.0.cpr

### man_fr-2011.0.cpr

### man_fr-2012.1.cpr

### ...

### man/

### series/

### 1/odb.ebase

### 2/odb.ebase

### 3/odb.ebase

### DE/

### 1/

### cat/xcf.zip

### db/pdata.ebase

### etc/artsetup.csv

### image/image.zip

### mat/mat.zip

### oam/oam.ebase

### 2/

### cat/xcf.zip

### db/pdata.ebase

### etc/artsetup.csv

### image/image.zip

### mat/mat.zip

### oam/oam.ebase

### FR/

### 1/

### cat/xcf.zip

### db/pdata.ebase

### etc/artsetup.csv

### image/image.zip

### mat/mat.zip

### oam/oam.ebase

### 3/

### cat/xcf.zip

### db/pdata.ebase

### etc/artsetup.csv

### image/image.zip

### mat/mat.zip

### oam/oam.ebase

### ...

### registry/

### man/

### man.jpg

### MAN.cfg

### man_series_DE_1.cfg

### man_series_DE_2.cfg

### man_series_FR_1.cfg

### man_series_FR_3.cfg

### ...

DSR3.7 5

<!-- Page 8 -->

3 DATAANDCATALOGPROFILES

# 3 Data and Catalog profiles

## ThischapterdescribestheregistrationofOFMLdatainapConapplication.

# 3.1 Directory structure of data registration

## Allapplicationshavetosupportadirectorystructurethatlookslikethis:

## Directory(relative) Shortdescription

## /bin executableprogramfiles,systemlibraries

## /lib moduledirectory(optional)

## /data OFMLproductandcatalogfiles

## /data/catalogs catalogprofilesandassociatedresources

## /etc/data dataprofiledirectory

## configurationfiles

## /etc/startup

## Usuallythesedirectoriesarelocatedunderneaththeprogramdirectory.

## Particulardirectoriescanbeoutsideoftheprogramdirectory,e.g. inordertorealizeserversolutions.

## OFMLdataisregisteredviadataprofilesorcatalogprofiles:

## • AdataprofiledescribesasingleOFMLdatasetofamanufacturerwithoutanidentificationfordistribution

## regionandversion.

## Date profiles are used if in the application can or should be used only a single OFML dataset of the

## manufacturer.

## • AcatalogprofiledescribesanOFMLdataset(catalog)ofamanufacturerresp. supplierwithidentification

## fordistributionregionandversion.

## Catalog profiles allow for simultaneous usage of various OFML datasets of a manufacturer/supplier, dif-

2

## feringindistributionregionand/orversion . However,not(yet)allapplicationsupportthis. Therefore,for

3

## otherapplicationsadataprofile shouldbeprovidedanyway.

## Thedataprofilesandcatalogprofilestobeprocessedbytheapplicationarespecifiedinthestartfiledefault.cfg

## locatedinthedirectory/etc/startup.

## Amongstothers,thisfilecontainsthekeyapp.gf.data.profile and/orthekeyapp.gf.data.catalogs. They

## containthenamesoftheprofileswhichhavetobeloaded.

## Alternativelythesekeyscanbereadfromaseparatefile. Thisfilecanbespecifiedbythekey

4

## app.gf.data.profile.registration .

## 3.1.1 Registrationofdataprofilesviaapp.gf.data.profile

## Thiskeyisusedbyapplicationsnotyetsupportingtheprocessingofcatalogprofiles.

## Dataprofileswillbestoredasfileswithextension.cfgintheprofiledirectory.

## The profile directory can be specified by the key app.gf.data.profile.path. This key is optional. If it is

## not defined the locale profile directory (/etc/data) will be used. Data profiles are privileged loaded from the

## directoryapp.gf.data.profile.path. Ifnoprofiledirectoryexiststheretheapplicationattemptstoloaditfrom

## thelocaledirectory.

2
ThisconceptsometimesiscalledMultiplepricelists.
3
theso-calledcompatibilitydataprofile
4
Keyapp.gf.data.profile.registration takesprecedenceovertheothertwokeys.

DSR3.7 6

<!-- Page 9 -->

3 DATAANDCATALOGPROFILES

## In the key the names of the profile files are given without the extension . Several

## app.gf.data.profile .cfg

## profilesareseparatedbysemicolon.

## Example1

### default.cfg:

### app.gf.data.profile.path = \\SERVER\data\profiles

### app.gf.data.profile = standard_DE_1;man1

## Example2

### default.cfg:

### app.gf.data.profile.path = \\SERVER\data\profiles

### app.gf.data.profile = standard_DE_1;man1;man2

## Example3

### default.cfg:

### app.gf.data.profile.path = \\SERVER\data\profiles

### app.gf.data.profile.registration = \\SERVER\data\profiles\app.profiles

### \\SERVER\data\profiles\app.profiles:

### app.gf.data.profile = standard_DE_1;man1;man2;man3

## 3.1.2 Registrationofcatalogprofilesvia app.gf.data.catalogs

## Thiskeyisusedbyapplicationssupportingtheprocessingofcatalogprofiles.

## Note:

## Ifthekeyapp.gf.data.catalogs doesnotexistintheprofileregistrationfile,anapplicationreads

## theprofilesfromtheoldkeyapp.gf.data.profile. Thisensuresbackwardcompatibilityofanap-

## plicationthatsupportscatalogprofileswithrespecttotraditionaldatainstallationsthathavenotbeen

## migratedyet. However,theoldkeyapp.gf.data.profile isnotevaluatedifkeyapp.gf.data.catalogs

## ispresentintheprofileregistrationfile.

## Thenameofacatalogprofilefilehasthefollowingstructure:

## ($brand)_($catalog_id).cpr

## Thekeyapp.gf.data.catalogs containsthefilenamesoftheprofilestobeloadedincludingfileextensionbut

## withoutapath. Multipleprofilesareeachseparatedbyasemicolon.

## Iadditiontocatalogprofilesinthekeyconventionaldataprofilescanbespecified,too. Thiswaymanufacturers

## aresupported,whichdonotprovidecatalogprofilesyet.

## Catalog profiles are stored by default in the profile directory catalogs/profiles under the OFML data direc-

## tory. Analternateprofiledirectorycanbespecifiedviaoptionalkeyapp.gf.data.profile.pathinthebootfile

## etc/startup/default.cfg of an OFML application. If a catalog profile does not exist in the profile directory,

## theapplicationlooksfortheprofileinitslocalpathetc/data.

## Example

### app.gf.data.catalogs=man1_de-2012.1.cpr;man2.cfg;man3_any-2012.4.cpr

DSR3.7 7

<!-- Page 10 -->

3 DATAANDCATALOGPROFILES

## 3.1.3 Storageofcatalogprofileresources

## An optional logo to represent a catalog in a catalog selection of the application can be stored in 2 different

## sizesas:

## Cataloglogosmall:

## catalogs/images/($brand)_($catalog_id)_.jpg

## [catalogs/images/($brand)_($catalog_id)_.png]

## Imagesize: [1-max. 100]x20 (WxHinpixels)

## Cataloglogolarge:

## catalogs/images/($brand)_($catalog_id).jpg

## [catalogs/images/($brand)_($catalog_id).png]

## Imagesize: [1-max. 200]x40 (WxHinpixels)

5

## The format of the image file is JPEG . Optionally also PNG can be used, however this is not supported by all

## applications. IfthelogoisgiveninJPEGformataswellasinPNGformat,PNGtakesprecedence.

## Ifnologoisstoredforthecatalog,theapplicationusesthelogoofthebrandorofthemanufacturertorepresent

## thecatalog(seesection4.2.3).

# 3.2 Data profiles

## Data profiles are text files based on a fixed scheme. The following table gives a review about the individual

## sections:

## Section Shortdescription

## [config] Settingsandpaths

## [<lang>] languagespecificdescriptions

## [lib:$group] packagesofagroup$group

## Annotation:

## Thegroupidentifier$group shouldusethemanufactureridentifierspecifiedintheregistration. Itisallowedto

## enlargethename byasuccessivenumber orusefreeidentifier names, topoolspecificpackages inseparate

## sections.

## Lines starting with character ’#’ are interpreted as a comment. If the key encoding (see below) has the value

## UTF-8,thecharactersafter’#’mustalsobeencodedwithUTF-8.

## 3.2.1 Settingsandpaths

## [1] encoding [O]

## – definestheencodingofthedataprofile

## Forthecurrentpossiblevalues,seethespecificationofthekeyinthepackageregistration(section5.3).

## Ifspecified,thekeyshouldbethefirstinthesection.

5 Forimageformatconventionsseesection6.5.

DSR3.7 8

<!-- Page 11 -->

3 DATAANDCATALOGPROFILES

## [2]

## path[M/O]

## – definesthepackagesearchpath

## Theentry path specifiesthepathtothepackagesregisteredwiththeprofile. Thisentryhastobespecifiedif

## the packages are not located in the locale data directory ( <program>/data ) of the software system. Only one

## pathisallowedwithinaprofile.

## The entry has to provide a complete path information in the form <drive>/<path> or //<server>/<path>

## withoutaclosingslash(’/’).

## [3] use_version[O]

## – permitstheuseofnotreleaseddata

## Normallythevalueis . With theversioningwillbedeactivated. Forthatcompatiblelibrarieswithout

## true false

## versioningareassumed.

## 3.2.2 Descriptions

## Thenameofthesection <lang> hastobespecifiedaccordingtoISOlanguagecode(ISO–639-1).

## [4] name [O]

## – definesashorttermfortheprofile

## [5] desc [O]

## – definesadetaileddescriptionfortheprofile

## 3.2.3 Packagesofagroup

## In the section [lib:$group] all manufacturer specific packages are specified which have to be used by the

## software system. Each entry consists of the name of the package registration file without file extension .cfg

## (see section 5.2) followed by the equality sign and the loading mode. This mode is defined either as true or

## asfalse,wheretrue instructsthesoftwaresystemtousethepackage.

6

## ForagivenOFMLlibraryonlyonepackage maybespecified.

## 3.2.4 Exampleforadataprofile: standard_DE_1.cfg

### [config]

### path =

### [en]

### name = Standard

### desc = profile for EasternGraphics basic libraries

### [lib:egr]

### egr_office_np_DE_1=true

### egr_accessories_DE_1=true

6
foradefineddistributionregionandadefinedversion

DSR3.7 9

<!-- Page 12 -->

3 DATAANDCATALOGPROFILES

# 3.3 Catalog profiles

## A catalog is a collection of products of a given manufacturer resp. supplier and comprises – from an OFML

## point of view – all OFML packages needed for the selection, graphical presentation, configuration and order

7

## processingoftheproductsofthecatalog . Acataloghasalwaysbothaspatialdimension(salesregion)anda

## temporaldimension(version).

## Acatalogprofiledefinesareleaseofacatalogofamanufacturer/supplier.

## 3.3.1 Structure

## Thecatalogprofileisstoredasaconfigurationfile. Theprofilesettingsaredefinedaskey–valuepairs

## <key> = <value>

## eachinasinglelineanddividedintoseveralsections.

## Belowthesectionsandkeysofacatalogprofilefilearedescribedindetail.

## section explanation

## [catalog] settingsandpaths

## [<lang>] languagespecificdescriptions

## [lib] OFMLpackagesusedbythecatalog

## AcatalogprofileusesUTF–8asthecodepage. Thefirst3bytesmaycontaintheoptionalbyteordermarkfor

## UTF–8(EF BB BF).Alternatively,itispermittedtosaveacatalogprofileinUTF–16LittleEndian. Theusageof

## UTF–16isdeclaredbythebyteordermarkFF FE.

## Linesstartingwithcharacter#areinterpretedasacomment.

## 3.3.2 Settings

## [1] catalog_id [M]

## – specifiestheuniqueidentificationkeyofthecatalog.

## ThecatalogIDuniquelyidentifiesacatalogandtheproductsinsertedfromthiscatalogintoanOFMLproject.

## Therefore, for each new release of a catalog a new catalog ID must be assigned. It is not permitted for two

## differentversionsofacatalogtousethesamecatalogID.

## ThecatalogIDhasthefollowingstructure: <identifier>.<revision>

## Theidentifieridentifiesthecatalogandmustmatchtheregularexpression[a-z][a-z0-9_-]*. Anidentifierof

## theform<sales region>-<year of release>isrecommended.

## Catalog revisions are used to represent changes (corrections) within a catalog. The revision number is a

## natural number greater than or equal to 0. For the initial issue of a catalog revision number 0 has to be used.

## Ateachdeliveredchangeofthecatalogitmustbeincreasedaccordingly.

## Catalogs which are supposed to be processed simultaneously in an application have to possess different

## identifiers in their catalog ID. A revision of a catalog replaces a previous revision of the same catalog with a

## lowerrevisionnumber.

## Example: catalog_id = de-2011.1

7
Sometimesasasynonymthetermpricelistisused.

DSR3.7 10

<!-- Page 13 -->

3 DATAANDCATALOGPROFILES

## [2]

## release_date [M]

## – declaresthereleasedateofthecatalog.

## ThevalueofthiskeyhastobespecifiedasanISOdateintheform YYYY-MM-DD [iso8601].

## Example: release_date = 2011-03-17

## [3] brand [M]

## – definestheOFMLidentifierofthebrandunderwhichthecatalogislisted.

## The value of the key can not be freely assigned. It has to be registered in the central registry database of

## manufacturers(s.4.1).

## If the catalog is not listed under a specific brand, here the short name of the manufacturer/supplier has to be

## specified(key manufacturer ,see5.3).

## [4] brand_id [M]

## – definesthecommercialIDofthebrandunderwhichthecatalogislisted.

## The value of the key can not be freely assigned. It has to be registered in the central registry database of

## manufacturers(s.4.1).

## Usingthiskey,additionalinformationisretrievedfromthecentralregistrydatabaseofmanufacturers(e.g. the

## displaynameorthemanufacturer’saddress).

## Ifthecatalogisnotlistedunderaspecificbrand,herethemanufacturer_id ofthemanufacturer/supplierhas

## tobespecified.

## [5] distribution_region[M]

## – definesthebasicsalesregionforwhichthecatalogisvalid.

## Usingthesalesregion,anapplicationcancategorizedifferentcatalogsinordertosubmitreplacementpropos-

## alstotheuser.

## [6] valid_from[O]

## – definesthedatefromwhichonthecatalogmaybeused.

## ThevaluehastobeformattedasanISOdateYYYY-MM-DD[iso8601].

## The validity period specified via valid_from and valid_to has only informative character. Applications do

## not limit the use of the catalog to that period. However, this information can be used to display warnings or

## recommendationstouninstallthecatalogiftheperiodhasexceeded.

## If the lower limit of the validity period is not specified, the date 1970-01-01, sufficiently far in the past, will be

## assumed.

## [7] valid_to [O]

## – definesthedateuptowhichthecatalogmaybeused.

## ThevaluehastobeformattedasanISOdateYYYY-MM-DD[iso8601].

## Iftheupperlimitofthevalidityperiodisnotspecified,thedate9999-12-31,sufficientlyfarinthefuture,willbe

## assumed.

## [8] path[O]

## – definesthepathtotheusedOFMLdata.

## IftheOFMLdatausedbythecatalogisnotlocatedinthelocaldatadirectoryoftheapplication,thebasepath

## tothedatahastobespecifiedinthiskey.

## Thepathhastobestatedintheform <drive>/<path> or //<server>/<path> withoutfinalslash(’/’).

DSR3.7 11

<!-- Page 14 -->

3 DATAANDCATALOGPROFILES

## [9]

## ppr_region_id [O]

## – assignsthecatalogtoapriceprofileregion.

## If a price profile region is activated, together with the catalog a price profile package has to be distributed, in

## whichthisregionisdefined(seealso6.6).

## [10] ppr_version[M/O]

## – definestheversionoftheusedpriceprofile.

## Theversionoftheusedpriceprofilehastobespecifedifapriceprofileregionisactivatedviakey ppr_region_id

## (seealso6.6).

## Example: ppr_version = 1

## 3.3.3 Descriptions

## Thenameofacatalogaswellasoptionaldescriptionsforadefaultlanguagearestatedinsection [catalog] .

## Furthermore,thesetextscanbestoredforadditionallanguagesinadditionaloptionalsections [<lang>] . The

## key [<lang>] defines the language and must be specified as a two-letter ISO language code (ISO–639-1)

## [iso639-1].

## [11] catalog_name [M]

## – specifiesthenameofthecatalog.

## Thenameshouldallowforaneasyidentificationofthecatalogbytheuser,e.g.:

## catalog <sales region> <year>/<issue>.

## Note:

## Catalogs are usually hierarchically listed below the manufacturer (supplier). Applications that use

## a manufacturer–independent list of available catalogs, can concatenate the manufacturer name

## with the catalog name. Therefore, the catalog name itself should not include the name of the

## manufacturer.

## [12] description[O]

## – specifiesadetaileddescriptionofthecatalog.

## Fixedlinebreakscanbedefinedinthedescriptionusing\n.

## 3.3.4 Datapackages

## Thepackagesusedbyacatalogarespecifiedinthesection[lib].

## Foreachpackageakeyofform

## <package key> = [true|false]

## hastobespecified,where<package key> correspondstothenameofthepackageregistrationfilewithoutfile

## extension(seesection5.2)andvaluetruespecifies,thatthepackageisusedinthecontextofthecatalog.

### ForagivenOFMLlibraryonlyonepackage 8 maybespecified.

## Ifapackageregistrationfilecannotbeloaded,theentirecatalogcannotbeloaded/used.

8 foradefineddistributionregionandadefinedversion

DSR3.7 12

<!-- Page 15 -->

3 DATAANDCATALOGPROFILES

## A catalog profile may reference packages of several manufacturers, but the packages with catalog data have

## to be from the same manufacturer resp. from manufacturers of same concern ( ) or from manufacturers

## brand

## ::egr:: and ::ofml:: .

DSR3.7 13

<!-- Page 16 -->

4 REGISTRATIONOFMANUFACTURERSANDCONCERNS

# 4 Registration of manufacturers and concerns

# 4.1 Central registration database

### Manufacturers 9 andconcernsareregisteredcentrallybyEasternGraphics.

## (Pleasecontactcto@EasternGraphics.com.)

## This avoids conflicts assigning unique keys more than once. The registration data is maintained in a global

## manufacturerdatabase( Manufacturers.ebase ).

## Thisdatabasecontainstheassignmentofcodedesignations(IDs)ofmanufacturersandconcerns,aswellas

## theirnames.

## AlistwithallocatedIDscanberequestedfromEasternGraphicsatanytime.

## Thefollowingkeysmightpartiallynotbeusedifanapplicationderivestheinformationdirectlyfromtheglobal

## manufacturerdatabase.

# 4.2 Manufacturer registration

## For each manufacturer an own registration file has to be created. In this file manufacturer specific, package

## independentcontentcanbespecified.

## The file name is formed from the commercial identifier of the manufacturer (according to the global manufac-

## turerdatabase,seeabove). Thefileextensionis.cfg.

## Themanufacturerregistrationfilesarelocatedinthedirectory<data>/registry.

## Example:

## <data>/registry/MAN.cfg

## 4.2.1 Manufacturerregistrationformat

## Theformatofthemanufacturerregistrationfilesisequaltotheformatofthepackageregistrationfiles(see5.1).

## The file is separated in two parts: a language independent [general] section and several language-specific

## [<ISO-identifier>]sections.

## In principle, each key can be used both in section [general] as well as in language-specific sections. The

## application always is looking for a key first in the relevant language-specific section. An exception is the key

## encoding: thismayonlybeusedinsection[general]section.

10

## In principle, each keyof the packageregistration canbe used inthe manufacturerregistration too . This key

## willbeusedifitisnotspecifiedinthepackageregistration. Anexceptionisthekeyencoding,seebelow.

9 Here,amanufacturerisgenerallydefinedasanyentitythatprovidesanddistributesOFMLdata. Inadditiontoactualmanufacturers
ofproducts,thiscanalsobeanassociationorsimilar.
10
However,inpracticethismakessensenotforallkeys.

DSR3.7 14

<!-- Page 17 -->

4 REGISTRATIONOFMANUFACTURERSANDCONCERNS

## Example:

### [general]

### encoding = UTF-8

### address.name = EasternGraphics GmbH

### address.street = Einsteinstrasse 1

### address.city = Ilmenau

### address.zip = 98693

### address.country = Deutschland

### address.tel = 03677 6782-0

### address.fax = 03677 678250

### address.email = info@EasternGraphics.com

### address.www = www.EasternGraphics.com

### ppr_region_id = GER

### [de]

### manufacturer_name = Standard

### [en]

### manufacturer_name = Default

### address.country = Germany

## 4.2.2 Manufacturerregistrationkeys

## [1] encoding [O]

## – definestheencodingofthisregistryfile

## Incontrasttootherkeysthatcanalsobeusedinthepackageregistration,thevalueofthiskeyisnotinherited

## fromthemanufacturerregistrationtothepackageregistration.

## Forthecurrentpossiblevalues,seethespecificationofthekeyinthepackageregistration(section5.3).

## Ifspecified,thekeyshouldbethefirstinthesection.

## [2] concern_id [O]

## – definestheuniqueidentifieroftheconcernthemanufacturerbelongsto

## The identifier may contain alphanumeric characters including the underscore, where the first character must

## bealetter:

## [a-zA-Z][a-zA-Z0-9_]*

## Attention : Thiskeyneedstoberegistered(see4.1).

## Note:

## The identifier can contain both uppercase and lowercase letters, but the same correct spelling must be main-

## tained at each use of the identifier. There must not be two identifiers, which differ only in the case of the

## characters.

## Forthecurrentpossiblevalues,seethespecificationofthekeyinthepackageregistration(section5.3).

## [3] manufacturer_name [M]

## – definesthe(languagedependent)nameofthemanufacturer

## [4] ppr_region_id [O]

## – determinestheregionkeytobeusedinthepriceprofileofthemanufacturer.

## Thiskeywillbereferencedinthepriceprofileincolumn country oftable profile (see[ppr]). (Seealso6.6)

DSR3.7 15

<!-- Page 18 -->

4 REGISTRATIONOFMANUFACTURERSANDCONCERNS

## Example: ppr_region_id = BENELUX

## [5] address.name [O]

## [6] address.street [O]

## [7] address.postbox [O]

## [8] address.city [O]

## [9] address.zip [O]

## [10] address.state [O]

## [11] address.country [O]

## [12] address.tel [O]

## [13] address.fax [O]

## [14] address.email [O]

## [15] address.www [O]

## Themeaningofthesekeysisselfexplaining(seealsotheexampleabove),sothedocumentforgoesadetailed

## descriptionoftheaddresskeys.

## A special feature of these keys is that the value can be a multiline text. For this purpose, an index must be

## appended to the key as a postfix. The order of the indices and not the sequence of the lines determines the

## compositionofthetext.

## [16] release_note [O]

## – definesanarbitrarytextforthemanufacturer

## Thistextcancontainpackageindependentinformation. Asoftwaresystemcoulddisplaythetextinthecatalog

## view,forexample.

## Example: release_text = Version 2.3 with price alignments from April the 1st

## [17] gln_id [O]

## – specifiestheGLN(GlobalLocationNumber)ofthemanufacturer/concern(see[gln])

## [18] series_name.<program_id> [O]

## – Nameofcommercialseriesprogram_id

## Thenamecanbeusedbytheapplication,e.g.,inselectiondialogs.

## If this key is not specified for a given commercial series program_id, the application must try to determine

## the appropriate OFML library by means of the commercial identifiers of manufacturer and series, in order to

## determine the name (key program_name) from the registration file. However, this procedure is not reliable,

## becausethereisnotalwaysaclearrelationshipbetweenacommercialseriesandanOFMLlibrary.

## [19] external_catalog.url [O]

## [20] external_catalog.name [O]

## Theexternal_catalog.url keymustappearonlyonceinsection[general]. Ifthevalueofthekeyisavalid

## HTTPSURL,anycatalogdatastoredinthemanufacturer’sOFMLpackageswillbeignoredandtheapplication

## willofferaconnectiontotheexternalcatalogdefinedbytheURLinstead.

## The key external_catalog.name can be used to specify language-specific names for the catalog. If no key

## exists in the corresponding language-specific section for the catalog language set in the application, the key

## from section is used. If the key does not exist there either, the name of the manufacturer will be

## [general]

## used(seekey manufacturer_name above).

## ExternalcatalogsarenotsupportedinallpConapplications. Inordertoinsertarticlesfromtheexternalcatalog

DSR3.7 16

<!-- Page 19 -->

4 REGISTRATIONOFMANUFACTURERSANDCONCERNS

### intoaproject,theexternalcatalogsmustserveaspecial,application-specficAPI 11 .

## Example:

### [general]

### external_catalog.url=https://www.example.com

### external_catalog.name=Example Catalog

### [de]

### external_catalog.name=Beispielkatalog

## 4.2.3 Storageofmanufacturerresources

## Manufacturerresourcesarestoredinthedirectory <data>/registry/($manufacturer).

## Thefollowingresourcesaredefined:

## Manufacturerlogo:

## registry/($manufacturer)/manufacturer.jpg

## [registry/($manufacturer)/manufacturer.png]

## • Imagesize: [1-max. 200]x40(widthxheightinpixels)

## Largemanufacturerlogo(optional):

## registry/($manufacturer)/($manufacturer)_l.jpg

## [registry/($manufacturer)/($manufacturer)_l.png]

## • Theimagemayhaveamaximumedgelengthof2000pixels.

## • Asarecommendation,thelongestedgeshouldbeatleast1000pixelslong.

## • Thereisnospecificationabouttheaspectratio.

## • Theapplicationsareresponsibleforcorrectlyprocessingimageswithdifferentsizes.

12

## The format of the image file has to be JPEG or PNG . If the logo is given in JPEG format as well as in PNG

## format,PNGtakesprecedence.

# 4.3 Concern registration

## The registration of a concern (corporate group) works similar to the manufacturer registration. It is preceding

## tothemanufacturerregistrationlikeselfsameprecedesthepackageregistration.

## Foreachconcernaregistrationfilecanbecreated. Concern-specificcontentcanbestoredinthisfile.

## The file name is formed from the identifier of the concern (according to the global manufacturer database,

## see4.1). Thefileextensionis.cfg.

## Theconcernregistrationfilesarelocatedinthedirectory <data>/registry .

11 Detailscanbeobtainedfromtheproductmanagersorthesupport.
12 Forgeneralimageformatconventionsseesection6.5.

DSR3.7 17

<!-- Page 20 -->

4 REGISTRATIONOFMANUFACTURERSANDCONCERNS

## 4.3.1 Concernregistrationformat

## Theformatoftheconcernregistrationfilesisasfaraspossibleidenticaltothemanufacturerregistration.

## Each key of the manufacturer or package registration can be defined in the concern registration too. This key

## willbeusedifitisnotdefinedinthemanufacturerorpackageregistration.

## Example:

## [general]

## concern_id=egr

## [de]

## concern_name = EasternGraphics GmbH

## 4.3.2 Concernregistrationkeys

## Thefollowingkeysaredefinedadditionallyfortheconcernregistrationaccordingtothemanufacturerregistra-

## tion:

## [1] concern_name [M]

## – definesthe(languagedependent)nameoftheconcern

## 4.3.3 StorageofConcernresources

## Concernresourcesarestoredinthedirectory<data>/registry/($concern).

## Thefollowingresourcesaredefined:

## Concernlogo:

## registry/($concern)/concern.jpg

## [registry/($concern)/concern.png]

## • Imagesize: [1-max. 200]x40(widthxheightinpixels)

## Largeconcernlogo(optional):

## registry/($concern)/($concern)_l.jpg

## [registry/($concern)/($concern)_l.png]

## • Theimagemayhaveamaximumedgelengthof2000pixels.

## • Asarecommendation,thelongestedgeshouldbeatleast1000pixelslong.

## • Thereisnospecificationabouttheaspectratio.

## • Theapplicationsareresponsibleforcorrectlyprocessingimageswithdifferentsizes.

## The format of the image file has to be JPEG or PNG 13 . If the logo is given in JPEG format as well as in PNG

## format,PNGtakesprecedence.

13
Forgeneralimageformatconventionsseesection6.5.

DSR3.7 18

<!-- Page 21 -->

5 REGISTRATIONOFOFMLPACKAGES

# 5 Registration of OFML packages

## ForeachpackagewhichistobeusedinapConapplicationaregistrationfilehastobeprovided. Thiswaythe

## content,thestructureanddifferentconstraintsforthepackagewillbespecified.

## Regardingrepositoryofthesefilesseesection2.1andregardingintegrationwithindataresp. catalogprofiles

## seesections3.2resp.3.3.

# 5.1 Package registration format

## Theregistrationfileformatconsistsof(languagespecific)sections,keysandcorrespondingvalues.

## Lines starting with character ’ # ’ are interpreted as a comment. If the key encoding (see below) has the value

## UTF-8 ,thecharactersafter’ # ’mustalsobeencodedwithUTF-8.

## Languagedependentvaluesarespecifiedinitsownsection. Thenameofthesectionresultsfromthedouble-

## digitISOlanguagecode(ISO–639-1)(see5.4).

## Themeaningofthekeysandvaluesisexplainedinthenextsection.

# 5.2 Registration

## In the data root directory the directory <data>/registry is located. In that directory the registration files are

## stored. Thenameofapackageregistrationfilehastobecreatedoutofthekeyswhicharerecordedinthefile.

14

## Thefilenameformatfollowsthisconvention :

## ($manufacturer)_($program)_($distribution_region)_($version).cfg

## Thepackageregistrationfilesarereferencedbytheirnamesfromdataprofiles(seesection3.2)resp. catalog

## profiles(seesection3.3).

# 5.3 Package registration keys

## [1] encoding [O]

## – definestheencodingoftheregistryfileandthepackageitself

## Thiskeymayonlybespecifiedifalldatainthepackagepossessesthespecifiedcharacterencoding.

## Currently,thepossible/supportedvaluesare:

## Encoding Note

### UTF-8 accordingtostandardISO/IEC10646-1(UCSTransformationFormat8Bit) a

a
Thebyteordermarkatthebeginningofthefilesisnotpermitted.ThenormalizationformshouldbeNFC.

## Example: encoding = UTF-8

## Ifspecified,thekeyshouldbethefirstinthepackageregistrationfile.

14
Conversely,thevaluesforprogramanddistribution_regioncannotbeuniquelydeterminedbystringseparationfromthenameof
apackageregistrationfile(sinceprogramidentifiersthemselvescancontainanunderscore).

DSR3.7 19

<!-- Page 22 -->

5 REGISTRATIONOFOFMLPACKAGES

## [2]

## manufacturer [M]

## – definestheuniqueOFMLidentifierofthemanufacturer

## Theidentifiermaycontainalphanumericcharacters,wherethefirstcharactermustbealetterandlettersmust

## belowercase:

## [a-z][a-z0-9]*

## Attention: Thiskeyneedstoberegistered(see4.1).

## The identifier of the manufacturer forms the path name on the first level of the directory structure defined in

## section2.1.

## Example: manufacturer = ofml

## [3] program[M]

## – definestheuniqueOFMLidentifieroftheOFMLlibrary(program)withinthemanufacturer

## The identifier may contain alphanumeric characters including the underscore, where the first character must

## bealetter:

## [a-zA-Z][a-zA-Z0-9_]*

## Theidentifieroftheprogramformsthepathnameunderneaththemanufacturerlevel(seesection2.1).

## Example: program = goiex

## [4] manufacturer_id [M/O]

## – definestheuniquecommercialidentifierofthemanufacturer

## Theidentifiermaycontainalphanumericcharacters,wherelettersmustbeuppercase:

## [A-Z0-9]*

## Attention : Thiskeyneedstoberegistered(see4.1).

## Mandatorykeyifamanufacturerregistrationexistsandforpackagesoftypeproduct.

## Each identifier must be used uniformly in all packages of the manufacturer. An explicit one-to-one mapping

## manufacturer_id ↔manufacturer hastobeguaranteed.

## Alsoinreferencingpackagesonlyoneidentificationcodeisallowed,i.e. referencingseveralmanufacturersat

## thesametimeisnotpossible.

## Example: manufacturer_id = EG

## [5] program_id [M/O]

15

## – specifiestheidentifiersofthecommercialseries containedinthisOFMLpackage

## Multipleidentifiershavetobeseparatedbysemicolons.

## Mandatory key for packages of type product. For packages of type catalog the identifiers of all commercial

## series of the referenced packages have to be declared here if they are not defined in the registration file of

## thesepackages.

## A series ID must not contain more than 16 characters. The permitted resp. recommended characters are

## specifiedin[ocd]. TheIDsmustbespecifiedexactlyasstoredintheOCDdata.

15
definitionsee[glos]

DSR3.7 20

<!-- Page 23 -->

5 REGISTRATIONOFOFMLPACKAGES

## Each identifier should be used only once in all packages (of the manufacturer). This ensures an one-to-one

## reversemapping → .

## program_id program

## If commercial series ( program_id ) are distributed across several OFML packages the following requirements

## havetobemet:

## 1. thearticlenumbersareuniqueacrossthemanufacturer(nonorepeatedoccurrenceinseveralseries))

## AND

## 2. thearticlenumbersmustbepresentinthecatalogdataoftherespectiveOFMLpackage

## Example: program_id = L1;L2;Z1

## [6] distribution_region[M]

## – definestheidentifierofthedistributionregionofthepackage

## Distributionregionsrepresentalogicalseparationfortherepositoryofcatalogdataandcommercialdata.

## PossibleidentifiersfordistributionregionsarethestatecodesaccordingtoISO–3166-1Alpha-2resp. Alpha-3

## (see[iso3166])oranyothertermcontainingthecharacters[a-z,A-Z,0-9]andstartingwithanallowedletter.

## TheidentifierofthedistributionregionformsthenameofadirectorylevelbelowtheOFMLprogram(see2.1).

## Forpackagesoftypefound (seekeytype below)withoutcatalogandcommercialdata,thisdirectorylevelcan

## beomitted.

## Example: distribution_region = DE

## [7] release_version[M]

## – definestheversionnumberfortheregisteredpackage

## There are different regulations for the structure of the version number depending whether the package is

## referencedinthedataprofileorinthecatalogprofilesofthemanufacturer:

## • If the package is referenced in the data profile, the version number has to be specified in the form

## Major.Minor.Build.

## Thepartsarewholenumbers,majornumbersstartingwith1,otherswith0.

## Forincrementingtheversionnumberafterchangesinproductdata,thefollowingregulationsarerecom-

## mended:

## Build Incrementing the Build number means a minimal change, error fixes in graphical data, pricing,

## etc.

## Minor IncrementingtheMinornumbermeansbeyondgoingchanges,e.g. removaloraddingofarticles,

## properties, property values, etc. Even a normal price update requires a increment of the Minor

## number.

## Major Incrementing the Major number means serious changes like incompatible changes in graphical

## data.

### Ifthepackagealsoisreferencedincatalogprofiles 16 ,minorandbuildnumbersareirrelevant,i.e. always

## havetobestatedas0.

## • If the package only is referenced in catalog profiles, the version number is single whole number greater

## than0(i.e. consistsonlyofamajornumber).

16
Inthiscasethedataprofileactsastheso-calledcompatibilitydataprofile.

DSR3.7 21

<!-- Page 24 -->

5 REGISTRATIONOFOFMLPACKAGES

## Inbothcases,beforereleasingachangedOFMLpackagethereleaseversionhastobeincremented. i.e. the

## versionnumberisstrictlymonotonicincreasing.

## AninstallationroutineforOFMLpackageswiththisversionnumberthencandecidewhetheranupdateofthe

## libraryisnecessary.

## Theversionnumberisindependentofthedistributionregion. Thiswayseveralpackageswithinonemanufac-

## turercanhaveidenticalversionnumbers. Then,thesenumbershavetohavedifferentdistributionregions.

## Example: release_version = 1.3.1

## [8] release_date [M]

## – definesthedateofthepackagerelease

## ThedateformathastobespecifiedaccordingtoISOdateformat(ISO–8601): YYYY-MM-DD(see[iso8601])

## Example: release_date = 2004-01-17

## [9] release_timestamp [O]

## – specifiesthefinalcreationtimeofthepackage.

## ThetimeisnormalizedtoUTC(s. [utc])andgiveninthefollowingformat: yyyyMMddhhmmss

## Example: release_timestamp = 20100204145736

## Itisrecommendedtospecifythekeyrelease_timestamp,becauseitallowstheapplications–togetherwiththe

17

## keysrelease_version andrelease_date –toreliablydetectwhetheranewpackageversionisinstalled .

## [10] release_state [O]

## – definesthereleasestatusofthepackage

## Possible values are: alpha, beta, rc, test, final. For all none empty values deviating from final the

## softwaresystemdisplaysamessage(seerelease_text).

## Example: release_state = final

## [11] release_text [O]

## – definesastatetextwhichcanbedisplayedbythesoftwaresystem

## (seerelease_state).

## Example: release_text = Non official test version!

## [12] version[M]

## – definesthemajornumberoftheregisteredpackage

## Thisversionmustbeidenticalwiththemajornumberofthekeyrelease_version.

## Theversionnumberbuildsthename-spaceinsidetheOFMLpackageandadirectoryunderneaththedistribu-

## tionregion. Bothmustbemaintainedsynchronouslywithinonelibrary(see2.1.)

## Example: version = 1

17
comparedtothetimewhenagivenprojectwaslastsavedorupdated

DSR3.7 22

<!-- Page 25 -->

5 REGISTRATIONOFOFMLPACKAGES

## [13]

## languages [M]

## – definesthelanguagessupportedbythepackage

## Alllanguageidentifieraredouble-digitlowercasevaluesaccordingtoISOlanguagecodes(ISO–639-1). Sev-

## erallanguagesareseparablebysemicolon.

## Ifthesoftwaresystemdemandsalanguagenotmentionedhere,thestandardlanguageofthepackagewillbe

## used. Thestandardlanguageisthefirsttermedlanguageinthelist.

## Example: languages = de;en;fr;nl;es

## [14] type [M]

## – definesthetypeofthepackage

## Thefollowingtypesareallowed:

## Type Description

## found basicOFMLlibrarywithoutproductandcatalogdata

## product OFMLlibrarywithproductdataandoptionalcatalogdata

## catalog Catalogdatawithoutproductdata

## Example: type = found

## [15] productdb [O]

## – containstheclassnamefortheproductdatabase

## ThefullqualifiedOFMLclassname(see[ofml])isrequired.

## Example: productdb = ::ofml::xoi::xOiNativeOCDProductDB21

## [16] productdb_path[O]

## – definesthepathtothefilesoftheproductdatabase

## Thepathisrelativelytothedatarootdirectory.

## Example: productdb_path = ofml/goiex/DE/1/db

## [17] oam_path[O]

## – definesthepathtotheOAMdatabase

## Thiskeyismaintainedlikeproductdb_path.

## Bydefault: <productdb_path>/../oam

## Example: oam_path = ofml/goiex/DE/1/oam

DSR3.7 23

<!-- Page 26 -->

5 REGISTRATIONOFOFMLPACKAGES

## [18]

## mddb_path[O]

## – definesthepathtotheMetaDialogdatabase

## Thisislocatedbydefaultin:

## <data>/($manufacturer)/($program)/($version)

## Thiskeyisspecifiedlike productdb_path .

## Example.: mddb_path = ofml/goiex/1/md

## [19] proginfo [O]

## – definesthenameoftheprograminformationclass

## ThefullqualifiedOFMLclassname(see[ofml])isrequired.

## Example: ::ofml::goiex::gOiExProgInfo

## [20] proginfodb_path[O]

## – definesthepathtotheprograminformationdatabase

## Thisislocatedbydefaultin:

## <data>/($manufacturer)/($program)/($version)

## The path is relatively to the data root directory. It is effective only if in the default path is no info DB (That

## means, an Info-DB in the default path of the OFML program has precedence over an possibly existing DB in

## proginfodb_path).

## Example: proginfodb_path = ofml/oi/1

## [21] category [M/O]

## – determinatesacategoryforthelibrary

## A category defines in which planning hierarchy objects from the library are inserted. Mandatory key for pack-

## agesoftypeproduct.

## Category Description

## furniture Furnitureandarticlesplacedlikefurniture

## building Roomorbuildingelements

## undefined Basicornotassignablelibrary

## Example: category = furniture

## [22] depend [O]

## – definesthepackageswhicharerequiredbeforeloadingthispackage(dependencies).

## Severalpackagesareseparatedbysemicolon.

DSR3.7 24

<!-- Page 27 -->

5 REGISTRATIONOFOFMLPACKAGES

## The list should be irreducible, i.e. contain only packages directly required for this package. Keep in mind that

## thegivenpackagesmayhavedependencies,too(riskofcyclicdependencies).

## Keysyntax: ::($manufacturer)::($program)::($release_version)/($distribution_region);...

## Thedeclarationofminorandbuildnumbersin release_version isoptional.

## Thereleaseversionwillbeverifiedbytheapplicationifthepresentpackagewasloadedfromadataprofile,or

### ifrequiredpackageisnotlistedinthecatalogprofile,fromwhichthepresentpackagewasloaded 18 .

## For catalog profiles compliance with the dependencies between the packages listed therein is presupposed.

## The applications processing catalog profiles are free whether they verify the dependencies anyhow. Alterna-

## tively,verificationalsomaytakeplacewhithintheinstallationroutine.

## If the release version is verified by the application, the following conditions must be fulfilled in order that the

## currentlyinstalledversionoftherequiredpackagecanbeused:

## • If the required package is not listed in the data resp. catalog profile, the major number of the installed

## version has to exactly match the major number given in this key. Otherwise, the major number of the

## installedversionmustbegreaterthanorequaltomajornumbergiveninthiskey.

## If both major numbers identical, and if the minor number is given in this key, the minor number will be

## examined,too:

## • Theminornumberoftheinstalledversionmustbegreaterthanorequaltotheminornumbergiveninthis

## key.

## If both minor numbers identical, and if the build number is given in this key, the build number will be

## examined,too:

## • Thebuildnumberoftheinstalledversionmustbegreaterthanorequaltothebuildnumbergiveninthis

## key.

## Example: depend = ::ofml::goi::1.2.0/ANY;::ofml::xoi::1.11.10/ANY

## [23] cat_type [O]

## – definesthecatalogtypeforthispackage.

## Thekeystructurefollowsthisform:

## cat_type=<Type>[:<Version>[.<MinorVersion>[.<SubMinorVersion>]]][/<PhysicalFormat>]

## Thefollowingtypesaredefined:

## cataloginXCFFormat(Default)

## XCF

## OAS cataloginOASFormat

## NULL Packagewithoutcatalog

## (Thisexplicitlypreventsthedisplayofanyexistingcatalogdata.)

## The(optional)versionspecificationindicatestheversionusedforcatalogtypeswithversioneddataformats.

## Currently,thefollowingphysicalformatsaredefined(optional):

## • CSV (Default)

## Example 1: cat_type = XCF:1.8/CSV

## Example 2: cat_type = NULL

18
ThelatternormallyonlyappliestobasicOFMLlibraries,becausetheyarenotprovidedbythemanufactureritself.

DSR3.7 25

<!-- Page 28 -->

5 REGISTRATIONOFOFMLPACKAGES

## [24]

## catalogs [M/O]

## – specifiesthelibrariesreferencingarticlesfromthislibrarywithinitscatalogdata

## Ifarticlesofthepresentpackagearereferencedinthecatalogdatafromotherlibraries,theselibrarieshaveto

## be specified in this key, otherwise, in certain application scenarios the catalog entry required for the insertion

## ofanarticlecannotbedeterminedorsearchingthecatalogforanarticlecanfail.

## Severallibrarieshavetobeseparatedbysemicolon.

## Keysyntax: ::($manufacturer)::($program)::;...

## The application uses the packages of the specified OFML libraries, which are listed in the same data resp.

## catalogprofilefromwhichthepresentpackagehasbeenloaded.

## Example: catalogs = ::egr::office::;::egr::office_np::

## [25] oap_program[M/O]

## – specifiesthelibrarythatcontainstheOAPdataforthearticlesofthepresentlibrary

## Ifthekeyismissing,theOAPdata[oap]isexpectedinthepresentlibraryitself.

## Keysyntax: ::($manufacturer)::($program)::

## TheapplicationusesthepackageofthespecifiedOFMLlibrary,whichislistedinthesamedataresp. catalog

## profilefromwhichthepresentpackagehasbeenloaded.

## [26]

## pd_format [M/O]

## – definestheusedproductdataformat

## This key is mandatory for packages containing commercial data. All other packages explicitly should use the

## valueNULL.

## Thefollowingformatsaredefined:

## • OCD_2.1,OCD_2.2,OCD_3.0,OCD_4.0,OCD_4.1,OCD_4.2,OCD_4.3

## • NULL (nocommercialproductdata)

## Example: pd_format = OCD_4.3

## [27] meta_type [O]

## – indicateswhetheraninstantiationincontextofOFML–MetaTypesispossible.

## Ifthiskeyisgivenandnotempty,articlesmightbeencapsulatedbyanOFML–MetaType.

## ThegivenfunctioninthesecondpartofthevaluewillbeusedtoidentifythearticlespecificOFML–MetaType.

## The definition of the OFML type before the function is necessary to guarantee the evaluation of the OFML

## classes. ThegivenfunctionhastobeimplementedfortheOFMLtypeexplicitlyorimplicitly.

## Example: meta_type = ::ofml::go::GoMetaType;::ofml::go::goGetMetaType()

## [28] features [O]

## – definesspecialfunctionsallowedforthispackage

## Severalfunctionsareseparatedbysemicolon.

DSR3.7 26

<!-- Page 29 -->

5 REGISTRATIONOFOFMLPACKAGES

## Thefollowingfunctionkeysareavailable:

## Key Description

## showInitProgressDlg Aprogressdialogisdisplayedduringinitialization

## (obsolete) oftheproductdatabase.

## editableCatalog Usersareallowedtoeditthecatalog

## (obsolete) atruntime.

## programProperties Thispackageprovidesstaticpropertiesforthe

## (obsolete) ProgInfoobject.

## useMetaDialogs Thispackageprovidesspecificconfigurationdialogues.

## maySetFinalArticleSpec Hastobespecified,iftheuserisenabledtoenter(possiblyincomplete)final

## articlenumbersinordertocreatespecificarticlevariants(i.e.,thearticle

a

## willbecreatedwiththeconfigurationencodedbythefinalarticlenumber) .

a
Forreasonsofperformanceandinordertoavoidpotentialproblemsduringevaluationoffinalarticlenumbers,thisfeatureshouldbe
setonlyifthecodingschemereallyallowsfortheprocessingofentered(possiblyincomplete)finalarticlenumbers.

## Example: features = useMetaDialogs;maySetFinalArticleSpec

## [29] series_type [O]

## – definesspecifictypesforthepackage

## Thiskeycontrolstypespecifichandlings. Severaltypescanbeseparatedbysemicolon.

## Thefollowingvaluesaredefined:

## Value Description

## go_meta supportofOFML–MetaTypes1.x

## Example: series_type = go_meta

## [30] special_article_scheme [O]

## – determinesaspecificformattingforarticlenumberofspecialmodels

## The value can contain any alphanumeric characters and the substitution characters ’?’ and ’*’. A ’?’ will be

## replaced by a characters of the original basic article number. The replacement take place in order from the

## first character of the basic article number. A ’*’ will be replaced by the whole basic article number. By default

## ’SPECIAL*’isused(languagedependent).

## Example: special_article_scheme = CS??????

## [31] gtin_id [O]

## – ThiskeyspecifiestheGTIN(GlobalTradeItemNumber)forthepackage(see[gtin]).

## The length of the key may be 8, 12, 13 or 14 digits, according to the different schemes GTIN–14, GTIN–13,

## GTIN–12orGTIN–8.

DSR3.7 27

<!-- Page 30 -->

5 REGISTRATIONOFOFMLPACKAGES

## [32]

## masked_catalogs [O]

## – Determinesthevisibilityofacataloginspecificapplications

## The catalog data of a package can be marked as „not to show“ in certain applications. The applications are

## defined by the standard module keys and an optional version number. If specified the version number part

## requiresanexactmatch. Thepackageisstillregisteredandifnecessaryloadedbutnotshownregularly.

## Theformationruleofthekeyis:

## masked_catalogs=<ModuleKey>[:<Version>[.<MinorVersion>[.<SubMinorVersion>]]][;...]

## Versionreferstotheversionofeachmodule.

## Example: masked_catalogs = P-PL-X:6.3.0;P-XCAD:2

## [33] add_gfx_symbols.<format> [O]

## – definestheOFMLlibrary,whichcontainsadditionalgraphicsymbolsinthespecifiedformat

## Theadditionalgraphicsymbolscanbeusedbyanapplicationtogenerateagraphicforarticlesfromthepresent

## packageinthespecifiedformat.

## Keysyntax: ::($manufacturer)::($program)::

## TheapplicationusesthepackageofthespecifiedOFMLlibrary,whichislistedinthesamedataresp. catalog

## profilefromwhichthepresentpackagehasbeenloaded.

## Currently,thefollowingformatsaresupported:

## Value Description

## skp Sketchup

# 5.4 Language dependent keys

## The registration files can contain several section of language dependent texts. A section will be started with

## a section name within squared brackets. The name of the language dependent sections corresponding to

## the double-digit ISO language codes (ISO–639-1) (see [iso639-1]). The succeeding keys are permitted to

## use in each of these sections. Each key overwrites a possibly given value in a manufacturer resp. concern

## registration.

## Languageindependentkeysarenotfoundinalanguagedependentsectionandarenotallowedthere.

## [34] manufacturer_name [O]

## – definesthenameofthemanufacturerresp. supplier

## [35] program_name [M]

## – definesthenameofthelibrary

## Example: program_name = Office elements

## [36] copyright [O]

## – containsthecopyrightnote

DSR3.7 28

<!-- Page 31 -->

5 REGISTRATIONOFOFMLPACKAGES

## Example: copyright = EasternGraphics 2004

## [37] description[O]

## – containsashortdescriptionforthelibrary

## Example: description = Examples for the creation of OFML and product data

DSR3.7 29

<!-- Page 32 -->

5 REGISTRATIONOFOFMLPACKAGES

# 5.5 Example

## egr_office2_EGR_1.cfg :

### # manufacturer information

### manufacturer=egr

### manufacturer_id=EG

### # package information

### program=office2

### program_name=Office, V.2

### program_id=OFFICE2

### # catalog information

### type=product

### category=furniture

### languages=en;de;es;fr;it;nl;pl;ru

### distribution_region=EGR

### version=1

### release_version=1.0.19

### release_date=2016-02-23

### release_timestamp=20160225135032

### cat_type=XCF

### # product database

### pd_format=OCD_4.0

### productdb=::ofml::xoi::xOiNativeOCDProductDB40

### productdb_path=egr/office2/EGR/1/db

### oam_path=egr/office2/EGR/1/oam

### # program information

### proginfo=::ofml::xoi::xOiProgInfo

### proginfodb_path=egr/office2/1

### # relations and dependencies

### depend=::ofml::go::1.14.9/ANY

### # additional settings

### series_type=go_meta

### meta_type=::ofml::go::GoMetaType;::ofml::go::goGetMetaType()

### geo_export_params=use_proxy_geometries

### [de]

### program_name=B¨uroelemente

### [en]

### program_name=Office elements

DSR3.7 30

<!-- Page 33 -->

6 DATATYPESANDFILETYPES

# 6 Data types and file types

# 6.1 OFML and picture data

## TheOFMLdataofanOFMLpackageisstoredindependentofthedistributionregioninthedirectory:

## <data>/($manufacturer)/($program)/($version)

## This directory defines the name-space. Out of it results the formation regulation for the name of the OFML

## archive( *.alb ). ThefollowingfileformatsareamongtotheOFMLandgraphicdata:

## Use Filename Extension

## OFMLarchives $manufacturer_$program_$version alb

### OFMLclasses ∗ $name cls

∗

## Textresources $program_$lang-code sr

### 3Dgeometries ∗ $name geo(+vnm),3ds,dwg,obj

∗

## 2Dsymboles $name egms,dwg

∗

## Textures/imagemaps $name jpg,png

### OFMLmaterials ∗ $name mat

## EBasedatabase $name ebase

## CSVdatabase $name csv

## Materiallibraries $name mli

## The file name is formed by the name of the object ($name) or by values ($manufacturer), ($program) in the

## registrationfiles.

∗

## All types marked with could and should be stored in the OFML archive. For extended data distribution

## conceptsthiswilllikelygetmandatory.

## CSVdatabasesshouldberemovedfromdistributiondataaftertheconversiontothehigh-performanceEBase

19

## format .

## Ifthepackagedoesnotcontainanyoftheabovedata,thedirectorycanbeomitted.

# 6.2 OFML product data

## Productdatahereinthenarrowersensereferstocommercialdata[ocd]. Thisisstoredinthedirectory

## <data>/($manufacturer)/($program)/($distribution_region)/($version)/db

## inadatabase.

# 6.3 XCF catalog

## ThecatalogdataoftheOFMLpackageinXCFformat[xcf]isstoredinthedirectory

## <data>/($manufacturer)/($program)/($distribution_region)/($version)/cat

19
EBaseisadatabaseinbinaryformatdevelopedbyEasternGraphicsforread-onlyaccess.AnEBasedatabaseisgeneratedbymeans
ofatabledescriptionfilefromtextfileswithfixedorvariablefieldlength(e.g. CSV).ThetoolforcreatinganEBasedatabaseandthe
descriptionfilesforthedifferenttypesofOFMLdatacanberequestedfromEasternGraphics.

DSR3.7 31

| Filename |
| --- |
| $manufacturer_$program_$version |
| $name |
| $program_$lang-code |
| $name |
| $name |
| $name |
| $name |
| $name |
| $name |
| $name |

<!-- Page 34 -->

6 DATATYPESANDFILETYPES

# 6.4 Specific resources

## Specificresourcesarestoredseparatelyinsub-directoriesof:

## <data>/($manufacturer)/($program)/($distribution_region)/($version)

## These can include HTML documents, pictures, videos and other data. The use of that data is optional for the

## softwaresystem. Thepredefinedresourcetypesarecoveredbelow.

## Resourcesofothertypesnotexplicitlymentionedbelowaretobestoredindirectory:

## <data>/($manufacturer)/($program)/($distribution_region)/($version)/etc

## 6.4.1 Catalogimages

## Theimagefilesreferencedfromthecatalogarestoredinthedirectory:

## <data>/($manufacturer)/($program)/($distribution_region)/($version)/image

## TheimagedatacanalsobeusedfortheprintoutorforareferenceinHTML-documents.

### TheformatoftheimagefilehastobeJPEGorPNG 20 .

## ThefilesinthisdirectorycanbealsostoredinaZIParchiveimage.zip(seealsosection2.1).

## 6.4.2 Materialimages

## Materialimagesarepicturedatathatareusedforthevisualizationofmaterialcharacteristicsor,moregenerally,

### ofpropertyvalues 21 .

## The names of the image files (without filename extension) are determined based on the property key and the

## propertyvalueusingtheOFMLinterfaceProperty.

## Thegraphicfileformatusedisdeterminedbythefilenameextension. JPEGandPNGformatsareallowedfor

22

## materialimages,withpreferencegiventoaPNGformatfile .

## Twowaysofstoringthematerialimagesaresupported:

## 1. Thisolderwaysupportsasmalliconwithdefaultimagesizeof50x18pixels(widthxheight)andalarger

## squareimagewithdefaultimagesizeof50x50pixels.

## Thesearestoredinthedirectory:

## <data>/($manufacturer)/($program)/($distribution_region)/($version)/mat

## Thefilenameforthesquareimageisformedbyappendinganunderscoretotheactualimagename.

### Example:

### small:

### <data>/($manufacturer)/($program)/($distribution_region)/($version)/mat/material.jpg

### square:

### <data>/($manufacturer)/($program)/($distribution_region)/($version)/mat/material_.jpg

20
Forimageformatconventionsseesection6.5.
21
e.g.withinthepropertyeditor
22
Forgeneralimageformatconventionsseesection6.5.

DSR3.7 32

<!-- Page 35 -->

6 DATATYPESANDFILETYPES

### 2. Inordertogivetheapplicationsmoredesignoptionsforthepresentation 23 ,inthisnewwaythematerial

## imagescanbeprovidedinfollowing3sizes:

## • smalliconforcompactpresentation: 200x72(widthxheightinpixels)

## • medium(square)icon: 200x200pixels

## • largeimageforthematerialresp. propertyvaluepreview:

## – theimagemayhaveamaximumedgelengthof2000pixels

## – asarecommendation,thelongestedgeshouldbeatleast1000pixelslong

## – thereisnospecificationabouttheaspectratio

## Thefilesforthedifferentimagesizesarelocatedincorrespondingsubdirectoriesof

## <data>/($manufacturer)/($program)/($distribution_region)/($version)/mat

## s –smallicons

## m –mediumicons

## l –largeimages

## The creation of the subdirectory l is optional. In addition, it is not necessary to store an image there

## for all property values. An image only needs to be stored if a material resp. property value preview is

## requiredforagivenvalue.

### Example:

### small:

### <data>/($manufacturer)/($program)/($distribution_region)/($version)/mat/s/material.jpg

### medium:

### <data>/($manufacturer)/($program)/($distribution_region)/($version)/mat/m/material.jpg

### large:

### <data>/($manufacturer)/($program)/($distribution_region)/($version)/mat/l/material.jpg

## Foravisuallygoodrepresentation,thefollowinggeneralrecommendationsapply:

## • Materialimagesshouldnothaveunnecessarywhitespace.

## • Materialimagesmustnothaveaframe/borderorthelike.

## Thedisplayofmaterialimagesbytheapplicationsisoptionalandtheformofthepresentationdependsonthe

## application. Theapplicationsareresponsibleforscalinganddisplayingtheimagescorrectly.

## Ifthereisnosubdirectorysornosubdirectorym,theprevioussmallerimageswillcontinuetobeused(accor-

## dingtotheolderwayofdatacreation).

## Ifthereisasubdirectorysandasubdirectorym,onlytheimagesstoredtherewillbeusedbyapplicationsthat

## support this new way of data creation. This means that there is no fallback to images according to the older

## wayofdatacreationiftherearenoimagesinsubdirectorysresp. subdirectorymforindividualpropertyvalues.

## Thus,ifallapplicationsaretobesupportedwiththebestpossibledisplayquality,thematerialimagesmustbe

## providedaccordingtoboththeolderandthenewwayofdatacreation.

## Thefilesindirectory(includingsubdirectorieswiththesecondstoragevariant)

## <data>/($manufacturer)/($program)/($distribution_region)/($version)/mat

## canbealsostoredinaZIParchivemat.zip(seealsosection2.1).

23
includingsupportofhigh-resolutiondisplays

DSR3.7 33

<!-- Page 36 -->

6 DATATYPESANDFILETYPES

## 6.4.3 HTMLfiles

## HTMLfilesreferencedinthecatalogdatacanbestoredinthedirectories:

## <data>/($manufacturer)/($program)/($distribution_region)/($version)/html/($language)

## <data>/($manufacturer)/($program)/($distribution_region)/($version)/html

## Foreachsupportedlanguageasubdirectorycanbecreatedwiththerespectivetwo-letterISOlanguagecode

## (ISO639-1)asthedirectoryname. AreferencedHTMLfilealwaysfirstislookedforinthelanguage-specificdi-

## rectoryaccordingtothecataloglanguagecurrentlysetintheapplication,regardlessofwhethertheassociated

## resourceinthecatalogitselfislanguage-specificornot.

## HTMLfilescanreferenceimagedatafromthepicturedatadirectory.

## 6.4.4 Configurationsandgeometries

## Configurations(.fml),OFMLgroups(.ogrp),geometries(.3ds,.dwg)aswellascontainerfiles(.pec)referenced

## inthecatalogdataarestoredhere:

## <data>/($manufacturer)/($program)/($distribution_region)/($version)/etc

## 6.4.5 Articlespecificviewsetup

## Atablewithanarticlespecificviewsetup[asv]canbestoredin:

## <data>/($manufacturer)/($program)/($distribution_region)/($version)/etc/artsetups.csv

## Thisviewsareinterpretedapplicationspecific.

## Primarily the table from that OFML package is employed whose catalog data was used to create the article.

## AlternativelythetablefromthatOFMLpackageisemployedwhichisreferencedinthecatalogdata.

# 6.5 Image format conventions

24

## Imagesin JPEG formathavetocomplywiththespecificationofthe"JPEGFileInterchangeFormat(JFIF)"

## • havetobesequentiallystructured(notinterlaced/progressive)

## • havetouseHuffmancoding(notarithmeticcoding)

## • havetousetheYCbCrcolormodel(noCMYK,noblack/white)

## • havetouse8bitpercolorchannel(nomore)

### ImagesinPNGformathavetocomplywiththe"PNG(PortableNetworkGraphics)Specification,Version2.2" 25 :

## • havetobesequentiallystructured(notinterlaced/progressive)

## • havetousetheRGBcolormodel(3colorchannels,notless,i.e.,noblack/white)

## • havetouse8bitpercolorchannel(nomore)

## • optionallyan8bitalphachannelcanbeusedfortransparentimages

## • animatedPNGs(APNG)arenotsupported

## Embeddedmetadata(thumbnails,EXIF,IPTC,ICCprofiles,printinginformation)areignored(notevaluated)in

## bothformats.

24
http://www.w3.org/Graphics/JPEG/jfif3.pdf
25
http://libpng.org/pub/png/spec/1.2/png-1.2-pdg.html

DSR3.7 34

<!-- Page 37 -->

6 DATATYPESANDFILETYPES

# 6.6 Price profiles

## Priceprofiles[ppr]installedinconjunctionwithcatalogsofamanufacturerresp. abrand(seekey ppr_version ,

## section3.3.2)havetobelocatedindirectory

## <data>/($brand)/priceprofiles/($ppr_version)/

## This means that for a catalog only one price profile can be specified and this has to be installed under the

26

## brandunderwhichthecatalogislisted(seekey brand ,section3.3.2) .

## Priceprofilesassociatedwithaconventionaldatasetofamanufacturerhavetobelocatedindirectory

## <data>/($manufacturer)/priceprofiles/

## If a manufacturer registers data both via a catalog profile and a compatibility data profile, accordingly 2 price

## profileshavetobeprovidedintheabovementionedpaths.

26 Therefore,ifthecatalogcontainsdatafrommultiplemanufacturers,possiblyexistingmanufacturer-specificpriceprofileshavetobe
mergedintoacommonpriceprofile.

DSR3.7 35

<!-- Page 38 -->

7 HISTORY

# 7 History

3.2
3.7.0 -Specificationregardingcommentlinesindataprofiles
-Newoptionalkeyencodingindataprofiles 3.2.1
4.2.1,4.2.2
-Clarificationoftheuseofkeyencodingintheregistrationofmanufacturers
4.2.2
-Removedunusedkeysort_namesfromtheregistrationofmanufacturers
5.1
-Clarificationofcharacterencodingincommentlinesinpackageregistrationfiles
-OnlyvalueUTF-8is(currently)supportedforthekeyencoding 5.3
-Thekeydistribution_regionnowismandatory,butthecorrespondingdirectorylevelcanbeomittedforpackagesof
5.3
typefound
5.3
-Removedobsoletevalueextensionforkeytype
5.3
-ADLMisnolongerrequiredforthekeymeta_type
-FunctionsdenyFreePosanddeny3DFdbMoveinkeyfeaturesarenolongersupported 5.3
5.3
-FunctionsshowInitProgressDlg,editableCatalogandprogramPropertiesinkeyfeaturesmarkedasobsolete
-Removedobsoletekeysprogid_3d,layer_progid_2d,layer_progid_3d,block_progid_2d,block_progid_3dand
5.3
geo_export_params
-Removedobsoletekeypersistency_form 5.3
-Updateinsection6.1regardingthesupportedformatsof3Dand2Dgeometryfiles
-Clarificationinsection 6.1thatthedirectorycanbeomittedifthepackagedoesnotcontainanyofthementionedOFMLdata
6.1
-Accordingtospecification[omats],formatsTGAandBMParenolongerpermittedfortexturesandimagemaps
-Someminorclarifications
3.6.0 -Clarificationontheuseofsubdirectoriesinarchivemat.zip 2.1
-Theregistrationofmanufacturers(section4)isnowdescribedbeforetheregistrationofpackages(section5)
-Moreprecisespecificationsinsections4.1and4.2
4.2.2
-Indexsuffixestospecifyamultilinetextnowareallowedonlyinthekeysofgroupaddressformanufacturerregistration
4.2.2
-Newkeys external_catalog.url und external_catalog.name fortheregistrationofmanufacturers
-Removedobsoletekeymodule_depends 5.3
4.2.2,5.3,5.4
-Removedkeyssupplier_idanddistributor_name
5.3,5.4
-Removedkeysconcern_id,ppr_region_idandconcern_namefromthepackageregistration
5.4
-Keymanufacturer_nameisnowoptionalinpackageregistration
3.5.1 -Markedkeysprogid_3d,layer_progid_2d,layer_progid_3d,block_progid_2d,block_progid_3dand
5.3
geo_export_params asobsolete(thecorrespondingbehaviorispartofthegraphicexportoftherespectiveapplication)
3.2
3.5.0 -Removedobsoletedataprofilesection[libdef]
5.3
-RemovedobsoletevalueISO-8859-2(ISO–Latin-2)forkeyencoding
5.3
-Keyrelease_timestamp isnolongerobsolete(butnowisoptional)
-Removedobsoletevalueattrselforkeytype 5.3
5.3
-Newkeyoap_program
5.3
-Updatedsupportedproductdataformatsinkeypd_format
5.3
-Removedobsoletekeysvisibilityandinsertion_mode
-RemovednotsupportedphysicalformatsEBASE,DBFandSQLITEwithkeycat_typeentfernt 5.3
5.3
-Defaultvalueforkeypersistency_formisnowSTATECODES
-Updatedsection5.5–Example(s)
4.2.3,4.3.3
-Thesmallmanufacturerandconcernlogoisnolongersupported,butalargerlogoisnowsupportedinstead
4.2.3,4.3.3
-PNGsupportformanufacturerandconcernlogosbytheapplicationsisnowmandatory
-Removedinvalidreferencetoxcf.ebase 6.3
6.4
-Specificationofthelocationofnon-predefinedresources
6.4.2
-MaterialimagesnowmaybeprovidedalsoinPNGformat
6.4.2
-Athirdimagesizenowissupportedforlargematerialimages
6.4.2
-Newsizesforsmallandmediummaterialimages
-Newstructureforstoringmaterialimages 6.4.2
6.4.4
-Thelocationofcontainerfilesisnowspecified
6.5
-Clarificationsregardingimageformatconventions
5.3
3.4.1 -Moreprecisespecificationregardingdefaultforkey persistency_form
3.4.0 -Newvalue maySetFinalArticleSpec forkey features 5.3
5.3
-Removedobsoletefeature freeArticles (bynow,conversionintospecialarticlesalwaysisallowed)
5.3
-Moreprecisespecificationsregardingkeys encoding , distribution_region , visibility and persistency_form
5.3
-Recommendationregardingusablecharactersinkey program_id
6.4.3
-MoreprecisespecificationregardingHTMLfilesreferencedincatalogdata
-Someminorcorrections
6.6
3.3.0 -Changedregulationsregardingpriceprofilesinconjunctionwithcatalogs
5.3
-Specifiedsetofcharactersallowedinkeys manufacturer , manufacturer_id and concern_id
5.3
3.2.0 -Newkey add_gfx_symbols
-Correctedusageofterms"library"und"package"
3.2.3
-Removedobsoletekey extpath indataprofiles
3.2.3,3.3.4
-Moreprecisespecificationregardingdeclarationofpackagesindataresp.catalogprofiles
5.3
-Moreprecisespecificationregardingusageofpackagesinkeycatalogs
-Someminorcorrections
Forolderhistoryseeolderversions.

DSR3.7 36