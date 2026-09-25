# `tCOMd_*` Table Documentation

**Cross-refs:** [../README.md](../README.md) · [../ERDiagram.md](../ERDiagram.md) · [../WriteOrder.md](../WriteOrder.md)

One file per important OCD table. Each file documents: purpose, primary key, foreign keys, referenced
by, depends on, important columns, Builder Table source, generation stage, consumer services, business
rules, example record, typical row count, and generation order.

## Structural (Package Builder stage)

| # | Table | File |
|---|---|---|
| 1 | `tCOMd_DistributionRegion` | [tCOMd_DistributionRegion.md](./tCOMd_DistributionRegion.md) |
| 2 | `tCOMd_ComGroup` | [tCOMd_ComGroup.md](./tCOMd_ComGroup.md) |
| 3 | `tCOMd_OfmlType` | [tCOMd_OfmlType.md](./tCOMd_OfmlType.md) |
| 4 | `tCOMd_Package` | [tCOMd_Package.md](./tCOMd_Package.md) |
| 5 | `tCOMd_Text` | [tCOMd_Text.md](./tCOMd_Text.md) |
| 6 | `tCOMd_Class` | [tCOMd_Class.md](./tCOMd_Class.md) |
| 7 | `tCOMd_Property` | [tCOMd_Property.md](./tCOMd_Property.md) |
| 8 | `tCOMd_PropValue` | [tCOMd_PropValue.md](./tCOMd_PropValue.md) |
| 9 | `tCOMd_Article` | [tCOMd_Article.md](./tCOMd_Article.md) |
| 10 | `tCOMd_ArticleClass` | [tCOMd_ArticleClass.md](./tCOMd_ArticleClass.md) |
| 11 | `tCOMd_ArtBase` | [tCOMd_ArtBase.md](./tCOMd_ArtBase.md) |

## Item-level (Price Generator stage)

| # | Table | File |
|---|---|---|
| 12 | `tCOMd_PriceList2` | [tCOMd_PriceList2.md](./tCOMd_PriceList2.md) |
| 13 | `tCOMd_Price` | [tCOMd_Price.md](./tCOMd_Price.md) |

> Column names are grounded in `helpers/mdb_helper.py` and `services/mdb_service.py`. Fields not
> directly observed in source are marked `UNKNOWN` and should be confirmed against a live MDB schema.
