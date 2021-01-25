# Contributing to pslab-python

Before opening a pull request, make sure that:

1.  The code builds.
2.  The docs build.
3.  The linters pass.
4.  The tests pass.
5.  Test coverage has not decreased.

## Building & Installing

The following assumes that the commands are executed from the root of the repository:

The project can be built with:

    pip install wheel
    python setup.py sdist bdist_wheel

The project can be installed in editable mode with:

    pip install -e .

The documentation can be built with:

    tox -e docs

The linters can be run with:

    tox -e lint

## Testing

pslab-python tests are written to run against real hardware. The tests are integration tests, since they depend on the correct function of not just the Python code under test, but also the firmware and hardware of the connected PSLab device. The tests can be run with:

    tox -e integration

When running the tests, the serial traffic to and from the PSLab can optionally be recorded by running:

    tox -e record

The recorded traffic is played back when running the tests on Travis, since no real device is connected in that situation. The tests can be run with recorded traffic instead of against real hardware by running:

    tox -e playback

### Writing new tests

Tests are written in pytest.

If the test requires multiple PSLab instruments to be connected together, this should be documented in the module docstring.

Test coverage should be \>90%, but aim for 100%.

## Code style

### General

-   Black.
-   When in doubt, refer to PEP8.
-   Use type hints (PEP484).
-   Maximum line length is 88 characters, but aim for less than 80.
-   Maximum [cyclomatic complexity](https://en.wikipedia.org/wiki/Cyclomatic_complexity) is ten, but aim for five or lower.
-   Blank lines before and after statements (for, if, return, \...), unless
    -   the statement comes at the beginning or end of another statement.
    -   the indentation level is five lines or fewer long.

### Imports

-   All imports at the top of the module.
-   Built-in imports come first, then third-party, and finally pslab, with a blank line between each group of imports.
-   No relative imports.
-   Within import groups, `import`-style imports come before `from`-style imports.
-   One `import`-style import per line.
-   All `from`-style imports from a specific package or module on the same line, unless that would violate the line length limit.
    -   In that case, strongly consider using `import`-style instead.
    -   If that is not possible, use one import per line.
-   Imports are sorted alphabetically within groups.

### Comments and docstrings

-   All public interfaces (modules, classes, methods) have Numpydoc-style docstrings.
-   Blank line after module- and class-level docstrings, but not after method-level docstrings.
-   Comments start with a capital letter and end with a period if they contain at least two words.
-   Comments go on the same line as the code they explain, unless that would violate the line length limit.
    -   In that case, the comment goes immediately before the code it explains.
-   Avoid multiline comments.
