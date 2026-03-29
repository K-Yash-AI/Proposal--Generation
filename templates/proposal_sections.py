"""
Proposal section definitions for Fruition — matching the Fruition enterprise PDF format.

Eight AI-generated sections feeding the fixed template builder:
  1. landscape_objective   — Page 3: client background, challenges, goal
  2. solution_design       — Page 4: architecture text + embedded DIAGRAM_JSON spec
  3. phase_1_content       — Phase 1 detailed deliverables
  4. phase_2_content       — Phase 2 detailed deliverables
  5. phase_3_content       — Phase 3 detailed deliverables
  6. investment_notes      — Notes accompanying the investment table
  7. next_steps            — Numbered action items
  8. future_opportunities  — Numbered expansion opportunities
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProposalSection:
    key: str
    title: str
    prompt: str
    required: bool = True
    max_words: int = 300


PROPOSAL_SECTIONS: list[ProposalSection] = [
    # ── Page 3 ──────────────────────────────────────────────────────────────
    ProposalSection(
        key="landscape_objective",
        title="Landscape & Objective Overview",
        max_words=550,
        prompt="""You are writing the "Landscape & Objective Overview" section for a Fruition monday.com proposal.
Use ONLY facts from the client insights — never invent names, systems, numbers, or details not present.

Output the section using EXACTLY these markers on their own lines:

COMPANY_OVERVIEW:
2-3 sentences. Who the client is, what they do, their scale/size, location, and current situation.
Start with the client's company name. Be specific and factual.

CONTEXT:
2-3 sentences. Their current operational context — what systems/tools they currently use,
what manual processes they rely on, and what they are trying to build or achieve.

CURRENT_CHALLENGES:
List exactly 5-8 specific pain points from the transcript/insights. One per line in this format:
• **Challenge Title** — One sentence explaining the specific problem and its impact.

Example format only (do not copy content):
• **No centralised lead management** — Inbound enquiries are handled via email and verbal handoffs, creating lost leads and no pipeline visibility.

GOAL:
2-3 sentences starting with "The goal is to implement...". Describe what Fruition will build,
what platform it runs on, how it overlays existing systems, and the 2-3 key outcomes expected
(scalability, compliance, efficiency, audit-readiness, etc.).

RULES:
- If no transcripts are available, base content on the client name, industry, and company context provided
- Never use placeholder text like [Client Name] — use the actual name from insights
- Every challenge bullet MUST be grounded in the client's real situation
- Do not include any other text outside the 4 marked sections
""",
    ),

    # ── Page 4 ──────────────────────────────────────────────────────────────
    ProposalSection(
        key="solution_design",
        title="Solution Design",
        max_words=400,
        prompt="""You are writing the "Solution Design" section for a Fruition monday.com proposal.
Use ONLY facts from the client insights. Never invent details.

Output using EXACTLY these markers on their own lines:

OVERVIEW_TEXT:
2-3 paragraphs describing the solution architecture:
- Paragraph 1: What platform/solution is being implemented and its role (operational layer, command centre, etc.)
- Paragraph 2: The two or three core workflow components (e.g., CRM pipeline, operations management, etc.)
- Paragraph 3: How the system connects to external systems (integrations, one-way sync, etc.)

DIAGRAM_JSON:
Generate a valid JSON object (no markdown fences) that describes the workflow diagram. Use this exact structure:
{
  "sources": ["Source Type 1", "Source Type 2", "Source Type 3"],
  "pipeline_title": "Platform Name — Main Workflow Name",
  "pipeline_stages": ["Stage 1", "Stage 2", "Stage 3", "Stage 4", "Stage 5"],
  "external_system": "External System Name (if any, else empty string)",
  "external_label": "What the external system does (brief)",
  "post_stages": ["Post Feature 1", "Post Feature 2", "Post Feature 3"],
  "reporting": ["Report/Dashboard 1", "Report/Dashboard 2", "Report/Dashboard 3"],
  "caption": "End-to-end lifecycle description: Stage A → Stage B → Stage C → Stage D → Stage E"
}

Rules for DIAGRAM_JSON:
- sources: Where inputs/leads come from (website, trade shows, referrals, API feeds, etc.)
- pipeline_stages: The main sequential stages in the core workflow (4-6 stages)
- external_system: Any external system that syncs with the platform (payroll, ERP, etc.) — leave "" if none
- post_stages: Features/activities that happen AFTER the main pipeline (3-4 items)
- reporting: Dashboard and reporting outputs (3 items)
- caption: A one-line lifecycle summary using → arrows

RULES:
- The JSON must be valid — no trailing commas, proper quotes
- Stage names must be concise (max 4 words each)
- Use actual system names from the insights (monday.com, Fast Track 360, Procore, Salesforce, etc.)
- If no external system exists, use "" for external_system
""",
    ),

    # ── Phase Pages ──────────────────────────────────────────────────────────
    ProposalSection(
        key="phase_1_content",
        title="Phase 1",
        max_words=500,
        prompt="""You are writing Phase 1 content for a Fruition monday.com proposal.
Phase 1 is typically "Discovery & Requirements Workshops" (adjust the name based on insights).
Use ONLY facts from the client insights. Reference actual stakeholder names, systems, and processes.

Output using EXACTLY this format:

PHASE_NAME:
[Full phase name, e.g. "Discovery & Requirements Workshops"]

INTRO:
One sentence describing what this phase establishes and why it matters before build begins.

1. [Sub-section title relevant to client — e.g. "Stakeholder Alignment & Process Mapping"]
• **[Specific activity]** — [Brief description referencing actual stakeholders/systems/processes]
• **[Specific activity]** — [Brief description]
• **[Specific activity]** — [Brief description]
• **[Specific activity]** — [Brief description]

2. [Sub-section title — e.g. "Board Architecture & Blueprint Design"]
• **[Specific deliverable]** — [Brief description]
• **[Specific deliverable]** — [Brief description]
• **[Specific deliverable]** — [Brief description]
• **[Specific deliverable]** — [Brief description]

3. Agreed Brief & Sign-Off
• **Deliver a finalised requirements document** — with board designs, workflow diagrams, and agreed scope
• **Present the brief** to [key stakeholder name] and leadership for approval before proceeding to Phase 2

RULES:
- Use actual stakeholder names from insights (e.g., "Facilitated workshops with Kaveena and Amy")
- Reference actual systems being reviewed (e.g., "Fast Track 360 data fields", "Procore integration points")
- Reference actual compliance/regulatory frameworks if mentioned (VRQA, ISO, etc.)
- Sub-section titles must be specific to the client, not generic
""",
    ),

    ProposalSection(
        key="phase_2_content",
        title="Phase 2",
        max_words=650,
        prompt="""You are writing Phase 2 content for a Fruition monday.com proposal.
Phase 2 is typically "MVP Build" or "Core Build" (adjust name based on insights).
Use ONLY facts from the client insights. Be extremely specific about what gets built.

Output using EXACTLY this format:

PHASE_NAME:
[Full phase name, e.g. "MVP Build — Core Operational Workflows"]

INTRO:
One sentence describing what gets built in this phase.

1. [Primary Feature — e.g. "Pre-Placement Recruitment Pipeline (CRM)" or "Lead Management System"]
• **[Specific configuration]** — [What gets set up: stages, statuses, columns, forms]
• **[Specific automation]** — [What gets automated: notifications, stage changes, assignments]
• **[Specific data structure]** — [What data gets tracked: fields, categories, classifications]
• **[Specific integration/form]** — [Lead capture, forms, source attribution, etc.]
• **[Specific workflow]** — [Exception handling, re-engagement, disqualification logic]

2. [Secondary Feature — e.g. "Field Officer Caseload Management" or "Project Management Board"]
• **[Specific feature]** — [Description]
• **[Specific feature]** — [Description]
• **[Specific feature]** — [Description]
• **[Mobile/access consideration]** — [If mobile-first or offline mode is relevant]

3. [Supporting Feature — e.g. "Host Employer Management" or "Client Account Management"]
• **[Specific feature]** — [Description]
• **[Specific feature]** — [Description]
• **[Specific feature]** — [Description]
• **[Linked relationships]** — [How items connect across boards]

4. Dashboards & Reporting
• **[Role-specific dashboard]** — [What this dashboard shows, who uses it]
• **[Management dashboard]** — [KPIs, conversion rates, status views]
• **[Compliance/audit view]** — [Filterable logs, timestamped records, audit-ready format]

RULES:
- Name the actual boards, stages, automations, and integrations specifically
- Reference real workflows discussed in transcripts (compliance requirements, approval processes, etc.)
- Every bullet must describe something concrete and buildable
- Include mobile/offline considerations if mentioned in insights
""",
    ),

    ProposalSection(
        key="phase_3_content",
        title="Phase 3",
        max_words=400,
        prompt="""You are writing Phase 3 content for a Fruition monday.com proposal.
Phase 3 is typically "Testing, Training & Hypercare" or "Go-Live" (adjust based on insights).
Use ONLY facts from the client insights. Reference actual stakeholder names.

Output using EXACTLY this format:

PHASE_NAME:
[Full phase name, e.g. "Testing, Training & Hypercare"]

INTRO:
One sentence describing what this phase covers.

1. User Acceptance Testing
• **Walkthrough sessions** — with [specific stakeholder names] to validate all workflows match agreed requirements from Phase 1
• **[Specific testing area]** — [e.g., mobile testing, compliance logging, field officer workflows]
• **Refinement and adjustments** — based on stakeholder feedback before go-live

2. Training & Go-Live
• **Admin training for [name/role]** — board management, automation configuration, user permissions, ongoing maintenance
• **[End-user role] training** — [specific training focus: mobile app, daily workflows, compliance logging]
• **Go-live support** — active monitoring and rapid response during the first week of live operation

3. Hypercare Period
• **[Duration] post go-live support** — priority access to Fruition for bug fixes, workflow adjustments, and user queries
• **Handover documentation** — system guide covering board structure, automation logic, and admin procedures

RULES:
- Use actual stakeholder names and roles from insights (e.g., "Admin training for Kaveena")
- Reference the specific platform/system being trained on
- Be concrete about support commitment duration
""",
    ),

    # ── Summary Section Content ──────────────────────────────────────────────
    ProposalSection(
        key="investment_notes",
        title="Investment Notes",
        max_words=200,
        prompt="""Write 3-5 concise bullet point notes for the "Notes" section of the Investment Summary page.

These notes provide important context alongside the pricing tables. Cover points relevant to this client:
• Pricing basis (hourly rate, estimates may vary based on Phase 1 discovery)
• Licensing terms (billed directly by monday.com, not through Fruition; approximate based on current plan rates)
• Any platform upgrade options discussed (Pro vs Enterprise comparison, if relevant)
• Any time-limited promotions or offers mentioned in transcripts (AWS credits, partner discounts, etc.)
• Any third-party licensing mentioned (e.g., monday.com AE contact providing formal options)

Format as bullet points starting with "•"
Keep each note to 1-2 sentences. Be factual. Do NOT invent dollar amounts.

If no specific pricing was discussed in transcripts, include standard Fruition notes:
• All implementation pricing is based on [rate] per hour. Hours are estimated and may vary based on scope refinements during Phase 1.
• monday.com licensing is billed directly by monday.com. Pricing shown is approximate based on current plan rates.
""",
    ),

    ProposalSection(
        key="next_steps",
        title="Next Steps",
        max_words=250,
        prompt="""Write exactly 5-7 numbered next steps to move this engagement forward.

Generate steps specific to this client's situation from the insights. Consider:
1. Client review/confirmation of the proposal and phased approach
2. Licensing or platform decisions to be made (name the specific people involved if known)
3. Any technical coordination needed (AWS account, dev team, IT access, etc.)
4. Scheduling the first workshop or kickoff (include target date if mentioned in insights)
5. Documentation the client needs to prepare before Workshop 1 (Miro boards, data exports, system access, etc.)
6. What Fruition will do after sign-off (set up workspace, begin Phase 1, etc.)
7. Any time-sensitive actions (promotions expiring, launch deadlines, regulatory deadlines)

Format as numbered list ONLY — no other text:
1. [Action step — specific, owned, time-bound where possible]
2. [Action step]
...

Reference specific names, platforms, target dates, and actions from the insights where possible.
""",
    ),

    ProposalSection(
        key="future_opportunities",
        title="Future Phase Opportunities",
        max_words=250,
        prompt="""Write exactly 5-7 future phase expansion opportunities for this client.

These must be:
- Logical next steps BEYOND the current proposal scope
- Specific to this client's industry, platform, and operational context
- Each with a clear value proposition in one sentence

Format as numbered list ONLY:
1. [Opportunity Title] — [One sentence describing the specific value it delivers for this client]
2. [Opportunity Title] — [One sentence]
...

Good opportunity types to consider:
- Platform API integration with a specific named external system from the insights
- AI-powered automation for a specific workflow relevant to the client
- Advanced analytics and dashboards for a specific audience (field officers, management, compliance)
- Mobile app enhancement or offline capability
- Multi-entity or multi-site expansion (if client is growing)
- Third-party integration with specific named tools from the insights
- Compliance reporting automation specific to their regulatory framework
- Training and change management programme

RULES:
- Do NOT include anything already in the current proposal scope
- Use specific names from the insights (system names, regulation names, stakeholder roles)
- Each opportunity title should be concise (4-7 words)
""",
    ),
]

# Map section key → section object for quick lookup
SECTIONS_BY_KEY: dict[str, ProposalSection] = {s.key: s for s in PROPOSAL_SECTIONS}

# All section keys in generation order
SECTION_KEYS = [s.key for s in PROPOSAL_SECTIONS]
