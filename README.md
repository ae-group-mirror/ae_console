<!--
  THIS FILE IS EXCLUSIVELY MAINTAINED IN THE AE ROOT PACKAGE. ANY CHANGES SHOULD BE DONE THERE.
  All changes will be deployed automatically to all the portions of this namespace package.
-->
# console Portion Of ae Namespace Package

The portions (modules and sub-packages) of the Application Environment for Python are within
the `ae` namespace and are providing helper methods and classes for to develop
full-featured applications with Python.


## Installation

Execute the following command for to use the ae.console module in your
application. It will install ae.console into your python (virtual) environment:
 
```shell script
pip install ae-console
```

If you instead want to contribute to this portion then first fork
[the ae-console repository at GitLab](https://gitlab.com/ae-group/ae_console "ae.console code repository"),
then pull it to your machine and finally execute the following command in the root folder
of this repository (ae_console):

```shell script
pip install -e .[dev]
```

The last command will install this module portion into your virtual environment, along with
the tools you need to develop and run tests or for to extend the portion documentation.
For to contribute only to the unit tests or the documentation of this portion replace
the setup extras key `dev` in the above command with `tests` or `docs` respectively.


## Namespace Portion Documentation

More info on the features and usage of this portion are available at
[ReadTheDocs](https://ae.readthedocs.io/en/latest/_autosummary/ae.console.html#module-ae.console
"ae_console documentation").

<!-- Common files version 0.0.21 deployed (with 0.0.21)
     to the ae_console module version 0.0.11.
-->