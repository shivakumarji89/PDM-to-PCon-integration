"""Account for every reported OBX failure without inferring product validity."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def source_matches(records, root):
    from services.obx_validation_service import ObxValidationService

    wanted = {(record["SKU"], round(float(record["OBX List Price (EUR)"]), 2))
              for record in records}
    matches = {}
    parse_errors = {}
    service = ObxValidationService(None)
    for path in sorted(root.rglob("*.obx")):
        try:
            _, lines = service.parse_obx(path.read_text(encoding="utf-8-sig"))
        except (ValueError, OSError, ET.ParseError) as error:
            parse_errors[str(path)] = str(error)
            continue
        for line in lines:
            key = (line.final_article, round(line.obx_price, 2))
            if key in wanted:
                matches.setdefault(key, []).append({
                    "path": str(path), "seq": line.seq,
                    "source_index": line.source_index, "currency": line.currency,
                    "source_date": line.source_date, "features": line.features,
                    "base_article": line.base_article,
                })
    return matches, parse_errors


def capture_reference(records, context, output, validation_date):
    from repositories.pdm_repository import PDMRepository
    from services.sif_validation_service import SifValidationService

    items = sorted({record["SKU"].split()[0] for record in records})
    repo = PDMRepository(context)
    conn = repo.get_connection()
    try:
        family_rows = repo._execute(
            "SELECT i.Item, p.Name AS ProductName, pr.Name AS Family "
            "FROM Item i INNER JOIN Product p ON p.ProductId=i.ProductId "
            "INNER JOIN ProductRange pr ON pr.ProductRangeId=p.ProductRangeId "
            f"WHERE i.Item IN ({repo._placeholders(len(items))})",
            tuple(items), conn,
        )
        families = {row.Item: row.Family for row in family_rows}
        wanted = {}
        for record in records:
            tokens = record["SKU"].split()
            wanted.setdefault(tokens[0], set()).update(tokens[1:])
        reference = {"database": context.config.pdm_database,
                     "server": context.config.pdm_server,
                     "validation_date": validation_date, "site": 1,
                     "families": families, "items": {}}
        fields = ("Item", "OptionId", "OptionValueId", "OrderCodeValue2", "Status",
                  "IsFabric", "ParentOptId", "ParentOptValId", "ParentOptValCode",
                  "IncPrice", "Quantity")
        for item in items:
            rows = repo.fetch_item_validation_options(
                [item], "EUR", validation_date, 1, conn
            )
            selected = [row for row in rows if any(
                SifValidationService._increment_key_match(
                    code, {str(row.OrderCodeValue2 or ""): row}
                ) is not None for code in wanted[item]
            )]
            parents = {row.ParentOptId for row in selected if row.ParentOptId}
            relevant = [row for row in rows if row in selected or row.OptionId in parents]
            reference["items"][item] = [
                {field: (float(getattr(row, field))
                         if field == "IncPrice" and getattr(row, field) is not None
                         else getattr(row, field)) for field in fields}
                for row in relevant
            ]
            print(f"Captured {item}: {len(rows)} PDM rows, {len(relevant)} relevant", flush=True)
        (output / "pdm_reference.json").write_text(
            json.dumps(reference, indent=2) + "\n", encoding="utf-8"
        )
        return reference
    finally:
        conn.close()


def revalidate(records, matches, context, validation_date):
    from services.obx_validation_service import ObxLine, ObxValidationService

    lines = []
    unknown = {}
    for index, record in enumerate(records, start=1):
        key = (record["SKU"], round(float(record["OBX List Price (EUR)"]), 2))
        candidates = matches.get(key, [])
        currencies = {candidate["currency"] for candidate in candidates}
        if len(currencies) != 1 or not next(iter(currencies), ""):
            unknown[record["Report CSV Row"]] = "Missing or ambiguous source currency"
            continue
        source = candidates[0]
        lines.append(ObxLine(
            seq=index, base_article=source["base_article"],
            final_article=record["SKU"], currency=source["currency"],
            obx_price=float(record["OBX List Price (EUR)"]),
            qty=int(record["OBX Qty"]), features=source["features"],
            source_date=source["source_date"], source_index=source["source_index"],
        ))
    service = ObxValidationService(context)
    sites, results = service.validate(
        "", lines, validation_date=validation_date,
        progress=lambda done, total, item: print(
            f"Revalidating {done}/{total}: {item}", flush=True
        ) if done % 50 == 0 else None,
    )
    return {records[result.seq - 1]["Report CSV Row"]: result for result in results}, unknown, sites


def currency_trials(records, context, validation_date, currencies):
    from repositories.pdm_repository import PDMRepository
    from services.obx_validation_service import ObxLine, ObxValidationService
    from services.sif_validation_service import SifValidationService

    lines = []
    row_by_seq = {}
    for record in records:
        for currency in currencies:
            seq = len(lines) + 1
            row_by_seq[seq] = record["Report CSV Row"]
            lines.append(ObxLine(
                seq=seq, base_article=record["SKU"].split()[0],
                final_article=record["SKU"], currency=currency,
                obx_price=float(record["OBX List Price (EUR)"]),
                qty=int(record["OBX Qty"]),
            ))
    verifier = SifValidationService._verify_selected_options
    fetch_options = PDMRepository.fetch_item_validation_options
    open_connection = PDMRepository.get_connection
    option_cache = {}

    def bounded_connection(repo):
        connection = open_connection(repo)
        connection.timeout = 60
        return connection

    def cached_options(repo, items, currency, mydate, site_id, connection=None):
        rows = []
        for item in items:
            key = (str(item), currency, mydate, site_id)
            if key not in option_cache:
                print(f"Currency trial metadata: {currency} {item}", flush=True)
                option_cache[key] = fetch_options(repo, [item], currency, mydate, site_id, connection)
            rows.extend(option_cache[key])
        return rows

    def original_verifier(cls, rows, codes):
        return verifier([row for row in rows if int(row.IsFabric or 0) != 2], codes)

    def execute():
        service = ObxValidationService(context)
        service._validation_cache().clear()
        service._pricing_service()._PRICE_WINDOW = len(lines)
        return service.validate(
            "", lines, validation_date=validation_date,
            progress=lambda done, total, item: print(
                f"Currency trial {done}/{total}: {item}", flush=True
            ) if done % 100 == 0 else None,
        )[1]

    with patch.object(PDMRepository, "get_connection", bounded_connection), patch.object(
        PDMRepository, "fetch_item_validation_options", cached_options
    ):
        print("Running reconstructed currency trials: original option behavior", flush=True)
        with patch.object(SifValidationService, "_verify_selected_options", classmethod(original_verifier)):
            baseline = execute()
        print("Running reconstructed currency trials: corrected option behavior", flush=True)
        corrected = execute()
    original = {(result.seq, result.currency): result for result in baseline}
    output = {}
    for result in corrected:
        before = original.get((result.seq, result.currency))
        output.setdefault(row_by_seq[result.seq], {})[result.currency] = {
            "original_behavior": before.result if before else "NO RESULT",
            "corrected_behavior": result.result,
            "pdm_price": result.pdm_price,
            "obx_price": result.sif_price,
            "baseline_pdm_price": before.pdm_price if before else None,
        }
    return output


def load_report(path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"SKU", "Result", "OBX Qty"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Report is missing SKU, Result or OBX Qty")
        records, summaries = [], []
        for record in reader:
            record = {key: value or "" for key, value in record.items()}
            record["Report CSV Row"] = str(reader.line_num)
            if not record["SKU"].strip() or (
                not record["Result"].strip() and not record["OBX Qty"].strip()
            ):
                summaries.append(record)
            else:
                records.append(record)
    return records, summaries


def inventory(records: list[dict[str, str]], source: Path) -> list[dict[str, str]]:
    output = []
    for record in records:
        if record["Result"].strip() == "VALID":
            continue
        tokens = record["SKU"].split()
        match = re.fullmatch(
            r"invalid option string in order code at position (\d+): (.+)",
            record["Result"],
        )
        output.append({
            **record,
            "Report Source": str(source),
            "Original OBX Source": "Not supplied in report",
            "Original OBX Row": "Not supplied in report",
            "Product Family": "Requires authoritative lookup",
            "Base Code": tokens[0] if tokens else "",
            "Option String": " ".join(tokens[1:]),
            "Order Code Pattern": " ".join(tokens[:2]) + " <option>" if tokens else "",
            "Error Position": match.group(1) if match else "",
            "Rejected Option": match.group(2) if match else "",
            "Root Cause": "Requires reference-data verification",
            "Code Location": (
                "services/sif_validation_service.py:_verify_selected_options"
                if match else "Requires tracing"
            ),
            "Lookup Location": "repositories/pdm_repository.py:fetch_item_validation_options",
            "Fix Applied": "None established",
            "Revalidated Result": "NOT REVALIDATED",
            "Remaining Error": record["Result"],
            "Evidence": "Report alone does not establish active PDM option membership or price",
        })
    return output


def write_csv(path: Path, records: list[dict[str, str]]) -> None:
    if not records:
        raise ValueError("Refusing to write an empty investigation")
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-failures", type=int, default=724)
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--validation-date", default=date.today().isoformat())
    parser.add_argument("--fixed", action="store_true")
    parser.add_argument("--currency-trials", nargs="*", default=[])
    parser.add_argument("--reuse-reference", action="store_true")
    parser.add_argument("--reference-trial-date")
    parser.add_argument("--reuse-trials", action="store_true")
    args = parser.parse_args()
    records, summaries = load_report(args.report)
    failed = inventory(records, args.report)
    if len(failed) != args.expected_failures:
        raise ValueError(f"Expected {args.expected_failures} failures, found {len(failed)}")
    args.output.mkdir(parents=True, exist_ok=True)
    matches, parse_errors = source_matches(records, args.sources) if args.sources else ({}, {})
    reference = None
    results, unknown, sites = {}, {}, {}
    trials = {}
    reference_trials = {}
    source_reference_results = {}
    if args.live:
        from core.application_context import ApplicationContext

        context = ApplicationContext()
        reference = (
            json.loads((args.output / "pdm_reference.json").read_text(encoding="utf-8"))
            if args.reuse_reference else
            capture_reference(records, context, args.output, args.validation_date)
        )
        results, unknown, sites = revalidate(records, matches, context, args.validation_date)
        if args.reference_trial_date:
            source_reference_results = revalidate(
                records, matches, context, args.reference_trial_date
            )[0]
        if args.currency_trials:
            if args.reuse_trials:
                saved_trials = json.loads((args.output / "currency_trials.json").read_text(encoding="utf-8"))
                trials = saved_trials[args.validation_date]
                if args.reference_trial_date:
                    reference_trials = saved_trials[args.reference_trial_date]
                print("Replaying previously captured dated currency trials", flush=True)
            else:
                trials = currency_trials(records, context, args.validation_date, args.currency_trials)
                if args.reference_trial_date:
                    reference_trials = currency_trials(
                        records, context, args.reference_trial_date, args.currency_trials
                    )
            (args.output / "currency_trials.json").write_text(
                json.dumps({args.validation_date: trials, **(
                    {args.reference_trial_date: reference_trials} if reference_trials else {}
                )}, indent=2) + "\n", encoding="utf-8"
            )
    for record in failed:
        record["Option Revalidation"] = "NOT CHECKED"
        record["Original Option Behavior"] = "NOT CHECKED"
        record["Currency Trials (Not Source Revalidation)"] = json.dumps(trials.get(record["Report CSV Row"], {}))
        record["Reference-Date Trials (Not Source Revalidation)"] = json.dumps(
            {args.reference_trial_date: reference_trials.get(record["Report CSV Row"], {})}
            if reference_trials else {}
        )
        record["Full Live Trial Outcome"] = "NOT CHECKED"
        record["Final Investigation Outcome"] = "Requires reference-data verification"
        source_reference = source_reference_results.get(record["Report CSV Row"])
        record["Matched Source Reference-Date Result"] = (
            source_reference.result if source_reference else "SOURCE UNAVAILABLE"
        )
        key = (record["SKU"], round(float(record["OBX List Price (EUR)"]), 2))
        candidates = matches.get(key, [])
        if candidates:
            record["Original OBX Source"] = json.dumps(candidates)
            record["Original OBX Row"] = "; ".join(str(source["seq"]) for source in candidates)
        if reference:
            record["Product Family"] = reference["families"].get(record["Base Code"], "Unknown")
            from services.sif_validation_service import SifValidationService

            rows = [SimpleNamespace(**row) for row in reference["items"][record["Base Code"]]]
            codes = record["SKU"].split()[1:]
            original_error = SifValidationService._verify_selected_options(
                [row for row in rows if row.IsFabric != 2], codes
            )
            corrected_error = SifValidationService._verify_selected_options(rows, codes)
            record["Original Option Behavior"] = original_error or "PASS"
            record["Option Revalidation"] = corrected_error or "PASS"
            if original_error == record["Result"] and corrected_error is None:
                record["Root Cause"] = "Dependent fabric colour excluded from validation"
                record["Fix Applied"] = "Exact item-scoped colour with active fabric parent and selected ancestor"
                record["Evidence"] = (
                    "Captured PDMLive active colour, fabric parent value and selected ancestor match; "
                    "original option error reproduced; corrected options pass; original-source pricing pending"
                )
                record["Remaining Error"] = "Original-source date/currency/row unavailable; see explicit price trials"
                record["Final Investigation Outcome"] = "Confirmed option defect corrected; original-source confirmation pending"
            if reference_trials:
                passing = [currency for currency, value in reference_trials.get(record["Report CSV Row"], {}).items()
                           if value["corrected_behavior"] == "VALID"]
                record["Evidence"] += (
                    f"; explicit {args.reference_trial_date} live price trial matched report in {passing}; "
                    "report date/currency still require original-source confirmation"
                )
                record["Full Live Trial Outcome"] = (
                    f"VALID at {args.reference_trial_date} in {passing} (reconstructed CSV input)"
                    if passing else f"No passing {args.reference_trial_date} currency trial"
                )
                if passing:
                    record["Final Investigation Outcome"] = (
                        "Confirmed defect corrected; full live option and price trial PASS; "
                        "original-source confirmation pending"
                    )
        result = results.get(record["Report CSV Row"])
        if result:
            record["Revalidated Result"] = result.result
            record["Remaining Error"] = "" if result.status == "ok" else result.message
            if args.fixed and result.status == "ok":
                record["Root Cause"] = "Dependent fabric colour excluded from validation"
                record["Fix Applied"] = "Item-scoped dependent-colour matching"
            record["Evidence"] += "; " + (
                f"PDMLive validation at {args.validation_date}; site {sites.get(result.currency)}; "
                f"currency {result.currency}; PDM {result.pdm_price}; OBX {result.sif_price}; "
                "source matched by exact SKU and price; original report date/source not recorded"
            )
        elif args.live:
            record["Evidence"] += "; " + unknown.get(record["Report CSV Row"], "No validation result returned")
    write_csv(args.output / "reconciliation.csv", failed)
    valid = []
    for record in records:
        if record["Result"].strip() != "VALID":
            continue
        result = results.get(record["Report CSV Row"])
        trial = trials.get(record["Report CSV Row"], {})
        reference_trial = reference_trials.get(record["Report CSV Row"], {})
        valid.append({**record, "Revalidated Result": result.result if result else "NOT REVALIDATED",
                      "Currency Trials (Not Source Revalidation)": json.dumps(trial),
                  "Reference-Date Trials (Not Source Revalidation)": json.dumps(reference_trial),
                      "Behavior Regression": str(any(
                          value["original_behavior"] != value["corrected_behavior"]
                          or value["baseline_pdm_price"] != value["pdm_price"]
                          for value in [*trial.values(), *reference_trial.values()]
                      )) if trial else "NOT CHECKED"})
    write_csv(args.output / "original_valid.csv", valid)
    summary = {
        "report_sha256": hashlib.sha256(args.report.read_bytes()).hexdigest(),
        "sku_records": len(records),
        "original_failures": len(failed),
        "original_valid": len(records) - len(failed),
        "excluded_summary_rows": summaries,
        "distinct_failed_skus": len({record["SKU"] for record in failed}),
        "exact_errors": dict(Counter(record["Result"] for record in failed)),
        "base_codes": dict(Counter(record["Base Code"] for record in failed)),
        "option_strings": dict(Counter(record["Option String"] for record in failed)),
        "root_causes": dict(Counter(record["Root Cause"] for record in failed)),
        "original_source_confirmed_corrected": sum(record["Revalidated Result"] == "VALID" for record in failed),
        "matched_failed_sources_passing_reference_date": sum(
            record["Matched Source Reference-Date Result"] == "VALID" for record in failed
        ),
        "corrected_option_checks": sum(record["Option Revalidation"] == "PASS" for record in failed),
        "awaiting_original_source_revalidation": sum(record["Revalidated Result"] == "NOT REVALIDATED" for record in failed),
        "awaiting_authoritative_option_reference": sum(record["Option Revalidation"] == "NOT CHECKED" for record in failed),
        "confirmed_product_errors": 0,
        "unresolved_software_defects": 0,
        "valid_records_revalidated": sum(record["Report CSV Row"] in results for record in valid),
        "valid_record_current_source_price_failures": sum(
            record["Revalidated Result"] not in {"VALID", "NOT REVALIDATED"} for record in valid
        ),
        "valid_record_regressions": sum(record["Behavior Regression"] == "True" for record in valid)
            if trials else "NOT CHECKED: requires before/after revalidation",
        "valid_records_before_after_checked": sum(record["Behavior Regression"] != "NOT CHECKED" for record in valid),
        "failed_records_with_a_passing_currency_trial": sum(
            any(value["corrected_behavior"] == "VALID" for value in trials.get(record["Report CSV Row"], {}).values())
            for record in failed
        ),
        "reference_trial_date": args.reference_trial_date,
        "failed_records_with_a_passing_reference_date_trial": sum(
            any(value["corrected_behavior"] == "VALID" for value in reference_trials.get(record["Report CSV Row"], {}).values())
            for record in failed
        ),
        "corrected_by_code_in_supported_live_context": sum(
            any(value["corrected_behavior"] == "VALID" and value["original_behavior"] == record["Result"]
                for value in reference_trials.get(record["Report CSV Row"], {}).values())
            for record in failed
        ),
        "source_parse_errors": parse_errors,
        "source_records_matched": sum(bool(matches.get((
            record["SKU"], round(float(record["OBX List Price (EUR)"]), 2)
        ))) for record in records),
        "validation_date": args.validation_date if args.live else None,
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in summary.items() if key not in {
        "option_strings", "base_codes", "excluded_summary_rows"
    }}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())