"""LangGraph akisi: github -> reviewer -> jira -> reporter.
LLM sadece plan kararinda kullanilir; bagimliliklar deterministik graftir.
Her dugum plan uyeligine gore calisir veya sessizce atlar.
"""
import json
import logging
from typing import Any, Dict, TypedDict

logger = logging.getLogger("flow.graph")


class FlowState(TypedDict, total=False):
    user_goal: str
    plan: list
    reason: str
    github_context: Dict[str, Any]
    dry_run: bool
    commit_units: list
    raw_commits: list
    review_passed: bool
    final_report: str
    jira_planned: list


def build_graph(workers: Dict[str, Any]):
    from langgraph.graph import END, StateGraph

    llm = workers["llm"]
    github_worker = workers["github"]
    reviewer_worker = workers["reviewer"]
    jira_worker = workers["jira"]
    reporter_worker = workers["reporter"]
    enabled = workers.get("enabled", {})
    plan_prompt = workers.get("plan_prompt", "")

    async def plan_node(state: FlowState) -> Dict[str, Any]:
        logger.info("Graf dugumu: plan")
        system_prompt = plan_prompt or (
            "Sen bir DevOps Orkestra Sefisin. Elinde su 4 alt ajan (arac) var:\n"
            "1. 'github_agent': Canli depodan son commitleri okur.\n"
            "2. 'reviewer_agent': Kod kalitesi ve guvenlik analizini yapip PASSED/FAILED raporlar.\n"
            "3. 'jira_agent': Bulunan biletleri Jira'da gunceller.\n"
            "4. 'reporter_agent': Commitlerden Turkce surum raporu hazirlar.\n\n"
            "Kullanicinin hedefine bakarak, hangi sirayla hangi ajanlari calistirman gerektigini planla.\n"
            "Yonlendirme Kurallari: Kodlari incelemeden kalite analizi veya jira guncellemesi yapamazsin.\n"
            "Yanıtını SADECE ve SADECE su JSON formatinda don, baska hicbir aciklama yazma:\n"
            "{\n"
            '  "plan": ["ajan_adi_1", "ajan_adi_2"],\n'
            '  "reason": "Bu plani yapma nedenin"\n'
            "}"
        )
        raw = await llm.generate_response(
            system_prompt, f"Hedef: {state.get('user_goal', '')}",
            trace_name="orchestrator.plan",
        )
        print("\n==================================================")
        print("OLLAMA TARAFINDAN OLUSTURULAN OTONOM IS PLANI:")
        print("==================================================")
        print(raw)
        print("==================================================\n")
        try:
            plan_json = json.loads(raw.replace("```json", "").replace("```", "").strip())
            steps = plan_json.get("plan", [])
            reason = plan_json.get("reason", "")
            logger.info("LLM plani parse edildi: %s", steps)
        except Exception as e:
            logger.warning("LLM gecerli JSON donmedi (%s). Fallback akis.", e)
            steps = ["github_agent", "reviewer_agent", "jira_agent", "reporter_agent"]
            reason = "fallback"
        # Kapali ajanlari plandan dusur
        active = {"github_agent": "github", "reviewer_agent": "reviewer",
                  "jira_agent": "jira", "reporter_agent": "reporter"}
        steps = [s for s in steps if s in active and enabled.get(active[s], True)]
        return {"plan": steps, "reason": reason}

    async def github_node(state: FlowState) -> Dict[str, Any]:
        if "github_agent" not in state.get("plan", []):
            return {}
        print("[Orkestrator] Graf dugumu: github_agent")
        res = await github_worker.run("Scan", context=state.get("github_context", {}))
        data = res.get("extracted_data", {})
        return {"commit_units": data.get("commit_units", []), "raw_commits": data.get("raw_commits", [])}

    async def reviewer_node(state: FlowState) -> Dict[str, Any]:
        units = state.get("commit_units", []) or []
        if "reviewer_agent" not in state.get("plan", []) or not units:
            return {"review_passed": True}
        print("[Orkestrator] Graf dugumu: reviewer_agent")
        for unit in units:
            if not unit.get("code_changes") or not unit["code_changes"].strip():
                unit["review_status"] = "PASSED"
                unit["review_comment"] = "Incelenecek kod degisikligi bulunamadi."
                continue
            r = await reviewer_worker.run("Review code quality", context={"code_changes": unit["code_changes"]})
            unit["review_status"] = r.get("review_status", "FAILED")
            unit["review_comment"] = r.get("review_comment", "")
            if unit["review_status"] == "FAILED":
                logger.warning("Commit %s kritik risk, ilgili biletler kilitlenecek.", unit.get("short_sha"))
        blocked = any(u.get("review_status") == "FAILED" for u in units)
        return {"commit_units": units, "review_passed": not blocked}

    async def jira_node(state: FlowState) -> Dict[str, Any]:
        units = state.get("commit_units", []) or []
        if "jira_agent" not in state.get("plan", []) or not units:
            return {}
        dry_run = state.get("dry_run", False)
        planned: list = list(state.get("jira_planned", []) or [])
        any_ticket = False
        for unit in units:
            if not unit.get("jira_ids"):
                continue
            any_ticket = True
            ok = unit.get("review_status", "PASSED") != "FAILED"
            print(f"[Orkestrator] Graf dugumu: jira_agent (commit {unit.get('short_sha')} -> {unit['jira_ids']})")
            author_line = f"Yazar: {unit.get('author', 'bilinmiyor')} ({unit.get('short_sha', '')})\n"
            if not ok:
                ctx = {"jira_ids": unit["jira_ids"], "action": "both",
                       "code_changes": author_line + f"[GUVENLIK/KALITE BLOKAJI]\n{unit.get('review_comment', '')}",
                       "review_passed": False}
            else:
                ctx = {"jira_ids": unit["jira_ids"], "action": "both",
                       "code_changes": author_line + (unit.get("code_changes", "") or ""),
                       "review_passed": True}
            if dry_run:
                planned.append({"commit_sha": unit.get("sha"), "short_sha": unit.get("short_sha"),
                                "jira_ids": list(unit["jira_ids"]), "review_passed": ok,
                                "code_changes": ctx["code_changes"], "action": "both"})
                logger.info("dry-run: %s icin Jira yazmasi atlandi.", unit["jira_ids"])
            else:
                await jira_worker.run("Update", context=ctx)
        if not any_ticket:
            logger.info("jira_agent planlanmisti ama bilet ID'si yok, atlandi.")
        return {"jira_planned": planned}

    async def reporter_node(state: FlowState) -> Dict[str, Any]:
        raw_commits = state.get("raw_commits", []) or []
        if "reporter_agent" not in state.get("plan", []) or not raw_commits:
            return {}
        print("[Orkestrator] Graf dugumu: reporter_agent")
        units = state.get("commit_units", []) or []
        blocked_shas = {u["sha"] for u in units if u.get("review_status") == "FAILED"}
        reportable = [c for c in raw_commits if c.get("sha") not in blocked_shas]
        if not reportable:
            logger.info("Tum commit'ler bloklu, raporlanacak degisiklik yok.")
            return {"final_report": "Tum degisiklikler guvenlik/kalite blokaji nedeniyle raporlanamadi."}
        r = await reporter_worker.run("Report", context={"raw_commits": reportable})
        return {"final_report": r.get("generated_report")}

    graph = StateGraph(FlowState)
    graph.add_node("plan", plan_node)
    graph.add_node("github", github_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("jira", jira_node)
    graph.add_node("reporter", reporter_node)
    graph.set_entry_point("plan")
    graph.add_edge("plan", "github")
    graph.add_edge("github", "reviewer")
    graph.add_edge("reviewer", "jira")
    graph.add_edge("jira", "reporter")
    graph.add_edge("reporter", END)
    return graph.compile()
