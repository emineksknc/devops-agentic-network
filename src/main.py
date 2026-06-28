import asyncio
import json
from src.agents.github_agent import GitHubAgent
from src.agents.jira_agent import JiraAgent
from src.agents.reporter_agent import ReporterAgent
from src.config.settings import settings

async def main():
    print("==================================================")
    print("🚀 DevOps Agentic Network (DAN) - MULTI-AGENT AI PIPELINE")
    print("==================================================\n")
    
    # 1. Bütün Ajanları Ayağa Kaldır
    github_agent = GitHubAgent()
    jira_agent = JiraAgent()
    reporter_agent = ReporterAgent()
    
    github_context = {
        "owner": settings.GITHUB_OWNER, 
        "repo": settings.GITHUB_REPO, 
        "count": 3
    }
    
    # 🔹 ADIM 1: GitHub Modülü Çalışıyor
    print(f"🔹 [1/3] {github_agent.name} çalıştırılıyor...")
    github_result = await github_agent.run("Scan commits", context=github_context)
    
    extracted_ids = github_result["extracted_data"]["jira_ids_found"]
    raw_commits = github_result["extracted_data"]["raw_commits"]
    print(f"🎯 Otomatik Ayıklanan Biletler: {extracted_ids}\n")
    
    if not extracted_ids:
        print("⚠️ İşlenecek bilet veya commit bulunamadı. Akış durduruluyor.")
        return

    # 🔹 ADIM 2: Jira Modülü Çalışıyor
    print(f"🔹 [2/3] {jira_agent.name} canlı panoyu güncelliyor...")
    jira_context = {"jira_ids": extracted_ids, "action": "both"}
    await jira_agent.run("Update live tickets", context=jira_context)
    print("✅ Jira güncellemeleri tamamlandı.\n")

    # 🔹 ADIM 3: Yapay Zeka Raporlama Modülü Çalışıyor
    print(f"🔹 [3/3] {reporter_agent.name} lokal AI (Ollama) ile rapor hazırlıyor...")
    reporter_context = {"raw_commits": raw_commits}
    reporter_result = await reporter_agent.run("Generate executive summary", context=reporter_context)
    
    print("\n==================================================")
    print("📝 OLLAMA TARAFINDAN ÜRETİLEN YÖNETİCİ RAPORU:")
    print("==================================================")
    print(reporter_result["generated_report"])
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())