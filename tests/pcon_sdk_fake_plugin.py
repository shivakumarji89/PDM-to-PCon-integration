"""In-process stand-in for the MK OBX Generator pCon.planner plugin.

It speaks the same job-file protocol as ``tools/pcon_obx_plugin`` so the
Python services can be exercised without pCon.planner. The product model is a
small, dependent one:

* ``Material`` offers Wood or Metal.
* ``Finish`` depends on Material: Wood -> Oak/Walnut, Metal -> Silver.
* ``Size`` is independent: S/L.

That mimics what pCon's OFML runtime does through ``IProperty.ValueSet``:
after ``SetValue(Material=Metal)`` the Finish ValueSet shrinks to Silver. The
enumeration mirrors ``ConfigurationEnumerator.cs`` (depth-first, re-reading
the live value set at every step). None of this is real SDK validation; the
live test in ``tests/test_pcon_sdk_obx_live.py`` covers that.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable
import xml.etree.ElementTree as ET

from services.pcon_sdk_obx import protocol

PACKAGES = [
    {
        "packageName": "::mk::demo::1", "manufacturerId": "MK", "manufacturer": "mk",
        "manufacturerName": "MillerKnoll Demo", "programIds": "DM", "program": "demo",
        "programName": "Demo Seating", "type": "ProductWithCatalog", "version": "1.0",
        "distributionRegion": "UK", "hasCatalog": True,
    },
    {
        "packageName": "::mk::found::1", "manufacturerId": "MK", "manufacturer": "mk",
        "manufacturerName": "MillerKnoll Demo", "programIds": "", "program": "found",
        "programName": "Foundation", "type": "Found", "version": "1.0",
        "distributionRegion": "UK", "hasCatalog": False,
    },
    {
        "packageName": "::eg::office::2", "manufacturerId": "EG", "manufacturer": "egr",
        "manufacturerName": "EasternGraphics", "programIds": "AX;BX", "program": "office2",
        "programName": "Office", "type": "ProductWithCatalog", "version": "2.0",
        "distributionRegion": "DE", "hasCatalog": True,
    },
]

ARTICLES = {
    "::mk::demo::1": [
        {"articleNumber": "CHAIR1", "variantCode": "", "variantKey": "", "packageName": "::mk::demo::1",
         "label": "Task chair", "description": "Demo chair", "inCatalogTree": True},
        {"articleNumber": "CHAIR1", "variantCode": "", "variantKey": "", "packageName": "::mk::demo::1",
         "label": "Task chair (dup folder)", "description": "", "inCatalogTree": True},
        {"articleNumber": "STOOL1", "variantCode": "", "variantKey": "", "packageName": "::mk::demo::1",
         "label": "Stool", "description": "Demo stool", "inCatalogTree": False},
        {"articleNumber": "BROKEN", "variantCode": "", "variantKey": "", "packageName": "::mk::demo::1",
         "label": "Cannot insert", "description": "", "inCatalogTree": True},
        {"articleNumber": "DUPE", "variantCode": "", "variantKey": "", "packageName": "::mk::demo::1",
         "label": "Label does not change the SKU", "description": "", "inCatalogTree": True},
    ],
    "::eg::office::2": [],
}

PRICES = {"Wood": 100.0, "Metal": 120.0, "Oak": 0.0, "Walnut": 15.0, "Silver": 5.0, "S": 0.0, "L": 30.0,
          "Fixed": 0.0, "Adjustable": 40.0}


class FakeArticle:
    """Mutable property state with pCon-like dependent value sets."""

    def __init__(self, number: str) -> None:
        self.number = number
        self.values = {"Material": "Wood", "Finish": "Oak", "Size": "S"}
        if number == "STOOL1":
            # Stool has no Finish property at all.
            self.values.pop("Finish")
        if number == "DUPE":
            # "Label" is configurable but does not feed the final article number,
            # so two configurations encode to the same SKU.
            self.values = {"Material": "Wood", "Label": "X"}

    def choices(self, key: str) -> list[tuple[str, str]]:
        if key == "Material":
            return [("Wood", "Wood"), ("Metal", "Metal")]
        if key == "Finish":
            if self.values.get("Material") == "Metal":
                return [("Silver", "Silver")]
            return [("Oak", "Oak"), ("Walnut", "Walnut")]
        if key == "Size":
            return [("S", "Small"), ("L", "Large")]
        if key == "Arm":
            return [("Fixed", "Fixed arms"), ("Adjustable", "Adjustable arms")]
        if key == "Label":
            return [("X", "X"), ("Y", "Y")]
        return []

    def set_value(self, key: str, value: str) -> tuple[bool, str]:
        if key not in self.values:
            return False, f"Property {key} is not available for this configuration."
        if value not in {k for k, _ in self.choices(key)}:
            return False, f"Value {value} is not offered for {key} in this configuration."
        self.values[key] = value
        # Dependent property: Material drives the Finish value set.
        if key == "Material" and "Finish" in self.values:
            allowed = {k for k, _ in self.choices("Finish")}
            if self.values["Finish"] not in allowed:
                self.values["Finish"] = sorted(allowed)[0]
        # Nested dependency: the Arm property only exists for Metal chairs.
        if key == "Material" and self.number == "CHAIR1":
            if value == "Metal":
                self.values.setdefault("Arm", "Fixed")
            else:
                self.values.pop("Arm", None)
        return True, ""

    def properties(self) -> list[dict[str, Any]]:
        rows = []
        for key, value in self.values.items():
            choices = self.choices(key)
            rows.append({
                "key": key, "name": key, "description": f"{key} of {self.number}", "type": "Choice",
                "state": "Enabled, Editable", "valueKey": value,
                "valueText": dict(choices).get(value, value), "editable": True, "hidden": False,
                "choices": [{"key": k, "text": t} for k, t in choices],
            })
        rows.append({"key": "Height", "name": "Height", "description": "", "type": "Length",
                     "state": "ReadOnly", "valueKey": "0.45", "valueText": "0.45 m",
                     "editable": False, "hidden": False, "choices": []})
        return rows

    def final_number(self) -> str:
        codes = "".join(v[0] for k, v in self.values.items() if k != "Label")
        return f"{self.number} {codes}"

    def price(self) -> float:
        return sum(PRICES.get(v, 0.0) for v in self.values.values())

    def info(self) -> dict[str, Any]:
        return {
            "baseNumber": self.number, "finalNumber": self.final_number(),
            "variantCode": ";".join(f"{k}={v}" for k, v in self.values.items()),
            "ofmlVariantCode": ";".join(f"demo.{k}={v}" for k, v in self.values.items()),
            "shortText": f"{self.number} configured", "manufacturerId": "MK", "seriesId": "DM",
            "purchasePrice": self.price(), "salesPrice": self.price() * 1.5, "currency": "GBP",
            "features": [{"key": k, "name": k, "valueKey": v, "valueText": v, "visible": True}
                         for k, v in self.values.items()],
        }


class FakePconPlugin:
    """Background thread that polls ``job_dir`` exactly like the C# plugin."""

    def __init__(self, job_dir: Path, *, poll: float = 0.02, ready: bool = True,
                 heartbeat_every: float = 0.2, protocol_version: int = protocol.PROTOCOL_VERSION,
                 fail_export: bool = False, truncate_obx: bool = False,
                 generate_hook: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.job_dir = Path(job_dir)
        self.poll = poll
        self.ready = ready
        self.heartbeat_every = heartbeat_every
        self.protocol_version = protocol_version
        self.fail_export = fail_export
        self.truncate_obx = truncate_obx
        self.generate_hook = generate_hook
        self.document_modified = False
        self.requests: list[dict[str, Any]] = []
        self.plannings_started = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="fake-pcon-plugin", daemon=True)

    # -- lifecycle ------------------------------------------------------
    def start(self) -> "FakePconPlugin":
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.write_heartbeat()
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def __enter__(self) -> "FakePconPlugin":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    def write_heartbeat(self, *, timestamp: float | None = None) -> None:
        body = {
            "pluginVersion": "fake-0.1", "protocolVersion": self.protocol_version,
            "plannerReady": self.ready, "timestamp": time.time() if timestamp is None else timestamp,
            "jobDir": str(self.job_dir), "plannerVersion": "fake",
        }
        self._write_atomic(self.job_dir / protocol.HEARTBEAT_FILE, body)

    def _write_atomic(self, path: Path, body: dict[str, Any]) -> None:
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(body), encoding="utf-8")
        for attempt in range(50):
            try:
                os.replace(temp, path)
                return
            except PermissionError:
                # Windows refuses to replace a file the Workbench is reading.
                if attempt == 49:
                    raise
                time.sleep(0.01)

    def _loop(self) -> None:
        last_beat = 0.0
        while not self._stop.is_set():
            now = time.monotonic()
            if now - last_beat >= self.heartbeat_every:
                self.write_heartbeat()
                last_beat = now
            if self.ready:
                for path in sorted(self.job_dir.glob(f"*{protocol.REQUEST_SUFFIX}")):
                    self._handle(path)
            time.sleep(self.poll)

    # -- dispatch -----------------------------------------------------------
    def _handle(self, path: Path) -> None:
        job_id = path.name[: -len(protocol.REQUEST_SUFFIX)]
        result_path = self.job_dir / f"{job_id}{protocol.RESULT_SUFFIX}"
        progress_path = self.job_dir / f"{job_id}{protocol.PROGRESS_SUFFIX}"
        try:
            text = None
            for _attempt in range(20):
                try:
                    text = path.read_text(encoding="utf-8")
                    break
                except PermissionError:
                    # The Workbench renames .pending -> .request.json; Windows can
                    # report a sharing violation for a moment. Same retry as C#.
                    time.sleep(0.01)
            if text is None:
                return
            request = json.loads(text)
            self.requests.append(request)
            if int(request.get("protocolVersion", 0)) != protocol.PROTOCOL_VERSION:
                raise ValueError(f"Unsupported protocol version {request.get('protocolVersion')}")
            body = self._dispatch(request, progress_path)
            body.update({"protocolVersion": self.protocol_version, "id": job_id,
                         "kind": request.get("kind"), "ok": True, "error": ""})
        except Exception as exc:  # noqa: BLE001 - mirrors the plugin's catch-all
            body = {"protocolVersion": self.protocol_version, "id": job_id,
                    "kind": "", "ok": False, "error": str(exc)}
        try:
            path.unlink()
        except OSError:
            pass
        self._write_atomic(result_path, body)

    def _dispatch(self, request: dict[str, Any], progress_path: Path) -> dict[str, Any]:
        kind = request.get("kind")
        if kind == protocol.KIND_PING:
            return {"pluginVersion": "fake-0.1", "plannerVersion": "fake", "languages": ["en", "de"],
                    "documentModified": self.document_modified}
        if kind == protocol.KIND_CATALOG:
            return {"packages": PACKAGES}
        if kind == protocol.KIND_ARTICLES:
            name = request.get("packageName")
            if name not in ARTICLES:
                raise ValueError(f"Package not registered in pCon.planner: {name}")
            return {"articles": ARTICLES[name]}
        if kind == protocol.KIND_PROPERTIES:
            article = self._insert(request.get("articleNumber", ""))
            applied = []
            for assignment in request.get("assignments", []) or []:
                ok, error = article.set_value(assignment.get("key", ""), assignment.get("valueKey", ""))
                applied.append({"key": assignment.get("key"), "valueKey": assignment.get("valueKey"),
                                "ok": ok, "error": error})
            return {"article": article.info(), "properties": article.properties(), "applied": applied}
        if kind == protocol.KIND_GENERATE:
            return self._generate(request, progress_path)
        raise ValueError(f"Unknown request kind: {kind}")

    @staticmethod
    def _insert(number: str) -> FakeArticle:
        if number == "BROKEN":
            raise ValueError(f"pCon.planner could not insert article {number}")
        return FakeArticle(number)

    # -- generation (mirrors ConfigurationEnumerator.cs) --------------------
    def _generate(self, request: dict[str, Any], progress_path: Path) -> dict[str, Any]:
        if self.generate_hook is not None:
            self.generate_hook(request)
        if self.document_modified and not request.get("discardUnsavedPlanning", False):
            raise ValueError("The current pCon.planner planning has unsaved changes. "
                             "Save it or allow the Workbench to discard it.")
        self.plannings_started += 1
        self.document_modified = False
        max_count = int(request.get("maxConfigurations", 500))
        rules = request.get("properties", []) or []
        vary_all = bool(request.get("varyAll", True))
        deduplicate = bool(request.get("deduplicate", True))
        fixed = [(r["key"], r.get("valueKey", "")) for r in rules if r.get("mode") == protocol.MODE_FIXED]
        vary = [r["key"] for r in rules if r.get("mode") == protocol.MODE_VARY]
        excluded = {r["key"] for r in rules if r.get("mode") != protocol.MODE_VARY}
        cancel_path = progress_path.with_name(progress_path.name.replace(protocol.PROGRESS_SUFFIX, protocol.CANCEL_SUFFIX))

        configurations: list[dict[str, Any]] = []
        warnings: list[str] = []
        state = {"skipped": 0, "truncated": False, "duplicates": 0, "visited": 0, "cancelled": False}
        seen_finals: set[str] = set()

        def next_property(probe: FakeArticle, assigned: set[str]) -> str | None:
            if vary_all:
                for key in probe.values:
                    if key not in assigned and key not in excluded and probe.choices(key):
                        return key
                return None
            for key in vary:
                if key not in assigned and key in probe.values and probe.choices(key):
                    return key
            return None

        def enumerate_(number: str, prefix: list[tuple[str, str]], vary_index: int) -> None:
            if state["cancelled"] or cancel_path.exists():
                state["cancelled"] = True
                return
            if len(configurations) >= max_count:
                state["truncated"] = True
                return
            state["visited"] += 1
            try:
                probe = self._insert(number)
            except ValueError as exc:
                state["skipped"] += 1
                warnings.append(f"{number}: {exc}")
                return
            for key, value in prefix:
                ok, error = probe.set_value(key, value)
                if not ok:
                    state["skipped"] += 1
                    warnings.append(f"{number} {prefix}: {error}")
                    return
            key = next_property(probe, {k for k, _ in prefix})
            if key is None:
                # Leaf: fixed values are re-applied and every assignment must
                # still hold after pCon's relation cascade, otherwise the
                # configuration is not the one requested and is skipped.
                for key, value in fixed:
                    ok, error = probe.set_value(key, value)
                    if not ok:
                        state["skipped"] += 1
                        warnings.append(f"{number} {prefix}: {error}")
                        return
                for key, value in prefix:
                    if probe.values.get(key) != value:
                        state["skipped"] += 1
                        warnings.append(f"{number} {prefix}: {key}={value} changed by relations to "
                                        f"{probe.values.get(key)}")
                        return
                info = probe.info()
                if deduplicate and info["finalNumber"] in seen_finals:
                    state["duplicates"] += 1
                    return
                seen_finals.add(info["finalNumber"])
                configurations.append({
                    "index": len(configurations) + 1, "baseArticle": number,
                    "finalArticle": info["finalNumber"], "variantCode": info["variantCode"],
                    "ofmlVariantCode": info["ofmlVariantCode"],
                    "assignments": [{"key": k, "name": k, "valueKey": v, "valueText": v} for k, v in prefix],
                    "features": info["features"],
                    "currency": info["currency"], "purchasePrice": info["purchasePrice"],
                    "salesPrice": info["salesPrice"], "status": "ok", "message": "",
                })
                self._write_atomic(progress_path, {"processed": len(configurations), "total": max_count,
                                                   "message": f"{number} -> {info['finalNumber']}"})
                return
            for value, _ in probe.choices(key):
                if state["cancelled"] or cancel_path.exists():
                    state["cancelled"] = True
                    return
                if len(configurations) >= max_count:
                    state["truncated"] = True
                    return
                enumerate_(number, prefix + [(key, value)], 0)

        for article in request.get("articles", []) or []:
            if state["truncated"] or state["cancelled"]:
                break
            seen_finals.clear()
            enumerate_(article.get("articleNumber", ""), list(fixed), 0)

        output = request.get("outputPath", "")
        exported = False
        if state["cancelled"]:
            warnings.append("Generation cancelled by the Workbench.")
        elif configurations and not self.fail_export:
            self._write_obx(Path(output), configurations)
            exported = True
        elif not configurations:
            warnings.append("No configuration could be generated; nothing exported.")
        for path in (progress_path, cancel_path):
            try:
                path.unlink()
            except OSError:
                pass
        return {
            "outputPath": output, "exported": exported, "configurations": configurations,
            "skipped": state["skipped"], "truncated": state["truncated"],
            "duplicates": state["duplicates"], "visited": state["visited"], "cancelled": state["cancelled"],
            "basketItems": len(configurations), "basketIncomplete": False, "warnings": warnings,
        }

    def _write_obx(self, path: Path, configurations: list[dict[str, Any]]) -> None:
        """Write a cutBuffer/bskArticle document shaped like a pCon OBX export."""
        root = ET.Element("cutBuffer")
        ET.SubElement(root, "versionInfo", {"vendorKey": "EasternGraphics", "appKey": "pCon.planner",
                                             "appVersion": "8.15", "bskXmlVersion": "1.8.10"})
        items = ET.SubElement(root, "items")
        for config in configurations:
            article = ET.SubElement(items, "bskArticle", {"itemType": "BasketArticle", "updateState": "Current"})
            ET.SubElement(article, "manufacturer", {"id": "MK"})
            ET.SubElement(article, "series", {"id": "DM"})
            ET.SubElement(article, "artNr", {"type": "base"}).text = config["baseArticle"]
            ET.SubElement(article, "artNr", {"type": "final"}).text = config["finalArticle"]
            ET.SubElement(article, "artNr", {"type": "ofmlvarcode"}).text = config["ofmlVariantCode"]
            ET.SubElement(article, "itemPrice", {"type": "sale", "pd": "1",
                                                 "value": f"{config['salesPrice']:.2f}", "currency": "GBP"})
            ET.SubElement(article, "priceDate", {"value": "2026-10-30"})
            ET.SubElement(article, "quantity", {"count": "1"})
            for assignment in config["assignments"]:
                ET.SubElement(article, "feature", {"name": assignment["key"], "value": assignment["valueKey"],
                                                   "flags": "1"})
        path.parent.mkdir(parents=True, exist_ok=True)
        text = ET.tostring(root, encoding="unicode")
        if self.truncate_obx:
            text = text[: len(text) // 2]
        path.write_text("<?xml version='1.0' encoding='utf-8'?>\n" + text, encoding="utf-8")


__all__ = ["ARTICLES", "FakeArticle", "FakePconPlugin", "PACKAGES"]
