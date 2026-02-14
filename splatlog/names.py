"""
Helpers for working with logger and module names.

Convention is to use module names as logger names, so they are effectively
the same thing in practice.
"""


def root_name(module_name: str) -> str:
    """Get the root (first dotted component) of a module name.

    ## Parameters

    -   `module_name`: A dotted module name like `"splatlog.names"`.

    ## Returns

    The first component before the first `"."`.

    ## Examples

    ```python
    >>> root_name("splatlog.names")
    'splatlog'

    >>> root_name("splatlog")
    'splatlog'

    ```
    """
    return module_name.split(".")[0]


def is_in_hierarchy(hierarchy_name: str, logger_name: str) -> bool:
    """
    Test whether a logger name belongs to a given hierarchy.

    A name is in the hierarchy if it is exactly the hierarchy name or is a
    dotted child of it. This prevents false positives where one name is a
    prefix of another without a dot boundary (e.g. `"splat"` is *not* a
    parent of `"splatlog"`).

    ## Parameters

    -   `hierarchy_name`: The root name of the hierarchy to test against.
    -   `logger_name`: The logger name to check.

    ## Returns

    {py:data}`True` if `logger_name` is equal to or a child of
    `hierarchy_name`.

    ## Examples

    ```python
    >>> is_in_hierarchy("splatlog", "splatlog")
    True

    >>> is_in_hierarchy("splatlog", "splatlog.names")
    True

    >>> is_in_hierarchy("blah", "splatlog")
    False

    >>> is_in_hierarchy("splat", "splatlog")
    False

    ```
    """
    if not logger_name.startswith(hierarchy_name):
        return False
    hierarchy_name_length = len(hierarchy_name)
    return (
        hierarchy_name_length == len(logger_name)  # same as == at this point
        or logger_name[hierarchy_name_length] == "."
    )
