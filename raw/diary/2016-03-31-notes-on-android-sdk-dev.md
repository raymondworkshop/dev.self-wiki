---
layout: post
title: "Notes on Android SDK dev"
date: 2016-03-31
comments: true
categories: [android, technology]
abstract: "A share about Android NDK - build c/c++ code into shared lib app uses"
---

> <small> A share about Android NDK - build c/c++ code into shared lib app uses </small>

#### Android NDK - build c/c++ code into shared lib app uses

-   Android.mk - glue the c/c++ code to the Android NDK

    -   defines properties specific to individual modules, or libs

-   Application.mk - defines properties for all the modules that app uses

-   ndk-build -

-   toolchain

-   the dev tool is so important (eclipse is so terrible for this task)

#### about the linking [TO UPDATE]

-   Linking - concatenates blocks together, and decides on run-time locations for the concatenated blocks

    -   symbol resolution step - symbol table in .symtab associate each global symbol (functions and global variables) reference with a unique symbol definition

    -   relocation - associate a memory location with each symbol definition, and then make them point to the memory location meger all sections of the same type into a new aggregate section relocate symbol references so that they point to the correct run-time addresses

-   linking with static libraries

    -   related functions can be compiled into separate object modules and then packaged in a single static library file; At link time, the linker will copy only the object modules(symbol resolution) that are referenced by the program.

-   advantages
    need to maintain and update the static libraries periodically  
    At run time, the code of the functions like I/O functions is duplicated in the text segment of each running process

-   dynamic linking with shared libraries

    -   a single copy of the .text section of a shared libray in memory can be shared by different running

-   the basic idea is to link the relocation and symbol table info when the executable file is created, and then complete the linking process (code and data ) dynamically when the program is loaded
