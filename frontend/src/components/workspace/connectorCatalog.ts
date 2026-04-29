export type CatalogItem = {
  id: string;
  name: string;
  live: boolean;
};

export const CONNECTOR_CATALOG: { category: string; items: CatalogItem[] }[] = [
  {
    category: "Engineering",
    items: [
      { id: "github", name: "GitHub", live: true },
      { id: "gitlab", name: "GitLab", live: false },
    ],
  },
  {
    category: "Project management",
    items: [
      { id: "linear", name: "Linear", live: true },
      { id: "jira", name: "Jira", live: false },
    ],
  },
  {
    category: "Communication",
    items: [{ id: "slack", name: "Slack", live: true }],
  },
  {
    category: "Documentation",
    items: [{ id: "notion", name: "Notion", live: false }],
  },
];

export const ALL_CATALOG_TOOL_IDS: string[] = CONNECTOR_CATALOG.flatMap((g) => g.items.map((i) => i.id));
