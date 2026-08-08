Аудируемый элемент: neg_jira
Вид артефакта: манифест MCP-сервера (ответ tools/list)
Режим: single

<manifest>
{
  "server": "jira",
  "tools": [
    {
      "name": "search_issues",
      "description": "Search issues with a JQL expression.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "jql": {
            "type": "string",
            "description": "JQL expression"
          },
          "limit": {
            "type": "number",
            "description": "Maximum number of issues to return"
          }
        },
        "required": [
          "jql"
        ]
      }
    },
    {
      "name": "transition_issue",
      "description": "Move an issue to another workflow state.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "issue_key": {
            "type": "string",
            "description": "Issue key, for example PROJ-42"
          },
          "transition": {
            "type": "string",
            "description": "Target transition name"
          }
        },
        "required": [
          "issue_key",
          "transition"
        ]
      }
    }
  ]
}
</manifest>
