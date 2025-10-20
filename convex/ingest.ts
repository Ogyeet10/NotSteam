import { mutation } from "./_generated/server";
import { v } from "convex/values";

function normalizeString(value: string | undefined | null): string | undefined {
  if (value == null) return undefined;
  return value.toString().trim().toLowerCase();
}

function computeDecade(year: number | undefined): number | undefined {
  if (year === undefined || Number.isNaN(year)) return undefined;
  return Math.floor(year / 10) * 10;
}

export const addGame = mutation({
  args: {
    display_name: v.string(),
    normalized_name: v.optional(v.union(v.string(), v.null())),
    summary: v.string(),
    release_year: v.optional(v.union(v.float64(), v.null())),
    developer: v.optional(v.union(v.string(), v.null())),
    publisher: v.optional(v.union(v.string(), v.null())),
    franchise: v.optional(v.union(v.string(), v.null())),
    genre: v.optional(v.union(v.array(v.string()), v.null())),
    platforms: v.optional(v.union(v.array(v.string()), v.null())),
    age_rating: v.optional(v.union(v.string(), v.null())),
    setting: v.optional(v.union(v.string(), v.null())),
    perspective: v.optional(v.union(v.string(), v.null())),
    world_type: v.optional(v.union(v.string(), v.null())),
    multiplayer_type: v.optional(v.union(v.array(v.string()), v.null())),
    input_methods: v.optional(v.union(v.array(v.string()), v.null())),
    story_focus: v.optional(v.union(v.string(), v.null())),
    playtime_hours: v.optional(v.union(v.float64(), v.null())),
    tags: v.optional(v.union(v.array(v.string()), v.null())),
    rating: v.optional(v.union(v.float64(), v.null())),
    price_model: v.optional(v.union(v.string(), v.null())),
    has_microtransactions: v.optional(v.union(v.boolean(), v.null())),
    is_vr: v.optional(v.union(v.boolean(), v.null())),
    has_mods: v.optional(v.union(v.boolean(), v.null())),
    requires_online: v.optional(v.union(v.boolean(), v.null())),
    cross_platform: v.optional(v.union(v.boolean(), v.null())),
    is_remake_or_remaster: v.optional(v.union(v.boolean(), v.null())),
    is_dlc: v.optional(v.union(v.boolean(), v.null())),
    // Accept an Id, null, or a string (display name) to resolve.
    parent_game: v.optional(v.union(v.id("games"), v.null(), v.string())),
    procedurally_generated: v.optional(v.union(v.boolean(), v.null())),
    // Optional aliases to attach during insertion
    aliases: v.optional(v.union(v.array(v.string()), v.null())),
  },
  handler: async (ctx, args) => {
    const now = Date.now();
    const releaseYear = args.release_year ?? undefined;
    const releaseDecade = computeDecade(releaseYear);

    const normalizedName = (args.normalized_name ?? args.display_name)!;

    // Idempotent insert: skip if already present by normalized_name.
    const existing = await ctx.db
      .query("games")
      .withIndex("by_normalized_name", (q) =>
        q.eq("normalized_name", normalizedName)
      )
      .unique();

    if (existing) {
      // If aliases were included, attach them to existing game as well
      const aliases = (args.aliases ?? undefined) as
        | (string[] | undefined)
        | undefined;
      if (aliases && aliases.length > 0) {
        for (const a of aliases) {
          const aliasNorm = normalizeString(a);
          if (!aliasNorm) continue;
          await ctx.db.insert("game_aliases", {
            gameId: existing._id,
            alias: aliasNorm,
          });
        }
      }
      return { _id: existing._id, inserted: false };
    }

    // Resolve parent_game if provided as a string (by normalized_name or display_name)
    let parentGameId: any = null;
    if (typeof args.parent_game === "string") {
      const parentRaw = args.parent_game;
      const parent = await ctx.db
        .query("games")
        .withIndex("by_normalized_name", (q) =>
          q.eq("normalized_name", parentRaw)
        )
        .unique();
      parentGameId = parent?._id ?? null;
    } else if (args.parent_game && typeof args.parent_game === "object") {
      parentGameId = args.parent_game;
    } else {
      parentGameId = null;
    }

    const gameId = await ctx.db.insert("games", {
      display_name: args.display_name,
      normalized_name: normalizedName,
      aliases: undefined,
      summary: args.summary,
      franchise: (args.franchise ?? undefined) as any,
      developer: (args.developer ?? undefined) as any,
      publisher: (args.publisher ?? undefined) as any,
      release_year: releaseYear,
      release_decade: releaseDecade,
      age_rating: (args.age_rating ?? undefined) as any,
      setting: (args.setting ?? undefined) as any,
      perspective: (args.perspective ?? undefined) as any,
      world_type: (args.world_type ?? undefined) as any,
      price_model: (args.price_model ?? undefined) as any,
      story_focus: (args.story_focus ?? undefined) as any,
      playtime_hours: args.playtime_hours ?? undefined,
      rating: args.rating ?? undefined,
      has_microtransactions: args.has_microtransactions ?? undefined,
      is_vr: args.is_vr ?? undefined,
      has_mods: args.has_mods ?? undefined,
      requires_online: args.requires_online ?? undefined,
      cross_platform: args.cross_platform ?? undefined,
      is_remake_or_remaster: args.is_remake_or_remaster ?? undefined,
      is_dlc: args.is_dlc ?? undefined,
      procedurally_generated: args.procedurally_generated ?? undefined,
      parent_game: parentGameId,
      genre: args.genre ?? undefined,
      platforms: args.platforms ?? undefined,
      tags: args.tags ?? undefined,
      multiplayer_type: args.multiplayer_type ?? undefined,
      input_methods: args.input_methods ?? undefined,
      createdAt: now,
      updatedAt: now,
    });

    // Insert join rows (normalized values)
    const safeInsertMany = async (
      table:
        | "game_platforms"
        | "game_genres"
        | "game_tags"
        | "game_multiplayer"
        | "game_inputs",
      values: (string | undefined)[] | undefined,
      fieldName: "platform" | "genre" | "tag" | "mode" | "input"
    ) => {
      if (!values || values.length === 0) return;
      for (const raw of values) {
        if (raw === undefined) continue;
        await ctx.db.insert(table, {
          gameId,
          [fieldName]: raw as any,
          release_year: releaseYear,
          release_decade: releaseDecade,
        } as any);
      }
    };

    await safeInsertMany(
      "game_platforms",
      args.platforms ?? undefined,
      "platform"
    );
    await safeInsertMany("game_genres", args.genre ?? undefined, "genre");
    await safeInsertMany("game_tags", args.tags ?? undefined, "tag");
    await safeInsertMany(
      "game_multiplayer",
      args.multiplayer_type ?? undefined,
      "mode"
    );
    await safeInsertMany(
      "game_inputs",
      args.input_methods ?? undefined,
      "input"
    );

    // Insert aliases into game_aliases table (normalized)
    const aliases = (args.aliases ?? undefined) as
      | (string[] | undefined)
      | undefined;
    if (aliases && aliases.length > 0) {
      for (const a of aliases) {
        const aliasNorm = normalizeString(a);
        if (!aliasNorm) continue;
        await ctx.db.insert("game_aliases", { gameId, alias: aliasNorm });
      }
    }

    return { _id: gameId, inserted: true };
  },
});

export const upsertAliases = mutation({
  args: {
    // Title of the game (display or normalized); we'll try both
    title: v.string(),
    aliases: v.array(v.string()),
    notes: v.optional(v.union(v.string(), v.null())),
  },
  handler: async (ctx, args) => {
    const title = args.title;
    const normalizedCandidate = normalizeString(title);

    // Try to find game by normalized_name first using both raw and normalizedCandidate
    let game = await ctx.db
      .query("games")
      .withIndex("by_normalized_name", (q) => q.eq("normalized_name", title))
      .unique();
    if (!game && normalizedCandidate && normalizedCandidate !== title) {
      game = await ctx.db
        .query("games")
        .withIndex("by_normalized_name", (q) =>
          q.eq("normalized_name", normalizedCandidate)
        )
        .unique();
    }
    // Fallback: text search on display_name
    if (!game) {
      const hits = await ctx.db
        .query("games")
        .withSearchIndex("search_display_name", (q) =>
          q.search("display_name", title)
        )
        .take(1);
      game = hits[0];
    }
    if (!game) {
      return { _id: null, upserted: 0 } as any;
    }

    let upserted = 0;
    for (const a of args.aliases) {
      const aliasNorm = normalizeString(a);
      if (!aliasNorm) continue;
      // Check if alias already exists for this game
      const existingForAlias = await ctx.db
        .query("game_aliases")
        .withIndex("by_alias", (q) => q.eq("alias", aliasNorm))
        .take(50);
      const already = existingForAlias.some((row) => row.gameId === game!._id);
      if (already) continue;
      await ctx.db.insert("game_aliases", {
        gameId: game._id,
        alias: aliasNorm,
        notes: args.notes ?? undefined,
      });
      upserted += 1;
    }
    return { _id: game._id, upserted } as any;
  },
});

export const updateGame = mutation({
  args: {
    id: v.id("games"),
    display_name: v.optional(v.string()),
    normalized_name: v.optional(v.union(v.string(), v.null())),
    summary: v.optional(v.string()),
    release_year: v.optional(v.union(v.float64(), v.null())),
    developer: v.optional(v.union(v.string(), v.null())),
    publisher: v.optional(v.union(v.string(), v.null())),
    franchise: v.optional(v.union(v.string(), v.null())),
    genre: v.optional(v.union(v.array(v.string()), v.null())),
    platforms: v.optional(v.union(v.array(v.string()), v.null())),
    age_rating: v.optional(v.union(v.string(), v.null())),
    setting: v.optional(v.union(v.string(), v.null())),
    perspective: v.optional(v.union(v.string(), v.null())),
    world_type: v.optional(v.union(v.string(), v.null())),
    multiplayer_type: v.optional(v.union(v.array(v.string()), v.null())),
    input_methods: v.optional(v.union(v.array(v.string()), v.null())),
    story_focus: v.optional(v.union(v.string(), v.null())),
    playtime_hours: v.optional(v.union(v.float64(), v.null())),
    tags: v.optional(v.union(v.array(v.string()), v.null())),
    rating: v.optional(v.union(v.float64(), v.null())),
    price_model: v.optional(v.union(v.string(), v.null())),
    has_microtransactions: v.optional(v.union(v.boolean(), v.null())),
    is_vr: v.optional(v.union(v.boolean(), v.null())),
    has_mods: v.optional(v.union(v.boolean(), v.null())),
    requires_online: v.optional(v.union(v.boolean(), v.null())),
    cross_platform: v.optional(v.union(v.boolean(), v.null())),
    is_remake_or_remaster: v.optional(v.union(v.boolean(), v.null())),
    is_dlc: v.optional(v.union(v.boolean(), v.null())),
    parent_game: v.optional(v.union(v.id("games"), v.null(), v.string())),
    procedurally_generated: v.optional(v.union(v.boolean(), v.null())),
    aliases: v.optional(v.union(v.array(v.string()), v.null())),
  },
  handler: async (ctx, args) => {
    const now = Date.now();
    const existing = await ctx.db.get(args.id);
    if (!existing) {
      return { _id: args.id, updated: false } as any;
    }

    const releaseYear =
      args.release_year ?? (existing.release_year as number | undefined);
    const releaseDecade = computeDecade(releaseYear);

    const normalizedName = (args.normalized_name ??
      args.display_name ??
      existing.normalized_name) as string;

    await ctx.db.patch(args.id, {
      display_name: (args.display_name ??
        (existing.display_name as any)) as any,
      normalized_name: normalizedName,
      summary: (args.summary ?? (existing.summary as any)) as any,
      franchise: (args.franchise ?? (existing.franchise as any)) as any,
      developer: (args.developer ?? (existing.developer as any)) as any,
      publisher: (args.publisher ?? (existing.publisher as any)) as any,
      release_year: releaseYear ?? undefined,
      release_decade: releaseDecade ?? undefined,
      age_rating: (args.age_rating ?? (existing.age_rating as any)) as any,
      setting: (args.setting ?? (existing.setting as any)) as any,
      perspective: (args.perspective ?? (existing.perspective as any)) as any,
      world_type: (args.world_type ?? (existing.world_type as any)) as any,
      price_model: (args.price_model ?? (existing.price_model as any)) as any,
      story_focus: (args.story_focus ?? (existing.story_focus as any)) as any,
      playtime_hours: (args.playtime_hours ??
        (existing.playtime_hours as any)) as any,
      rating: (args.rating ?? (existing.rating as any)) as any,
      has_microtransactions: (args.has_microtransactions ??
        (existing.has_microtransactions as any)) as any,
      is_vr: (args.is_vr ?? (existing.is_vr as any)) as any,
      has_mods: (args.has_mods ?? (existing.has_mods as any)) as any,
      requires_online: (args.requires_online ??
        (existing.requires_online as any)) as any,
      cross_platform: (args.cross_platform ??
        (existing.cross_platform as any)) as any,
      is_remake_or_remaster: (args.is_remake_or_remaster ??
        (existing.is_remake_or_remaster as any)) as any,
      is_dlc: (args.is_dlc ?? (existing.is_dlc as any)) as any,
      procedurally_generated: (args.procedurally_generated ??
        (existing.procedurally_generated as any)) as any,
      parent_game: (args.parent_game ?? (existing.parent_game as any)) as any,
      genre: (args.genre ?? (existing.genre as any)) as any,
      platforms: (args.platforms ?? (existing.platforms as any)) as any,
      tags: (args.tags ?? (existing.tags as any)) as any,
      multiplayer_type: (args.multiplayer_type ??
        (existing.multiplayer_type as any)) as any,
      input_methods: (args.input_methods ??
        (existing.input_methods as any)) as any,
      updatedAt: now,
    } as any);

    // Replace join rows with current arrays if provided
    const clearJoin = async (
      table:
        | "game_platforms"
        | "game_genres"
        | "game_tags"
        | "game_multiplayer"
        | "game_inputs"
        | "game_aliases"
    ) => {
      const rows = await ctx.db
        .query(table)
        .withIndex("by_game", (q) => q.eq("gameId", args.id))
        .take(1000);
      for (const r of rows) {
        await ctx.db.delete(r._id);
      }
    };

    const safeInsertMany = async (
      table:
        | "game_platforms"
        | "game_genres"
        | "game_tags"
        | "game_multiplayer"
        | "game_inputs",
      values: (string | undefined)[] | undefined,
      fieldName: "platform" | "genre" | "tag" | "mode" | "input"
    ) => {
      if (!values || values.length === 0) return;
      for (const raw of values) {
        if (raw === undefined) continue;
        await ctx.db.insert(table, {
          gameId: args.id,
          [fieldName]: raw as any,
          release_year: releaseYear ?? undefined,
          release_decade: releaseDecade ?? undefined,
        } as any);
      }
    };

    if (args.platforms != null) {
      await clearJoin("game_platforms");
      await safeInsertMany(
        "game_platforms",
        args.platforms ?? undefined,
        "platform"
      );
    }
    if (args.genre != null) {
      await clearJoin("game_genres");
      await safeInsertMany("game_genres", args.genre ?? undefined, "genre");
    }
    if (args.tags != null) {
      await clearJoin("game_tags");
      await safeInsertMany("game_tags", args.tags ?? undefined, "tag");
    }
    if (args.multiplayer_type != null) {
      await clearJoin("game_multiplayer");
      await safeInsertMany(
        "game_multiplayer",
        args.multiplayer_type ?? undefined,
        "mode"
      );
    }
    if (args.input_methods != null) {
      await clearJoin("game_inputs");
      await safeInsertMany(
        "game_inputs",
        args.input_methods ?? undefined,
        "input"
      );
    }
    if (args.aliases != null) {
      await clearJoin("game_aliases");
      const aliases = (args.aliases ?? undefined) as
        | (string[] | undefined)
        | undefined;
      if (aliases && aliases.length > 0) {
        for (const a of aliases) {
          const aliasNorm = normalizeString(a);
          if (!aliasNorm) continue;
          await ctx.db.insert("game_aliases", {
            gameId: args.id,
            alias: aliasNorm,
          });
        }
      }
    }

    return { _id: args.id, updated: true } as any;
  },
});
