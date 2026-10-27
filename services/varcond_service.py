"""Variant-condition (VARCOND) generation for PA_PRICING.

Offline port of PDM ``VarCondThread.execThread`` ("Generate VARCOND for
PA_PRICING (pCon)"). It reproduces PDM's output from the active snapshot - no
database access - by carrying every ingredient PDM's queries need into the
snapshot at load time:

* ``article_components``     - super-product BOM (``ItemComponents``); the rule
  targets. VARCOND is a SUPER-PRODUCT feature: only articles with a BOM emit
  rules, one ``$VARCOND = '<sub_item>' IF <config>`` per sub-item, all sharing
  the super product's property configuration.
* ``article_varcond_terms``  - the ordered attribute rows (name, display order,
  ``HasDependentOptions``, ``OrderCodeValue``) PDM's attribute query returns.
* ``article_prefix_length``  - PDM ``getArticlePrefixLength`` per article, used
  to slice parametric dimension codes (Width/Height/Depth) out of the article
  number exactly as PDM's ``SUBSTRING`` CASE does.

Property names are normalised through the exact port of
``parseAttributeNameAsPConProperty`` (product-specific special cases included)
plus PDM's second-word capitalisation. Exclusions/substitutions use PDM's
substring semantics. Order codes have dots stripped. Rules are joined with
``",\\r\\n"`` and terminated with a trailing ``"\\r\\n"``.

Option-increment price-suffix rules (``$VARCOND = '<sub> <optionId>=' + Name``)
are emitted per option that carries an ``ItemOptionValues.IncrementalPrice`` for
the sub-item (general path of ``getOptionIncrementSuffixes``); option names use
the ``SIFImport.camelCase`` port. Compiled-IL-derived property renames for
HZ13/HZ14, RYMPSH, RY3VNN...HW, RYT, and RY2U, plus the RYT/RYMPSH alternate
suffix format, are implemented in the opt-in legacy mode. The snapshot's
option-increment rows have not been proven equivalent to the legacy live query.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from models.snapshot import Snapshot
from services.base_service import BaseService


@dataclass
class VarCondRule:
    """One generated variant-condition line for a target (sub-item)."""

    article: str                                # the target sub-item
    body: str                                   # the shared "IF ... AND ..." expr
    rule: str                                   # full "$VARCOND = '<sub>' IF ..."


@dataclass
class VarCondResult:
    """Result of a VARCOND generation run."""

    rules: list[VarCondRule] = field(default_factory=list)
    text: str = ""                              # all rules joined, ready to export
    warnings: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)  # properties excluded


class VarCondService(BaseService):
    """Generate PA_PRICING variant-condition rules offline (PDM parity)."""

    # -- property-name parsing (ports of the PDM helpers) -----------------

    @staticmethod
    def _capitalise_second_word(name: str) -> str:
        """Port of PDM's attribute-query name CASE: upper-case the first letter
        of the second word (the char after the first space)."""
        idx = name.find(" ")
        if idx < 0 or idx + 1 >= len(name):
            return name
        return name[: idx + 1] + name[idx + 1 : idx + 2].upper() + name[idx + 2 :]

    @staticmethod
    def _parse_attr_as_pcon(attrname: str, itemcontext: str) -> str:
        """Exact port of ``CADMaintenance.parseAttributeNameAsPConProperty``.

        Applies the product-specific special-case renames (Castors/Glides,
        Hinge, Power Entry, RYSCR*/RYWX/HZ/RY3X prefixes) and strips a trailing
        ``" (...)"`` qualifier. Spaces are turned into underscores by the caller.
        """
        low = attrname.lower()
        if "castor" in low and "glide" in low:
            attrname = "Castors Glides"
        elif attrname == "Hinge / closure":
            attrname = "Hinge"
        elif attrname == "Power Entry cord":
            attrname = "Power Entry"

        if "RYSCRM" in itemcontext:
            if attrname.lower() in ("width", "material type"):
                attrname = "Panel_" + attrname
        elif "RYSCR" in itemcontext:
            if attrname.lower() in ("height", "width", "material type"):
                attrname = "Screen_" + attrname
            if "RYSCRL" in itemcontext:
                attrname += "_FS"
        elif "RYWX" in itemcontext:
            if attrname.lower() == "width":
                attrname = "Wire_Management_" + attrname
        elif itemcontext.startswith("HZ"):
            if attrname.lower() in ("upper tiles", "upper_tile_front"):
                attrname = "Upper_Tile_Front"
            if attrname.lower() == "upper tile back":
                attrname = "Upper_Tile_Back"
            if attrname.lower() in ("lower tiles", "lower_tile_front"):
                attrname = "Lower_Tile_Front"
            if attrname.lower() == "lower tile back":
                attrname = "Lower_Tile_Back"
            if attrname.lower() == "board material type":
                attrname = "Board_Material_Type"
            if attrname.lower() == "foot":
                attrname = "Glides_Castors"

        if " (" in attrname:
            idx = attrname.index(" (")
            suffix = attrname[idx:]
            attrname = attrname[:idx]
            if "RY3X" in itemcontext:
                if suffix == " (A)":
                    attrname += "_A"
                elif suffix == " (B)":
                    attrname += "_B"
        return attrname

    def _pcon_property_name(self, raw_name: str, item: str) -> str:
        """Full PDM property-name normalisation: second-word capitalisation ->
        ``parseAttributeNameAsPConProperty`` -> spaces to underscores."""
        name = self._capitalise_second_word((raw_name or "").strip())
        name = self._parse_attr_as_pcon(name, item or "")
        return name.replace(" ", "_")

    @staticmethod
    def _parse_pcon_property_name(name: str) -> str:
        """Port of ``CADMaintenance.ParsePConPropertyName``: parentheses are
        dropped, each space becomes ``_`` and the next kept character is
        upper-cased. Verified against the real helper by
        ``scripts/varcond_parity/run_legacy_helpers.ps1``."""
        out = ""
        capitalise = False
        for ch in name:
            if ch in "()":
                continue
            if capitalise:
                out += ch.upper()
                capitalise = False
            elif ch == " ":
                out += "_"
                capitalise = True
            else:
                out += ch
        return out

    @staticmethod
    def _apply_substitutions(prop: str, subs: str) -> str:
        """Exact port of PDM's substitution pass (comma list of ``old=new``).

        Replaces ``old`` with ``new`` in ``prop`` only when ``prop`` contains
        ``old``, differs from ``new`` and either does not already contain ``new``
        or ``new`` has no underscore.
        """
        if not subs:
            return prop
        for token in subs.split(","):
            if not token or "=" not in token:
                continue
            old = token[: token.index("=")]
            new = token[token.index("=") + 1 :]
            if old in prop and prop != new and (new not in prop or "_" not in new):
                prop = prop.replace(old, new)
        return prop

    # -- option-increment name parsing (ports of the PDM helpers) ---------

    #: brand/word fixups applied by ``SIFImport.camelCase`` after casing.
    _CAMEL_FIXUPS = (
        ("Herman miller", "Herman Miller"), ("herman miller", "Herman Miller"),
        ("logitech", "Logitech"), ("Logitechg", "LogitechG"),
        ("europe", "Europe"), ("emea", "EMEA"), ("uk", "UK"),
        ("france", "France"), ("germany", "Germany"), ("italy", "Italy"),
        ("spain", "Spain"), ("singapore", "Singapore"), ("india", "India"),
        ("8z pel", "8Z Pel"), ("y-tower", "Y-tower"),
        ("posturefit", "PostureFit"), ("PostureFit sl", "PostureFit SL"),
    )

    @classmethod
    def _camel_word(cls, word: str) -> str:
        """Capitalise the first letter and lower-case the rest of one word, but
        stop lower-casing at a ``[`` (PDM's OrderCodeValue/ModelSuffix marker)."""
        if len(word) <= 1:
            return word
        rest = word[1:]
        lowered = ""
        for ch in rest:
            if ch == "[":
                break
            lowered += ch.lower()
        if len(lowered) < len(rest):
            lowered += rest[len(lowered):]
        return word[0].upper() + lowered

    @classmethod
    def _camel_case(cls, value: str) -> str:
        """Port of ``SIFImport.camelCase`` (general path used for option names)."""
        value = value or ""
        if " " in value:
            words = [cls._camel_word(w) for w in value.split(" ") if w != ""]
            value = " ".join(words).strip()
        elif len(value) > 1:
            value = cls._camel_word(value)
        for old, new in cls._CAMEL_FIXUPS:
            value = value.replace(old, new)
        if value == "fr":
            value = "FR"
        if value.endswith(" fr"):
            value = value[: value.rfind(" fr")] + " FR"
        return value

    @classmethod
    def _pcon_option_name(cls, name: str) -> str:
        """Port of PDM's option-name -> pCon property: ``camelCase`` then drop
        ``/`` and turn spaces (and doubled underscores) into single ``_``."""
        return (
            cls._camel_case(name).replace("/", "").replace(" ", "_").replace("__", "_")
        )

    @staticmethod
    def _item_prefix(item: str) -> str:
        """Item name up to and including the first ``.`` (PDM ``text14`` rule)."""
        item = (item or "").strip()
        dot = item.find(".")
        return item[: dot + 1] if dot > -1 else item

    # -- live PDM generation ------------------------------------------------

    def generate_live(
        self,
        article_codes: Sequence[str],
        prefix: str = "",
        property_exclusions: str = "",
        property_substitutions: str = "",
    ) -> VarCondResult:
        """Generate VARCOND using fresh, read-only PDM queries, not snapshots.

        The selected parent article codes define the scope. BOM, attributes,
        prefix-length metadata and option increments are re-read from PDM for
        this run. SQL remains in PDMRepository; the legacy output formatting
        and exclusion/substitution semantics are retained here.
        """
        from repositories.pdm_repository import PDMRepository

        result = VarCondResult()
        codes = list(dict.fromkeys((code or "").strip() for code in article_codes if (code or "").strip()))
        if not codes:
            result.warnings.append("No parent article codes selected.")
            return result

        repo = PDMRepository(self.context)
        conn = repo.get_connection()
        try:
            for parent in codes:
                rows = repo._execute(
                    "SELECT i.ItemId, i.Item, i.Notes, pr.ProductCategoryId, p.Product "
                    "FROM Item i INNER JOIN Product p ON i.ProductId = p.ProductId "
                    "INNER JOIN ProductRange pr ON p.ProductRangeId = pr.ProductRangeId "
                    "WHERE i.Item = ?",
                    (parent,), connection=conn,
                )
                if not rows:
                    result.warnings.append(f"{parent}: article was not found in live PDM.")
                    continue
                item_row = rows[0]
                item_id = getattr(item_row, "ItemId")
                category_id = getattr(item_row, "ProductCategoryId", None)

                components = repo.fetch_item_components([item_id], connection=conn)
                if not components:
                    continue

                # CADMaintenance.getArticlePrefixLength: numeric Item.Notes,
                # falling back to the category's master item's Notes.
                prefix_length = 0
                notes = str(getattr(item_row, "Notes", "") or "").split(",")[0].strip()
                if notes.isdigit():
                    prefix_length = int(notes)
                if prefix_length <= 0 and category_id is not None:
                    master_rows = repo.fetch_category_master_notes([category_id], connection=conn)
                    for master in master_rows:
                        token = str(getattr(master, "Notes", "") or "").split(",")[0].strip()
                        if token.isdigit():
                            prefix_length = int(token)
                            break
                if prefix_length <= 0:
                    result.warnings.append(
                        f"{parent}: article prefix length is undefined; parametric codes may be incorrect."
                    )

                attr_sql = (
                    "SELECT DISTINCT Product.Product, "
                    "CASE WHEN ABS(attr.HasDependentOptions) > 0 THEN "
                    "SUBSTRING(Item.Item, ? + 1 + (SELECT COALESCE((SELECT SUM(ABS(attr2.HasDependentOptions)) "
                    "FROM Item i2 INNER JOIN BaseAttributeValues bav2 ON i2.ItemId = bav2.ItemId "
                    "INNER JOIN AttributeValue atval2 ON bav2.AttributeValueId = atval2.AttributeValueId "
                    "INNER JOIN Attribute attr2 ON atval2.AttributeId = attr2.AttributeId "
                    "WHERE i2.Item = ? AND (atval2.OrderCodeValue IS NOT NULL OR ABS(attr2.HasDependentOptions) <> 0) "
                    "AND attr2.DisplayOrder < attr.DisplayOrder), 0)), ABS(attr.HasDependentOptions)) "
                    "ELSE atval.OrderCodeValue END AS OrderCodeValue, attr.DisplayOrder, "
                    "CASE WHEN CHARINDEX(' ', attr.Name) > 0 THEN "
                    "SUBSTRING(attr.Name, 1, CHARINDEX(' ', attr.Name)) + "
                    "UPPER(SUBSTRING(attr.Name, CHARINDEX(' ', attr.Name) + 1, 1)) + "
                    "SUBSTRING(attr.Name, CHARINDEX(' ', attr.Name) + 2, 99) ELSE attr.Name END AS prop "
                    "FROM Product INNER JOIN Item ON Product.ProductId = Item.ProductId "
                    "INNER JOIN BaseAttributeValues bav ON Item.ItemId = bav.ItemId "
                    "INNER JOIN AttributeValue atval ON bav.AttributeValueId = atval.AttributeValueId "
                    "INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId "
                    "WHERE Item.Item = ? AND (atval.OrderCodeValue IS NOT NULL OR ABS(attr.HasDependentOptions) > 0) "
                    "ORDER BY attr.DisplayOrder"
                )
                attrs = repo._execute(
                    attr_sql, (prefix_length, parent, parent), connection=conn
                )
                condition_parts: list[str] = []
                for attr in attrs:
                    prop = self._pcon_property_name(str(getattr(attr, "prop", "") or ""), parent)
                    if property_exclusions and prop in property_exclusions:
                        if prop not in result.excluded:
                            result.excluded.append(prop)
                        continue
                    prop = self._apply_substitutions(prop, property_substitutions)
                    value = str(getattr(attr, "OrderCodeValue", "") or "").replace(".", "")
                    condition_parts.append(
                        f"{(prefix.strip() + '.') if prefix.strip() else ''}{prop} = '{value}'"
                    )
                body = "IF" + ((" " + " AND ".join(condition_parts)) if condition_parts else "")

                for comp in components:
                    sub = str(getattr(comp, "SubItem", "") or "").strip()
                    if not sub:
                        continue
                    rule = f"$VARCOND = '{sub}' {body}"
                    result.rules.append(VarCondRule(article=sub, body=body, rule=rule))
                    try:
                        qty = int(getattr(comp, "Quantity", 1) or 1)
                    except (TypeError, ValueError):
                        qty = 1
                    if qty > 1:
                        result.rules.append(VarCondRule(
                            article=sub, body=body,
                            rule=f"$SET_PRICING_FACTOR('{sub}', {qty}) {body}",
                        ))

                    # Live PDM option increment rows for this component prefix.
                    inc_rows = repo.fetch_item_option_increments(
                        [self._item_prefix(sub)], connection=conn
                    )
                    seen: set[int] = set()
                    for inc in inc_rows:
                        option_id = getattr(inc, "OptionId", None)
                        if option_id is None or int(option_id) in seen:
                            continue
                        seen.add(int(option_id))
                        option_name = self._pcon_option_name(
                            str(getattr(inc, "OptionName", "") or "")
                        )
                        option_name = self._apply_substitutions(option_name, property_substitutions)
                        suffix = f"'{sub} {option_id}=' + {option_name}"
                        result.rules.append(VarCondRule(
                            article=sub, body=body, rule=f"$VARCOND = {suffix} {body}"
                        ))
                        if qty > 1:
                            result.rules.append(VarCondRule(
                                article=sub, body=body,
                                rule=f"$SET_PRICING_FACTOR({suffix}, {qty}) {body}",
                            ))
        finally:
            conn.close()

        # Legacy emits repeated definitions and preserves order.
        if result.rules:
            result.text = ",\r\n".join(rule.rule for rule in result.rules) + "\r\n"
        return result

    # -- generation --------------------------------------------------------

    def generate(
        self,
        prefix: str = "",
        property_exclusions: str = "",
        property_substitutions: str = "",
        snapshot: Snapshot | None = None,
        *,
        legacy_exact: bool = False,
        article_codes: Sequence[str] | None = None,
    ) -> VarCondResult:
        """Build super-product VARCOND rules offline from the active snapshot.

        The default mode retains Workbench behavior. ``legacy_exact`` is a
        source-shaped port based on compiled legacy IL; runtime parity against
        the generator and equivalent SQL inputs is not yet verified.

        Parameters mirror PDM's ``SuperProductVarCondRelation`` form:

        * ``prefix``                 - pCon property-class prefix (usually empty).
        * ``property_exclusions``    - string; a property is dropped when its
          parsed name is a substring of this text (PDM ``IndexOf`` semantics).
        * ``property_substitutions`` - comma list of ``old=new`` renames.

        ``legacy_exact`` (opt-in) follows the compiled ``VarCondThread.execThread``
        literally instead of the Workbench refinements below (per-component IF
        filtering, identical-rule de-duplication, automatic exclusion of
        unresolved parametric codes). ``article_codes`` is the ordered parent
        list the legacy worker receives; it is only honoured in that mode.
        See ``tools/legacy_varcond_bridge/PARITY_REVIEW.md``.
        """
        snapshot = snapshot if snapshot is not None else self.context.active_snapshot
        result = VarCondResult()
        if snapshot is None:
            result.warnings.append("No active snapshot.")
            return result
        if legacy_exact:
            return self._generate_legacy_exact(
                snapshot, prefix, property_exclusions, property_substitutions,
                article_codes,
            )

        text6 = (prefix.strip() + ".") if prefix.strip() else ""
        components = snapshot.article_components or {}
        component_head_attrs = snapshot.component_head_attrs or {}
        terms_by_article = snapshot.article_varcond_terms or {}
        prefix_len_by_article = snapshot.article_prefix_length or {}
        increments_by_prefix = snapshot.option_increments or {}
        code_by_id = {
            str(a.id): (a.code or "")
            for a in snapshot.articles
            if a.id is not None
        }

        if not components:
            result.warnings.append(
                "No super-product BOM loaded (ItemComponents) - nothing to "
                "generate. VARCOND only applies to super products."
            )

        for article_id, comps in components.items():
            item_name = code_by_id.get(str(article_id), "")
            prefix_length = prefix_len_by_article.get(str(article_id), 0) or 0
            terms = terms_by_article.get(str(article_id), [])

            # Decode each parent head term once into (raw attr name, IF fragment),
            # advancing the parametric position across the parent's FULL layout so
            # the SUBSTRING math stays correct even when a component omits a prop.
            decoded: list[tuple[str, str]] = []
            running = 0                          # sum of prior parametric widths
            for term in terms:
                hdo = int(term.get("has_dependent_options", 0) or 0)
                base_code = str(term.get("order_code", "") or "")
                # PDM WHERE: include only if OrderCodeValue set OR dependent.
                if not base_code and hdo == 0:
                    continue

                if hdo != 0:
                    width = abs(hdo)
                    start = prefix_length + 1 + running   # SQL SUBSTRING is 1-based
                    code = item_name[start - 1 : start - 1 + width]
                    running += width
                    # PDM flags a short code only for the dimension attributes
                    # (Height/Width/Depth); a width-1 attribute (e.g. Base type)
                    # legitimately has a 1-char code.
                    _nm = (term.get("name", "") or "").lower()
                    if (("height" in _nm) or ("width" in _nm) or ("depth" in _nm)) \
                            and len(code.replace(".", "")) < 2:
                        result.warnings.append(
                            f"{item_name}: parametric code for "
                            f"'{term.get('name', '')}' resolved to '{code}' "
                            "(shorter than 2 characters)."
                        )
                else:
                    code = base_code
                code = code.replace(".", "")

                # Automatic exclusion: a parametric property whose code does not
                # resolve from this article number is not applicable to it - only
                # the properties actually encoded in the article number stay.
                if hdo != 0 and not code:
                    continue

                prop = self._pcon_property_name(term.get("name", ""), item_name)

                if property_exclusions and prop in property_exclusions:
                    if prop not in result.excluded:
                        result.excluded.append(prop)
                    continue

                prop = self._apply_substitutions(prop, property_substitutions)
                decoded.append(
                    (str(term.get("name", "") or ""), f"{text6}{prop} = '{code}'")
                )

            for comp in comps:
                sub = (comp.get("sub_item") or "").strip()
                if not sub:
                    continue
                # A component is conditioned only by the head properties it itself
                # carries (its own BaseAttributeValues); absent that info, keep the
                # parent's full set (PDM VarCondThread behaviour).
                own = component_head_attrs.get(sub)
                if own is None:
                    parts = [frag for _n, frag in decoded]
                else:
                    own_set = set(own)
                    parts = [frag for n, frag in decoded if n in own_set]
                body = ("IF " + " AND ".join(parts)) if parts else "IF"
                result.rules.append(
                    VarCondRule(
                        article=sub, body=body, rule=f"$VARCOND = '{sub}' {body}"
                    )
                )
                try:
                    qty = int(comp.get("quantity", 1) or 1)
                except (TypeError, ValueError):
                    qty = 1
                if qty > 1:
                    result.rules.append(
                        VarCondRule(
                            article=sub,
                            body=body,
                            rule=f"$SET_PRICING_FACTOR('{sub}', {qty}) {body}",
                        )
                    )

                # Option-increment price-suffix lines (PDM getOptionIncrementSuffixes
                # general path): one per option that carries an incremental price
                # for this sub-item, sharing the same IF condition.
                seen_options: set = set()
                for inc in increments_by_prefix.get(self._item_prefix(sub), []):
                    option_id = inc.get("option_id")
                    if option_id is None or option_id in seen_options:
                        continue
                    seen_options.add(option_id)
                    name = self._pcon_option_name(inc.get("option_name", ""))
                    name = self._apply_substitutions(name, property_substitutions)
                    suffix = f"'{sub} {option_id}=' + {name}"
                    result.rules.append(
                        VarCondRule(
                            article=sub, body=body, rule=f"$VARCOND = {suffix} {body}"
                        )
                    )
                    if qty > 1:
                        result.rules.append(
                            VarCondRule(
                                article=sub,
                                body=body,
                                rule=f"$SET_PRICING_FACTOR({suffix}, {qty}) {body}",
                            )
                        )

        # Deduplicate identical rules: a component that does not depend on the
        # varying head property produces the SAME rule for every super-item
        # variant that shares it (PDM emits each copy). One entry suffices - a
        # smaller, byte-for-byte equivalent relation. Order preserved (first win).
        seen_rules: set = set()
        unique: list[VarCondRule] = []
        for r in result.rules:
            if r.rule not in seen_rules:
                seen_rules.add(r.rule)
                unique.append(r)
        result.rules = unique

        # PDM joins entries with ",\r\n" and terminates with a trailing "\r\n".
        if result.rules:
            result.text = ",\r\n".join(r.rule for r in result.rules) + "\r\n"

        if result.excluded:
            n = len(result.excluded)
            result.warnings.append(
                f"{n} property{'ies' if n != 1 else ''} excluded: "
                + ", ".join(result.excluded)
            )
        return result

    # -- legacy-exact mode ---------------------------------------------------

    #: ``VarCondThread`` family prefixes whose suffix rules use the
    #: ``'<optionId>=<target>_' + Name`` form (IL: the RYT / RYMPSH flag).
    _LEGACY_ALT_SUFFIX_PREFIXES = ("RYT", "RYMPSH")

    def _generate_legacy_exact(
        self,
        snapshot: Snapshot,
        prefix: str,
        property_exclusions: str,
        property_substitutions: str,
        article_codes: Sequence[str] | None,
    ) -> VarCondResult:
        """Literal port of ``VarCondThread.execThread`` (assembly 1.0.9686.24988).

        Derived from the compiled IL, not from runtime output of the generator
        itself: pass one collects ``(target, IF text, quantity)`` for every BOM
        row of every parent in list order; pass two emits ``$VARCOND`` /
        ``$SET_PRICING_FACTOR`` text per target plus option-increment suffix
        rules. There is no de-duplication, no per-component IF filtering and no
        automatic exclusion of unresolved parametric codes.

        Known input gaps (reported as warnings, never hidden): legacy reads
        suffixes from ``PDMOptionDataReportWithIncBase`` while the snapshot only
        carries ``ItemOptionValues``; non-BOM parents need the Product name,
        which the snapshot does not carry.
        """
        result = VarCondResult()
        # IL: text6 is built only when the *untrimmed* prefix is non-empty, so a
        # whitespace-only prefix yields "." (unlike the default mode).
        text6 = (prefix.strip() + ".") if prefix != "" else ""
        components = snapshot.article_components or {}
        terms_by_article = snapshot.article_varcond_terms or {}
        prefix_len_by_article = snapshot.article_prefix_length or {}
        increments_by_prefix = snapshot.option_increments or {}
        code_by_id = {
            str(a.id): (a.code or "") for a in snapshot.articles if a.id is not None
        }
        id_by_code: dict[str, str] = {}
        for art in snapshot.articles:
            if art.id is not None:
                id_by_code.setdefault(art.code or "", str(art.id))

        if article_codes is None:
            parents = [(code_by_id.get(str(aid), ""), str(aid)) for aid in components]
        else:
            parents = []
            for code in article_codes:
                aid = id_by_code.get(code)
                if aid is None:
                    result.warnings.append(
                        f"{code}: not in the snapshot; legacy would query it by "
                        "name, so its rows cannot be reproduced."
                    )
                    continue
                parents.append((code, aid))

        if not parents:
            result.warnings.append(
                "No super-product BOM loaded (ItemComponents) - nothing to generate."
            )

        targets: list[tuple[str, str, int]] = []      # (sub item, IF text, qty)
        for item_name, article_id in parents:
            prefix_length = prefix_len_by_article.get(article_id, 0) or 0
            if prefix_length == 0:
                result.warnings.append(
                    f"{item_name}: article prefix length undefined; legacy shows a "
                    "modal 'Article Prefix Length Undefined' Yes/No dialog "
                    "(No aborts the whole run). Assumed Yes."
                )
            body, accepted = self._legacy_if_body(
                item_name, terms_by_article.get(article_id, []), prefix_length,
                text6, property_exclusions, property_substitutions, result,
            )
            comps = self._legacy_component_order(components.get(article_id, []))
            if comps:
                for comp in comps:
                    targets.append(
                        (str(comp.get("sub_item") or ""), body,
                         self._legacy_quantity(comp.get("quantity")))
                    )
            elif accepted:
                result.warnings.append(
                    f"{item_name}: no BOM components. Legacy emits one rule "
                    "targeting the article code with its Product name removed; "
                    "the snapshot has no Product name, so that rule is not "
                    "reproduced."
                )

        suffix_inputs_seen = False
        for index, (sub, body, qty) in enumerate(targets):
            result.rules.append(
                VarCondRule(article=sub, body=body, rule=f"$VARCOND = '{sub}' {body}")
            )
            if qty > 1:
                result.rules.append(
                    VarCondRule(
                        article=sub, body=body,
                        rule=f"$SET_PRICING_FACTOR('{sub}', {qty}) {body}",
                    )
                )
            for option_id, name in self._legacy_suffix_entries(
                sub, increments_by_prefix, property_substitutions
            ):
                suffix_inputs_seen = True
                if sub.startswith(self._LEGACY_ALT_SUFFIX_PREFIXES):
                    suffix = f"'{option_id}={sub}_' + {name}"
                else:
                    suffix = f"'{sub} {option_id}=' + {name}"
                result.rules.append(
                    VarCondRule(article=sub, body=body, rule=f"$VARCOND = {suffix} {body}")
                )
                if qty > 1:
                    result.rules.append(
                        VarCondRule(
                            article=sub, body=body,
                            rule=f"$SET_PRICING_FACTOR({suffix}, {qty}) {body}",
                        )
                    )

        if suffix_inputs_seen:
            result.warnings.append(
                "Option-increment suffix rules use snapshot ItemOptionValues, not "
                "the legacy PDMOptionDataReportWithIncBase output; suffix parity "
                "is unverified."
            )
        if result.rules:
            result.text = ",\r\n".join(r.rule for r in result.rules) + "\r\n"
        return result

    def _legacy_if_body(
        self,
        item_name: str,
        terms: list[dict],
        prefix_length: int,
        text6: str,
        property_exclusions: str,
        property_substitutions: str,
        result: VarCondResult,
    ) -> tuple[str, bool]:
        """Port of the attribute query + IF builder; returns ``(IF text,
        whether any term was accepted)``."""
        ordered = sorted(terms, key=lambda t: int(t.get("order", 0) or 0))

        def qualifies(term: dict) -> bool:
            # SQL: OrderCodeValue IS NOT NULL OR ABS(HasDependentOptions) <> 0.
            # The snapshot stores NULL as "", so "" is treated as NULL.
            return bool(term.get("order_code")) or int(term.get("has_dependent_options", 0) or 0) != 0

        parts: list[str] = []
        seen_rows: set[tuple[str, int, str]] = set()
        for term in ordered:
            if not qualifies(term):
                continue
            order = int(term.get("order", 0) or 0)
            hdo = abs(int(term.get("has_dependent_options", 0) or 0))
            if hdo > 0:
                # SUBSTRING(Item, prefixLen + 1 + <sum of ABS(HDO) of qualifying
                # terms with a strictly lower DisplayOrder>, ABS(HDO))
                offset = sum(
                    abs(int(o.get("has_dependent_options", 0) or 0))
                    for o in ordered
                    if qualifies(o) and int(o.get("order", 0) or 0) < order
                )
                start = prefix_length + offset
                code = item_name[start : start + hdo]
            else:
                code = str(term.get("order_code") or "")
            sql_name = self._capitalise_second_word(str(term.get("name") or ""))
            row_key = (sql_name, order, code)
            if row_key in seen_rows:                  # SELECT DISTINCT
                continue
            seen_rows.add(row_key)

            prop = self._parse_attr_as_pcon(sql_name, item_name).replace(" ", "_")
            if prop in property_exclusions:           # IndexOf(prop) > -1, no empty guard
                if prop not in result.excluded:
                    result.excluded.append(prop)
                continue
            prop = self._apply_substitutions(prop, property_substitutions)
            parts.append(f"{text6}{prop} = '{code.replace('.', '')}'")
        body = ("IF " + " AND ".join(parts)) if parts else "IF"
        return body, bool(parts)

    @staticmethod
    def _legacy_component_order(comps: list[dict]) -> list[dict]:
        """``ORDER BY CONVERT(INT, ComponentSequence)`` (stable)."""
        def key(comp: dict) -> int:
            try:
                return int(str(comp.get("sequence", "")).strip())
            except ValueError:
                return 0
        return sorted(comps, key=key)

    @staticmethod
    def _legacy_quantity(value) -> int:
        """Legacy default 1; replaced only by an all-digit quantity text."""
        text = "" if value is None else str(value)
        return int(text) if text.isascii() and text.isdigit() else 1

    def _legacy_suffix_entries(
        self, sub: str, increments_by_prefix: dict, property_substitutions: str
    ) -> list[tuple[int, str]]:
        """Suffix (option id, property name) pairs for one target, with the
        legacy name de-duplication, product-family property renames and
        plain-replace substitutions."""
        entries: list[tuple[int, str]] = []
        names: list[str] = []
        seen_options: set = set()
        for inc in increments_by_prefix.get(self._item_prefix(sub), []):
            option_id = inc.get("option_id")
            if option_id is None or option_id in seen_options:
                continue
            seen_options.add(option_id)
            name = self._pcon_option_name(inc.get("option_name", ""))
            if "fabric" in name.lower() and sub.startswith(("HZ13", "HZ14")):
                name = (
                    "Upper_Front_Fabric_Type" if sub.startswith("HZ13")
                    else "Lower_Front_Fabric_Type"
                )
            elif sub.startswith("RYMPSH"):
                name = "Panel_Finish"
            elif sub.startswith("RY3VNN") and sub.endswith("HW"):
                name = "Screen_Finish"
            elif sub.startswith("RYT"):
                name = "Worktop_Finish"
            elif sub.startswith("RY2U"):
                name = "Hardware_Pack_Finish"
            if name in names:                         # V_68.Contains(name)
                continue
            names.append(name)
            entries.append((int(option_id), name))
        if property_substitutions:
            for token in property_substitutions.split(","):
                if not token or "=" not in token:
                    continue
                old, new = token.split("=", 1)
                if old == "":
                    continue                          # legacy would throw here
                entries = [
                    (oid, name.replace(old, new) if old in name else name)
                    for oid, name in entries
                ]
        return entries
