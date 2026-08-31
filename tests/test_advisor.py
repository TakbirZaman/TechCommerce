from ml.data.schemas import Category, UseCase
from ml.inference.advisor import AdvisorState, advance_conversation


def test_complete_query_needs_no_follow_up():
    state = AdvisorState()
    state, question, requirement = advance_conversation(
        state, "I need a laptop under 80k for programming."
    )
    assert question is None
    assert requirement is not None
    assert requirement.category == Category.LAPTOP


def test_incomplete_query_asks_one_material_question():
    state = AdvisorState()
    state, question, requirement = advance_conversation(state, "I need a laptop.")
    assert requirement is None
    assert question is not None
    assert "budget" in question.lower()


def test_multi_turn_conversation_builds_requirement_incrementally():
    state = AdvisorState()
    state, question, requirement = advance_conversation(state, "I need a laptop.")
    assert requirement is None
    assert "budget" in question.lower()

    state, question, requirement = advance_conversation(state, "90k")
    assert requirement is None
    assert "use" in question.lower()

    state, question, requirement = advance_conversation(state, "Programming")
    assert requirement is not None
    assert requirement.category == Category.LAPTOP
    assert requirement.budget_max == 90000
    assert UseCase.PROGRAMMING in requirement.use_cases


def test_does_not_ask_unnecessary_questions_when_info_sufficient():
    state = AdvisorState()
    state, question, requirement = advance_conversation(
        state, "Best laptop for programming under 80,000."
    )
    assert question is None
    assert requirement is not None
