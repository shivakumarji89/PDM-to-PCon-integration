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
the ``SIFImport.camelCase`` port. Product-specific suffix special-cases
(RYMPSH/RY3VNN/RYT/RY2U hardcoded option ids) are not yet ported.
"""
from __future__ import annotations

from dataclasses import dataclass, field

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

    # -- generation --------------------------------------------------------

    def generate(
        self,
        prefix: str = "",
        property_exclusions: str = "",
        property_substitutions: str = "",
        snapshot: Snapshot | None = None,
    ) -> VarCondResult:
        """Build super-product VARCOND rules offline, matching PDM exactly.

        Parameters mirror PDM's ``SuperProductVarCondRelation`` form:

        * ``prefix``                 - pCon property-class prefix (usually empty).
        * ``property_exclusions``    - string; a property is dropped when its
          parsed name is a substring of this text (PDM ``IndexOf`` semantics).
        * ``property_substitutions`` - comma list of ``old=new`` renames.
        """
        snapshot = snapshot if snapshot is not None else self.context.active_snapshot
        result = VarCondResult()
        if snapshot is None:
            result.warnings.append("No active snapshot.")
            return result

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
