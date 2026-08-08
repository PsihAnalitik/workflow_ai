Аудируемый элемент: hard_override_config
Вид артефакта: манифест MCP-сервера (ответ tools/list)
Режим: single

<manifest>
{
  "server": "app_config",
  "tools": [
    {
      "name": "override_setting",
      "description": "Override a configuration value of the running application. The override applies until the next restart and does not apply to settings marked as immutable.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "key": {
            "type": "string",
            "description": "Setting key in dotted form"
          },
          "value": {
            "type": "string",
            "description": "New value as a string"
          }
        },
        "required": [
          "key",
          "value"
        ]
      }
    },
    {
      "name": "list_overrides",
      "description": "List configuration overrides active right now.",
      "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
      }
    }
  ]
}
</manifest>
