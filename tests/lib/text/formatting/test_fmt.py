from faker import Faker
from splatlog.testing import assert_text
from splatlog.lib.text import fmt


def test_block_breakout():
    """
    Test "block-breakout", when use of {py:func}`splatlog.lib.text.fmt` on a
    "big" object produces a multi-line output, and we set it apart in its own
    markdown-style code block.

    The object formatting itself is done by
    {py:func}`splatlog.lib.text.fmt_pretty_repr`, which is reached via its
    presence as the default {py:attr}`splatlog.lib.text.FmtOpts.fallback`.
    """

    # Create a `Faker` that will generate the same output each time
    fake = Faker()
    fake.seed_instance(0)

    # Generate a "big" object that will span multiple lines when formatted
    big = fake.profile(fields=["name", "sex", "job", "mail"])

    # Pick a single key/value pair out of it as a "little" object that can be
    # formatted on a single line
    lil = {k: v for k, v in big.items() if k in {"name"}}

    # The "little" object should be formatted inline
    assert (
        f"given {fmt(lil, quote=True, type=True)}"
        == "given `<dict>` `{'name': 'Gary Cross'}`"
    )

    # The "big" object should "breakout" to its own markdown code block
    assert_text(
        actual=f"given {fmt(big, quote=True, type=True)}",
        expected="""
            given `<dict>`:

            ```py
            {
                'job': 'Musician',
                'name': 'Gary Cross',
                'sex': 'M',
                'mail': 'tamaramorrison@hotmail.com'
            }
            ```
        """,
        trailing_newlines=1,
    )
