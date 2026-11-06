# The Legend of Zelda: Ocarina of Time (`0400486024DEC000`)

A Switch 2 game: update v131072, SDK 22.2.8 built for the Switch 2 (`Ounce`), NVN2 API 231.40. The Tears of the Kingdom engine family (sead / agl / gsys, Phive), modules `main`, `subsdk0` (the movie player) and `sdk`. This profile is the flaviopz fork's ([LEIAME-FLAVIOPZ.md](../../../LEIAME-FLAVIOPZ.md)): **plays on the Mac** (M4 MacBook Air, 16 GB) at 30 fps in handheld mode, Hyrule Field smooth; Castle Town still drops frames.

## What it needs

| Setting | Where | Why |
|---|---|---|
| `app_pool 0x240000000`, `mem_map_limit on` | [`game.tsv`](game.tsv) | the game keeps 2.74 GiB of the pool for its virtual-address heaps; without the limit it mapped 6 GB in Hyrule Field and a model heap ran out |
| `mem_reserve 0x620000000`, `mem_alias 0x400000000` | `game.tsv` | a Mac-only layout sized for room: a 16 GB alias region |
| `render_cond on` | `game.tsv` | agl wraps its clears in render conditions |
| frame step, model heap, movie renderer | [`patches.py`](patches.py) | the game ran at 45% speed at 27 fps, crashed when its model GPU heap filled in Hyrule Field, and stalled 61 s on the first movie |

## Settings it was played with

`DM_OPMODE=0 DM_FPS_TARGET=30 DM_NVN_GMEM_CHUNKS=1 DM_NVN_POOL_BUDGET_MB=32 DM_NVN_POOL_PER_FRAME=4 DM_NVN_UNC_ANY_POOL=1 DM_NVN_KEEP_SHARED_RETIRED=1`, in the app's `env.txt`. `DM_NVN_POOL_PER_FRAME` above about 5 is unsafe: the deferred release keeps a fixed 32 fences.

## Known issues

- Castle Town and the road to the castle drop frames: storage takeovers create and zero-fill tens of thousands of textures every 300 frames. `DM_NVN_TAKEOVER_REUSE=1` recycles them (76% fewer in a headless run), not yet approved in play.
- A white band along the Lon Lon Ranch fence in Hyrule Field, cause open.
- 2 task / mesh pipelines fail on a fragment input mismatch, so some foliage draws are missing.
- About 14 GB of memory in use.
