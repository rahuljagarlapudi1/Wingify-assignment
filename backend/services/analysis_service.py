# services/analysis_service.py
import json
from beanie import PydanticObjectId
from datetime import datetime
from crewai import Crew, Process, Task
from models.document import Document, DocumentStatus
from agents import financial_analyst, document_verifier, investment_advisor, risk_assessor
from task import (
    verification_task,
    financial_analysis_task,
    risk_analysis_task,
    investment_recommendation_task,
)

async def process_financial_document(query: str, file_path: str, user_id: str, document_id: str) -> str:
    doc = await Document.get(PydanticObjectId(document_id))
    if not doc:
        return "NO_DOC"

    try:
        # Create fresh tasks using the same descriptions & expected outputs, but reuse the agent objects.
        vt = Task(
            description=verification_task.description,
            expected_output=verification_task.expected_output,
            agent=document_verifier,
        )
        fat = Task(
            description=financial_analysis_task.description,
            expected_output=financial_analysis_task.expected_output,
            agent=financial_analyst,
        )
        rt = Task(
            description=risk_analysis_task.description,
            expected_output=risk_analysis_task.expected_output,
            agent=risk_assessor,
        )
        ir = Task(
            description=investment_recommendation_task.description,
            expected_output=investment_recommendation_task.expected_output,
            agent=investment_advisor,
        )

        crew = Crew(
            agents=[document_verifier, financial_analyst, risk_assessor, investment_advisor],
            tasks=[vt, fat, rt, ir],
            process=Process.sequential,
            verbose=False,
        )

        await crew.kickoff_async(inputs={"query": query, "file_path": file_path, "user_id": user_id})

        def _clean(o):
            if o is None: return None
            if isinstance(o, (str, int, float, bool, dict, list)): return o
            return str(o)

        payload = {
            "verification": _clean(vt.output),
            "analysis": _clean(fat.output),
            "risk": _clean(rt.output),
            "recommendation": _clean(ir.output),
            "query_used": query,
            "source": file_path,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

        # ensure JSON-safe
        json.loads(json.dumps(payload))

        doc.analysis = payload
        doc.status = DocumentStatus.COMPLETED
        doc.processed_date = datetime.utcnow()
        doc.error = None
        await doc.save()
        return "OK"

    except Exception as e:
        doc.status = DocumentStatus.FAILED
        doc.processed_date = datetime.utcnow()
        doc.error = str(e)
        await doc.save()
        raise
