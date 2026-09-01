import { defineCollection } from 'astro:content'
import { glob } from 'astro/loaders'
import { z } from 'astro/zod'

const docs = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/docs' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    order: z.number(),
    sidebarGroup: z.enum(['Start', 'System', 'Reference']),
    // coerce: YAML parses ISO dates like 2026-08-31 as Date objects
    updated: z.coerce.string().optional(),
  }),
})

export const collections = { docs }