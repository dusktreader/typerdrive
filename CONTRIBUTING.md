# Contributing Guidelines

## Security Concerns

Before any further discussion, a point about security needs to be addressed:

> [!WARNING]
> If you find a serious security vulnerability that could affect current users, please report it to maintainers via
> email or some form of private communication. For other issue reports, see below.


## Thanks!

First, thank you for your interest in contributing to typerdrive! Even though this is mostly a personal project,
it takes a bit of work to keep it maintained. All contributions help and improve it.


## Contact Us

The maintainers of typerdrive can be reached most easily via email:

* **Tucker Beck**: [tucker.beck@gmail.com](mailto:tucker.beck@gmail.com)


## Conduct

Everyone's conduct should be respectful and friendly. For most folks, these things don't need to be spelled out.
However, to establish a baseline of acceptable conduct, the typerdrive project expects contributors to adhere to
the [Code of Conduct](./CONDUCT.md) for this project. Any issues working with other contributors should be reported to
the maintainers


## Contribution Recommendations

### Github Issues

The first and primary source of contributions is opening issues on github. Please feel free to open issues when you find
problems or wish to request a feature. All issues will be treated seriously and taken under consideration. However, the
maintainers may disregard/close issues at their discretion.

Issues are most helpful when they contain specifics about the problem they address. Specific error messages, references
to specific lines of code, environment contexts, and such are extremely helpful.


### Code Contributions

Code contributions should be submitted via pull-requests on github. Project maintainers will review pull-requests and
may test new features out. All merge requests should come with commit messages that describe the changes as well as a
reference to the issue that the code addresses. Commit messages should also adhere to
[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)

Commit messages should look like this:

```
fix: Fixed gizmo component that was parfolecting

Addresses Issue #56

The parfolection happening in the gizmo component was causing a vulterability in the anti-parfolection checks during the
enmurculation process.

This was addressed by caching the restults of parfolection prior to enmurculation.

Also:
* Added and updated unit tests
* Added documentation
* Cleaned up some code
```

> [!Note]
> The maintainers of typerdrive _hate_ the use of `!` to indicate breaking changes in the subject line. If you
> introduce a breaking change, please note it in a _footer_ instead.

Code contributions should follow best-practices where possible. Use the
[Zen of Python](https://www.python.org/dev/peps/pep-0020/) as a guideline. All code must stick to pep8 style guidelines.

Adding additional dependencies should be limited except where needed functionality can be easily added through pip
packages. Please include dependencies that are only applicable to development and testing in the dev dependency list.
Packages should only be added to the dependency lists if:

* They are actively maintained
* They are widely used
* They are hosted on pypi.org
* They have source code hosted on a public repository (github, gitlab, bitbucket, etc)
* They include tests in their repositories
* They include a software license


### Documentation

Help with documentation is *always* welcome.

The typerdrive project uses [mkdocs-material](https://squidfunk.github.io/mkdocs-material/) for document
generation.

Documentation lives in the `docs` subdirectory.

Documentation should be clear, include examples where possible, and reference source material as much as possible.

Documentation through code comments should be kept to a minimum. Code should
be as self-documenting as possible. If a section of code needs some explanation,
the bulk of it should be be presented as docstrings that use
[Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
`docstrings <https://www.python.org/dev/peps/pep-0257/>`_ for methods, modules,
and classes.

> [!Note]
> The maintainers of typerdrive don't like starting the docstring on the same line as the triple-quotes.
> Instead, the > docstring should stat on a new line:
>
> ```python
> def gizmo():
>     """"
>     Parfolect the enmurculation process.
>     """
>     ...
> ```


## Non-preferred Contributions

There are some types of contribution that aren't as helpful and are not as welcome:

* Complaints without suggestion
* Criticism about the overall approach of the extension
* Copied code without attribution
* Promotion of personal packages/projects without due need
* Sarcasm/ridicule of contributions or design choices
