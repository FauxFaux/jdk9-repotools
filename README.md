This repo exists to work around Oracle's OpenJDK project using `hg`,
and using it badly.


flatten.py
---

# git clone hg::...jdk9
# for each submodule, git submodule add that into this repo
# destory the .gitmodules file (i.e don't commit anything)

This leaves you with a super weird git repo:

```
$ cat jdk9/.git/config
[core]
	repositoryformatversion = 0
	filemode = true
	bare = false
[remote "origin"]
	url = hg::http://hg.openjdk.java.net/jdk9/jdk9
	fetch = +refs/heads/*:refs/remotes/origin/*
[branch "master"]
	remote = origin
	merge = refs/heads/master
[submodule "corba"]
	url = hg::http://hg.openjdk.java.net/jdk9/jdk9/corba
[submodule "jaxp"]
	url = hg::http://hg.openjdk.java.net/jdk9/jdk9/jaxp
[submodule "jaxws"]
	url = hg::http://hg.openjdk.java.net/jdk9/jdk9/jaxws
[submodule "langtools"]
	url = hg::http://hg.openjdk.java.net/jdk9/jdk9/langtools
[submodule "nashorn"]
	url = hg::http://hg.openjdk.java.net/jdk9/jdk9/nashorn
[submodule "hotspot"]
	url = hg::http://hg.openjdk.java.net/jdk9/jdk9/hotspot
[submodule "jdk"]
	url = hg::http://hg.openjdk.java.net/jdk9/jdk9/jdk
```

```
% ls jdk9/.git/modules
corba  hotspot  jaxp  jaxws  jdk  langtools  nashorn
```

Unlike with normal submodules, you can just cd into these things
and pull them, and you should.

Once you've pulled everything, you can:

```
mkdir flattened; (cd flattened; git init)
python3 flatten.py
cd flattened
git reset --hard
```

Then, you'll have a sane repo!

My copy is: https://github.com/FauxFaux/jdk9-flat

