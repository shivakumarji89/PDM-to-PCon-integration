from __future__ import annotations

from services.sif_validation_service import SifValidationService


class CancellableSifValidationService(SifValidationService):
    """Shared SIF pricing pipeline with an OBX-only cancellable repository."""

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

        repo = CancellablePDMRepository(self.context, operation_control)
        conn = repo.get_connection()
        try:
            server_date = self._server_date(repo, conn)
            mydate = self._normalise_pricing_date(validation_date or server_date)
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
