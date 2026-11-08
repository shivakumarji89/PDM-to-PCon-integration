"""PDM-driven bulk price update orchestration.

This service deliberately keeps Maintenance and Development state untouched:
it builds an isolated PDM snapshot for each linked repository, runs the existing
PricingService, previews the existing non-destructive MDB exporter, then writes
only a validated and read-back-verifiable plan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from core.cancellation import OperationCancelled, checkpoint
from models.snapshot import Snapshot
from services.price_mdb_export_service import PriceMdbExportService
from services.pricing_program import validate_pricing_program
from services.pricing_service import PriceParams, PricingService


@dataclass
class BulkPriceSeriesResult:
    path: str
    name: str
    status: str
    message: str = ""
    product_code: str = ""
    articles: int = 0
    computed_records: int = 0
    updated: int = 0
    inserted: int = 0
    verified: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class BulkPriceUpdateResult:
    results: list[BulkPriceSeriesResult] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return sum(r.status == "Updated" for r in self.results)

    @property
    def failed(self) -> int:
        return sum(r.status != "Updated" for r in self.results)


@dataclass(frozen=True)
class TemporarySeriesPricingContext:
    """Pricing inputs extracted from one target series MDB for one batch item.

    This object is deliberately short-lived: it is created immediately before
    pricing this series and discarded before the next series is processed.
    """
    repository_path: str
    mdb_path: str
    program_code: str
    price_lists: tuple[Any, ...]
    package_id: str
    package_label: str


class BulkPdmPriceUpdateService:
    """Compute and export PDM prices independently for each selected series."""

    def __init__(self, context) -> None:
        self.context = context

    def discover(self, repository_roots: str | Iterable[str]) -> list[dict[str, Any]]:
        roots = (
            [p.strip() for p in repository_roots.split(";") if p.strip()]
            if isinstance(repository_roots, str)
            else [str(p).strip() for p in repository_roots if str(p).strip()]
        )
        discovered: dict[str, dict[str, Any]] = {}
        link_service = self.context.maintenance_repository_link_service
        for root in roots:
            checkpoint()
            files = self.context.price_update_service._discover_packages(root, True)
            for mdb_path in files:
                checkpoint()
                folder = Path(mdb_path).parent
                key = str(folder.resolve()).casefold()
                if key in discovered:
                    continue
                try:
                    identity = link_service.inspect_repository(folder)
                    connection = link_service.get(identity["path"])
                    pdm = (connection or {}).get("pdm", {})
                    status = (connection or {}).get("connection", {}).get("status", "")
                    discovered[key] = {
                        "path": identity["path"],
                        "mdb_path": identity["ocd_path"],
                        "name": identity["name"],
                        "program": identity["code"],
                        "version": identity.get("version", ""),
                        "link_status": status or "Not linked",
                        "product_id": str(pdm.get("product_id") or ""),
                        "product_code": str(pdm.get("product_code") or ""),
                        "error": "",
                    }
                except Exception as exc:
                    discovered[key] = {
                        "path": str(folder.resolve()),
                        "mdb_path": str(mdb_path),
                        "name": folder.name,
                        "program": "",
                        "version": "",
                        "link_status": "Inspection failed",
                        "product_id": "",
                        "product_code": "",
                        "error": str(exc),
                    }
        return sorted(discovered.values(), key=lambda x: (x["name"].casefold(), x["path"].casefold()))

    def _extract_temporary_pricing_context(
        self, repository_path: str, mdb_path: Path, expected_program: str,
        effective_date: date,
    ) -> TemporarySeriesPricingContext:
        """Extract the pricing configuration from this series MDB only.

        Read only package identity and price-list metadata. Do not import the
        series' structural graph or its historical price rows into the PDM
        pricing snapshot: those rows are the destination baseline, not inputs
        to the PDM calculation.
        """
        from services.mdb_reverse_engineering_service import MdbReverseEngineeringService

        reader = MdbReverseEngineeringService(self.context)
        data = reader.read(mdb_path, tables=("tCOMd_PriceList2",))
        package = data.package or {}
        actual_program = str(package.get("reg_ProgramCode") or "").strip()
        if not actual_program:
            raise ValueError("Series MDB has no Package Program Code.")
        if actual_program.casefold() != str(expected_program).casefold():
            raise ValueError(
                f"Series identity changed: discovered Program Code '{expected_program}', "
                f"but MDB now contains '{actual_program}'. Scan the series again."
            )
        if not data.rows("tCOMd_PriceList2"):
            raise ValueError(
                "Series MDB contains no price-list configuration. "
                "Pricing cannot safely choose a target list."
            )

        # Use the existing importer for canonical date/currency/label mapping.
        # The temporary snapshot contains only package + price-list metadata.
        series_config = reader.import_snapshot(data)
        price_lists = tuple(
            item for item in series_config.price_lists
            if (item.currency or "").strip()
            and (item.label or item.id or "").strip()
            and str(item.label or item.id).strip().casefold() != "default"
        )
        if not price_lists:
            raise ValueError(
                "Series MDB has no usable non-default price lists with currency and label."
            )
        from services.price_list_targets import DATE_MAX, DATE_MIN, normalize_mdb_date

        currencies = {str(item.currency).strip().upper() for item in price_lists}
        required = {"EUR", "GBP"}
        missing = sorted(required - currencies)
        if missing:
            raise ValueError(
                "Series MDB is missing required Maintenance pricing currency list(s): "
                + ", ".join(missing)
            )

        # PricingService computes each supported currency. Before invoking it,
        # prove that this series has exactly one applicable list for every
        # currency on the requested date. Overlapping lists are ambiguous and
        # must never be resolved by table order.
        day = effective_date.strftime("%Y%m%d")
        for currency in sorted(currencies):
            applicable = []
            for price_list in price_lists:
                if str(price_list.currency).strip().upper() != currency:
                    continue
                start = normalize_mdb_date(price_list.date_from, DATE_MIN)
                end = normalize_mdb_date(price_list.date_to, DATE_MAX)
                if start <= day <= end:
                    applicable.append(price_list)
            if not applicable:
                raise ValueError(
                    f"Series MDB has no {currency} price list valid on {day}. "
                    "No PDM pricing request or MDB write was attempted."
                )
            if len(applicable) > 1:
                labels = ", ".join(
                    f"{item.label or item.id} (ID {item.id})" for item in applicable
                )
                raise ValueError(
                    f"Series MDB has overlapping {currency} price lists valid on {day}: "
                    f"{labels}. Resolve the list configuration before updating."
                )

        return TemporarySeriesPricingContext(
            repository_path=str(Path(repository_path).resolve()),
            mdb_path=str(mdb_path.resolve()),
            program_code=actual_program,
            price_lists=price_lists,
            package_id=str(package.get("com_PackageID") or ""),
            package_label=str(package.get("reg_ProgramLabel") or ""),
        )

    def update(
        self,
        selected: Iterable[dict[str, Any]],
        *,
        effective_date: str,
        site_id: int = 1,
        reporter=None,
    ) -> BulkPriceUpdateResult:
        """Update selected series sequentially; each failure is isolated.

        effective_date is yyyy-MM-dd. A successful result requires:
        exact repository link -> exact live PDM product -> isolated snapshot ->
        PDM pricing -> clean export preview -> export with the preview digest ->
        explicit MDB read-back verification.
        """
        try:
            day = date.fromisoformat(effective_date)
        except (TypeError, ValueError):
            raise ValueError("Effective date must be a valid YYYY-MM-DD date.")

        series = list(selected)
        output = BulkPriceUpdateResult()
        if not series:
            return output

        pdm = self.context.pdm_service
        products = pdm.get_products()
        products_by_id = {str(p.id): p for p in products if getattr(p, "id", None)}
        pricing = PricingService(self.context)
        exporter = PriceMdbExportService(self.context)
        link_service = self.context.maintenance_repository_link_service

        if reporter is not None:
            reporter.begin(len(series), title="Update Prices from PDM", subject="Selected series")

        for entry in series:
            checkpoint()
            path = str(entry.get("path") or "")
            name = str(entry.get("name") or Path(path).name or path)
            result = BulkPriceSeriesResult(path=path, name=name, status="Failed")
            output.results.append(result)
            try:
                if entry.get("error"):
                    raise ValueError(str(entry["error"]))
                mdb_path = Path(entry.get("mdb_path") or (Path(path) / link_service.OCD_FILE))
                if not mdb_path.is_file():
                    raise ValueError(f"Series MDB not found: {mdb_path}")

                # Always re-read the persisted link immediately before pricing.
                # A stale discovery row must never route prices to another product.
                link = link_service.get(path)
                if not link or link.get("connection", {}).get("status") != "established":
                    raise ValueError("Series has no established PDM link. Link it before updating prices.")
                linked_product_id = str(link.get("pdm", {}).get("product_id") or "")
                product = products_by_id.get(linked_product_id)
                if not linked_product_id or product is None:
                    raise ValueError(
                        f"Linked PDM product id '{linked_product_id or '(blank)'}' "
                        "could not be resolved in the live PDM product list."
                    )
                result.product_code = str(product.code or "")
                if entry.get("product_id") and str(entry["product_id"]) != linked_product_id:
                    raise ValueError("The PDM link changed after discovery. Scan the series again.")

                # Extract this series' pricing configuration into a temporary
                # context before fetching PDM prices. This is deliberately
                # per-series; no settings are carried over from the previous row.
                identity = link_service.inspect_repository(path)
                program = validate_pricing_program(identity.get("code", ""))
                temporary = self._extract_temporary_pricing_context(
                    path, mdb_path, program, day
                )

                # Isolated PDM snapshot: never publish it to SnapshotManager and
                # never replace active/PDM/MDB Maintenance snapshots.
                load_data = pdm._fetch_and_map(product)
                snapshot = Snapshot(product=product)
                snapshot.price_lists = list(temporary.price_lists)
                pdm._populate_snapshot(snapshot, load_data)
                pdm._populate_links(snapshot)
                self.context.engineering_reduction_service.materialize_article_sets(snapshot)
                if not snapshot.articles:
                    raise ValueError("The linked PDM product returned no articles.")
                snapshot.generation_program = program
                params = PriceParams(
                    currency="",
                    mydate=day.strftime("%d-%b-%Y"),
                    site_id=int(site_id),
                    valid_from=day.strftime("%Y-%m-%d"),
                    valid_to="",
                    program_code=temporary.program_code,
                    require_program=True,
                )
                computed = pricing.compute(params, snapshot)
                result.articles = len(snapshot.articles)
                result.computed_records = len(computed.records)
                if computed.warnings:
                    result.warnings.extend(computed.warnings)
                if computed.unresolved:
                    raise ValueError(
                        f"{len(computed.unresolved)} PDM item(s) have unresolved base prices; "
                        "no MDB write was attempted."
                    )
                if not computed.records:
                    raise ValueError("PDM returned no price records; no MDB write was attempted.")

                # The dry-run plan is the write authorization. Ambiguous/unmapped
                # identities, blocked text rows, unlinked lists, or any planner
                # blocking error fail closed.
                preview = exporter.export(snapshot, mdb_path, dry_run=True)
                if not preview.get("ok"):
                    raise ValueError(preview.get("error") or "MDB export preview failed.")
                if not preview.get("export_allowed", False):
                    raise ValueError(
                        "MDB export preview contains blocking errors: "
                        + "; ".join(preview.get("blocking_errors") or ["unspecified validation error"])
                    )
                unsafe = {
                    "unmapped": int(preview.get("skipped_unmapped") or 0),
                    "ambiguous": int(preview.get("skipped_ambiguous") or 0),
                    "blocked": int(preview.get("blocked_rows") or 0),
                    "no_base": int(preview.get("skipped_no_base_price") or 0),
                }
                unsafe = {k: v for k, v in unsafe.items() if v}
                if unsafe:
                    raise ValueError(
                        "MDB preview is incomplete; no write attempted (" +
                        ", ".join(f"{k}={v}" for k, v in unsafe.items()) + ")."
                    )
                unlinked = [
                    str(x.get("label") or x.get("id"))
                    for x in (preview.get("target_lists") or [])
                    if not x.get("linked")
                ]
                if unlinked:
                    raise ValueError(
                        "Target price list(s) are not linked to a distribution region: "
                        + ", ".join(unlinked) + ". Link the lists before updating."
                    )

                checkpoint()
                written = exporter.export(
                    snapshot, mdb_path, expected_plan=preview.get("plan_digest")
                )
                if not written.get("ok"):
                    raise ValueError(written.get("error") or "MDB export failed.")
                if written.get("verified") is not True:
                    raise ValueError(
                        "MDB write did not return a successful read-back verification."
                    )
                if int(written.get("failed") or 0):
                    raise ValueError(
                        f"{written['failed']} MDB write(s) were not confirmed."
                    )

                result.status = "Updated"
                result.verified = True
                result.updated = int(written.get("updated_prices") or 0) + int(
                    written.get("updated_global_prices") or 0
                )
                result.inserted = int(written.get("inserted_prices") or 0) + int(
                    written.get("inserted_global_prices") or 0
                )
                result.warnings.extend(written.get("warnings") or [])
                result.message = (
                    f"Read-back verified. {result.updated} price row(s) corrected; "
                    f"{result.inserted} inserted."
                )
            except OperationCancelled:
                raise
            except Exception as exc:
                result.message = str(exc)
            finally:
                if reporter is not None:
                    reporter.advance(f"{name}: {result.status}")
        return output
