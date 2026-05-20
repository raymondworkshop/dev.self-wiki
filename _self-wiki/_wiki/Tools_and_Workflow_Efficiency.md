---
last_updated: 2024-05-20T12:00:00Z
title: Tools and Workflow Efficiency
description: A technical guide detailing the setup, shortcuts, and usage of various productivity tools including Macvim, iTerm2, and Spacemacs for enhanced cognitive flow states.
tags: [type/principle, habit, work]
---

> This document serves as a technical manual for maximizing efficiency across various computing environments, detailing specific shortcuts and configurations for Macvim, iTerm2, and Spacemacs. The goal is to minimize cognitive load during technical execution by automating workflows.

## Evolution
- Initial entries were scattered across various notes regarding specific software setups. This page synthesizes them into a cohesive operational manual.

## Content

### Macvim & Rectangle (Window Management)
- **Rectangle Shortcuts:**
    - `cmd+crl+<-`: Left Half
    - `cmd+crl+->`: Right Half
    - `q cmd+ctl+return`: Full Screen

### iTerm2 (Terminal Management)
- `cmd+shift+D`: Splits the window vertically.
- `cmd+D`: Splits the window horizontally.

### Python in Emacs (Advanced Development)
- **pyenv Integration:**
    - `M-x pyvenv-workon`: To activate a virtual environment in `WORKON_HOME`.
- **IPython Usage:**
    - `spc m s i`: Start IPython for PERL.
    - `SPC m s F`: Send function and switch to REPL in insert mode.
- **Debugging:**
    - `<F5>`: Insert debug.
- **Execution Modes:**
    - `SPC m c c`: Execute current file in a comint shell.
    - `SPC m t t`: Launch the current test (pytest).
    - `[reference]`: Link to Spacemacs documentation for detailed usage.

### Spacemacs (Editor Configuration)
- **Key Bindings Summary:**
    - `spc 1`: Switch to window 1.
    - `SPC + h`: Help.
    - `SPC f e R`: Reload configuration.
    - `SPC b b`: List all buffers.
    - `w`: Advance one word.
    - `b`: Back one word.
    - `SPC f t`: Toggle NeoTree at pwd.
    - `u`: Undo last change.
    - `SPC 1`: Switch windows.
    - `SPC w d`: Close current window.
- **Text Editing Modes (Vim/Insert):**
    - `'i'`: Enter insert editor.
    - `ESC`: Return to normal state.
    - `d d`: Cut the line under the cursor.
    - `y y`: Copy line.
    - `p`: Paste.
    - `v`: Highlight text.
    - `y`: Yank.
    - `d`: Delete highlighted text.
    - `dw`: Delete word.
    - `d$`: Delete to end of line.
    - `g g`: Beginning of file.
    - `G`: End of file.

### Markdown in Emacs
- `F5`: Preview the markdown buffer and open a new tab in the browser.

## Backlinks
<!-- BEGIN BACKLINKS -->
- **Mentioned in**: [[Productivity_and_Success_Mindset.md]] (Potential conceptual link regarding efficiency)
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/docs.md]]