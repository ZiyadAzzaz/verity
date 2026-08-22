"""Google ADK declarations for Verity's four named agents.

The durable background runner in `verity.pipeline` invokes the same four roles with
durable checkpoints around every side effect; these declarations make the agent graph
inspectable and runnable with ADK tooling.
"""

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.apps import App

from verity.config import get_settings
from verity.models import DebugProposal, ExecutionPlan, ParsedClaim, Verdict
from verity.prompts import (
    DEBUG_INSTRUCTION,
    ENVIRONMENT_INSTRUCTION,
    PARSER_INSTRUCTION,
    REPORTER_INSTRUCTION,
)

MODEL = get_settings().gemini_model

parser_agent = LlmAgent(
    name="parser_agent",
    model=MODEL,
    instruction=PARSER_INSTRUCTION,
    output_schema=ParsedClaim,
    output_key="parsed_claim",
)

environment_agent = LlmAgent(
    name="environment_agent",
    model=MODEL,
    instruction=ENVIRONMENT_INSTRUCTION,
    output_schema=ExecutionPlan,
    output_key="execution_plan",
)

debug_agent = LlmAgent(
    name="debug_agent",
    model=MODEL,
    instruction=DEBUG_INSTRUCTION,
    output_schema=DebugProposal,
    output_key="debug_proposal",
)

reporter_agent = LlmAgent(
    name="reporter_agent",
    model=MODEL,
    instruction=REPORTER_INSTRUCTION,
    output_schema=Verdict,
    output_key="verdict",
)

root_agent = SequentialAgent(
    name="verity_pipeline",
    sub_agents=[parser_agent, environment_agent, debug_agent, reporter_agent],
    description="Four-agent AI claim verification pipeline with durable bounded execution.",
)

app = App(root_agent=root_agent, name="app")
