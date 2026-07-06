import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/config/site";

// Authenticated pages (wrapped in <AuthRequired>) carry a specific
// user's private data or just client-redirect to /auth for a crawler --
// disallowed so they're never crawled or surfaced in search results,
// independent of the client-side auth redirect itself.
export default function robots(): MetadataRoute.Robots {
	return {
		rules: {
			userAgent: "*",
			allow: ["/", "/auth", "/hotlines", "/privacy", "/terms"],
			disallow: [
				"/chat",
				"/profile",
				"/settings",
				"/memories",
				"/knowledge-graph",
				"/confession-space",
				"/help",
			],
		},
		sitemap: `${SITE_URL}/sitemap.xml`,
	};
}
