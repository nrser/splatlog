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
    uv sync
    source .venv/bin/activate

Breakdown:

1.  `nix-shell`
    
    Executes [`shell.nix`](./shell.nix) to install [uv][], as well as other
    system dependencies like `make`.

2.  `uv sync`
    
    1.  Installs a compatible [Python][].
    2.  Creates the [venv][] at [`.venv`](./.venv).
    3.  Installs package deps from [`pyproject.toml`](./pyproject.toml).

3.  `source .venv/bin/activate`
    
    Makes the Python dependency packages and commands available in your shell.

[nix]: https://nixos.org/download/
[uv]: https://docs.astral.sh/uv/
[Python]: https://www.python.org/
[PyPi]: https://pypi.org/
[venv]: https://peps.python.org/pep-0405/

> ⁉️ If you **do not want to use [nix][]** for whatever reason, you should be
> fine getting [uv][] from your OS package manager or the
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

    tox

Single file:

    poe test <filename>


Publishing
------------------------------------------------------------------------------

1.  Update the version in `pyproject.toml`.

2.  Commit, tag `vX.Y.Z`, push. A GitHub Action will build and publish.
    
3.  Bump patch by 1 and append `a0`, commit and push (now we're on the "alpha"
    of the next patch version).
