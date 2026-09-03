# V5c capture reconstruction — stopped at the qualification gate

**Date:** 2026-09-02
**Status:** stopped — row 3 of the qualification table does not reproduce
deterministically on this machine.

## What was done

V5c reconstructs `local-pings` from its recorded synthetic pair. The
reconstruction was carried out against the public `hynek/svcs` repository:

- upstream base `31bc6dfd`, upstream target `52c6689d`
  (`2026-08-27-local-pings-corrected-probe.md:56-59`).
- Synthetic base = upstream base + the target's test changes
  (`tests/test_container.py`) + the re-authored curator preservation test.
- Synthetic fix = the target's source change (`src/svcs/_core.py`,
  `get_pings` gains locally-defined services).

The target commit splits cleanly: source change in `src/svcs/_core.py`,
test changes in `tests/test_container.py` (`make_ping_stub` fixture plus
`test_local_pings_are_retrieved`, `test_local_pings_override_global_pings`,
`test_local_services_without_pings_discard_global_pings`).

## The re-authored curator test

`tests/test_eval_preservation.py`, re-authored from the probe's description
(`2026-08-27-local-pings-corrected-probe.md:36-49`):

```python
from .ifaces import AnotherService, Service, YetAnotherService


def _ping(_service) -> None:
    pass


def test_local_ping_keeps_registry_ping_order(registry, container):
    registry.register_factory(Service, Service, ping=_ping)
    registry.register_factory(AnotherService, AnotherService, ping=_ping)
    container.register_local_factory(YetAnotherService, YetAnotherService, ping=_ping)

    pings = container.get_pings()

    local_svc_types = {rs.svc_type for rs in container._lazy_local_registry}
    registry_only = [p for p in pings if p._svc_type not in local_svc_types]

    assert [p._svc_type for p in registry_only] == [Service, AnotherService]
    assert any(p._svc_type is YetAnotherService for p in pings)
```

The four-test oracle is the three upstream local-ping tests plus this
curator test.

## Qualification result

The three-row table, re-recorded against the synthetic pair:

| Row | Input | Expected (`:62-68`) | Observed |
| --- | --- | ---: | ---: |
| 1 | base | 0 pass, 4 fail | 0 pass, 4 fail ✅ |
| 2 | upstream known-good patch | 4 pass | 4 pass ✅ |
| 3 | set-union patch | 3 pass, 1 fail | flaky ❌ |

Row 3 over six fresh processes: four runs 4 pass, two runs 3 pass / 1 fail.
The curator test does not catch the set-union patch deterministically here.

## Why row 3 does not reproduce

The set-union patch reconstructs the recorded defect — it combines the
remaining service types in a `set`
(`set(self.registry._services) - local_svc_types`), losing the registry's
insertion order. Whether the curator test catches that depends on the set's
iteration order over two class objects, which is `id()`-based (ASLR) and
therefore non-deterministic across processes on this machine. The probe's
frozen environment had "controlled class hashes" that made the failure
deterministic (`2026-08-27-local-pings-corrected-probe.md:42-44`); this
machine does not.

## Stop condition

Per the V5c spec's risk 2, this is a stop-and-record condition, not a
tune-until-green. The oracle, environment, and patch are unchanged. V5c's
done-when — the three-row table reproducing exactly — is not met
deterministically here.

**Reopens** under a controlled-hash environment (the frozen Python 3.14
environment with its controlled class hashes, or an equivalent that makes
the set-union patch's order loss deterministic), or with a re-proposal of
the oracle so that row 3's signal does not depend on hash order.

## Recomputation

```bash
git clone https://github.com/hynek/svcs.git upstream
cd upstream && git checkout 31bc6dfd
git apply <(git diff 31bc6dfd 52c6689d -- tests/test_container.py)   # test changes
# add tests/test_eval_preservation.py as above
git commit -m base; git apply <(git diff 31bc6dfd 52c6689d -- src/svcs/_core.py)
git commit -m fix
# oracle = the three upstream local-ping tests + the curator test
# rows 1 and 2: run the oracle at base and at fix
# row 3: apply a set-union variant of get_pings; run the oracle across
#        multiple fresh processes to observe the flakiness
```

Scratch artifacts live under `/tmp/satyrn-v5c/` and are not committed.

## Correction and re-record (2026-09-02, after the adversary decision)

**Correction to this record.** This record's row-3 patch was described as a
"set-union patch" combining service types in a set. The follow-up
investigation established the known cause of the recorded flakiness: the
record's own set-union patch preserved insertion order on the processes
where row 3 read as passing, and whether order is preserved is a discrete
function of hash stride versus set-table geometry and the classes'
allocation phase — not a residual probability (see the cross-machine
research record). The N=2 recorded size does not reproduce on this machine:
measured 0/60 caught under the curator tests (both parametrizations) in the
pytest context. The record's "controlled class hashes" phrasing also
cannot have meant hash seeding: `PYTHONHASHSEED` does not move
`id()`-based class hashes, so the frozen environment must have controlled
allocation layout.

**Re-specification (maintainer-confirmed).** Row 3's adversary is now the
type-set at six registry-only services, per the spec amendment
(`docs/superpowers/specs/2026-09-02-v5c-capture-admitted-suite-design.md`):
a re-specification, not a reproduction. The rebuilt synthetic pair (durable
scratch `~/projects/pauleveritt/satyrn-v5c-scratch/pair`):

```text
upstream base:    31bc6dfd5d1a570b3b96cfefd878ccc686bde980
upstream target:  52c6689d34ce80c0f5a754f95d2aad54837402df
N=6 task base:    71f5f5c  (31bc6df + target's test changes + N=6 curator
                            test with forward/reversed parametrization +
                            canary + pyproject pythonpath=["src"])
N=6 task fix:     96341fa  (upstream source change to get_pings)
```

The oracle is the five ids: three upstream local-ping tests plus
`tests/test_eval_preservation.py::test_local_ping_keeps_registry_ping_order[order0]`
and `[order1]`.

**Re-recorded qualification table** (this machine, Python 3.14.2; each row
runs the five oracle ids plus the canary in one fresh pytest process):

| Row | Input | Oracle | Canary | Runs |
| --- | --- | ---: | --- | ---: |
| 1 | base | 0 pass, 5 fail | scramble face (ok) | 5/5 |
| 2 | base + known-good (fix diff) | 5 pass | scramble face (ok) | 5/5 |
| 3 | base + type-set patch | 3 pass, 2 fail | scramble face (ok) | 20/20 |

Row 3 caught the adversary in 20/20 fresh processes (both curator cases
failed in every run; the parametrization's guarantee — at least one case
fails whenever the set scrambles — held with margin). No row read
inconclusive; the gate is meaningful on this machine at N=6.

Recompute:

```bash
cd ~/projects/pauleveritt/satyrn-v5c-scratch
./venv/bin/python exp/qualify_gate.py "1,2" 5   # rows 1-2
./venv/bin/python exp/qualify_gate.py "3" 20    # row 3, 20 fresh processes
```
