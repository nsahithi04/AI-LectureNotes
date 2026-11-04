import pytest

from app.meetings.errors import MeetingError
from app.meetings.oauth import STATE_LIFETIME_SECONDS, OAuthStateStore, id_token_email
from tests.meetings.fake_google import id_token


def test_a_state_works_once_and_only_for_its_provider():
    states = OAuthStateStore()
    state, _ = states.create("google_meet", "teacher-1")

    with pytest.raises(MeetingError):
        states.consume("microsoft_teams", state)
    # A wrong-provider attempt uses the state up too.
    with pytest.raises(MeetingError):
        states.consume("google_meet", state)

    state, _ = states.create("google_meet", "teacher-1")
    assert states.consume("google_meet", state).user_id == "teacher-1"
    with pytest.raises(MeetingError) as error:
        states.consume("google_meet", state)
    assert error.value.code == "invalid_connection"


def test_states_expire():
    now = [1000.0]
    states = OAuthStateStore(clock=lambda: now[0])
    state, _ = states.create("google_meet", "teacher-1")
    now[0] += STATE_LIFETIME_SECONDS + 1

    with pytest.raises(MeetingError):
        states.consume("google_meet", state)


def test_pending_sign_ins_are_limited():
    states = OAuthStateStore(max_pending=2)
    first, _ = states.create("google_meet", "a")
    states.create("google_meet", "b")
    states.create("google_meet", "c")

    with pytest.raises(MeetingError):
        states.consume("google_meet", first)


@pytest.mark.parametrize("token, email", [(id_token("t@school.edu"), "t@school.edu"), ("garbage", None), (None, None)])
def test_the_account_email_is_read_from_the_id_token(token, email):
    assert id_token_email(token) == email
