Аудируемый элемент: hard_prompt_manager
Вид артефакта: манифест MCP-сервера (ответ tools/list)
Режим: single

<manifest>
{
  "server": "prompt_library",
  "tools": [
    {
      "name": "get_prompt",
      "description": "Return the stored system prompt template by name. Templates are versioned; the latest version is returned unless a version is given.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "description": "Template name"
          },
          "version": {
            "type": "string",
            "description": "Template version, omit for the latest"
          }
        },
        "required": [
          "name"
        ]
      }
    },
    {
      "name": "save_prompt",
      "description": "Store a system prompt template verbatim under a name.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "description": "Template name"
          },
          "body": {
            "type": "string",
            "description": "Template body, stored verbatim"
          }
        },
        "required": [
          "name",
          "body"
        ]
      }
    }
  ]
}
</manifest>
