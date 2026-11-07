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

`DM_OPMODE=0 DM_FPS_TARGET=30 DM_NVN_GMEM_CHUNKS=1 DM_NVN_POOL_BUDGET_MB=32 DM_NVN_POOL_PER_FRAME=4 DM_NVN_UNC_ANY_POOL=1 DM_NVN_KEEP_SHARED_RETIRED=1`, in the app's `env.txt`. The memory ones and `DM_FPS_TARGET=30` are this profile's `env.txt`, which the build bakes into every app (`build_env_file`): a Mac mini M4 app built without them reached 19 GB of GPU allocations on entering the game ("Insufficient Memory", a black screen). `DM_NVN_POOL_PER_FRAME` above about 5 is unsafe: the deferred release keeps a fixed 32 fences.

## Button mods

`button_mods/make_mods.py` makes two RomFS overlays from the player's RomFS: `xbox/` and `ps/`, with the symbol font's button glyphs (E040-E04C), the HUD and ocarina button textures, and the "Controles básicos" controller art, its dark variant, shadow and callout lines (all three slots: handheld, grip, Pro). The labels follow position, as an Xbox or PlayStation pad is mapped by position (the right button is the game's A). The controller drawings `xbox.png` and `ps5.png` were drawn from photos of the real pads; nothing of the game is in the folder. The font must keep its original decompressed size (ResourceSizeTable), so the generator trims and pads it. The Mac app build runs the generator (it needs numpy, Pillow, scipy, shapely, fonttools and astc-encoder-py, and skips it without them) and packs the result as `Resources/button_mods`; the host picks a folder by the gamepad connected at start (`DM_BUTTON_MODS`, `DM_BUTTONS`). In test: not yet approved in play.

## Known issues

- Castle Town and the road to the castle drop frames: storage takeovers create and zero-fill tens of thousands of textures every 300 frames. `DM_NVN_TAKEOVER_REUSE=1` recycles them (76% fewer in a headless run), not yet approved in play.
- A white band along the Lon Lon Ranch fence in Hyrule Field, cause open.
- 2 task / mesh pipelines fail on a fragment input mismatch, so some foliage draws are missing.
- About 14 GB of memory in use.
