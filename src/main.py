import asyncio
from src.agents.github_agent import GitHubAgent

async def test_run():
    print("🚀 DevOps Agent Network - GitHub Agent Testi Başlatılıyor...\n")
    
    gh_agent = GitHubAgent()
    
    # Gerçek veya simüle edilmiş bir repo için bağlam (context) veriyoruz
    context = {
        "owner": "test-organization",
        "repo": "core-backend",
        "count": 4
    }
    
    result = await gh_agent.run("Fetch commits and analyze for Jira tickets", context=context)
    
    print("✅ Ajan Çalışma Sonucu:")
    print(f"Hedef Repo: {result['extracted_data']['owner']}/{result['extracted_data']['repo']}")
    print(f"Analiz Edilen Commit Sayısı: {result['extracted_data']['commits_analyzed']}")
    print(f"Bulunan Jira ID'leri: {result['extracted_data']['jira_ids_found']}")
    print("\n📦 Detaylı JSON Çıktısı:")
    import json
    print(json.dumps(result, indent=4))

if __name__ == "__main__":
    asyncio.run(test_run())