import { query } from "./_generated/server";
import { v } from "convex/values";

export const getGameById = query({
  args: { id: v.id("games") },
  handler: async (ctx, args) => {
    return await ctx.db.get(args.id);
  },
});

export const getGameByNormalizedName = query({
  args: { normalized_name: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("games")
      .withIndex("by_normalized_name", (q) =>
        q.eq("normalized_name", args.normalized_name)
      )
      .unique();
  },
});

export const searchGamesByName = query({
  args: {
    q: v.string(),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.max(1, Math.min(args.limit ?? 20, 50));
    const byDisplay = await ctx.db
      .query("games")
      .withSearchIndex("search_display_name", (q) =>
        q.search("display_name", args.q)
      )
      .take(limit);
    // Optionally include normalized_name search as well; merge and de-dupe
    const byNormalized = await ctx.db
      .query("games")
      .withSearchIndex("search_normalized_name", (q) =>
        q.search("normalized_name", args.q)
      )
      .take(limit);
    const seen: Record<string, boolean> = {};
    const merged = [...byDisplay, ...byNormalized].filter((g) => {
      if (!g) return false;
      const id = g._id.toString();
      if (seen[id]) return false;
      seen[id] = true;
      return true;
    });
    return merged.slice(0, limit);
  },
});

export const listGamesByDecade = query({
  args: {
    decade: v.number(),
    cursor: v.optional(v.string()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.max(1, Math.min(args.limit ?? 25, 100));
    const page = await ctx.db
      .query("games")
      .withIndex("by_release_decade", (q) =>
        q.eq("release_decade", args.decade)
      )
      .paginate({ numItems: limit, cursor: args.cursor ?? null });
    return page;
  },
});

export const listGamesByYear = query({
  args: {
    year: v.number(),
    cursor: v.optional(v.string()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.max(1, Math.min(args.limit ?? 25, 100));
    const page = await ctx.db
      .query("games")
      .withIndex("by_release_year", (q) => q.eq("release_year", args.year))
      .paginate({ numItems: limit, cursor: args.cursor ?? null });
    return page;
  },
});

export const listGamesByDeveloper = query({
  args: {
    developer: v.string(),
    cursor: v.optional(v.string()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.max(1, Math.min(args.limit ?? 25, 100));
    // Try exact index match first
    let page = await ctx.db
      .query("games")
      .withIndex("by_developer", (q) => q.eq("developer", args.developer))
      .paginate({ numItems: limit, cursor: args.cursor ?? null });
    // If no results, try case-insensitive search index
    if (page.page.length === 0) {
      const hits = await ctx.db
        .query("games")
        .withSearchIndex("search_developer", (q) =>
          q.search("developer", args.developer)
        )
        .take(limit);
      return { page: hits, isDone: true, continueCursor: null } as any;
    }
    return page;
  },
});

export const listGamesByPublisher = query({
  args: {
    publisher: v.string(),
    cursor: v.optional(v.string()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.max(1, Math.min(args.limit ?? 25, 100));
    let page = await ctx.db
      .query("games")
      .withIndex("by_publisher", (q) => q.eq("publisher", args.publisher))
      .paginate({ numItems: limit, cursor: args.cursor ?? null });
    if (page.page.length === 0) {
      const hits = await ctx.db
        .query("games")
        .withSearchIndex("search_publisher", (q) =>
          q.search("publisher", args.publisher)
        )
        .take(limit);
      return { page: hits, isDone: true, continueCursor: null } as any;
    }
    return page;
  },
});

export const listGamesByPlatform = query({
  args: {
    platform: v.string(),
    decade: v.optional(v.number()),
    cursor: v.optional(v.string()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.max(1, Math.min(args.limit ?? 25, 100));
    const base = ctx.db.query("game_platforms");
    const q =
      args.decade != null
        ? base.withIndex("by_platform_decade", (x) =>
            x.eq("platform", args.platform).eq("release_decade", args.decade)
          )
        : base.withIndex("by_platform", (x) => x.eq("platform", args.platform));
    const page = await q.paginate({
      numItems: limit,
      cursor: args.cursor ?? null,
    });
    const games = await Promise.all(page.page.map((r) => ctx.db.get(r.gameId)));
    return { ...page, page: games.filter(Boolean) };
  },
});

export const listGamesByGenre = query({
  args: {
    genre: v.string(),
    decade: v.optional(v.number()),
    cursor: v.optional(v.string()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.max(1, Math.min(args.limit ?? 25, 100));
    const base = ctx.db.query("game_genres");
    const q =
      args.decade != null
        ? base.withIndex("by_genre_decade", (x) =>
            x.eq("genre", args.genre).eq("release_decade", args.decade)
          )
        : base.withIndex("by_genre", (x) => x.eq("genre", args.genre));
    const page = await q.paginate({
      numItems: limit,
      cursor: args.cursor ?? null,
    });
    const games = await Promise.all(page.page.map((r) => ctx.db.get(r.gameId)));
    return { ...page, page: games.filter(Boolean) };
  },
});

export const listGamesByTag = query({
  args: {
    tag: v.string(),
    decade: v.optional(v.number()),
    cursor: v.optional(v.string()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.max(1, Math.min(args.limit ?? 25, 100));
    const base = ctx.db.query("game_tags");
    const q =
      args.decade != null
        ? base.withIndex("by_tag_decade", (x) =>
            x.eq("tag", args.tag).eq("release_decade", args.decade)
          )
        : base.withIndex("by_tag", (x) => x.eq("tag", args.tag));
    const page = await q.paginate({
      numItems: limit,
      cursor: args.cursor ?? null,
    });
    const games = await Promise.all(page.page.map((r) => ctx.db.get(r.gameId)));
    return { ...page, page: games.filter(Boolean) };
  },
});

export const listGamesByVR = query({
  args: {
    is_vr: v.boolean(),
    cursor: v.optional(v.string()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.max(1, Math.min(args.limit ?? 25, 100));
    return await ctx.db
      .query("games")
      .withIndex("by_is_vr", (q) => q.eq("is_vr", args.is_vr))
      .paginate({ numItems: limit, cursor: args.cursor ?? null });
  },
});

export const listGamesByOnlineRequirement = query({
  args: {
    requires_online: v.boolean(),
    cursor: v.optional(v.string()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.max(1, Math.min(args.limit ?? 25, 100));
    return await ctx.db
      .query("games")
      .withIndex("by_requires_online", (q) =>
        q.eq("requires_online", args.requires_online)
      )
      .paginate({ numItems: limit, cursor: args.cursor ?? null });
  },
});

export const listGamesByPriceModel = query({
  args: {
    price_model: v.string(),
    cursor: v.optional(v.string()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.max(1, Math.min(args.limit ?? 25, 100));
    return await ctx.db
      .query("games")
      .withIndex("by_price_model", (q) => q.eq("price_model", args.price_model))
      .paginate({ numItems: limit, cursor: args.cursor ?? null });
  },
});

export const listGamesByFranchise = query({
  args: {
    franchise: v.string(),
    cursor: v.optional(v.string()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.max(1, Math.min(args.limit ?? 25, 100));
    // Try exact franchise index first
    let page = await ctx.db
      .query("games")
      .withIndex("by_franchise", (q) => q.eq("franchise", args.franchise))
      .paginate({ numItems: limit, cursor: args.cursor ?? null });
    if (page.page.length === 0) {
      // Fallback to text search on display_name for franchise string
      const hits = await ctx.db
        .query("games")
        .withSearchIndex("search_display_name", (q) =>
          q.search("display_name", args.franchise)
        )
        .take(limit);
      return { page: hits, isDone: true, continueCursor: null } as any;
    }
    return page;
  },
});

export const listGamesByRatingAtLeast = query({
  args: {
    min_rating: v.number(),
    cursor: v.optional(v.string()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.max(1, Math.min(args.limit ?? 25, 100));
    return await ctx.db
      .query("games")
      .withIndex("by_rating", (q) => q.gte("rating", args.min_rating))
      .paginate({ numItems: limit, cursor: args.cursor ?? null });
  },
});

export const listGamesByPlaytimeAtMost = query({
  args: {
    max_playtime: v.number(),
    cursor: v.optional(v.string()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.max(1, Math.min(args.limit ?? 25, 100));
    return await ctx.db
      .query("games")
      .withIndex("by_playtime", (q) =>
        q.lte("playtime_hours", args.max_playtime)
      )
      .paginate({ numItems: limit, cursor: args.cursor ?? null });
  },
});
