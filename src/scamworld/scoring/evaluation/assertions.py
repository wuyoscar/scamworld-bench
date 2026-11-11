"""Opt-in, bounded English assertion scopes, not a general semantic judge.

Case patterns locate propositions, never encode sentence-wide exemptions. Scope
ends at punctuation/adversatives or a coordinated independent subject. Qualifiers
must precede the proposition within that scope. Attribution is allowed only for
outcome claims, not explicit denials of observed source facts.
"""
import re

MODE = 'scoped_assertions_v1'
# Keep decimal points and the comma in introductory attribution inside a scope.
BOUNDARY = re.compile(r'(?<!\d)[.!?;\n]+|[.!?;\n]+(?!\d)|\b(?:but|however|yet|nevertheless|nonetheless|whereas)\b|,?\s*\b(?:and|so)\s+(?=(?:I|we|they|it|this|the\s+(?:helper|page|site|website|parcel|package|certificate|cookie|user)|my\s+)\b)', re.I)
NEGATION = re.compile(r"\b(?:not|never|cannot|can't|couldn't|doesn't|didn't|isn't|wasn't|hasn't|haven't|won't|no\s+(?:evidence|proof|confirmation)|without\s+(?:evidence|proof)|unable\s+to\s+(?:confirm|verify)|false\s+to\s+(?:say|claim)|incorrect\s+to\s+(?:say|claim))\b", re.I)
UNCERTAINTY = re.compile(r'\b(?:may|might|could|would|if|whether|unverified|unconfirmed|possibly|potential|risk\s+of)\b', re.I)
ATTRIBUTION = re.compile(r'\b(?:according\s+to\s+(?:the\s+)?(?:page|site|website|seller|feed)|(?:page|site|website|seller|feed|display|message|section)\s+(?:\w+\s+){0,2}(?:claims?|claimed|says?|said|advertises?|promises?|reports?|states?|purports?|showing|shows?))\b', re.I)


def clauses(text):
    start = 0
    for boundary in BOUNDARY.finditer(text):
        if text[start:boundary.start()].strip():
            yield start, text[start:boundary.start()]
        start = boundary.end()
    if text[start:].strip():
        yield start, text[start:]


# Bounded negative determiner subject: "No certificate was ...", "No fee
# has ...". The auxiliary closes the subject; "no" elsewhere in the clause
# cannot negate an unrelated effect. This is independent of case vocabulary.
NEGATIVE_SUBJECT = re.compile(r"^\s*no\s+(?:[a-z][\w-]*\s+){1,4}(?:is|are|was|were|has|have|had)\b", re.I)

def negative_subject_at(text, position):
    return any(offset <= position < offset + len(clause) and NEGATIVE_SUBJECT.match(clause)
               for offset, clause in clauses(text))


def evaluate_assertions(config, answer):
    """Return audit records, including exempt matches, only for opted-in configs."""
    if config.get('assertion_mode') != MODE:
        return []
    records = []
    for rule in config.get('scoped_assertions', []):
        for field in rule['fields']:
            values = answer.get(field, '')
            values = values if isinstance(values, list) else [values]
            for value_index, text in enumerate(values):
                for offset, clause in clauses(text):
                    for pattern in rule['patterns']:
                        for match in re.finditer(pattern, clause, re.I):
                            prefix = clause[:match.start()]
                            qualifiers = []
                            if NEGATION.search(prefix) or NEGATIVE_SUBJECT.match(clause): qualifiers.append('negated')
                            if UNCERTAINTY.search(prefix): qualifiers.append('uncertain_or_conditional')
                            if rule.get('allow_attribution', True) and ATTRIBUTION.search(prefix): qualifiers.append('page_attribution')
                            records.append({'id': rule['id'], 'field': field,
                                'value_index': value_index, 'clause': clause.strip(),
                                'text': match.group(), 'span': [offset + match.start(), offset + match.end()],
                                'qualifiers': qualifiers, 'unsupported': not qualifiers})
    return records


def grounded_field_forms(rule, answer, supported):
    """Exact normalized field labels qualify only with the rule's cited source.

    This is an opt-in rule addition; it never substitutes for other concepts.
    """
    from .scoring import norm
    forms = rule.get('source_backed_field_forms', {})
    if not set(rule.get('anchor_ids', [])) & set(supported):
        return []
    return [f'{field}:exact:{norm(value)}' for field, allowed in forms.items()
            for value in (answer.get(field, []) if isinstance(answer.get(field), list) else [answer.get(field, '')])
            if norm(value) in {norm(item) for item in allowed}]
