#!/bin/sh
set -eux

export GIT_ALLOW_PROTOCOL=hg

R=hg::http://hg.openjdk.java.net/jdk9/jdk9

cd jdk9
git pull --rebase

subrepos="$(grep '^subrepos=' common/bin/hgforest.sh | cut -d\" -f 2)"
for f in $subrepos; do (
    cd $f
    git pull --rebase
); done

