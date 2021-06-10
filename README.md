<!--
  THIS FILE IS EXCLUSIVELY MAINTAINED IN THE NAMESPACE ROOT PACKAGE. CHANGES HAVE TO BE DONE THERE.
-->
# console portion of ae namespace package

[![GitLabPipeline](https://img.shields.io/gitlab/pipeline/ae-group/ae_console/master?logo=python)](
    https://gitlab.com/ae-group/ae_console)
[![PyPIVersion](https://img.shields.io/pypi/v/ae_console)](
    https://pypi.org/project/ae-console/#history)

>The portions (modules and sub-packages) of the Application Environment for Python are within
the `ae` namespace and are providing helper methods and classes to develop
full-featured applications with Python.

[![Coverage](https://ae-group.gitlab.io/ae_console/coverage.svg)](
    https://ae-group.gitlab.io/ae_console/coverage/ae_console_py.html)
[![MyPyPrecision](https://ae-group.gitlab.io/ae_console/mypy.svg)](
    https://ae-group.gitlab.io/ae_console/lineprecision.txt)
[![PyLintScore](https://ae-group.gitlab.io/ae_console/pylint.svg)](
    https://ae-group.gitlab.io/ae_console/pylint.log)

[![PyPIImplementation](https://img.shields.io/pypi/implementation/ae_console)](
    https://pypi.org/project/ae-console/)
[![PyPIPyVersions](https://img.shields.io/pypi/pyversions/ae_console)](
    https://pypi.org/project/ae-console/)
[![PyPIWheel](https://img.shields.io/pypi/wheel/ae_console)](
    https://pypi.org/project/ae-console/)
[![PyPIFormat](https://img.shields.io/pypi/format/ae_console)](
    https://pypi.org/project/ae-console/)
[![PyPIStatus](https://img.shields.io/pypi/status/ae_console)](
    https://libraries.io/pypi/ae-console)
[![PyPIDownloads](https://img.shields.io/pypi/dm/ae_console)](
    https://pypi.org/project/ae-console/#files)


## installation


execute the following command to use the ae.console module in your
application. it will install ae.console into your python (virtual) environment:
 
```shell script
pip install ae-console
```

if you instead want to contribute to this portion then first fork
[the ae_console repository at GitLab](https://gitlab.com/ae-group/ae_console "ae.console code repository"),
then pull it to your machine and finally execute the following command in the root folder
of this repository (ae_console):

```shell script
pip install -e .[dev]
```

the last command will install this module portion into your virtual environment, along with
the tools you need to develop and run tests or to extend the portion documentation.
to contribute only to the unit tests or to the documentation of this portion replace
the setup extras key `dev` in the above command with `tests` or `docs` respectively.


## namespace portion documentation

more info on the features and usage of this portion are available at
[ReadTheDocs](https://ae.readthedocs.io/en/latest/_autosummary/ae.console.html#module-ae.console
"ae_console documentation").

<!-- common files version 0.2.77 deployed version 0.2.51 (with 0.2.77)
     to https://gitlab.com/ae-group as ae_console module as well as
     to https://ae-group.gitlab.io with CI check results as well as
     to https://pypi.org/project/ae-console as namespace portion ae-console.
-->
