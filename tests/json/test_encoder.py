import pytest
import splatlog as slog


class TestJSONEncoderWithFailingReducer:
    @pytest.fixture
    def reducer(self):
        return slog.json.JSONReducer(
            name="match_fail",
            priority=1,
            is_match=lambda obj: obj.x == 1,
            reduce=lambda obj: obj.__dict__,
        )

    @pytest.fixture
    def encoder(self, reducer):
        encoder = slog.json.JSONEncoder()
        encoder.add_reducers(reducer)
        return encoder

    def test_on_reducer_error_raise(self, encoder: slog.json.JSONEncoder):
        encoder.on_reducer_error = "raise"

        try:
            encoder.encode(int)
        except Exception as err:
            assert isinstance(err, AttributeError)
            assert str(err) == "type object 'int' has no attribute 'x'"
            assert err.__notes__ == [
                "in match|reduce of JSONReducer 'match_fail'",
                "called with `<type>` `<int>`",
            ]
        else:
            assert False, "expected exception to be raised"

    def test_on_reducer_error_continue(self, encoder: slog.json.JSONEncoder):
        encoder.on_reducer_error = "continue"

        enc = encoder.encode(int)
        assert enc == encoder.encode(int.__name__)
