from __future__ import annotations

from services.sif_validation_service import SifValidationService


class CancellableSifValidationService(SifValidationService):
    """Shared SIF pricing pipeline with an OBX-only cancellable repository."""

    def __init__(self, context, lookup_cache=None) -> None:
        super().__init__(context)
        self._lookup_cache = lookup_cache if lookup_cache is not None else {}

    def _fetch_plc(self, items, site, repo, conn) -> dict[str, str]:
        """Reuse completed OBX PLC lookups and query only missing items."""
        cache = self._lookup_cache.setdefault("plc", {})
        vals = [str(i) for i in items if i]
        missing = []
        for item in vals:
            key = (item, int(site) if site is not None else None)
            if key not in cache:
                missing.append(item)

        if missing:
            for chunk in repo._chunked(missing, repo._IN_CHUNK):
                ph = repo._placeholders(len(chunk))
                rows = repo._execute(
                    "SELECT i.Item, pc.Product_Code AS Code, cat.Name AS Category "
                    "FROM Item i "
                    "INNER JOIN Product p ON i.ProductId = p.ProductId "
                    "LEFT JOIN Product_Code pc ON "
                    "pc.ProductCodeId = CASE "
                    "WHEN i.ProductCodeIdOverride IS NOT NULL "
                    "THEN i.ProductCodeIdOverride "
                    "ELSE p.ProductCodeId "
                    "END "
                    "AND pc.SiteId = ? "
                    "LEFT JOIN ProductRange pr ON p.ProductRangeId = pr.ProductRangeId "
                    "LEFT JOIN ProductCategory cat ON pr.ProductCategoryId = cat.ProductCategoryId "
                    f"WHERE i.Item IN ({ph})",
                    (site,) + tuple(chunk),
                    conn,
                )
                for row in rows:
                    item = str(row.Item)
                    code = (row.Code or "").strip()
                    category = (row.Category or "").strip()
                    value = f"{category} ({code})" if code else category
                    cache[(item, int(site) if site is not None else None)] = value
            for item in missing:
                cache.setdefault((item, int(site) if site is not None else None), "")

        return {
            item: cache.get((item, int(site) if site is not None else None), "")
            for item in vals
        }

    def validate(
        self,
        currency: str,
        lines: list,
        site: int | None = None,
        obx: bool = False,
        validation_date: str | None = None,
        progress=None,
        stage=None,
        on_result=None,
        operation_control=None,
    ):
        if operation_control is None:
            return super().validate(
                currency,
                lines,
                site=site,
                obx=obx,
                validation_date=validation_date,
                progress=progress,
                stage=stage,
                on_result=on_result,
            )

        from repositories.cancellable_pdm_repository import CancellablePDMRepository

        repo = CancellablePDMRepository(self.context, operation_control, self._lookup_cache)
        conn = repo.get_connection()
        try:
            # Only query PDM for the server date when no validation date was supplied.
            # The OBX UI always supplies a date, so this avoids an unnecessary round trip
            # while preserving the existing fallback for programmatic callers.
            mydate = validation_date or self._server_date(repo, conn)
            groups: dict[str, list] = {}
            for line in lines:
                groups.setdefault(line.currency or currency, []).append(line)

            sites: dict[str, int | None] = {}
            results: list = []
            done = [0]
            total = len(lines)
            for cur, group in groups.items():
                operation_control.checkpoint()
                group_site = site if site is not None else self.site_for_currency(
                    cur, repo, conn, obx=obx
                )
                sites[cur] = group_site
                results.extend(
                    self._validate_group(
                        cur,
                        group,
                        group_site,
                        repo,
                        conn,
                        mydate,
                        done,
                        total,
                        progress,
                        stage,
                        on_result,
                        "OBX" if obx else "SIF",
                        obx,
                    )
                )
            results.sort(key=lambda result: result.seq)
            return sites, results
        finally:
            conn.close()
            operation_control.unregister_cancel_handler(repo.cancel_active_operation)
