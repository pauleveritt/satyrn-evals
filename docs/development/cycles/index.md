# Investigation cycles

Each cycle finds one candidate pathology behind a deterministic-reproducer
entry gate, applies the smallest remedy or records why none should be applied,
has the result reviewed, and closes before the next opens. The loop itself is
defined in [the overnight cycle protocol](../../current/overnight-cycle-protocol.md).

These are kept **because several of them concluded against a change**. A cycle
that measured a real pathology and then refuted its own remedy is the most
expensive kind of finding to rediscover, and the least likely to be written
down anywhere else.

| cycle | subject | outcome |
|---|---|---|
| [1](cycle-01.md) | Engine messages that fail to redirect the model | Pathology real; remedy written and **refuted**; numbers later found to describe a retired breaker |
| [2](cycle-02.md) | Do those numbers describe the shipping breaker? | **84% of refusals survive** the fix; a whole-run replay proved an invalid instrument |
| [3](cycle-03.md) | Telling *refused-while-stuck* from *refused-while-progressing* | A real discriminator; the remedy's margin shrank to near break-even under review, and ships **off** |
| [4](cycle-04.md) | A session loop that never repeats consecutively | A window detector reaches it; the separating margin is **one call**, and is stated as such |

**The batch evidence stays outside version control**, under `~/satyrn-smokes/`:
transcripts, patches, receipts, preflight records and per-batch results are
large, are pinned to the commit their preflight recorded, and are never edited
after the fact. What is committed here is the reasoning and the decisions —
including the ones that were wrong and were corrected.

```{toctree}
:hidden:

cycle-01
cycle-02
cycle-03
cycle-04
```
