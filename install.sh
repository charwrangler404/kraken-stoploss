#!/bin/bash

ln -s pre-commit ./.git/hooks/pre-commit
chmod u+x pre-commit

python3 -m venv .venv
source .venv

