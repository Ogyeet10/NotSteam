import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  games: defineTable({
    // Identity & Search
    display_name: v.string(),
    normalized_name: v.string(),
    aliases: v.optional(v.array(v.string())),
    summary: v.string(),
    franchise: v.optional(v.string()),

    // Credits
    developer: v.optional(v.string()),
    publisher: v.optional(v.string()),

    // Release/Era
    release_year: v.optional(v.float64()),
    release_decade: v.optional(v.float64()),

    // Classification
    age_rating: v.optional(v.string()),
    setting: v.optional(v.string()),
    perspective: v.optional(v.string()),
    world_type: v.optional(v.string()),
    price_model: v.optional(v.string()),
    story_focus: v.optional(v.string()),

    // Gameplay & Meta
    playtime_hours: v.optional(v.float64()),
    rating: v.optional(v.float64()),

    // Boolean Features
    has_microtransactions: v.optional(v.boolean()),
    is_vr: v.optional(v.boolean()),
    has_mods: v.optional(v.boolean()),
    requires_online: v.optional(v.boolean()),
    cross_platform: v.optional(v.boolean()),
    is_remake_or_remaster: v.optional(v.boolean()),
    is_dlc: v.optional(v.boolean()),
    procedurally_generated: v.optional(v.boolean()),

    // Relationships
    parent_game: v.union(v.id("games"), v.null()),

    // Original Arrays (kept for completeness)
    genre: v.optional(v.array(v.string())),
    platforms: v.optional(v.array(v.string())),
    tags: v.optional(v.array(v.string())),
    multiplayer_type: v.optional(v.array(v.string())),
    input_methods: v.optional(v.array(v.string())),

    // System
    createdAt: v.float64(),
    updatedAt: v.float64(),
  })
    // Text Search
    .searchIndex("search_display_name", { searchField: "display_name" })
    .searchIndex("search_normalized_name", { searchField: "normalized_name" })
    .searchIndex("search_summary", { searchField: "summary" })
    .searchIndex("search_developer", { searchField: "developer" })
    .searchIndex("search_publisher", { searchField: "publisher" })
    // Exact/Range Filters
    .index("by_normalized_name", ["normalized_name"])
    .index("by_release_year", ["release_year"])
    .index("by_release_decade", ["release_decade"])
    .index("by_rating", ["rating"])
    .index("by_playtime", ["playtime_hours"])
    .index("by_is_vr", ["is_vr"])
    .index("by_has_mods", ["has_mods"])
    .index("by_has_microtransactions", ["has_microtransactions"])
    .index("by_requires_online", ["requires_online"])
    .index("by_cross_platform", ["cross_platform"])
    .index("by_is_dlc", ["is_dlc"])
    .index("by_is_remake_or_remaster", ["is_remake_or_remaster"])
    .index("by_procedural", ["procedurally_generated"])
    .index("by_price_model", ["price_model"])
    .index("by_world_type", ["world_type"])
    .index("by_perspective", ["perspective"])
    .index("by_setting", ["setting"])
    .index("by_age_rating", ["age_rating"])
    .index("by_franchise", ["franchise"])
    .index("by_developer", ["developer"])
    .index("by_publisher", ["publisher"])
    .index("by_parent_game", ["parent_game"]),

  game_platforms: defineTable({
    gameId: v.id("games"),
    platform: v.string(), // normalized
    release_year: v.optional(v.float64()),
    release_decade: v.optional(v.float64()),
  })
    .index("by_platform", ["platform"])
    .index("by_platform_decade", ["platform", "release_decade"])
    .index("by_platform_year", ["platform", "release_year"])
    .index("by_game", ["gameId"]),

  game_genres: defineTable({
    gameId: v.id("games"),
    genre: v.string(), // normalized
    release_year: v.optional(v.float64()),
    release_decade: v.optional(v.float64()),
  })
    .index("by_genre", ["genre"])
    .index("by_genre_decade", ["genre", "release_decade"])
    .index("by_genre_year", ["genre", "release_year"])
    .index("by_game", ["gameId"]),

  game_tags: defineTable({
    gameId: v.id("games"),
    tag: v.string(), // normalized
    release_year: v.optional(v.float64()),
    release_decade: v.optional(v.float64()),
  })
    .index("by_tag", ["tag"])
    .index("by_tag_decade", ["tag", "release_decade"])
    .index("by_tag_year", ["tag", "release_year"])
    .index("by_game", ["gameId"]),

  game_multiplayer: defineTable({
    gameId: v.id("games"),
    mode: v.string(), // e.g., online, co-op, split-screen, local
    release_year: v.optional(v.float64()),
    release_decade: v.optional(v.float64()),
  })
    .index("by_mode", ["mode"])
    .index("by_mode_decade", ["mode", "release_decade"])
    .index("by_mode_year", ["mode", "release_year"])
    .index("by_game", ["gameId"]),

  game_inputs: defineTable({
    gameId: v.id("games"),
    input: v.string(), // e.g., controller, kb+m, touch
    release_year: v.optional(v.float64()),
    release_decade: v.optional(v.float64()),
  })
    .index("by_input", ["input"])
    .index("by_input_decade", ["input", "release_decade"])
    .index("by_input_year", ["input", "release_year"])
    .index("by_game", ["gameId"]),

  // Store aliases as separate normalized strings per game for indexing and search
  game_aliases: defineTable({
    gameId: v.id("games"),
    alias: v.string(), // normalized lowercase alias/nickname/acronym
    notes: v.optional(v.string()), // optional rationale/description
  })
    .index("by_game", ["gameId"])
    .index("by_alias", ["alias"]) // exact match index
    .searchIndex("search_alias", { searchField: "alias" }),
});
