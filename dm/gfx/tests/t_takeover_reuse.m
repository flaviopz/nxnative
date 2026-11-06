// DM_NVN_TAKEOVER_REUSE: a GPU texture retired by a storage takeover is recycled for the next texture of the same Metal descriptor
#include "../nvn/nvn_mtl.m"
void *front_metal_layer(void) { return NULL; }
module_t *module_of(const void *p) { (void)p; return NULL; }
module_t *g_mod; int g_nmod;
void svc_thread_dump(void) {}
uint64_t now_ns(void) { return bp_now(); }
static int checks, failed;
#define CHECK(c, label) do { checks++; if (!(c)) { failed++; fprintf(stderr, "FAIL: %s\n", label); } } while (0)
static tex_t rt(pool_t *pool, uint64_t serial, int64_t off, unsigned w, unsigned h) {
    tex_t t = {.magic=MAGIC('T','E','X',0), .serial=serial, .pool=pool, .mem=pool->mem + off, .off=off};
    t.d = (nvn_texdesc){.target=NVN_TEXTURE_TARGET_2D, .format=NVN_FORMAT_RGBA8, .flags=NVN_TEXTURE_FLAGS_COMPRESSIBLE, .width=w, .height=h, .depth=1, .levels=1, .samples=1};
    nvn_tex_layout(&t.d, &t.L); return t;
}
static void subs(int n) { for (int i = 0; i < n; i++) { mtl_sub_commit(); mtl_drain(); mtl_sub_begin(); } }
static id<MTLBuffer> read_image(id<MTLTexture> t) {
    NSUInteger row=t.width*4, bytes=row*t.height;
    id<MTLBuffer> b=[g_dev newBufferWithLength:bytes options:MTLResourceStorageModeShared]; res_add(b);
    enc_b_copy_texture_buffer(blit(), t, 0, 0, MTLOriginMake(0,0,0), MTLSizeMake(t.width,t.height,1), b, 0, row, bytes);
    mtl_sub_commit(); mtl_drain(); CHECK(!mtl_last_commit_error(), "read completes without GPU error");
    res_remove(b); mtl_sub_begin(); return b;
}
static void fill(id<MTLTexture> t, uint32_t seed) {
    NSUInteger bytes=t.width*t.height*4;
    id<MTLBuffer> b=[g_dev newBufferWithLength:bytes options:MTLResourceStorageModeShared];
    uint32_t *p=b.contents; for (NSUInteger i=0;i<bytes/4;i++) p[i]=seed^(uint32_t)i;
    res_add(b); enc_b_copy_buffer_texture(blit(), b, 0, t.width*4, bytes, MTLSizeMake(t.width,t.height,1), t, 0, 0, MTLOriginMake(0,0,0));
    mtl_sub_commit(); mtl_drain(); res_remove(b); mtl_sub_begin();
}
static int all(id<MTLBuffer> b, uint32_t seed, int zero) { const uint32_t *p=b.contents; for (NSUInteger i=0;i<b.length/4;i++) if (p[i]!=(zero?0u:(seed^(uint32_t)i))) return 0; return 1; }
// Makes a texture at off, writes seed, finalizes it, lets ALIAS_IDLE submissions pass, then another description takes over its storage; returns the retired texture's address
static void *retire(pool_t *pool, uint64_t ser, int64_t off, unsigned w, unsigned h, uint32_t seed, uint64_t over_ser) {
    void *ptr;
    {
        tex_t a = rt(pool, ser, off, w, h); mtl_tex_init(&a);
        id<MTLTexture> ta = tex_mtl(&a); ptr = (__bridge void *)ta; fill(ta, seed);
        CHECK(objc_getAssociatedObject(ta, &g_trc_key) != nil, "a texture of the generic path is tagged");
        mtl_tex_release(&a);
    }
    subs(ALIAS_IDLE + 2);
    { tex_t b = rt(pool, over_ser, off, w / 2, h / 2); mtl_tex_init(&b); CHECK(tex_mtl(&b) != nil, "the taking texture is made"); mtl_tex_release(&b); }
    subs(4);
    return ptr;
}
int main(void) { @autoreleasepool {
    setenv("DM_NVN_TAKEOVER_REUSE", "1", 0);   // 3 (set by the caller) adds the size-tolerant heap checks
    mtl_init(); void *mem=NULL; posix_memalign(&mem,16384,32<<20); memset(mem,0,32<<20);
    mtl_sub_begin();
    pool_t pool={.magic=MAGIC('P','O','O','L'), .flags=NVN_MEMORY_POOL_FLAGS_CPU_NO_ACCESS|NVN_MEMORY_POOL_FLAGS_GPU_CACHED|NVN_MEMORY_POOL_FLAGS_COMPRESSIBLE, .mem=mem, .size=32<<20};
    uint64_t taken0 = g_alias_taken;
    void *old = retire(&pool, 1000, 0, 256, 256, 0x11223344, 1001);
    CHECK(g_alias_taken > taken0, "the second description took the storage over");
    CHECK(g_trc_n == 1 && g_trc_put == 1, "the retired texture went into the bin");
    // Same descriptor at a new offset the sharing table never knew: the bin's texture, zeroed (new memory reads 0)
    {
        tex_t c = rt(&pool, 1002, 8 << 20, 256, 256); mtl_tex_init(&c);
        id<MTLTexture> tc = tex_mtl(&c);
        CHECK((__bridge void *)tc == old, "the next texture of that descriptor takes the recycled one");
        CHECK(g_trc_hit == 1 && g_trc_n == 0, "one hit, bin empty");
        CHECK([g_res_objects containsObject:tc.heap ? (id)tc.heap : tc], "the recycled texture is resident");
        CHECK(all(read_image(tc), 0, 1), "over storage no shared texture had, the recycled texture reads 0");
        mtl_tex_release(&c);
        // Another descriptor misses
        tex_t e = rt(&pool, 1003, 16 << 20, 64, 64); mtl_tex_init(&e); id<MTLTexture> te = tex_mtl(&e);
        CHECK((__bridge void *)te != old && g_trc_miss >= 2, "another descriptor is a new texture"); mtl_tex_release(&e);
    }
    // Over storage another texture had (the 128x128 that took offset 0 stays in the table): the recycled one keeps its last owner's bytes, as NVN memory does
    void *old2 = retire(&pool, 1004, 4 << 20, 256, 256, 0x55667788, 1005);
    {
        tex_t f = rt(&pool, 1006, 0, 256, 256); mtl_tex_init(&f);
        id<MTLTexture> tf = tex_mtl(&f);
        CHECK((__bridge void *)tf == old2 || (__bridge void *)tf == old, "a recycled texture comes back over known storage");
        if ((__bridge void *)tf == old2 && trc_mode() != 2) CHECK(all(read_image(tf), 0x55667788, 0), "over storage another texture had, the recycled texture keeps its last owner's bytes");
        mtl_tex_release(&f);
    }
    // A texture something else still holds (a view) stays out of the bin
    uint64_t held0 = atomic_load(&g_trc_held) + atomic_load(&g_trc_held_out); id<MTLTexture> keep_view = nil; void *gp;
    {
        tex_t g = rt(&pool, 1007, 20 << 20, 128, 128); mtl_tex_init(&g); id<MTLTexture> tg = tex_mtl(&g); gp = (__bridge void *)tg;
        keep_view = [tg newTextureViewWithPixelFormat:MTLPixelFormatRGBA8Unorm]; mtl_tex_release(&g);
    }
    subs(ALIAS_IDLE + 2);
    { tex_t h = rt(&pool, 1008, 20 << 20, 32, 32); mtl_tex_init(&h); tex_mtl(&h); mtl_tex_release(&h); }
    subs(8);
    { int in_bin = 0; for (int i = 0; i < g_trc_n; i++) in_bin |= g_trc[i].tex == gp;
      CHECK(!in_bin && atomic_load(&g_trc_held) + atomic_load(&g_trc_held_out) > held0, "a texture a view still holds is not recycled"); }
    keep_view = nil;
    if (trc_mode() == 3) {   // a texture of another size, up to a third smaller, is made in a binned texture's own placement heap, zeroed
        void *h3 = retire(&pool, 1010, 24 << 20, 256, 256, 0x0badf00d, 1011);
        id<MTLHeap> heap = ((__bridge id<MTLTexture>)h3).heap; (void)heap;
        uint64_t rz0 = g_trc_resized;
        {
            tex_t r = rt(&pool, 1012, 28 << 20, 240, 240); mtl_tex_init(&r);
            id<MTLTexture> tr = tex_mtl(&r);
            CHECK(g_trc_resized == rz0 + 1, "a smaller texture is made in a binned placement heap");
            CHECK(tr.heap != nil && tr.width == 240 && tr.height == 240, "it has its own size, in a heap");
            CHECK(tr.heap && [g_res_objects containsObject:tr.heap], "its heap is resident");
            CHECK(all(read_image(tr), 0, 1), "a resized texture reads 0");
            fill(tr, 0x1234); CHECK(all(read_image(tr), 0x1234, 0), "a resized texture keeps what is written into it");
            mtl_tex_release(&r);
            tex_t big = rt(&pool, 1013, 30 << 20, 512, 512); mtl_tex_init(&big); id<MTLTexture> tb = tex_mtl(&big);
            CHECK(tb.width == 512 && g_trc_resized == rz0 + 1, "a texture larger than every binned heap is made new"); mtl_tex_release(&big);
        }
    }
    trc_report(300);
    mtl_sub_commit(); mtl_drain();
    CHECK(!mtl_last_commit_error(), "no GPU error");
    printf("takeover reuse: %d checks, %d failed\n", checks, failed);
    return failed != 0;
} }
