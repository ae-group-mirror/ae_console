<!--
  THIS FILE IS EXCLUSIVELY MAINTAINED IN THE NAMESPACE ROOT PACKAGE. CHANGES HAVE TO BE DONE THERE.
  All changes will be deployed automatically to all the portions of this namespace package.
-->
# console portion of ae namespace package

[![GitLabPipeline](https://img.shields.io/gitlab/pipeline/ae-group/ae_console/master?logo=python)](
    https://gitlab.com/ae-group/ae_console)
[![PyPIVersion](https://img.shields.io/pypi/v/ae_console)](
    https://pypi.org/project/ae-console/#history)

>The portions (modules and sub-packages) of the Application Environment for Python are within
the `ae` namespace and are providing helper methods and classes for to develop
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


Execute the following command for to use the ae.console module in your
application. It will install ae.console into your python (virtual) environment:
 
```shell script
pip install ae-console
```

If you instead want to contribute to this portion then first fork
[the ae_console repository at GitLab](https://gitlab.com/ae-group/ae_console "ae.console code repository"),
then pull it to your machine and finally execute the following command in the root folder
of this repository (ae_console):

```shell script
pip install -e .[dev]
```

The last command will install this module portion into your virtual environment, along with
the tools you need to develop and run tests or for to extend the portion documentation.
For to contribute only to the unit tests or the documentation of this portion replace
the setup extras key `dev` in the above command with `tests` or `docs` respectively.


## namespace portion documentation

More info on the features and usage of this portion are available at
[ReadTheDocs](https://ae.readthedocs.io/en/latest/_autosummary/ae.console.html#module-ae.console
"ae_console documentation").

<!-- Common files version 0.0.60 deployed version 0.1.36 (with 0.0.60)
     to https://gitlab.com/ae-group as ae_console module as well as
     to https://ae-group.gitlab.io with CI check results as well as
     to https://pypi.org/project/ae-console as namespace portion ae-console.
-->
