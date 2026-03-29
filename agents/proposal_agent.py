"""
Proposal Generation Agent — optimised direct pipeline.

Architecture (no agentic loop):
  1. Fetch Fireflies transcripts  (Fireflies API)
  2. Analyse transcripts          (single Claude call → structured insights JSON)
  3. Extract & compute pricing    (pure Python, no hallucination)
  4. Generate all sections        (parallel Claude calls via ThreadPoolExecutor)
  5. Build DOCX                   (FixedTemplateBuilder)
  6. Upload to Drive              (optional)
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any, Optional

from config import settings
from services.claude_service import ClaudeService
from services.fireflies_service import FirefliesService, Transcript
from services.google_docs_service import GoogleDocsService
from templates.proposal_sections import PROPOSAL_SECTIONS, SECTIONS_BY_KEY
from utils.fixed_template_builder import FixedTemplateBuilder
from utils.logger import log

# ── System prompt for section generation ─────────────────────────────────────

_SECTION_SYSTEM = (
    "You are a senior proposal writer for {company_name}, a certified monday.com "
    "Platinum Partner. Write enterprise-quality proposal content that is:\n"
    "- Specific: grounded in the client's real situation from the insights provided\n"
    "- Professional: confident, client-centric tone without hyperbole\n"
    "- Accurate: never invent facts, names, numbers, or systems not in the insights\n"
    "- Formatted: follow the output structure markers EXACTLY as instructed\n"
    "Write only the requested section — no preamble, no meta-commentary."
)

# ── Analysis prompt ───────────────────────────────────────────────────────────

_ANALYSIS_PROMPT = """Analyse the following meeting transcripts and extract structured insights.

Return a single valid JSON object (no markdown, no explanation) with exactly these fields:

{{
  "client_name": "string — contact person name",
  "client_company": "string — company name",
  "industry": "string — industry/sector",
  "pain_points": ["list of specific pain points as strings"],
  "goals": ["list of stated goals and success criteria"],
  "requirements": ["list of specific functional requirements"],
  "key_contacts": [
    {{"name": "string", "role": "string", "organisation": "string"}}
  ],
  "discussed_solutions": ["list of solutions or platforms discussed"],
  "next_actions": ["list of agreed next steps from the meetings"],
  "timeline_notes": "string — any deadlines, launch dates, or urgency mentioned",
  "budget_notes": "string — any pricing, budget ranges, or financial constraints mentioned",
  "integrations": ["list of external systems to integrate with"],
  "out_of_scope": ["list of things explicitly excluded from scope"],
  "pricing": {{
    "hourly_rate": 250,
    "currency": "AUD",
    "phase_1_name": "string — e.g. Discovery & Requirements Workshops",
    "phase_1_hours": 10,
    "phase_1_weeks": "string — e.g. 1-2",
    "phase_1_lead": "string — e.g. Fruition Team",
    "phase_2_name": "string — e.g. MVP Build",
    "phase_2_hours": 20,
    "phase_2_weeks": "string — e.g. 2-5",
    "phase_2_lead": "string — e.g. Fruition Team",
    "phase_3_name": "string — e.g. Testing, Training & Go-Live",
    "phase_3_hours": 5,
    "phase_3_weeks": "string — e.g. 5-6",
    "phase_3_lead": "string — e.g. Fruition Team",
    "total_weeks": 6,
    "initial_users": 5,
    "monday_products": ["list of monday.com products needed: CRM, Work Management, Service, Campaigns"],
    "licensing_year1_description": "string — brief note about Year 1 licensing if discussed, else ''",
    "licensing_year2_description": "string — brief note about Year 2+ licensing if discussed, else ''",
    "managed_services_monthly": 500
  }}
}}

Rules:
- For pricing.phase_X_hours: estimate based on project scope if not explicitly stated. Typical ranges:
  Phase 1 Discovery: 8-15 hrs, Phase 2 Build: 15-40 hrs, Phase 3 Training/Go-Live: 5-10 hrs
- hourly_rate is always 250 AUD unless transcripts explicitly state otherwise
- initial_users: extract from transcripts, default to 5 if not mentioned
- monday_products: infer from what's being implemented (CRM boards → "CRM", project boards → "Work Management")
- If a field cannot be determined from transcripts, use sensible defaults — never leave arrays empty

TRANSCRIPTS:
{transcripts_text}
"""


class ProposalAgent:
    """End-to-end proposal generation — direct pipeline, parallel section generation."""

    def __init__(
        self,
        template_doc_id: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> None:
        self._fireflies = FirefliesService()
        self._google_docs = GoogleDocsService()
        self._claude = ClaudeService()

        self._template_doc_id = template_doc_id or settings.google_template_doc_id
        self._output_dir = Path(output_dir or settings.output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    # ── Public entry point ────────────────────────────────────────────────────

    def run(
        self,
        client_name: str,
        client_email: Optional[str] = None,
        client_company: Optional[str] = None,
        prepared_by: Optional[str] = None,
        transcripts_limit: int = 5,
        use_fixed_format: bool = True,   # kept for API compat, always True now
        upload_to_drive: bool = False,
    ) -> dict[str, str]:
        """
        Generate a proposal for the given client.
        Returns dict with 'local_path' and optionally 'drive_link'.
        """
        log.info(
            f"[step]Starting proposal generation for:[/step] "
            f"{client_name!r} ({client_company or 'unknown company'})"
        )

        # ── Step 1: Fetch transcripts ─────────────────────────────────────────
        log.info("[step]Fetching Fireflies transcripts...[/step]")
        transcripts = self._fireflies.get_transcripts_for_client(
            client_name=client_name,
            client_email=client_email,
            limit=transcripts_limit,
        )

        # ── Step 2: Analyse transcripts ───────────────────────────────────────
        log.info("[step]Analysing transcripts with Claude...[/step]")
        insights = self._analyse_transcripts(
            transcripts, client_name, client_company or client_name
        )

        # ── Step 3: Compute pricing from insights ─────────────────────────────
        pricing = self._compute_pricing(insights)

        # ── Step 4: Build metadata ────────────────────────────────────────────
        safe_company = re.sub(r"[^\w\s-]", "", client_company or client_name).strip()
        safe_company = re.sub(r"\s+", "_", safe_company)
        date_str = date.today().strftime("%Y%m%d")
        filename = f"Proposal_{safe_company}_{date_str}.docx"
        output_path = str(self._output_dir / filename)

        metadata: dict[str, Any] = {
            "client_name": client_name,
            "client_company": client_company or client_name,
            "client_email": client_email or "",
            "proposal_date": date.today().strftime("%B %dth, %Y"),
            "prepared_by": prepared_by or settings.company_name,
            "company_name": settings.company_name,
            "company_tagline": settings.company_tagline,
            "company_email": settings.company_email,
            "company_phone": settings.company_phone,
            "company_website": settings.company_website,
            "key_contacts": insights.get("key_contacts", []),
            "pricing": pricing,
        }

        # ── Step 5: Generate sections in parallel ─────────────────────────────
        log.info("[step]Generating proposal sections in parallel...[/step]")
        sections = self._generate_sections_parallel(insights, metadata)

        # ── Step 6: Build DOCX ────────────────────────────────────────────────
        log.info("[step]Building proposal document...[/step]")
        builder = FixedTemplateBuilder()
        final_path = builder.build(sections, metadata, output_path)

        result: dict[str, str] = {"local_path": final_path}

        # ── Step 7: Upload to Drive (optional) ───────────────────────────────
        if upload_to_drive:
            drive_link = self._upload_to_google_drive(final_path)
            if drive_link:
                result["drive_link"] = drive_link
                log.info(f"[success]Shared:[/success] {drive_link}")

        log.info(f"[success]Proposal complete:[/success] {final_path}")
        return result

    # ── Transcript analysis ───────────────────────────────────────────────────

    def _analyse_transcripts(
        self,
        transcripts: list[Transcript],
        client_name: str,
        client_company: str,
    ) -> dict[str, Any]:
        """Single Claude call → structured insights JSON."""
        if not transcripts:
            log.warning(
                "No transcripts found — generating proposal from client name/company only."
            )
            return self._default_insights(client_name, client_company)

        # Build text dump (capped per transcript to control token usage)
        text_dump = ""
        for t in transcripts:
            text_dump += f"\n\n{'='*60}\n"
            text_dump += f"MEETING: {t.title} — {t.date_str}\n"
            text_dump += f"PARTICIPANTS: {', '.join(t.participants)}\n"
            text_dump += f"OVERVIEW: {t.summary.overview}\n"
            if t.summary.shorthand_bullet:
                text_dump += "HIGHLIGHTS:\n" + "\n".join(
                    f"  • {h}" for h in t.summary.shorthand_bullet
                )
            if t.summary.action_items:
                text_dump += "\nACTION ITEMS:\n" + "\n".join(
                    f"  • {a}" for a in t.summary.action_items
                )
            text_dump += f"\n\nTRANSCRIPT EXCERPT:\n{t.full_text[:5000]}"

        analysis_prompt = _ANALYSIS_PROMPT.format(transcripts_text=text_dump)

        raw = self._claude.complete(
            system=(
                "You are a business analyst. Extract structured insights from meeting transcripts. "
                "Respond with valid JSON only — no markdown code fences, no explanation."
            ),
            user=analysis_prompt,
            max_tokens=3000,
        )

        # Strip markdown fences if Claude added them anyway
        raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`")

        try:
            insights = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("Failed to parse insights JSON — using defaults.")
            insights = self._default_insights(client_name, client_company)

        # Ensure required keys exist
        insights.setdefault("client_name", client_name)
        insights.setdefault("client_company", client_company)
        insights.setdefault("pricing", {})
        insights.setdefault("key_contacts", [])

        return insights

    def _default_insights(self, client_name: str, client_company: str) -> dict[str, Any]:
        """Fallback insights when no transcripts are available."""
        return {
            "client_name": client_name,
            "client_company": client_company,
            "industry": "business",
            "pain_points": [
                "Manual processes limiting operational efficiency",
                "Lack of centralised visibility across teams",
                "No structured workflow for tracking client/project lifecycle",
                "Difficulty scaling existing systems to meet growth demands",
                "Limited reporting and dashboard capability for management oversight",
            ],
            "goals": [
                "Implement a centralised operational platform",
                "Automate key workflows to reduce manual effort",
                "Improve visibility and reporting for leadership",
            ],
            "requirements": [],
            "key_contacts": [],
            "discussed_solutions": ["monday.com"],
            "next_actions": [],
            "timeline_notes": "",
            "budget_notes": "",
            "integrations": [],
            "out_of_scope": [],
            "pricing": {},
        }

    # ── Pricing computation ───────────────────────────────────────────────────

    def _compute_pricing(self, insights: dict[str, Any]) -> dict[str, Any]:
        """
        Compute the full pricing breakdown from insights.
        All dollar amounts are computed in Python — never hallucinated.
        """
        p = insights.get("pricing", {})

        hourly_rate = int(p.get("hourly_rate", 250))
        currency = p.get("currency", "AUD")

        ph1_hours = int(p.get("phase_1_hours", 10))
        ph2_hours = int(p.get("phase_2_hours", 20))
        ph3_hours = int(p.get("phase_3_hours", 5))
        total_hours = ph1_hours + ph2_hours + ph3_hours

        ph1_cost = ph1_hours * hourly_rate
        ph2_cost = ph2_hours * hourly_rate
        ph3_cost = ph3_hours * hourly_rate
        total_impl_cost = ph1_cost + ph2_cost + ph3_cost

        # monday.com licensing — $600/user/year per product (approx)
        users = int(p.get("initial_users", 5))
        products = p.get("monday_products", ["Work Management"])
        license_per_user = 600
        n_products = max(1, len(products))
        licensing_year1 = users * license_per_user * n_products
        licensing_year2 = licensing_year1  # ongoing

        def fmt(amount: int) -> str:
            return f"~${amount:,}"

        return {
            "hourly_rate": hourly_rate,
            "currency": currency,
            # Phase 1
            "phase_1_name": p.get("phase_1_name", "Discovery & Requirements Workshops"),
            "phase_1_hours": ph1_hours,
            "phase_1_weeks": p.get("phase_1_weeks", "1–2"),
            "phase_1_lead": p.get("phase_1_lead", "Fruition Team"),
            "phase_1_cost": ph1_cost,
            "phase_1_cost_fmt": f"${ph1_cost:,}",
            "phase_1_deliverables": "Process mapping, board architecture blueprint, agreed brief",
            # Phase 2
            "phase_2_name": p.get("phase_2_name", "Core Build & Configuration"),
            "phase_2_hours": ph2_hours,
            "phase_2_weeks": p.get("phase_2_weeks", "2–5"),
            "phase_2_lead": p.get("phase_2_lead", "Fruition Team"),
            "phase_2_cost": ph2_cost,
            "phase_2_cost_fmt": f"${ph2_cost:,}",
            "phase_2_deliverables": "Core workflows, automations, integrations, dashboards",
            # Phase 3
            "phase_3_name": p.get("phase_3_name", "Testing, Training & Go-Live"),
            "phase_3_hours": ph3_hours,
            "phase_3_weeks": p.get("phase_3_weeks", "5–6"),
            "phase_3_lead": p.get("phase_3_lead", "Fruition Team"),
            "phase_3_cost": ph3_cost,
            "phase_3_cost_fmt": f"${ph3_cost:,}",
            "phase_3_deliverables": "UAT, training sessions, go-live support, handover documentation",
            # Totals
            "total_hours": total_hours,
            "total_weeks": int(p.get("total_weeks", 6)),
            "total_impl_cost": total_impl_cost,
            "total_impl_cost_fmt": f"${total_impl_cost:,}",
            # Licensing
            "initial_users": users,
            "monday_products": products,
            "licensing_year1": licensing_year1,
            "licensing_year1_fmt": fmt(licensing_year1),
            "licensing_year1_description": p.get("licensing_year1_description", ""),
            "licensing_year2": licensing_year2,
            "licensing_year2_fmt": fmt(licensing_year2),
            "licensing_year2_description": p.get("licensing_year2_description", ""),
            "managed_services_monthly": int(p.get("managed_services_monthly", 500)),
            "managed_services_monthly_fmt": f"From ${p.get('managed_services_monthly', 500):,}",
            # Grand total year 1
            "total_year1": total_impl_cost + licensing_year1,
            "total_year1_fmt": fmt(total_impl_cost + licensing_year1),
        }

    # ── Parallel section generation ───────────────────────────────────────────

    def _generate_sections_parallel(
        self,
        insights: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, str]:
        """Generate all sections concurrently — ~5x faster than sequential."""
        insights_text = json.dumps(insights, indent=2)
        system_prompt = _SECTION_SYSTEM.format(company_name=settings.company_name)

        def _gen(section_def) -> tuple[str, str]:
            prompt = (
                f"CLIENT INSIGHTS:\n{insights_text}\n\n"
                f"SECTION INSTRUCTIONS:\n{section_def.prompt}\n\n"
                f"Generate the section content now. "
                f"Follow the output structure EXACTLY as specified above. "
                f"Maximum {section_def.max_words} words."
            )
            content = self._claude.complete(
                system=system_prompt,
                user=prompt,
                max_tokens=section_def.max_words * 7,
                temperature=0.2,
            )
            return section_def.key, content.strip()

        sections: dict[str, str] = {}
        max_workers = min(5, len(PROPOSAL_SECTIONS))

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_gen, sec): sec for sec in PROPOSAL_SECTIONS}
            for future in as_completed(futures):
                sec = futures[future]
                try:
                    key, content = future.result()
                    sections[key] = content
                    log.info(f"[success]Section ready:[/success] {sec.title}")
                except Exception as exc:
                    log.warning(f"Section '{sec.key}' failed: {exc} — using empty.")
                    sections[sec.key] = ""

        return sections

    # ── Drive upload ──────────────────────────────────────────────────────────

    def _upload_to_google_drive(self, file_path: str) -> str:
        try:
            _doc_id, share_link = self._google_docs.upload_docx_to_drive(
                file_path, folder_id=None, make_public=True
            )
            return share_link
        except Exception as exc:
            log.warning(f"Drive upload failed: {exc}")
            return ""
