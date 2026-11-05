# Shared fabric: explicit second-fabric choices are preserved

`shared_fabric` (opt-in, default off; `OcdArticleGenerator.generate(shared_fabric=True)`) ties fabric positions that
offer the same fabric choice so the independent product is not enumerated.

## Rule
1. Positions are tied when their type properties offer the same type codes and their colour properties share a colour
   code (`fabric.analyse_shared_fabric`; no property, article or SKU is named).
2. A follower is **not** tied when it carries a precondition (own or class level) that the primary does not carry,
   e.g. `Number_Of_Fabrics IN ('2')`. The data then deliberately offers a second fabric, so it stays independent.
3. Any extra follower precondition bypasses the tie: it cannot be distinguished from an unrelated visibility rule,
   and valid configurations are never removed on a guess.
4. Positions gated by the same preconditions are still tied.

Diagnostics: `GenerationOutcome.fabric_notes` lists `shared fabric: ...` for applied ties and
`shared fabric not applied: ... (reason)` for skipped ones.

## NOHAN1 (range `hatch`, EUR, 2026-11-04), PEP-style full generation
Seat fabric type/colour carry `(SPECIFIED Number_Of_Fabrics) AND (Number_Of_Fabrics IN ('2'))`.

| Mode | Configurations | SKUs | Seconds* | Ordered digest | Sorted digest |
|---|---|---|---|---|---|
| independent (`shared_fabric=False`) | 246,960 | 246,960 | 1,296 | `7d9cb21a23ce0f7a` | `dd1927fb6cccd770` |
| previous shared (tied everywhere) | 10,080 | 10,080 | 36.7 | `ce71f711ef6aca9d` | `c74e4261503da441` |
| refined shared | 246,960 | 246,960 | 1,068 | `7d9cb21a23ce0f7a` | `dd1927fb6cccd770` |

\*Wall time with other heavy jobs running concurrently; not a clean timing. Price digest (`final|price`, truncated)
is `b368c603a255ed94` for independent and refined.

The previous behaviour removed 236,880 valid configurations (the whole `Number_Of_Fabrics = 2` different-fabric
branch). The refined rule keeps them: NOHAN1 now has no eligible tie, so its output equals the independent baseline.
Reduction for eligible articles is covered by `tests/ocd_engine/test_ocd_shared_fabric.py`.
