import re

# Loose on purpose: feeds without a search param return every job, role mapping happens later in enrich.
_DATA = re.compile(r"data|daten|donn[ée]es|dati|gegevens|analy|machine learning|\bml\b|\bai\b|\bki\b|\bbi\b|intelligence", re.I)


def is_relevant(title):
    return bool(_DATA.search(title or ""))
