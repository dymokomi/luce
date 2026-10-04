# The Luce Guide

Luce is a compiled language for applications. If you know Python, most of it will look
familiar: blocks are indented, loops read `for name in names`, and lists, maps and strings
work much as they do there. The main differences are that types are checked before the
program runs, that a function which can fail says so in its signature, and that programs
compile to native executables. Memory is managed for you, as in Python.

## Install

On macOS or Linux:

```sh
curl -fsSL https://luce.luciaos.com/install.sh | sh && . "$HOME/.local/luce/env"
```

On Windows, in PowerShell:

```sh
irm https://luce.luciaos.com/install.ps1 | iex
```

This installs the compiler, `luce`, and the project tool, `luc`.
[Chapter 1 of the Tour](tour/01-hello.md) covers what you need and a first program.

## The documentation

The documentation comes in three parts.

**[The Tour](tour/README.md)** is an introduction in ten short chapters, each built around
programs you can run. It starts from a first `print` and ends with running work in
parallel. Read it in order.

**[The Guide](topics/README.md)** covers one topic per chapter in full: types, text,
collections, classes and memory, errors, generics, workers, packages, testing and the
tools. [Gotchas](topics/gotchas.md) lists the things most likely to surprise you, each
linked to where it is explained.

**[The Reference](../luce.md)** is the language specification: every rule, with the
reasoning behind it. The Tour and the Guide link to it where the exact wording matters.

The programs in this documentation are run as part of the compiler's tests, so their output
is what the current compiler prints.
