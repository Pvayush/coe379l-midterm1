"""Milestone 3: implement three selected validation responsibilities."""

from __future__ import annotations

from .agent_models import ToolCallDecision
from .models import AgentResponse, LabRequest, TraceEvent
from .policy_context import ReservationContext, build_reservation_context


def validate_request_binding(
    decision: ToolCallDecision,
    *,
    request: LabRequest,
) -> list[str]:
    """TODO 3.1: Prevent identity and resolved-field substitution."""
    errors = []

    arguments = decision.arguments
    reserving = decision.tool == "reserve_resource"

    if "user_id" in arguments or decision.tool == "get_user_authorizations" or reserving:

        if arguments.get("user_id") != request.authenticated_user_id:
            errors.append("user_id_must_match_authenticated_user")

    for field in ("project_id", "resource_id", "start", "end"):


        trusted_value = getattr(request, field)

        if trusted_value is None and reserving:
            if reserving:
                errors.append(f"{field}_unresolved_in_request")
        elif reserving or field in arguments:

            if arguments.get(field) != trusted_value:
                errors.append(f"{field}_does_not_match_request")

    return errors


def validate_reservation_preconditions(context: ReservationContext) -> list[str]:
    """TODO 3.2: Return an error for every required context fact that is false."""
    errors = []
    if not context.arguments_complete:
        errors.append("reservation_arguments_incomplete")

    if not context.policy_retrieved:
        errors.append("policy_not_retrieved")

    if not context.authorizations_checked:
        errors.append("authorizations_not_checked")

    if not context.resource_status_checked:
        errors.append("resource_status_not_checked")

    if not context.project_authorized:
        errors.append("project_not_authorized")

    if not context.qualification_current:
        errors.append("required_qualification_missing")

    if not context.resource_available:
        errors.append("resource_unavailable")

    if not context.calibration_current:
        errors.append("calibration_not_current")


    if not context.maintenance_clear:
        errors.append("resource_under_maintenance")

    if not context.after_hours_approval_satisfied:
        errors.append("after_hours_approval_required")

    return errors



def validate_proposed_tool_call(
    decision: ToolCallDecision,
    *,
    request: LabRequest,
    trace: list[TraceEvent],
) -> list[str]:
    """Supplied wrapper. Do not modify this function."""
    errors = validate_request_binding(decision, request=request)
    if decision.tool == "reserve_resource":
        context = build_reservation_context(decision, trace)
        errors.extend(validate_reservation_preconditions(context))
    return errors


def retrieved_passage_ids(trace: list[TraceEvent]) -> set[str]:
    """Supplied helper. Do not modify this function."""
    identifiers: set[str] = set()
    for event in trace:
        if event.observation.tool != "search_lab_documents" or not event.observation.ok:
            continue
        identifiers.update(
            passage["passage_id"]
            for passage in event.observation.data.get("passages", [])
        )
    return identifiers


def validate_final_response(
    response: AgentResponse, trace: list[TraceEvent]
) -> list[str]:
    """TODO 3.3: Validate citations, claimed actions, and final status."""
    
    errors = []

    retrieved = retrieved_passage_ids(trace)
    for citation in response.citations:
        if citation not in retrieved:

            errors.append("citations_not_retrieved")
            break

    successful_actions = []


    for event in trace:

        if event.mutating and event.observation.ok:
            successful_actions.append(event.observation.tool)

    for action in response.completed_actions:

        if action not in successful_actions:
            errors.append("completed_action_not_in_successful_trace")
            break

    if response.status == "completed":

        if not successful_actions:
            errors.append("completed_without_successful_mutation")
        if not response.completed_actions:
            errors.append("completed_without_completed_actions")

    else:

        if response.completed_actions:
            errors.append("non_completed_response_claims_actions")
        if successful_actions:
            errors.append("successful_mutation_not_reported")
            
    return errors
