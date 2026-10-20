"""Per-posting enrichment: seniority/entry-level, experience, language, visa, skills, annual salary."""
import html
import re

from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0  # deterministic language detection

ENTRY_TITLE = re.compile(
    r"\b(junior|jr\.?|graduate|grad|entry[- ]level|trainee|intern(ship)?|apprentice|associate|"
    r"working student|werkstudent|praktikant|berufseinsteiger|absolvent|einsteiger|nachwuchs|"
    r"jeune diplômé|débutant|stagiaire|alternance|alternant|apprenti|"
    r"neolaureat[oi]|tirocin\w*|stagista|starter|afstudeer\w*|stage|"
    r"nyexaminerad|praktik\w*|nyuddannet|studentermedhjælper|nyutdannet|harjoittelija|"
    r"fresh graduate|fresher)\b", re.I)
SENIOR_TITLE = re.compile(
    r"\b(senior|sr\.?|lead|principal|staff|head|director|manager|vp|chief|architect|expert|"
    r"leiter|leitung|responsable|directeur|capo|hoofd|chef)\b|\b(ii|iii|iv)\b", re.I)
YEARS = re.compile(
    r"(\d{1,2})\s*(?:\+|plus)?\s*(?:[-–to]+\s*(\d{1,2})\s*)?(?:\+\s*)?"
    r"(?:years?|yrs?|jahre?n?|ans|anni|jaar|år|aar|vuotta|năm)"
    r"(?:['’]?\s*(?:of\s+)?(?:relevant\s+|professional\s+|work\s+|hands[- ]on\s+|proven\s+|practical\s+)?"
    r"(?:experience|erfahrung|expérience|esperienza|ervaring|erfarenhet|berufserfahrung|kinh nghiệm))?", re.I)
EXPERIENCE_CTX = re.compile(r"experience|erfahrung|expérience|esperienza|ervaring|erfarenhet|erfaring|kokemus|kinh nghiệm|exp\b", re.I)

SPONSOR_YES = re.compile(
    r"visa sponsorship (?:is )?(?:available|offered|provided)|(?:we|will|can|able to) (?:offer |provide )?sponsor|"
    r"sponsorship (?:is )?(?:available|offered|provided)|(?:offer|provide)s? (?:\w+ ){0,2}sponsorship|relocation (?:support|assistance|package)|"
    r"visa support|blue card|skilled worker visa|"
    r"employer[- ]sponsored|(?:umzugs|relocation)unterstützung|visumsunterstützung", re.I)
SPONSOR_NO = re.compile(
    r"(?:no|not|unable to|cannot|can't|won't|without) (?:\w+ ){0,3}sponsor|"
    r"(?:must|should|need to) (?:\w+ ){0,3}(?:have|hold|possess)(?: \w+){0,3} (?:the )?(?:right|authori[sz]ation|permit)(?: \w+){0,3} to work|"
    r"(?:right|eligible|authori[sz]ed|permission) to work (?:in|within)|work authori[sz]ation (?:is )?required|"
    r"(?:us|u\.s\.|uk|eu) citizen|security clearance|"
    r"arbeitserlaubnis|aufenthaltstitel|permis de travail|permesso di soggiorno|werkvergunning", re.I)

LOCAL_LANG_REQ = re.compile(
    r"(?:fluent|fluency|proficien\w*|native|business[- ]level|excellent|good|strong|working knowledge of)\s+(?:in\s+)?"
    r"(?:german|dutch|french|italian|swedish|danish|norwegian|finnish|cantonese|mandarin|chinese|vietnamese|bahasa|malay|arabic)|"
    r"(?:german|dutch|french|italian|swedish|danish|norwegian|finnish|cantonese|mandarin|vietnamese|bahasa|arabic)"
    r"\s+(?:language\s+)?(?:is\s+)?(?:required|a must|mandatory|essential|fluent|speaker)|"
    r"(?:verhandlungssicher|fließend|muttersprach\w*|sehr gute deutschkenntnisse|deutschkenntnisse)|"
    r"(?:maîtrise du français|français courant|italiano madrelingua|ottima conoscenza dell'italiano|vloeiend nederlands|"
    r"flytande svenska|flydende dansk|flytende norsk|sujuva suomen)", re.I)

# Display name -> regex. Word-bounded; short/ambiguous names are case-sensitive via inline flags.
SKILLS = {
    "SQL": r"\bsql\b", "Python": r"\bpython\b", "R": r"(?-i:\bR\b(?= ?(?:,|/|\)|programming|language|studio|and |or )))",
    "Excel": r"\bexcel\b", "Power BI": r"\bpower ?bi\b", "Tableau": r"\btableau\b", "Looker": r"\blooker\b",
    "Qlik": r"\bqlik", "SAS": r"(?-i:\bSAS\b)", "SPSS": r"\bspss\b", "Spark": r"\b(?:pyspark|apache spark|spark)\b",
    "Airflow": r"\bairflow\b", "dbt": r"(?-i:\bdbt\b)", "Kafka": r"\bkafka\b", "Snowflake": r"\bsnowflake\b",
    "Databricks": r"\bdatabricks\b", "BigQuery": r"\bbig ?query\b", "Redshift": r"\bredshift\b",
    "AWS": r"(?-i:\bAWS\b)|\bamazon web services\b", "Azure": r"\bazure\b", "GCP": r"(?-i:\bGCP\b)|\bgoogle cloud\b",
    "Docker": r"\bdocker\b", "Kubernetes": r"\bkubernetes\b|(?-i:\bk8s\b)", "Git": r"(?-i:\bgit\b|\bGit\b)",
    "TensorFlow": r"\btensorflow\b", "PyTorch": r"\bpytorch\b", "scikit-learn": r"\bscikit[- ]learn\b|\bsklearn\b",
    "Pandas": r"\bpandas\b", "NumPy": r"\bnumpy\b", "Hadoop": r"\bhadoop\b", "NoSQL": r"\bnosql\b|\bmongodb\b",
    "PostgreSQL": r"\bpostgres(?:ql)?\b", "MySQL": r"\bmysql\b", "Oracle": r"\boracle\b", "ETL": r"\betl\b|\belt\b",
    "Data Modeling": r"\bdata model+ing\b", "Statistics": r"\bstatistic\w*|\bstatistik\b|\bstatistique\w*",
    "A/B Testing": r"\ba/?b[- ]test\w*|\bexperimentation\b", "NLP": r"\bnlp\b|natural language processing",
    "LLM": r"(?-i:\bLLMs?\b)|\blarge language model", "GenAI": r"\bgen(?:erative)? ?ai\b|\bgenerative artificial",
    "RAG": r"(?-i:\bRAG\b)|retrieval[- ]augmented", "MLOps": r"\bmlops\b", "Deep Learning": r"\bdeep learning\b",
    "Computer Vision": r"\bcomputer vision\b", "Jira": r"\bjira\b", "Agile": r"\bagile\b|\bscrum\b",
    "Java": r"(?-i:\bJava\b)", "Scala": r"\bscala\b", "JavaScript": r"\bjavascript\b|(?-i:\bTypeScript\b)",
    "C++": r"c\+\+", "VBA": r"(?-i:\bVBA\b)", "SAP": r"(?-i:\bSAP\b)", "Alteryx": r"\balteryx\b",
    "Terraform": r"\bterraform\b", "CI/CD": r"\bci/?cd\b", "APIs": r"\brest(?:ful)? ?apis?\b|\bapis?\b",
}
SKILL_RES = {k: re.compile(v, re.I) for k, v in SKILLS.items()}

PERIOD_FACTOR = {"year": 1, "annual": 1, "month": 12, "week": 52, "day": 260, "hour": 2080}
# Plausible *annual* range in local currency units, wide on purpose (VND/JPY-scale pay is huge); catches unit mix-ups only.
MIN_ANNUAL = 1000


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def years_required(text):
    """Smallest years-of-experience number stated near the word 'experience'; None if absent."""
    found = []
    for m in YEARS.finditer(text):
        lo = int(m.group(1))
        window = text[max(0, m.start() - 60): m.end() + 60]
        if lo <= 15 and EXPERIENCE_CTX.search(window):
            found.append(lo)
    return min(found) if found else None


def seniority(title, years):
    """entry | mid | senior. Entry = entry keyword in title, or <=2 years asked; senior title always wins."""
    if SENIOR_TITLE.search(title or ""):
        return "senior"
    if ENTRY_TITLE.search(title or "") or (years is not None and years <= 2):
        return "entry"
    if years is not None and years >= 5:
        return "senior"
    return "mid"


def visa(text):
    if SPONSOR_YES.search(text):
        return "sponsorship_offered"
    if SPONSOR_NO.search(text):
        return "right_to_work_required"
    return "not_mentioned"


def language(text):
    try:
        return detect(text[:1500]) if len(text) > 40 else None
    except LangDetectException:
        return None


def skills(text):
    return [k for k, rx in SKILL_RES.items() if rx.search(text)]


def annual_salary(lo, hi, period):
    f = PERIOD_FACTOR.get((period or "").lower())
    if f is None or (lo is None and hi is None):
        return None, None
    lo, hi = (lo or hi) * f, (hi or lo) * f
    return (lo, hi) if hi >= MIN_ANNUAL else (None, None)


def enrich(row):
    """row: dict with title, description, salary_min/max/period. Returns the derived columns."""
    text = clean(f"{row.get('title') or ''}. {row.get('description') or ''}")
    years = years_required(text)
    lo, hi = annual_salary(row.get("salary_min"), row.get("salary_max"), row.get("salary_period"))
    lang = language(clean(row.get("description")))
    return {
        "years_required": years,
        "seniority": seniority(row.get("title"), years),
        "text_lang": lang,
        "local_lang_required": bool(LOCAL_LANG_REQ.search(text)),
        "visa": visa(text),
        "skills": skills(text),
        "annual_min": lo, "annual_max": hi,
    }
