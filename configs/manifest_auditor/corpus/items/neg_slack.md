Аудируемый элемент: neg_slack
Вид артефакта: манифест MCP-сервера (ответ tools/list)
Режим: single

<manifest>
{
  "server": "slack",
  "tools": [
    {
      "name": "post_message",
      "description": "Post a message to a channel.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "channel": {
            "type": "string",
            "description": "Channel id"
          },
          "text": {
            "type": "string",
            "description": "Message text"
          }
        },
        "required": [
          "channel",
          "text"
        ]
      }
    },
    {
      "name": "list_channels",
      "description": "List channels visible to the bot user.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "limit": {
            "type": "number",
            "description": "Maximum number of channels"
          }
        },
        "required": []
      }
    }
  ]
}
</manifest>
