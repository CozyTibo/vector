"""Linear GraphQL: doc-only notes for the mock (subset in dataset_generator)."""

# The mock implements a small operational subset of https://api.linear.app/graphql
# sufficient for OAuth completion (`viewer { organization { id name } }`) and smoke queries.

LINEAR_GRAPHQL_SUBSET = """
type Query {
  viewer: User!
  issues(first: Int, after: String): IssueConnection!
  issue(id: ID!): Issue
}

type User {
  id: ID!
  name: String!
  email: String
  organization: Organization
}

type Organization {
  id: ID!
  name: String!
}
"""
