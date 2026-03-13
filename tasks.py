import textwrap
from crewai import Task

def get_code_review_task(agent, repo: str, pr_number: int) -> Task:
    return Task(
        description=textwrap.dedent(f"""\
            1. Fetch pull request details and diffs for target repository: {repo} (PR #{pr_number}).
            2. Perform rigorous static analysis, scrutinizing for SOLID violations, cyclomatic complexity, and anti-patterns.
            3. Execute a security evaluation against OWASP Top 10 vectors (e.g., hardcoded secrets, injection vectors).
            4. Formulate a final deterministic review decision (APPROVE | REQUEST_CHANGES | COMMENT).
            5. Post the synthesized review summary directly to the GitHub PR.
            Ensure you adhere to an elite, 50-year veteran engineering standard. Do not hallucinate code issues.
        """),
        expected_output="A structured JSON string matching the CODE_REVIEW_PROMPT 'OUTPUT FORMAT', concluding with a GitHub broadcast.",
        agent=agent
    )

def get_ci_monitor_task(agent, repo: str, run_id: str) -> Task:
    return Task(
        description=textwrap.dedent(f"""\
            1. Ingest and parse the failed CI pipeline telemetry for {repo} (Run ID: {run_id}).
            2. Systematically isolate the root cause (e.g., Code Compilation, Infrastructure, Env Vars, Test Flakiness).
            3. If an automated fix can be applied with >0.90 heuristic confidence, generate the exact patch diff.
            4. Otherwise, generate an immediate, high-fidelity Slack escalation payload.
        """),
        expected_output="A structured JSON string summarizing the CI failure root cause, confidence metric, and proposed remediation.",
        agent=agent
    )

def get_infra_optimization_task(agent) -> Task:
    return Task(
        description=textwrap.dedent("""\
            1. Query the AWS Cost Explorer API for a rolling 30-day window to identify anomalous spend.
            2. Isolate underutilized EC2 instances, phantom EBS volumes, and unoptimized RDS instances.
            3. Generate deterministic Terraform IaC mutation proposals to close the waste gap.
            4. Prioritize recommendations by "low hanging fruit" versus "high operational risk" optimizations.
        """),
        expected_output="A comprehensive JSON financial report detailing current waste patterns and exact remediation paths.",
        agent=agent
    )

def get_incident_responder_task(agent, incident_id: str) -> Task:
    return Task(
        description=textwrap.dedent(f"""\
            1. Acknowledge the PagerDuty incident {incident_id} immediately to halt escalation policies.
            2. Analyze synchronous metrics to formulate a high-probability root cause hypothesis.
            3. Check against known SRE runbooks for safe, reversible mitigations (e.g., rolling back deployments, recycling pods).
            4. Emit resolution state or page the tier-2 human on-call engineer with a succinct context brief.
        """),
        expected_output="A JSON-formatted incident report covering start_time, mitigation notes, MTTR impact, and next steps.",
        agent=agent
    )

def get_documentation_task(agent, repo: str) -> Task:
    return Task(
        description=textwrap.dedent(f"""\
            1. Deep-scan recent PR merges in {repo} to detect missing or stale technical documentation.
            2. Auto-generate compliant docstrings for public classes/methods (Google Style or JSDoc).
            3. Synthesize OpenAPI updates for any newly detected HTTP interfaces.
            4. Output structural instructions to synchronize against Confluence or the central developer portal.
        """),
        expected_output="A structured JSON response detailing all detected documentation drift and the corresponding auto-generated content.",
        agent=agent
    )

def get_security_audit_task(agent, repo: str) -> Task:
    return Task(
        description=textwrap.dedent(f"""\
            1. Conduct a granular Software Composition Analysis (SCA) to identify transitive dependency CVEs in {repo}.
            2. Execute a Static Application Security Testing (SAST) pass looking for unencrypted storage or broken access control logic.
            3. Enforce strict Zero-Trust principles; any detected plaintext credentials must trigger an immediate P1 alert block.
            4. Compile mappings directly to SOC2 compliance requirements.
        """),
        expected_output="A stringent JSON-formatted security posture report, including CVSS scores and explicit patch instructions.",
        agent=agent
    )
