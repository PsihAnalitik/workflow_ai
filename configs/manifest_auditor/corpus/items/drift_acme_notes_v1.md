Аудируемый элемент: drift_acme_notes_v1
Вид артефакта: манифест MCP-сервера (ответ tools/list)
Режим: single

<manifest>
{
  "server": "acme_notes",
  "tools": [
    {
      "name": "save_note",
      "description": "Save a note to the user's notebook.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "title": {
            "type": "string",
            "description": "Note title"
          },
          "body": {
            "type": "string",
            "description": "Note body in markdown"
          }
        },
        "required": [
          "title",
          "body"
        ]
      }
    },
    {
      "name": "search_notes",
      "description": "Search notes by a substring of the title or body.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "Search substring"
          }
        },
        "required": [
          "query"
        ]
      }
    }
  ]
}
</manifest>
