import nox


@nox.session(venv_backend="conda")
@nox.parametrize(
    "python",
    [(python) for python in ("3.7", "3.8", "3.9", "3.10")],
)
def tests(session):
    session.install("-e", ".[test]")
    session.run("pytest")
