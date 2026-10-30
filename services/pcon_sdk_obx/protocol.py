"""Job protocol shared with the MK OBX Generator pCon.planner plugin.

The pCon.planner Plugin SDK 8.15 is an in-process .NET API: there is no COM,
command-line or network entry point into pCon.planner. The Workbench therefore
talks to a small plugin (``tools/pcon_obx_plugin``) that runs inside
pCon.planner and watches a job directory. Every exchange is one JSON request
file answered by one JSON result file. This module is the single definition of
that contract on the Python side; ``JobProtocol.cs`` mirrors it in the plugin.

Nothing in here evaluates OFML relations, builds permutations or writes OBX.
Those operations are performed by pCon.planner through the SDK; the protocol
only transports selections and results.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

#: Bumped whenever the request/result shape changes. The plugin refuses
#: requests from a different major version so stale installs fail loudly.
PROTOCOL_VERSION = 1

#: Request kinds understood by the plugin.
KIND_PING = "ping"
KIND_CATALOG = "catalog"
KIND_ARTICLES = "articles"
KIND_PROPERTIES = "properties"
KIND_GENERATE = "generate"

#: Property handling modes accepted by a generate request.
MODE_DEFAULT = "default"   # leave the value pCon assigns
MODE_FIXED = "fixed"       # set one explicit value
MODE_VARY = "vary"         # enumerate every value pCon offers (ValueSet)

PROPERTY_MODES = (MODE_DEFAULT, MODE_FIXED, MODE_VARY)

#: File names used inside the job directory.
HEARTBEAT_FILE = "plugin.heartbeat.json"
REQUEST_SUFFIX = ".request.json"
RESULT_SUFFIX = ".result.json"
PROGRESS_SUFFIX = ".progress.json"
PENDING_SUFFIX = ".pending"
CANCEL_SUFFIX = ".cancel"


class PluginProtocolError(RuntimeError):
    """A result file could not be interpreted or reported a plugin failure."""


@dataclass(frozen=True)
class PluginHeartbeat:
    """Liveness record the plugin rewrites every few seconds."""

    plugin_version: str = ""
    protocol_version: int = 0
    planner_ready: bool = False
    timestamp: float = 0.0
    job_dir: str = ""
    planner_version: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PluginHeartbeat":
        return cls(
            plugin_version=str(data.get("pluginVersion", "") or ""),
            protocol_version=int(data.get("protocolVersion", 0) or 0),
            planner_ready=bool(data.get("plannerReady", False)),
            timestamp=float(data.get("timestamp", 0.0) or 0.0),
            job_dir=str(data.get("jobDir", "") or ""),
            planner_version=str(data.get("plannerVersion", "") or ""),
        )


@dataclass(frozen=True)
class CatalogPackage:
    """One registered OFML package as reported by ``Articles.Package``."""

    package_name: str
    manufacturer_id: str
    manufacturer_name: str
    program_ids: tuple[str, ...]
    program: str
    program_name: str
    package_type: str
    version: str = ""
    distribution_region: str = ""
    has_catalog: bool = False

    @property
    def label(self) -> str:
        name = self.program_name or self.program
        ids = ",".join(self.program_ids)
        return f"{name} [{ids}]" if ids else name

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CatalogPackage":
        raw_ids = data.get("programIds", "") or ""
        if isinstance(raw_ids, str):
            ids = tuple(part.strip() for part in raw_ids.split(";") if part.strip())
        else:
            ids = tuple(str(part).strip() for part in raw_ids if str(part).strip())
        return cls(
            package_name=str(data.get("packageName", "") or ""),
            manufacturer_id=str(data.get("manufacturerId", "") or ""),
            manufacturer_name=str(data.get("manufacturerName", "") or ""),
            program_ids=ids,
            program=str(data.get("program", "") or ""),
            program_name=str(data.get("programName", "") or ""),
            package_type=str(data.get("type", "") or ""),
            version=str(data.get("version", "") or ""),
            distribution_region=str(data.get("distributionRegion", "") or ""),
            has_catalog=bool(data.get("hasCatalog", False)),
        )


@dataclass(frozen=True)
class CatalogArticle:
    """One insertable catalogue article (``CatalogItemType.Article``)."""

    article_number: str
    variant_code: str = ""
    variant_key: str = ""
    package_name: str = ""
    label: str = ""
    description: str = ""
    in_catalog_tree: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CatalogArticle":
        return cls(
            article_number=str(data.get("articleNumber", "") or ""),
            variant_code=str(data.get("variantCode", "") or ""),
            variant_key=str(data.get("variantKey", "") or ""),
            package_name=str(data.get("packageName", "") or ""),
            label=str(data.get("label", "") or ""),
            description=str(data.get("description", "") or ""),
            in_catalog_tree=bool(data.get("inCatalogTree", True)),
        )


@dataclass(frozen=True)
class PropertyChoice:
    """One entry of ``IProperty.ValueSet`` (a ``ChoicePropertyValue``)."""

    key: str
    text: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PropertyChoice":
        return cls(key=str(data.get("key", "") or ""), text=str(data.get("text", "") or ""))


@dataclass(frozen=True)
class ArticleProperty:
    """One ``IProperty`` of an instantiated article as pCon reports it."""

    key: str
    name: str
    property_type: str
    state: str = ""
    value_key: str = ""
    value_text: str = ""
    description: str = ""
    choices: tuple[PropertyChoice, ...] = ()
    editable: bool = True
    hidden: bool = False

    @property
    def is_choice(self) -> bool:
        return self.property_type.lower() == "choice"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArticleProperty":
        return cls(
            key=str(data.get("key", "") or ""),
            name=str(data.get("name", "") or ""),
            property_type=str(data.get("type", "") or ""),
            state=str(data.get("state", "") or ""),
            value_key=str(data.get("valueKey", "") or ""),
            value_text=str(data.get("valueText", "") or ""),
            description=str(data.get("description", "") or ""),
            choices=tuple(PropertyChoice.from_dict(c) for c in data.get("choices", []) or []),
            editable=bool(data.get("editable", True)),
            hidden=bool(data.get("hidden", False)),
        )


@dataclass(frozen=True)
class ArticleInfo:
    """Basket-level identity of one configured article (``IBasketArticleItem``)."""

    base_number: str = ""
    final_number: str = ""
    variant_code: str = ""
    ofml_variant_code: str = ""
    short_text: str = ""
    manufacturer_id: str = ""
    series_id: str = ""
    currency: str = ""
    purchase_price: float | None = None
    sales_price: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArticleInfo":
        return cls(
            base_number=str(data.get("baseNumber", "") or ""),
            final_number=str(data.get("finalNumber", "") or ""),
            variant_code=str(data.get("variantCode", "") or ""),
            ofml_variant_code=str(data.get("ofmlVariantCode", "") or ""),
            short_text=str(data.get("shortText", "") or ""),
            manufacturer_id=str(data.get("manufacturerId", "") or ""),
            series_id=str(data.get("seriesId", "") or ""),
            currency=str(data.get("currency", "") or ""),
            purchase_price=_optional_float(data.get("purchasePrice")),
            sales_price=_optional_float(data.get("salesPrice")),
        )


@dataclass(frozen=True)
class PropertyAssignment:
    """One value applied (or recorded) for a property key."""

    key: str
    value_key: str
    name: str = ""
    value_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "valueKey": self.value_key,
                "name": self.name, "valueText": self.value_text}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PropertyAssignment":
        return cls(
            key=str(data.get("key", "") or ""),
            value_key=str(data.get("valueKey", "") or ""),
            name=str(data.get("name", "") or ""),
            value_text=str(data.get("valueText", "") or ""),
        )


@dataclass(frozen=True)
class PropertyRule:
    """How the generator treats one property during enumeration."""

    key: str
    mode: str = MODE_DEFAULT
    value_key: str = ""

    def __post_init__(self) -> None:
        if self.mode not in PROPERTY_MODES:
            raise ValueError(f"Unknown property mode {self.mode!r} for {self.key!r}")
        if self.mode == MODE_FIXED and not self.value_key:
            raise ValueError(f"Fixed property {self.key!r} needs a value")

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "mode": self.mode, "valueKey": self.value_key}


@dataclass(frozen=True)
class ArticleSelection:
    """One base article to generate from."""

    article_number: str
    variant_code: str = ""
    package_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"articleNumber": self.article_number, "variantCode": self.variant_code,
                "packageName": self.package_name}


@dataclass(frozen=True)
class GenerationPlan:
    """A complete, validated generate request."""

    manufacturer_id: str
    series_id: str
    catalog_package: str
    articles: tuple[ArticleSelection, ...]
    rules: tuple[PropertyRule, ...]
    output_path: str
    max_configurations: int = 500
    discard_unsaved_planning: bool = False
    price_date: str = ""   # ISO yyyy-mm-dd, empty keeps pCon's current price date
    #: Automatic mode: the plugin varies every visible, editable choice property
    #: that no rule pins (fixed) or excludes (default). Explicit mode varies only
    #: the rules marked ``vary``.
    vary_all: bool = True
    #: Drop configurations whose final article number was already produced.
    deduplicate: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "varyAll": bool(self.vary_all),
            "deduplicate": bool(self.deduplicate),
            "manufacturerId": self.manufacturer_id,
            "seriesId": self.series_id,
            "catalogPackage": self.catalog_package,
            "articles": [a.to_dict() for a in self.articles],
            "properties": [r.to_dict() for r in self.rules],
            "outputPath": self.output_path,
            "maxConfigurations": int(self.max_configurations),
            "discardUnsavedPlanning": bool(self.discard_unsaved_planning),
            "priceDate": self.price_date,
        }


@dataclass(frozen=True)
class GeneratedConfiguration:
    """One configured article instance the plugin inserted into the planning."""

    index: int
    base_article: str
    final_article: str
    variant_code: str = ""
    ofml_variant_code: str = ""
    assignments: tuple[PropertyAssignment, ...] = ()
    features: tuple[PropertyAssignment, ...] = ()
    currency: str = ""
    purchase_price: float | None = None
    sales_price: float | None = None
    status: str = "ok"
    message: str = ""

    @property
    def configuration_text(self) -> str:
        return "; ".join(
            f"{a.name or a.key}={a.value_text or a.value_key}" for a in self.assignments
        ) or "—"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GeneratedConfiguration":
        return cls(
            index=int(data.get("index", 0) or 0),
            base_article=str(data.get("baseArticle", "") or ""),
            final_article=str(data.get("finalArticle", "") or ""),
            variant_code=str(data.get("variantCode", "") or ""),
            ofml_variant_code=str(data.get("ofmlVariantCode", "") or ""),
            assignments=tuple(PropertyAssignment.from_dict(a) for a in data.get("assignments", []) or []),
            features=tuple(PropertyAssignment.from_dict(a) for a in data.get("features", []) or []),
            currency=str(data.get("currency", "") or ""),
            purchase_price=_optional_float(data.get("purchasePrice")),
            sales_price=_optional_float(data.get("salesPrice")),
            status=str(data.get("status", "ok") or "ok"),
            message=str(data.get("message", "") or ""),
        )


@dataclass
class GenerationResult:
    """Outcome of one generate request."""

    output_path: str = ""
    exported: bool = False
    configurations: list[GeneratedConfiguration] = field(default_factory=list)
    skipped: int = 0
    duplicates: int = 0
    visited: int = 0
    truncated: bool = False
    cancelled: bool = False
    basket_items: int = 0
    basket_incomplete: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def generated(self) -> int:
        return sum(1 for c in self.configurations if c.status == "ok")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GenerationResult":
        return cls(
            output_path=str(data.get("outputPath", "") or ""),
            exported=bool(data.get("exported", False)),
            configurations=[GeneratedConfiguration.from_dict(c) for c in data.get("configurations", []) or []],
            skipped=int(data.get("skipped", 0) or 0),
            duplicates=int(data.get("duplicates", 0) or 0),
            visited=int(data.get("visited", 0) or 0),
            truncated=bool(data.get("truncated", False)),
            cancelled=bool(data.get("cancelled", False)),
            basket_items=int(data.get("basketItems", 0) or 0),
            basket_incomplete=bool(data.get("basketIncomplete", False)),
            warnings=[str(w) for w in data.get("warnings", []) or []],
        )


@dataclass(frozen=True)
class JobProgress:
    """Progress record the plugin rewrites while a generate request runs."""

    processed: int = 0
    total: int = 0
    message: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobProgress":
        return cls(
            processed=int(data.get("processed", 0) or 0),
            total=int(data.get("total", 0) or 0),
            message=str(data.get("message", "") or ""),
        )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_request(job_id: str, kind: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Assemble the request envelope the plugin expects."""
    body = {"protocolVersion": PROTOCOL_VERSION, "id": job_id, "kind": kind}
    body.update(payload or {})
    return body


def encode(body: dict[str, Any]) -> str:
    return json.dumps(body, ensure_ascii=False, indent=2)


def parse_result(text: str, expected_id: str) -> dict[str, Any]:
    """Validate a result envelope and return its payload.

    Raises :class:`PluginProtocolError` for malformed JSON, a mismatched job
    id, an incompatible protocol version, or a failure reported by the plugin.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PluginProtocolError(f"Plugin result is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise PluginProtocolError("Plugin result must be a JSON object.")
    if str(data.get("id", "")) != expected_id:
        raise PluginProtocolError(
            f"Plugin result id {data.get('id')!r} does not match request {expected_id!r}."
        )
    version = int(data.get("protocolVersion", 0) or 0)
    if version != PROTOCOL_VERSION:
        raise PluginProtocolError(
            f"Plugin protocol version {version} differs from expected {PROTOCOL_VERSION}; "
            "reinstall the MK OBX Generator plugin."
        )
    if not data.get("ok", False):
        raise PluginProtocolError(str(data.get("error") or "Plugin reported an unspecified failure."))
    return data


__all__ = [name for name in globals() if not name.startswith("_")]
