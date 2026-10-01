import asyncio
import logging
import sys
import threading
import uuid
from typing import Annotated, Optional, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from sqlmodel import Session

from src.agent.prompts import AGENT_SYSTEM_PROMPT
from src.agent.tools.knowledge import create_knowledge_search_tool
from src.agent.tools.pricing import estimate_trip_cost
from src.config import settings
from src.agent.retry_handler import RetryHandler
from src.schemas.itinerary_schema import ItinerarySchema

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    itinerary: Optional[ItinerarySchema]


def _run_async(coro):
    result = {}
    error = {}

    def runner():
        try:
            result["value"] = asyncio.run(coro)
        except Exception as e:
            error["value"] = e

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]
    return result["value"]


async def _fetch_mcp_tools() -> list:
    logger.info(
        "Connecting to MCP server (weather, maps) via stdio subprocess"
    )
    client = MultiServerMCPClient({
        "vacation_tools": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "src.mcp_server.server"],
        }
    })
    tools = await client.get_tools()
    logger.info(
        f"Retrieved {len(tools)} tool(s) from MCP server: "
        f"{[t.name for t in tools]}"
    )
    return tools


def build_tools(session: Session) -> list:
    mcp_tools = _run_async(_fetch_mcp_tools())
    return [
        *mcp_tools,
        estimate_trip_cost,
        create_knowledge_search_tool(session),
    ]


def build_initial_messages(user_request: str) -> list[BaseMessage]:
    return [
        SystemMessage(content=AGENT_SYSTEM_PROMPT),
        HumanMessage(content=user_request),
    ]

def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return "finalize"


def build_agent_graph(session: Session):
    tools = build_tools(session)
    model = ChatAnthropic(model=settings.ANTHROPIC_MODEL, api_key=settings.ANTHROPIC_API_KEY)
    model_with_tools = model.bind_tools(tools)
    structured_model = model.with_structured_output(ItinerarySchema)

    def call_model(state: AgentState) -> dict:
        response = model_with_tools.invoke(state["messages"])
        if getattr(response, "tool_calls", None):
            names = [tc["name"] for tc in response.tool_calls]
            logger.info(f"Agent decided to call tool(s): {names}")
        else:
            logger.info("Agent has enough information, moving to finalize")
        return {"messages": [response]}

    def finalize(state: AgentState) -> dict:
        logger.info("Finalizing structured itinerary")
        try:
            itinerary = structured_model.invoke(state["messages"])
        except Exception as e:
            raise ValueError(f"Failed to produce a valid itinerary: {str(e)}") from e
        return {"itinerary": itinerary}

    tool_node = ToolNode(tools)

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "finalize": "finalize"}
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("finalize", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


def run_agent(user_request: str, session: Session) -> ItinerarySchema:

    graph = build_agent_graph(session)
    messages = build_initial_messages(user_request)
    retry_handler = RetryHandler(max_attempts=3, delay=1.0)

    async def _ainvoke():
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}

        result = await graph.ainvoke(
            {"messages": messages, "itinerary": None},
            config=config
        )
        itinerary = result.get("itinerary")
        if itinerary is None:
            raise ValueError("Agent did not produce a final itinerary")
        return itinerary

    def _invoke():
        return _run_async(_ainvoke())

    return retry_handler.execute(_invoke)
