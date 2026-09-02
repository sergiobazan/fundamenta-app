export const site = {
  name: "Fundamenta",
  legalName: "Fundamenta",
  tagline: "Los estados financieros, finalmente legibles.",
  siteUrl: import.meta.env.PUBLIC_SITE_URL || "http://localhost:4321",
  appUrl: import.meta.env.PUBLIC_APP_URL || "http://localhost:3000",
  contactEmail: import.meta.env.PUBLIC_CONTACT_EMAIL || "",
  gaId: import.meta.env.PUBLIC_GA_MEASUREMENT_ID || "",
  businessAddress: import.meta.env.PUBLIC_BUSINESS_ADDRESS || "",
  mapEmbedUrl: import.meta.env.PUBLIC_MAP_EMBED_URL || "",
  directionsUrl: import.meta.env.PUBLIC_DIRECTIONS_URL || "",
};

export const reviews: Array<{
  quote: string;
  author: string;
  role: string;
  permissionRecorded: boolean;
}> = [];
