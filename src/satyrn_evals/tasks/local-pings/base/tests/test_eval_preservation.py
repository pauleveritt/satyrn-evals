import pytest

from .ifaces import AnotherService, Service, YetAnotherService


def _ping(_service) -> None:
    pass


# Curator-authored preservation test for the `local-pings` task, re-specified
# by the V5c amendment of 2026-09-02.
#
# The recorded adversary -- a get_pings that combines service types in a set
# -- loses the registry's insertion order only when the environment's set
# iteration scrambles. At the recorded fixture size (two registry-only
# services) this environment preserves insertion order deterministically, so
# the fixture scales the registered set to six registry-only services plus
# one local. See the V5c cross-machine research record for the mechanism
# (hash stride vs table geometry and allocation phase).
#
# Two parametrizations (forward and reversed registration order) guarantee
# that at least one case fails whenever the set scrambles: a single
# iteration order cannot match both registration orders. Node ids order0 and
# order1 are the fifth and sixth entries of the task's expected_test_ids
# after the three upstream local-ping tests.
class S2:  # third registry-only ping service (S0/S1 live in tests.ifaces)
    pass


class S3:
    pass


class S4:
    pass


class S5:
    pass


REGISTRY_SERVICES = (Service, AnotherService, S2, S3, S4, S5)


@pytest.mark.parametrize(
    "order",
    [REGISTRY_SERVICES, tuple(reversed(REGISTRY_SERVICES))],
)
def test_local_ping_keeps_registry_ping_order(registry, container, order):
    for svc in order:
        registry.register_factory(svc, svc, ping=_ping)
    container.register_local_factory(YetAnotherService, YetAnotherService, ping=_ping)

    pings = container.get_pings()

    local_svc_types = {rs.svc_type for rs in container._lazy_local_registry}
    registry_only = [p for p in pings if p._svc_type not in local_svc_types]

    assert [p._svc_type for p in registry_only] == list(order)
    assert any(p._svc_type is YetAnotherService for p in pings)


def test_environment_scrambles_registry_type_set(registry, container):
    """Canary: the row-3 gate is only meaningful on the scramble face.

    Mirrors the adversary's exact mechanism: the defective get_pings iterates
    ``set(registry._services) - local_svc_types``, and set subtraction
    rebuilds the table, so the check compares the *subtraction result's*
    iteration order against registry order -- not the raw source set.

    If this test fails, the environment is on the preserve face: the
    type-set adversary is undetectable by any order comparison here, the
    gate is INCONCLUSIVE (never a pass), and capture stops. This test is not
    part of the oracle's expected_test_ids; it is a gate-time guard.
    """
    for svc in REGISTRY_SERVICES:
        registry.register_factory(svc, svc, ping=_ping)
    container.register_local_factory(YetAnotherService, YetAnotherService, ping=_ping)

    local_svc_types = {rs.svc_type for rs in container._lazy_local_registry}
    registry_types = set(registry._services) - local_svc_types

    assert list(registry_types) != list(registry._services)
