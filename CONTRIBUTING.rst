
..
    THIS FILE IS EXCLUSIVELY MAINTAINED IN THE NAMESPACE ROOT PACKAGE. CHANGES HAVE TO BE DONE THERE. 

contributing
============

we want to make it as easy and fun as possible for you to contribute to
this namespace.


reporting bugs
--------------

before you create a new issue, please check to see if you are using the latest
portion version; the bug may already be resolved.

also search for similar problems in the issue tracker; it may already be an
identified problem.

include as much information as possible into the issue description, at least:

1. version numbers of Python, the namespace portion and any involved packages
2. small self-contained code example that reproduces the bug
3. steps to reproduce the error
4. any traceback/error/log messages shown


requesting new features
-----------------------

1. provide a clear and detailed explanation of the feature you want and
   why it's important to add.
2. if you are able to implement the feature yourself (refer to the
   `contribution steps`_ section below).


contribution steps
------------------

1. make sure you have a `GitLab account <https://gitlab.com/users/sign_in>`__
   to be able to `fork this repository <https://docs.gitlab.com/ce/workflow/forking_workflow.html>`__.

2. clone your forked repo as ``origin`` remote to your computer, and add
   an ``upstream`` remote for the destination repo::

       git clone https://gitlab.com/<YourGitLabUserName>/<ThisRepositoryName>.git
       git remote add upstream https://gitlab.com/ae-group/<ThisRepositoryName>.git

3. checkout out a new local feature branch and update it to the latest
   version of the ``develop`` branch::

       git checkout -b feature-xxx develop
       git pull --rebase upstream develop

       please keep your code clean by staying current with the
       ``develop`` branch, where code will be merged. if you find
       another bug, please fix it in a separated branch instead.

4. push the branch to your fork. treat it as a backup::

       git push origin feature-xxx

5. code

   implement the new feature or the bug fix; include tests, and ensure they pass.

6. commit

   for every commit please write a short (max 72 characters) summary in the
   first line followed with a blank line and then more detailed
   descriptions of the change. use Markdown syntax for simple styling.
   please include any issue number (in the format #nnn) in your summary::

        git commit -m "issue #123: put change summary here (can be a issue title)"

   **never leave the commit message blank!** provide a detailed, clear, and
   complete description of your commit!

7. prepare a Merge Request

   before submitting a `merge request <https://docs.gitlab.com/ce/workflow/forking_workflow.html#merging-upstream>`__,
   update your branch to the latest code::

        git pull --rebase upstream develop

   if you have made many commits, we ask you to squash them into atomic
   units of work. most issues should have one commit only, especially bug
   fixes, which makes them easier to back port::

        git checkout develop
        git pull --rebase upstream develop
        git checkout feature-xxx
        git rebase -i develop

   push changes to your fork::

        git push -f

8. issue/make a GitLab Merge Request:

   * navigate to your fork where you just pushed to
   * click `Merge Request`
   * in the branch field write your feature branch name (this is filled with
     your default branch name)
   * click `Update Commit Range`
   * ensure the changes you implemented are included in the `Commits` tab
   * ensure that the `Files Changed` tab incorporate all of your changes
   * fill in some details about your potential patch including a meaningful title
   * click `New merge request`.


.. hint::
   the steps 4 to 7 may be repeated, and could alternatively be automated with
   the helper script ``deploy_portions.py`` of the namespace root package.
   this script also allows to manage feature branches which are including
   changes on multiple portions of this namespace.

thanks for your contribution -- we'll get your merge request reviewed.
you should also review other merge requests, just like other developers
will review yours and comment on them. based on the comments, you should
address them. once the reviewers approve, the maintainers will merge the
code.


other resources
---------------

-  `General GitLab documentation <https://docs.gitlab.com/ce/>`__
-  `GitLab workflow
   documentation <https://docs.gitlab.com/ce/workflow/README.html>`__
