import re
import logging
from typing import List, Dict, Any
import httpx
from src.core.base_agent import BaseAgent
from src.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GitHubAgent")

class GitHubAgent(BaseAgent):
    def __init__(self, name: str = "GitHubAgent", model_client: Any = None):
        super().__init__(name, model_client)
        self.register_tool("fetch_commits", self.fetch_commits)
        self.register_tool("fetch_commit_diff", self.fetch_commit_diff)
        self.register_tool("extract_jira_ids", self.extract_jira_ids)

    async def fetch_commits(self, repo_owner: str, repo_name: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        GitHub REST API'sine canlı token ile asenkron HTTP isteği atar ve commit listesini döner.
        """
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "DevOps-Agentic-Network"
        }
        
        if settings.GITHUB_TOKEN and settings.GITHUB_TOKEN != "mock_github_token":
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        try:
            logger.info(f"📡 GitHub Canlı API'sine istek atılıyor: {repo_owner}/{repo_name}")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, params={"per_page": count})
                
                if response.status_code == 200:
                    commits_data = response.json()
                    parsed_commits = []
                    for c in commits_data:
                        parsed_commits.append({
                            "sha": c.get("sha", ""), # Tam SHA'yı tutuyoruz ki detay sorgusunda patlamayalım
                            "short_sha": c.get("sha", "")[:7],
                            "message": c.get("commit", {}).get("message", ""),
                            "author": c.get("commit", {}).get("author", {}).get("name", "Unknown")
                        })
                    return parsed_commits
                else:
                    logger.error(f"❌ GitHub API Hatası ({response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"❌ GitHub API Bağlantı Hatası: {str(e)}")
        
        return []

    async def fetch_commit_diff(self, repo_owner: str, repo_name: str, sha: str) -> str:
        """
        🎯 YENİ METOD: Belirli bir commit SHA'sına giderek değişen kodların (patch) özetini getirir.
        """
        if not sha:
            return ""
            
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits/{sha}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "DevOps-Agentic-Network"
        }
        
        if settings.GITHUB_TOKEN and settings.GITHUB_TOKEN != "mock_github_token":
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        try:
            logger.info(f"📡 GitHub Diff API'sine istek atılıyor: {sha[:7]}")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    commit_detail = response.json()
                    files = commit_detail.get("files", [])
                    
                    diff_logs = []
                    for f in files:
                        filename = f.get("filename")
                        # Kod bloğundaki ham satır değişikliklerini (patch) alıyoruz
                        patch = f.get("patch", "Büyük değişiklik veya binary dosya, diff üretilemedi.")
                        diff_logs.append(f"--- Dosya: {filename} ---\n{patch}\n")
                        
                    return "\n".join(diff_logs) if diff_logs else "Kod değişikliği bulunamadı."
                else:
                    logger.error(f"❌ GitHub Diff API Hatası ({response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"❌ GitHub Diff API Bağlantı Hatası: {str(e)}")
            
        return ""

    def extract_jira_ids(self, commit_messages: List[str]) -> List[str]:
        jira_pattern = r"(SCRUM-\d+)"
        jira_ids = []
        for msg in commit_messages:
            matches = re.findall(jira_pattern, msg, re.IGNORECASE)
            if matches:
                jira_ids.extend([match.upper() for match in matches])
        return list(set(jira_ids))

    async def run(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}
        owner = context.get("owner")
        repo = context.get("repo")
        count = context.get("count", 5)
        
        if not owner or not repo:
            return {"agent": self.name, "status": "error", "message": "Missing owner or repo in context"}
            
        commits = await self.fetch_commits(owner, repo, count)
        messages = [c["message"] for c in commits]
        jira_ids = self.extract_jira_ids(messages)
        
        # 🎯 En son commit'in kod diff'ini (değişikliklerini) çekiyoruz
        code_changes = ""
        if commits:
            latest_sha = commits[0].get("sha") # İlk eleman en güncel commit'tir
            code_changes = await self.fetch_commit_diff(owner, repo, latest_sha)
        
        return {
            "agent": self.name,
            "status": "success",
            "extracted_data": {
                "owner": owner,
                "repo": repo,
                "commits_analyzed": len(commits),
                "jira_ids_found": jira_ids,
                "raw_commits": commits,
                "code_changes": code_changes # 🎯 Şef Ajan'a (Orchestrator) paslanan sıcak kod verisi
            }
        }

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return []