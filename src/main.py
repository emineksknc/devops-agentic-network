import asyncio
from src.agents.orchestrator_agent import OrchestratorAgent

async def main():
    print("==================================================")
    print("🚀 DevOps Agentic Network (DAN) - OTONOM ORKESTRASYON")
    print("==================================================")
    
    # Sadece Şef Ajanı ayağa kaldırıyoruz
    orchestrator = OrchestratorAgent()
    
    # Şefe tek bir görev/hedef veriyoruz
    user_goal = "GitHub reposundaki son değişiklikleri incele, ilgili Jira kartlarını güncelle ve teknik bülteni hazırla."
    # user_goal = "GitHub reposundaki son değişiklikleri incele ve sadece teknik bülteni hazırla. Kesinlikle Jira kartlarında bir güncelleme yapma."
    # Kontrolü tamamen şefe devrediyoruz
    result = await orchestrator.run(user_goal)
    
    print("\n==================================================")
    print("📝 ŞEF AJAN DENETİMİNDE TAMAMLANAN NİHAİ RAPOR:")
    print("==================================================")
    if result.get("status") == "success":
        print(result.get("final_report"))
    else:
        print(result.get("message", "Akış tamamlanamadı."))
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())