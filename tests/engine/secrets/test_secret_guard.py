import pytest
from pydantic import ValidationError

from tests.support.scenario import CREDENTIAL, make_context
from veil.engine import Context, redact


def test_the_context_hides_the_credential_values_in_repr_and_json(tmp_path):
    context, _, _, _ = make_context(tmp_path, [], credentials=(CREDENTIAL,))

    assert CREDENTIAL not in repr(context)
    assert CREDENTIAL not in str(context)
    assert CREDENTIAL not in context.model_dump_json(include={"secrets"})


@pytest.mark.parametrize("short", ["", "short", "1234567"])
def test_the_context_refuses_a_credential_value_that_is_too_short_and_does_not_echo_it(
    tmp_path, short
):
    context, _, _, _ = make_context(tmp_path, [])

    with pytest.raises(ValidationError) as error:
        Context(
            settings=context.settings,
            tracker=context.tracker,
            repo_provider=context.repo_provider,
            model_client=context.model_client,
            credentials=(short,),
        )

    assert "at least 8 characters" in str(error.value)
    assert not short or short not in str(error.value)


@pytest.mark.parametrize("blank", [" " * 8, "\t" * 9, " \n " * 4])
def test_the_context_refuses_a_credential_value_that_is_only_white_space(
    tmp_path, blank
):
    context, _, _, _ = make_context(tmp_path, [])

    with pytest.raises(ValidationError) as error:
        Context(
            settings=context.settings,
            tracker=context.tracker,
            repo_provider=context.repo_provider,
            model_client=context.model_client,
            credentials=(blank,),
        )

    assert "only white space" in str(error.value)


def test_the_engine_exports_the_redaction_filter_for_adapters_and_shells():
    text = f"The git error says {CREDENTIAL} and again {CREDENTIAL}-suffix."

    assert redact(text, (CREDENTIAL,)) == (
        "The git error says [redacted] and again [redacted]-suffix."
    )
    assert redact("nothing to hide", (CREDENTIAL,)) == "nothing to hide"
    assert redact(
        "a long-secret-value-1 and long-secret-value",
        ("long-secret-value", "long-secret-value-1"),
    ) == ("a [redacted] and [redacted]")


def test_redact_leaves_no_part_of_two_credential_values_that_overlap():
    first, second = "abcdefgh-12", "efgh-12-XYZ99"
    text = f"Error: abcdefgh-12-XYZ99 and again {second}."

    result = redact(text, (first, second))

    assert result == "Error: [redacted] and again [redacted]."
    assert "XYZ" not in result
    assert "abcd" not in result


def test_redact_hides_a_value_that_sits_inside_a_secret_pattern_match():
    key = "".join(["ghp_", "a1B2c3D4e5F6g7H8i9J0", "k1L2m3N4o5P6q7R8s9T0"])  # noqa: FLY002
    inner = key[10:30]

    assert redact(f"token {key} end", (inner,)) == "token [redacted] end"
