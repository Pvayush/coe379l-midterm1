from atlas_agent.agent import run_agent
from atlas_agent.llm import ScriptedLLM
from atlas_agent.models import LabRequest



REQUEST = LabRequest(
    authenticated_user_id="john",
    text="Book the tensile tester for my polymer-study project on October 16 from 2 to 3:30 PM.",
    project_id="polymer-study",
    resource_id="tensile-01",
    start="2026-10-16T14:00:00",
    end="2026-10-16T15:30:00",
)


def test_unsafe_action(environment):

    llm = ScriptedLLM([{
        "kind": "tool_call",
        "tool": "reserve_resource",
        "arguments": {
            "user_id": "john",
            "project_id": "polymer-study",
            "resource_id": "tensile-01",
            "start": "2026-10-16T14:00:00",
            "end": "2026-10-16T15:30:00",
        },
        "reasoning_summary": "Reserve without checking policy or permissions.",
    }])

    run = run_agent(REQUEST, llm=llm, environment=environment, max_steps=1)

    assert run.trace[0].observation.error_code == "action_gate_denied"
    assert len(environment.simulator.state["reservations"]) == 1


def test_invalid_final_response(environment):

    llm = ScriptedLLM([{
        "kind": "final",
        "response": {
            "status": "completed",
            "message": "The reservation was made.",
            "completed_actions": ["reserve_resource"],
        },
    }])

    run = run_agent(REQUEST, llm=llm, environment=environment)

    assert run.response.status == "failed"
    assert run.termination_reason == "invalid_final_response"


def test_invalid_decision(environment):

    llm = ScriptedLLM([{"kind": "unknown"}])

    run = run_agent(REQUEST, llm=llm, environment=environment)

    assert run.termination_reason == "invalid_model_decision"
    assert run.trace == []
