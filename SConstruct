# Starter SConstruct for enscons
# (filled by enscons.setup2toml)

import enscons

try:
    import tommlib  # Python 3.11+
except ImportError:
    import tomli as tomllib

metadata = dict(tomllib.load(open("pyproject.toml", "rb")))["tool"]["enscons"]

full_tag = "py3-none-any"

env = Environment(
    tools=["default", "packaging", enscons.generate],
    PACKAGE_METADATA=metadata,
    WHEEL_TAG=full_tag,
)

# Only *.py is included automatically by setup2toml.
# Add extra 'purelib' files or package_data here.
py_source = Glob("conda_package_streaming/*.py")

lib = env.Whl("purelib", py_source, root="")
whl = env.WhlFile(lib)

# Add automatic source files, plus any other needed files.
sdist_source = FindSourceFiles() + ["PKG-INFO"]

sdist = env.SDist(source=sdist_source)

env.NoClean(sdist)
env.Alias("sdist", sdist)

develop = env.Command("#DEVELOP", enscons.egg_info_targets(env), enscons.develop)
env.Alias("develop", develop)

# needed for pep517 / enscons.api to work
env.Default(whl, sdist)
