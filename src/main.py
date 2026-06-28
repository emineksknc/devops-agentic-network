import asyncio
import json
from src.agents.github_agent import GitHubAgent
from src.agents.jira_agent import JiraAgent
from src.config.settings import settings

async def main():
    print("==================================================")
    print("🚀 DevOps Agentic Network (DAN) - DİNAMİK AKIŞ TESTİ")
    print("==================================================\n")
    
    github_agent = GitHubAgent()
    jira_agent = JiraAgent()
    
    # Bilgiler artık kuruşu kuruşuna .env dosyasından otomatik çekiliyor!
    github_context = {
        "owner": settings.GITHUB_OWNER, 
        "repo": settings.GITHUB_REPO, 
        "count": 3
    }
    
    print(f"🔹 [1/2] {github_agent.name}, env'den alınan '{settings.GITHUB_OWNER}/{settings.GITHUB_REPO}' reposunu tarıyor...")
    github_result = await github_agent.run("Scan real commits", context=github_context)
    
    extracted_ids = github_result["extracted_data"]["jira_ids_found"]
    print(f"🎯 Commit geçmişinden otomatik ayıklanan biletler: {extracted_ids}\n")
    
    if not extracted_ids:
        print("⚠️ Son commit'lerde 'SCRUM-X' pattern'ı bulunamadı veya repo erişim hatası oluştu. Akış durduruldu.")
        return

    print(f"🔹 [2/2] {jira_agent.name} canlı Jira biletlerini güncelliyor...")
    jira_context = {
        "jira_ids": extracted_ids,
        "action": "both"
    }
    jira_result = await jira_agent.run("Update live tickets", context=jira_context)
    
    print("\n✅ Tam Otomatik Akış Başarıyla Tamamlandı.")
    print("==================================================")
    print(json.dumps(jira_result, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())