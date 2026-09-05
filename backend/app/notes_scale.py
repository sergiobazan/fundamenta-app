"""Evidence from a document-wide presentation policy, with dated table anchors."""

import re

from app.document_scale import explicit_scale, number_tokens
from app.notes import _normalized

ALIASES = {
    "profit_before_tax": {"utilidad antes de impuesto a la renta"},
    "income_tax_expense": {"total impuesto a la renta"},
    "cash_and_cash_equivalents": {"efectivo y equivalentes del efectivo"},
    "closing_cash": {"efectivo y equivalentes del efectivo"},
}


def clean_label(text):
    text = _normalized(text)
    text = re.sub(r"\([^)]*\)", "", text)
    return " ".join(re.findall(r"[a-z]+", text))


def presentation_policy(pages, currency):
    policies = []
    for index, page in enumerate(pages):
        text = " ".join(_normalized(page).split())
        if not re.search(r"bases de preparacion|moneda de presentacion", text):
            continue
        for match in re.finditer(
            r"(?:los |estos )estados financieros(?: consolidados| separados| individuales)?"
            r" se (?:presentan|expresan)[^.]{0,400}\.",
            text,
        ):
            statement = match.group()
            scale = explicit_scale(statement, currency)
            if scale is None:
                return None
            # Only the standard non-specific exception is accepted. Concrete
            # exceptions need scoped interpretation and remain unverified.
            exception = re.search(r"excepto[^.]*|salvo[^.]*", statement)
            if exception and exception.group() not in {
                "excepto donde se indique de otro modo",
                "excepto donde se indique lo contrario",
                "salvo que se indique lo contrario",
            }:
                return None
            policies.append(
                {
                    "scale": scale,
                    "page": index + 1,
                    "declaration": statement,
                    "exception": exception.group() if exception else None,
                }
            )
    if not policies or len({p["scale"] for p in policies}) != 1:
        return None
    return policies[0]


def table_anchors(pages, facts, year, currency, scale):
    matches = {}
    for page_index, page in enumerate(pages):
        lines = page.splitlines()
        years = None
        table_scale = None
        heading = ""
        first_table = False
        seen_table = False
        for index, line in enumerate(lines):
            title = re.match(r"^\s*\d{1,2}\.\s+(.+)", line)
            if title:
                heading = clean_label(title.group(1))
                first_table = True
                seen_table = False
                years = None
                table_scale = None
            # Only unambiguous tables with year-only headers are supported.
            if re.fullmatch(r"\s*20\d{2}(?:\s+20\d{2}){1,2}\s*", line):
                if seen_table:
                    first_table = False
                seen_table = True
                years = [int(x) for x in re.findall(r"20\d{2}", line)]
                table_scale = None
                continue
            if years and explicit_scale(line, currency):
                table_scale = explicit_scale(line, currency)
                continue
            if years and re.search(r"s/|us\s*\$|miles|millones|unidades", _normalized(line)):
                # A mixed or foreign currency/unit header is not evidence for
                # this table, even if a previous header was compatible.
                years = None
                table_scale = None
                continue
            if not years or len(set(years)) != len(years) or table_scale != scale:
                continue
            if year not in years or year - 1 not in years:
                continue
            values = number_tokens(line)
            if len(values) != len(years):
                # Repeated units or narrative paragraphs end the table; they
                # must not inherit an earlier table's unit declaration.
                if len(line.strip()) > 100 or re.match(r"^\s*\([a-z]\)", line):
                    years = None
                continue
            label = clean_label(line)
            for fact in facts:
                if fact.get("value_kind", "monetary") != "monetary":
                    continue
                if not fact["current_amount"] or fact["comparative_amount"] is None:
                    continue
                accepted = {clean_label(fact["original_label"])}
                accepted |= ALIASES.get(fact.get("normalized_concept"), set())
                # A label-free total is accepted only under an exact note title
                # and separator, in the note's first table.
                total = (
                    not label
                    and first_table
                    and heading in accepted
                    and index > 0
                    and "___" in lines[index - 1]
                )
                if label not in accepted and not total:
                    continue
                if [values[years.index(year)], values[years.index(year - 1)]] != [
                    fact["current_amount"],
                    fact["comparative_amount"],
                ]:
                    continue
                key = (fact["filing_id"], fact["account_code"])
                matches[key] = {
                    "filing_id": fact["filing_id"],
                    "account_code": fact["account_code"],
                    "page": page_index + 1,
                    "line": line.strip(),
                    "label": heading if total else label,
                    "years": years,
                    "current": str(fact["current_amount"]),
                    "comparative": str(fact["comparative_amount"]),
                }
            if not label:
                first_table = False
    return list(matches.values())


def verify_notes_policy(pages, filings, facts_by_id):
    if (
        not filings
        or len(
            {(f["currency_code"], f["fiscal_year"], f["scope"], f["period_code"]) for f in filings}
        )
        != 1
    ):
        return {}
    first = filings[0]
    policy = presentation_policy(pages, first["currency_code"])
    if policy is None:
        return {}
    facts = [fact for filing in filings for fact in facts_by_id[filing["id"]]]
    matches = table_anchors(
        pages, facts, first["fiscal_year"], first["currency_code"], policy["scale"]
    )
    # >=3 distinct economic amounts, including accounts from >=2 statements.
    # Each verified filing must have its own anchor. Never assign another
    # statement's scale to a filing that cannot be reconciled to the PDF.
    if (
        len({(m["label"], m["current"], m["comparative"]) for m in matches}) < 3
        or len({m["filing_id"] for m in matches}) < 2
    ):
        return {}
    return {
        filing["id"]: {
            **policy,
            "method": "notes_presentation_policy",
            "matches": matches,
            "filing_matches": [m for m in matches if m["filing_id"] == filing["id"]],
        }
        for filing in filings
        if any(m["filing_id"] == filing["id"] for m in matches)
    }
