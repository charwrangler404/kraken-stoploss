# kraken-stoploss

## Linux documentation stnadards

All commands are written in a way that is predictable

There are two basic ways to change a way a program behaves. Options, and arguments

Options are preceded by a single dash when a single letter, and a double dash when a word. e.g.

    ls -l

    git pull --all

Arguments are not proceded by dashes, and represent fundimental actions that the program can perfrom

    git checkout <branchname>

Arguments that are wrapped in brackets have a special meanings. The type of bracket denotes
what the meaning is. The word in the bracket is the type of argument, not what you actually
want to pass. It's a descriptive of what you should put in there, and the actual string you
use is variable.

Arrow brackets are used to denote mandatory arguments. You must always provide these options.

    git checkout <branchname>

Becomes

    git checkout influx

Arguments in square brackets are used to denote optional arguments. They, by their nature, are
optional, but can effect the way the program behaves

    ls -l [directory]

Becomes:

    ls -l /bin

## bash idiosyncrosies

In Unix (Linux is a Unix-like, not all Unixes are Linuxes) directories are nested using forward
slashes, unlike Windows, which uses backslashes.

A directory path might look like the following

    /bin/bash

Also, in bash, backslashes are an escape character. This is used to prevent certain symbols from
being interpreted by the command interpeter, or shell.

Try the following

    echo $PATH

    echo \$PATH

This should provide some insight in to how these are different. $PATH is what is called an
environment variable, and all variables in bash are proceded by the $ character.

Because backslash is a special character


## BEFORE YOU WRITE ANY CODE DURING A SESSION

    git pull --all

## To add a new feature

The `-b` option in `git checkout` tells git that you want to create a new branch.

    git checkout -b <branchname>

## After you are done developing

make sure you are on the branch you want, i.e. the one with your new features (see to add a new feature)

    git checkout <branchname>

Add the changed files

    git add .

Create a commit

    git commit -m "<commit message>"

Push your changes up into github or whatever git website you're using

    git push origin <branchname>

e.g.

    git push origin influx

You can alternatively use the following, to sync all changes,

    git push --all

If this fails, try just pushing the new branch you're working on. It's always right to 
create a new branch for new code when you are working with others. This allows the maintainer
of the project to properly merge code into the correct repository.

## NEVER PUSH TO `main` or `master`

In order to maintain a clean project without any merge conflicts, we must make sure to never push
to the `main` or `master` branches. These branches are special and are meant to contain the most
recent working version of the code. Changes to these branches are *always* done via merge request