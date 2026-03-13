import os
import json
import logging
from datetime import datetime, timedelta
from typing import Type, Optional, List

import httpx
import boto3
from github import Github, GithubException
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger("AutoOps.Tools")

# ------------------------------------------------------------------------
# 1. GITHUB PR MATCHER
# ------------------------------------------------------------------------
class GithubPRFetchSchema(BaseModel):
    repo: str = Field(..., description="The repository fullname, e.g., 'IsmailSajid/Microservices-Core'")
    pr_number: int = Field(..., description="The pull request number to fetch")

class GithubPRFetchTool(BaseTool):
    name: str = "Fetch GitHub PR Details"
    description: str = "Fetches details of a GitHub PR including title, description, and file diffs."
    args_schema: Type[BaseModel] = GithubPRFetchSchema

    def _run(self, repo: str, pr_number: int) -> str:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return "ERROR: GITHUB_TOKEN environment variable is not configured."
        
        try:
            g = Github(token)
            gh_repo = g.get_repo(repo)
            pr = gh_repo.get_pull(pr_number)
            
            # Protective bounds: don't exhaust memory on massive PRs.
            files = pr.get_files()
            diffs = []
            file_count = 0
            
            for file in files:
                if file_count > 50:
                    diffs.append("... [DIFF TRUNCATED: PR EXCEEDS 50 FILES] ...")
                    break
                # Only include patch if it exists (binary files won't have it)
                patch = file.patch if file.patch else "Binary/Large file - no patch viewable."
                diffs.append(f"File: {file.filename} | Status: {file.status}\nChanges:\n{patch}")
                file_count += 1
                
            return f"PR #{pr.number} - {pr.title}\n{pr.body}\n\n=== DIFFS ===\n" + "\n".join(diffs)
            
        except GithubException as e:
            logger.error(f"GitHub API Fault on PR {pr_number}: {e.status} {e.data}")
            return f"GitHub API Error: {e.data.get('message', str(e))}"
        except Exception as e:
            return f"Unexpected fault fetching PR details: {str(e)}"

# ------------------------------------------------------------------------
# 2. GITHUB COMMENTER
# ------------------------------------------------------------------------
class GithubCommentSchema(BaseModel):
    repo: str = Field(..., description="The repository fullname")
    pr_number: int = Field(..., description="The pull request number")
    comment: str = Field(..., description="The markdown-formatted review comment to post")

class GithubCommentTool(BaseTool):
    name: str = "Post GitHub PR Comment"
    description: str = "Posts an actionable code review comment or summary on a specific GitHub Pull Request."
    args_schema: Type[BaseModel] = GithubCommentSchema

    def _run(self, repo: str, pr_number: int, comment: str) -> str:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return "ERROR: GITHUB_TOKEN environment variable is not configured."
            
        try:
            g = Github(token)
            gh_repo = g.get_repo(repo)
            pr = gh_repo.get_pull(pr_number)
            pr.create_issue_comment(comment)
            return f"Successfully broadcasted review payload to PR #{pr_number} in {repo}."
        except Exception as e:
            return f"Failed to dispatch PR comment: {str(e)}"

# ------------------------------------------------------------------------
# 3. CI Pipeline Logs (Mock/Stub for Synthetic Testing)
# ------------------------------------------------------------------------
class FetchCILogsSchema(BaseModel):
    pipeline_id: str = Field(..., description="The CI Run ID or Pipeline ID")

class FetchCILogsTool(BaseTool):
    name: str = "Fetch CI Pipeline Logs"
    description: str = "Fetches the build or test logs for a failed CI pipeline run."
    args_schema: Type[BaseModel] = FetchCILogsSchema

    def _run(self, pipeline_id: str) -> str:
        # NOTE: In a true production environment, hook this into GitHub Actions 
        # (via `/repos/{owner}/{repo}/actions/runs/{run_id}/logs`) or Jenkins API.
        logger.info(f"Simulating pipeline log retrieval for run: {pipeline_id}")
        return """
        [ERROR] Context: Synthetic Pipeline Analysis
        [TRACE] File "/app/core/auth.py", line 42, in verify_token
        [TRACE] jwt.exceptions.DecodeError: Signature verification failed
        [INFO] Build step 'test-auth' failed with exit code 1.
        """

# ------------------------------------------------------------------------
# 4. AWS COST EXPLORER (FinOps Engine)
# ------------------------------------------------------------------------
class AWSCostExplorerSchema(BaseModel):
    pass  # No mandatory fields for 30-day generic fetch

class AWSCostExplorerTool(BaseTool):
    name: str = "AWS Cost Explorer Fetcher"
    description: str = "Fetches cloud spend and anomalies for the past 30 days."
    args_schema: Type[BaseModel] = AWSCostExplorerSchema

    def _run(self) -> str:
        if not os.getenv("AWS_ACCESS_KEY_ID"):
            return "ERROR: AWS Credentials missing. Cannot query Cost Explorer."
            
        try:
            client = boto3.client('ce', 
                                  aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                                  aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                                  region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
            
            end_date = datetime.today()
            start_date = end_date - timedelta(days=30)
            
            response = client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost']
            )
            
            costs = response.get('ResultsByTime', [])
            output = "[AWS Cost Analysis - Last 30 Days Phase]\n"
            for t in costs:
                amount = float(t['Total']['UnblendedCost']['Amount'])
                unit = t['Total']['UnblendedCost']['Unit']
                output += f"Period {t['TimePeriod']['Start']} to {t['TimePeriod']['End']}: {amount:.2f} {unit}\n"
                
            return output
        except Exception as e:
            return f"AWS Boto3 Fault: Cannot fetch Cost Metrics: {str(e)}"

# ------------------------------------------------------------------------
# 5. PAGERDUTY INCIDENT RESPONDER
# ------------------------------------------------------------------------
class PagerDutyAlertSchema(BaseModel):
    incident_id: str = Field(..., description="The unique PagerDuty incident ID")
    action: str = Field(..., description="Either 'acknowledge' or 'resolve'")
    note: Optional[str] = Field("", description="Optional runbook actions taken or context to append.")

class PagerDutyAlertTool(BaseTool):
    name: str = "PagerDuty Incident Responder"
    description: str = "Acknowledges or resolves incidents on PagerDuty and appends resolution notes."
    args_schema: Type[BaseModel] = PagerDutyAlertSchema

    def _run(self, incident_id: str, action: str, note: str = "") -> str:
        pd_api_key = os.getenv("PAGERDUTY_API_KEY")
        if not pd_api_key:
            return "ERROR: PAGERDUTY_API_KEY environment variable is missing."
            
        headers = {
            "Authorization": f"Token token={pd_api_key}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json",
            "From": "autoops_agent@autonomous.system"
        }
        
        url = f"https://api.pagerduty.com/incidents/{incident_id}"
        
        try:
            payload = {
                "incident": {
                    "type": "incident_reference",
                    "status": "acknowledged" if action.lower() == "acknowledge" else "resolved"
                }
            }
            
            # Use hitting timeout to prevent graph lockups on PagerDuty outages
            with httpx.Client(timeout=10.0) as client:
                res = client.put(url, headers=headers, json=payload)
                res.raise_for_status()
                
                if note:
                    note_url = f"{url}/notes"
                    note_payload = {"note": {"content": f"🤖 AutoOps AI: {note}"}}
                    client.post(note_url, headers=headers, json=note_payload)
                    
            return f"Successfully {action}ed PagerDuty incident {incident_id}."
        except httpx.HTTPError as e:
            return f"HTTP Fault interacting with PagerDuty API: {str(e)}"
        except Exception as e:
            return f"Fatal PagerDuty interaction fault: {str(e)}"

# ------------------------------------------------------------------------
# 6. DOCUMENTATION AND SCANNERS (Stubs)
# ------------------------------------------------------------------------
class DocumentationUpdateSchema(BaseModel):
    doc_type: str = Field(..., description="Type of document: 'api', 'readme', 'architecture'")
    content: str = Field(..., description="Markdown payload to synchronize")

class DocumentationUpdateTool(BaseTool):
    name: str = "Documentation Uploader Tool"
    description: str = "Synchronizes intelligent documentation updates to Git, Confluence, or Notion."
    args_schema: Type[BaseModel] = DocumentationUpdateSchema

    def _run(self, doc_type: str, content: str) -> str:
        logger.info(f"Simulating doc push for {doc_type}")
        return f"Documentation matrix updated successfully for sequence type: {doc_type}."

class SecurityScanSchema(BaseModel):
    repo: str = Field(..., description="Repository namespace to target for SCA/SAST scans")

class SecurityScanTool(BaseTool):
    name: str = "SAST & SCA Security Scanner"
    description: str = "Runs targeted pipeline security scans for hardcoded secrets and CVEs."
    args_schema: Type[BaseModel] = SecurityScanSchema

    def _run(self, repo: str) -> str:
        return """
        [SYNTHETIC SCAN REPORT - COMPLIANCE ENGINE]
        Findings:
        - HIGH: 0
        - MEDIUM: 1 (CVE-2024-xyz - PyJWT signature bypass vulnerability)
        - LOW: 2 (Weak RNG in test modules)
        SLA: Must patch MEDIUM within 14 days.
        """

# ------------------------------------------------------------------------
# EXPORTS
# ------------------------------------------------------------------------
github_pr_tool = GithubPRFetchTool()
github_comment_tool = GithubCommentTool()
fetch_ci_logs_tool = FetchCILogsTool()
aws_cost_tool = AWSCostExplorerTool()
pagerduty_tool = PagerDutyAlertTool()
documentation_tool = DocumentationUpdateTool()
security_scan_tool = SecurityScanTool()
