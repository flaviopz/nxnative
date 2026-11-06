# Ocarina of Time v131072's own code, keyed by the NSO build ID.
CUTS = {
    # The movie player's choice of renderer: the branch it takes for a movie with no NDVE resource, always. Movies then go through its plain nv12decode program instead of nn::ndve's 22 compute shaders (a 61 s pipeline stall on first use, 50 to 100 ms of GPU a frame on an M4).
    'e0f3ccfaf50065ae4ea01eb5aeb13b1a': [(0x3b5f51c, '680100b4', '0b000014', 'movie renderer: always plain, no NDVE'),
        # gsys::ModelResourceMgr's shared GPU heap (main+0xf3b720, from the config key ModelResourceMgrGpuHeap): 16 pools of 1 MiB, trimmed to fit, that hold every model's MatBlock and DisplayList.
        # In Hyrule Field it filled (no free byte, 16 of 16 pools used, probe at main+0x436f24); main+0x502050's false return is ignored and the next material buffer is built on a NULL pool (crash).
        # Twice the configured size (32 pools); costs 16 MiB. x23 = size + 0xfffff -> 2*size + 0xfffff
        (0xf3b760, '3700088b', '1705018b', 'model resource GPU heap: twice the configured size')],
}

from nso_asm import ADRP, B

# Frame step and render scale, as Tears of the Kingdom's (same engine). The game steps its time by 60 / int fps (timing +0x58, read at main+0x3b4eadc and main+0x6e6c98; the clock main+0x3b4e300)
# and stays locked at 60: on a Mac that renders 27 fps it ran at 45% speed. The stub replaces the picker's tail call in main+0x4dbd60: int fps = 60 / the host's step. Target 0 or no step yet: the original picker
def frame_step(ctx):
    here, emit, site, put, S = ctx.here, ctx.emit, ctx.site, ctx.put, ctx.state
    site(0x4dbd94, '73ccd914')
    start = here(); emit(ADRP(16, here(), S))
    for w in (0xb9400209,  # ldr w9,[x16]        target
              0x34000149,  # cbz w9,off
              0xb9402209,  # ldr w9,[x16,#0x20]  step
              0x34000109,  # cbz w9,off
              0x5280078a,  # mov w10,#60
              0x1ac9094a,  # udiv w10,w10,w9
              0xb900580a,  # str w10,[x0,#0x58]  int fps
              0xf9401a0b,  # ldr x11,[x16,#0x30]
              0x8b29416b,  # add x11,x11,w9,uxtw
              0xf9001a0b,  # str x11,[x16,#0x30] vsyncs stepped
              0xd65f03c0): # ret
        emit(w)
    emit(B(here(), 0x3b4ef60))  # off
    put(0x4dbd94, [B(0x4dbd94, start)], 'frame step from the host in whole vsyncs (target 0 = original picker)')
    # View scales x state +0x10 on every size path of main+0x654e70; 1.0 = the original
    site(0x654efc, '4918231e')
    start = here(); emit(ADRP(10, here(), S))
    for w in (0xbd401146,  # ldr s6,[x10,#0x10]
              0x1e2020c8,  # fcmp s6,#0.0
              0x5400006d,  # b.le +12
              0x1e260800,  # fmul s0,s0,s6
              0x1e260821,  # fmul s1,s1,s6
              0x1e231849): # fdiv s9,s2,s3 (original)
        emit(w)
    emit(B(here(), 0x654f00))
    put(0x654efc, [B(0x654efc, start)], 'view render size x the host render scale (1.0 = original)'); ctx.render_scale = 1

FRAME_STEP = {'e0f3ccfaf50065ae4ea01eb5aeb13b1a': frame_step}

BINDING = [
    {'what': 'movie renderer: always the plain nv12decode path, no NDVE', 'now': 'build', 'goal': 'game', 'purpose': 'shaders',
     'why': "a branch in the game's own movie player: NDVE's 22 compute shaders stalled the first movie for 61 s and cost 50 to 100 ms of GPU a frame on an M4"},
    {'what': 'gsys ModelResourceMgr shared GPU heap: twice the configured size', 'now': 'build', 'goal': 'game', 'purpose': 'memory',
     'why': "the size comes from the game's own config key ModelResourceMgrGpuHeap; in Hyrule Field its 16 pools filled and the next material buffer was built on a NULL pool (crash)"},
    {'what': 'frame step and render scale, as Tears of the Kingdom', 'now': 'build', 'goal': 'game', 'purpose': 'frame rate',
     'why': "the game steps its time by 60 / its own fps value and stays locked at 60: at 27 fps on a Mac it ran at 45% speed",
     'blocked': 'frame-step stubs have no function-matched form yet'},
]
