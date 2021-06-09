# Invoker: Python Research Project Bootstrapper

Invoker is a tool for bootstrapping small python projects which are often necessary in
my research. Key design goals of this tool are to

1. Streamline creation of simple scripts with easily controllable parameters
2. Simplify the process of swapping different implementations of modules
3. Take care of tedious steps such as
    - saving and loading configurations of past executions, and
    - enabling job re-runs with past configurations
4. Produce a resultant codebase that is independent of the tool itself.

The design considerations for this tool force a very specific style of code organization
and approach to software development; in certain ways, this approach to writing code
might be very bad practice. However, invoker does a good job of eliminating extra steps
in developing small python projects and rapidly prototyping research ideas.

In my case, this tool has been incredibly useful for creating simple synthetic datasets,
processing large datasets, as well as training and evaluating neural network models.

## Motivation

When I'm starting a new project, there is always a lot of "plumbing" I NEED to do, as
well as a lot of "nice-to-have" features that I WANT. The "plumbing" is the simple
stuff like setting up a way to pass parameters from a config file, defining properly
abstracted modules etc. that either can be achieved via a simple boilerplate and proper
planning. But the "nice-to-have" features are often cast aside due to time constraints.
These are stuff like being able to save the set of all configurations used in the current
execution for record keeping, or setting up proper logging which would make debugging
much easier. This tool attempts to make the "plumbing" parts more seamless and also
to introduce many "nice-to-have" features for free.

Most of the abstractions introduced in this tool are due to specific pains I've found
myself dealing with on a regular basis for every new project I started on. At first this
tool started off as a boilerplate which I'd copy-paste between projects, but over time
it becamse cumbersome to keep track of which files to copy, what parts of the boilerplate
to change, and how to incorporate new code-infra changes to multiple existing projects.

### Keeping track of execution parameters

Every script I write ends up with over a dozen variable parameters, ranging from I/O
path related strings, to knobs and flags that change the behavior of the script. Keeping
track of a set of parameters which might be used by another script as a dependency is a
pain. Instead, invoker takes care of all the annoying parts of parameter handling by
saving the parameters into a configuration file upon execution and loads them as
necessary.

### Easily swappable modules

Often I need to change up the implementation of a module used by a script, often multiple
times, making such changes, although not difficult, is often cumbersome and error-prone.
Invoker allows me to easily implement multiple variants of a module and dynamically load
the one I need via the script's config variable.

### Standalone codebases

Once a project is completed, and/or the results have been published, making the codebase
runnable with little effort with as few esoteric dependencies is crucial. Although
invoker enforces a lot of specific structures onto the codebase, the resultant codebase
does not depend on invoker at runtime. Additionally, I'm currently working on extending
invoker so that it can automatically re-organize the codebase to make it even more
conducive for publication.

## Installation

Clone the repository:

```
git clone https://github.com/budmonde/invoker.git
```

Navigate into the repo, and run:

```
pip install invoker
```

## Documentation

Basic tutorial and documentation at
[invoke.readthedocs.io](https://invoke.readthedocs.io/).

## Dependencies

```
pyyaml
```
