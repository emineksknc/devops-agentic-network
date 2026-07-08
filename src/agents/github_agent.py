import re
import json
import logging
from typing import List, Dict, Any
import httpx
from src.core.base_agent import BaseAgent
from src.config.settings import settings
from src.core.llm_client import LLMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GitHubAgent")

class GitHubAgent(BaseAgent):
    def __init__(self, name: str = "GitHubAgent", model_client: Any = None):
        super().__init__(name, model_client)
        self.llm = model_client or LLMClient()
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

    async def extract_jira_ids(self, commit_messages: List[str]) -> List[str]:
        """
        🎯 HİBRİT YAKALAMA:
        1. Önce hızlı/ucuz regex ile standart formatı ("PROJKEY-123") dener.
        2. Regex hiçbir eşleşme bulamazsa (örn. "fixes #123", "closes ticket 45" gibi
           serbest formatlı mesajlar), lokal LLM'e (Ollama) semantik olarak sorar.
        Bu sayede hem hızlı/deterministik yol korunur hem de esnek formatlar kaçırılmaz.
        """
        project_key = getattr(settings, "JIRA_PROJECT_KEY", "SCRUM")
        jira_pattern = rf"({re.escape(project_key)}-\d+)"

        jira_ids: List[str] = []
        unmatched_messages: List[str] = []

        for msg in commit_messages:
            matches = re.findall(jira_pattern, msg, re.IGNORECASE)
            if matches:
                jira_ids.extend([match.upper() for match in matches])
            else:
                unmatched_messages.append(msg)

        jira_ids = list(set(jira_ids))

        # 🧠 Fallback: regex hiçbir şey yakalayamadıysa semantik analiz dene
        if not jira_ids and unmatched_messages:
            logger.info(
                "⚠️ Regex ile bilet numarası bulunamadı, LLM ile semantik analiz deneniyor..."
            )
            semantic_ids = await self._extract_jira_ids_semantic(unmatched_messages, project_key)
            jira_ids = list(set(semantic_ids))

        return jira_ids

    async def _extract_jira_ids_semantic(self, commit_messages: List[str], project_key: str) -> List[str]:
        """
        Regex'in kaçırdığı serbest formatlı commit mesajlarından (örn. "fixes #123",
        "closes ticket 45") lokal LLM ile bilet referansı çıkarmaya çalışır.
        """
        joined_messages = "\n".join(f"- {msg}" for msg in commit_messages)
        system_prompt = (
            "Sen bir DevOps asistanısın. Sadece istenen JSON formatını dönersin, "
            "başka hiçbir açıklama yazmazsın."
        )
        user_prompt = (
            f"Aşağıda bir geliştiricinin commit mesajları listelenmiştir. Proje anahtarı '{project_key}'.\n"
            "Bu mesajların içinde (varsa) bir Jira/iş bileti referansı olabilir; bu referans "
            f"'{project_key}-123' formatında açıkça yazılmamış olabilir "
            "(örn. 'fixes #123', 'closes ticket 45', 'SCRUM 123 çözüldü' gibi serbest ifadeler).\n"
            f"Eğer bir sayı bulursan, bunu '{project_key}-<sayı>' formatına çevirerek dön.\n"
            "Emin olmadığın veya bilet referansı olmayan mesajları atla, uydurma bilet numarası üretme.\n\n"
            "SADECE şu JSON formatında dön:\n"
            '{"jira_ids": ["PROJKEY-123", "PROJKEY-45"]}\n\n'
            f"Commit Mesajları:\n{joined_messages}"
        )

        try:
            llm_response = await self.llm.generate_response(system_prompt, user_prompt)
            clean_json = llm_response.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean_json)
            ids = parsed.get("jira_ids", [])
            return [str(i).upper() for i in ids if isinstance(i, (str, int))]
        except Exception as e:
            logger.warning(f"⚠️ Semantik bilet çıkarımı başarısız oldu: {e}")
            return []

    async def run(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}
        owner = context.get("owner")
        repo = context.get("repo")
        count = context.get("count", 5)
        
        if not owner or not repo:
            return {"agent": self.name, "status": "error", "message": "Missing owner or repo in context"}
            
        commits = await self.fetch_commits(owner, repo, count)
        messages = [c["message"] for c in commits]
        jira_ids = await self.extract_jira_ids(messages)
        
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