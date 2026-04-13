from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pymongo import MongoClient, DESCENDING
from datetime import datetime, timezone

load_dotenv()

router = APIRouter(prefix="/api", tags=["Chat"])

DATABASE_NAME = "aqua_gaurd_db"
INSIGHTS_DB_NAME = "generated_insights"

_openai_client: Optional[OpenAI] = None


def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def get_mongo_db(db_name: str):
    client = MongoClient(os.getenv("MONGODB_URI"), serverSelectionTimeoutMS=5000)
    return client[db_name]


def serialize_doc(doc: dict) -> dict:
    """Convert non-JSON-serializable fields (datetime, ObjectId) to strings."""
    clean = {}
    for k, v in doc.items():
        if isinstance(v, datetime):
            clean[k] = v.isoformat()
        elif isinstance(v, dict):
            clean[k] = serialize_doc(v)
        else:
            clean[k] = v
    return clean


# ── Tool definitions ──────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_tank_config",
            "description": (
                "Fetch the user-configured safe ranges (min/max) for all water parameters "
                "of a specific tank (temperature, pH, turbidity, light, TDS). "
                "Call this whenever the user asks whether a value is safe, normal, or within range "
                "for their specific tank — each tank has its own custom thresholds."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tank_id": {
                        "type": "string",
                        "description": "The tank collection name, e.g. 'tank_1', 'tank_2'",
                    }
                },
                "required": ["tank_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_latest_readings",
            "description": (
                "Fetch the most recent sensor readings for a tank: "
                "temperature (°C), pH, turbidity (NTU), and TDS (ppm). "
                "Use this when the current values are not already in the page context."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tank_id": {
                        "type": "string",
                        "description": "The tank collection name, e.g. 'tank_1'",
                    }
                },
                "required": ["tank_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_latest_insights",
            "description": (
                "Fetch the latest AI-generated insights and predictions for a tank: "
                "current fish stress risk score, insight types, alert messages, and statuses. "
                "Use this when the user asks about predictions, alerts, or overall tank health."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tank_id": {
                        "type": "string",
                        "description": "The tank collection name, e.g. 'tank_1'",
                    }
                },
                "required": ["tank_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_readings_history",
            "description": (
                "Fetch a statistical summary of historical sensor readings "
                "(min, max, average, latest) for temperature, pH, and turbidity "
                "over a chosen time range. Use this for trend questions like "
                "'has pH been stable?' or 'what is the temperature trend?'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tank_id": {
                        "type": "string",
                        "description": "The tank collection name, e.g. 'tank_1'",
                    },
                    "range": {
                        "type": "string",
                        "enum": ["24h", "7d", "30d"],
                        "description": "Time range: '24h' for recent, '7d' for weekly, '30d' for monthly.",
                    },
                },
                "required": ["tank_id", "range"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_history",
            "description": (
                "Fetch a statistical summary of historical fish stress risk scores "
                "(min, max, average, latest) for a tank over a time range. "
                "Use this for questions about stress trends or risk escalation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tank_id": {
                        "type": "string",
                        "description": "The tank collection name, e.g. 'tank_1'",
                    },
                    "range": {
                        "type": "string",
                        "enum": ["24h", "7d", "30d"],
                        "description": "Time range for risk score history.",
                    },
                },
                "required": ["tank_id", "range"],
            },
        },
    },
]


# ── Tool execution ────────────────────────────────────────────────────────────

def tool_get_tank_config(tank_id: str) -> dict:
    try:
        db = get_mongo_db(DATABASE_NAME)
        doc = db["tank_config"].find_one({"tank_id": tank_id}, {"_id": 0})
        if not doc:
            return {"error": f"No configuration found for tank '{tank_id}'. "
                             "The tank may not have been configured yet."}
        return serialize_doc(doc)
    except Exception as e:
        return {"error": str(e)}


def tool_get_latest_readings(tank_id: str) -> dict:
    try:
        db = get_mongo_db(DATABASE_NAME)
        doc = db[tank_id].find_one({}, {"_id": 0}, sort=[("timestamp", DESCENDING)])
        if not doc:
            return {"error": f"No readings found for tank '{tank_id}'."}
        return serialize_doc(doc)
    except Exception as e:
        return {"error": str(e)}


def tool_get_latest_insights(tank_id: str) -> dict:
    try:
        insights_db = get_mongo_db(INSIGHTS_DB_NAME)

        # Latest risk score
        risk_doc = insights_db[tank_id].find_one(
            {"risk_score": {"$exists": True}},
            {"_id": 0, "risk_score": 1, "generated_at": 1},
            sort=[("generated_at", DESCENDING)],
        )

        # Latest insight per type
        insight_types = insights_db[tank_id].distinct(
            "insight_type",
            {"insight_type": {"$exists": True, "$ne": None}},
        )
        insights = []
        for itype in [t for t in insight_types if isinstance(t, str) and t.strip()]:
            doc = insights_db[tank_id].find_one(
                {"insight_type": itype},
                {"_id": 0, "insight_type": 1, "status": 1, "message": 1, "generated_at": 1},
                sort=[("generated_at", DESCENDING)],
            )
            if doc:
                msg = doc.get("message")
                if isinstance(msg, dict):
                    msg = msg.get("message") or msg.get("text") or str(msg)
                insights.append({
                    "insight_type": itype,
                    "status": doc.get("status"),
                    "message": str(msg) if msg is not None else None,
                    "generated_at": doc["generated_at"].isoformat()
                    if isinstance(doc.get("generated_at"), datetime)
                    else str(doc.get("generated_at")),
                })

        result: dict = {"tank_id": tank_id, "insights": insights}
        if risk_doc:
            result["risk_score"] = risk_doc.get("risk_score")
            ga = risk_doc.get("generated_at")
            result["risk_generated_at"] = ga.isoformat() if isinstance(ga, datetime) else str(ga)
        return result
    except Exception as e:
        return {"error": str(e)}


def tool_get_readings_history(tank_id: str, range: str) -> dict:
    try:
        db = get_mongo_db(DATABASE_NAME)
        limit = {"24h": 100, "7d": 300, "30d": 500}.get(range, 100)

        docs = list(
            db[tank_id]
            .find({}, {"_id": 0, "temperature": 1, "ph": 1, "turbidity": 1, "tds": 1, "timestamp": 1})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )
        if not docs:
            return {"tank_id": tank_id, "range": range, "num_readings": 0}

        def stats(values):
            v = [x for x in values if x is not None and isinstance(x, (int, float))]
            if not v:
                return None
            return {
                "min": round(min(v), 3),
                "max": round(max(v), 3),
                "avg": round(sum(v) / len(v), 3),
                "latest": round(v[0], 3),  # docs sorted newest first
            }

        return {
            "tank_id": tank_id,
            "range": range,
            "num_readings": len(docs),
            "temperature_C": stats([d.get("temperature") for d in docs]),
            "ph": stats([d.get("ph") for d in docs]),
            "turbidity_NTU": stats([d.get("turbidity") or d.get("tds") for d in docs]),
        }
    except Exception as e:
        return {"error": str(e)}


def tool_get_risk_history(tank_id: str, range: str) -> dict:
    try:
        insights_db = get_mongo_db(INSIGHTS_DB_NAME)
        limit = {"24h": 100, "7d": 300, "30d": 500}.get(range, 100)

        docs = list(
            insights_db[tank_id]
            .find({"risk_score": {"$exists": True}}, {"_id": 0, "risk_score": 1, "generated_at": 1})
            .sort("generated_at", DESCENDING)
            .limit(limit)
        )
        if not docs:
            return {"tank_id": tank_id, "range": range, "num_readings": 0}

        scores = [d["risk_score"] for d in docs if isinstance(d.get("risk_score"), (int, float))]
        if not scores:
            return {"tank_id": tank_id, "range": range, "num_readings": 0}

        return {
            "tank_id": tank_id,
            "range": range,
            "num_readings": len(scores),
            "risk_score": {
                "min": round(min(scores), 2),
                "max": round(max(scores), 2),
                "avg": round(sum(scores) / len(scores), 2),
                "latest": round(scores[0], 2),  # docs sorted newest first
            },
        }
    except Exception as e:
        return {"error": str(e)}


def dispatch_tool(name: str, args: dict) -> str:
    handlers = {
        "get_tank_config":      lambda: tool_get_tank_config(args["tank_id"]),
        "get_latest_readings":  lambda: tool_get_latest_readings(args["tank_id"]),
        "get_latest_insights":  lambda: tool_get_latest_insights(args["tank_id"]),
        "get_readings_history": lambda: tool_get_readings_history(args["tank_id"], args.get("range", "24h")),
        "get_risk_history":     lambda: tool_get_risk_history(args["tank_id"], args.get("range", "24h")),
    }
    handler = handlers.get(name)
    result = handler() if handler else {"error": f"Unknown tool: {name}"}
    return json.dumps(result)


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are AquaGuard Assistant, an AI helper embedded in AquaGuard — an aquarium tank monitoring and prediction system.

SCREEN DATA — the JSON below is exactly what the user is currently looking at on their screen.
When they say "this chart", "this metric", "this tank", or "what I'm seeing" — they mean the values in this data.
Treat it as ground truth. Never say you cannot see the screen.

{context}

You have access to tools that query the live database for deeper analysis. Use them proactively:
- Always call get_tank_config before judging whether a value is safe — every tank has its own custom-configured thresholds.
- Call get_latest_readings if current sensor values are not in the screen data above.
- Call get_latest_insights for questions about predictions, alerts, or fish stress.
- Call get_readings_history or get_risk_history for trend and pattern questions.

General domain knowledge (use only as fallback if no tank config is found):
- Temperature: safe ~24–28°C | pH: safe ~6.5–7.5 | Turbidity: safe 0–5 NTU
- Fish Stress Risk Score: 0–30 safe, 31–60 warning, 61–100 critical

When answering:
- Be concise and practical (2–4 sentences unless more detail is asked for)
- Always prefer tank-specific configured thresholds over general knowledge
- Reference specific values from the screen data or fetched data when available
- Give actionable advice when a metric is in warning or critical state
- Use plain, friendly language

OFF-TOPIC RULE — if a question has absolutely nothing to do with aquariums, fish, water quality, or this application, do not answer it.
Reply with a single short, witty, fish-themed line instead. For example:
- "I'm a fish out of water on that one! Ask me about your tanks instead. 🐠"
- "That's way outside my tank! Anything aquarium-related I can help with? 🐡"
"""


# ── Request / Response models ─────────────────────────────────────────────────

class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None
    history: Optional[List[ChatHistoryMessage]] = []


class ChatResponse(BaseModel):
    reply: str


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        client = get_openai_client()

        context_str = (
            json.dumps(req.context, indent=2)
            if req.context
            else "The user has not navigated to a specific page yet. Use tools to fetch data if a tank is mentioned."
        )
        system_content = SYSTEM_PROMPT.format(context=context_str)

        messages: list = [{"role": "system", "content": system_content}]
        for msg in (req.history or []):
            if msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": req.message})

        # Agentic loop — allow up to 4 tool-call rounds before forcing a final answer
        for _ in range(4):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=512,
                temperature=0.7,
            )

            choice = response.choices[0]

            # No tool calls → final answer ready
            if choice.finish_reason == "stop" or not choice.message.tool_calls:
                return ChatResponse(reply=choice.message.content or "")

            # Append assistant turn (with tool_calls) then execute each call
            messages.append(choice.message)
            for tool_call in choice.message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                result = dispatch_tool(tool_call.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        # Safety fallback — call once more without tools to get a plain answer
        final = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=512,
            temperature=0.7,
        )
        return ChatResponse(reply=final.choices[0].message.content or "")

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
