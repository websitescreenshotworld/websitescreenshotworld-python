# Releasing

1. Move the "Unreleased" section of `CHANGELOG.md` under the new version and date, and add its link at the bottom.
2. Set `__version__` in `src/websitescreenshotworld/_version.py`.
3. Commit, then tag that commit `v<version>`, such as `v0.1.1`, and push the tag.
4. The tag's workflow runs the tests again, builds the wheel and the source archive, and publishes
   `websitescreenshotworld` to PyPI through trusted publishing (environment `pypi`). No token is stored anywhere.

The libraries for the other languages share the version number, so a change made in all of them is released at
the same version in each.
