---
title: docs
date: 2021-06-08
---

#### notes on tools I am using     

* Macvim 
    
* Rectangle  
    + cmd+crl+<-  -> Left Half  
    + cmd+crl+->  -> Right Half  
    + q cmd+ctl+return -> Full Screen  

* iterm2 
    + cmd+shift+D ->  splits the window vertically 
    + cmd+D -> splits the window horizontally


* python in emacs 
    + **pyenv** for python versions  
      > M-x pyvenv-workon  
      > SPC m V w -> work on virtual environment in WORKON_HOME
    

    + using ipython 
      > spc m s i -> start a Ipython for PERL 
      >  SPC m s F -> send function and switch to REPL in insert mode

    + debug  
      > <F5> - insert debug  

    + run python in shell  
      > SPC m c c -> exec current file in a comint shell  

    + testing - pytest
      > SPC m t t -> launch the current test (function)   

    + reference  
      > [reference](https://develop.spacemacs.org/layers/+lang/python/README.html)  


* spacesmacs
  - fix package download err
    > emacs --insecure
    > SPC q q 退出 Emacs 并杀掉服务器

  - vim

  - python
    > SPC m V w -> work on virtual environment in WORKON_HOME  
    > SPC m c c -> Execute current file in a comint shell  

  - standard ML
    + SPC m s b -> Send buffer to REPL
    + ctr-c ctr-s -> send buffer to REPL
    + ctr-d -> stop REPL
    + C-c M-o in the REPL buffer

  - keys  
    + 
    + spc 1 - switch to window 1  
    + SPC + h -> help
    + SPC f e R 来重载配置  
    + SPC b b -> list all buffer  
    + 
    + w -> advance one word	
    + b -> back one word  
    + 
    + SPC f t -> toggle NeoTree at pwd
    + u -> Undo last change
    + SPC 1   -> switch windows
    + SPC w d -> Close current window
    +
    + 'i' to be in insert editor, use 'ESC' key to be in normal state
    + 
    + d d - cut the line under cursor
    + y y -> copy line
    + p -> paste  
    + v -> highlight text  
    + y -> yank 
    + d -> delete highlight text  
    + dw -> delete word  
    + d$ -> delete to end of line  
    + 
    + g g -> beginning of file
    + G   -> end of file  
    + b -> back one word 
    + w -> advance one word 
    + 

  - notes:  
    * reload config file  
      > M-x load-file  
      > M-x eval-buffer  

    * move  
      > c-n -> down  
      > c-p -> up

* markdown in emacs  
  - preview the markdown buffer, and open a new tab in the browser  
    > F5 -> grip-mode  


* emacs
  - use emacs not emacsclient now  
    + > emacs &  


  - autoload emacs daemon when logining
    > launchctl unload /Users/zhaowenlong/Library/LaunchAgents/gnu.emacs.daemon.plist  
    > launchctl load -w /Users/zhaowenlong/Library/LaunchAgents/gnu.emacs.daemon.plist  

  -  also could use "emacs --fg-daemon" to start the daemon mode  

  - reference
    + [Spacemacs Basics](https://search-and-deploy.gitlab.io/cheat-sheets/spacemacs-basics/)
    + [spacemacs](https://wiki.archlinux.org/index.php/Spacemacs#Install_Spacemacs)


#### goodbooks
* [The Lean Startup](https://www.amazon.com/Lean-Startup-Entrepreneurs-Continuous-Innovation/dp/B005MM7HY8/ref=sr_1_1?crid=SVIK2EFUKTBZ&dchild=1&keywords=the+lean+startup&qid=1588064286&sprefix=the+lean+startup%2Caps%2C330&sr=8-1)
* [The Great CEO Within](https://www.goodreads.com/book/show/48691943-the-great-ceo-within)
* [The Effective Executive](https://www.goodreads.com/book/show/48019.The_Effective_Executive?ac=1&from_search=true&qid=76WiM1JVBT&rank=1)
