import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/config/site";

// Only routes that render without requiring login belong here. /help,
// /chat, /profile, /memories, /knowledge-graph, /settings, and
// /confession-space all wrap in <AuthRequired>, which client-redirects
// an unauthenticated visitor (or crawler) straight to /auth -- so they
// carry no indexable content and must stay out of both the sitemap and
// search results.
export default function sitemap(): MetadataRoute.Sitemap {
	return [
		{
			url: SITE_URL,
			lastModified: new Date(),
			changeFrequency: "monthly",
			priority: 1,
		},
		{
			url: `${SITE_URL}/auth`,
			lastModified: new Date(),
			changeFrequency: "yearly",
			priority: 0.8,
		},
		{
			url: `${SITE_URL}/hotlines`,
			lastModified: new Date(),
			changeFrequency: "monthly",
			priority: 0.6,
		},
		{
			url: `${SITE_URL}/privacy`,
			lastModified: new Date(),
			changeFrequency: "yearly",
			priority: 0.3,
		},
		{
			url: `${SITE_URL}/terms`,
			lastModified: new Date(),
			changeFrequency: "yearly",
			priority: 0.3,
		},
	];
}
