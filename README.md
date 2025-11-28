splatlog
==============================================================================

Python logger that accepts ** values and prints 'em out.

Because I'll forget, and because I know I'll look here when I do...

Usage
------------------------------------------------------------------------------

```python
# Swap `splatlog` for `logging`
import splatlog

# Get a logger instance same as you would from `logging`
log = splatlog.getLogger(__name__)

# In your `__main__.py` or wherever you get started
splatlog.setup(level="info", console="stderr")
```

Development
------------------------------------------------------------------------------

Setup the [nix][] package manager on your machine and run:

    nix-shell

[nix]: https://nixos.org/download/

That's it, you should be in a shell session with `uv`, `python`, `dr.t`,
`make`, `sphinx-build`, and everything else you'll need available.

What `nix-shell` did:

1.  Install [uv][] and enter a shell session with it (and other system
    dependencies) available
2.  Run `uv sync` to
    1.  Install a compatible [Python][] version
    2.  Create a new [Python Virtual Environment (`venv`)][venv]
    3.  Install package dependencies specified in `pyproject.toml` from [PyPi][]
        into the [venv][]
3.  Run `source .venv/bin/activate` to _activate_ the [venv][], making the
    Python packages and executables available

These steps are specified in the `shell.nix` file.

[uv]: https://docs.astral.sh/uv/
[Python]: https://www.python.org/
[PyPi]: https://pypi.org/
[venv]: https://peps.python.org/pep-0405/

> ⁉️ If you **do not want to use [nix][]** for whatever reason, you should be fine
> getting [uv][] from your OS package manager or the
> [online installer](https://docs.astral.sh/uv/getting-started/installation/).
> Just run `uv sync` and `source .venv/bin/activate` and you should be good.

> ⁉️ If you **do not want to use [uv][]** for whatever reason, you should — _in
> theory_ — be able to substitute your favorite Python ecosystem tool that
> understands the [pyproject.toml standard][].
>
> [pyproject.toml standard]: https://packaging.python.org/en/latest/specifications/pyproject-toml/

Building Docs
------------------------------------------------------------------------------

    cd ./docs && make html
    
Watching and serving:

    cd ./docs && make watch
    

Running Tests
------------------------------------------------------------------------------

All of them:

    dr.t ./splatlog/**/*.py ./docs/content/**/*.md

Single file, fail-fast, printing header panel (so you can find where they
start and end easily during repeated runs):

    dr.t -fp <filename>


Publishing
------------------------------------------------------------------------------

1.  Update the version in `pyproject.toml`.
    
2.  Commit, tag `vX.Y.Z`, push.
    
3.  Log in to [PyPI](https://pypi.org) and go to
    
    https://pypi.org/manage/account/
    
    to generate an API token.
    
4.  Throw `poetry` at it:
    
        poetry publish --build --username __token__ --password <token>
    
5.  Bump patch by 1 and append `a0`, commit and push (now we're on the "alpha"
    of the next patch version).
