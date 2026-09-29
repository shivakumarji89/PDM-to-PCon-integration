# omats_2.2_en

> Auto-generated from omats_2.2_en.pdf for AI consumption.

---


<!-- Page 1 -->

# Specification

# OMATS

### *

# OFML compatible Materials

### Version 2.2

Thomas Gerth, EasternGraphics GmbH (Editor)

April 22, 2025

*
Copyright'2003–2025IndustrieverbandBu¨roundArbeitswelte.V.(IBA)

<!-- Page 2 -->

<!-- Page 3 -->

# Contents

1 Introduction 2

2 The material models 2
2.1 Overview . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2
2.2 Used data types. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
2.3 Material types . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
2.4 The material parameters . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5

3 Texture mapping methods 9
3.1 Plane mapping . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9
3.2 Block mapping . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
3.3 Texture coordinates . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10

4 OFML data format for materials 11

A Introduction into Physically Based Rendering (PBR) 14

B Conversion of older materials to the new model 15

C History 16

# References

[jfif] JPEG File Interchange Format, Version 1.02
World Wide Web Consortium (W3C)
(www.w3.org/Graphics/JPEG/jfif3.pdf)
[odb] ODB – OFML Database (OFML Part I), Version 2.4.
Industrieverband Bu¨ro und Arbeitswelt e. V. (IBA)
[ofml] OFML – Standardized Data Description Format of the Office Furniture Industry,
Version 2.0, 3rd revised edition
Industrieverband Bu¨ro und Arbeitswelt e. V. (IBA)
[png] Portable Network Graphics (PNG) Specification, Version 1.2
PNG Development Group
(www.libpng.org/pub/png/spec/1.2/png-1.2-pdg.html)

1

<!-- Page 4 -->

# 1 Introduction

This specification defines two material models which are used in OFML based applications for the repre-
sentation of object surfaces (materials), both in the real-time and in the photorealistic domain.
Furthermore, thisspecificationdescribesthesupportedtexturemappingmethodsaswellasthemapping
of abstract model parameters into OFML material definition files.
The two material models are referenced as OMATS1 and OMATS2. OMATS1 is the older model. In
newer OFML applications it is replaced by the new model OMATS2, which uses the concept of physically
based rendering(PBR).Withamorecompactmaterialdescription,thismodelallowsamorerealisticand
appealing representation in real-time mode (see appendix A for more information). In addition, material
editorsbasedonthismodelofferabetterusability,asfewerparametersneedtobesetandtherearefewer
dependencies between the parameters.
Toensuredownwardscompatibleprocessingofmaterials,thefollowingtermsapplytoOFMLapplications
which use the new model:
(cid:136)
Materials created on the basis of OMATS1 automatically are converted to the new model (see also
appendix B).
(cid:136)
Contrarytothepreviouspoint,whenexportinganOFMLmaterialdefinitionfile,missingparameters
for the processing according to OMATS1 are derived from the parameters for OMATS2 (and also
exported).

# 2 The material models

### 2.1 Overview

Each model defines a set of parameters describing specific characteristics of a material.
The parameter Material Type (s. 2.3) plays a special role: depending on the selected material type, only
certain material parameters are used during rendering.
The following table provides an overview of the defined material parameters (in alphabetical order of
their identifiers) and their correlation with the material types and the two models.
All parameters are optional, i.e. need not be specified in a material description 1 .
If a parameter is not specified, a predefined value is used. This value is specified below in the description
of each parameter.
For some parameters defined only for model OMATS2, there is no predefined value. Rather, if the
parameter specification is missing, the value is derived from OMATS1 parameters (resp. from their
default values) 2 .

1 Theoretically,thisallowsemptymaterialdescriptions.
2 Theprocedureforthisderivationisundefinedandmayvaryfromapplicationtoapplication.

2

<!-- Page 5 -->

Material type Model
Parameter
Common Glass Illuminant OMATS1 OMATS2
Base Color X X X X
Base Color Map X X X X
Clearcoat X X
Clearcoat Roughness X X
Clearcoat Normal Map X X
Emissive Color X X X
Emissive Color Map X X
Luminance X X X
Metallness X X
Metallness Map X X
Normal Map X X X X
Opacity Map X X X X
Refractive Index X X X
Roughness X X X
Roughness Map X X X
Sheen X X
Sheen Color X X
Sheen Roughness X X
Shininess X X
Sound Absorption X X X X X
Specular Color X X
Specular Factor X X
Transparency X X X X X

### 2.2 Used data types

The following data types are used in the description of the parameters:

positive integer
PI
FP floating-point number
RGB Vector of three color values representing the base colors red, green and blue
Each color value C must be in the range 0.0≤C ≤1.0.
RGB-IMAGE image file
This data type describes two-dimensional image files consisting of RGB color values.
The following formats are allowed: PNG, JPEG
The dimensions of the image files should be powers of two.
The maximum size allowed is 4.096 x 4.096, but in general textures should only be resolved
as high as necessary.
Depending on the nature of the material, the following recommendations apply:
(cid:136)
1.024 x 1.024 – very fine, highly structured materials
(cid:136)
512 x 512 – ”ordinary”materials
(cid:136)
256 x 256 – simple, low-structured materials

3

| Parameter | Material type |  |  | Model |  |
| --- | --- | --- | --- | --- | --- |
|  | Common | Glass | Illuminant | OMATS1 | OMATS2 |
| Base Color | X | X |  | X | X |
| Base Color Map | X | X |  | X | X |
| Clearcoat | X |  |  |  | X |
| Clearcoat Roughness | X |  |  |  | X |
| Clearcoat Normal Map | X |  |  |  | X |
| Emissive Color |  |  | X | X | X |
| Emissive Color Map |  |  | X |  | X |
| Luminance |  |  | X | X | X |
| Metallness | X |  |  |  | X |
| Metallness Map | X |  |  |  | X |
| Normal Map | X | X |  | X | X |
| Opacity Map | X | X | X |  | X |
| Refractive Index |  | X |  | X | X |
| Roughness | X | X |  |  | X |
| Roughness Map | X | X |  |  | X |
| Sheen | X |  |  |  | X |
| Sheen Color | X |  |  |  | X |
| Sheen Roughness | X |  |  |  | X |
| Shininess | X |  |  | X |  |
| Sound Absorption | X | X | X | X | X |
| Specular Color | X |  |  | X |  |
| Specular Factor | X |  |  | X |  |
| Transparency | X | X | X | X | X |

<!-- Page 6 -->

Theimagefilesnormallyshouldbecreatedinsuchawaythatarepetitioninbothdimensions
is visually appealing.
The naming of the image files is arbitrary.
image file with transparency
RGBA-IMAGE
Thisdatatyperepresentsanextensionoftype RGB-IMAGE andcontainsanadditionaltrans-
parency value. This either can be a scalar value or an explicit color value which digitally
3
controlsthetransparency,i.e. texels withthiscolorvaluehaveatransparentrepresentation.
The following formats are allowed: PNG
GRAYSCALE-IMAGE
grayscale image file
4
Unlike RGB-IMAGE , this type includes only one value per pixel .
The following formats are allowed: PNG, JPEG
SYMBOL symbolic identifier

Note regarding data types RGB , RGB-IMAGE and RGBA-IMAGE :
The sRGB color space is assumed for RGB color values.

Notes regarding image file formats PNG and JPEG:

Images in PNG format have to comply with the ”PNG (Portable Network Graphics) Specification”[png]:
(cid:136)
have to be sequentially structured (non-interlaced/progressive)
(cid:136)
have to use the RGB color model in case of RGB-IMAGE
(cid:136)
have to use 8 bit for a (color) channel
(cid:136)
may not be animated

Images in JPEG format have to comply with the specification of the ”JPEG File Interchange Format”
[jfif]:
(cid:136)
have to be sequentially structured (non-interlaced/progressive)
(cid:136)
have to use Huffman coding (non-arithmetic coding)
(cid:136) 5
have to use the YCbCr color model
(cid:136)
have to use 8 bit for a color channel

Images in both formats should not contain embedded metadata (thumbnails, EXIF, IPTC, ICC profiles,
etc.) 6 . If metadata is included, it must not contain any rotation 7 .

3 apixelofatexturein3Dcomputergraphics
4
Ifthereisanimagefilewith3colorchannels(RGB),thegrayvalueofthecolorisused.
5
Whenimporting,colorvaluesareconvertedtotheRGBcolormodel
6 Theseareofnousefortexturesandjustunnecessarilyincreasethefilesizeanddownloadtime.
7 Otherwisethiscanleadtoanincorrectrepresentation.

4

<!-- Page 7 -->

### 2.3 Material types

The material type (parameter Material Type of type ) is used to select an appropriate shader 8 .
SYMBOL
Furthermore,basedonthematerialtype,theavailableparametersmayberestrictedinamaterialeditor.

The following types are defined:
(cid:136)
Common
This is the recommended default type if a material can not or should not be correlated with any of
the specific material types mentioned below.
(cid:136)
Glass
This type should be assigned to all glass materials. If, instead, type Common is used, it may be
the case that the material looks like a transparent plastic.
(cid:136)
Illuminant
Type for self-luminous objects. Useful in conjunction with parameter Luminance.

If this parameter is not specified, the application autonomously determines a matching shader using
heuristics based on the (other) specified parameters (which then possibly might not deliver the desired
9
results) .

### 2.4 The material parameters

Preliminary remarks:
The parameters are listed in alphabetical order. The identifier of the parameter is followed by the data
type in square brackets as well as the corresponding material types and models in curly brackets.

(cid:136)
Base Color [RGB] {Common, Glass, OMATS1, OMATS2}
The base color is used to simulate the diffuse reflection characteristics of the object’s surface. In
the model OMATS2, for metals the parameter also serves to determine the color and intensity of
the specular reflection.
The predefined value is 1.0,1.0,1.0 (white).

(cid:136)
Base Color Map [RGB-IMAGE, RGBA-IMAGE, GRAYSCALE-IMAGE] {Common, Glass, OMATS1, OMATS2}
The referenced image file is used as a compensating description for parameter Base Color.
Additionally,inthecaseofanRGBA-IMAGE,thetransparencyvaluesresultingfromthealphachannel
are used as a compensating description of parameter Transparency.
In the case of a GRAYSCALE-IMAGE , the (single) value is used for all 3 color channels.
There is no predefined image file for this purpose.
For details regarding the texture mapping methods see section 3.

(cid:136)
Clearcoat
[FP] {Common, OMATS2}
This parameter allows to simulate a layer of clearcoat on top of the underlying surface.
The values are in the range of 0.0 to 1.0 and control the strength of the clearcoat layer.
The predefined value is 0.0 .

8
Shadersareprogramsforcalculatingrenderingeffects,e.g. forthespatialperceptionof3Dmodels.
9 Forexample,iftheluminancevalueofthematerialisgreaterthan0andthematerialisnottextured,typeIlluminant
isassumed.

5

<!-- Page 8 -->

(cid:136)
Clearcoat Normal Map
[RGB-IMAGE] {Common, OMATS2}
Allows to modify the surface normals for the clearcoat layer. If this normal map is not set, the
surface normals will be used instead. This means that the clearcoat layer is not affected by the
regular normal map (parameter Normal Map).
The values in the referenced image file are interpreted as normalized normal vectors.
There is no predefined image file for this purpose.
For details regarding the texture mapping methods see section 3.

(cid:136)
Clearcoat Roughness [FP] {Common, OMATS2}
The degree of clearcoat roughness determines how smooth or rough the surface of the clearcoat
layer is.
The values are in the range of 0.0 to 1.0 .
The predefined value is 0.0 .

(cid:136)
Emissive Color [RGB] {Illuminant, OMATS1, OMATS2}
Defines the color of the emitted light of a geometry based light source.
The predefined value is 0.0,0.0,0.0 (black).

(cid:136)
Emissive Color Map
[RGB-IMAGE, GRAYSCALE-IMAGE] {Illuminant, OMATS2}
The referenced image file is used as a compensating description for parameter Emissive Color.
In the case of a GRAYSCALE-IMAGE, the (single) value is used for all 3 color channels.

There is no predefined image file for this purpose.
For details regarding the texture mapping methods see section 3.
(cid:136)
Luminance [FP] {Illuminant, OMATS1, OMATS2}
2
Specifies the luminance of a geometry based light source in cd/m .
(Candela — cd — is the SI unit for the basic parameter light intensity.)
The predefined value is 0.0.

(cid:136)
Metallness {Common, OMATS2}
[FP]
In the real world, materials can be divided into metals and non-metals. Therefore, for most ma-
terials, this value should be 0.0 or 1.0. Intermediate values are used to represent semi-metals or
contaminated metals.

(cid:136)
Metallness Map
[GRAYSCALE-IMAGE] {Common, OMATS2}
The referenced image file is used as a compensating description for parameter Metallness:
Bright image areas receive metal characteristics, dark ones are interpreted as non-metal.
There is no predefined image file for this purpose.

For details regarding the texture mapping methods see section 3.
(cid:136)
Normal Map [RGB-IMAGE] {Common, Glass, OMATS1, OMATS2}
A normal map modifies the normal vectors of the surface in order to simulate the illumination of
unevenness that is not present in the object geometry.

6

<!-- Page 9 -->

The values in the referenced image file are interpreted as normalized normal vectors.
There is no predefined image file for this purpose.
For details regarding the texture mapping methods see section 3.

(cid:136)
Opacity Map [GRAYSCALE-IMAGE] {Common, Glass, Illuminant, OMATS2}
The referenced image file is used as a compensating description for parameter Transparency.
The values in the image file are interpreted as alpha , where transparency = 1.0 - alpha .
If parameter Base Color Map references an RGBA-IMAGE, it’s alpha channel is ignored if there is
an Opacity Map.
There is no predefined image file for this purpose.
For details regarding the texture mapping methods see section 3.

(cid:136)
Refractive Index {Glass, OMATS1, OMATS2}
[FP]
The scalar value specifies the refraction of the light in the case of transparent materials. The
refractive index refers to the ratio of the phase velocity of the light in vacuum to that in the
respective material.
Selected values are:
– water: 1.33
– glass: 1.5 ... 1.9
The predefined value is 1.0 and corresponds to the refractive index of vacuum.

(cid:136)
Roughness {Common, Glass, OMATS2}
[FP]
The degree of roughness determines how smooth or rough a surface is. Depending on the degree,
the reflected light is scattered more or less at the surface.
The values are in the range of 0.0 to 1.0.

(cid:136)
Roughness Map
[GRAYSCALE-IMAGE] {Common, Glass, OMATS2}
The referenced image file is used as a compensating description for parameter Roughness:
Bright areas of the image appear dull, dark areas appear glossy.

There is no predefined image file for this purpose.
For details regarding the texture mapping methods see section 3.

(cid:136)
Sheen [FP] {Common, OMATS2}
Sheenisanadditionalreflectionlayer,whichsimulatesmicro-fibersontopoftheunderlyingsurface.
It may be used to create velvet materials.
The parameter controls the strength of the effect, with values in the range of 0.0 to 1.0 .
The predefined value is 0.0 .

(cid:136)
Sheen Color {Common, OMATS2}
[RGB]
The color of micro-fibers (see parameter Sheen). Tints the sheen reflection.
The predefined value is 1.0,1.0,1.0 (white).

7

<!-- Page 10 -->

(cid:136)
Sheen Roughness
[FP] {Common, OMATS2}
Controls how sheen reflection distributes accross the surface.
Smallervaluesleadtosharpreflectionsatgrazingangles,whilelargervaluescausesofterreflections
accross the whole surface.
Thesheenroughnessmodelshowmuchtheorientationofthemicro-fibersdeviatesfromthesurface
normal.
The values are in the range of 0.0 to 1.0 .
The predefined value is 0.5 .
(cid:136)
Shininess
[FP] {Common, OMATS1}
The scalar value indicates the gloss for shiny surfaces. This is the integer exponent of the cos term
according to the lighting model of Phong.
As a rule of thumb: The larger this value, the smaller the gloss effect simulating the reflection of
the light source.
The predefined value is 30 .
(cid:136)
Sound Absorption
[PI {PI FP}*] {Common, Glass, Illuminant, OMATS1, OMATS2}
The parameter is a set of value pairs specifying the sound absorption coefficient (2nd value) for
different frequencies (1st value). In front of the value pairs the number of the pairs is specified.
Usually, the sound absorption coefficient is given for the following frequencies:
125Hz, 250Hz, 500Hz, 1000Hz, 2000Hz, 4000Hz.
The sound absorption coefficient is a non-negative floating point number. Usually the value is in
therangeof0.0(noabsorption)to1.0(completeabsorption). Buttherecanalsobevaluesslightly
above1.0. Thisispossibleiftheactualeffectivesurfaceofasound-absorbingobjectisgreaterthan
the geometric surface that is used for calculating the acoustics.
Example: 6 125 0.1 250 0.3 500 0.2 1000 0.1 2000 0.5 4000 0.4

If the parameter is missing in the material description, the corresponding object is not considered
during acoustics calculation.
(cid:136)
Specular Color
[RGB] {Common, OMATS1}
The specular color is used to simulate the specular reflection characteristics of the object’s surface
and also determines the color for highlights (Phong model).
The predefined value is 0.0,0.0,0.0 (black).
(cid:136)
Specular Factor [FP] {Common, OMATS1}
The weight of the specular color is used to control the intensity of the specular reflection of the
object’s surface. Highlights (Phong model) are not affected by this parameter.
The values usually are in the range of 0.0 to 1.0 .
The predefined value is 1.0 .
(cid:136)
Transparency [FP] {Common, Glass, Illuminant, OMATS1, OMATS2}
The transparency is used to simulate transparent characteristics of the material. It is a frequency-
independent scalar value.
The values are in the range of 0.0 to 1.0.
The predefined value is 0.0, which means that there is no transparency.

8

<!-- Page 11 -->

# 3 Texture mapping methods

OMATS supports the texture mapping methods described in this section.
These relate to the material parameters Base Color Map, Clearcoat Normal Map, Emissive Color Map,
Metallness Map, Normal Map, Opacity Map and Roughness Map.
All methods start with the data types , or as defined in 2.2.
RGB-IMAGE RGBA-IMAGE GRAYSCALE-IMAGE
As shown in figure 1, these images are projected onto the normalized UV coordinate space which is the
basis for all other statements in this section.

Figure 1: UV coordinate space

The following texture transformations are supported (in the specified order):
1. Rotation by the angle W
2. Translation by an U-V offset
3. Scaling in the UV space

For normal maps separate transformation parameters can be specified (related to the other maps). If no
specific transformation parameter is specified for the normal map, the corresponding parameter for the
other maps is used (if available).

### 3.1 Plane mapping

This is a planar mapping onto a given projection plane. It defines the location of the UV space and can
be selected as follows:
(cid:136)
YZ plane
(cid:136)
XZ plane
(cid:136)
XY plane
(cid:136)
Definition by a normalized normal vector

In addition, the projection plane freely can be rotated around all coordinate axes.
Translation and scaling in the UV space is supported, too.

9

<!-- Page 12 -->

### 3.2 Block mapping

This is a automatic mapping of the model coordinates onto the boundary surfaces of a paraxial oriented
block. The block defines its own UV space along each coordinate axis. If basic vectors U and V each
correspond to a canonical basic vector, the 8 base variants can be specified, as shown in figure 2.
Inversions of the block at the coordinate planes cause corresponding inversions in the UV space, and
thus lead to further variants. Translation, scaling and rotation in UV space are supported, too. The
assignment of a vertex to a side surface of the block is based on the coordinate of the normal vector with
the greatest amount.

Figure 2: Block mapping

In the triple after the keyword auto , the direction of the U vector is encoded for each side of the
block in the order: front, right, top.
(Analog the directions for back, left and bottom sides.)

### 3.3 Texture coordinates

Not always the desired result can be described by means of general mapping methods. Sometimes an
explicit specification of the UV coordinates is required. Then, these coordinates are not stored with the
material, but with the geometry itself. This eliminates the need to calculate the projection from the
model space into the UV space. Scaling, offset and rotation still are applied to the UV coordinates.
This method applies to all types of maps.
How the texture coordinates are stored depends on the geometry format, i.e. the specification of texture
coordinates must be provided there. For this purpose formats 3DS and OBJ can be used.

10

<!-- Page 13 -->

# 4 OFML data format for materials

Preliminary note:
ThestatementsinthissectionreplaceandupdatethestatementsinappendixD.2”Materials”from[ofml]!

The definition of an OFML material consists of a set of parameters. A parameter is comprised of a key
10
that defines the meaning of the parameter, followed by space-separated arguments . The tables below
define the currently supported keys and corresponding arguments.
Amaterialdefinitioncanberepresentedintwoformats, whichdifferessentiallyintheformofseparation
of the parameters:
(cid:136)
material definition file
The parameters are separated by the end of the line.
The name of a material definition file (extension .mat ) results from the last component of the fully
qualified name of the material which is used to reference it in the OFML data (e.g. ODB, OFML
11
part I [odb]), where the file name is spelled with lower case .
(cid:136)
inline declaration
The parameters are separated by a semicolon (’ ; ’).
Inline declarations can be used in OFML programming according to part III of the OFML specifi-
cation [ofml] or in ODB data [odb].
Inline declarations can be specified in two forms:
– Pure inline declarations start with the dollar character (’$’) and contain a complete material
definition.
– Material modifiers start with a fully qualified material name that refers to a material in the
OFML database (basic material). This is followed by individual parameters, separated by a
semicolon, which overwrite the corresponding parameter of the basic material.

The syntactic and lexical elements used in the description of the arguments in the following tables are
described in the legend at the end of this section.

10
Therearealsoparameterswithoutarguments.
11 The name of a material – without the prepended package name space – should follow the rules for OFML identifiers,
i.e. shouldcontainonlyalphanumericcharacters(includingtheunderscore)andnotbeginwithadigit.

11

<!-- Page 14 -->

The following table defines the corresponding keys and arguments for all currently supported model
parameters (see section 2):

Parameter Model Key Argument(s)
Material Type 1, 2 type (common|glass|illuminant)
Base Color 1, 2 dif R[F1] G[F1] B[F1]
Base Color Map 1, 2
tex image FT[FT] FN[FN]
Clearcoat 2 clearcoat S[F1]
Clearcoat Normal Map 2 clearcoat_bumps FT[FT] FN[FN]
Clearcoat Roughness 2 clearcoat_roughness S[F1]
Emissive Color 1, 2 emission R[F1] G[F1] B[F1]
Emissive Color Map 2 emission image FT[FT] FN[FN]
Luminance 1, 2 luminance S[F]
Metallness 2 metallic S[F1]
Metallness Map 2
metallic image FT[FT] FN[FN]
Normal Map 1, 2 bumps FT[FT] FN[FN]
Opacity Map 2 opacity image FT[FT] FN[FN]
Refractive Index 1, 2 refraction S[F]
Roughness 2 roughness S[F1]
Roughness Map 2 roughness image FT[FT] FN[FN]
Sheen 2 sheen S[F1]
Sheen Color 2 sheen_color R[F1] G[F1] B[F1]
Sheen Roughness 2
sheen_roughness S[F1]
Shininess 1 shi S[F]
Sound Absorption 1, 2 sndabsorb N[I] {F[I] C[F]}*
Specular Color 1 spe R[F1] G[F1] B[F1]
Specular Factor 1 reflection S[F]
Transparency 1, 2 tra S[F1]

(Legend see below next table.)

12

| Parameter | Model | Key | Argument(s) |
| --- | --- | --- | --- |
| Material Type | 1, 2 | type | (common|glass|illuminant) |
| Base Color | 1, 2 | dif | R[F1] G[F1] B[F1] |
| Base Color Map | 1, 2 | tex image | FT[FT] FN[FN] |
| Clearcoat | 2 | clearcoat | S[F1] |
| Clearcoat Normal Map | 2 | clearcoat_bumps | FT[FT] FN[FN] |
| Clearcoat Roughness | 2 | clearcoat_roughness | S[F1] |
| Emissive Color | 1, 2 | emission | R[F1] G[F1] B[F1] |
| Emissive Color Map | 2 | emission image | FT[FT] FN[FN] |
| Luminance | 1, 2 | luminance | S[F] |
| Metallness | 2 | metallic | S[F1] |
| Metallness Map | 2 | metallic image | FT[FT] FN[FN] |
| Normal Map | 1, 2 | bumps | FT[FT] FN[FN] |
| Opacity Map | 2 | opacity image | FT[FT] FN[FN] |
| Refractive Index | 1, 2 | refraction | S[F] |
| Roughness | 2 | roughness | S[F1] |
| Roughness Map | 2 | roughness image | FT[FT] FN[FN] |
| Sheen | 2 | sheen | S[F1] |
| Sheen Color | 2 | sheen_color | R[F1] G[F1] B[F1] |
| Sheen Roughness | 2 | sheen_roughness | S[F1] |
| Shininess | 1 | shi | S[F] |
| Sound Absorption | 1, 2 | sndabsorb | N[I] {F[I] C[F]}* |
| Specular Color | 1 | spe | R[F1] G[F1] B[F1] |
| Specular Factor | 1 | reflection | S[F] |
| Transparency | 1, 2 | tra | S[F1] |

<!-- Page 15 -->

The following table defines the keys and corresponding arguments required for the texture mapping
methods (see section 3).
Parameter Key Argument(s)
a
Transformations
Rotation rotate , nrotate , clearcoat_rotate 0 0 A[F]
Translation offset , noffset , clearcoat_offset U[F] V[F] 0
Scaling scale , nscale , clearcoat_scale U[F] V[F] 0
Plane mapping
YZ plane prjx
XZ plane prjy
XY plane prjz
normal vector prj X[F1] Y[F1] Z[F1]
Block mapping auto (xyx|xzx|xzz|yyz|xyz|yyx|yzx|yzz)
b
Texture coordinates import
a
The parameters that begin with the letter ’n’, affect only the normal map. If one of them is not specified, the
correspondingparameterwithoutletter’n’atthebeginningisusedforthenormalmap.
Likewise,theparametersthatbeginwith”clearcoat ”,affectonlytheclearcoatnormalmap. Ifoneofthemisnotspecified,
thecorrespondingparameterwithout”clearcoat ”atthebeginningisusedforthismap.
b
Texturecoordinatesstoredintheobjectgeometryareusedonlyiftheimportparameterispresent. Ifthekeyisspecified
buttherearenotexturecoordinatesinthegeometry,thebehaviorisundefined.

Legend:
(cid:136)
An argument is described either by an explicit list of the possible (alternative) values in the form
12
(value1|value2|...) or in the form name[type], where the name denotes the semantics of the
argument.
(cid:136)
A repeating set of arguments is represented in the form {arg1 ...}*.
(cid:136)
The following identifiers (abbreviations) are used for named arguments:
– S – scalar value
– FT, – file type, file name
FN
– R, G, – red, green, blue
B
– U, V, – UV coordinates or scaling, angle
A
– X, Y, – XYZ coordinates
Z
– N, F, – number, frequency, absorption coefficient
C
(cid:136)
The following identifiers are used for the types of arguments:
– F – floating-point number
– F1 – floating-point number in the range of 0.0 to 1.0
– I – integer
– FT – file type: (png|jpg)
– FN –filename: (possiblyfullyqualified)OFMLnamewhichreferstoanimagefileintheOFML
13
database

12
Ifthereisonlyasinglepossiblevaluetheenclosingparenthesisisomitted.
13 QualificationisnecessaryiftheimagefileisnotinthedatadirectoryoftheOFMLseries,wherethematerialdefinition
fileisstored,orifitisnotinthedatadirectoryoftheseriesoftheOFMLinstancetowhichaninlinedeclarationisapplied.

13

| Parameter | Key | Argument(s) |
| --- | --- | --- |
| Transformationsa
Rotation
Translation
Scaling | rotate, nrotate, clearcoat_rotate
offset, noffset, clearcoat_offset
scale, nscale, clearcoat_scale | 0 0 A[F]
U[F] V[F] 0
U[F] V[F] 0 |
| Plane mapping
YZ plane
XZ plane
XY plane
normal vector | prjx
prjy
prjz
prj | X[F1] Y[F1] Z[F1] |
| Block mapping | auto | (xyx|xzx|xzz|yyz|xyz|yyx|yzx|yzz) |
| Texture coordinatesb | import |  |

<!-- Page 16 -->

# A Introduction into Physically Based Rendering (PBR)

PBR simulates what happens when light hits the surface of an object. A physically correct described
material interacts with light in different ways: Light is reflected, refracted or absorbed. In natural condi-
tions, light is not completely absorbed, reflected or refracted – all materials are in the spectrum between
these extremes.
Amaterialbecomesvisibletousbecauseitreflectsincidentlight. Furthermoreweareabletoseematerials
that emit light by themselves.
Amongst others, the mentioned three basic possibilities of interaction between light and material are
affected by the characteristics of the material:
(cid:136)
The characteristics of the material determine the type of reflection:
In specular reflection, the light is reflected directly at the surface.
Diffusereflectionoccursduetoscatteringwithinthematerial(lightrayspenetrateintothematerial
a little and are deflected in different directions.)
Metal materials only have specular reflection, non-metals predominantly reflect diffuse.
(cid:136)
Depending on the characteristics of the material, the light rays enter deeper into the material.
They are either passed through the material (transparency), or thrown back within the material
(translucency) or swallowed by the material (absorption).

specular reflection diffuse reflection transparency translucency absorption

In addition to the characteristics of the material (see above) Physically Based Rendering also considers
the physical characteristics of the light:
(cid:136)
According to the principle of conservation of energy, no more light is reflected than irradiated.
A – non-luminous – material is displayed according to the lighting of the environment.
(cid:136)
Theamountofreflectedlightraysdependsontheangleofview. Thisso-calledFresnel effectcauses
14
surfaces to reflect more intensely at a flat viewing angle than when looking perpendicular to the
surface.

Thecharacteristicsofthelightaresimulatedviatheshaderoftheapplicationandcannotbemanipulated
directly by the user (material data creator).
The characteristics of materials, however, are the instruments for creating physically coherent materials.
The PBR-oriented material model OMATS2 defines corresponding parameters, where the amount of the
relevant material parameters depends on the specified material type (see section 2).

14 theso-calledgrazingangle

14

<!-- Page 17 -->

# B Conversion of older materials to the new model

Materials that were created based on the old model OMATS1 automatically are converted by the OFML
application to the new model.
Normally, this conversion provides a satisfying representation. In rare cases, however, adjustments may
be necessary:

(cid:136)
In some cases, materials shine more intensely.
In this case, the roughness has to be adjusted by specifying the (new) parameter Roughness.
(cid:136)
Metals may not be recognized as such (this may be true, e.g., for chrome surfaces).
In this case, new parameter Metallness has to be specified explicitly (with value ).
1.0

15

<!-- Page 18 -->

# C History

The first versions of this specification were prepared by Ekkehard Beier (EasternGraphics GmbH) on
behalf of the Working Group Industrielle Aspekte der OFML-Normung 15 (IAON) in cooperation with
wegscheiderofficesolutiongmbh(Germany)andweberofficesolutiongmbh(Schwitzerland). Startingwith
version1.4,thespecificationissubjecttostandardizationbytheOFMLstandardizationboardoftheIBA.

### Version 2.2

(2025-04-22)
(cid:136)
Added new parameters for model OMATS2 as well as their corresponding keys in OFML ma-
terial definitions: Clearcoat, Clearcoat Normal Map, Clearcoat Roughness, Emissive Color Map,
Opacity Map, Sheen, Sheen Color and Sheen Roughness.
(cid:136)
ThekeyforthematerialparameterRefractive IndexinOFMLmaterialdefinitionshasbeenrenamed
.
refraction
The previous key is declared deprecated.
ref
(cid:136)
Removed the ambiguous and unused file type any for image files in OFML material definitions.
(cid:136)
Clarification regarding the use of metadata in image files for textures.

### Version 2.1

(2023-06-27)
(cid:136)
For image files (data types *-IMAGE) the maximum allowed size was set to 4.096 x 4.096.

### Version 2.0

(2019-06-19)
(cid:136)
New material model OMATS2
(cid:136)
New data type GRAYSCALE-IMAGE
(cid:136)
Removed data type FP3-IMAGE, instead enhanced description of parameter Normal Map
(cid:136)
Renamed parameter Diffuse Color in Base Color and Diffuse Map in Base Color Map as well as
Refraction in Refractive Index
(cid:136)
RemovedmaterialtypesGlass TranslucentandMetal PolishedaswellasparameterAmbient Color
due to low practical relevance
(cid:136)
Image file format TGA now is obsolet
(cid:136)
Removed references to AutoCAD
(cid:136)
Restructuring of the document

### Version 1.5

(2015-02-27)
(cid:136)
New, explicit transformation parameters nrotate, noffset and nscale for normal maps.

### Version 1.4, 1st revised version

(2014-01-08)
(cid:136)
First english issue of this specification.

15 IndustrialaspectsofOFMLstandardization

16