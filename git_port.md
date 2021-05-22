# dpjuge

## git porting

dpjudge is originally lying here:
+ [Project dpjudge](https://sourceforge.net/projects/dpjudge/), at _Sourceforge_.
  + credits to Manus Hand, and Mario Huys.

The sourceforge fork is [here](https://sourceforge.net/p/dpjudge/code/forks/), from _hclm_:
+ default tree [here](https://sourceforge.net/u/hclm/dpjudge/ci/default/tree/)

Porting to git, from Mercurial (hg), was done using:
+ [fast-export](https://github.com/serrasqueiro/fast-export)
  + Used Sourceforge clone from Mercurial, then _**hg**_, version:
    o Mercurial Distributed SCM (version 5.8)

The Mercurial configuration used was as follow:
```
ludo:~/hclm-dpjudge> more .hg/hgrc  
# example repository config (see 'hg help config' for more info)
[paths]
###default = ssh://hclm@hg.code.sf.net/u/hclm/dpjudge
###default = ssh://git@github.com:serrasqueiro/dpjudge.git
default = ../my-local-git

# path aliases to other clones of this repo in URLs or filesystem paths
# (see 'hg help config.paths' for more info)
#
# default:pushurl = ssh://jdoe@example.net/hg/jdoes-fork
# my-fork         = ssh://jdoe@example.net/hg/jdoes-fork
# my-clone        = /home/jdoe/jdoes-clone

[ui]
# name and email (local to this repository, optional), e.g.
# username = Jane Doe <jdoe@example.com>
verbose = True
```
Then at the git dir, performed:
- `/tmp/fast-export/hg-fast-export.sh -r ~/hclm-dpjudge/`

## Elsewhere...

- About the Diplomatic Pouch, article [here](http://uk.diplom.org/pouch/Zine/S2020M/Editor/about.html).
