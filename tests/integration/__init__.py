"""Integration tier package.

Makes this directory a package so pytest's prepend import mode gives these
modules distinct names (``integration.test_attempt`` vs ``test_attempt`` in
``tests/``). Without it, the two same-basename modules collide at
collection time and the default tier fails to collect.
"""
