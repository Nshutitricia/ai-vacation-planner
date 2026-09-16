from typing import Annotated, Optional, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from sqlmodel import Session

from src.agent.prompts import AGENT_SYSTEM_PROMPT
from src.agent.tools.knowledge import create_knowledge_search_tool
from src.agent.tools.maps import find_place
from src.agent.tools.pricing import estimate_trip_cost
from src.agent.tools.weather import get_weather
from src.config import settings
from src.schemas.itinerary_schema import ItinerarySchema


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    itinerary: Optional[ItinerarySchema]


def build_tools(session: Session) -> list:
    return [
        get_weather,
        find_place,
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
    model = ChatAnthropic(model="claude-haiku-4-5", api_key=settings.ANTHROPIC_API_KEY)
    model_with_tools = model.bind_tools(tools)
    structured_model = model.with_structured_output(ItinerarySchema)

    def call_model(state: AgentState) -> dict:
        response = model_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def finalize(state: AgentState) -> dict:
        itinerary = structured_model.invoke(state["messages"])
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
